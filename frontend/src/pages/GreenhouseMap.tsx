/** 温室地图页：SVG 布局展示分区、传感器点位与执行器状态（4 秒轮询） */

import { useEffect, useMemo, useState } from 'react';
import { AlertBanner } from '../components/AlertBanner';
import { levelOf, type SensorLevel } from '../components/SensorCard';
import { Loading } from '../components/StatusViews';
import { usePolling } from '../hooks/usePolling';
import { api, describeError } from '../services/api';
import { DEFAULT_THRESHOLDS, type NumericSensorKey, type Thresholds } from '../types';
import { formatTime } from '../utils/format';

const LEVEL_COLOR: Record<SensorLevel, string> = {
  normal: '#2e7d4f',
  low: '#d97706',
  high: '#c0392b',
  unknown: '#94a3b8',
};

const LEVEL_TEXT: Record<SensorLevel, string> = {
  normal: '正常',
  low: '偏低',
  high: '偏高',
  unknown: '未知',
};

interface Spot {
  key: NumericSensorKey;
  label: string;
  x: number;
  y: number;
  unit: string;
  digits: number;
}

const SENSOR_SPOTS: Spot[] = [
  { key: 'light', label: '光照', x: 150, y: 175, unit: 'lx', digits: 0 },
  { key: 'temperature', label: '温度', x: 270, y: 190, unit: '°C', digits: 1 },
  { key: 'humidity', label: '湿度', x: 430, y: 190, unit: '%', digits: 1 },
  { key: 'co2', label: 'CO₂', x: 650, y: 175, unit: 'ppm', digits: 0 },
  { key: 'ph', label: 'pH', x: 270, y: 330, unit: '', digits: 2 },
  { key: 'soil_moisture', label: '土壤湿度', x: 400, y: 330, unit: '%', digits: 1 },
  { key: 'ec', label: 'EC', x: 540, y: 330, unit: 'mS/cm', digits: 2 },
];

interface ActuatorSpot {
  key: string;
  label: string;
  x: number;
  y: number;
}

const ACTUATOR_SPOTS: ActuatorSpot[] = [
  { key: 'shade', label: '遮阳', x: 400, y: 62 },
  { key: 'ventilation', label: '通风', x: 600, y: 88 },
  { key: 'grow_light', label: '补光灯', x: 250, y: 92 },
  { key: 'mister', label: '迷雾', x: 520, y: 92 },
  { key: 'heating', label: '加热', x: 110, y: 205 },
  { key: 'fan', label: '风机', x: 690, y: 205 },
  { key: 'co2', label: 'CO₂ 补充', x: 690, y: 300 },
  { key: 'irrigation', label: '灌溉阀', x: 400, y: 446 },
];

const ACTUATOR_LABEL: Record<string, string> = {
  shade: '遮阳网',
  ventilation: '通风口',
  grow_light: '补光灯',
  mister: '迷雾喷淋',
  heating: '加热器',
  fan: '循环风机',
  co2: 'CO₂ 发生器',
  irrigation: '灌溉阀',
};

function stateColor(state: string | undefined): string {
  if (state === 'on') return '#16a34a';
  if (state === 'off') return '#94a3b8';
  return '#e2e8f0';
}

function stateText(state: string | undefined): string {
  if (state === 'on') return '开启';
  if (state === 'off') return '关闭';
  return '未知';
}

function rangeFor(key: NumericSensorKey, t: Thresholds): { min: number; max: number } | undefined {
  if (key === 'temperature') return t.temperature;
  if (key === 'humidity') return t.humidity;
  if (key === 'ph') return t.ph;
  if (key === 'soil_moisture') return { min: 30, max: 70 };
  return undefined;
}

