import datetime
import json
import pathlib
import sys
import tempfile

from bridges.planner_bridge import (
    collect_schedule_lesson_indices_for_day,
    derive_schedule_period_end_date,
    is_week_even,
    select_active_template_index,
    time_to_minutes,
)
from managers.planner_manager import PlannerManager
from models.schedule_template import ScheduleArchive, ScheduleTemplate, TemplateLesson


def _storage_dir() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        cache_dir = pathlib.Path(tempfile.gettempdir())
        base_dir = cache_dir.parent / "files"
        root = base_dir / ".pnipu_planner"
    else:
        root = pathlib.Path.home() / ".pnipu_planner"

    root.mkdir(parents=True, exist_ok=True)
    return root


def get_schedule_storage_path() -> pathlib.Path:
    return _storage_dir() / "schedule.json"


class ScheduleManager:
    def __init__(self):
        self._path = get_schedule_storage_path()
        self.archive = ScheduleArchive()
        self.template = ScheduleTemplate()
        self.reload()

    def _load(self) -> ScheduleArchive:
        if not self._path.exists():
            return ScheduleArchive()

        try:
            with open(self._path, encoding="utf-8") as handle:
                return ScheduleArchive.from_dict(json.load(handle))
        except Exception:
            return ScheduleArchive()

    def save(self) -> None:
        self._sort_archive()
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(self.archive.to_dict(), handle, ensure_ascii=False, indent=2)

    def reload(self) -> None:
        self.archive = self._load()
        self._sort_archive()
        self.template = self.get_active_template(datetime.date.today())

    def has_templates(self) -> bool:
        return bool(self.archive.templates)

    def _sort_archive(self) -> None:
        self.archive.templates.sort(
            key=lambda template: self._parse_template_start(template) or datetime.date.max
        )

    def _parse_template_start(
        self,
        template: ScheduleTemplate,
    ) -> datetime.date | None:
        return self._parse_start_text(template.semester_start)

    @staticmethod
    def _parse_start_text(value: str) -> datetime.date | None:
        try:
            return datetime.datetime.strptime(str(value).strip(), "%d.%m.%Y").date()
        except Exception:
            return None

    @staticmethod
    def _derive_period_end(start_date: datetime.date) -> datetime.date:
        if start_date.month >= 8:
            return datetime.date(start_date.year + 1, 1, 31)
        return datetime.date(start_date.year, 6, 30)

    def merge_template(self, template: ScheduleTemplate) -> None:
        start_date = self._parse_template_start(template)
        if start_date is None:
            return

        replaced = False
        merged: list[ScheduleTemplate] = []
        for current in self.archive.templates:
            current_start = self._parse_template_start(current)
            if current_start == start_date:
                merged.append(template)
                replaced = True
            else:
                merged.append(current)

        if not replaced:
            merged.append(template)

        self.archive.templates = merged
        self._sort_archive()

    def import_schedule_json(self, parsed_json_path: str | pathlib.Path) -> ScheduleTemplate:
        with open(parsed_json_path, encoding="utf-8") as handle:
            template = ScheduleTemplate.from_dict(json.load(handle))

        self.merge_template(template)
        self.save()
        self.reload()
        return template

    def get_active_template(self, date: datetime.date | None = None) -> ScheduleTemplate:
        if not self.archive.templates:
            return ScheduleTemplate()

        target_date = date or datetime.date.today()
        valid_templates: list[ScheduleTemplate] = []
        start_texts: list[str] = []
        for template in self.archive.templates:
            start_date = self._parse_template_start(template)
            if start_date is None:
                continue
            valid_templates.append(template)
            start_texts.append(start_date.strftime("%d.%m.%Y"))

        if not valid_templates:
            return self.archive.templates[0]

        active_index = select_active_template_index(start_texts, target_date)
        if active_index < 0:
            return valid_templates[0]
        return valid_templates[active_index]

    def get_active_schedule_payload(self, date: datetime.date | None = None) -> dict:
        return self.get_active_template(date).to_dict()

    @staticmethod
    def _get_weekday_lessons(
        template: ScheduleTemplate,
        is_even: bool,
        weekday: int,
    ) -> list[TemplateLesson]:
        lessons = template.get_week(is_even)
        indices = collect_schedule_lesson_indices_for_day(
            [int(lesson.day) for lesson in lessons],
            [time_to_minutes(lesson.time_start) for lesson in lessons],
            weekday,
        )
        return [lessons[index] for index in indices]

    def get_lessons_for_date(self, date: datetime.date) -> list[TemplateLesson]:
        template = self.get_active_template(date)
        if not template.semester_start:
            return []

        weekday = date.isoweekday()
        is_even = is_week_even(
            date,
            template.semester_start,
            template.first_week_even,
        )
        return self._get_weekday_lessons(template, is_even, weekday)

    @staticmethod
    def _format_subject(lesson: TemplateLesson) -> str:
        lesson_type = str(lesson.lesson_type).strip()
        if lesson_type:
            return f"{lesson.subject} ({lesson_type})"
        return lesson.subject

    def _initial_dedupe_keys(self, planner: PlannerManager) -> set[tuple[str, str, str, str]]:
        keys: set[tuple[str, str, str, str]] = set()
        lessons = getattr(planner, "_lessons", {})
        for lesson in lessons.values():
            keys.add(
                (
                    lesson.date.strftime("%d.%m.%Y"),
                    lesson.time_start,
                    lesson.time_end,
                    lesson.subject,
                )
            )
        return keys

    def _apply_template_period(
        self,
        planner: PlannerManager,
        template: ScheduleTemplate,
        start_date: datetime.date,
        end_date: datetime.date,
        existing_keys: set[tuple[str, str, str, str]],
    ) -> int:
        if end_date < start_date:
            return 0

        applied = 0
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.isoweekday()
            is_even = is_week_even(
                current_date,
                template.semester_start,
                template.first_week_even,
            )

            for lesson in self._get_weekday_lessons(template, is_even, weekday):
                subject = self._format_subject(lesson)
                key = (
                    current_date.strftime("%d.%m.%Y"),
                    lesson.time_start,
                    lesson.time_end,
                    subject,
                )
                if key in existing_keys:
                    continue

                planner.add_lesson(
                    current_date,
                    lesson.time_start,
                    lesson.time_end,
                    subject,
                    teacher = lesson.teacher,
                    room = lesson.room,
                    auditorium = lesson.auditorium,
                    building = lesson.building,
                )
                existing_keys.add(key)
                applied += 1

            current_date += datetime.timedelta(days=1)

        return applied

    def apply_template_to_planner(
        self,
        planner: PlannerManager,
        clear_existing: bool = True,
    ) -> bool:
        templates = [
            template
            for template in self.archive.templates
            if self._parse_template_start(template) is not None
        ]
        if not templates:
            if clear_existing:
                planner.clear()
            return False

        if clear_existing:
            planner.clear(preserve_custom = True)

        existing_keys = self._initial_dedupe_keys(planner)
        applied = 0

        for index, template in enumerate(templates):
            start_date = self._parse_template_start(template)
            if start_date is None:
                continue

            next_start = None
            if index + 1 < len(templates):
                next_start = self._parse_template_start(templates[index + 1])
            end_date = derive_schedule_period_end_date(start_date, next_start)

            applied += self._apply_template_period(
                planner,
                template,
                start_date,
                end_date,
                existing_keys,
            )

        self.template = self.get_active_template(datetime.date.today())
        return applied > 0
