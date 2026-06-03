import json
import pathlib
import sys
import tempfile

from bridges.planner_bridge import (
    is_valid_date_text,
    normalize_duration_minutes,
    normalize_hour_24,
    normalize_theme,
)
from models.user_config import UserConfig, VALID_TRANSPORT_TYPES


def _storage_path() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        cache_dir = pathlib.Path(tempfile.gettempdir())
        base_dir = cache_dir.parent / "files"
        directory = base_dir / ".pnipu_planner"
    else:
        directory = pathlib.Path.home() / ".pnipu_planner"

    directory.mkdir(parents = True, exist_ok = True)
    return directory / "config.json"


class ConfigManager:
    def __init__(self):
        self._path = _storage_path()
        self.config: UserConfig = self._load()

        if not self._path.exists():
            self.save()

    def _load(self) -> UserConfig:
        if not self._path.exists():
            return self._sanitize(UserConfig())
        try:
            with open(self._path, encoding = "utf-8") as file:
                return self._sanitize(UserConfig.from_dict(json.load(file)))
        except Exception:
            return self._sanitize(UserConfig())

    def _sanitize_transport_type(self, value: str) -> str:
        normalized = str(value).strip()
        if normalized in VALID_TRANSPORT_TYPES:
            return normalized
        return UserConfig().transport_type

    def _sanitize_optional_coordinate(self, value) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sanitize(self, config: UserConfig) -> UserConfig:
        defaults = UserConfig()
        semester_start = str(config.semester_start).strip()
        if not is_valid_date_text(semester_start):
            semester_start = defaults.semester_start

        refresh_hour = normalize_hour_24(getattr(config, "auto_alarm_refresh_hour", defaults.auto_alarm_refresh_hour))
        recheck_lead = normalize_duration_minutes(
            getattr(config, "auto_alarm_recheck_lead_minutes", defaults.auto_alarm_recheck_lead_minutes)
        )
        user_faculty = str(getattr(config, "user_faculty", defaults.user_faculty)).strip() or defaults.user_faculty
        transport_type = self._sanitize_transport_type(
            getattr(config, "transport_type", ""),
        )
        user_longitude = self._sanitize_optional_coordinate(getattr(config, "user_longitude", None))
        user_latitude = self._sanitize_optional_coordinate(getattr(config, "user_latitude", None))

        return UserConfig(
            theme = normalize_theme(config.theme),
            user_name = str(config.user_name).strip(),
            get_together_time = normalize_duration_minutes(config.get_together_time),
            travel_time = normalize_duration_minutes(config.travel_time),
            user_address = str(config.user_address).strip(),
            user_longitude = user_longitude,
            user_latitude = user_latitude,
            user_faculty = user_faculty,
            transport_type = transport_type,
            semester_start = semester_start,
            first_week_even = bool(config.first_week_even),
            auto_alarm_enabled = bool(getattr(config, "auto_alarm_enabled", False)),
            auto_alarm_refresh_hour = refresh_hour,
            auto_alarm_recheck_lead_minutes = recheck_lead,
        )

    def save(self) -> None:
        self.config = self._sanitize(self.config)
        with open(self._path, "w", encoding = "utf-8") as file:
            json.dump(self.config.to_dict(), file, ensure_ascii = False, indent = 2)

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
        normalized_value = str(value).strip()
        if self.config.user_address != normalized_value:
            self.config.user_longitude = None
            self.config.user_latitude = None
        self.config.user_address = normalized_value
        self.save()

    def set_user_coordinates(self, longitude: float | None, latitude: float | None) -> None:
        self.config.user_longitude = self._sanitize_optional_coordinate(longitude)
        self.config.user_latitude = self._sanitize_optional_coordinate(latitude)
        self.save()

    def set_user_faculty(self, value: str) -> None:
        self.config.user_faculty = str(value).strip()
        self.save()

    def set_transport_type(self, value: str) -> None:
        self.config.transport_type = self._sanitize_transport_type(value)
        self.save()

    def set_has_car(self, value: bool) -> None:
        self.config.transport_type = "driving" if bool(value) else "public_transport"
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
        self.config.auto_alarm_refresh_hour = normalize_hour_24(value)
        self.save()

    def set_auto_alarm_recheck_lead_minutes(self, value: int) -> None:
        self.config.auto_alarm_recheck_lead_minutes = normalize_duration_minutes(value)
        self.save()
