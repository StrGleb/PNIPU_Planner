"""
Персистентное хранилище задач (д/з, к/р, лабораторные).
Файл: ~/.pnipu_planner/tasks.json
ВРЕМЕННАЯ РЕАЛИЗАЦИЯ ЧЕРЕЗ JSON-ФАЙЛ?
"""

import json
import datetime
import pathlib
import sys
import tempfile
import os
from typing import List

from bridges.planner_bridge import (
    collect_task_indices_for_lesson_sorted,
    collect_task_indices_for_type_and_date_sorted,
    collect_urgent_task_indices_sorted,
    compute_task_ratings_for_dates,
    normalize_priority,
)
from models.task_model import Task, TASK_TYPE_HOMEWORK, TASK_TYPE_TEST, TASK_TYPE_LAB


def _storage_path() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        # На Android получаем путь к кэшу (/data/user/0/<pkg>/cache)
        cache_dir = pathlib.Path(tempfile.gettempdir())
        # Его родитель — это корень песочницы приложения (/data/user/0/<pkg>)
        base_dir = cache_dir.parent / "files"
        d = base_dir / ".pnipu_planner"
    else:
        # На Windows/macOS/Linux используем домашнюю папку пользователя
        d = pathlib.Path.home() / ".pnipu_planner"

    d.mkdir(parents = True, exist_ok = True)
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
            with open(self._path, encoding = "utf-8") as f:
                data = json.load(f)
            return [Task.from_dict(d) for d in data.get("tasks", [])]
        except Exception:
            return []

    def _save(self) -> None:
        with open(self._path, "w", encoding = "utf-8") as f:
            json.dump(
                {"version": 2, "tasks": [t.to_dict() for t in self._tasks]},
                f, ensure_ascii = False, indent = 2,
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
        priority: int = 0,
    ) -> Task:
        task = Task(
            task_type = task_type,
            date_str = date_str,
            time_start = time_start,
            subject = subject,
            text = text,
            lesson_id = lesson_id,
            priority = normalize_priority(priority),
        )
        self._tasks.append(task)
        self._save()
        return task

    def remove_task(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._save()

    def remove_tasks_for_lesson(self, lesson_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.lesson_id != lesson_id]
        self._save()

    def update_rating(self, task_id: str, rating: float) -> None:
        for t in self._tasks:
            if t.id == task_id:
                t.rating = rating
        self._save()

    def update_task(self, task_id: str, text: str, priority: int) -> None:
        for t in self._tasks:
            if t.id == task_id:
                t.text = text.strip()
                t.priority = normalize_priority(priority)
                break
        self._save()

    # ── Запросы ───────────────────────────────────────────────────────────────
    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks)

    def _get_by_type_and_date(self, task_type: str, date: datetime.date) -> List[Task]:
        ds = date.strftime("%d.%m.%Y")
        indices = collect_task_indices_for_type_and_date_sorted(
            [task.task_type for task in self._tasks],
            [task.date_str for task in self._tasks],
            [task.priority for task in self._tasks],
            task_type,
            ds,
        )
        return [self._tasks[index] for index in indices]

    def get_tests_for_date(self, date: datetime.date) -> List[Task]:
        return self._get_by_type_and_date(TASK_TYPE_TEST, date)

    def get_homework_for_date(self, date: datetime.date) -> List[Task]:
        return self._get_by_type_and_date(TASK_TYPE_HOMEWORK, date)

    def get_labs_for_date(self, date: datetime.date) -> List[Task]:
        return self._get_by_type_and_date(TASK_TYPE_LAB, date)
    
    def get_tasks_for_lesson(self, lesson_id: str) -> List[Task]:
        indices = collect_task_indices_for_lesson_sorted(
            [task.lesson_id for task in self._tasks],
            [task.priority for task in self._tasks],
            lesson_id,
        )
        return [self._tasks[index] for index in indices]

    def refresh_all_ratings(self, today: datetime.date | None = None) -> None:
        if not self._tasks:
            return

        current_date = today or datetime.date.today()
        ratings = compute_task_ratings_for_dates(
            [task.priority for task in self._tasks],
            [task.date_str for task in self._tasks],
            current_date,
        )
        for task, rating in zip(self._tasks, ratings):
            task.rating = rating
        self._save()

    def get_urgent_tasks(self, threshold: float) -> List[Task]:
        if not self._tasks:
            return []

        indices = collect_urgent_task_indices_sorted(
            [task.rating for task in self._tasks],
            threshold,
        )
        return [self._tasks[index] for index in indices]
