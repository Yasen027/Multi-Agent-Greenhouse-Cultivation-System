/**
 * 轮询数据 Hook（阶段 2：3–5 秒轮询）。
 * 后续阶段将替换为 /ws/updates 的持续 WebSocket 推送。
 *
 * 特性：
 * - 挂载后立即拉取一次，随后按固定间隔刷新；
 * - 页面不可见时暂停轮询，恢复可见时立即补拉；
 * - 后台刷新失败保留旧数据，通过 error 字段提示；
 * - 卸载时清理定时器并取消在途请求。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { POLL_INTERVAL_MS, isAbortError } from '../services/api';

export interface PollingResult<T> {
  /** 最近一次成功的数据；从未成功时为 null */
  data: T | null;
  /** 最近一次失败的错误；成功后自动清空 */
  error: Error | null;
  /** 首次加载中（尚无任何数据） */
  loading: boolean;
  /** 后台刷新中（已保留旧数据） */
  refreshing: boolean;
  /** 最近一次成功时间（epoch ms） */
  lastUpdated: number | null;
  /** 手动立即刷新 */
  refresh: () => Promise<void>;
  /** 就地更新数据（如审批后从列表移除一项） */
  setData: (updater: T | ((prev: T | null) => T)) => void;
}

export function usePolling<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  intervalMs: number = POLL_INTERVAL_MS,
  deps: readonly unknown[] = [],
): PollingResult<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const fetcherRef = useRef(fetcher);
  const inFlightRef = useRef(false);
  const mountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const run = useCallback(async (background: boolean) => {
    if (inFlightRef.current) return; // 跳过重叠请求
    inFlightRef.current = true;
    if (background) setRefreshing(true);
    else setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const result = await fetcherRef.current(controller.signal);
      if (!mountedRef.current) return;
      setDataState(result);
      setError(null);
      setLastUpdated(Date.now());
    } catch (err) {
      if (!mountedRef.current) return;
      if (isAbortError(err)) return; // 主动取消：静默
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      inFlightRef.current = false;
      abortRef.current = null;
      if (mountedRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void run(false);

    const timer = window.setInterval(() => {
      if (document.visibilityState !== 'hidden') void run(true);
    }, intervalMs);

    const onVisibility = () => {
      if (document.visibilityState === 'visible') void run(true);
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      mountedRef.current = false;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
      abortRef.current?.abort();
    };
    // deps 变化（如筛选条件）时重建轮询
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);

  const refresh = useCallback(() => run(true), [run]);

  const setData = useCallback((updater: T | ((prev: T | null) => T)) => {
    setDataState((prev) => (typeof updater === 'function' ? (updater as (p: T | null) => T)(prev) : updater));
  }, []);

  return { data, error, loading, refreshing, lastUpdated, refresh, setData };
}
