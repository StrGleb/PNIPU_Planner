import json
import pathlib
import sys
import tempfile
import os
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
            return UserConfig()
        try:
            with open(self._path, encoding = "utf-8") as f:
                return UserConfig.from_dict(json.load(f))
        except Exception:
            return UserConfig()

    def save(self) -> None:
        with open(self._path, "w", encoding = "utf-8") as f:
            json.dump(self.config.to_dict(), f, ensure_ascii = False, indent = 2)


    # ── Набор сеттеров ─────────────────────────
    def set_theme(self, value: str) -> None:
        self.config.theme = value
        self.save()

    def set_user_name(self, value: str) -> None:
        self.config.user_name = value
        self.save()

    def set_get_together_time(self, value: int) -> None:
        self.config.get_together_time = value
        self.save()

    def set_user_address(self, value: str) -> None:
        self.config.user_address = value
        self.save()

    def set_user_faculty(self, value: str) -> None:
        self.config.user_faculty = value
        self.save()
    
    def set_transport_type(self, value: str) -> None:
        self.config.transport_type = value
        self.save()

    def set_semester_start(self, value: str) -> None:
        self.config.semester_start = value
        self.save()

    def set_first_week_even(self, value: bool) -> None:
        self.config.first_week_even = value
        self.save()

    def set_travel_time(self, value: int) -> None:
        self.config.travel_time = value
        self.save()