/**
 * 统一 API 客户端：封装 dashboard、agents、decisions、HITL、audit 接口。
 *
 * - 开发环境：请求走 Vite 代理（vite.config.ts 中 /api → http://localhost:8000）。
 * - 生产环境：可通过 VITE_API_BASE 指定后端地址。
 * - 所有错误统一归一化为 ApiError，便于页面展示明确的错误信息。
 * - 当前阶段使用 3–5 秒轮询（见 hooks/usePolling.ts）；
 *   后续将切换到后端 /ws/updates 的持续 WebSocket 推送（代理已就绪）。
 */

import type {
  AgentStatus,
  AuditEvent,
  DashboardSummary,
  Decision,
  HealthInfo,
  HitlRequest,
  SensorReading,
  Thresholds,
} from '../types';

const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, '') ?? '';

export const POLL_INTERVAL_MS = 4000;
const DEFAULT_TIMEOUT_MS = 10_000;
const LONG_TIMEOUT_MS = 120_000;

export type ApiErrorKind = 'http' | 'network' | 'parse' | 'timeout';

/** 归一化后的 API 错误，message 为可直接展示给用户的中文描述 */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly url: string;

  constructor(kind: ApiErrorKind, message: string, url: string, status: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.url = url;
    this.status = status;
  }
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}

/** 把任意错误转成面向用户的提示文案 */
export function describeError(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.message) return err.message;
  return '发生未知错误，请稍后重试';
}

function httpStatusMessage(status: number, detail: string): string {
  const byStatus: Record<number, string> = {
    400: '请求参数不合法',
    401: '未授权，请检查访问凭证',
    403: '无权访问该资源',
    404: '接口不存在或已下线',
    409: '请求与当前状态冲突',
    422: '请求参数校验失败',
    429: '请求过于频繁，请稍后再试',
    500: '后端服务器内部错误',
    502: '后端网关错误',
    503: '后端服务暂时不可用',
    504: '后端响应超时',
  };
  const prefix = byStatus[status] ?? `后端返回 HTTP ${status}`;
  return detail ? `${prefix}：${detail}` : prefix;
}

interface RequestOptions extends RequestInit {
  /** 请求超时（毫秒） */
  timeoutMs?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...rest } = options;
  const url = `${API_BASE}${path}`;

  const controller = new AbortController();
  let timedOut = false;
  const onExternalAbort = () => controller.abort();
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  if (rest.signal) {
    if (rest.signal.aborted) controller.abort();
    else rest.signal.addEventListener('abort', onExternalAbort, { once: true });
  }

  try {
    let res: Response;
    try {
      res = await fetch(url, {
        ...rest,
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(headers ?? {}) },
        signal: controller.signal,
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        if (timedOut) {
          throw new ApiError('timeout', `后端响应超时（${Math.round(timeoutMs / 1000)}s）：${path}`, url);
        }
        // 调用方主动取消（如轮询切换/卸载），原样抛出以便上层静默处理
        throw err;
      }
      throw new ApiError(
        'network',
        `无法连接后端服务：请确认后端已启动（${API_BASE || '代理目标 http://localhost:8000'}），接口 ${path}`,
        url,
      );
    }

    let payload: unknown = null;
    const text = await res.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        throw new ApiError('parse', `后端返回了无法解析的数据（接口 ${path}），请检查后端版本是否匹配`, url, res.status);
      }
    }

    if (!res.ok) {
      const detail =
        typeof payload === 'object' && payload !== null && 'detail' in payload
          ? String((payload as { detail: unknown }).detail)
          : '';
      throw new ApiError('http', httpStatusMessage(res.status, detail), url, res.status);
    }

    return payload as T;
  } finally {
    window.clearTimeout(timer);
    rest.signal?.removeEventListener('abort', onExternalAbort);
  }
}

/** 判断是否为“主动取消”，轮询层据此跳过错误提示 */
export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError';
}

/** 后端 REST 接口的统一封装 */
export const api = {
  /** GET /api/health */
  getHealth: () => request<HealthInfo>('/api/health'),

  /** GET /api/dashboard/summary：传感器 + 最新决策 + 待审批数 + Agent 数 */
  getDashboardSummary: () => request<DashboardSummary>('/api/dashboard/summary'),

  /** GET /api/sensors/latest */
  getSensorsLatest: () => request<SensorReading | null>('/api/sensors/latest'),

  /** GET /api/agents/status */
  getAgentsStatus: () => request<AgentStatus[]>('/api/agents/status'),

  /** POST /api/agents/run：触发一轮完整多智能体决策（可能耗时较长） */
  runAgents: () => request<Decision>('/api/agents/run', { method: 'POST', timeoutMs: LONG_TIMEOUT_MS }),

  /** GET /api/decisions */
  getDecisions: () => request<Decision[]>('/api/decisions'),

  /** GET /api/decisions/latest：无决策时返回 null */
  getLatestDecision: async (): Promise<Decision | null> => {
    const result = await request<Decision | { message: string }>('/api/decisions/latest');
    return 'priority_actions' in result ? result : null;
  },

  /** GET /api/hitl/pending */
  getPendingHitl: () => request<HitlRequest[]>('/api/hitl/pending'),

  /** POST /api/hitl/{id}/approve */
  approveHitl: (id: string) => request<HitlRequest>(`/api/hitl/${encodeURIComponent(id)}/approve`, { method: 'POST' }),

  /** POST /api/hitl/{id}/reject */
  rejectHitl: (id: string) => request<HitlRequest>(`/api/hitl/${encodeURIComponent(id)}/reject`, { method: 'POST' }),

  /** GET /api/audit/history?limit=n */
  getAuditHistory: (limit = 100) => request<AuditEvent[]>(`/api/audit/history?limit=${limit}`),

  /** GET /api/config/thresholds */
  getThresholds: () => request<Thresholds>('/api/config/thresholds'),
};
