/** 单个智能体的运行状态卡片：状态、置信度、风险等级、发现与建议 */

import type { AgentStatus } from '../types';

const RISK_TEXT: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
};

const AGENT_META: Record<string, { label: string; icon: string }> = {
  soil: { label: '土壤专家', icon: '🪴' },
  temperature: { label: '温度专家', icon: '🌡️' },
  humidity: { label: '湿度专家', icon: '💧' },
  pest: { label: '病虫害专家', icon: '🐛' },
  irrigation: { label: '灌溉专家', icon: '🚿' },
  light_co2: { label: '光照/CO₂ 专家', icon: '☀️' },
  crop_stage: { label: '生育期专家', icon: '🌾' },
  crop_identification: { label: '作物识别', icon: '🔍' },
};

export function AgentCard({ agent }: { agent: AgentStatus }) {
  const meta = AGENT_META[agent.agent] ?? { label: agent.agent, icon: '🤖' };
  const statusOk = agent.status === 'ok';
  const statusText = statusOk ? '正常' : agent.status === 'idle' ? '待命' : agent.status || '待命';
  const risk = agent.risk_level ? (RISK_TEXT[agent.risk_level] ?? agent.risk_level) : '—';
  const riskClass = agent.risk_level ? `risk-${String(agent.risk_level).toLowerCase()}` : '';
  const confidencePct = Math.round(Math.min(1, Math.max(0, Number(agent.confidence) || 0)) * 100);

  return (
    <article className="card agent-card">
      <header className="agent-head">
        <span className="agent-icon" aria-hidden="true">
          {meta.icon}
        </span>
        <div className="agent-title">
          <p className="agent-name">{meta.label}</p>
          <p className="agent-id">{agent.agent}</p>
        </div>
        <span className={`status-dot ${statusOk ? 'ok' : 'idle'}`} aria-hidden="true" />
        <span className={`badge ${statusOk ? 'badge-normal' : 'badge-idle'}`}>{statusText}</span>
      </header>

      <div className="agent-stats">
        <div className="stat">
          <p className="stat-label">置信度</p>
          <p className="stat-value">{confidencePct}%</p>
          <div className="meter">
            <div className="meter-fill" style={{ width: `${confidencePct}%` }} />
          </div>
        </div>
        <div className="stat">
          <p className="stat-label">风险等级</p>
          <p className={`stat-value ${riskClass}`}>{risk}</p>
        </div>
      </div>

      <section className="agent-section">
        <p className="agent-section-title">发现</p>
        {agent.findings?.length ? (
          <ul className="chip-list">
            {agent.findings.map((f) => (
              <li key={f} className="chip chip-finding">
                {f}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">无明显异常</p>
        )}
      </section>

      <section className="agent-section">
        <p className="agent-section-title">建议动作</p>
        {agent.recommendations?.length ? (
          <ul className="chip-list">
            {agent.recommendations.map((r) => (
              <li key={r} className="chip chip-action">
                {r}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">无需干预</p>
        )}
      </section>
    </article>
  );
}
