import uuid
from dataclasses import dataclass, field
from typing import List
from datetime import datetime

DAY_NAMES = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}


@dataclass
class Alarm:
    hour: int
    minute: int
    enabled: bool = True
    days: List[int] = field(default_factory = list)
    id: str = field(default_factory = lambda: str(uuid.uuid4()))

    @property
    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def days_label(self) -> str:
        """Читаемое перечисление дней: 'Пн, Ср, Пт' или 'Каждый день'."""
        if not self.days:
            return "Каждый день"
        return ", ".join(DAY_NAMES[d] for d in sorted(self.days) if d in DAY_NAMES)
    
    def matches_now(self, now: datetime) -> bool:
        """True если будильник должен сработать прямо сейчас."""
        if not self.enabled:
            return False
        if now.hour != self.hour or now.minute != self.minute:
            return False
        if not self.days:
            return True # каждый день
        iso_weekday = now.isoweekday() # 1=Пн … 7=Вс
        return iso_weekday in self.days

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hour": self.hour,
            "minute": self.minute,
            "enabled": self.enabled,
            "days": self.days,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Alarm":
        return cls(
            id = d.get("id", str(uuid.uuid4())),
            hour = int(d["hour"]),
            minute = int(d["minute"]),
            enabled = bool(d.get("enabled", True)),
            days = list(d.get("days", [])),
        )