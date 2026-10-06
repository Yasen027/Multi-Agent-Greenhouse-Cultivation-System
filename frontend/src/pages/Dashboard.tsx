/** 总览页：KPI、实时传感器网格与最新决策面板（4 秒轮询） */

import { useEffect, useState } from 'react';
import { AlertBanner } from '../components/AlertBanner';
import { DecisionPanel } from '../components/DecisionPanel';
import { SensorCard } from '../components/SensorCard';
import { Loading } from '../components/StatusViews';
import { usePolling } from '../hooks/usePolling';
import { api, describeError } from '../services/api';
import { DEFAULT_THRESHOLDS, type NumericSensorKey, type Thresholds } from '../types';
import { formatTime } from '../utils/format';

interface Metric {
  key: NumericSensorKey;
  name: string;
  icon: string;
  unit: string;
  digits: number;
  /** 正常范围来源 */
  rangeOf?: (t: Thresholds) => { min: number; max: number };
}

const METRICS: Metric[] = [
  { key: 'temperature', name: '空气温度', icon: '🌡️', unit: '°C', digits: 1, rangeOf: (t) => t.temperature },
  { key: 'humidity', name: '空气湿度', icon: '💧', unit: '%', digits: 1, rangeOf: (t) => t.humidity },
  { key: 'soil_moisture', name: '土壤湿度', icon: '🪴', unit: '%', digits: 1, rangeOf: () => ({ min: 30, max: 70 }) },
  { key: 'ph', name: '土壤 pH', icon: '🧪', unit: '', digits: 2, rangeOf: (t) => t.ph },
  { key: 'ec', name: '电导率 EC', icon: '⚡', unit: ' mS/cm', digits: 2 },
  { key: 'light', name: '光照强度', icon: '☀️', unit: ' lx', digits: 0 },
  { key: 'co2', name: 'CO₂ 浓度', icon: '🌫️', unit: ' ppm', digits: 0 },
];

export function Dashboard() {
  const { data, error, loading, refreshing, lastUpdated, refresh } = usePolling(api.getDashboardSummary);
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getThresholds()
      .then((t) => {
        if (!cancelled) setThresholds(t);
      })
      .catch(() => {
        /* 阈值获取失败时使用默认值，不打扰用户 */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runAgents = async () => {
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

  const sensor = data?.sensor ?? null;
  const decision = data?.decision ?? null;
  const pending = data?.pending_hitl ?? 0;

  return (
    <div className="page">
      {error ? <AlertBanner kind="error" message={describeError(error)} onRetry={refresh} retrying={refreshing} /> : null}
      {runError ? <AlertBanner kind="error" title="运行决策失败" message={runError} onRetry={runAgents} /> : null}

      {loading && !data ? (
        <Loading label="正在连接后端…" />
      ) : (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <p className="kpi-label">🤖 智能体</p>
              <p className="kpi-value">{data?.agents ?? 0}</p>
              <p className="kpi-sub">已注册运行</p>
            </div>
            <a className={`kpi-card kpi-link ${pending > 0 ? 'kpi-alert' : ''}`} href="#/hitl">
              <p className="kpi-label">⏳ 待审批</p>
              <p className="kpi-value">{pending}</p>
              <p className="kpi-sub">{pending > 0 ? '需要人工介入，点击处理 →' : '无积压请求'}</p>
            </a>
            <div className="kpi-card">
              <p className="kpi-label">📡 传感器设备</p>
              <p className="kpi-value kpi-value-sm">{sensor ? sensor.device_id : '未连接'}</p>
              <p className="kpi-sub">{sensor ? `最后上报 ${formatTime(sensor.timestamp)}` : '等待边缘设备上报'}</p>
            </div>
            <div className="kpi-card">
              <p className="kpi-label">🧭 最新决策</p>
              <p className={`kpi-value kpi-value-sm ${decision?.human_intervention ? 'text-warning' : 'text-ok'}`}>
                {decision ? (decision.human_intervention ? '需人工介入' : '自动执行') : '暂无'}
              </p>
              <p className="kpi-sub">{decision?.id ? `#${String(decision.id).slice(0, 8)}` : '等待首轮决策'}</p>
            </div>
          </div>

          <section className="section">
            <header className="section-head">
              <h2 className="section-title">实时传感器</h2>
              <p className="muted">
                {lastUpdated ? `更新于 ${formatTime(new Date(lastUpdated).toISOString())}` : ''}
                {refreshing ? ' · 刷新中…' : ''}
              </p>
            </header>
            {sensor ? (
              <div className="card-grid sensor-grid">
                {METRICS.map((m) => (
                  <SensorCard
                    key={m.key}
                    name={m.name}
                    icon={m.icon}
                    value={sensor[m.key]}
                    unit={m.unit}
                    digits={m.digits}
                    min={m.rangeOf ? m.rangeOf(thresholds).min : undefined}
                    max={m.rangeOf ? m.rangeOf(thresholds).max : undefined}
                    note={`设备 ${sensor.device_id}`}
                  />
                ))}
              </div>
            ) : (
              <p className="muted">暂无传感器数据：边缘设备尚未上报，或后端为模拟空状态。</p>
            )}
          </section>

          <DecisionPanel decision={decision} onRun={runAgents} running={running} />
        </>
      )}
    </div>
  );
}
