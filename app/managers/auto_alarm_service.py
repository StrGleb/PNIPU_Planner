import datetime
import logging
import threading
from time import sleep

from bridges.planner_bridge import (
    compute_buffered_alarm_minutes,
    normalize_duration_minutes,
    select_next_lesson_index,
    time_to_minutes,
)
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager
from managers.planner_manager import PlannerManager
from models.alarm_model import Alarm, SOURCE_AUTO_SCHEDULE
from models.lesson_model import ENTRY_TYPE_EVENT, Lesson
from utils.campus_locations import FACULTIES_COORDS

logger = logging.getLogger(__name__)

_ROUTE_RECHECK_COOLDOWN_MINUTES = 10
_ALARM_BUFFER_MINUTES = 10
_UPCOMING_HORIZON_DAYS = 60


class AutoAlarmService:
    def __init__(
        self,
        alarm_manager: AlarmManager,
        config_manager: ConfigManager,
        planner_manager: PlannerManager,
    ) -> None:
        self._alarm_manager = alarm_manager
        self._config_manager = config_manager
        self._planner_manager = planner_manager
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        if self._config_manager.config.auto_alarm_enabled:
            self.sync_next_upcoming(force = False)

        self._thread = threading.Thread(target = self._loop, daemon = True)
        self._thread.start()

    def sync_tomorrow(self, force: bool = False) -> str:
        now = datetime.datetime.now()
        tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days = 1), datetime.time.min)
        return self.sync_next_upcoming(force = force, from_datetime = tomorrow)

    def sync_next_upcoming(
        self,
        force: bool = False,
        from_datetime: datetime.datetime | None = None,
    ) -> str:
        cfg = self._config_manager.config
        if not cfg.auto_alarm_enabled and not force:
            return "disabled"

        if cfg.get_together_time <= 0:
            return "missing_prep"

        if cfg.travel_time <= 0:
            return "missing_travel"

        now = from_datetime or datetime.datetime.now()
        candidate = self._select_next_candidate(now)
        if candidate is None:
            self._alarm_manager.clear_auto_schedule_alarms()
            return "no_upcoming_entries"

        target_date, lesson = candidate
        alarm = self._build_auto_alarm(target_date, lesson, allow_live = False)
        if alarm is None:
            self._alarm_manager.clear_auto_schedule_alarms()
            return "invalid_lesson_time"

        self._alarm_manager.replace_auto_schedule_alarms([alarm])
        return "scheduled"

    def handle_alarm_triggered(
        self,
        alarm: Alarm,
        fired_at: datetime.datetime | None = None,
    ) -> str:
        if not alarm.is_auto_schedule:
            return "ignored"

        fire_time = fired_at or datetime.datetime.now()
        self._alarm_manager.clear_auto_schedule_alarms()
        next_start = fire_time + datetime.timedelta(minutes = 1)
        return self.sync_next_upcoming(force = True, from_datetime = next_start)

    def handle_planner_change(self) -> str:
        if not self._config_manager.config.auto_alarm_enabled:
            return "disabled"
        return self.sync_next_upcoming(force = False)

    def disable(self) -> None:
        self._alarm_manager.clear_auto_schedule_alarms()

    def recheck_upcoming_alarm(self, now: datetime.datetime | None = None) -> str:
        cfg = self._config_manager.config
        if not cfg.auto_alarm_enabled:
            return "disabled"

        now = now or datetime.datetime.now()
        today_text = now.strftime("%d.%m.%Y")
        alarms = [
            alarm
            for alarm in self._alarm_manager.get_auto_schedule_alarms()
            if alarm.enabled and alarm.target_date == today_text
        ]
        if not alarms:
            return "no_alarm_today"

        alarm = min(alarms, key = lambda item: (item.hour, item.minute))
        alarm_minutes = alarm.hour * 60 + alarm.minute
        now_minutes = now.hour * 60 + now.minute
        minutes_until_alarm = alarm_minutes - now_minutes
        if minutes_until_alarm < 0 or minutes_until_alarm > cfg.auto_alarm_recheck_lead_minutes:
            return "outside_recheck_window"

        if not self._can_recheck_again(alarm, now):
            return "cooldown"

        lesson = self._find_alarm_lesson(alarm)
        if lesson is None:
            return "lesson_missing"

        live_travel_minutes = self._resolve_travel_minutes(lesson, allow_live = True)
        if live_travel_minutes <= 0:
            alarm.rechecked_at = now.strftime("%d.%m.%Y %H:%M")
            self._alarm_manager.update_alarm_instance(alarm)
            return "live_route_unavailable"

        was_shifted = False
        if live_travel_minutes > alarm.route_minutes:
            delta = live_travel_minutes - alarm.route_minutes
            new_alarm_minutes = alarm_minutes - delta
            while new_alarm_minutes < 0:
                new_alarm_minutes += 24 * 60
            alarm.hour = new_alarm_minutes // 60
            alarm.minute = new_alarm_minutes % 60
            alarm.route_minutes = live_travel_minutes
            was_shifted = True

        alarm.rechecked_at = now.strftime("%d.%m.%Y %H:%M")
        self._alarm_manager.update_alarm_instance(alarm)
        return "shifted" if was_shifted else "checked"

    def _loop(self) -> None:
        while True:
            try:
                now = datetime.datetime.now()
                self._cleanup_expired_auto_alarms(now.date())
                self.recheck_upcoming_alarm(now)
            except Exception:
                logger.exception("Auto alarm loop failed")
            sleep(30)

    def _select_next_candidate(
        self,
        now: datetime.datetime,
    ) -> tuple[datetime.date, Lesson] | None:
        candidates: list[Lesson] = []
        date_strings: list[str] = []
        start_minutes: list[int] = []

        for lesson in self._planner_manager.get_all_lessons():
            date_delta = (lesson.date - now.date()).days
            if date_delta < 0 or date_delta > _UPCOMING_HORIZON_DAYS:
                continue

            lesson_minutes = time_to_minutes(lesson.time_start)
            if lesson_minutes < 0:
                continue

            candidates.append(lesson)
            date_strings.append(lesson.date_str)
            start_minutes.append(lesson_minutes)

        if not candidates:
            return None

        selected_index = select_next_lesson_index(date_strings, start_minutes, now)
        if selected_index < 0:
            return None

        selected_lesson = candidates[selected_index]
        return selected_lesson.date, selected_lesson

    def _build_auto_alarm(
        self,
        target_date: datetime.date,
        lesson: Lesson,
        allow_live: bool,
    ) -> Alarm | None:
        cfg = self._config_manager.config
        lesson_minutes = time_to_minutes(lesson.time_start)
        if lesson_minutes < 0:
            return None

        travel_minutes = self._resolve_travel_minutes(lesson, allow_live = allow_live)
        if travel_minutes <= 0:
            travel_minutes = normalize_duration_minutes(cfg.travel_time)

        alarm_minutes = compute_buffered_alarm_minutes(
            lesson_minutes,
            cfg.get_together_time,
            travel_minutes,
            _ALARM_BUFFER_MINUTES,
        )

        return Alarm(
            hour = alarm_minutes // 60,
            minute = alarm_minutes % 60,
            source = SOURCE_AUTO_SCHEDULE,
            target_date = target_date.strftime("%d.%m.%Y"),
            lesson_time = lesson.time_start,
            route_minutes = travel_minutes,
            subject = lesson.subject,
            destination = lesson.address or lesson.location_text,
            entry_type = lesson.entry_type,
        )

    def _find_alarm_lesson(self, alarm: Alarm) -> Lesson | None:
        if not alarm.target_date:
            return None

        try:
            alarm_date = datetime.datetime.strptime(alarm.target_date, "%d.%m.%Y").date()
        except ValueError:
            return None

        for lesson in self._planner_manager.get_lessons_for_date(alarm_date):
            if lesson.time_start != alarm.lesson_time:
                continue
            if alarm.subject and lesson.subject != alarm.subject:
                continue
            return lesson
        return None

    def _cleanup_expired_auto_alarms(self, today: datetime.date) -> None:
        auto_alarms = self._alarm_manager.get_auto_schedule_alarms()
        if not auto_alarms:
            return

        valid_alarms: list[Alarm] = []
        changed = False
        for alarm in auto_alarms:
            if not alarm.target_date:
                changed = True
                continue

            try:
                alarm_date = datetime.datetime.strptime(alarm.target_date, "%d.%m.%Y").date()
            except ValueError:
                changed = True
                continue

            if alarm_date < today:
                changed = True
                continue
            valid_alarms.append(alarm)

        if changed:
            self._alarm_manager.replace_auto_schedule_alarms(valid_alarms)

    def _can_recheck_again(self, alarm: Alarm, now: datetime.datetime) -> bool:
        if not alarm.rechecked_at:
            return True

        try:
            last_check = datetime.datetime.strptime(alarm.rechecked_at, "%d.%m.%Y %H:%M")
        except ValueError:
            return True

        delta = now - last_check
        return delta.total_seconds() >= _ROUTE_RECHECK_COOLDOWN_MINUTES * 60

    def _resolve_travel_minutes(self, lesson: Lesson, allow_live: bool) -> int:
        cfg = self._config_manager.config
        fallback_minutes = normalize_duration_minutes(cfg.travel_time)
        if not allow_live:
            return fallback_minutes

        live_minutes = self._resolve_live_route_minutes(lesson)
        if live_minutes and live_minutes > 0:
            return live_minutes
        return fallback_minutes

    def _resolve_live_route_minutes(self, lesson: Lesson) -> int | None:
        cfg = self._config_manager.config
        user_address = str(cfg.user_address).strip()
        if not user_address:
            return None

        destination_coordinates: tuple[float, float] | None = None
        destination_address = ""
        if lesson.entry_type == ENTRY_TYPE_EVENT and lesson.address:
            destination_address = lesson.address
        else:
            faculty_name = str(cfg.user_faculty).strip()
            faculty_destination = FACULTIES_COORDS.get(faculty_name)
            if faculty_destination is not None:
                destination_coordinates = (faculty_destination[0], faculty_destination[1])

        try:
            from utils.geocoder_utils import get_coordinates_by_address
            from utils.route_utis import get_route
        except Exception:
            logger.exception("Route utilities are unavailable")
            return None

        address_query = user_address
        if "перм" not in address_query.lower():
            address_query = f"Пермь, {address_query}"

        coordinates = get_coordinates_by_address(address_query)
        if not coordinates:
            return None

        start = (coordinates[1], coordinates[0])

        if destination_address:
            destination_query = destination_address
            if "перм" not in destination_query.lower():
                destination_query = f"Пермь, {destination_query}"
            destination_coordinates_raw = get_coordinates_by_address(destination_query)
            if not destination_coordinates_raw:
                return None
            end = (destination_coordinates_raw[1], destination_coordinates_raw[0])
        elif destination_coordinates is not None:
            end = (destination_coordinates[0], destination_coordinates[1])
        else:
            return None

        transport = "driving" if cfg.has_car else "public_transport"
        route = get_route(start, end, transport)
        if not route:
            return None

        if isinstance(route, dict):
            return normalize_duration_minutes(route.get("duration_min", 0))

        if isinstance(route, list) and len(route) >= 2:
            return normalize_duration_minutes(int(route[1]) // 60)

        return None
