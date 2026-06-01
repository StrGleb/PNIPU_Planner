import datetime
import logging
from typing import Any

from bridges.planner_bridge import (
    can_recheck_alarm_now,
    collect_alarm_indices_on_or_after_date,
    collect_upcoming_lesson_indices_with_horizon,
    compute_buffered_alarm_minutes,
    is_alarm_within_recheck_datetime_window,
    normalize_duration_minutes,
    select_next_lesson_index,
    time_to_minutes,
)
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager
from managers.planner_manager import PlannerManager
from models.alarm_model import (
    ALARM_KIND_REMINDER,
    ALARM_KIND_ROUTE,
    Alarm,
    SOURCE_AUTO_SCHEDULE,
)
from models.lesson_model import ENTRY_TYPE_EVENT, Lesson, normalize_event_reminder_lead_minutes
from utils.campus_locations import FACULTIES_COORDS

logger = logging.getLogger(__name__)

_ALARM_BUFFER_MINUTES = 10
_UPCOMING_HORIZON_DAYS = 60
_QUEUE_HORIZON_DAYS = 3
_QUEUE_VERSION = 1
_RECHECK_COOLDOWN_MINUTES = 45
_PUBLIC_TRANSPORT_RECHECK_LEAD_MINUTES = 90
_PUBLIC_TRANSPORT_RECHECK_AFTER_MINUTES = 30
_DEFAULT_RECHECK_AFTER_MINUTES = 15


