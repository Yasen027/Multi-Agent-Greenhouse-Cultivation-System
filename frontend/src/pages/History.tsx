/** 历史审计页：审计事件流（4 秒轮询），支持按事件类型过滤 */

import { useMemo, useState } from 'react';
import { History as HistoryIcon, RefreshCw } from 'lucide-react';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState, Loading } from '../components/StatusViews';
import { usePolling } from '../hooks/usePolling';
import { api, describeError } from '../services/api';
import type { AuditEvent } from '../types';
import { formatTime } from '../utils/format';
import { formatAuditPayload, translateAuditEvent } from '../utils/i18n';

/** 事件类型 → 徽章配色 */
function badgeClass(event: string): string {
  if (event === 'decision') return 'badge-normal';
  if (event === 'sensor_reading') return 'badge-info';
  if (event.startsWith('hitl_')) return 'badge-warning';
  if (event.startsWith('crop_identification')) return 'badge-purple';
  if (event.startsWith('actuator_command_blocked')) return 'badge-danger';
  if (event.startsWith('actuator_command')) return 'badge-teal';
  return 'badge-neutral';
}

export function History() {
  const { data, error, loading, refreshing, refresh } = usePolling(() => api.getAuditHistory(100));
  const [filter, setFilter] = useState<string>('all');

  // 反转数组让最新事件排最前，再按筛选条件过滤
  const events = useMemo(() => {
    const list = [...(data ?? [])].reverse(); // 最新的在前
    return filter === 'all' ? list : list.filter((e) => e.event === filter);
  }, [data, filter]);

  // 从当前数据动态生成筛选按钮（去重并按名称排序）
  const eventNames = useMemo(() => {
    const names = new Set((data ?? []).map((e) => e.event));
    return [...names].sort();
  }, [data]);

  return (
    <div className="page">
      {error ? <AlertBanner kind="error" message={describeError(error)} onRetry={refresh} retrying={refreshing} /> : null}

      <div className="toolbar">
        <div className="toolbar-stats">
          <span className="chip chip-action">共 {events.length} 条记录</span>
          <span className="muted">审计事件来自决策、传感器上报与人工审批</span>
        </div>
        <div className="toolbar-actions">
          <button type="button" className="btn btn-ghost" onClick={refresh} disabled={refreshing}>
            <RefreshCw size={16} aria-hidden /> {refreshing ? '刷新中…' : '刷新'}
          </button>
        </div>
      </div>

      <div className="filter-row">
        <button
          type="button"
          className={`chip chip-filter ${filter === 'all' ? 'chip-active' : ''}`}
          onClick={() => setFilter('all')}
        >
          全部
        </button>
        {eventNames.map((name) => (
          <button
            key={name}
            type="button"
            className={`chip chip-filter ${filter === name ? 'chip-active' : ''}`}
            onClick={() => setFilter(name)}
          >
            {translateAuditEvent(name)}
          </button>
        ))}
      </div>

      {/* 三态渲染：首载 Loading / 空态 / 事件列表；payload 可点击展开完整内容 */}
      {loading && !data ? (
        <Loading label="正在获取审计记录…" />
      ) : events.length === 0 ? (
        <EmptyState icon={<HistoryIcon size={36} />} title="暂无审计记录" hint="后端产生决策、传感器上报或审批操作后，记录会出现在这里。" />
      ) : (
        <ul className="history-list">
          {events.map((e: AuditEvent, i) => (
            <li key={`${e.timestamp}-${i}`} className="history-item">
              <div className="history-main">
                <span className={`badge ${badgeClass(e.event)}`}>{translateAuditEvent(e.event)}</span>
                <details className="payload">
                  <summary className="payload-summary">{formatAuditPayload(e.payload)}</summary>
                  <pre className="payload-full">{formatAuditPayload(e.payload, 4000)}</pre>
                </details>
              </div>
              <time className="muted history-time">{formatTime(e.timestamp)}</time>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
