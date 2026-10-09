/** 最新决策面板：展示融合命令、人工介入状态、执行器分发结果与对农户说明 */

import type { Decision, DispatchResult } from '../types';
import { translateAction, translateActuator, translateDecisionText } from '../utils/i18n';
import { EmptyState } from './StatusViews';

const DISPATCH_TEXT: Record<string, string> = {
  published: '已通过 MQTT 下发',
  blocked_by_safety: '安全层拦截，等待人工审批',
  blocked_unsafe_actuator: '包含未授权执行器，已拦截',
  skipped_no_broker: '未配置 MQTT Broker，仅记录（模拟运行）',
  nothing_to_dispatch: '无命令需要下发',
  dispatch_failed: '下发失败',
};

interface DecisionPanelProps {
  decision: Decision | null;
  /** 运行一轮决策 */
  onRun?: () => void;
  running?: boolean;
}

export function DecisionPanel({ decision, onRun, running = false }: DecisionPanelProps) {
  const dispatch: DispatchResult | null | undefined = decision?.dispatch;

  return (
    <section className="card panel">
      <header className="panel-head">
        <h2 className="panel-title">📋 最新决策</h2>
        <div className="panel-actions">
          {decision?.id ? <span className="mono badge badge-neutral">#{String(decision.id).slice(0, 8)}</span> : null}
          {onRun ? (
            <button type="button" className="btn" onClick={onRun} disabled={running}>
              {running ? '决策运行中…' : '▶ 运行一轮决策'}
            </button>
          ) : null}
        </div>
      </header>

      {!decision ? (
        <EmptyState icon="🧭" title="暂无决策记录" hint="点击“运行一轮决策”或等待后端调度，将在此展示融合决策。" />
      ) : (
        <div className="panel-body">
          <div className="decision-flags">
            <span className={`badge ${decision.human_intervention ? 'badge-warning' : 'badge-normal'}`}>
              {decision.human_intervention ? '🛑 已拦截 · 需人工介入' : '✅ 自动执行'}
            </span>
            {dispatch ? (
              <span className={`badge ${dispatch.status === 'published' ? 'badge-normal' : 'badge-neutral'}`}>
                {DISPATCH_TEXT[dispatch.status] ?? dispatch.status}
                {dispatch.count !== undefined ? `（${dispatch.count} 条命令）` : ''}
              </span>
            ) : null}
          </div>

          <p className="farmer-note">
            {decision.explanation_for_farmer ? translateDecisionText(decision.explanation_for_farmer) : '（暂无说明）'}
          </p>

          {decision.priority_actions?.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>执行器</th>
                    <th>动作</th>
                    <th>来源/原因</th>
                  </tr>
                </thead>
                <tbody>
                  {decision.priority_actions.map((cmd, i) => (
                    <tr key={`${cmd.actuator}-${cmd.action}-${i}`}>
                      <td>{translateActuator(cmd.actuator)}</td>
                      <td>
                        <span className={`badge ${cmd.action === 'on' ? 'badge-action-on' : 'badge-action-off'}`}>
                          {translateAction(cmd.action)}
                        </span>
                      </td>
                      <td className="muted">{cmd.reason ? translateDecisionText(cmd.reason) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">本轮无优先动作。</p>
          )}
        </div>
      )}
    </section>
  );
}
