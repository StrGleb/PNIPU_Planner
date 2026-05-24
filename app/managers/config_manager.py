import json
import pathlib
import sys
import tempfile
import os
from bridges.planner_bridge import (
    is_valid_date_text,
    normalize_duration_minutes,
    normalize_theme,
)
from models.user_config import UserConfig

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
    return d / "config.json" # (или "tasks.json" / "alarms.json" / "schedule.json")


class ConfigManager:
    """Хранит настройки пользователя. Читает/пишет JSON"""
    def __init__(self):
        self._path = _storage_path()
        self.config: UserConfig = self._load()

        if not self._path.exists():
            self.save()

    def _load(self) -> UserConfig:
        if not self._path.exists():
            return self._sanitize(UserConfig())
        try:
            with open(self._path, encoding = "utf-8") as f:
                return self._sanitize(UserConfig.from_dict(json.load(f)))
        except Exception:
            return self._sanitize(UserConfig())

    def _sanitize(self, config: UserConfig) -> UserConfig:
        default_semester_start = UserConfig().semester_start
        semester_start = str(config.semester_start).strip()
        if not is_valid_date_text(semester_start):
            semester_start = default_semester_start

        refresh_hour = max(0, min(23, int(getattr(config, "auto_alarm_refresh_hour", 21))))
        recheck_lead = normalize_duration_minutes(getattr(config, "auto_alarm_recheck_lead_minutes", 60))

        return UserConfig(
            theme = normalize_theme(config.theme),
            user_name = str(config.user_name).strip(),
            get_together_time = normalize_duration_minutes(config.get_together_time),
            travel_time = normalize_duration_minutes(config.travel_time),
            user_address = str(config.user_address).strip(),
            user_faculty = str(config.user_faculty).strip(),
            has_car = bool(config.has_car),
            semester_start = semester_start,
            first_week_even = bool(config.first_week_even),
            auto_alarm_enabled = bool(getattr(config, "auto_alarm_enabled", False)),
            auto_alarm_refresh_hour = refresh_hour,
            auto_alarm_recheck_lead_minutes = recheck_lead,
        )

    def save(self) -> None:
        self.config = self._sanitize(self.config)
        with open(self._path, "w", encoding = "utf-8") as f:
            json.dump(self.config.to_dict(), f, ensure_ascii = False, indent = 2)


    # ── Набор сеттеров ─────────────────────────
    def set_theme(self, value: str) -> None:
        self.config.theme = normalize_theme(value)
        self.save()

    def set_user_name(self, value: str) -> None:
        self.config.user_name = str(value).strip()
        self.save()

    def set_get_together_time(self, value: int) -> None:
        self.config.get_together_time = normalize_duration_minutes(value)
        self.save()

    def set_user_address(self, value: str) -> None:
        self.config.user_address = str(value).strip()
        self.save()

    def set_user_faculty(self, value: str) -> None:
        self.config.user_faculty = str(value).strip()
        self.save()

    def set_has_car(self, value: bool) -> None:
        self.config.has_car = bool(value)
        self.save()

    def set_semester_start(self, value: str) -> None:
        normalized_value = str(value).strip()
        if is_valid_date_text(normalized_value):
            self.config.semester_start = normalized_value
        self.save()

    def set_first_week_even(self, value: bool) -> None:
        self.config.first_week_even = bool(value)
        self.save()

    def set_travel_time(self, value: int) -> None:
        self.config.travel_time = normalize_duration_minutes(value)
        self.save()

    def set_auto_alarm_enabled(self, value: bool) -> None:
        self.config.auto_alarm_enabled = bool(value)
        self.save()

    def set_auto_alarm_refresh_hour(self, value: int) -> None:
        self.config.auto_alarm_refresh_hour = max(0, min(23, int(value)))
        self.save()

    def set_auto_alarm_recheck_lead_minutes(self, value: int) -> None:
        self.config.auto_alarm_recheck_lead_minutes = normalize_duration_minutes(value)
        self.save()