export function GreenhouseMap() {
  const { data, error, loading, refreshing, refresh } = usePolling(api.getDashboardSummary);
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);

  useEffect(() => {
    let cancelled = false;
    api
      .getThresholds()
      .then((t) => {
        if (!cancelled) setThresholds(t);
      })
      .catch(() => {
        /* 使用默认阈值 */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const reading = data?.sensor ?? null;
  const decision = data?.decision ?? null;

  const actuatorActions = useMemo(() => {
    const map: Record<string, string> = {};
    for (const cmd of decision?.priority_actions ?? []) map[cmd.actuator] = cmd.action;
    return map;
  }, [decision]);

  return (
    <div className="page">
      {error ? <AlertBanner kind="error" message={describeError(error)} onRetry={refresh} retrying={refreshing} /> : null}

      <div className="toolbar">
        <div className="toolbar-stats">
          <span className="chip chip-action">{reading ? `设备 ${reading.device_id}` : '传感器未连接'}</span>
          {reading ? <span className="muted">上报于 {formatTime(reading.timestamp)}</span> : null}
        </div>
        <div className="toolbar-actions">
          <button type="button" className="btn btn-ghost" onClick={refresh} disabled={refreshing}>
            {refreshing ? '刷新中…' : '🔄 刷新'}
          </button>
        </div>
      </div>

      {loading && !data ? (
        <Loading label="正在获取温室状态…" />
      ) : (
        <section className="card map-card">
          <svg className="map-svg" viewBox="0 0 800 470" role="img" aria-label="温室平面布局图">
            {/* 天空与地面 */}
            <rect x="0" y="0" width="800" height="470" fill="#f0f7f0" />
            <rect x="0" y="350" width="800" height="120" fill="#e8dcc0" />

            {/* 温室结构 */}
            <polygon points="70,110 400,35 730,110" fill="rgba(190,230,200,0.35)" stroke="#2e7d4f" strokeWidth="3" />
            <rect x="70" y="110" width="660" height="240" fill="rgba(190,230,200,0.25)" stroke="#2e7d4f" strokeWidth="3" />
            <line x1="70" y1="200" x2="730" y2="200" stroke="#2e7d4f" strokeWidth="1" strokeDasharray="6 6" opacity="0.4" />

            {/* 种植区 A/B/C */}
            {[
              { label: 'A 区', x: 100 },
              { label: 'B 区', x: 310 },
              { label: 'C 区', x: 520 },
            ].map((zone) => (
              <g key={zone.label}>
                <rect x={zone.x} y="368" width="180" height="62" rx="8" fill="#9a6b3f" stroke="#7c5230" strokeWidth="2" />
                {[0, 1, 2, 3, 4].map((row) =>
                  [0, 1, 2, 3].map((col) => (
                    <circle
                      key={`${row}-${col}`}
                      cx={zone.x + 24 + col * 44}
                      cy={376 + row * 15}
                      r="5.5"
                      fill="#4d9e4d"
                    />
                  )),
                )}
                <text x={zone.x + 90} y="452" textAnchor="middle" fontSize="13" fontWeight="600" fill="#6b4e2e">
                  {zone.label}
                </text>
              </g>
            ))}

            {/* 传感器点位 */}
            {SENSOR_SPOTS.map((s) => {
              const value = reading ? reading[s.key] : null;
              const range = rangeFor(s.key, thresholds);
              const level = levelOf(value, range?.min, range?.max);
              const color = LEVEL_COLOR[level];
              const display = value === null ? '—' : `${value.toFixed(s.digits)}${s.unit}`;
              return (
                <g key={s.key}>
                  <title>{`${s.label}：${value === null ? '无数据' : `${display}（${LEVEL_TEXT[level]}）`}`}</title>
                  <circle cx={s.x} cy={s.y} r="19" fill="#ffffff" stroke={color} strokeWidth="2.5" />
                  <text x={s.x} y={s.y + 4} textAnchor="middle" fontSize="11.5" fontWeight="700" fill="#1f2937">
                    {display}
                  </text>
                  <text x={s.x} y={s.y + 34} textAnchor="middle" fontSize="11.5" fill={color} fontWeight="600">
                    {s.label} · {LEVEL_TEXT[level]}
                  </text>
                </g>
              );
            })}

            {/* 执行器点位 */}
            {ACTUATOR_SPOTS.map((a) => {
              const state = actuatorActions[a.key];
              return (
                <g key={a.key}>
                  <title>{`${ACTUATOR_LABEL[a.key] ?? a.label}：${stateText(state)}`}</title>
                  <circle cx={a.x} cy={a.y} r="13" fill={stateColor(state)} stroke="#334155" strokeWidth="1.5" />
                  <text x={a.x} y={a.y + 30} textAnchor="middle" fontSize="11.5" fill="#334155" fontWeight="600">
                    {a.label}
                  </text>
                </g>
              );
            })}

            {/* 标题 */}
            <text x="400" y="18" textAnchor="middle" fontSize="15" fontWeight="700" fill="#173b2a">
              温室布局
            </text>
          </svg>

          <div className="map-legend">
            <span className="legend-item">
              <i className="legend-dot" style={{ background: LEVEL_COLOR.normal }} /> 正常
            </span>
            <span className="legend-item">
              <i className="legend-dot" style={{ background: LEVEL_COLOR.low }} /> 偏低
            </span>
            <span className="legend-item">
              <i className="legend-dot" style={{ background: LEVEL_COLOR.high }} /> 偏高
            </span>
            <span className="legend-item">
              <i className="legend-dot" style={{ background: LEVEL_COLOR.unknown }} /> 未知
            </span>
            <span className="legend-sep" />
            <span className="legend-item">
              <i className="legend-dot" style={{ background: '#16a34a' }} /> 执行器开启
            </span>
            <span className="legend-item">
              <i className="legend-dot" style={{ background: '#94a3b8' }} /> 执行器关闭
            </span>
          </div>

          <div className="map-columns">
            <div className="map-overview">
              <h3 className="panel-title">环境概览</h3>
              <ul className="overview-list">
                {SENSOR_SPOTS.map((s) => {
                  const value = reading ? reading[s.key] : null;
                  const range = rangeFor(s.key, thresholds);
                  const level = levelOf(value, range?.min, range?.max);
                  return (
                    <li key={s.key} className="overview-row">
                      <span className="overview-name">{s.label}</span>
                      <span className="overview-value">
                        {value === null ? '—' : `${value.toFixed(s.digits)}${s.unit}`}
                      </span>
                      <span className={`badge badge-${level}`}>{LEVEL_TEXT[level]}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
            <div className="map-overview">
              <h3 className="panel-title">执行器状态</h3>
              <div className="actuator-strip actuator-strip-col">
                {ACTUATOR_SPOTS.map((a) => (
                  <div key={a.key} className={`actuator-chip actuator-${actuatorActions[a.key] ?? 'unknown'}`}>
                    <span className="actuator-name">{ACTUATOR_LABEL[a.key] ?? a.label}</span>
                    <span className="actuator-state">{stateText(actuatorActions[a.key])}</span>
                  </div>
                ))}
              </div>
              <p className="muted map-note">
                执行器状态来自最新融合决策（priority_actions）；未出现于决策中的执行器显示为“未知”。
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
