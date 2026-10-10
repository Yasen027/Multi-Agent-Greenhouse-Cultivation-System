/** 比赛版首页：实时态势、温室分区、智能体决策、趋势预测与人工审批。 */

import { useEffect, useMemo, useState, type ComponentType } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  CloudSun,
  Cpu,
  Droplets,
  FlaskConical,
  Gauge,
  Leaf,
  Lightbulb,
  PanelRightOpen,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
  Sprout,
  SunMedium,
  Thermometer,
  Trophy,
  Waves,
  Wind,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import { AlertBanner } from '../components/AlertBanner';
import { levelOf, type SensorLevel } from '../components/SensorCard';
import { Loading } from '../components/StatusViews';
import { usePolling } from '../hooks/usePolling';
import { api, describeError } from '../services/api';
import {
  DEFAULT_THRESHOLDS,
  type AgentStatus,
  type AuditEvent,
  type DeviceDiagnostics,
  type HitlRequest,
  type NumericSensorKey,
  type SensorReading,
  type Thresholds,
  type TwinScenario,
} from '../types';
import { formatRelative, formatTime } from '../utils/format';
import {
  translateAction,
  translateActuator,
  translateDecisionText,
  translateEvent,
  translateFinding,
  translateHitlType,
} from '../utils/i18n';

type Icon = ComponentType<{ size?: number; strokeWidth?: number; 'aria-hidden'?: boolean }>;

/** 指标卡片配置：key 对应传感器字段，rangeOf 从阈值取正常范围（缺省则不参与等级判断） */
interface Metric {
  key: NumericSensorKey;
  name: string;
  icon: Icon;
  unit: string;
  digits: number;
  rangeOf?: (thresholds: Thresholds) => { min: number; max: number };
}

// 首页 7 个指标：前 4 个渲染主指标卡，其余进次级指标行；土壤湿度无阈值配置，使用固定 30–70 范围
const METRICS: Metric[] = [
  { key: 'temperature', name: '空气温度', icon: Thermometer, unit: '°C', digits: 1, rangeOf: (t) => t.temperature },
  { key: 'humidity', name: '空气湿度', icon: Droplets, unit: '%', digits: 1, rangeOf: (t) => t.humidity },
  { key: 'soil_moisture', name: '土壤湿度', icon: Sprout, unit: '%', digits: 1, rangeOf: () => ({ min: 30, max: 70 }) },
  { key: 'co2', name: 'CO₂ 浓度', icon: CloudSun, unit: ' ppm', digits: 0 },
  { key: 'ph', name: '土壤 pH', icon: FlaskConical, unit: '', digits: 2, rangeOf: (t) => t.ph },
  { key: 'ec', name: '电导率 EC', icon: Zap, unit: ' mS/cm', digits: 2 },
  { key: 'light', name: '光照强度', icon: SunMedium, unit: ' lx', digits: 0 },
];

// 指标等级 → 文案（unknown 显示“等待数据”，与 SensorCard 的“未知”区分）
const LEVEL_TEXT: Record<SensorLevel, string> = {
  normal: '正常',
  low: '偏低',
  high: '偏高',
  unknown: '等待数据',
};

// 比赛讲解模式步骤：id 对应页面锚点，按步骤滚动定位，最后一步自动打开审批抽屉
const TOUR = [
  { id: 'live-metrics', title: '实时环境态势', body: '先看关键指标、采集设备与数据新鲜度。' },
  { id: 'approval-drawer', title: '人工审批闭环', body: '极端条件进入 HITL，现场可直接批准或拒绝。' },
  { id: 'zone-map', title: '温室分区与设备', body: '三类控制分区汇总环境风险和本轮执行器命令。' },
  { id: 'agent-timeline', title: '多智能体决策链', body: '专家智能体依次分析，融合层统一生成安全动作。' },
  { id: 'trend-forecast', title: '趋势与预测', body: '审计数据形成短时趋势，并给出下一时段预测。' },
];

// 取指标正常范围（rangeOf 未配置时返回 undefined，该指标不做等级判断）
function metricRange(metric: Metric, thresholds: Thresholds) {
  return metric.rangeOf?.(thresholds);
}

