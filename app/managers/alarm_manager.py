import json
import pathlib
import threading
from time import sleep
from datetime import datetime
from typing import Callable, Optional
from models.alarm_model import Alarm


def _storage_path() -> pathlib.Path:
    d = pathlib.Path.home() / ".pnipu_planner"
    d.mkdir(parents = True, exist_ok = True)
    return d / "alarms.json"


class AlarmManager:
    def __init__(self):
        self._path = _storage_path()
        self._lock = threading.Lock()
        self.alarms: list[Alarm] = self._load()
        self._fired_keys: set[str] = set()
        self._on_trigger: Optional[Callable] = None
        self._week_even_fn: Optional[Callable[[], bool]] = None

    # ── Персистентность ───────────────────────────────────────────────────────
    def _load(self) -> list[Alarm]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            alarms = [Alarm.from_dict(d) for d in data.get("alarms", [])]
            return sorted(alarms, key = lambda a: (a.hour, a.minute))
        except Exception:
            return []

    def _save(self) -> None:
        with open(self._path, "w", encoding = "utf-8") as f:
            json.dump(
                {"version": 1, "alarms": [a.to_dict() for a in self.alarms]},
                f, ensure_ascii = False, indent = 2,
            )

    # ── Public API ────────────────────────────────────────────────────────────
    def add(self, alarm: Alarm) -> None:
        with self._lock:
            self.alarms.append(alarm)
            self.alarms.sort(key = lambda a: (a.hour, a.minute))
        self._save()

    def remove(self, alarm_id: str) -> None:
        with self._lock:
            self.alarms = [a for a in self.alarms if a.id != alarm_id]
        self._save()

    def toggle(self, alarm_id: str) -> None:
        with self._lock:
            for a in self.alarms:
                if a.id == alarm_id:
                    a.enabled = not a.enabled
                    break
        self._save()

    def update(self, alarm_id: str, hour: int, minute: int, days: list, week_type: str) -> None:
        """Обновляет время и дни существующего будильника."""
        with self._lock:
            for a in self.alarms:
                if a.id == alarm_id:
                    a.hour = hour
                    a.minute = minute
                    a.days = days
                    a.week_type = week_type
                    break
            self.alarms.sort(key = lambda a: (a.hour, a.minute))
        self._save()

    def set_trigger_callback(self, callback: Callable) -> None:
        self._on_trigger = callback

    def set_week_even_fn(self, fn: Callable[[], bool]) -> None:
        """Функция возвращает True если текущая неделя чётная."""
        self._week_even_fn = fn

    def start_background_checker(self) -> None:
        t = threading.Thread(target = self._check_loop, daemon = True)
        t.start()

    # ── Internal ──────────────────────────────────────────────────────────────
    def _check_loop(self) -> None:
        while True:
            now = datetime.now()
            is_even = self._week_even_fn() if self._week_even_fn else False
            key = f"{now.hour}:{now.minute}"
            with self._lock:
                alarms_copy = list(self.alarms)
            for alarm in alarms_copy:
                fire_key = f"{alarm.id}:{key}"
                if alarm.matches_now(now, is_even) and fire_key not in self._fired_keys:
                    self._fired_keys.add(fire_key)
                    if self._on_trigger:
                        self._on_trigger(alarm)
            self._fired_keys = {k for k in self._fired_keys if k.endswith(key)}
            sleep(1)