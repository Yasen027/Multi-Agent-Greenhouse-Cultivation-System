/** 前端展示文案：中文优先，配置/接口 key 保留在括号中便于排查。 */

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

const RECOMMENDATION_TEXT: Record<string, string> = {
  ventilation_on: '开启通风（ventilation_on）',
  irrigation_on: '开启灌溉（irrigation_on）',
  heating_on: '开启加热（heating_on）',
  grow_light_on: '开启补光（grow_light_on）',
  co2_on: '补充 CO₂（co2_on）',
  notify_pest_agent: '通知 pest Agent（notify_pest_agent）',
  update_stage_thresholds: '更新生育期阈值（update_stage_thresholds）',
};

const EVENT_TEXT: Record<string, string> = {
  decision: '决策（decision）',
  sensor_reading: '传感器上报（sensor_reading）',
  actuator_command: '执行器命令（actuator_command）',
  actuator_command_blocked: '执行器命令拦截（actuator_command_blocked）',
  crop_identification: '作物识别（crop_identification）',
  crop_identification_pending: '作物识别待确认（crop_identification_pending）',
  crop_identification_confirmed: '作物识别已确认（crop_identification_confirmed）',
  crop_profile_analysis: '作物档案分析（crop_profile_analysis）',
  hitl_pending: '人工审批待处理（hitl_pending）',
  hitl_approved: '人工审批已通过（hitl_approved）',
  hitl_rejected: '人工审批已拒绝（hitl_rejected）',
  hitl_resolved: '人工审批已处理（hitl_resolved）',
};

const STATUS_TEXT: Record<string, string> = {
  pending: '待审批（pending）',
  approved: '已批准（approved）',
  rejected: '已拒绝（rejected）',
  resolved: '已处理（resolved）',
};

const TYPE_TEXT: Record<string, string> = {
  crop_identification: '🌾 作物识别确认（crop_identification）',
  actuator_command: '🎛️ 执行器命令审批（actuator_command）',
  decision: '🧭 决策审批（decision）',
};

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

export function translateFinding(value: string): string {
  if (FINDING_TEXT[value]) return FINDING_TEXT[value];
  const stage = value.match(/^stage=(.+)$/);
  if (stage) return `生育期：${stage[1] === 'unknown' ? '未知' : stage[1]}（${value}）`;
  return value;
}

export function translateRecommendation(value: string): string {
  return RECOMMENDATION_TEXT[value] ?? value;
}

export function translateEvent(value: string): string {
  return EVENT_TEXT[value] ?? value;
}

export function translateStatus(value: string): string {
  return STATUS_TEXT[value] ?? value;
}

export function translateHitlType(value: string | undefined): string {
  return value ? TYPE_TEXT[value] ?? value : '人工审批';
}

export function translateAction(value: string): string {
  if (value === 'on') return '开启（on）';
  if (value === 'off') return '关闭（off）';
  return value;
}

export function translateActuator(value: string): string {
  return ACTUATOR_TEXT[value] ?? value;
}

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