/** 从审计事件流提取最近 12 组有效传感器读数（温度/土壤湿度必须为有限数值）；无历史数据时回退到最新读数 */
function getSensorHistory(events: AuditEvent[], latest: SensorReading | null): SensorReading[] {
  const readings = events
    .filter((event) => event.event === 'sensor_reading' && event.payload && typeof event.payload === 'object')
    .map((event) => event.payload as SensorReading)
    .filter((reading) => Number.isFinite(reading.temperature) && Number.isFinite(reading.soil_moisture))
    .slice(-12);
  if (readings.length === 0 && latest) return [latest];
  return readings;
}

// 短时线性外推：以最近 4 组数据的斜率预测下一时段值（仅用于温度与土壤湿度）
function predictNext(readings: SensorReading[], key: 'temperature' | 'soil_moisture'): number | null {
  if (readings.length < 2) return null;
  const recent = readings.slice(-4);
  const slope = (recent.at(-1)![key] - recent[0][key]) / (recent.length - 1);
  return recent.at(-1)![key] + slope;
}

type ChartKey = 'temperature' | 'soil_moisture';
type ChartDomain = { min: number; max: number };

// 图表 Y 轴范围：数据最值上下各留 10% 余量（温度至少 ±1、土壤湿度至少 ±5）；无数据时用默认范围
function chartDomain(readings: SensorReading[], key: ChartKey): ChartDomain {
  if (readings.length === 0) return key === 'temperature' ? { min: 0, max: 40 } : { min: 0, max: 100 };
  const values = readings.map((reading) => reading[key]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = Math.max((max - min) * 0.1, key === 'temperature' ? 1 : 5);
  return { min: Math.floor(min - padding), max: Math.ceil(max + padding) };
}

// 把读数序列映射为 SVG polyline 坐标点（560×195 视口内硬编码的绘图区坐标）
function chartPoints(readings: SensorReading[], key: ChartKey, domain: ChartDomain): string {
  if (readings.length === 0) return '';
  const spread = Math.max(domain.max - domain.min, 1);
  return readings
    .map((value, index) => {
      const x = readings.length === 1 ? 280 : 54 + (index / (readings.length - 1)) * 452;
      const y = 142 - ((value[key] - domain.min) / spread) * 112;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

// 图表悬浮提示用的短时间格式（HH:MM）
function chartTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

// 生成 Y 轴整数刻度序列
function integerTicks(domain: ChartDomain): number[] {
  return Array.from({ length: domain.max - domain.min + 1 }, (_, index) => domain.min + index);
}

// 按值域跨度选择刻度步长（≤16→1、≤40→5、其余→10），避免标签过密
function showTickLabel(value: number, domain: ChartDomain): boolean {
  const span = domain.max - domain.min;
  const step = span <= 16 ? 1 : span <= 40 ? 5 : 10;
  return value === domain.min || value === domain.max || value % step === 0;
}

// 时间线事件的中文描述：覆盖常见事件类型，其余回退到 i18n 事件表
function auditDescription(event: AuditEvent): string {
  if (event.event === 'sensor_reading') return '边缘采集器完成环境数据上报';
  if (event.event === 'decision') return '融合智能体生成新一轮控制策略';
  if (event.event === 'hitl_pending') return '安全规则拦截命令，等待人工复核';
  if (event.event === 'hitl_approved') return '人工审批通过，已使用最新传感器完成重新决策与安全校验';
  if (event.event === 'hitl_revalidated') return '最新状态复核完成，安全结果决定下发或再次拦截';
  if (event.event === 'hitl_rejected') return '人工拒绝高风险控制命令';
  if (event.event.startsWith('actuator_command')) return '执行器命令已进入安全分发流程';
  return translateEvent(event.event);
}

// 智能体 key → “xx智能体”文案（如 soil → 土壤智能体）
function agentLabel(agent: AgentStatus): string {
  return `${translateDecisionText(agent.agent)}智能体`;
}

// 数字孪生故障注入模式的描述文案（超时/固定值/异常值/执行器故障）
function twinFaultText(fault: Record<string, unknown> | null | undefined): string {
  if (!fault) return '';
  const sensor = {
    temperature: '温度',
    humidity: '空气湿度',
    soil_moisture: '土壤湿度',
    ph: 'pH',
    ec: 'EC',
    light: '光照',
    co2: 'CO₂',
  }[String(fault.sensor)] ?? String(fault.sensor);
  if (fault.mode === 'timeout') return '传感器数据超时';
  if (fault.mode === 'fixed') return `${sensor}固定值`;
  if (fault.mode === 'abnormal') return `${sensor}异常值`;
  const [actuator, mode] = Object.entries(fault)[0] ?? [];
  return actuator ? `${translateActuator(actuator)} ${mode === 'timeout' ? '无响应' : '故障'}` : '已注入故障';
}

// 汇总传感器与执行器两侧的诊断问题文本；无诊断数据时提示等待
function diagnosticText(diagnostics: DeviceDiagnostics | undefined): string {
  if (!diagnostics) return '等待诊断数据';
  const issues = [...diagnostics.sensor.issues, ...diagnostics.actuator.issues];
  return issues.length ? issues.map((issue) => issue.message).join('；') : '未检出异常';
}

export function Dashboard() {
  // 三路独立轮询：总览、审计事件（最近 80 条）、待审批列表，互不阻塞
  const summary = usePolling(api.getDashboardSummary);
  const audit = usePolling(() => api.getAuditHistory(80));
  const hitl = usePolling(api.getPendingHitl);
  // 阈值与各类 UI 状态：决策运行中、操作错误、审批抽屉、审批忙碌、演示步骤、场景与设备下发中
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [scenarios, setScenarios] = useState<TwinScenario[]>([]);
  const [scenarioBusy, setScenarioBusy] = useState(false);
  const [deviceBusy, setDeviceBusy] = useState<string | null>(null);

  // 挂载时一次性加载阈值与比赛场景；失败静默处理，保留默认值
  useEffect(() => {
    let cancelled = false;
    api.getThresholds().then((value) => !cancelled && setThresholds(value)).catch(() => undefined);
    api.getTwinScenarios().then((value) => !cancelled && setScenarios(value)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // 演示模式：滚动定位到当前步骤锚点，走到最后一步时自动打开审批抽屉
  useEffect(() => {
    if (tourStep === null) return;
    if (tourStep === TOUR.length - 1) setDrawerOpen(true);
    document.getElementById(TOUR[tourStep].id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [tourStep]);

  // 审批抽屉打开时监听 Esc 键关闭
  useEffect(() => {
    if (!drawerOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && setDrawerOpen(false);
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [drawerOpen]);

  // 运行一轮完整决策链，结束后并行刷新总览/审计/审批三路数据
  const runAgents = async () => {
    setRunning(true);
    setRunError(null);
    try {
      await api.runAgents();
      await Promise.all([summary.refresh(), audit.refresh(), hitl.refresh()]);
    } catch (error) {
      setRunError(describeError(error));
    } finally {
      setRunning(false);
    }
  };

  // 切换数字孪生比赛场景；延迟 500ms 刷新，等后端完成场景切换
  const selectScenario = async (scenario: string) => {
    setScenarioBusy(true);
    setRunError(null);
    try {
      await api.selectTwinScenario(scenario);
      window.setTimeout(() => void summary.refresh(), 500);
    } catch (error) {
      setRunError(describeError(error));
    } finally {
      setScenarioBusy(false);
    }
  };

  // 手动切换执行器开/关（比赛演示）：按孪生当前状态取反，下发后延迟刷新
  const toggleActuator = async (actuator: string) => {
    setDeviceBusy(actuator);
    setRunError(null);
    const current = summary.data?.digital_twin?.actuators?.[actuator];
    try {
      await api.sendActuatorCommand({ actuator, action: current === 'on' ? 'off' : 'on', reason: 'competition_demo' });
      window.setTimeout(() => void summary.refresh(), 500);
    } catch (error) {
      setRunError(describeError(error));
    } finally {
      setDeviceBusy(null);
    }
  };

  // 批准/拒绝审批项：成功后乐观地从待审批列表移除，并刷新总览与审计
  const actOnRequest = async (item: HitlRequest, action: 'approve' | 'reject') => {
    setBusyId(item.id);
    try {
      if (action === 'approve') await api.approveHitl(item.id);
      else await api.rejectHitl(item.id);
      hitl.setData((previous) => (previous ?? []).filter((request) => request.id !== item.id));
      await Promise.all([summary.refresh(), audit.refresh()]);
    } catch (error) {
      setRunError(describeError(error));
    } finally {
      setBusyId(null);
    }
  };

  // 派生数据：传感器/决策/待审批/审计读数、趋势计算、执行器动作映射与孪生状态
  const sensor = summary.data?.sensor ?? null;
  const decision = summary.data?.decision ?? null;
  const pending = hitl.data ?? [];
  const events = audit.data ?? [];
  const readings = useMemo(() => getSensorHistory(events, sensor), [events, sensor]);
  const temperatureDomain = chartDomain(readings, 'temperature');
  const soilDomain = chartDomain(readings, 'soil_moisture');
  const tempPrediction = predictNext(readings, 'temperature');
  const soilPrediction = predictNext(readings, 'soil_moisture');
  const actuatorActions = useMemo(
    () => Object.fromEntries((decision?.priority_actions ?? []).map((command) => [command.actuator, command.action])),
    [decision],
  );
  const agents = decision?.audit?.agents ?? [];
  const twin = summary.data?.digital_twin;
  const latestAck = summary.data?.recent_acks?.[0];

  const metricLevel = (metric: Metric) => {
    const range = metricRange(metric, thresholds);
    return levelOf(sensor?.[metric.key] ?? null, range?.min, range?.max);
  };

  // 三个控制分区的汇总：区名、关键读数、告警等级与设备列表；气候区看“高”，根域区看“高/低”
  const zones = [
    {
      name: 'A 区 · 气候调控',
      meta: sensor ? `${sensor.temperature.toFixed(1)}°C · ${sensor.humidity.toFixed(0)}% RH` : '等待环境数据',
      icon: Wind,
      level: [metricLevel(METRICS[0]), metricLevel(METRICS[1])].includes('high') ? 'warning' : 'normal',
      devices: ['ventilation', 'mister', 'shade'],
    },
    {
      name: 'B 区 · 根域水肥',
      meta: sensor ? `含水 ${sensor.soil_moisture.toFixed(0)}% · pH ${sensor.ph.toFixed(1)}` : '等待土壤数据',
      icon: Waves,
      level: [metricLevel(METRICS[2]), metricLevel(METRICS[4])].some((level) => level === 'high' || level === 'low')
        ? 'warning'
        : 'normal',
      devices: ['irrigation', 'co2'],
    },
    {
      name: 'C 区 · 光能管理',
      meta: sensor ? `${sensor.light.toFixed(0)} lx · CO₂ ${sensor.co2.toFixed(0)} ppm` : '等待光照数据',
      icon: SunMedium,
      level: sensor ? 'normal' : 'unknown',
      devices: ['grow_light', 'heating', 'fan'],
    },
  ];

  const tourClass = (step: number) => (tourStep === step ? 'demo-focus' : '');

  return (
    <div className="page dashboard-page">
      {(summary.error || audit.error) && (
        <AlertBanner
          kind="error"
          message={describeError(summary.error ?? audit.error)}
          onRetry={() => void Promise.all([summary.refresh(), audit.refresh()])}
          retrying={summary.refreshing || audit.refreshing}
        />
      )}
      {runError ? <AlertBanner kind="error" title="操作失败" message={runError} onRetry={() => setRunError(null)} /> : null}

      <div className="dashboard-heading">
        <div>
          <div className="eyebrow"><Activity size={14} aria-hidden /> LIVE OPERATION</div>
          <h2>智能温室实时总览</h2>
          <p>传感器、专家智能体与安全审批在一个闭环内协同运行。</p>
        </div>
        <div className="heading-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setTourStep(0)}>
            <Trophy size={17} aria-hidden /> 比赛讲解模式
          </button>
          <button type="button" className="btn" onClick={() => void runAgents()} disabled={running}>
            {running ? <span className="spinner spinner-inline" aria-hidden /> : <Play size={17} fill="currentColor" aria-hidden />}
            {running ? '智能体运行中…' : '运行一轮决策'}
          </button>
        </div>
      </div>

      {/* 首载显示 Loading；此后即使后台刷新失败也保留旧数据继续渲染 */}
      {summary.loading && !summary.data ? (
        <Loading label="正在连接温室控制系统…" />
      ) : (
        <>
          {/* 数字孪生比赛控制台：场景选择、故障注入状态、执行器手动开关与闭环流程 */}
          <section className="card twin-console">
            <header className="section-head section-head-tight">
              <div>
                <p className="section-kicker">DIGITAL TWIN / COMPETITION</p>
                <h3 className="section-title">数字孪生比赛场景</h3>
              </div>
              <span className={`connection-pill ${twin?.online ? 'is-online' : 'is-offline'}`}>
                <Radio size={14} aria-hidden />
                {twin?.online ? `运行中 · 第 ${twin.cycle ?? 0} 周期` : '等待 MQTT 孪生服务'}
              </span>
            </header>

            <div className="twin-toolbar">
              <label>
                <span>比赛场景</span>
                <select
                  value={twin?.scenario ?? ''}
                  disabled={scenarioBusy || scenarios.length === 0}
                  onChange={(event) => void selectScenario(event.target.value)}
                >
                  <option value="" disabled>请选择场景</option>
                  {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}
                </select>
              </label>
              <p>{scenarios.find((scenario) => scenario.id === twin?.scenario)?.description ?? '选择场景后，传感器数据会经 MQTT 自动触发多智能体决策。'}</p>
              <div className="twin-health-status">
                {twin?.fault ? (
                  <span className="twin-fault"><AlertTriangle size={15} /> 已注入：{twinFaultText(twin.fault)}</span>
                ) : (
                  <span className="twin-healthy"><CheckCircle2 size={15} /> 故障注入：无</span>
                )}
                <span className={twin?.diagnostics?.status === 'healthy' ? 'twin-healthy' : 'twin-diagnosed'}>
                  {twin?.diagnostics?.status === 'healthy' ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
                  系统诊断：{diagnosticText(twin?.diagnostics)}
                </span>
              </div>
            </div>

            <div className="twin-devices">
              {['fan', 'irrigation', 'heating', 'grow_light', 'co2'].map((actuator) => {
                const on = twin?.actuators?.[actuator] === 'on';
                return (
                  <button
                    type="button"
                    key={actuator}
                    className={`twin-device ${on ? 'is-on' : ''}`}
                    disabled={!twin?.online || deviceBusy !== null}
                    onClick={() => void toggleActuator(actuator)}
                  >
                    <span><i />{translateActuator(actuator)}</span>
                    <strong>{deviceBusy === actuator ? '下发中…' : on ? '运行' : '待机'}</strong>
                  </button>
                );
              })}
            </div>

            <div className="twin-flow" aria-label="数字孪生闭环">
              <span>场景</span><ChevronRight size={14} /><span>MQTT 传感器</span><ChevronRight size={14} />
              <span>多智能体决策</span><ChevronRight size={14} /><span>控制命令</span><ChevronRight size={14} /><span>下一周期</span>
              {latestAck ? <small className={`ack-${latestAck.status}`}>最新 ACK：{translateActuator(latestAck.actuator)} {latestAck.status === 'applied' ? '已执行' : '失败'}</small> : null}
            </div>
          </section>

          <section id="live-metrics" className={`dashboard-section ${tourClass(0)}`}>
            <header className="section-head section-head-tight">
              <div>
                <p className="section-kicker">01 / REALTIME</p>
                <h3 className="section-title">实时指标与连接状态</h3>
              </div>
              <div className={`connection-pill ${sensor ? 'is-online' : 'is-offline'}`}>
                <Radio size={14} aria-hidden />
                {sensor ? `${sensor.device_id} · ${formatRelative(sensor.timestamp)}` : '边缘设备未连接'}
              </div>
            </header>

            {/* 主指标 4 宫格：温度 / 湿度 / 土壤湿度 / CO₂ */}
            <div className="metric-grid">
              {METRICS.slice(0, 4).map((metric) => {
                const MetricIcon = metric.icon;
                const value = sensor?.[metric.key] ?? null;
                const level = metricLevel(metric);
                return (
                  <article key={metric.key} className={`metric-card metric-${level}`}>
                    <div className="metric-card-head">
                      <span className="metric-icon"><MetricIcon size={19} aria-hidden /></span>
                      <span>{metric.name}</span>
                      <i className={`status-indicator status-${level}`} aria-label={LEVEL_TEXT[level]} />
                    </div>
                    <strong className="metric-reading">
                      {value === null ? '—' : value.toFixed(metric.digits)}<small>{metric.unit}</small>
                    </strong>
                    <span className="metric-caption">{LEVEL_TEXT[level]} · 实时采集</span>
                  </article>
                );
              })}
            </div>

            <div className="secondary-metrics">
              {METRICS.slice(4).map((metric) => {
                const MetricIcon = metric.icon;
                const value = sensor?.[metric.key] ?? null;
                return (
                  <span key={metric.key}>
                    <MetricIcon size={15} aria-hidden />
                    {metric.name}<strong>{value === null ? '—' : `${value.toFixed(metric.digits)}${metric.unit}`}</strong>
                  </span>
                );
              })}
              <span><Cpu size={15} aria-hidden /> 活跃智能体<strong>{summary.data?.agents ?? 0}</strong></span>
            </div>
          </section>

          <section id="approval-drawer" className={`approval-entry ${tourClass(1)}`}>
            <div>
              <span className="approval-icon"><ShieldCheck size={22} aria-hidden /></span>
              <div><strong>人工审批安全闭环</strong><p>高风险决策不会直接下发，由现场人员完成最终确认。</p></div>
            </div>
            <button type="button" className={`btn ${pending.length ? 'btn-warning' : 'btn-ghost'}`} onClick={() => setDrawerOpen(true)}>
              <PanelRightOpen size={17} aria-hidden /> 打开审批台
              {pending.length ? <span className="button-count">{pending.length}</span> : null}
            </button>
          </section>

          {/* 左右分栏：分区设备面板 + 决策时间线 */}
          <div className="dashboard-split">
            <section id="zone-map" className={`card dashboard-section zone-panel ${tourClass(2)}`}>
              <header className="section-head section-head-tight">
                <div>
                  <p className="section-kicker">02 / ZONES</p>
                  <h3 className="section-title">温室分区与设备状态</h3>
                </div>
                <a className="text-link" href="#/map">查看地图 <ChevronRight size={15} aria-hidden /></a>
              </header>

              <div className="greenhouse-map-mini" aria-label="温室三个控制分区">
                <div className="greenhouse-roof"><Leaf size={22} aria-hidden /><span>GREENHOUSE · GH-01</span></div>
                <div className="zone-grid">
                  {zones.map((zone) => {
                    const ZoneIcon = zone.icon;
                    return (
                      <article key={zone.name} className={`zone-card zone-${zone.level}`}>
                        <div className="zone-title">
                          <ZoneIcon size={18} aria-hidden />
                          <strong>{zone.name}</strong>
                          <span>{zone.level === 'warning' ? '关注' : zone.level === 'normal' ? '稳定' : '离线'}</span>
                        </div>
                        <p>{zone.meta}</p>
                        <div className="device-row">
                          {zone.devices.map((device) => {
                            const action = actuatorActions[device];
                            return (
                              <span key={device} className={`device-state device-${action ?? 'idle'}`}>
                                <i />{translateActuator(device)} · {action ? translateAction(action).split('（')[0] : '待机'}
                              </span>
                            );
                          })}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </div>
            </section>

            <section id="agent-timeline" className={`card dashboard-section decision-timeline-panel ${tourClass(3)}`}>
              <header className="section-head section-head-tight">
                <div>
                  <p className="section-kicker">03 / AGENTS</p>
                  <h3 className="section-title">多智能体决策时间线</h3>
                </div>
                <span className={`badge ${decision?.human_intervention ? 'badge-warning' : 'badge-normal'}`}>
                  {decision ? (decision.human_intervention ? '人工复核' : '自动执行') : '等待决策'}
                </span>
              </header>

              <ol className="decision-timeline">
                {agents.length > 0 ? (
                  <>
                    {agents.slice(0, 4).map((agent) => (
                      <li key={agent.agent}>
                        <span className="timeline-icon"><Bot size={15} aria-hidden /></span>
                        <div>
                          <strong>{agentLabel(agent)}</strong>
                          <p>{agent.findings?.length ? agent.findings.slice(0, 2).map(translateFinding).join('、') : '未发现明显异常'}</p>
                          <small>置信度 {Math.round((agent.confidence || 0) * 100)}% · {agent.risk_level === 'high' ? '高风险' : agent.risk_level === 'medium' ? '中风险' : '低风险'}</small>
                        </div>
                      </li>
                    ))}
                    <li className="timeline-final">
                      <span className="timeline-icon"><Sparkles size={15} aria-hidden /></span>
                      <div>
                        <strong>融合决策完成</strong>
                        <p>{decision?.explanation_for_farmer ? translateDecisionText(decision.explanation_for_farmer) : '已汇总各专家智能体建议'}</p>
                        <div className="action-chips">
                          {(decision?.priority_actions ?? []).slice(0, 3).map((command, index) => (
                            <span key={`${command.actuator}-${index}`}>{translateActuator(command.actuator)} · {translateAction(command.action).split('（')[0]}</span>
                          ))}
                        </div>
                      </div>
                    </li>
                  </>
                ) : events.length > 0 ? (
                  [...events].reverse().slice(0, 5).map((event, index) => (
                    <li key={`${event.timestamp}-${index}`}>
                      <span className="timeline-icon"><Clock3 size={15} aria-hidden /></span>
                      <div>
                        <strong>{translateEvent(event.event)}</strong>
                        <p>{auditDescription(event)}</p>
                        <small>{formatRelative(event.timestamp)}</small>
                      </div>
                    </li>
                  ))
                ) : (
                  <li>
                    <span className="timeline-icon"><Clock3 size={15} aria-hidden /></span>
                    <div><strong>等待第一轮决策</strong><p>运行智能体后将在此展示完整决策链。</p></div>
                  </li>
                )}
              </ol>
            </section>
          </div>

          {/* 趋势图：SVG 双轴折线（温度/土壤湿度）+ 下一时段预测卡 */}
          <section id="trend-forecast" className={`card dashboard-section trend-panel ${tourClass(4)}`}>
            <header className="section-head section-head-tight">
              <div>
                <p className="section-kicker">04 / FORECAST</p>
                <h3 className="section-title">环境趋势与预测结果</h3>
              </div>
              <span className="muted">基于最近 {readings.length} 组审计读数</span>
            </header>

            <div className="trend-layout">
              <div className="chart-wrap">
                <div className="chart-legend">
                  <span><i className="legend-line line-temp" />空气温度</span>
                  <span><i className="legend-line line-soil" />土壤湿度</span>
                </div>
                <svg viewBox="0 0 560 195" className="trend-chart" role="img" aria-label="温度和土壤湿度历史趋势">
                  {[0, 1 / 3, 2 / 3, 1].map((ratio) => {
                    const y = 30 + ratio * 112;
                    return <line key={ratio} x1="54" y1={y} x2="506" y2={y} className="chart-grid-line" />;
                  })}
                  <line x1="54" y1="30" x2="54" y2="142" className="chart-axis-line" />
                  <line x1="506" y1="30" x2="506" y2="142" className="chart-axis-line" />
                  <line x1="54" y1="142" x2="506" y2="142" className="chart-axis-line" />
                  {readings.length > 0 ? integerTicks(temperatureDomain).map((value) => {
                    const y = 142 - ((value - temperatureDomain.min) / (temperatureDomain.max - temperatureDomain.min)) * 112;
                    return (
                      <g key={`温度-${value}`}>
                        <line x1="50" y1={y} x2="54" y2={y} className="chart-minor-tick chart-axis-temp" />
                        {showTickLabel(value, temperatureDomain) ? <text x="46" y={y + 3} textAnchor="end" className="chart-axis-text chart-axis-temp">{value}°</text> : null}
                      </g>
                    );
                  }) : null}
                  {readings.length > 0 ? integerTicks(soilDomain).map((value) => {
                    const y = 142 - ((value - soilDomain.min) / (soilDomain.max - soilDomain.min)) * 112;
                    return (
                      <g key={`湿度-${value}`}>
                        <line x1="506" y1={y} x2="510" y2={y} className="chart-minor-tick chart-axis-soil" />
                        {showTickLabel(value, soilDomain) ? <text x="514" y={y + 3} textAnchor="start" className="chart-axis-text chart-axis-soil">{value}%</text> : null}
                      </g>
                    );
                  }) : null}
                  {readings.map((reading, index) => {
                    const x = readings.length === 1 ? 280 : 54 + (index / (readings.length - 1)) * 452;
                    return (
                      <g key={reading.timestamp}>
                        <title>第 {index + 1} 组，采样时间 {chartTime(reading.timestamp)}</title>
                        <line x1={x} y1="142" x2={x} y2="146" className="chart-minor-tick" />
                        <text x={x} y="158" textAnchor="middle" className="chart-axis-text">{index + 1}</text>
                      </g>
                    );
                  })}
                  <text x="280" y="179" textAnchor="middle" className="chart-axis-title">采样序号（每小格 1 组）</text>
                  {readings.length > 0 ? (
                    <>
                      <polyline points={chartPoints(readings, 'temperature', temperatureDomain)} className="chart-line chart-line-temp" />
                      <polyline points={chartPoints(readings, 'soil_moisture', soilDomain)} className="chart-line chart-line-soil" />
                    </>
                  ) : null}
                </svg>
                {readings.length < 2 ? <p className="chart-empty">继续接收数据后将自动生成趋势线</p> : null}
              </div>

              <div className="forecast-cards">
                <article>
                  <span className="forecast-icon"><Thermometer size={18} aria-hidden /></span>
                  <div><small>下一时段温度预测</small><strong>{tempPrediction === null ? '数据积累中' : `${tempPrediction.toFixed(1)}°C`}</strong></div>
                  <span className={tempPrediction !== null && tempPrediction > thresholds.temperature.max ? 'forecast-warning' : 'forecast-ok'}>
                    {tempPrediction !== null && tempPrediction > thresholds.temperature.max ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
                    {tempPrediction !== null && tempPrediction > thresholds.temperature.max ? '可能超阈' : '风险可控'}
                  </span>
                </article>
                <article>
                  <span className="forecast-icon"><Droplets size={18} aria-hidden /></span>
                  <div><small>下一时段土壤湿度</small><strong>{soilPrediction === null ? '数据积累中' : `${soilPrediction.toFixed(1)}%`}</strong></div>
                  <span className={soilPrediction !== null && soilPrediction < 30 ? 'forecast-warning' : 'forecast-ok'}>
                    {soilPrediction !== null && soilPrediction < 30 ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
                    {soilPrediction !== null && soilPrediction < 30 ? '灌溉关注' : '水分稳定'}
                  </span>
                </article>
                <div className="forecast-note"><Lightbulb size={16} aria-hidden />预测仅基于短时线性趋势，用于比赛演示与辅助判断，不替代安全规则。</div>
              </div>
            </div>
          </section>

        </>
      )}

      {/* 右侧审批抽屉：遮罩点击关闭，列表内直接批准/拒绝 */}
      {drawerOpen ? (
        <div className="drawer-layer" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setDrawerOpen(false)}>
          <aside className="approval-drawer" role="dialog" aria-modal="true" aria-labelledby="approval-title">
            <header className="drawer-head">
              <div><p className="section-kicker">HUMAN IN THE LOOP</p><h3 id="approval-title">人工审批控制台</h3></div>
              <button type="button" className="icon-button" onClick={() => setDrawerOpen(false)} aria-label="关闭审批抽屉"><X size={20} /></button>
            </header>
            <div className="drawer-summary">
              <ShieldCheck size={19} aria-hidden />
              <span><strong>{pending.length}</strong> 项待处理</span>
              <small>操作将写入审计日志</small>
            </div>
            <div className="drawer-body">
              {hitl.loading && !hitl.data ? <Loading label="正在获取审批请求…" /> : null}
              {!hitl.loading && pending.length === 0 ? (
                <div className="drawer-empty"><CheckCircle2 size={34} /><strong>当前没有待审批请求</strong><p>系统处于安全自动运行状态。</p></div>
              ) : null}
              {pending.map((item) => (
                <article key={item.id} className="approval-card">
                  <header><span className="badge badge-warning">{translateHitlType(item.type)}</span><code>#{item.id.slice(0, 8)}</code></header>
                  <div className="approval-reason"><AlertTriangle size={17} aria-hidden /><p><small>拦截原因</small><strong>{translateDecisionText(item.reason ?? '命令需要人工审批')}</strong></p></div>
                  {item.question ? <p className="approval-question">{item.question}</p> : null}
                  <footer>
                    <button type="button" className="btn btn-approve" disabled={busyId !== null} onClick={() => void actOnRequest(item, 'approve')}><Check size={16} />{item.type === 'device_failure' ? '解除熔断' : '批准执行'}</button>
                    <button type="button" className="btn btn-reject" disabled={busyId !== null} onClick={() => void actOnRequest(item, 'reject')}><XCircle size={16} />拒绝命令</button>
                  </footer>
                </article>
              ))}
            </div>
            <a href="#/hitl" className="drawer-footer-link" onClick={() => setDrawerOpen(false)}>进入完整审批页面 <ChevronRight size={15} /></a>
          </aside>
        </div>
      ) : null}

      {/* 比赛讲解模式浮层：步骤进度 + 下一步/完成按钮 */}
      {tourStep !== null ? (
        <div className="demo-guide" role="status">
          <span className="demo-step">{tourStep + 1} / {TOUR.length}</span>
          <div><strong>{TOUR[tourStep].title}</strong><p>{TOUR[tourStep].body}</p></div>
          <button type="button" className="icon-button demo-close" onClick={() => { setTourStep(null); setDrawerOpen(false); }} aria-label="退出讲解"><X size={17} /></button>
          <button
            type="button"
            className="btn btn-small"
            onClick={() => {
              if (tourStep === TOUR.length - 1) {
                setTourStep(null);
                setDrawerOpen(false);
              } else setTourStep(tourStep + 1);
            }}
          >
            {tourStep === TOUR.length - 1 ? '完成讲解' : '下一步'} <ChevronRight size={15} />
          </button>
        </div>
      ) : null}
    </div>
  );
}
