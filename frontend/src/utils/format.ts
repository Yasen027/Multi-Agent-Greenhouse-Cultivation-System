/** 展示格式化工具 */

/** ISO 时间 → 本地可读时间 */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('zh-CN', { hour12: false });
}

/** 相对时间（如“3 秒前”） */
export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const diffSec = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (diffSec < 60) return `${diffSec} 秒前`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小时前`;
  return `${Math.round(diffHour / 24)} 天前`;
}

/** 审计 payload → 单行 JSON 摘要（可截断） */
export function summarizePayload(payload: unknown, max = 240): string {
  if (payload === null || payload === undefined) return '—';
  let text: string;
  try {
    text = typeof payload === 'string' ? payload : JSON.stringify(payload);
  } catch {
    text = String(payload);
  }
  return text.length > max ? `${text.slice(0, max)}…` : text;
}
