import datetime
from typing import Optional
from models.lesson_model import Lesson
import logging

logger = logging.getLogger(__name__)

class PlannerManager:
    """
    Хранит все пары и предоставляет CRUD-интерфейс.
    Также поддерживает загрузку из словаря формата
    {"ДД.ММ.ГГГГ ЧЧ:ММ-ЧЧ:ММ": "Название"}.
    """

    def __init__(self):
        self._lessons: dict[str, Lesson] = {}  # id -> Lesson

    # ── CRUD ────────────────────────────────────────────────────────────────────
    def add_lesson(
        self,
        date: datetime.date,
        time_start: str,
        time_end: str,
        subject: str,
    ) -> Lesson:
        lesson = Lesson(date = date, time_start = time_start, time_end = time_end, subject = subject)
        self._lessons[lesson.id] = lesson
        return lesson

    def remove_lesson(self, lesson_id: str) -> None:
        self._lessons.pop(lesson_id, None)

    def clear(self) -> None:
        self._lessons.clear()

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        return self._lessons.get(lesson_id)

    def get_lessons_for_date(self, date: datetime.date) -> list[Lesson]:
        result = [l for l in self._lessons.values() if l.date == date]
        return sorted(result, key = lambda l: (int(l.time_start.split(":")[0]), int(l.time_start.split(":")[1])))

    def add_homework(self, lesson_id: str, text: str) -> None:
        lesson = self._lessons.get(lesson_id)
        if lesson:
            lesson.homeworks.append(text)

    def add_test_work(self, lesson_id: str, text: str) -> None:
        lesson = self._lessons.get(lesson_id)
        if lesson:
            lesson.test_works.append(text)

    def add_lab_work(self, lesson_id: str, text: str) -> None:
        lesson = self._lessons.get(lesson_id)
        if lesson:
            lesson.lab_works.append(text)

    # ── Import ───────────────────────────────────────────────────────────────────
    def load_from_dict(self, data: dict[str, str]) -> None:
        """
        Загружает пары из словаря:
        {"13.04.2026 9:40-11:10": "Математика (лек.)", ...}
        """
        for key, subject in data.items():
            try:
                lesson = Lesson.from_dict_entry(key, subject)
                self._lessons[lesson.id] = lesson
            except Exception as e:
                logger.error("Не удалось подгрузить файл с шаблоном распсиания: {e}")
