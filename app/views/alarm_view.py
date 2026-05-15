import flet as ft
from models.alarm_model import Alarm
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager
from bridges.planner_bridge import is_valid_time


def build_alarm_view(
    navigation_bar: ft.NavigationBar,
    clock_text: ft.Text,
    alarm_manager: AlarmManager,
    config_manager: ConfigManager,
    page: ft.Page,
) -> ft.View:

    # ── Список ───────────────────────────────────────────────────────────────
    alarms_list = ft.ListView(
        spacing = 10,
        padding = ft.padding.symmetric(horizontal = 16),
        expand  = True,
        # bgcolor = "transparent",   # ← убирает серый прямоугольник
    )

    def refresh_list():
        alarms_list.controls.clear()
        with alarm_manager._lock:
            alarms_copy = list(alarm_manager.alarms)
        for alarm in alarms_copy:
            alarms_list.controls.append(_build_alarm_tile(alarm))
        try:
            alarms_list.update()
        except Exception:
            pass

    def _build_alarm_tile(alarm: Alarm) -> ft.Dismissible:
        toggle = ft.Switch(
            value        = alarm.enabled,
            active_color = ft.Colors.BLUE_400,
            on_change    = lambda e, aid = alarm.id: _on_toggle(aid),
        )

        tile = ft.Container(
            content = ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                alarm.label,
                                size   = 32,
                                weight = ft.FontWeight.BOLD,
                                color  = ft.Colors.WHITE,
                            ),
                            ft.Text(
                                alarm.days_label,
                                size  = 12,
                                color = ft.Colors.WHITE70,
                            ),
                        ],
                        spacing = 2,
                        tight   = True,
                    ),
                    toggle,
                ],
                alignment          = ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor       = ft.Colors.GREY_600,
            border_radius = 16,
            padding       = ft.padding.symmetric(horizontal = 20, vertical = 14),
        )

        return ft.Dismissible(
            content           = tile,
            dismiss_direction = ft.DismissDirection.END_TO_START,
            dismiss_thresholds = {ft.DismissDirection.END_TO_START: 0.3},
            background = ft.Container(
                content = ft.Row(
                    [ft.Icon(ft.Icons.DELETE, color = ft.Colors.WHITE)],
                    alignment = ft.MainAxisAlignment.END,
                ),
                bgcolor       = ft.Colors.RED_400,
                border_radius = 16,
                padding       = ft.padding.only(right = 20),
            ),
            on_dismiss = lambda e, aid = alarm.id: _on_delete(aid),
        )

    def _on_toggle(alarm_id: str):
        alarm_manager.toggle(alarm_id)
        refresh_list()

    def _on_delete(alarm_id: str):
        alarm_manager.remove(alarm_id)
        refresh_list()

    # ── Snackbar-хелпер ──────────────────────────────────────────────────────
    def show_error(msg: str):
        snack = ft.SnackBar(
            content  = ft.Text(msg),
            bgcolor  = ft.Colors.RED_700,
            duration = 4000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def show_info(msg: str):
        snack = ft.SnackBar(
            content  = ft.Text(msg),
            bgcolor  = ft.Colors.GREEN_700,
            duration = 3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # ── Диалог ручного добавления ────────────────────────────────────────────
    hour_field   = ft.TextField(label = "Час (0–23)",    keyboard_type = ft.KeyboardType.NUMBER, width = 120)
    minute_field = ft.TextField(label = "Минута (0–59)", keyboard_type = ft.KeyboardType.NUMBER, width = 120)
    dialog_error = ft.Text("", color = ft.Colors.RED_400, size = 12)

    add_dialog = ft.AlertDialog(
        modal = True,
        title = ft.Text("Новый будильник"),
    )
    page.overlay.append(add_dialog)

    def _open_add_dialog(e):
        hour_field.value   = ""
        minute_field.value = ""
        dialog_error.value = ""
        add_dialog.content = ft.Column(
            [ft.Row([hour_field, ft.Text(":"), minute_field]), dialog_error],
            tight = True, spacing = 8,
        )
        add_dialog.actions = [
            ft.TextButton("Отмена",     on_click = lambda e: _close_dialog()),
            ft.FilledButton("Добавить", on_click = _save_alarm),
        ]
        add_dialog.open = True
        page.update()

    def _close_dialog():
        add_dialog.open = False
        page.update()

    def _save_alarm(e):
        try:
            h = int(hour_field.value)
            m = int(minute_field.value)
            if not is_valid_time(h, m):
                raise ValueError("invalid time")
        except ValueError:
            dialog_error.value = "Введите корректное время (ч: 0–23, мин: 0–59)"
            page.update()
            return
        alarm_manager.add(Alarm(hour = h, minute = m))
        add_dialog.open = False
        refresh_list()
        page.update()

    # ── Авто-кнопка ──────────────────────────────────────────────────────────
    def _on_auto(e):
        pass

    # ── Кнопки внизу ─────────────────────────────────────────────────────────
    btn_auto = ft.Container(
        content       = ft.Text("Авто", size = 14, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
        bgcolor       = ft.Colors.BLUE_GREY_600,
        border_radius = 16,
        padding       = ft.padding.symmetric(horizontal = 20, vertical = 14),
        on_click      = _on_auto,
        ink           = True,
    )

    btn_add = ft.Container(
        content       = ft.Icon(ft.Icons.ADD, color = ft.Colors.WHITE),
        bgcolor       = ft.Colors.BLUE_200,
        border_radius = 16,
        width         = 54,
        height        = 54,
        alignment = ft.Alignment.CENTER,
        on_click      = _open_add_dialog,
        ink           = True,
    )

    bottom_row = ft.Container(
        content = ft.Row(
            [btn_auto, ft.Container(expand = True), btn_add],
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        padding = ft.padding.symmetric(horizontal = 16, vertical = 12),
    )

    # ── View ─────────────────────────────────────────────────────────────────
    return ft.View(
        route   = "/alarm",
        bgcolor = ft.Colors.TRANSPARENT,
        controls = [
            ft.Column(
                [
                    ft.Container(
                        padding = ft.padding.symmetric(horizontal = 16, vertical = 8),
                        content = ft.Column(
                            [
                                ft.Text("Будильники", size = 25, weight = ft.FontWeight.BOLD),
                                clock_text,
                            ],
                            spacing = 2,
                        ),
                    ),
                    alarms_list,   # expand=True — тянет оставшееся место
                    bottom_row,    # фиксированная высота, всегда снизу
                ],
                expand  = True,
                spacing = 0,
            )
        ],
        navigation_bar = navigation_bar,
        padding        = 0,
    )
