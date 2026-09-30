# 作物识别 Agent

触发：首次启动、reason=new_season、reason=crop_change、每168小时定期校验、其他Agent报告mismatch、或force=true。

接口：POST /api/agents/crop-identification/run；GET /api/agents/crop-identification/status。

普通 POST /api/agents/run 不会每次重复识别，只在首次、到期或档案不匹配时触发。