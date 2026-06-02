import logging
import flet as ft

from bridges.planner_bridge import is_valid_time
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager
from utils.geocoder_utils import get_coordinates_by_address
from utils.route_utis import get_route
from models.alarm_model import Alarm, WEEK_ANY, WEEK_EVEN, WEEK_ODD

logger = logging.getLogger(__name__)

_DAYS = [(1, "Пн"), (2, "Вт"), (3, "Ср"), (4, "Чт"), (5, "Пт"), (6, "Сб"), (7, "Вс")]
_WEEKS = [(WEEK_ANY, "Любая"), (WEEK_ODD, "Нечёт."), (WEEK_EVEN, "Чётная")]
FACULTIES_COORDS = {
    "ЭТФ - Электротехнический факультет": [58.054531, 56.222769], 
    "ХТФ - Факультет химических технологий, промышленной экологии и биотехнологий": [58.054541, 56.223820],
    "АКФ - Аэрокосмический факультет": [58.054355, 56.231653], 
    "Гуманитарный факультет": [58.002134, 56.247455], 
    "МТФ - Механико-технологический факультет": [58.008495, 56.239190],
    "Строительный факультет": [57.984680, 56.247428], 
    "Прикладной математики и механики": [58.054531, 56.224898],
    "ГНФ - Горно-нефтяной факультет": [58.008295, 56.240250],
    "Автодорожный факультет": [58.056593, 56.235830],
}