class AutoAlarmService:
    def __init__(
        self,
        alarm_manager: AlarmManager,
        config_manager: ConfigManager,
        planner_manager: PlannerManager,
        bridge_manager: Any | None = None,
    ) -> None:
        self._alarm_manager = alarm_manager
        self._config_manager = config_manager
        self._planner_manager = planner_manager
        self._bridge_manager = bridge_manager

    def start(self) -> None:
        now = datetime.datetime.now()
        self._cleanup_expired_auto_alarms(now)

        if self._bridge_manager is not None:
            payload = self._bridge_manager.prune_expired(
                now_timestamp = self._datetime_to_timestamp_ms(now),
            )
            self._sync_visible_alarm_from_payload(payload)

        if not self._config_manager.config.auto_alarm_enabled:
            return

        if self._bridge_manager is not None:
            self._refresh_after_app_open(now)
            if self._bridge_manager.use_system_schedule:
                self._bridge_manager.restore_after_boot()
            return

        self.sync_next_upcoming(force = False)

    def sync_tomorrow(self, force: bool = False) -> str:
        now = datetime.datetime.now()
        tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days = 1), datetime.time.min)
        if self._bridge_manager is not None:
            result, _ = self.sync_week_ahead(reference_datetime = tomorrow)
            return result
        return self.sync_next_upcoming(force = force, from_datetime = tomorrow)

    def sync_week_ahead(
        self,
        reference_datetime: datetime.datetime | None = None,
    ) -> tuple[str, int]:
        now = reference_datetime or datetime.datetime.now()
        queue_items, missing_prep_seen, route_error_seen = self._build_week_queue_items(now)
        if not queue_items:
            if self._bridge_manager is not None:
                self._bridge_manager.cancel_auto_alarms()
            self._alarm_manager.clear_auto_schedule_alarms()
            if missing_prep_seen:
                return "missing_prep", 0
            if route_error_seen:
                return "route_unavailable", 0
            return "no_upcoming_entries", 0

        if queue_items:
            payload = {
                "version": _QUEUE_VERSION,
                "generated_at": self._datetime_to_timestamp_ms(now),
                "alarms": queue_items,
            }
            if self._bridge_manager is not None:
                self._bridge_manager.schedule_weekly_queue(payload)
            self._sync_visible_alarm_from_payload(payload)
            return "scheduled", len(queue_items)

        if self._bridge_manager is not None:
            self._bridge_manager.cancel_auto_alarms()
        self._alarm_manager.clear_auto_schedule_alarms()
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
        cfg = self._config_manager.config
        if not cfg.auto_alarm_enabled and not force:
            return "disabled"

        now = from_datetime or datetime.datetime.now()
        if self._bridge_manager is not None:
            if force:
                result, _ = self.sync_week_ahead(reference_datetime = now)
                return result
            return self._refresh_after_app_open(now)

        candidate = self._select_next_candidate(now)
        if candidate is None:
            self._alarm_manager.clear_auto_schedule_alarms()
            return "no_upcoming_entries"

        alarm, error_code, _route_source = candidate
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
        if not alarm.is_auto_schedule:
            return "ignored"

        fire_time = fired_at or datetime.datetime.now()
        if self._bridge_manager is not None:
            payload = self._bridge_manager.pop_due_alarm(self._datetime_to_timestamp_ms(fire_time))
            self._sync_visible_alarm_from_payload(payload)
            if payload.get("alarms"):
                return "scheduled"
            result, _ = self.sync_week_ahead(reference_datetime = fire_time + datetime.timedelta(minutes = 1))
            return result

        self._alarm_manager.clear_auto_schedule_alarms()
        next_start = fire_time + datetime.timedelta(minutes = 1)
        return self.sync_next_upcoming(force = True, from_datetime = next_start)

    def handle_planner_change(self) -> str:
        if not self._config_manager.config.auto_alarm_enabled:
            return "disabled"
        if self._bridge_manager is not None:
            result, _ = self.sync_week_ahead()
            return result
        return self.sync_next_upcoming(force = True)

    def disable(self) -> None:
        if self._bridge_manager is not None:
            self._bridge_manager.cancel_auto_alarms()
        self._alarm_manager.clear_auto_schedule_alarms()

    def _select_next_candidate(
        self,
        now: datetime.datetime,
    ) -> tuple[Alarm | None, str | None, str] | None:
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
                max_days_ahead = _UPCOMING_HORIZON_DAYS,
            )
            if selected_index < 0:
                break

            selected_lesson = lessons.pop(selected_index)
            alarm, error_code, route_source = self._build_auto_alarm(
                selected_lesson.date,
                selected_lesson,
                allow_live = True,
            )
            if alarm is not None:
                return alarm, None, route_source
            if error_code == "missing_prep":
                missing_prep_seen = True
            if error_code == "route_unavailable":
                route_error_seen = True

        if missing_prep_seen:
            return None, "missing_prep", ""
        if route_error_seen:
            return None, "route_unavailable", ""
        return None

    def _build_auto_alarm(
        self,
        target_date: datetime.date,
        lesson: Lesson,
        allow_live: bool,
        source: str = SOURCE_AUTO_SCHEDULE,
    ) -> tuple[Alarm | None, str | None, str]:
        cfg = self._config_manager.config
        lesson_minutes = time_to_minutes(lesson.time_start)
        if lesson_minutes < 0:
            return None, "invalid_lesson_time", ""

        if self._event_should_use_reminder(lesson):
            reminder_alarm = self._build_event_reminder_alarm(
                target_date = target_date,
                lesson = lesson,
                lesson_minutes = lesson_minutes,
                source = source,
            )
            return reminder_alarm, None, "estimated"

        if cfg.get_together_time <= 0:
            return None, "missing_prep", ""

        travel_minutes, route_source = self._resolve_travel_minutes(lesson, allow_live = allow_live)
        if travel_minutes <= 0:
            return None, "route_unavailable", ""

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
                rechecked_at = self._format_rechecked_at(datetime.datetime.now()),
                subject = lesson.subject,
                destination = lesson.address or lesson.location_text,
                entry_type = lesson.entry_type,
                alarm_kind = ALARM_KIND_ROUTE,
            ),
            None,
            route_source,
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
            rechecked_at = self._format_rechecked_at(datetime.datetime.now()),
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

    def _resolve_travel_minutes(self, lesson: Lesson, allow_live: bool) -> tuple[int, str]:
        cfg = self._config_manager.config
        fallback_minutes = normalize_duration_minutes(cfg.travel_time)
        if not allow_live:
            return fallback_minutes, "estimated"

        live_minutes = self._resolve_live_route_minutes(lesson)
        if live_minutes and live_minutes > 0:
            return live_minutes, "live"
        return fallback_minutes, "estimated"

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
            from utils.weather_utils import normalize_weather_address, resolve_coordinates_for_config
        except Exception:
            logger.exception("Route utilities are unavailable")
            return None

        coordinates = resolve_coordinates_for_config(self._config_manager)
        if not coordinates:
            return None

        start = (coordinates[1], coordinates[0])

        if destination_address:
            destination_query = normalize_weather_address(destination_address)
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

        if transport == "public_transport":
            route_candidates = [
                self._extract_route_minutes(get_route(start, end, "public_transport")),
                self._extract_route_minutes(get_route(start, end, "pedestrian")),
            ]
            valid_routes = [minutes for minutes in route_candidates if minutes and minutes > 0]
            return min(valid_routes) if valid_routes else None

        return self._extract_route_minutes(get_route(start, end, transport))

    def _extract_route_minutes(self, route: object) -> int | None:
        if not route:
            return None

        if isinstance(route, dict):
            return normalize_duration_minutes(route.get("duration_min", 0))

        if isinstance(route, list) and len(route) >= 2:
            return normalize_duration_minutes(int(route[1]) // 60)

        return None

    def _collect_upcoming_lessons(
        self,
        now: datetime.datetime,
        horizon_days: int,
    ) -> list[Lesson]:
        lessons_with_minutes = [
            (lesson, time_to_minutes(lesson.time_start))
            for lesson in self._planner_manager.get_all_lessons()
        ]
        lessons_with_minutes.sort(
            key = lambda item: (item[0].date, item[1], item[0].subject),
        )

        sorted_lessons = [lesson for lesson, _minutes in lessons_with_minutes]
        start_minutes = [minutes for _lesson, minutes in lessons_with_minutes]
        upcoming_indices = collect_upcoming_lesson_indices_with_horizon(
            [lesson.date_str for lesson in sorted_lessons],
            start_minutes,
            now,
            max_days_ahead = horizon_days,
        )
        return [sorted_lessons[index] for index in upcoming_indices]

    def _build_week_queue_items(
        self,
        now: datetime.datetime,
    ) -> tuple[list[dict[str, Any]], bool, bool]:
        upcoming = self._collect_upcoming_lessons(now, horizon_days = _QUEUE_HORIZON_DAYS)
        if not upcoming:
            return [], False, False

        grouped_by_date: dict[datetime.date, list[Lesson]] = {}
        for lesson in upcoming:
            grouped_by_date.setdefault(lesson.date, []).append(lesson)

        queue_items: list[dict[str, Any]] = []
        missing_prep_seen = False
        route_error_seen = False

        for target_date in sorted(grouped_by_date):
            day_lessons = sorted(
                grouped_by_date[target_date],
                key = lambda lesson: (time_to_minutes(lesson.time_start), lesson.subject),
            )
            first_route_item_added = False

            for lesson in day_lessons:
                is_event_reminder = self._event_should_use_reminder(lesson)
                alarm, error_code, route_source = self._build_auto_alarm(
                    target_date,
                    lesson,
                    allow_live = not first_route_item_added and not is_event_reminder,
                )
                if alarm is None:
                    if error_code == "missing_prep":
                        missing_prep_seen = True
                    if error_code == "route_unavailable" and not is_event_reminder and not first_route_item_added:
                        route_error_seen = True
                    continue

                if alarm.alarm_kind == ALARM_KIND_REMINDER:
                    queue_items.append(
                        self._build_queue_item(
                            alarm = alarm,
                            lesson = lesson,
                            route_source = "notification",
                        )
                    )
                    continue

                if first_route_item_added:
                    continue

                queue_items.append(
                    self._build_queue_item(
                        alarm = alarm,
                        lesson = lesson,
                        route_source = route_source,
                    )
                )
                first_route_item_added = True

        queue_items.sort(key = lambda item: int(item.get("alarm_timestamp", 0) or 0))
        return queue_items, missing_prep_seen, route_error_seen

    def _refresh_after_app_open(self, now: datetime.datetime) -> str:
        payload = self._bridge_manager.prune_expired(
            now_timestamp = self._datetime_to_timestamp_ms(now),
        )
        alarms = payload.get("alarms", [])
        if not alarms:
            result, _ = self.sync_week_ahead(reference_datetime = now)
            return result

        self._sync_visible_alarm_from_payload(payload)
        nearest_item = alarms[0]
        if not self._should_recheck_queue_item(nearest_item, now):
            return "scheduled"

        return self._recheck_nearest_queue_item(nearest_item, now)

    def _recheck_nearest_queue_item(
        self,
        queue_item: dict[str, Any],
        now: datetime.datetime,
    ) -> str:
        lesson = self._find_lesson_for_queue_item(queue_item)
        if lesson is None:
            result, _ = self.sync_week_ahead(reference_datetime = now)
            return result

        alarm, error_code, route_source = self._build_auto_alarm(
            lesson.date,
            lesson,
            allow_live = True,
        )
        if alarm is not None:
            updated_item = self._build_queue_item(
                alarm = alarm,
                lesson = lesson,
                route_source = route_source,
                item_id = str(queue_item.get("id", "")) or None,
                rechecked_at = now,
            )
            payload = self._bridge_manager.replace_first_alarm(updated_item)
            self._sync_visible_alarm_from_payload(payload)
            return "scheduled"

        if error_code == "route_unavailable":
            cached_item = dict(queue_item)
            cached_item["rechecked_at"] = self._format_rechecked_at(now)
            cached_item["route_source"] = str(cached_item.get("route_source", "")).strip() or "cached"
            payload = self._bridge_manager.replace_first_alarm(cached_item)
            self._sync_visible_alarm_from_payload(payload)
            return "scheduled"

        return error_code or "no_upcoming_entries"

    def _should_recheck_queue_item(
        self,
        queue_item: dict[str, Any],
        now: datetime.datetime,
    ) -> bool:
        if str(queue_item.get("alarm_kind", ALARM_KIND_ROUTE)) == ALARM_KIND_REMINDER:
            return False

        rechecked_at = str(queue_item.get("rechecked_at", "")).strip()
        if rechecked_at and not can_recheck_alarm_now(rechecked_at, now, _RECHECK_COOLDOWN_MINUTES):
            return False

        alarm_timestamp = int(queue_item.get("alarm_timestamp", 0) or 0)
        if alarm_timestamp <= 0:
            return False

        alarm_dt = datetime.datetime.fromtimestamp(alarm_timestamp / 1000)
        lead_minutes, after_minutes = self._recheck_window_bounds()
        return is_alarm_within_recheck_datetime_window(
            alarm_dt,
            now,
            lead_minutes,
            after_minutes,
        )

    def _recheck_window_bounds(self) -> tuple[int, int]:
        if self._config_manager.config.transport_type == "public_transport":
            return _PUBLIC_TRANSPORT_RECHECK_LEAD_MINUTES, _PUBLIC_TRANSPORT_RECHECK_AFTER_MINUTES
        return self._config_manager.config.auto_alarm_recheck_lead_minutes, _DEFAULT_RECHECK_AFTER_MINUTES

    def _build_queue_item(
        self,
        alarm: Alarm,
        lesson: Lesson,
        route_source: str,
        item_id: str | None = None,
        rechecked_at: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        target_date = datetime.datetime.strptime(alarm.target_date, "%d.%m.%Y").date()
        alarm_datetime = datetime.datetime.combine(
            target_date,
            datetime.time(hour = alarm.hour, minute = alarm.minute),
        )
        lesson_minutes = time_to_minutes(lesson.time_start)
        lesson_datetime = datetime.datetime.combine(
            target_date,
            datetime.time(hour = lesson_minutes // 60, minute = lesson_minutes % 60),
        )
        checked_at = rechecked_at or datetime.datetime.now()
        queue_id = item_id or f"auto:{lesson.id}:{alarm.target_date}:{alarm.hour:02d}{alarm.minute:02d}"

        return {
            "id": queue_id,
            "lesson_id": lesson.id,
            "target_date": alarm.target_date,
            "alarm_timestamp": self._datetime_to_timestamp_ms(alarm_datetime),
            "lesson_timestamp": self._datetime_to_timestamp_ms(lesson_datetime),
            "lesson_time": lesson.time_start,
            "subject": alarm.subject,
            "destination": alarm.destination,
            "entry_type": alarm.entry_type,
            "alarm_kind": alarm.alarm_kind,
            "lead_minutes": alarm.lead_minutes,
            "route_minutes": alarm.route_minutes,
            "route_source": route_source,
            "rechecked_at": self._format_rechecked_at(checked_at),
        }

    def _sync_visible_alarm_from_payload(self, payload: dict[str, Any]) -> None:
        alarms = payload.get("alarms", [])
        if not alarms:
            self._alarm_manager.clear_auto_schedule_alarms()
            return

        visible_alarm = self._alarm_from_queue_item(alarms[0])
        self._alarm_manager.replace_auto_schedule_alarms([visible_alarm])

    def _alarm_from_queue_item(self, item: dict[str, Any]) -> Alarm:
        alarm_timestamp = int(item.get("alarm_timestamp", 0) or 0)
        lesson_timestamp = int(item.get("lesson_timestamp", 0) or 0)
        alarm_datetime = datetime.datetime.fromtimestamp(alarm_timestamp / 1000)
        lesson_datetime = datetime.datetime.fromtimestamp(lesson_timestamp / 1000)
        return Alarm(
            id = str(item.get("id", "")) or None,
            hour = alarm_datetime.hour,
            minute = alarm_datetime.minute,
            source = SOURCE_AUTO_SCHEDULE,
            target_date = str(item.get("target_date", "")),
            lesson_time = lesson_datetime.strftime("%H:%M"),
            route_minutes = int(item.get("route_minutes", 0) or 0),
            rechecked_at = str(item.get("rechecked_at", "")),
            subject = str(item.get("subject", "")),
            destination = str(item.get("destination", "")),
            entry_type = str(item.get("entry_type", "")),
            alarm_kind = str(item.get("alarm_kind", ALARM_KIND_ROUTE)) or ALARM_KIND_ROUTE,
            lead_minutes = int(item.get("lead_minutes", 0) or 0),
        )

    def _find_lesson_for_queue_item(self, item: dict[str, Any]) -> Lesson | None:
        lesson_id = str(item.get("lesson_id", "")).strip()
        target_date = str(item.get("target_date", "")).strip()
        lesson_time = str(item.get("lesson_time", "")).strip()
        subject = str(item.get("subject", "")).strip()
        entry_type = str(item.get("entry_type", "")).strip()

        for lesson in self._planner_manager.get_all_lessons():
            if lesson_id and lesson.id == lesson_id:
                return lesson
            if (
                lesson.date_str == target_date
                and lesson.time_start == lesson_time
                and lesson.subject == subject
                and lesson.entry_type == entry_type
            ):
                return lesson
        return None

    def _datetime_to_timestamp_ms(self, value: datetime.datetime) -> int:
        return int(value.timestamp() * 1000)

    def _format_rechecked_at(self, value: datetime.datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")
