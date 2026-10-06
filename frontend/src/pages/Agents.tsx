/** 智能体页：各领域专家智能体的实时状态（4 秒轮询），可手动触发一轮决策 */

import { useState } from 'react';
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

  const agents = data ?? [];
  const okCount = agents.filter((a) => a.status === 'ok').length;
  const avgConfidence =
    agents.length > 0 ? Math.round((agents.reduce((sum, a) => sum + (Number(a.confidence) || 0), 0) / agents.length) * 100) : 0;

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
            {refreshing ? '刷新中…' : '🔄 刷新'}
          </button>
          <button type="button" className="btn" onClick={runAll} disabled={running}>
            {running ? '运行中（可能较慢）…' : '▶ 运行一轮决策'}
          </button>
        </div>
      </div>

      {loading && !data ? (
        <Loading label="正在获取智能体状态…" />
      ) : agents.length === 0 ? (
        <EmptyState icon="🤖" title="暂无智能体状态" hint="点击“运行一轮决策”或等待后端调度，即可看到各专家智能体的输出。" />
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
