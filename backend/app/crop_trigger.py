"""作物档案触发管理器。

按固定时间间隔触发作物识别/档案更新流程，
避免在每个传感器周期都重复调用识别服务。
"""

from datetime import datetime, timedelta


class CropTriggerManager:
    """管理作物识别触发时机与运行状态。"""

    def __init__(self, interval_hours=168):
        # 触发间隔（小时），默认 168 小时（一周）
        self.interval_hours = interval_hours
        # 上次运行时间，初始为空表示尚未运行过
        self.last_run = None
        # 最近一次触发的原因
        self.reason = 'startup'
        # 当前识别的作物
        self.current_crop = None
        # 生长季编号
        self.season = 1

    def due(self):
        """判断是否已到触发时间：从未运行或距上次运行超过间隔。"""
        if self.last_run is None:
            return True
        elapsed = datetime.utcnow() - self.last_run
        return elapsed >= timedelta(hours=self.interval_hours)

    def should_run(self, reason=None, force=False, mismatch=False):
        """综合判断是否应触发：强制、档案不匹配、特殊原因或已到期。"""
        special_reasons = ('startup', 'new_season', 'crop_change')
        return force or mismatch or reason in special_reasons or self.due()

    def mark(self, reason):
        """记录本次运行时间与原因。"""
        self.last_run = datetime.utcnow()
        self.reason = reason

    def status(self):
        """返回当前触发管理器状态快照。"""
        return {
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'interval_hours': self.interval_hours,
            'current_crop': self.current_crop,
            'season': self.season,
            'last_reason': self.reason,
            'due': self.due(),
        }


# 全局单例，供 API 层复用
manager = CropTriggerManager()
