import datetime
import json
import pathlib
import shutil
import sys
import tempfile

from bridges.planner_bridge import is_valid_date_text
from managers.planner_manager import PlannerManager
from models.schedule_template import ScheduleTemplate


_APP_DIR = pathlib.Path(__file__).resolve().parent.parent
_BUNDLED = _APP_DIR / "data" / "schedule.json"


def get_schedule_storage_path() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        cache_dir = pathlib.Path(tempfile.gettempdir())
        base_dir = cache_dir.parent / "files"
        storage_dir = base_dir / ".pnipu_planner"
    else:
        storage_dir = pathlib.Path.home() / ".pnipu_planner"

    storage_dir.mkdir(parents = True, exist_ok = True)
    return storage_dir / "schedule.json"


class ScheduleManager:
    """Loads, stores and applies the parsed schedule template."""

    def __init__(self):
        self._path = get_schedule_storage_path()
        self.template: ScheduleTemplate = self._load()

    def _load(self) -> ScheduleTemplate:
        if not self._path.exists():
            if _BUNDLED.exists():
                shutil.copy(_BUNDLED, self._path)
            else:
                return ScheduleTemplate()

        try:
            with open(self._path, encoding = "utf-8") as file:
                return ScheduleTemplate.from_dict(json.load(file))
        except Exception:
            return ScheduleTemplate()

    def save(self) -> None:
        with open(self._path, "w", encoding = "utf-8") as file:
            json.dump(self.template.to_dict(), file, ensure_ascii = False, indent = 2)

    def reload(self) -> None:
        self.template = self._load()

    def _parse_semester_start(self) -> datetime.date | None:
        value = (self.template.semester_start or "").strip()
        if not value or not is_valid_date_text(value):
            return None
        return datetime.datetime.strptime(value, "%d.%m.%Y").date()

    def _derive_semester_end(self, start_date: datetime.date) -> datetime.date:
        if start_date.month >= 8:
            return datetime.date(start_date.year + 1, 1, 31)
        return datetime.date(start_date.year, 6, 30)

    def _format_subject(
        self,
        subject: str,
        lesson_type: str,
        teacher: str,
        room: str,
    ) -> str:
        parts: list[str] = []
        head = subject.strip()
        if lesson_type.strip():
            head = f"{head} ({lesson_type.strip()})"
        if head:
            parts.append(head)
        if teacher.strip():
            parts.append(teacher.strip())
        if room.strip():
            parts.append(room.strip())
        return " | ".join(parts)

    def apply_template_to_planner(
        self,
        planner: PlannerManager,
        clear_existing: bool = True,
    ) -> bool:
        semester_start = self._parse_semester_start()
        if semester_start is None:
            return False

        if clear_existing:
            planner.clear()

        self.apply_semester(
            planner = planner,
            start_date = semester_start,
            end_date = self._derive_semester_end(semester_start),
            first_week_even = self.template.first_week_even,
        )
        return True

    def apply_week(
        self,
        planner: PlannerManager,
        monday: datetime.date,
        is_even: bool,
    ) -> None:
        lessons = self.template.get_week(is_even)
        for lesson in lessons:
            target_date = monday + datetime.timedelta(days = lesson.day - 1)
            subject_full = self._format_subject(
                lesson.subject,
                lesson.lesson_type,
                lesson.teacher,
                lesson.room,
            )

            existing = planner.get_lessons_for_date(target_date)
            already_exists = any(
                item.time_start == lesson.time_start and item.subject == subject_full
                for item in existing
            )
            if already_exists:
                continue

            planner.add_lesson(
                target_date,
                lesson.time_start,
                lesson.time_end,
                subject_full,
            )

    def apply_semester(
        self,
        planner: PlannerManager,
        start_date: datetime.date,
        end_date: datetime.date,
        first_week_even: bool,
    ) -> None:
        monday = start_date - datetime.timedelta(days = start_date.weekday())
        is_even = first_week_even
        while monday <= end_date:
            self.apply_week(planner, monday, is_even)
            monday += datetime.timedelta(weeks = 1)
            is_even = not is_even
