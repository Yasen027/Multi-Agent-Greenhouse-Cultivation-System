/** 单个传感器指标卡片：数值、量程进度条与状态标识 */

export type SensorLevel = 'normal' | 'low' | 'high' | 'unknown';

interface SensorCardProps {
  /** 指标名称，如“空气温度” */
  name: string;
  /** 图标（emoji） */
  icon: string;
  value: number | null;
  unit: string;
  /** 正常范围（可选）；缺省时不判断状态 */
  min?: number;
  max?: number;
  /** 小数位数 */
  digits?: number;
  /** 说明文字，如设备来源 */
  note?: string;
}

export function levelOf(value: number | null, min?: number, max?: number): SensorLevel {
  if (value === null || min === undefined || max === undefined || Number.isNaN(value)) return 'unknown';
  if (value < min) return 'low';
  if (value > max) return 'high';
  return 'normal';
}

const LEVEL_TEXT: Record<SensorLevel, string> = {
  normal: '正常',
  low: '偏低',
  high: '偏高',
  unknown: '未知',
};

export function SensorCard({ name, icon, value, unit, min, max, digits = 1, note }: SensorCardProps) {
  const level = levelOf(value, min, max);
  const hasRange = min !== undefined && max !== undefined && min < max;

  // 量程进度条位置（夹在 0–100%）
  let ratio = 50;
  if (hasRange && value !== null && Number.isFinite(value)) {
    ratio = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  }

  return (
    <article className={`card sensor-card sensor-${level}`} title={note}>
      <header className="sensor-head">
        <span className="sensor-icon" aria-hidden="true">
          {icon}
        </span>
        <span className="sensor-name">{name}</span>
        <span className={`badge badge-${level}`}>{LEVEL_TEXT[level]}</span>
      </header>
      <p className="sensor-value">
        {value === null ? '—' : value.toFixed(digits)}
        <span className="sensor-unit">{unit}</span>
      </p>
      {hasRange ? (
        <div className="range">
          <div className="range-bar">
            <div className={`range-fill range-${level}`} style={{ width: `${ratio}%` }} />
            <div className="range-dot" style={{ left: `${ratio}%` }} aria-hidden="true" />
          </div>
          <div className="range-labels">
            <span>{min}</span>
            <span>{max}</span>
          </div>
        </div>
      ) : (
        <p className="sensor-note">{note ?? '仅展示实时读数'}</p>
      )}
    </article>
  );
}
