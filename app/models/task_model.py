import uuid
from dataclasses import dataclass, field

# Типы ученических работ
TASK_TYPE_HOMEWORK = "homework"
TASK_TYPE_TEST = "test"
TASK_TYPE_LAB = "lab"

# Цветовые индикаторы приоритета задач (Для UI)
PRIORITY_COLORS = {
    0: "grey400",
    1: "blue400",
    2: "orange400",
    3: "red500",
}

# Таблица приоритетности задач
PRIORITY_LABELS = {
    0: "Обычная",
    1: "Важная",
    2: "Срочная",
    3: "Критическая",
}


@dataclass
class Task:
    task_type: str # "homework" | "test" | "lab"
    date_str: str # "DD.MM.YYYY"
    time_start: str # "9:40"
    subject: str
    text: str
    lesson_id: str
    priority: int = 0 # 0–3, по умолчанию 0
    rating: float = 0.0  # вычисляется менеджером уведомлений
    id: str   = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_line(self) -> str:
        return f"{self.subject} в {self.time_start} — {self.text}"

    @property
    def type_label(self) -> str:
        return {"homework": "Д/З", "test": "К/Р", "lab": "Лаб"}.get(self.task_type, "?")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "date_str": self.date_str,
            "time_start": self.time_start,
            "subject": self.subject,
            "text": self.text,
            "lesson_id": self.lesson_id,
            "priority": self.priority,
            "rating": self.rating,
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
            priority = int(d.get("priority", 0)),
            rating = float(d.get("rating", 0.0)),
        )