from dataclasses import dataclass

@dataclass
class UserConfig:
    theme: str = "system" # "light" | "dark" | "system"
    user_name: str = ""
    get_together_time: int = 0 # минут на сборы
    travel_time: int = 0 # минут от дома до ВУЗа
    user_address: str = ""
    user_faculty: str = "ЭТФ - Электротехнический факультет"
    transport_type: str = "public_transport" # "driving" | "public_transport" | "pedestrian"
    # Начало семестра и чётность первой недели
    semester_start: str = "30.03.2026" # DD.MM.YYYY
    first_week_even: bool = False # False = первая неделя нечётная

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "user_name": self.user_name,
            "get_together_time": self.get_together_time,
            "user_address": self.user_address,
            "user_faculty": self.user_faculty,
            "transport_type": self.transport_type,
            "semester_start": self.semester_start,
            "first_week_even": self.first_week_even,
            "travel_time": self.travel_time,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserConfig":
        return cls(
            theme = d.get("theme", "system"),
            user_name = d.get("user_name", ""),
            get_together_time = int(d.get("get_together_time", 0)),
            user_address = d.get("user_address", ""),
            user_faculty = d.get("user_faculty", "ЭТФ - Электротехнический факультет"),
            transport_type = d.get("transport_type", "public_transport"),
            semester_start = d.get("semester_start", "30.03.2026"),
            first_week_even = bool(d.get("first_week_even", False)),
            travel_time = int(d.get("travel_time", 0)),
        )