/** 前端展示文案：中文优先，配置/接口 key 保留在括号中便于排查。 */

// 发现（findings）文案映射：后端英文 key → 中文描述
const FINDING_TEXT: Record<string, string> = {
  'temperature high': '温度偏高',
  'temperature warning': '温度预警',
  'temperature emergency': '温度紧急异常',
  'temperature severely deviated': '温度严重偏离目标',
  'temperature within known thresholds': '温度处于已知阈值范围内',
  'humidity high': '湿度偏高',
  'humidity low': '湿度偏低',
  'humidity critical and disease risk': '湿度严重异常，存在病害风险',
  'humidity within known thresholds': '湿度处于已知阈值范围内',
  'soil dry': '土壤偏干',
  'soil moisture low': '土壤湿度偏低',
  'soil moisture below target': '土壤湿度低于目标值',
  'soil moisture high': '土壤湿度偏高',
  'soil saturation risk': '存在土壤过饱和风险',
  'soil moisture within known thresholds': '土壤湿度处于已知阈值范围内',
  'soil within known thresholds': '土壤指标处于已知阈值范围内',
  'pH critical': 'pH 严重异常',
  'pH severely deviated': 'pH 严重偏离目标',
  'pH warning': 'pH 预警',
  'EC critical': 'EC 严重异常',
  'EC high': 'EC 偏高',
  'fungal risk': '存在真菌病害风险',
  'valve fault': '阀门故障',
  'light low': '光照偏低',
  'excessive light with heat': '光照过强且伴随高温',
  'co2 low': 'CO₂ 偏低',
  'light and co2 within known thresholds': '光照和 CO₂ 处于已知阈值范围内',
};

// 建议动作（recommendations）文案映射：中文为主，key 保留在括号中便于排查
const RECOMMENDATION_TEXT: Record<string, string> = {
  ventilation_on: '开启通风（ventilation_on）',
  irrigation_on: '开启灌溉（irrigation_on）',
  heating_on: '开启加热（heating_on）',
  grow_light_on: '开启补光（grow_light_on）',
  co2_on: '补充 CO₂（co2_on）',
  notify_pest_agent: '通知 pest Agent（notify_pest_agent）',
  update_stage_thresholds: '更新生育期阈值（update_stage_thresholds）',
};

// 事件流文案映射（时间线/审计描述用）
const EVENT_TEXT: Record<string, string> = {
  decision: '决策（decision）',
  sensor_reading: '传感器上报（sensor_reading）',
  actuator_command: '执行器命令（actuator_command）',
  actuator_command_blocked: '执行器命令拦截（actuator_command_blocked）',
  actuator_ack: '执行器确认（actuator_ack）',
  actuator_circuit_reset: '执行器熔断已解除（actuator_circuit_reset）',
  sensor_diagnostic_changed: '传感器诊断变化（sensor_diagnostic_changed）',
  sensor_reading_rejected: '传感器读数拒绝（sensor_reading_rejected）',
  crop_identification: '作物识别（crop_identification）',
  crop_identification_pending: '作物识别待确认（crop_identification_pending）',
  crop_identification_confirmed: '作物识别已确认（crop_identification_confirmed）',
  crop_profile_analysis: '作物档案分析（crop_profile_analysis）',
  hitl_pending: '人工审批待处理（hitl_pending）',
  hitl_approved: '人工审批已通过（hitl_approved）',
  hitl_revalidated: '人工审批已重新校验（hitl_revalidated）',
  hitl_rejected: '人工审批已拒绝（hitl_rejected）',
  hitl_resolved: '人工审批已处理（hitl_resolved）',
};

// 审计事件类型 → 中文（筛选按钮与徽章用）
const AUDIT_EVENT_TEXT: Record<string, string> = {
  decision: '决策',
  decision_failed: '决策失败',
  sensor_reading: '传感器上报',
  actuator_ack: '执行器确认',
  actuator_command: '执行器命令',
  actuator_command_blocked: '执行器命令拦截',
  actuator_command_failed: '执行器命令失败',
  actuator_circuit_reset: '执行器熔断已解除',
  sensor_diagnostic_changed: '传感器诊断变化',
  sensor_reading_rejected: '传感器读数拒绝',
  digital_twin_scenario_selected: '数字孪生场景切换',
  digital_twin_status: '数字孪生状态',
  mqtt_payload_rejected: '消息载荷拒绝',
  crop_identification: '作物识别',
  crop_identification_pending: '作物识别待确认',
  crop_identification_confirmed: '作物识别已确认',
  crop_profile_analysis: '作物档案分析',
  hitl_pending: '人工审批待处理',
  hitl_approved: '人工审批已通过',
  hitl_revalidated: '人工审批已重新校验',
  hitl_rejected: '人工审批已拒绝',
  hitl_resolved: '人工审批已处理',
};

