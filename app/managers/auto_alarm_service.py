import datetime
import logging

from bridges.planner_bridge import (
    collect_alarm_indices_on_or_after_date,
    compute_buffered_alarm_minutes,
    normalize_duration_minutes,
    select_next_lesson_index,
    time_to_minutes,
)
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager
from managers.planner_manager import PlannerManager
from models.alarm_model import Alarm, SOURCE_AUTO_SCHEDULE, WEEK_ANY
from models.lesson_model import ENTRY_TYPE_EVENT, Lesson
from utils.campus_locations import FACULTIES_COORDS

logger = logging.getLogger(__name__)

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

    def start(self) -> None:
        self._cleanup_expired_auto_alarms(datetime.datetime.now())

    def sync_tomorrow(self, force: bool = False) -> str:
        now = datetime.datetime.now()
        tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days = 1), datetime.time.min)
        return self.sync_next_upcoming(force = force, from_datetime = tomorrow)

    def sync_week_ahead(self) -> tuple[str, int]:
        """
        Генерирует авто-будильники для всех занятий на ближайшие 7 дней.
        Использует сохранённое время в пути (без live API-вызовов).
        """
        cfg = self._config_manager.config
        if cfg.get_together_time <= 0:
            return "missing_prep", 0

        travel_minutes = normalize_duration_minutes(cfg.travel_time)
        if travel_minutes <= 0:
            return "route_unavailable", 0

        now = datetime.datetime.now()
        cutoff = now.date() + datetime.timedelta(days = 7)
        now_minutes = now.hour * 60 + now.minute

        lessons = self._planner_manager.get_all_lessons()
        if not lessons:
            return "no_upcoming_entries", 0

        upcoming: list[Lesson] = []
        for lesson in lessons:
            if lesson.date < now.date() or lesson.date > cutoff:
                continue
            if lesson.date == now.date() and time_to_minutes(lesson.time_start) <= now_minutes:
                continue
            upcoming.append(lesson)

        if not upcoming:
            return "no_upcoming_entries", 0

        count = 0
        for lesson in upcoming:
            lesson_minutes = time_to_minutes(lesson.time_start)
            if lesson_minutes < 0:
                continue

            alarm_minutes = compute_buffered_alarm_minutes(
                lesson_minutes,
                cfg.get_together_time,
                travel_minutes,
                _ALARM_BUFFER_MINUTES,
            )

            self._alarm_manager.add(
                Alarm(
                    hour = alarm_minutes // 60,
                    minute = alarm_minutes % 60,
                    days = [],
                    week_type = WEEK_ANY,
                    target_date = lesson.date.strftime("%d.%m.%Y"),
                )
            )
            count += 1

        return "scheduled", count
    

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

        now = from_datetime or datetime.datetime.now()
        candidate = self._select_next_candidate(now)
        if candidate is None:
            self._alarm_manager.clear_auto_schedule_alarms()
            return "no_upcoming_entries"

        target_date, lesson = candidate
        alarm = self._build_auto_alarm(target_date, lesson, allow_live = True)
        if alarm is None:
            self._alarm_manager.clear_auto_schedule_alarms()
            return "route_unavailable"

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

    def _select_next_candidate(
        self,
        now: datetime.datetime,
    ) -> tuple[datetime.date, Lesson] | None:
        lessons = self._planner_manager.get_all_lessons()
        if not lessons:
            return None

        selected_index = select_next_lesson_index(
            [lesson.date_str for lesson in lessons],
            [time_to_minutes(lesson.time_start) for lesson in lessons],
            now,
            max_days_ahead = _UPCOMING_HORIZON_DAYS,
        )
        if selected_index < 0:
            return None

        selected_lesson = lessons[selected_index]
        return selected_lesson.date, selected_lesson

    def _build_auto_alarm(
        self,
        target_date: datetime.date,
        lesson: Lesson,
        allow_live: bool,
        source: str = SOURCE_AUTO_SCHEDULE,
    ) -> Alarm | None:
        cfg = self._config_manager.config
        lesson_minutes = time_to_minutes(lesson.time_start)
        if lesson_minutes < 0:
            return None

        travel_minutes = self._resolve_travel_minutes(lesson, allow_live = allow_live)
        if travel_minutes <= 0:
            return None

        alarm_minutes = compute_buffered_alarm_minutes(
            lesson_minutes,
            cfg.get_together_time,
            travel_minutes,
            _ALARM_BUFFER_MINUTES,
        )

        return Alarm(
            hour = alarm_minutes // 60,
            minute = alarm_minutes % 60,
            source = source,
            target_date = target_date.strftime("%d.%m.%Y"),
            lesson_time = lesson.time_start,
            route_minutes = travel_minutes,
            subject = lesson.subject,
            destination = lesson.address or lesson.location_text,
            entry_type = lesson.entry_type,
        )

    def _cleanup_expired_auto_alarms(self, now: datetime.datetime) -> None:
        auto_alarms = self._alarm_manager.get_auto_schedule_alarms()
        if not auto_alarms:
            return

        indices = collect_alarm_indices_on_or_after_date(
            [alarm.target_date for alarm in auto_alarms],
            now.date(),
        )
        valid_alarms = [auto_alarms[index] for index in indices]
        still_upcoming: list[Alarm] = []
        for alarm in valid_alarms:
            if not alarm.target_date:
                continue
            try:
                alarm_datetime = datetime.datetime.strptime(alarm.target_date, "%d.%m.%Y").replace(
                    hour = alarm.hour,
                    minute = alarm.minute,
                )
            except ValueError:
                continue
            if alarm_datetime >= now:
                still_upcoming.append(alarm)

        if len(still_upcoming) != len(auto_alarms):
            self._alarm_manager.replace_auto_schedule_alarms(still_upcoming)

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
            return

        address_query = user_address
        if "перм" not in address_query.lower():
            address_query = f"Пермь, {address_query}"

        coordinates = get_coordinates_by_address(address_query)
        if not coordinates:
            return

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

        transport = str(getattr(cfg, "transport_type", "")).strip()
        if transport not in {"driving", "public_transport", "pedestrian"}:
            return
        route = get_route(start, end, transport)
        if not route:
            return None

        if isinstance(route, dict):
            return normalize_duration_minutes(route.get("duration_min", 0))

        if isinstance(route, list) and len(route) >= 2:
            return normalize_duration_minutes(int(route[1]) // 60)

        return None
