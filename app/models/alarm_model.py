from dataclasses import dataclass, field
import uuid


@dataclass
class Alarm:
    hour: int
    minute: int
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    def matches_now(self, current_hour: int, current_minute: int) -> bool:
        return self.enabled and self.hour == current_hour and self.minute == current_minute
