from datetime import datetime, timedelta


class CropTriggerManager:
    """管理作物识别的周期触发、手动触发和换季触发。"""

    def __init__(self, interval_hours=168):
        self.interval_hours = interval_hours
        self.last_run = None
        self.reason = "startup"
        self.current_crop = None
        self.season = 1

    def due(self):
        """判断是否已达到下一次周期识别时间。"""
        return self.last_run is None or datetime.utcnow() - self.last_run >= timedelta(
            hours=self.interval_hours
        )

    def should_run(self, reason=None, force=False, mismatch=False):
        """根据触发原因决定是否立即执行识别。"""
        return (
            force
            or mismatch
            or reason in ("startup", "new_season", "crop_change")
            or self.due()
        )

    def mark(self, reason):
        """记录本次识别时间和触发原因。"""
        self.last_run = datetime.utcnow()
        self.reason = reason

    def status(self):
        """返回供 API 和前端展示的触发器状态。"""
        return {
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "interval_hours": self.interval_hours,
            "current_crop": self.current_crop,
            "season": self.season,
            "last_reason": self.reason,
            "due": self.due(),
        }


manager = CropTriggerManager()
