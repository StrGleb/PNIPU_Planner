import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

DAY_NAMES = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}
WEEK_ANY = "any"
WEEK_ODD = "odd"
WEEK_EVEN = "even"
WEEK_NAMES = {
    WEEK_ANY: "Любая",
    WEEK_ODD: "Нечетная",
    WEEK_EVEN: "Четная",
}
SOURCE_MANUAL = "manual"
SOURCE_AUTO_SCHEDULE = "auto_schedule"
SOURCE_WEEK_SCHEDULE = "week_schedule"


@dataclass
class Alarm:
    hour: int
    minute: int
    enabled: bool = True
    days: List[int] = field(default_factory = list)
    week_type: str = WEEK_ANY
    id: str = field(default_factory = lambda: str(uuid.uuid4()))
    source: str = SOURCE_MANUAL
    target_date: str = ""
    lesson_time: str = ""
    route_minutes: int = 0
    rechecked_at: str = ""
    subject: str = ""
    destination: str = ""
    entry_type: str = ""

    @property
    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def days_label(self) -> str:
        if self.target_date:
            if self.source == SOURCE_AUTO_SCHEDULE:
                prefix = "Авто"
            elif self.source == SOURCE_WEEK_SCHEDULE:
                prefix = "Неделя"
            else:
                prefix = "Разово"
            suffix_parts = []
            if self.lesson_time:
                entry_label = "событие" if self.entry_type == "event" else "пара"
                suffix_parts.append(f"{entry_label} {self.lesson_time}")
            if self.subject:
                suffix_parts.append(self.subject)
            suffix = f" · {' · '.join(suffix_parts)}" if suffix_parts else ""
            return f"{prefix} · {self.target_date}{suffix}"

        days_str = ", ".join(DAY_NAMES[day] for day in sorted(self.days) if day in DAY_NAMES)
        if not days_str:
            days_str = "Каждый день"
        week_str = WEEK_NAMES.get(self.week_type, WEEK_NAMES[WEEK_ANY])
        return f"{days_str} · {week_str} нед."

    @property
    def is_auto_schedule(self) -> bool:
        return self.source == SOURCE_AUTO_SCHEDULE

    @property
    def is_one_time_manual(self) -> bool:
        return self.source == SOURCE_MANUAL and bool(self.target_date)

    def matches_now(self, now: datetime, is_even_week: bool) -> bool:
        if not self.enabled:
            return False
        if now.hour != self.hour or now.minute != self.minute:
            return False
        if self.target_date:
            return now.strftime("%d.%m.%Y") == self.target_date
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
            "source": self.source,
            "target_date": self.target_date,
            "lesson_time": self.lesson_time,
            "route_minutes": self.route_minutes,
            "rechecked_at": self.rechecked_at,
            "subject": self.subject,
            "destination": self.destination,
            "entry_type": self.entry_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        return cls(
            id = data.get("id", str(uuid.uuid4())),
            hour = int(data["hour"]),
            minute = int(data["minute"]),
            enabled = bool(data.get("enabled", True)),
            days = list(data.get("days", [])),
            week_type = data.get("week_type", WEEK_ANY),
            source = data.get("source", SOURCE_MANUAL),
            target_date = str(data.get("target_date", "")),
            lesson_time = str(data.get("lesson_time", "")),
            route_minutes = int(data.get("route_minutes", 0)),
            rechecked_at = str(data.get("rechecked_at", "")),
            subject = str(data.get("subject", "")),
            destination = str(data.get("destination", "")),
            entry_type = str(data.get("entry_type", "")),
        )
