from dataclasses import dataclass, field
from typing import List

@dataclass
class TemplateLesson:
    """Одна пара из шаблона расписания."""
    day: int # 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт, 6=Сб
    time_start: str # "9:40"
    time_end: str # "11:10"
    subject: str
    lesson_type: str # "лек" | "пр" | "лаб"
    teacher: str
    room: str

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "subject": self.subject,
            "lesson_type": self.lesson_type,
            "teacher": self.teacher,
            "room": self.room,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateLesson":
        return cls(
            day = int(d["day"]),
            time_start = d["time_start"],
            time_end = d["time_end"],
            subject = d["subject"],
            lesson_type = d.get("lesson_type", ""),
            teacher = d.get("teacher", ""),
            room = d.get("room", ""),
        )


@dataclass
class ScheduleTemplate:
    """Шаблон расписания — два списка пар (чётная/нечётная)"""
    version: int = 1
    odd:  List[TemplateLesson] = field(default_factory=list) # нечётная
    even: List[TemplateLesson] = field(default_factory=list) # чётная

    def get_week(self, is_even: bool) -> List[TemplateLesson]:
        return self.even if is_even else self.odd

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "odd":  [l.to_dict() for l in self.odd],
            "even": [l.to_dict() for l in self.even],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScheduleTemplate":
        return cls(
            version=d.get("version", 1),
            odd=[TemplateLesson.from_dict(x) for x in d.get("odd", [])],
            even=[TemplateLesson.from_dict(x) for x in d.get("even", [])],
        )