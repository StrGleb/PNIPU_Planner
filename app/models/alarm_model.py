import uuid
from dataclasses import dataclass, field
from typing import List
from datetime import datetime

DAY_NAMES = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}
WEEK_ANY = "any"
WEEK_ODD = "odd"
WEEK_EVEN = "even"
WEEK_NAMES = {WEEK_ANY: "Любая", WEEK_ODD: "Нечётная", WEEK_EVEN: "Чётная"}

@dataclass
class Alarm:
    hour: int
    minute: int
    enabled: bool = True
    days: List[int] = field(default_factory = list)
    week_type: str = WEEK_ANY   # "any" | "odd" | "even"
    id: str = field(default_factory = lambda: str(uuid.uuid4()))

    @property
    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def days_label(self) -> str:
        days_str = ", ".join(DAY_NAMES[d] for d in sorted(self.days) if d in DAY_NAMES) if self.days else "Каждый день"
        week_str = WEEK_NAMES.get(self.week_type, "Любая")
        return f"{days_str} · {week_str} нед."
    
    def matches_now(self, now: datetime, is_even_week: bool) -> bool:
        if not self.enabled:
            return False
        if now.hour != self.hour or now.minute != self.minute:
            return False
        if self.week_type == WEEK_ODD and is_even_week:
            return False
        if self.week_type == WEEK_EVEN and not is_even_week:
            return False
        if not self.days:
            return True
        return now.isoweekday() in self.days

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hour": self.hour,
            "minute": self.minute,
            "enabled": self.enabled,
            "days": self.days,
            "week_type": self.week_type,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "Alarm":
        return cls(
            id = d.get("id", str(uuid.uuid4())),
            hour = int(d["hour"]),
            minute = int(d["minute"]),
            enabled = bool(d.get("enabled", True)),
            days = list(d.get("days", [])),
            week_type = d.get("week_type", WEEK_ANY),
        )