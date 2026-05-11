import uuid
from dataclasses import dataclass, field

TASK_TYPE_HOMEWORK = "homework"
TASK_TYPE_TEST     = "test"

@dataclass
class Task:
    task_type: str # "homework" | "test"
    date_str: str # "DD.MM.YYYY" — дата пары, к которой привязана задача
    time_start: str # "9:40"
    subject: str
    text: str
    lesson_id: str # id пары в PlannerManager (для удаления вместе с парой)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_line(self) -> str:
        return f"{self.subject} в {self.time_start} — {self.text}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "date_str": self.date_str,
            "time_start": self.time_start,
            "subject": self.subject,
            "text": self.text,
            "lesson_id": self.lesson_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            id = d.get("id", str(uuid.uuid4())),
            task_type = d["task_type"],
            date_str = d["date_str"],
            time_start = d["time_start"],
            subject = d["subject"],
            text = d["text"],
            lesson_id = d.get("lesson_id", ""),
        )