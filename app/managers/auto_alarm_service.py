import datetime
import logging
import threading

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
from models.alarm_model import ALARM_KIND_REMINDER, ALARM_KIND_ROUTE, Alarm, SOURCE_AUTO_SCHEDULE
from models.lesson_model import ENTRY_TYPE_EVENT, Lesson, normalize_event_reminder_lead_minutes
from utils.campus_locations import FACULTIES_COORDS

logger = logging.getLogger(__name__)

_ALARM_BUFFER_MINUTES = 10
_AUTO_ALARM_LOOKAHEAD_DAYS = 60
_WEEK_AHEAD_DAYS = 7
_RECHECK_WINDOW_MINUTES = 120


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
        self._sync_lock = threading.RLock()
        self._planner_change_lock = threading.Lock()
        self._planner_change_running = False
        self._planner_change_pending_dates: set[datetime.date] | None = set()

    def start(self) -> None:
        with self._sync_lock:
            self._cleanup_expired_auto_alarms(datetime.datetime.now())

            if not self._config_manager.config.auto_alarm_enabled:
                return

            if self._alarm_manager.get_auto_schedule_alarms():
                return

            self.sync_next_upcoming(force = False)

    def sync_tomorrow(self, force: bool = False) -> str:
        with self._sync_lock:
            now = datetime.datetime.now()
            tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days = 1), datetime.time.min)
            return self.sync_next_upcoming(force = force, from_datetime = tomorrow)

    def sync_week_ahead(self) -> tuple[str, int]:
        with self._sync_lock:
            now = datetime.datetime.now()
            cutoff = now.date() + datetime.timedelta(days = _WEEK_AHEAD_DAYS)
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

            auto_alarms: list[Alarm] = []
            route_error_seen = False
            missing_prep_seen = False
            for lesson in upcoming:
                alarm, error_code = self._build_auto_alarm(lesson.date, lesson, allow_live = False)
                if alarm is not None:
                    auto_alarms.append(alarm)
                    continue
                if error_code == "missing_prep":
                    missing_prep_seen = True
                if error_code == "route_unavailable":
                    route_error_seen = True

            if auto_alarms:
                self._alarm_manager.replace_auto_schedule_alarms(auto_alarms)
                return "scheduled", len(auto_alarms)
            if missing_prep_seen:
                return "missing_prep", 0
            if route_error_seen:
                return "route_unavailable", 0
            return "no_upcoming_entries", 0

    def sync_next_upcoming(
        self,
        force: bool = False,
        from_datetime: datetime.datetime | None = None,
    ) -> str:
        with self._sync_lock:
            cfg = self._config_manager.config
            if not cfg.auto_alarm_enabled and not force:
                return "disabled"

            now = from_datetime or datetime.datetime.now()
            candidate = self._select_next_candidate(now)
            if candidate is None:
                self._alarm_manager.clear_auto_schedule_alarms()
                return "no_upcoming_entries"

            alarm, error_code = candidate
            if alarm is None:
                self._alarm_manager.clear_auto_schedule_alarms()
                return error_code or "no_upcoming_entries"

            self._alarm_manager.replace_auto_schedule_alarms([alarm])
            return "scheduled"

    def handle_alarm_triggered(
        self,
        alarm: Alarm,
        fired_at: datetime.datetime | None = None,
    ) -> str:
        with self._sync_lock:
            if not alarm.is_auto_schedule:
                return "ignored"

            fire_time = fired_at or datetime.datetime.now()
            self._alarm_manager.clear_auto_schedule_alarms()
            next_start = fire_time + datetime.timedelta(minutes = 1)
            return self.sync_next_upcoming(force = True, from_datetime = next_start)

    def handle_planner_change(self) -> str:
        with self._sync_lock:
            if not self._config_manager.config.auto_alarm_enabled:
                return "disabled"
            auto_alarms = self._alarm_manager.get_auto_schedule_alarms()
            if not auto_alarms:
                return self.sync_next_upcoming(force = False)
            return self._recheck_alarms_if_needed(auto_alarms, changed_dates = None)

    def handle_planner_change_for_dates(
        self,
        changed_dates: list[datetime.date] | None,
    ) -> str:
        with self._sync_lock:
            if not self._config_manager.config.auto_alarm_enabled:
                return "disabled"

            auto_alarms = self._alarm_manager.get_auto_schedule_alarms()
            if not auto_alarms:
                return self.sync_next_upcoming(force = False)
            return self._recheck_alarms_if_needed(auto_alarms, changed_dates = changed_dates)

    def enqueue_planner_change(
        self,
        changed_dates: list[datetime.date] | None = None,
    ) -> None:
        with self._planner_change_lock:
            self._planner_change_pending_dates = self._merge_changed_dates(
                self._planner_change_pending_dates,
                changed_dates,
            )
            if self._planner_change_running:
                return
            self._planner_change_running = True

        worker = threading.Thread(
            target = self._drain_planner_change_queue,
            daemon = True,
            name = "auto-alarm-planner-sync",
        )
        worker.start()

    def disable(self) -> None:
        with self._sync_lock:
            self._alarm_manager.clear_auto_schedule_alarms()

    def _drain_planner_change_queue(self) -> None:
        while True:
            with self._planner_change_lock:
                changed_dates = self._planner_change_pending_dates
                self._planner_change_pending_dates = set()

            try:
                if changed_dates is None:
                    self.handle_planner_change()
                else:
                    self.handle_planner_change_for_dates(list(changed_dates))
            except Exception:
                logger.exception("Failed to refresh auto alarms after planner change")

            with self._planner_change_lock:
                has_pending = self._planner_change_pending_dates is None or bool(self._planner_change_pending_dates)
                if has_pending:
                    continue
                self._planner_change_running = False
                return

    def _merge_changed_dates(
        self,
        current_dates: set[datetime.date] | None,
        new_dates: list[datetime.date] | None,
    ) -> set[datetime.date] | None:
        if current_dates is None or new_dates is None:
            return None

        merged = set(current_dates)
        normalized_dates = self._normalize_changed_dates(new_dates)
        if normalized_dates:
            merged.update(normalized_dates)
        return merged

    def _select_next_candidate(
        self,
        now: datetime.datetime,
    ) -> tuple[Alarm | None, str | None] | None:
        lessons = list(self._planner_manager.get_all_lessons())
        if not lessons:
            return None

        route_error_seen = False
        missing_prep_seen = False
        while lessons:
            selected_index = select_next_lesson_index(
                [lesson.date_str for lesson in lessons],
                [time_to_minutes(lesson.time_start) for lesson in lessons],
                now,
                max_days_ahead = _AUTO_ALARM_LOOKAHEAD_DAYS,
            )
            if selected_index < 0:
                break

            selected_lesson = lessons.pop(selected_index)
            alarm, error_code = self._build_auto_alarm(
                selected_lesson.date,
                selected_lesson,
                allow_live = True,
            )
            if alarm is not None:
                return alarm, None
            if error_code == "missing_prep":
                missing_prep_seen = True
            if error_code == "route_unavailable":
                route_error_seen = True

        if missing_prep_seen:
            return None, "missing_prep"
        if route_error_seen:
            return None, "route_unavailable"
        return None

    def _build_auto_alarm(
        self,
        target_date: datetime.date,
        lesson: Lesson,
        allow_live: bool,
        source: str = SOURCE_AUTO_SCHEDULE,
    ) -> tuple[Alarm | None, str | None]:
        cfg = self._config_manager.config
        lesson_minutes = time_to_minutes(lesson.time_start)
        if lesson_minutes < 0:
            return None, "invalid_lesson_time"

        if self._event_should_use_reminder(lesson):
            reminder_alarm = self._build_event_reminder_alarm(
                target_date = target_date,
                lesson = lesson,
                lesson_minutes = lesson_minutes,
                source = source,
            )
            return reminder_alarm, None

        if cfg.get_together_time <= 0:
            return None, "missing_prep"

        travel_minutes = self._resolve_travel_minutes(lesson, allow_live = allow_live)
        if travel_minutes <= 0:
            return None, "route_unavailable"

        alarm_minutes = compute_buffered_alarm_minutes(
            lesson_minutes,
            cfg.get_together_time,
            travel_minutes,
            _ALARM_BUFFER_MINUTES,
        )

        return (
            Alarm(
                hour = alarm_minutes // 60,
                minute = alarm_minutes % 60,
                source = source,
                target_date = target_date.strftime("%d.%m.%Y"),
                lesson_time = lesson.time_start,
                route_minutes = travel_minutes,
                subject = lesson.subject,
                destination = lesson.address or lesson.location_text,
                entry_type = lesson.entry_type,
                alarm_kind = ALARM_KIND_ROUTE,
            ),
            None,
        )

    def _build_event_reminder_alarm(
        self,
        target_date: datetime.date,
        lesson: Lesson,
        lesson_minutes: int,
        source: str,
    ) -> Alarm | None:
        if not getattr(lesson, "reminder_enabled", False):
            return None

        lead_minutes = normalize_event_reminder_lead_minutes(getattr(lesson, "reminder_lead_minutes", 60))
        alarm_minutes = compute_buffered_alarm_minutes(
            lesson_minutes,
            0,
            lead_minutes,
            0,
        )
        return Alarm(
            hour = alarm_minutes // 60,
            minute = alarm_minutes % 60,
            source = source,
            target_date = target_date.strftime("%d.%m.%Y"),
            lesson_time = lesson.time_start,
            route_minutes = 0,
            subject = lesson.subject,
            destination = lesson.address or lesson.location_text,
            entry_type = lesson.entry_type,
            alarm_kind = ALARM_KIND_REMINDER,
            lead_minutes = lead_minutes,
        )

    def _event_should_use_reminder(self, lesson: Lesson) -> bool:
        if lesson.entry_type != ENTRY_TYPE_EVENT:
            return False
        return self._event_has_prior_regular_lessons(lesson)

    def _event_has_prior_regular_lessons(self, lesson: Lesson) -> bool:
        event_start_minutes = time_to_minutes(lesson.time_start)
        if event_start_minutes < 0:
            return False

        for day_lesson in self._planner_manager.get_lessons_for_date(lesson.date):
            if day_lesson.id == lesson.id or day_lesson.entry_type == ENTRY_TYPE_EVENT:
                continue
            lesson_start_minutes = time_to_minutes(day_lesson.time_start)
            if 0 <= lesson_start_minutes < event_start_minutes:
                return True
        return False

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

    def _recheck_alarms_if_needed(
        self,
        auto_alarms: list[Alarm],
        changed_dates: list[datetime.date] | None,
    ) -> str:
        now = datetime.datetime.now()
        if not self._has_recheckable_alarm(auto_alarms, changed_dates, now):
            return "skipped"

        if len(auto_alarms) > 1:
            result, _ = self.sync_week_ahead()
            return result
        return self.sync_next_upcoming(force = False, from_datetime = now)

    def _has_recheckable_alarm(
        self,
        auto_alarms: list[Alarm],
        changed_dates: list[datetime.date] | None,
        now: datetime.datetime,
    ) -> bool:
        normalized_changed_dates = self._normalize_changed_dates(changed_dates)

        for alarm in auto_alarms:
            target_date = self._parse_alarm_target_date(alarm)
            if target_date is None:
                continue

            if normalized_changed_dates is not None:
                if target_date in normalized_changed_dates:
                    return True
                continue

            tomorrow = now.date() + datetime.timedelta(days = 1)
            if target_date != tomorrow:
                continue
            if self._is_within_recheck_window(alarm, now):
                return True
        return False

    def _normalize_changed_dates(
        self,
        changed_dates: list[datetime.date] | None,
    ) -> set[datetime.date] | None:
        if changed_dates is None:
            return None
        return {
            changed_date
            for changed_date in changed_dates
            if isinstance(changed_date, datetime.date)
        }

    def _parse_alarm_target_date(self, alarm: Alarm) -> datetime.date | None:
        if not alarm.target_date:
            return None
        try:
            return datetime.datetime.strptime(alarm.target_date, "%d.%m.%Y").date()
        except ValueError:
            return None

    def _is_within_recheck_window(
        self,
        alarm: Alarm,
        now: datetime.datetime,
    ) -> bool:
        alarm_minutes = alarm.hour * 60 + alarm.minute
        now_minutes = now.hour * 60 + now.minute
        return abs(alarm_minutes - now_minutes) <= _RECHECK_WINDOW_MINUTES

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

        transport = str(getattr(cfg, "transport_type", "")).strip()
        if transport not in {"driving", "public_transport", "pedestrian"}:
            return None

        return self._extract_route_minutes(get_route(start, end, transport))

    def _extract_route_minutes(self, route: object) -> int | None:
        if not route:
            return None

        if isinstance(route, dict):
            return normalize_duration_minutes(route.get("duration_min", 0))

        if isinstance(route, list) and len(route) >= 2:
            return normalize_duration_minutes(int(route[1]) // 60)

        return None
