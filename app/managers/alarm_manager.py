import threading
from time import sleep
from datetime import datetime
from typing import Callable
from models.alarm_model import Alarm

class AlarmManager:
    """
    Хранит список будильников и запускает фоновый поток,
    который каждую секунду проверяет, не пора ли звонить.
    """

    def __init__(self):
        self.alarms: list[Alarm] = []
        self._fired_keys: set[str] = set()   # чтобы не звонить дважды в одну минуту
        self._on_trigger: Callable[[Alarm], None] | None = None
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────────
    def add(self, alarm: Alarm) -> None:
        with self._lock:
            self.alarms.append(alarm)
            self.alarms.sort(key=lambda a: (a.hour, a.minute))

    def remove(self, alarm_id: str) -> None:
        with self._lock:
            self.alarms = [a for a in self.alarms if a.id != alarm_id]

    def toggle(self, alarm_id: str) -> None:
        with self._lock:
            for a in self.alarms:
                if a.id == alarm_id:
                    a.enabled = not a.enabled
                    break

    def set_trigger_callback(self, callback: Callable[[Alarm], None]) -> None:
        """Вызывается, когда будильник сработал."""
        self._on_trigger = callback

    def start_background_checker(self) -> None:
        t = threading.Thread(target=self._check_loop, daemon=True)
        t.start()

    # ── Internal ───────────────────────────────────────────────────────────
    def _check_loop(self) -> None:
        # !!!НА ДАННЫЙ МОМЕНТ НЕ РАБОТАЕТ!!!
        while True:
            now = datetime.now()
            key = f"{now.hour}:{now.minute}"

            with self._lock:
                alarms_copy = list(self.alarms)

            for alarm in alarms_copy:
                fire_key = f"{alarm.id}:{key}"
                if alarm.matches_now(now.hour, now.minute) and fire_key not in self._fired_keys:
                    self._fired_keys.add(fire_key)
                    if self._on_trigger:
                        self._on_trigger(alarm)

            # Очищаем старые ключи (оставляем только текущую минуту)
            self._fired_keys = {k for k in self._fired_keys if k.endswith(key)}

            sleep(1)
