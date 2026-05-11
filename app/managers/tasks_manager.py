"""
Персистентное хранилище домашних заданий и контрольных работ.
Файл: ~/.pnipu_planner/tasks.json
ВРЕМЕННАЯ РЕАЛИЗАЦИЯ ЧЕРЕЗ JSON-ФАЙЛ
"""
import json
import datetime
import pathlib
from typing import List
from models.task_model import Task, TASK_TYPE_HOMEWORK, TASK_TYPE_TEST


def _storage_path() -> pathlib.Path:
    d = pathlib.Path.home() / ".pnipu_planner"
    d.mkdir(parents=True, exist_ok=True)
    return d / "tasks.json"

class TasksManager:
    def __init__(self):
        self._path = _storage_path()
        self._tasks: List[Task] = self._load()

    # ── Загрузка / сохранение ─────────────────────────────────────────────────
    def _load(self) -> List[Task]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            return [Task.from_dict(d) for d in data.get("tasks", [])]
        except Exception:
            return []

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(
                {"version": 1, "tasks": [t.to_dict() for t in self._tasks]},
                f, ensure_ascii=False, indent=2,
            )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_task(
        self,
        task_type: str,
        date_str: str,
        time_start: str,
        subject: str,
        text: str,
        lesson_id: str,
    ) -> Task:
        task = Task(
            task_type = task_type,
            date_str = date_str,
            time_start = time_start,
            subject = subject,
            text = text,
            lesson_id = lesson_id,
        )
        self._tasks.append(task)
        self._save()
        return task

    def remove_task(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._save()

    def remove_tasks_for_lesson(self, lesson_id: str) -> None:
        """Удаляет все задачи, привязанные к паре (при удалении пары из Planner)."""
        self._tasks = [t for t in self._tasks if t.lesson_id != lesson_id]
        self._save()

    # ── Запросы ───────────────────────────────────────────────────────────────
    def get_tests_for_date(self, date: datetime.date) -> List[Task]:
        ds = date.strftime("%d.%m.%Y")
        return [t for t in self._tasks
                if t.task_type == TASK_TYPE_TEST and t.date_str == ds]

    def get_homework_for_date(self, date: datetime.date) -> List[Task]:
        ds = date.strftime("%d.%m.%Y")
        return [t for t in self._tasks
                if t.task_type == TASK_TYPE_HOMEWORK and t.date_str == ds]