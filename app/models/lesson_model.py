import datetime
import uuid
from dataclasses import dataclass, field

ENTRY_TYPE_LESSON = "lesson"
ENTRY_TYPE_EVENT = "event"
DEFAULT_EVENT_REMINDER_LEAD_MINUTES = 90
VALID_EVENT_REMINDER_LEAD_MINUTES = {60, 90}


def normalize_event_reminder_lead_minutes(value: int | str) -> int:
    try:
        lead_minutes = int(value)
    except (TypeError, ValueError):
        lead_minutes = DEFAULT_EVENT_REMINDER_LEAD_MINUTES

    if lead_minutes not in VALID_EVENT_REMINDER_LEAD_MINUTES:
        return DEFAULT_EVENT_REMINDER_LEAD_MINUTES
    return lead_minutes


@dataclass
class Lesson:
    date: datetime.date
    time_start: str
    time_end: str
    subject: str
    teacher: str = ""
    room: str = ""
    auditorium: str = ""
    building: str = ""
    description: str = ""
    address: str = ""
    reminder_enabled: bool = False
    reminder_lead_minutes: int = DEFAULT_EVENT_REMINDER_LEAD_MINUTES
    entry_type: str = ENTRY_TYPE_LESSON
    is_custom: bool = False
    homeworks: list[str] = field(default_factory = list)
    test_works: list[str] = field(default_factory = list)
    lab_works: list[str] = field(default_factory = list)
    id: str = field(default_factory = lambda: str(uuid.uuid4()))

    @staticmethod
    def build_stable_id(
        date: datetime.date,
        time_start: str,
        time_end: str,
        subject: str,
        entry_type: str = ENTRY_TYPE_LESSON,
    ) -> str:
        seed = "|".join([
            date.strftime("%d.%m.%Y"),
            str(time_start).strip(),
            str(time_end).strip(),
            str(subject).strip(),
            str(entry_type).strip() or ENTRY_TYPE_LESSON,
        ])
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    @property
    def date_str(self) -> str:
        return self.date.strftime("%d.%m.%Y")

    @property
    def is_event(self) -> bool:
        return self.entry_type == ENTRY_TYPE_EVENT

    @property
    def location_text(self) -> str:
        if self.address:
            return self.address
        if self.room:
            return self.room

        parts = [part for part in [self.auditorium, self.building] if part]
        return " ".join(parts)

    def storage_key(self) -> tuple[str, str, str, str]:
        return (
            self.date_str,
            self.time_start,
            self.time_end,
            self.subject,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date_str,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "subject": self.subject,
            "teacher": self.teacher,
            "room": self.room,
            "auditorium": self.auditorium,
            "building": self.building,
            "description": self.description,
            "address": self.address,
            "reminder_enabled": self.reminder_enabled,
            "reminder_lead_minutes": normalize_event_reminder_lead_minutes(self.reminder_lead_minutes),
            "entry_type": self.entry_type,
            "is_custom": self.is_custom,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Lesson":
        return cls(
            id = str(data.get("id", str(uuid.uuid4()))),
            date = datetime.datetime.strptime(str(data["date"]).strip(), "%d.%m.%Y").date(),
            time_start = str(data["time_start"]).strip(),
            time_end = str(data["time_end"]).strip(),
            subject = str(data["subject"]).strip(),
            teacher = str(data.get("teacher", "")).strip(),
            room = str(data.get("room", "")).strip(),
            auditorium = str(data.get("auditorium", "")).strip(),
            building = str(data.get("building", "")).strip(),
            description = str(data.get("description", "")).strip(),
            address = str(data.get("address", "")).strip(),
            reminder_enabled = bool(data.get("reminder_enabled", False)),
            reminder_lead_minutes = normalize_event_reminder_lead_minutes(
                data.get("reminder_lead_minutes", DEFAULT_EVENT_REMINDER_LEAD_MINUTES)
            ),
            entry_type = str(data.get("entry_type", ENTRY_TYPE_LESSON)).strip() or ENTRY_TYPE_LESSON,
            is_custom = bool(data.get("is_custom", False)),
        )

    @classmethod
    def from_dict_entry(cls, key: str, subject: str) -> "Lesson":
        date_part, time_part = key.split(" ")
        date = datetime.datetime.strptime(date_part, "%d.%m.%Y").date()
        time_start, time_end = time_part.split("-")
        return cls(
            id = cls.build_stable_id(
                date,
                time_start.strip(),
                time_end.strip(),
                subject,
                ENTRY_TYPE_LESSON,
            ),
            date = date,
            time_start = time_start.strip(),
            time_end = time_end.strip(),
            subject = subject,
        )
