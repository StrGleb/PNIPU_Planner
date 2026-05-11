import json
import pathlib
from models.user_config import UserConfig

def _storage_path() -> pathlib.Path:
    """
    ~/.pnipu_planner/config.json
    Работает на Windows, Linux, macOS и Android (Flet).
    На Android Path.home() → /data/user/0/<pkg>/files/
    """
    d = pathlib.Path.home() / ".pnipu_planner"
    d.mkdir(parents=True, exist_ok=True)
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
            with open(self._path, encoding="utf-8") as f:
                return UserConfig.from_dict(json.load(f))
        except Exception:
            return UserConfig()

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)


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