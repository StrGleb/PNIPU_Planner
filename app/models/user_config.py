from dataclasses import dataclass

@dataclass
class UserConfig:
    theme: str = "system" # "light" | "dark" | "system"
    user_name: str = ""
    get_together_time: int = 0 # минут на сборы
    user_address: str = ""
    user_faculty: str = ""
    has_car: bool = False
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
            "has_car": self.has_car,
            "semester_start": self.semester_start,
            "first_week_even": self.first_week_even,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserConfig":
        return cls(
            theme = d.get("theme", "system"),
            user_name = d.get("user_name", ""),
            get_together_time = int(d.get("get_together_time", 0)),
            user_address = d.get("user_address", ""),
            user_faculty = d.get("user_faculty", ""),
            has_car = bool(d.get("has_car", False)),
            semester_start = d.get("semester_start", "30.03.2026"),
            first_week_even = bool(d.get("first_week_even", False)),
        )