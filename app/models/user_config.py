from dataclasses import dataclass, field


VALID_TRANSPORT_TYPES = {"driving", "public_transport", "pedestrian"}


@dataclass
class UserConfig:
    theme: str = "system"
    user_name: str = ""
    get_together_time: int = 0
    travel_time: int = 0
    user_address: str = ""
    user_faculty: str = "ЭТФ - Электротехнический факультет"
    transport_type: str = "public_transport"
    semester_start: str = "30.03.2026"
    first_week_even: bool = False
    auto_alarm_enabled: bool = False
    auto_alarm_refresh_hour: int = 21
    auto_alarm_recheck_lead_minutes: int = 60
    user_longitude: float | None = None
    user_latitude: float | None = None
    weather_cached_at: str = ""
    weather_payload: dict = field(default_factory = dict)

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "user_name": self.user_name,
            "get_together_time": self.get_together_time,
            "travel_time": self.travel_time,
            "user_address": self.user_address,
            "user_faculty": self.user_faculty,
            "transport_type": self.transport_type,
            "semester_start": self.semester_start,
            "first_week_even": self.first_week_even,
            "auto_alarm_enabled": self.auto_alarm_enabled,
            "auto_alarm_refresh_hour": self.auto_alarm_refresh_hour,
            "auto_alarm_recheck_lead_minutes": self.auto_alarm_recheck_lead_minutes,
            "user_longitude": self.user_longitude,
            "user_latitude": self.user_latitude,
            "weather_cached_at": self.weather_cached_at,
            "weather_payload": self.weather_payload,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserConfig":
        transport_type = str(data.get("transport_type", "")).strip()
        if transport_type not in VALID_TRANSPORT_TYPES:
            transport_type = "public_transport"

        weather_payload = data.get("weather_payload", {})
        if not isinstance(weather_payload, dict):
            weather_payload = {}

        def _parse_float(value):
            try:
                if value in {"", None}:
                    return None
                return float(value)
            except (TypeError, ValueError):
                return None

        return cls(
            theme = str(data.get("theme", "system")),
            user_name = str(data.get("user_name", "")),
            get_together_time = int(data.get("get_together_time", 0)),
            travel_time = int(data.get("travel_time", 0)),
            user_address = str(data.get("user_address", "")),
            user_faculty = str(data.get("user_faculty", "ЭТФ - Электротехнический факультет")),
            transport_type = transport_type,
            semester_start = str(data.get("semester_start", "30.03.2026")),
            first_week_even = bool(data.get("first_week_even", False)),
            auto_alarm_enabled = bool(data.get("auto_alarm_enabled", False)),
            auto_alarm_refresh_hour = int(data.get("auto_alarm_refresh_hour", 21)),
            auto_alarm_recheck_lead_minutes = int(data.get("auto_alarm_recheck_lead_minutes", 60)),
            user_longitude = _parse_float(data.get("user_longitude")),
            user_latitude = _parse_float(data.get("user_latitude")),
            weather_cached_at = str(data.get("weather_cached_at", "")),
            weather_payload = weather_payload,
        )
