import logging
import threading

import flet as ft

from bridges.planner_bridge import is_valid_time
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager
from models.alarm_model import Alarm, WEEK_ANY, WEEK_EVEN, WEEK_ODD


logger = logging.getLogger(__name__)

_DAYS = [(1, "Пн"), (2, "Вт"), (3, "Ср"), (4, "Чт"), (5, "Пт"), (6, "Сб"), (7, "Вс")]
_WEEKS = [(WEEK_ANY, "Любая"), (WEEK_ODD, "Нечёт."), (WEEK_EVEN, "Чётная")]


def build_alarm_view(
    navigation_bar: ft.NavigationBar,
    clock_text: ft.Text,
    alarm_manager: AlarmManager,
    config_manager: ConfigManager,
    auto_alarm_service,
    page: ft.Page,
    auto_alarm_bridge_manager = None,
) -> ft.View:
    alarms_column = ft.Column(spacing = 12, scroll = ft.ScrollMode.AUTO)
    alarms_container = ft.Container(
        content = alarms_column,
        expand = True,
        padding = ft.Padding.symmetric(horizontal = 16),
    )
    alarm_dialog = ft.AlertDialog(modal = True, title = ft.Text(""))
    page.overlay.append(alarm_dialog)

    auto_label = ft.Text("", size = 15, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE)
    auto_spinner = ft.ProgressRing(width = 16, height = 16, stroke_width = 2, color = ft.Colors.WHITE, visible = False)
    exact_alarm_text = ft.Text("", size = 12, color = ft.Colors.WHITE)

    def _auto_button_style(bgcolor: str) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            shape = ft.RoundedRectangleBorder(radius = 16),
            padding = ft.Padding.symmetric(horizontal = 20, vertical = 16),
            bgcolor = {
                ft.ControlState.DEFAULT: bgcolor,
                ft.ControlState.DISABLED: ft.Colors.BLUE_GREY_400,
            },
        )

    def _safe_page_update() -> None:
        try:
            page.update()
        except Exception as exc:
            logger.debug("Alarm view update skipped: %s", exc)

    def show_info(message: str) -> None:
        snack = ft.SnackBar(
            content = ft.Text(message),
            bgcolor = ft.Colors.GREEN_700,
            duration = 3000,
        )
        page.overlay.append(snack)
        snack.open = True
        _safe_page_update()

    def show_error(message: str) -> None:
        snack = ft.SnackBar(
            content = ft.Text(message),
            bgcolor = ft.Colors.RED_700,
            duration = 4000,
        )
        page.overlay.append(snack)
        snack.open = True
        _safe_page_update()

    def _refresh_auto_button(is_loading: bool = False) -> None:
        enabled = config_manager.config.auto_alarm_enabled
        auto_label.value = "Авто: вкл" if enabled else "Авто: выкл"
        auto_spinner.visible = is_loading
        btn_auto.disabled = is_loading
        btn_auto.style = _auto_button_style(ft.Colors.BLUE_600 if enabled else ft.Colors.BLUE_GREY_600)

    def _refresh_exact_alarm_state(refresh_permission: bool = False) -> None:
        if (
            auto_alarm_bridge_manager is None
            or not auto_alarm_bridge_manager.is_android_bridge_enabled
        ):
            exact_alarm_banner.visible = False
            return

        has_permission = auto_alarm_bridge_manager.can_schedule_exact_alarms(
            refresh = refresh_permission,
        )
        exact_alarm_banner.visible = not has_permission
        exact_alarm_text.value = (
            "Точные Android-будильники временно отключены. "
            "Пока авто-очередь работает только внутри приложения."
        )

    def refresh_list() -> None:
        if page.route != "/alarm":
            return

        try:
            alarms_column.controls.clear()
            with alarm_manager._lock:
                alarms_copy = list(alarm_manager.alarms)
            for alarm in alarms_copy:
                alarms_column.controls.append(_build_alarm_tile(alarm))
            _refresh_auto_button()
            _refresh_exact_alarm_state()
            page.update()
        except Exception as exc:
            logger.error("Failed to refresh alarm list: %s", exc)

    def _on_toggle(alarm_id: str) -> None:
        alarm_manager.toggle(alarm_id)
        refresh_list()

    def _on_delete(alarm_id: str) -> None:
        alarm_manager.remove(alarm_id)
        refresh_list()

    def _build_alarm_tile(alarm: Alarm) -> ft.Control:
        toggle = ft.Switch(
            value = alarm.enabled,
            active_color = ft.Colors.BLUE_400,
            on_change = lambda e, aid = alarm.id: _on_toggle(aid),
        )

        title_color = ft.Colors.WHITE
        subtitle_color = ft.Colors.WHITE70
        tile_color = ft.Colors.BLUE_GREY_700 if alarm.is_auto_schedule else ft.Colors.GREY_700

        tile = ft.Container(
            bgcolor = tile_color,
            border_radius = 22,
            padding = ft.Padding.symmetric(horizontal = 18, vertical = 16),
            on_click = None if alarm.is_auto_schedule else lambda e, current_alarm = alarm: _open_alarm_dialog(existing = current_alarm),
            ink = not alarm.is_auto_schedule,
            content = ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                alarm.label,
                                size = 31,
                                weight = ft.FontWeight.BOLD,
                                color = title_color,
                                max_lines = 1,
                            ),
                            ft.Text(
                                alarm.days_label,
                                size = 13,
                                color = subtitle_color,
                                max_lines = 2,
                                overflow = ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing = 6,
                        expand = True,
                        tight = True,
                    ),
                    ft.Container(
                        width = 72,
                        alignment = ft.Alignment.CENTER_RIGHT,
                        content = toggle,
                    ),
                ],
                spacing = 12,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
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
                border_radius = 22,
                padding = ft.Padding.only(right = 22),
            ),
            on_dismiss = lambda e, aid = alarm.id: _on_delete(aid),
        )

    def _open_alarm_dialog(existing: Alarm | None = None) -> None:
        is_edit = existing is not None

        hour_field = ft.TextField(
            label = "Час (0-23)",
            value = str(existing.hour) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER,
            width = 120,
            text_align = ft.TextAlign.CENTER,
        )
        minute_field = ft.TextField(
            label = "Минута (0-59)",
            value = str(existing.minute) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER,
            width = 120,
            text_align = ft.TextAlign.CENTER,
        )
        error_text = ft.Text("", color = ft.Colors.RED_400, size = 12)

        selected_days: list[int] = list(existing.days) if is_edit else []
        selected_week: list[str] = [existing.week_type] if is_edit and existing.week_type in {WEEK_ODD, WEEK_EVEN} else []
        day_buttons: dict[int, ft.Container] = {}
        week_buttons: dict[str, ft.Container] = {}

        def _day_color(day: int) -> str:
            return ft.Colors.BLUE_500 if day in selected_days else ft.Colors.GREY_700

        def _week_color(week_type: str) -> str:
            return ft.Colors.BLUE_500 if week_type in selected_week else ft.Colors.GREY_700

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
                content = ft.Text(label, size = 12, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
                bgcolor = _day_color(day),
                border_radius = 18,
                width = 42,
                height = 42,
                alignment = ft.Alignment.CENTER,
                on_click = lambda e, current_day = day: _toggle_day(current_day),
                ink = True,
            )
            day_buttons[day] = button
            return button

        def _make_week_button(week_type: str, label: str) -> ft.Container:
            button = ft.Container(
                content = ft.Text(
                    label,
                    size = 12,
                    weight = ft.FontWeight.BOLD,
                    color = ft.Colors.WHITE,
                    text_align = ft.TextAlign.CENTER,
                ),
                bgcolor = _week_color(week_type),
                border_radius = 14,
                width = 96,
                height = 42,
                alignment = ft.Alignment.CENTER,
                on_click = lambda e, current_week = week_type: _toggle_week(current_week),
                ink = True,
            )
            week_buttons[week_type] = button
            return button

        days_wrap = ft.Wrap(
            [_make_day_button(day, label) for day, label in _DAYS],
            spacing = 8,
            run_spacing = 8,
        )
        weeks_wrap = ft.Wrap(
            [_make_week_button(week_type, label) for week_type, label in _WEEKS],
            spacing = 8,
            run_spacing = 8,
        )

        def _save(e) -> None:
            try:
                hour = int(hour_field.value)
                minute = int(minute_field.value)
                if not is_valid_time(hour, minute):
                    raise ValueError
            except ValueError:
                error_text.value = "Введите корректное время: час 0-23, минута 0-59."
                _safe_page_update()
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
            _safe_page_update()

        def _cancel(e) -> None:
            alarm_dialog.open = False
            _safe_page_update()

        selection_box_style = {
            "border_radius": 18,
            "padding": ft.Padding.symmetric(horizontal = 12, vertical = 12),
            "border": ft.border.all(1, ft.Colors.GREY_300),
            "bgcolor": ft.Colors.with_opacity(0.02, ft.Colors.BLACK),
        }

        alarm_dialog.title = ft.Text("Изменить будильник" if is_edit else "Новый будильник", size = 24)
        alarm_dialog.content = ft.Column(
            [
                ft.Row(
                    [hour_field, ft.Text(":", size = 26, weight = ft.FontWeight.BOLD), minute_field],
                    vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    alignment = ft.MainAxisAlignment.CENTER,
                    spacing = 10,
                ),
                ft.Container(height = 4),
                ft.Text("Повторять по дням", size = 13, color = ft.Colors.GREY_600),
                ft.Container(content = days_wrap, **selection_box_style),
                ft.Text("Повторять по неделе", size = 13, color = ft.Colors.GREY_600),
                ft.Container(content = weeks_wrap, **selection_box_style),
                ft.Text(
                    "Если ничего не выбрано, будильник будет разовым и после срабатывания отключится.",
                    size = 11,
                    italic = True,
                    color = ft.Colors.GREY_500,
                ),
                error_text,
            ],
            tight = True,
            spacing = 10,
            width = 340,
        )
        alarm_dialog.actions = [
            ft.TextButton("Отмена", on_click = _cancel),
            ft.FilledButton("Сохранить" if is_edit else "Добавить", on_click = _save),
        ]
        alarm_dialog.open = True
        _safe_page_update()

    def _show_auto_result(result: str) -> None:
        messages = {
            "scheduled": ("info", "Очередь авто-будильников обновлена, в списке показан ближайший."),
            "no_upcoming_entries": ("info", "Ближайших событий пока нет. Авто-режим остаётся включённым."),
            "missing_prep": ("error", "Укажите время на сборы в настройках."),
            "invalid_lesson_time": ("error", "Не удалось определить время ближайшего события."),
            "disabled": ("info", "Авто-будильники выключены."),
        }
        level, message = messages.get(result, ("error", "Не удалось обновить авто-будильники."))
        if result == "route_unavailable":
            show_error("Не удалось рассчитать маршрут. Проверьте адрес или укажите запасное время до вуза.")
            return
        if level == "info":
            show_info(message)
        else:
            show_error(message)

    def _set_auto_loading(value: bool) -> None:
        _refresh_auto_button(is_loading = value)
        try:
            if page.route == "/alarm":
                btn_auto.update()
                page.update()
        except Exception as exc:
            logger.debug("Auto button update skipped: %s", exc)

    def _run_auto_sync(enable: bool, force_refresh: bool = False) -> None:
        def _job() -> None:
            result = "disabled"
            try:
                if enable:
                    config_manager.set_auto_alarm_enabled(True)
                    if force_refresh:
                        result = auto_alarm_service.sync_next_upcoming(force = True)
                    else:
                        result, _count = auto_alarm_service.sync_week_ahead()
                    if result in {"missing_prep", "invalid_lesson_time", "route_unavailable"}:
                        config_manager.set_auto_alarm_enabled(False)
                else:
                    config_manager.set_auto_alarm_enabled(False)
                    auto_alarm_service.disable()
                    result = "disabled"
            except Exception:
                logger.exception("Failed to sync auto alarms in background")
                result = "error"
            finally:
                _set_auto_loading(False)
                try:
                    refresh_list()
                except Exception:
                    logger.exception("Failed to render alarm list after background sync")
                if page.route == "/alarm":
                    _show_auto_result(result)

        _set_auto_loading(True)
        threading.Thread(target = _job, daemon = True).start()

    def _open_exact_alarm_settings(e) -> None:
        if auto_alarm_bridge_manager is None:
            return
        auto_alarm_bridge_manager.open_exact_alarm_settings()
        _refresh_exact_alarm_state(refresh_permission = True)
        if config_manager.config.auto_alarm_enabled:
            _run_auto_sync(enable = True, force_refresh = True)
            return
        _safe_page_update()

    def _on_auto(e) -> None:
        _run_auto_sync(enable = not config_manager.config.auto_alarm_enabled)

    btn_auto = ft.FilledButton(
        content = ft.Row(
            [auto_spinner, auto_label],
            spacing = 10,
            tight = True,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        style = _auto_button_style(ft.Colors.BLUE_GREY_600),
        on_click = _on_auto,
    )

    btn_add = ft.Container(
        content = ft.Icon(ft.Icons.ADD, color = ft.Colors.WHITE, size = 28),
        bgcolor = ft.Colors.BLUE_200,
        border_radius = 16,
        width = 58,
        height = 58,
        alignment = ft.Alignment.CENTER,
        on_click = lambda e: _open_alarm_dialog(existing = None),
        ink = True,
    )

    exact_alarm_banner = ft.Container(
        visible = False,
        margin = ft.Margin.symmetric(horizontal = 16, vertical = 8),
        padding = ft.Padding.symmetric(horizontal = 14, vertical = 12),
        bgcolor = ft.Colors.ORANGE_700,
        border_radius = 14,
        content = ft.Column(
            [
                ft.Text(
                    "Нужно разрешение на точные будильники",
                    size = 14,
                    weight = ft.FontWeight.BOLD,
                    color = ft.Colors.WHITE,
                ),
                exact_alarm_text,
                ft.FilledButton(
                    "Открыть настройки",
                    icon = ft.Icons.OPEN_IN_NEW,
                    on_click = _open_exact_alarm_settings,
                ),
            ],
            spacing = 8,
            tight = True,
        ),
    )

    bottom_row = ft.Container(
        content = ft.Row(
            [
                btn_auto,
                ft.Container(expand = True),
                btn_add,
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
                        exact_alarm_banner,
                        alarms_container,
                        bottom_row,
                    ],
                    expand = True,
                    spacing = 0,
                )
            )
        ],
    )
