import json
import pathlib
import sys
import tempfile
import threading
from datetime import datetime
from time import sleep
from typing import Callable, Optional

from bridges.planner_bridge import (
    build_next_one_time_target_date as native_build_next_one_time_target_date,
    collect_expired_one_time_alarm_indices,
    collect_triggered_alarm_indices,
    days_to_mask,
    week_type_code,
)
from models.alarm_model import Alarm, SOURCE_WEEK_SCHEDULE


def _storage_path() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        cache_dir = pathlib.Path(tempfile.gettempdir())
        base_dir = cache_dir.parent / "files"
        storage_dir = base_dir / ".pnipu_planner"
    else:
        storage_dir = pathlib.Path.home() / ".pnipu_planner"

    storage_dir.mkdir(parents = True, exist_ok = True)
    return storage_dir / "alarms.json"


class AlarmManager:
    def __init__(self):
        self._path = _storage_path()
        self._lock = threading.Lock()
        self.alarms: list[Alarm] = self._load()
        self._fired_keys: set[str] = set()
        self._on_trigger: Optional[Callable] = None
        self._week_even_fn: Optional[Callable[[], bool]] = None

    def _load(self) -> list[Alarm]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, encoding = "utf-8") as file:
                data = json.load(file)
            alarms = [Alarm.from_dict(item) for item in data.get("alarms", [])]
            return sorted(alarms, key = lambda alarm: (alarm.hour, alarm.minute))
        except Exception:
            return []

    def _save(self) -> None:
        """ Сохранение файла alarm.json для будильников """
        with open(self._path, "w", encoding = "utf-8") as file:
            json.dump(
                {"version": 1, "alarms": [alarm.to_dict() for alarm in self.alarms]},
                file,
                ensure_ascii = False,
                indent = 2,
            )

    def build_next_one_time_target_date(
        self,
        hour: int,
        minute: int,
        now: datetime | None = None,
    ) -> str:
        current = now or datetime.now()
        return native_build_next_one_time_target_date(hour, minute, current)

    def add(self, alarm: Alarm) -> None:
        """ Добавление будильника """
        with self._lock:
            self.alarms.append(alarm)
            self.alarms.sort(key = lambda item: (item.hour, item.minute))
        self._save()

    def remove(self, alarm_id: str) -> None:
        """ Уаделение будильника """
        with self._lock:
            self.alarms = [alarm for alarm in self.alarms if alarm.id != alarm_id]
        self._save()

    def toggle(self, alarm_id: str) -> None:
        with self._lock:
            for alarm in self.alarms:
                if alarm.id != alarm_id:
                    continue
                alarm.enabled = not alarm.enabled
                if alarm.enabled and alarm.is_one_time_manual:
                    alarm.target_date = self.build_next_one_time_target_date(alarm.hour, alarm.minute)
                break
        self._save()

    def update(
        self,
        alarm_id: str,
        hour: int,
        minute: int,
        days: list[int],
        week_type: str,
        target_date: str = "",
    ) -> None:
        """ Изменение уже существующего будильника """
        with self._lock:
            for alarm in self.alarms:
                if alarm.id != alarm_id:
                    continue
                alarm.hour = hour
                alarm.minute = minute
                alarm.days = days
                alarm.week_type = week_type
                alarm.target_date = target_date
                break
            self.alarms.sort(key = lambda item: (item.hour, item.minute))
        self._save()

    def replace_auto_schedule_alarms(self, alarms: list[Alarm]) -> None:
        with self._lock:
            manual_alarms = [alarm for alarm in self.alarms if not alarm.is_auto_schedule]
            self.alarms = manual_alarms + list(alarms)
            self.alarms.sort(key = lambda item: (item.hour, item.minute))
        self._save()

    def clear_auto_schedule_alarms(self) -> None:
        self.replace_auto_schedule_alarms([])

    def replace_week_schedule_alarms(self, alarms: list[Alarm]) -> None:
        with self._lock:
            other_alarms = [alarm for alarm in self.alarms if alarm.source != SOURCE_WEEK_SCHEDULE]
            self.alarms = other_alarms + list(alarms)
            self.alarms.sort(key = lambda item: (item.hour, item.minute))
        self._save()

    def clear_week_schedule_alarms(self) -> None:
        self.replace_week_schedule_alarms([])

    def get_auto_schedule_alarms(self) -> list[Alarm]:
        with self._lock:
            return [alarm for alarm in self.alarms if alarm.is_auto_schedule]

    def update_alarm_instance(self, updated_alarm: Alarm) -> None:
        with self._lock:
            for index, alarm in enumerate(self.alarms):
                if alarm.id == updated_alarm.id:
                    self.alarms[index] = updated_alarm
                    break
            self.alarms.sort(key = lambda item: (item.hour, item.minute))
        self._save()

    def set_trigger_callback(self, callback: Callable) -> None:
        self._on_trigger = callback

    def set_week_even_fn(self, fn: Callable[[], bool]) -> None:
        self._week_even_fn = fn

    def start_background_checker(self) -> None:
        thread = threading.Thread(target = self._check_loop, daemon = True)
        thread.start()

    def _disable_expired_one_time_alarms(self, now: datetime) -> bool:
        expired_indices = collect_expired_one_time_alarm_indices(
            [alarm.target_date for alarm in self.alarms],
            [int(alarm.enabled) for alarm in self.alarms],
            [int(alarm.is_one_time_manual) for alarm in self.alarms],
            now.date(),
        )
        if not expired_indices:
            return False

        changed = False
        for index in expired_indices:
            if 0 <= index < len(self.alarms) and self.alarms[index].enabled:
                self.alarms[index].enabled = False
                changed = True
        return changed

    def _disable_triggered_one_time_alarms(self, alarm_ids: list[str]) -> bool:
        if not alarm_ids:
            return False

        changed = False
        alarm_id_set = set(alarm_ids)
        for alarm in self.alarms:
            if alarm.id in alarm_id_set and alarm.is_one_time_manual and alarm.enabled:
                alarm.enabled = False
                changed = True
        return changed

    def _check_loop(self) -> None:
        while True:
            now = datetime.now()
            is_even = self._week_even_fn() if self._week_even_fn else False
            key = f"{now.hour}:{now.minute}"
            changed = False

            with self._lock:
                changed = self._disable_expired_one_time_alarms(now) or changed
                alarms_copy = list(self.alarms)

            week_type_codes = []
            day_masks = []
            for alarm in alarms_copy:
                week_type_codes.append(week_type_code(alarm.week_type))
                normalized_days: list[int] = []
                for day in alarm.days:
                    try:
                        normalized_days.append(int(day))
                    except (TypeError, ValueError):
                        continue
                day_masks.append(days_to_mask(normalized_days))

            triggered_indices = collect_triggered_alarm_indices(
                [int(alarm.enabled) for alarm in alarms_copy],
                [alarm.hour for alarm in alarms_copy],
                [alarm.minute for alarm in alarms_copy],
                [int(bool(alarm.target_date)) for alarm in alarms_copy],
                [alarm.target_date for alarm in alarms_copy],
                week_type_codes,
                day_masks,
                now,
                is_even,
            )

            triggered_one_time_ids: list[str] = []
            for index in triggered_indices:
                if index < 0 or index >= len(alarms_copy):
                    continue
                alarm = alarms_copy[index]
                fire_key = f"{alarm.id}:{key}"
                if fire_key in self._fired_keys:
                    continue
                self._fired_keys.add(fire_key)
                if self._on_trigger:
                    self._on_trigger(alarm)
                if alarm.is_one_time_manual:
                    triggered_one_time_ids.append(alarm.id)

            with self._lock:
                changed = self._disable_triggered_one_time_alarms(triggered_one_time_ids) or changed

            self._fired_keys = {item for item in self._fired_keys if item.endswith(key)}
            if changed:
                self._save()
            sleep(1)
