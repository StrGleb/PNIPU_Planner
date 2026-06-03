from dataclasses import dataclass


VALID_TRANSPORT_TYPES = {"driving", "public_transport", "pedestrian"}


@dataclass
class UserConfig:
    theme: str = "system"  # "light" | "dark" | "system"
    user_name: str = ""
    get_together_time: int = 0
    travel_time: int = 0
    user_address: str = ""
    user_longitude: float | None = None
    user_latitude: float | None = None
    user_faculty: str = "ЭТФ - Электротехнический факультет"
    transport_type: str = "public_transport"
    semester_start: str = "30.03.2026"  # DD.MM.YYYY
    first_week_even: bool = False
    auto_alarm_enabled: bool = False
    auto_alarm_refresh_hour: int = 21
    auto_alarm_recheck_lead_minutes: int = 60

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "user_name": self.user_name,
            "get_together_time": self.get_together_time,
            "user_address": self.user_address,
            "user_longitude": self.user_longitude,
            "user_latitude": self.user_latitude,
            "user_faculty": self.user_faculty,
            "transport_type": self.transport_type,
            "semester_start": self.semester_start,
            "first_week_even": self.first_week_even,
            "travel_time": self.travel_time,
            "auto_alarm_enabled": self.auto_alarm_enabled,
            "auto_alarm_refresh_hour": self.auto_alarm_refresh_hour,
            "auto_alarm_recheck_lead_minutes": self.auto_alarm_recheck_lead_minutes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserConfig":
        def _parse_optional_float(value) -> float | None:
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        transport_type = str(d.get("transport_type", "")).strip()
        if transport_type not in VALID_TRANSPORT_TYPES:
            transport_type = "public_transport"

        return cls(
            theme = d.get("theme", "system"),
            user_name = d.get("user_name", ""),
            get_together_time = int(d.get("get_together_time", 0)),
            user_address = d.get("user_address", ""),
            user_longitude = _parse_optional_float(d.get("user_longitude")),
            user_latitude = _parse_optional_float(d.get("user_latitude")),
            user_faculty = d.get("user_faculty", "ЭТФ - Электротехнический факультет"),
            transport_type = transport_type,
            semester_start = d.get("semester_start", "30.03.2026"),
            first_week_even = bool(d.get("first_week_even", False)),
            travel_time = int(d.get("travel_time", 0)),
            auto_alarm_enabled = bool(d.get("auto_alarm_enabled", False)),
            auto_alarm_refresh_hour = int(d.get("auto_alarm_refresh_hour", 21)),
            auto_alarm_recheck_lead_minutes = int(d.get("auto_alarm_recheck_lead_minutes", 60)),
        )
