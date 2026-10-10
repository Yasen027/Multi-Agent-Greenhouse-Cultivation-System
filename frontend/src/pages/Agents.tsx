/** 智能体页：各领域专家智能体的实时状态（4 秒轮询），可手动触发一轮决策 */

import { useState } from 'react';
import { Bot, Play, RefreshCw } from 'lucide-react';
import { AgentCard } from '../components/AgentCard';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState, Loading } from '../components/StatusViews';
import { usePolling } from '../hooks/usePolling';
import { api, describeError } from '../services/api';
import { formatRelative } from '../utils/format';

export function Agents() {
  const { data, error, loading, refreshing, lastUpdated, refresh } = usePolling(api.getAgentsStatus);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  // 汇总统计：正常数量与平均置信度（防御 NaN/缺失值）
  const agents = data ?? [];
  const okCount = agents.filter((a) => a.status === 'ok').length;
  const avgConfidence =
    agents.length > 0 ? Math.round((agents.reduce((sum, a) => sum + (Number(a.confidence) || 0), 0) / agents.length) * 100) : 0;

  // 手动触发一轮完整多智能体决策，完成后立即刷新状态
  const runAll = async () => {
    setRunning(true);
    setRunError(null);
    try {
      await api.runAgents();
      await refresh();
    } catch (err) {
      setRunError(describeError(err));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="page">
      {error ? <AlertBanner kind="error" message={describeError(error)} onRetry={refresh} retrying={refreshing} /> : null}
      {runError ? <AlertBanner kind="error" title="运行决策失败" message={runError} onRetry={runAll} /> : null}

      <div className="toolbar">
        <div className="toolbar-stats">
          <span className="chip chip-action">
            {okCount}/{agents.length} 正常
          </span>
          <span className="chip">平均置信度 {avgConfidence}%</span>
          {lastUpdated ? <span className="muted">更新于 {formatRelative(new Date(lastUpdated).toISOString())}</span> : null}
        </div>
        <div className="toolbar-actions">
          <button type="button" className="btn btn-ghost" onClick={refresh} disabled={refreshing}>
            <RefreshCw size={16} aria-hidden /> {refreshing ? '刷新中…' : '刷新'}
          </button>
          <button type="button" className="btn" onClick={runAll} disabled={running}>
            <Play size={16} aria-hidden /> {running ? '运行中（可能较慢）…' : '运行一轮决策'}
          </button>
        </div>
      </div>

      {/* 三态渲染：首载 Loading / 无数据空态 / 智能体卡片网格 */}
      {loading && !data ? (
        <Loading label="正在获取智能体状态…" />
      ) : agents.length === 0 ? (
        <EmptyState icon={<Bot size={36} />} title="暂无智能体状态" hint="点击“运行一轮决策”或等待后端调度，即可看到各专家智能体的输出。" />
      ) : (
        <div className="card-grid agent-grid">
          {agents.map((a) => (
            <AgentCard key={a.agent} agent={a} />
          ))}
        </div>
      )}
    </div>
  );
}
