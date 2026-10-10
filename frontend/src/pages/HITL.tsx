/** 人工审批页（HITL）：查看、批准、拒绝待处理请求（4 秒轮询） */

import { useRef, useState } from 'react';
import { Check, CheckCircle2, RefreshCw, X } from 'lucide-react';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState, Loading } from '../components/StatusViews';
import { usePolling } from '../hooks/usePolling';
import { api, describeError } from '../services/api';
import type { HitlRequest } from '../types';
import { translateDecisionText, translateHitlType, translateStatus } from '../utils/i18n';

export function HITL() {
  const { data, error, loading, refreshing, refresh, setData } = usePolling(api.getPendingHitl);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const feedbackTimer = useRef<number | null>(null);

  // 操作反馈横幅：5 秒后自动消失，重复操作时重置计时器
  const showFeedback = (kind: 'success' | 'error', text: string) => {
    setFeedback({ kind, text });
    if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current);
    feedbackTimer.current = window.setTimeout(() => setFeedback(null), 5000);
  };

  // 批准/拒绝请求：成功后乐观移除该项，并按重新校验后的下发状态生成反馈文案
  const act = async (item: HitlRequest, action: 'approve' | 'reject') => {
    setBusyId(item.id);
    try {
      const updated = action === 'approve' ? await api.approveHitl(item.id) : await api.rejectHitl(item.id);
      // 乐观更新：从待审批列表移除已处理项
      setData((prev) => (prev ?? []).filter((x) => x.id !== item.id));
      // 根据 revalidation 的分发状态，补充“已下发/仍拦截/下发失败”等结果说明
      const dispatch = updated.revalidation?.dispatch?.status;
      const approvalResult = dispatch === 'published' || dispatch === 'simulated_local'
        ? '，已根据最新传感器重新决策并下发命令'
        : dispatch === 'blocked_by_safety'
          ? '，最新状态仍需人工复核，旧命令未执行'
          : dispatch === 'dispatch_failed'
            ? '，重新决策完成但命令下发失败'
            : '';
      const actionText = action === 'approve'
        ? item.type === 'device_failure' ? '解除熔断并处理' : '批准'
        : '拒绝';
      showFeedback('success', `已${actionText}请求 #${item.id.slice(0, 8)}（状态：${translateStatus(updated.status)}）${approvalResult}`);
      void refresh();
    } catch (err) {
      showFeedback('error', describeError(err));
    } finally {
      setBusyId(null);
    }
  };

  const pending = data ?? [];

  return (
    <div className="page">
      {error ? <AlertBanner kind="error" message={describeError(error)} onRetry={refresh} retrying={refreshing} /> : null}
      {feedback ? <AlertBanner kind={feedback.kind} message={feedback.text} /> : null}

      <div className="toolbar">
        <div className="toolbar-stats">
          <span className="chip chip-action">待审批 {pending.length} 项</span>
          <span className="muted">批准/拒绝操作会写入审计日志</span>
        </div>
        <div className="toolbar-actions">
          <button type="button" className="btn btn-ghost" onClick={refresh} disabled={refreshing}>
            <RefreshCw size={16} aria-hidden /> {refreshing ? '刷新中…' : '刷新'}
          </button>
        </div>
      </div>

      {loading && !data ? (
        <Loading label="正在获取待审批请求…" />
      ) : pending.length === 0 ? (
        <EmptyState icon={<CheckCircle2 size={36} />} title="暂无待审批请求" hint="当安全层拦截决策、作物识别置信度不足或执行器命令被阻断时，请求会出现在这里。" />
      ) : (
        <ul className="hitl-list">
          {pending.map((item) => (
            <li key={item.id} className="card hitl-card">
              <header className="hitl-head">
                <span className={`badge ${item.type ? 'badge-warning' : 'badge-neutral'}`}>
                  {translateHitlType(item.type)}
                </span>
                <span className="mono">#{item.id.slice(0, 8)}</span>
                <span className={`badge ${item.status === 'pending' ? 'badge-warning' : 'badge-neutral'}`}>
                  {translateStatus(item.status)}
                </span>
              </header>

              <div className="hitl-body">
                {item.reason ? (
                  <p className="hitl-row">
                    <span className="hitl-row-label">拦截原因</span>
                    <span>{translateDecisionText(item.reason)}</span>
                  </p>
                ) : null}
                {item.question ? (
                  <p className="hitl-row">
                    <span className="hitl-row-label">需要确认</span>
                    <span className="hitl-question">{item.question}</span>
                  </p>
                ) : null}
                {item.decision_id ? (
                  <p className="hitl-row">
                    <span className="hitl-row-label">关联决策</span>
                    <span className="mono">#{String(item.decision_id).slice(0, 8)}</span>
                  </p>
                ) : null}
              </div>

              <footer className="hitl-actions">
                <button
                  type="button"
                  className="btn btn-approve"
                  disabled={busyId !== null}
                  onClick={() => void act(item, 'approve')}
                >
                  <Check size={16} aria-hidden /> {busyId === item.id ? '处理中…' : item.type === 'device_failure' ? '解除熔断' : '批准'}
                </button>
                <button
                  type="button"
                  className="btn btn-reject"
                  disabled={busyId !== null}
                  onClick={() => void act(item, 'reject')}
                >
                  <X size={16} aria-hidden /> {busyId === item.id ? '处理中…' : '拒绝'}
                </button>
              </footer>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