def build_alarm_view(
    navigation_bar: ft.NavigationBar,
    clock_text: ft.Text,
    alarm_manager: AlarmManager,
    config_manager: ConfigManager,
    auto_alarm_service,
    page: ft.Page,
) -> ft.View:
    
    cfg = config_manager.config
    alarms_column = ft.Column(spacing = 10, scroll = ft.ScrollMode.AUTO)
    alarms_container = ft.Container(
        content = alarms_column,
        expand = True,
        padding = ft.Padding.symmetric(horizontal = 16),
    )
    alarm_dialog = ft.AlertDialog(modal = True, title = ft.Text(""))
    page.overlay.append(alarm_dialog)

    auto_label = ft.Text("", size = 14, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE)

    def show_info(message: str) -> None:
        """ Для отображения информационных сообщений """
        snack = ft.SnackBar(
            content = ft.Text(message),
            bgcolor = ft.Colors.GREEN_700,
            duration = 3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def show_error(message: str) -> None:
        """ Для отображений об ошибке """
        snack = ft.SnackBar(
            content = ft.Text(message),
            bgcolor = ft.Colors.RED_700,
            duration = 4000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def _refresh_auto_button() -> None:
        """ Обновление кнопки вкл/выкл """
        enabled = config_manager.config.auto_alarm_enabled
        auto_label.value = "Авто: вкл" if enabled else "Авто: выкл"
        btn_auto.bgcolor = ft.Colors.BLUE_600 if enabled else ft.Colors.BLUE_GREY_600

    def refresh_list() -> None:
        alarms_column.controls.clear()
        with alarm_manager._lock:
            alarms_copy = list(alarm_manager.alarms)
        for alarm in alarms_copy:
            alarms_column.controls.append(_build_alarm_tile(alarm))
        try:
            _refresh_auto_button()
            page.update()
        except Exception as exc:
            logger.error("Failed to refresh alarm list: %s", exc)

    def _on_toggle(alarm_id: str) -> None:
        alarm_manager.toggle(alarm_id)
        refresh_list()

    def _on_delete(alarm_id: str) -> None:
        alarm_manager.remove(alarm_id)
        refresh_list()
    
    def _build_notification_banner() -> ft.Container:
        """Создаёт плашку с напоминанием проверить уведомления"""
        return ft.Container(
            content = ft.Row(
                [
                    ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, size = 32, color = ft.Colors.BLUE_700),
                    ft.Column(
                        [
                            ft.Text(
                                "Проверьте уведомления",
                                size = 16,
                                weight = ft.FontWeight.BOLD,
                                color = ft.Colors.GREY_900,
                            ),
                            ft.Text(
                                "Если напоминания не приходят, откройте\nсистемные настройки уведомлений.",
                                size = 13,
                                color = ft.Colors.GREY_700,
                            ),
                        ],
                        spacing = 4,
                        expand = True,
                    ),
                    ft.TextButton(
                        "Открыть",
                        style = ft.ButtonStyle(
                            color = ft.Colors.BLUE_700,
                        ),
                        on_click = lambda e: page.launch_url("app-settings:notification"),
                    ),
                ],
                alignment = ft.MainAxisAlignment.START,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor = ft.Colors.BLUE_50,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            margin = ft.Padding.symmetric(horizontal = 16, vertical = 8),
            border = ft.Border.all(
                color = ft.Colors.BLUE_100,
                width = 1,
            ),
        )

    def _build_alarm_tile(alarm: Alarm) -> ft.Control:
        toggle = ft.Switch(
            value = alarm.enabled,
            active_color = ft.Colors.BLUE_400,
            on_change = lambda e, aid = alarm.id: _on_toggle(aid),
        )

        tile = ft.Container(
            content = ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(alarm.label, size = 32, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
                            ft.Text(alarm.days_label, size = 12, color = ft.Colors.WHITE70),
                        ],
                        spacing = 2,
                        tight = True,
                    ),
                    toggle,
                ],
                alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor = ft.Colors.BLUE_GREY_700 if alarm.is_auto_schedule else ft.Colors.GREY_700,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 20, vertical = 14),
            on_click = None if alarm.is_auto_schedule else lambda e, current_alarm = alarm: _open_alarm_dialog(existing = current_alarm),
            ink = not alarm.is_auto_schedule,
        )

        if alarm.is_auto_schedule:
            return tile

        return ft.Dismissible(
            content = tile,
            dismiss_direction = ft.DismissDirection.END_TO_START,
            dismiss_thresholds = {ft.DismissDirection.END_TO_START: 0.3},
            background = ft.Container(
                content = ft.Row(
                    [ft.Icon(ft.Icons.DELETE, color = ft.Colors.WHITE)],
                    alignment = ft.MainAxisAlignment.END,
                ),
                bgcolor = ft.Colors.RED_400,
                border_radius = 16,
                padding = ft.Padding.only(right = 20),
            ),
            on_dismiss = lambda e, aid = alarm.id: _on_delete(aid),
        )

    def _open_alarm_dialog(existing: Alarm | None = None) -> None:
        is_edit = existing is not None

        hour_field = ft.TextField(
            label = "Час (0-23)",
            value = str(existing.hour) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER,
            width = 110,
        )

        minute_field = ft.TextField(
            label = "Минута (0-59)",
            value = str(existing.minute) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER,
            width = 110,
        )
        error_text = ft.Text("", color = ft.Colors.RED_400, size = 12)

        selected_days: list[int] = list(existing.days) if is_edit else []
        selected_week: list[str] = [existing.week_type] if is_edit and existing.week_type in {WEEK_ODD, WEEK_EVEN} else []
        day_buttons: dict[int, ft.Container] = {}
        week_buttons: dict[str, ft.Container] = {}

        def _day_color(day: int) -> str:
            return ft.Colors.BLUE_400 if day in selected_days else ft.Colors.GREY_700

        def _week_color(week_type: str) -> str:
            return ft.Colors.BLUE_400 if week_type in selected_week else ft.Colors.GREY_700

        def _toggle_day(day: int) -> None:
            if day in selected_days:
                selected_days.remove(day)
            else:
                selected_days.append(day)
            day_buttons[day].bgcolor = _day_color(day)
            day_buttons[day].update()

        def _toggle_week(week_type: str) -> None:
            if week_type in selected_week:
                selected_week.clear()
            else:
                selected_week[:] = [week_type]
            for key, button in week_buttons.items():
                button.bgcolor = _week_color(key)
                button.update()

        def _make_day_button(day: int, label: str) -> ft.Container:
            button = ft.Container(
                content = ft.Text(label, size = 11, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
                bgcolor = _day_color(day),
                border_radius = 20,
                width = 36,
                height = 36,
                alignment = ft.Alignment.CENTER,
                on_click = lambda e, current_day = day: _toggle_day(current_day),
                ink = True,
            )
            day_buttons[day] = button
            return button

        def _make_week_button(week_type: str, label: str) -> ft.Container:
            button = ft.Container(
                content = ft.Text(label, size = 11, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
                bgcolor = _week_color(week_type),
                border_radius = 12,
                padding = ft.Padding.symmetric(horizontal = 12, vertical = 8),
                on_click = lambda e, current_week = week_type: _toggle_week(current_week),
                ink = True,
            )
            week_buttons[week_type] = button
            return button

        days_row = ft.Row([_make_day_button(day, label) for day, label in _DAYS], spacing = 4)
        weeks_row = ft.Row([_make_week_button(week_type, label) for week_type, label in _WEEKS], spacing = 8)

        def _save(e) -> None:
            try:
                hour = int(hour_field.value)
                minute = int(minute_field.value)
                if not is_valid_time(hour, minute):
                    raise ValueError
            except ValueError:
                error_text.value = "Введите корректное время: час 0-23, минута 0-59."
                page.update()
                return

            days = sorted(selected_days)
            week_type = selected_week[0] if selected_week else WEEK_ANY
            target_date = ""
            if not days and not selected_week:
                target_date = alarm_manager.build_next_one_time_target_date(hour, minute)

            if is_edit:
                alarm_manager.update(existing.id, hour, minute, days, week_type, target_date)
            else:
                alarm_manager.add(
                    Alarm(
                        hour = hour,
                        minute = minute,
                        days = days,
                        week_type = week_type,
                        target_date = target_date,
                    )
                )

            alarm_dialog.open = False
            refresh_list()
            page.update()

        def _cancel(e) -> None:
            alarm_dialog.open = False
            page.update()

        alarm_dialog.title = ft.Text("Изменить будильник" if is_edit else "Новый будильник")
        alarm_dialog.content = ft.Column(
            [
                ft.Row(
                    [hour_field, ft.Text(":", size = 24, weight = ft.FontWeight.BOLD), minute_field],
                    vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    spacing = 8,
                ),
                ft.Container(height = 4),
                ft.Text("Повторять по дням:", size = 13, color = ft.Colors.GREY_500),
                days_row,
                ft.Text("Повторять по неделе:", size = 13, color = ft.Colors.GREY_500),
                weeks_row,
                ft.Text(
                    "Если ничего не выбрано, будильник будет разовым. После срабатывания он отключится, но останется в списке.",
                    size = 11,
                    italic = True,
                    color = ft.Colors.GREY_500,
                ),
                error_text,
            ],
            tight = True,
            spacing = 10,
            width = 320,
        )
        alarm_dialog.actions = [
            ft.TextButton("Отмена", on_click = _cancel),
            ft.FilledButton("Сохранить" if is_edit else "Добавить", on_click = _save),
        ]
        alarm_dialog.open = True
        page.update()

    def _show_auto_result(result: str) -> None:
        messages = {
            "scheduled": ("info", "Автобудильник обновлен под ближайшее событие."),
            "no_upcoming_entries": ("info", "Ближайших событий пока нет. Авто-режим остается включенным."),
            "missing_prep": ("error", "Укажите время на сборы в настройках."),
            "invalid_lesson_time": ("error", "Не удалось определить время ближайшего события."),
            "disabled": ("info", "Автобудильники выключены."),
        }
        level, message = messages.get(result, ("error", "Не удалось обновить автобудильник."))
        if result == "route_unavailable":
            show_error("Не удалось рассчитать маршрут. Проверьте адрес, API-ключи или укажите запасное время до вуза.")
            return
        if level == "info":
            show_info(message)
        else:
            show_error(message)

    def _on_auto(e) -> None:
        if config_manager.config.auto_alarm_enabled:
            config_manager.set_auto_alarm_enabled(False)
            auto_alarm_service.disable()
            refresh_list()
            _show_auto_result("disabled")
            return
 
        # ── Рассчитываем время в пути ─────────────────────────────────────────
        user_address = "Пермь, " + cfg.user_address
        try:
            user_address_coordinates = tuple(reversed(list(get_coordinates_by_address(user_address))))
        except Exception as e:
            logger.error(f"Не удалеось получить координаты пользователя: {e}")
        faculty_name = cfg.user_faculty
        try:
            faculty_address_coordinates = tuple(FACULTIES_COORDS[faculty_name])
        except Exception:
            logger.error(f"Не удалеось получить координаты факультета: {e}")
        transport_type = cfg.transport_type

        try:
            travel_minutes = get_route(user_address_coordinates, faculty_address_coordinates, transport_type)
            if type(travel_minutes) == dict:
                travel_minutes = travel_minutes['duration_min']
            else:
                travel_minutes = round(travel_minutes[0] / 60)
        except Exception as e:
            logger.warning(f"Маршрут не рассчитан. Произошла ошибка: {e}")
            if cfg.travel_time <= 0:
                show_error(
                    f"Не удалось рассчитать маршрут:\n"
                )
                return

        config_manager.set_auto_alarm_enabled(True)
        result = auto_alarm_service.sync_next_upcoming(force = True)
        if result in {"missing_prep", "invalid_lesson_time", "route_unavailable"}:
            config_manager.set_auto_alarm_enabled(False)
        refresh_list()
        _show_auto_result(result)
    
    def _on_week(e) -> None:
        result, count = auto_alarm_service.sync_week_ahead()
        refresh_list()
        if result == "scheduled":
            show_info(f"Будильников на неделю: {count}")
        elif result == "missing_prep":
            show_error("Укажите время на сборы в настройках.")
        elif result == "no_upcoming_entries":
            show_info("Занятий на ближайшие 7 дней нет.")
        elif result == "route_unavailable":
            show_error("Укажите время до ВУЗа (мин) в настройках.")
        else:
            show_error("Не удалось расставить будильники.")

    btn_auto = ft.Container(
        content = auto_label,
        bgcolor = ft.Colors.BLUE_GREY_600,
        border_radius = 16,
        padding = ft.Padding.symmetric(horizontal = 20, vertical = 14),
        on_click = _on_auto,
        ink = True,
    )

    btn_week = ft.Container(
        content = ft.Text("На неделю", size = 14, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
        bgcolor = ft.Colors.TEAL_600,
        border_radius = 16,
        padding = ft.Padding.symmetric(horizontal = 20, vertical = 14),
        on_click = _on_week,
        ink = True,
    )

    btn_add = ft.Container(
        content = ft.Icon(ft.Icons.ADD, color = ft.Colors.WHITE),
        bgcolor = ft.Colors.BLUE_200,
        border_radius = 16,
        width = 54,
        height = 54,
        alignment = ft.Alignment.CENTER,
        on_click = lambda e: _open_alarm_dialog(existing = None),
        ink = True,
    )

    bottom_row = ft.Container(
        content = ft.Row(
            [
                # btn_week, 
                # ft.Container(width = 8), 
                btn_auto, 
                ft.Container(expand = True), 
                btn_add
            ],
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        padding = ft.Padding.symmetric(horizontal = 16, vertical = 12),
    )

    refresh_list()
    return ft.View(
        route = "/alarm",
        padding = 0,
        navigation_bar = navigation_bar,
        controls = [
            ft.SafeArea(
                content = ft.Column(
                    [
                        ft.Container(
                            padding = ft.Padding.symmetric(horizontal = 16, vertical = 8),
                            content = ft.Column(
                                [
                                    ft.Text("Будильники", size = 25, weight = ft.FontWeight.BOLD),
                                    clock_text,
                                ],
                                spacing = 2,
                            ),
                        ),
                        # Добавляем плашку с уведомлением
                        _build_notification_banner(),
                        alarms_container,
                        bottom_row,
                    ],
                    expand = True,
                    spacing = 0,
                )
            )
        ],
    )
