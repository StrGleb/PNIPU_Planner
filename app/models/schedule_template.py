from dataclasses import dataclass, field
from typing import List


@dataclass
class TemplateLesson:
    day: int
    time_start: str
    time_end: str
    subject: str
    date_text: str = ""
    lesson_type: str = ""
    teacher: str = ""
    room: str = ""
    auditorium: str = ""
    building: str = ""

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "subject": self.subject,
            "date_text": self.date_text,
            "lesson_type": self.lesson_type,
            "teacher": self.teacher,
            "room": self.room,
            "auditorium": self.auditorium,
            "building": self.building,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateLesson":
        return cls(
            day = int(data["day"]),
            time_start = data["time_start"],
            time_end = data["time_end"],
            subject = data["subject"],
            date_text = data.get("date_text", ""),
            lesson_type = data.get("lesson_type", ""),
            teacher = data.get("teacher", ""),
            room = data.get("room", ""),
            auditorium = data.get("auditorium", ""),
            building = data.get("building", ""),
        )


@dataclass
class ScheduleTemplate:
    version: int = 3
    title: str = ""
    semester_start: str = ""
    first_week_even: bool = False
    schedule_type: str = "weekly"
    odd: List[TemplateLesson] = field(default_factory = list)
    even: List[TemplateLesson] = field(default_factory = list)
    dated: List[TemplateLesson] = field(default_factory = list)

    def get_week(self, is_even: bool) -> List[TemplateLesson]:
        return self.even if is_even else self.odd

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "title": self.title,
            "semester_start": self.semester_start,
            "first_week_even": self.first_week_even,
            "schedule_type": self.schedule_type,
            "odd": [lesson.to_dict() for lesson in self.odd],
            "even": [lesson.to_dict() for lesson in self.even],
            "dated": [lesson.to_dict() for lesson in self.dated],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleTemplate":
        return cls(
            version = data.get("version", 3),
            title = data.get("title", ""),
            semester_start = data.get("semester_start", ""),
            first_week_even = bool(data.get("first_week_even", False)),
            schedule_type = data.get("schedule_type", "weekly"),
            odd = [TemplateLesson.from_dict(item) for item in data.get("odd", [])],
            even = [TemplateLesson.from_dict(item) for item in data.get("even", [])],
            dated = [TemplateLesson.from_dict(item) for item in data.get("dated", [])],
        )


@dataclass
class ScheduleArchive:
    version: int = 3
    templates: List[ScheduleTemplate] = field(default_factory = list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "templates": [template.to_dict() for template in self.templates],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleArchive":
        if isinstance(data, dict) and "templates" in data:
            return cls(
                version = data.get("version", 3),
                templates = [
                    ScheduleTemplate.from_dict(item)
                    for item in data.get("templates", [])
                    if isinstance(item, dict)
                ],
            )

        if isinstance(data, dict):
            return cls(templates = [ScheduleTemplate.from_dict(data)])

        return cls()
