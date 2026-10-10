/**
 * 与后端 FastAPI 接口对齐的统一类型定义。
 * 后端参考：backend/app/schemas.py、backend/app/api/*.py
 */

/** 传感器读数（POST /api/sensors/readings、GET /api/sensors/latest） */
export interface SensorReading {
  device_id: string;
  /** ISO 8601 时间字符串 */
  timestamp: string;
  /** 空气温度 ℃ */
  temperature: number;
  /** 空气湿度 % */
  humidity: number;
  /** 土壤湿度 % */
  soil_moisture: number;
  /** 土壤酸碱度 */
  ph: number;
  /** 电导率 mS/cm */
  ec: number;
  /** 光照强度 lx */
  light: number;
  /** 二氧化碳浓度 ppm */
  co2: number;
  /** 作物图像 URL（可选） */
  image_url: string | null;
}

/** 执行器命令（决策融合输出，ActuatorCommand） */
export interface ActuatorCommand {
  actuator: string;
  action: string;
  value?: number | string | boolean | null;
  reason?: string;
}

/** 决策分发结果（dispatch_commands 返回值） */
export interface DispatchResult {
  status:
    | 'published'
    | 'blocked_by_safety'
    | 'blocked_unsafe_actuator'
    | 'circuit_open'
    | 'skipped_no_broker'
    | 'simulated_local'
    | 'nothing_to_dispatch'
    | 'dispatch_failed'
    | string;
  count?: number;
  topic?: string;
  error?: string;
}

/** 一次完整决策（POST /api/agents/run、GET /api/decisions） */
export interface Decision {
  id?: string;
  /** 融合后的执行器命令列表 */
  priority_actions: ActuatorCommand[];
  /** true 表示被安全层拦截，需人工介入 */
  human_intervention: boolean;
  /** 面向农户的自然语言解释 */
  explanation_for_farmer?: string;
  audit?: { agents?: AgentStatus[] };
  dispatch?: DispatchResult | null;
}

/** 单智能体运行结果（GET /api/agents/status） */
export interface AgentStatus {
  agent: string;
  status: string;
  confidence: number;
  findings: string[];
  recommendations: string[];
  risk_level: string;
}

/** 仪表盘汇总（GET /api/dashboard/summary） */
export interface DashboardSummary {
  sensor: SensorReading | null;
  decision: Decision | null;
  /** 待人工审批数量 */
  pending_hitl: number;
  /** 已运行的智能体数量 */
  agents: number;
  digital_twin: DigitalTwinStatus;
  recent_acks: ActuatorAck[];
}

/** 执行器确认回执：设备侧对下发命令的执行结果回传 */
export interface ActuatorAck {
  command_id?: string | null;
  actuator: string;
  action: string;
  status: 'applied' | 'failed' | string;
  timestamp: string;
  error?: string;
}

/** 数字孪生比赛场景（GET /api/digital-twin/scenarios） */
export interface TwinScenario {
  id: string;
  name: string;
  description: string;
}

/** 设备健康问题：传感器/执行器诊断产生的一条具体告警 */
export interface DeviceHealthIssue {
  code: 'sensor_stuck' | 'sensor_offline' | 'out_of_range' | 'actuator_failure' | 'circuit_open' | string;
  severity: 'warning' | 'critical' | string;
  message: string;
  sensor?: string;
  actuator?: string;
  detected_at: string;
}

/** 设备诊断汇总：随数字孪生状态返回，含两侧问题列表、失败计数与熔断状态 */
export interface DeviceDiagnostics {
  status: 'healthy' | 'warning' | 'critical';
  sensor: { status: string; issues: DeviceHealthIssue[]; offline_after_seconds: number };
  actuator: {
    status: string;
    issues: DeviceHealthIssue[];
    consecutive_failures: Record<string, number>;
    circuits: Record<string, boolean>;
    pending_ack_count: number;
    ack_timeout_seconds: number;
  };
}

/** 数字孪生运行状态（GET /api/digital-twin/status）：在线、场景、环境快照与诊断 */
export interface DigitalTwinStatus {
  online: boolean;
  scenario: string | null;
  scenario_name: string;
  cycle?: number;
  actuators: Record<string, string>;
  environment?: Partial<Record<NumericSensorKey, number>>;
  fault: Record<string, unknown> | null;
  updated_at: string | null;
  last_sensor_at: string | null;
  sensor_age_seconds?: number | null;
  diagnostics?: DeviceDiagnostics;
  recent_acks?: ActuatorAck[];
  actuator_state?: Record<string, string>;
}

/** 人工审批请求状态（pending/approved/rejected/resolved，兼容未知值） */
export type HitlStatus = 'pending' | 'approved' | 'rejected' | 'resolved' | string;

/** 人工审批请求（GET /api/hitl/pending） */
export interface HitlRequest {
  id: string;
  /** crop_identification | actuator_command | 其他 */
  type?: string;
  /** 关联的决策 id（可选） */
  decision_id?: string;
  /** 拦截原因 */
  reason?: string;
  /** 需要人工回答的问题（可选） */
  question?: string;
  status: HitlStatus;
  /** 批准决策后，基于最新传感器重新运行得到的结果 */
  revalidation?: Decision;
}

/** 审计事件（GET /api/audit、GET /api/audit/history） */
export interface AuditEvent {
  timestamp: string;
  event: string;
  payload: unknown;
}

/** 健康检查（GET /api/health） */
export interface HealthInfo {
  status: string;
  version: string;
}

/** 传感器阈值配置（GET /api/config/thresholds） */
export interface Thresholds {
  temperature: { min: number; max: number };
  humidity: { min: number; max: number };
  ph: { min: number; max: number };
}

/** 数值型传感器字段（可用于 toFixed 等数值运算） */
export type NumericSensorKey = 'temperature' | 'humidity' | 'soil_moisture' | 'ph' | 'ec' | 'light' | 'co2';

/** 默认阈值（后端不可用或未配置时的兜底） */
export const DEFAULT_THRESHOLDS: Thresholds = {
  temperature: { min: 18, max: 30 },
  humidity: { min: 50, max: 80 },
  ph: { min: 5.5, max: 7.5 },
};
