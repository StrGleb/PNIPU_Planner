import datetime
import json
import logging
import pathlib
import sys
import tempfile
from typing import Optional

from bridges.planner_bridge import collect_lesson_indices_for_date_sorted, time_to_minutes
from models.lesson_model import ENTRY_TYPE_EVENT, Lesson

logger = logging.getLogger(__name__)


def _storage_path() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        cache_dir = pathlib.Path(tempfile.gettempdir())
        base_dir = cache_dir.parent / "files"
        root = base_dir / ".pnipu_planner"
    else:
        root = pathlib.Path.home() / ".pnipu_planner"

    root.mkdir(parents = True, exist_ok = True)
    return root / "custom_events.json"


class PlannerManager:
    def __init__(self):
        self._path = _storage_path()
        self._lessons: dict[str, Lesson] = {}
        self._load_custom_lessons()

    def _load_custom_lessons(self) -> None:
        if not self._path.exists():
            return

        try:
            with open(self._path, encoding = "utf-8") as handle:
                data = json.load(handle)
            for item in data.get("lessons", []):
                lesson = Lesson.from_dict(item)
                lesson.is_custom = True
                self._lessons[lesson.id] = lesson
        except Exception:
            logger.exception("Не удалось загрузить пользовательские события")
            return

    def _save_custom_lessons(self) -> None:
        custom_lessons = [lesson.to_dict() for lesson in self._lessons.values() if lesson.is_custom]
        with open(self._path, "w", encoding = "utf-8") as handle:
            json.dump(
                {"version": 1, "lessons": custom_lessons},
                handle,
                ensure_ascii = False,
                indent = 2,
            )

    def add_lesson(
        self,
        date: datetime.date,
        time_start: str,
        time_end: str,
        subject: str,
        teacher: str = "",
        room: str = "",
        auditorium: str = "",
        building: str = "",
        description: str = "",
        address: str = "",
        entry_type: str = "lesson",
        is_custom: bool = False,
    ) -> Lesson:
        lesson_kwargs = {}
        if not is_custom:
            lesson_kwargs["id"] = Lesson.build_stable_id(
                date,
                time_start,
                time_end,
                subject,
                entry_type,
            )

        lesson = Lesson(
            date = date,
            time_start = time_start,
            time_end = time_end,
            subject = subject,
            teacher = teacher,
            room = room,
            auditorium = auditorium,
            building = building,
            description = description,
            address = address,
            entry_type = entry_type,
            is_custom = is_custom,
            **lesson_kwargs,
        )
        self._lessons[lesson.id] = lesson
        if lesson.is_custom:
            self._save_custom_lessons()
        return lesson

    def add_custom_event(
        self,
        date: datetime.date,
        time_start: str,
        time_end: str,
        subject: str,
        description: str = "",
        address: str = "",
    ) -> Lesson:
        return self.add_lesson(
            date = date,
            time_start = time_start,
            time_end = time_end,
            subject = subject,
            description = description,
            address = address,
            entry_type = ENTRY_TYPE_EVENT,
            is_custom = True,
        )

    def remove_lesson(self, lesson_id: str) -> None:
        lesson = self._lessons.pop(lesson_id, None)
        if lesson and lesson.is_custom:
            self._save_custom_lessons()

    def clear(self, preserve_custom: bool = False) -> None:
        if preserve_custom:
            self._lessons = {
                lesson_id: lesson
                for lesson_id, lesson in self._lessons.items()
                if lesson.is_custom
            }
            return
        self._lessons.clear()
        self._save_custom_lessons()

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        return self._lessons.get(lesson_id)

    def get_all_lessons(self) -> list[Lesson]:
        return list(self._lessons.values())

    def get_lessons_for_date(self, date: datetime.date) -> list[Lesson]:
        lessons = list(self._lessons.values())
        indices = collect_lesson_indices_for_date_sorted(
            [lesson.date_str for lesson in lessons],
            [time_to_minutes(lesson.time_start) for lesson in lessons],
            date.strftime("%d.%m.%Y"),
        )
        return [lessons[index] for index in indices]

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

    def load_from_dict(self, data: dict[str, str]) -> None:
        for key, subject in data.items():
            try:
                lesson = Lesson.from_dict_entry(key, subject)
                self._lessons[lesson.id] = lesson
            except Exception:
                logger.exception("Не удалось загрузить шаблон расписания")
                return
