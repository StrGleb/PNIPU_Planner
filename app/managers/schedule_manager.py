import json
import datetime
import pathlib
import shutil

from models.schedule_template import ScheduleTemplate, TemplateLesson
from managers.planner_manager import PlannerManager


# ── Путь к файлу шаблона ────────────────────────────────────────────────────────
# Должно работать на Windows / Linux / macOS / Android
_APP_DIR = pathlib.Path(__file__).resolve().parent.parent # .../app/
_BUNDLED = _APP_DIR / "data" / "schedule.json" # поставляется с приложением

def _get_storage_path() -> pathlib.Path:
    """
    Персистентная директория:
    - Desktop: ~/.pnipu_planner/
    - Android (Flet): /data/user/0/<pkg>/files/.pnipu_planner/ 
    """
    
    storage = pathlib.Path.home() / ".pnipu_planner"
    storage.mkdir(parents=True, exist_ok=True)
    return storage / "schedule.json"


class ScheduleManager:
    """Загружает, сохраняет и применяет шаблон расписания."""

    def __init__(self):
        self._path = _get_storage_path()
        self.template: ScheduleTemplate = self._load()

    # ── Загрузка / сохранение ────────────────────────────────────────────────────

    def _load(self) -> ScheduleTemplate:
        # Если персистентного файла ещё нет — копируем встроенный шаблон
        if not self._path.exists():
            if _BUNDLED.exists():
                shutil.copy(_BUNDLED, self._path)
            else:
                return ScheduleTemplate() # пустой шаблон
        try:
            with open(self._path, encoding="utf-8") as f:
                return ScheduleTemplate.from_dict(json.load(f))
        except Exception:
            return ScheduleTemplate()

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self.template.to_dict(), f, ensure_ascii=False, indent=2)

    def reload(self) -> None:
        """Перечитать шаблон с диска (например, после импорта нового Excel)"""
        self.template = self._load()

    # ── Применение шаблона к планировщику ────────────────────────────────────────

    def apply_week(
        self,
        planner: PlannerManager,
        monday: datetime.date,
        is_even: bool,
    ) -> None:
        """
        Добавляет пары на указанную неделю
        Пропускает дни, которые уже есть в планере.
        """
        lessons = self.template.get_week(is_even)
        for tl in lessons:
            target_date = monday + datetime.timedelta(days=tl.day - 1)
            date_str = target_date.strftime("%d.%m.%Y")

            # Проверяем, нет ли уже такой пары на это место (дату и время)
            existing = planner.get_lessons_for_date(target_date)
            already = any(
                l.time_start == tl.time_start and l.subject == tl.subject
                for l in existing
            )
            if not already:
                subject_full = tl.subject
                if tl.lesson_type:
                    subject_full += f" ({tl.lesson_type})"
                if tl.room:
                    subject_full += f" | {tl.room}"
                planner.add_lesson(
                    target_date,
                    tl.time_start,
                    tl.time_end,
                    subject_full,
                )

    def apply_semester(
        self,
        planner: PlannerManager,
        start_date: datetime.date,
        end_date: datetime.date,
        first_week_even: bool,
    ) -> None:
        """
        Применяет шаблон на весь семестр
        first_week_even — True если первая неделя чётная
        """
        monday = start_date - datetime.timedelta(days=start_date.weekday())
        is_even = first_week_even
        while monday <= end_date:
            self.apply_week(planner, monday, is_even)
            monday += datetime.timedelta(weeks=1)
            is_even = not is_even