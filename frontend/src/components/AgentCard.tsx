/** 单个智能体的运行状态卡片：状态、置信度、风险等级、发现与建议 */

import type { AgentStatus } from '../types';
import { translateFinding, translateRecommendation } from '../utils/i18n';
import { Bot, Bug, Droplets, Lightbulb, ScanSearch, Sprout, Thermometer, Waves, type LucideIcon } from 'lucide-react';

// 风险等级 → 中文文案（未知等级回退为原始英文）
const RISK_TEXT: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
};

// 智能体 key → 中文名与图标；未知 key 回退到 Bot 图标并直接展示原始 id
const AGENT_META: Record<string, { label: string; icon: LucideIcon }> = {
  soil: { label: '土壤专家', icon: Sprout },
  temperature: { label: '温度专家', icon: Thermometer },
  humidity: { label: '湿度专家', icon: Droplets },
  pest: { label: '病虫害专家', icon: Bug },
  irrigation: { label: '灌溉专家', icon: Waves },
  light_co2: { label: '光照/CO₂ 专家', icon: Lightbulb },
  crop_stage: { label: '生育期专家', icon: Sprout },
  crop_identification: { label: '作物识别', icon: ScanSearch },
};

export function AgentCard({ agent }: { agent: AgentStatus }) {
  // 未知智能体兜底：展示原始 id 与通用机器人图标
  const meta = AGENT_META[agent.agent] ?? { label: agent.agent, icon: Bot };
  const AgentIcon = meta.icon;
  const statusOk = agent.status === 'ok';
  // 状态文案：ok → 正常，idle → 待命，其余状态原样显示
  const statusText = statusOk ? '正常' : agent.status === 'idle' ? '待命' : agent.status || '待命';
  const risk = agent.risk_level ? (RISK_TEXT[agent.risk_level] ?? agent.risk_level) : '—';
  const riskClass = agent.risk_level ? `risk-${String(agent.risk_level).toLowerCase()}` : '';
  // 置信度夹在 0–1 后转百分比并取整，防御缺失值、NaN 与越界
  const confidencePct = Math.round(Math.min(1, Math.max(0, Number(agent.confidence) || 0)) * 100);

  return (
    <article className="card agent-card">
      <header className="agent-head">
        <span className="agent-icon" aria-hidden="true">
          <AgentIcon size={20} aria-hidden />
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
                {translateFinding(f)}
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
                {translateRecommendation(r)}
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
