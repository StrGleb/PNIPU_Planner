import json
import pathlib
import sys
import os
from models.user_config import UserConfig

def _storage_path() -> pathlib.Path:
    """
    ~/.pnipu_planner/config.json
    Работает на Windows, Linux, macOS и Android (Flet).
    """
    # Проверяем, запущены ли мы на Android
    if hasattr(sys, "getandroidapilevel"):
        # На Android HOME часто указывает на закрытую систему /data.
        # Берем FILESDIR (внутреннюю песочницу приложения), где запись разрешена всегда.
        base_dir = os.environ.get("FILESDIR") or os.environ.get("HOME")
        
        # Если переменные не определились или ведут в корень /data
        if not base_dir or base_dir in ("/data", "/"):
            # Безопасный резервный вариант — папка самого проекта в песочнице
            base_dir = pathlib.Path(__file__).parent.parent
            
        d = pathlib.Path(base_dir) / ".pnipu_planner"
    else:
        # На Windows/macOS/Linux используем стандартную домашнюю папку пользователя
        d = pathlib.Path.home() / ".pnipu_planner"

    d.mkdir(parents = True, exist_ok = True)
    return d / "config.json"


class ConfigManager:
    """Хранит настройки пользователя. Читает/пишет JSON"""
    def __init__(self):
        self._path = _storage_path()
        self.config: UserConfig = self._load()

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

    def set_has_car(self, value: bool) -> None:
        self.config.has_car = value
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