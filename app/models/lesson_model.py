from dataclasses import dataclass, field
import uuid
import datetime


@dataclass
class Lesson:
    date: datetime.date
    time_start: str # "09:40"
    time_end: str # "11:10"
    subject: str
    homeworks: list[str] = field(default_factory=list)
    test_works: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def date_str(self) -> str:
        return self.date.strftime("%d.%m.%Y")

    @classmethod
    def from_dict_entry(cls, key: str, subject: str) -> "Lesson":
        """
        Парсит запись формата {"13.04.2026 9:40-11:10": "Математика (лек.)"}.
        """
        date_part, time_part = key.split(" ")
        date = datetime.datetime.strptime(date_part, "%d.%m.%Y").date()
        time_start, time_end = time_part.split("-")
        return cls(date=date, time_start=time_start.strip(), time_end=time_end.strip(), subject=subject)