// 审计 payload 字段名 → 中文（递归格式化 payload 时使用）
const AUDIT_FIELD_TEXT: Record<string, string> = {
  id: '编号',
  decision_id: '决策编号',
  command_id: '命令编号',
  device_id: '设备编号',
  timestamp: '时间',
  temperature: '空气温度',
  humidity: '空气湿度',
  soil_moisture: '土壤湿度',
  ph: '土壤酸碱度',
  ec: '电导率',
  light: '光照强度',
  co2: '二氧化碳浓度',
  image_url: '图像地址',
  priority_actions: '优先动作',
  human_intervention: '人工介入',
  explanation_for_farmer: '决策说明',
  audit: '分析记录',
  agents: '智能体分析',
  agent: '智能体',
  status: '状态',
  confidence: '置信度',
  findings: '分析发现',
  recommendations: '处理建议',
  risk_level: '风险等级',
  dispatch: '下发结果',
  actuator: '执行器',
  action: '动作',
  value: '设定值',
  reason: '原因',
  reasons: '原因列表',
  error: '错误信息',
  count: '数量',
  topic: '消息主题',
  command: '命令',
  alert: '告警',
  alerts: '告警列表',
  message: '消息',
  type: '类型',
  requires_hitl: '需要人工审批',
  scenario: '运行场景',
  scenario_name: '场景名称',
  transport: '传输方式',
  online: '在线状态',
  cycle: '运行周期',
  actuators: '执行器状态',
  environment: '环境数据',
  fault: '故障信息',
  updated_at: '更新时间',
  last_sensor_at: '最近采集时间',
  sensor_age_seconds: '数据时延秒数',
  recent_acks: '最近确认记录',
  actuator_state: '执行器状态',
  trigger: '触发原因',
  result: '识别结果',
  profile: '作物档案',
  crop: '作物',
  stage: '生育期',
  method: '识别方式',
  required: '是否需要',
  question: '确认问题',
  question_to_human: '人工确认问题',
  incident_active: '事件是否有效',
};

// 审计常见枚举值 → 中文（含执行器动作、审批状态、场景作物等）
const AUDIT_VALUE_TEXT: Record<string, string> = {
  on: '开启',
  off: '关闭',
  applied: '已执行',
  failed: '失败',
  timeout: '确认超时',
  pending: '待审批',
  approved: '已批准',
  rejected: '已拒绝',
  resolved: '已处理',
  published: '已发布',
  blocked_by_safety: '被安全规则拦截',
  blocked_unsafe_actuator: '不安全执行器已拦截',
  circuit_open: '执行器已熔断',
  skipped_no_broker: '消息服务未连接，已跳过',
  simulated_local: '本地模拟执行',
  nothing_to_dispatch: '无需下发命令',
  dispatch_failed: '命令下发失败',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  unknown: '未知',
  local: '本地',
  normal: '正常场景',
  tomato: '番茄',
  lettuce: '生菜',
  strawberry: '草莓',
  cucumber: '黄瓜',
  pepper: '辣椒',
};

// 审批状态 → 中文
const STATUS_TEXT: Record<string, string> = {
  pending: '待审批（pending）',
  approved: '已批准（approved）',
  rejected: '已拒绝（rejected）',
  resolved: '已处理（resolved）',
};

// 审批类型 → 中文
const TYPE_TEXT: Record<string, string> = {
  crop_identification: '作物识别确认（crop_identification）',
  actuator_command: '执行器命令审批（actuator_command）',
  decision: '决策审批（decision）',
  device_failure: '设备连续失败处理（device_failure）',
};

// 智能体名称 → 中文
const AGENT_TEXT: Record<string, string> = {
  soil: '土壤',
  temperature: '温度',
  humidity: '湿度',
  pest: '病虫害',
  irrigation: '灌溉',
  light_co2: '光照/CO₂',
  crop_stage: '生育期',
  crop_identification: '作物识别',
};

// 执行器名称 → 中文
const ACTUATOR_TEXT: Record<string, string> = {
  ventilation: '通风设备',
  irrigation: '灌溉设备',
  heating: '加热设备',
  mister: '喷雾设备',
  grow_light: '补光灯',
  shade: '遮阳设备',
  co2: 'CO₂ 发生器',
  fan: '循环风机',
  pesticide: '农药喷洒设备',
};

/** 发现文案翻译：优先查表；“stage=xxx” 动态拼接生育期；未命中则原样返回 */
export function translateFinding(value: string): string {
  if (FINDING_TEXT[value]) return FINDING_TEXT[value];
  const stage = value.match(/^stage=(.+)$/);
  if (stage) return `生育期：${stage[1] === 'unknown' ? '未知' : stage[1]}（${value}）`;
  return value;
}

/** 建议动作翻译：查表，未命中原样返回 */
export function translateRecommendation(value: string): string {
  return RECOMMENDATION_TEXT[value] ?? value;
}

/** 事件流文案翻译：查表，未命中原样返回 */
export function translateEvent(value: string): string {
  return EVENT_TEXT[value] ?? value;
}

/** 审计事件翻译：查表，未命中的未知事件统一显示“其他审计事件” */
export function translateAuditEvent(value: string): string {
  return AUDIT_EVENT_TEXT[value] ?? '其他审计事件';
}

// 递归把审计 payload 值转成中文单行文本：空值→“无”，布尔→是/否，数组/对象逐项翻译，特殊 key 走专用映射
function auditValue(value: unknown, key = ''): string {
  if (value === null || value === undefined || value === '') return '无';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.length ? value.map((item) => auditValue(item, key)).join('、') : '无';
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([field, item]) => `${AUDIT_FIELD_TEXT[field] ?? '扩展信息'}：${auditValue(item, field)}`)
      .join('；');
  }
  if (key === 'actuator') return translateActuator(String(value));
  if (key === 'action') return String(value) === 'on' ? '开启' : String(value) === 'off' ? '关闭' : '未知动作';
  if (key === 'agent') return AGENT_TEXT[String(value)] ?? '其他智能体';
  if (key === 'reason' || key === 'reasons' || key === 'findings') return translateDecisionText(String(value));
  return AUDIT_VALUE_TEXT[String(value)] ?? String(value);
}

/** 审计 payload → 中文摘要文本（超长自动截断） */
export function formatAuditPayload(payload: unknown, max = 240): string {
  const text = auditValue(payload);
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

/** 审批状态翻译（与 translateHitlType 配合用于 HITL 卡片） */
export function translateStatus(value: string): string {
  return STATUS_TEXT[value] ?? value;
}

/** 审批类型翻译：未知类型原样展示，未传类型时兜底“人工审批” */
export function translateHitlType(value: string | undefined): string {
  return value ? TYPE_TEXT[value] ?? value : '人工审批';
}

/** 动作翻译：on/off → 开启/关闭（保留英文 key 便于排查） */
export function translateAction(value: string): string {
  if (value === 'on') return '开启（on）';
  if (value === 'off') return '关闭（off）';
  return value;
}

/** 执行器翻译：查表，未命中原样返回 */
export function translateActuator(value: string): string {
  return ACTUATOR_TEXT[value] ?? value;
}

/** 决策说明翻译：整句精确匹配 → 分句处理（低置信度智能体/执行器安全等）→ 回退 finding 表 → 原样返回 */
export function translateDecisionText(value: string): string {
  if (AGENT_TEXT[value]) return AGENT_TEXT[value];
  if (value === 'Routine environmental optimization') return '日常环境优化';
  const clauses = value.split(/;\s*/).map((clause) => {
    if (clause.startsWith('low confidence agents:')) {
      const agents = clause
        .slice('low confidence agents:'.length)
        .trim()
        .split(/\s*,\s*/)
        .map((agent) => AGENT_TEXT[agent] ?? agent)
        .join('、');
      return `智能体置信度较低：${agents}`;
    }
    if (clause === 'crop identification requires human confirmation') return '作物识别需要人工确认';
    if (clause === 'extreme temperature') return '温度异常';
    if (clause === 'temperature condition requires human review') return '温度条件需要人工复核';
    if (clause === 'unsafe pH') return 'pH 不安全';
    if (clause === 'chemical pesticide') return '涉及化学农药';
    if (clause === 'command requires human approval') return '命令需要人工审批';
    const actuator = clause.match(/^unregistered or unsafe actuator:\s*(.+)$/);
    if (actuator) return `未注册或不安全的执行器：${actuator[1]}`;
    return FINDING_TEXT[clause] ?? clause;
  });
  return clauses.join('；');
}
