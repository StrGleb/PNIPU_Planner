import flet as ft
from models.alarm_model import Alarm
from managers.alarm_manager import AlarmManager


def build_alarm_view(
    navigation_bar: ft.NavigationBar,
    clock_text: ft.Text,
    alarm_manager: AlarmManager,
    page: ft.Page,
) -> ft.View:

    _mounted = {"value": False}

    # ---------- Список будильников ----------

    alarms_list = ft.ListView(spacing=10, padding=ft.padding.symmetric(horizontal=16))

    def refresh_list():
        alarms_list.controls.clear()
        with alarm_manager._lock:
            alarms_copy = list(alarm_manager.alarms)
        for alarm in alarms_copy:
            alarms_list.controls.append(_build_alarm_tile(alarm))
        if _mounted["value"]:
            alarms_list.update()

    def _build_alarm_tile(alarm: Alarm) -> ft.Dismissible:
        toggle = ft.Switch(
            value=alarm.enabled,
            active_color=ft.Colors.BLUE_400,
            on_change=lambda e, aid=alarm.id: _on_toggle(aid),
        )

        tile = ft.Container(
            content=ft.Row(
                [
                    ft.Text(alarm.label, size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    toggle,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.GREY_600,
            border_radius=16,
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
        )

        return ft.Dismissible(
            content=tile,
            dismiss_direction=ft.DismissDirection.END_TO_START,   # исправлено: direction → dismiss_direction
            dismiss_thresholds={ft.DismissDirection.END_TO_START: 0.3},
            background=ft.Container(
                content=ft.Row(
                    [ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE)],
                    alignment=ft.MainAxisAlignment.END,
                ),
                bgcolor=ft.Colors.RED_400,
                border_radius=16,
                padding=ft.padding.only(right=20),
            ),
            on_dismiss=lambda e, aid=alarm.id: _on_delete(aid),
        )

    def _on_toggle(alarm_id: str):
        alarm_manager.toggle(alarm_id)
        refresh_list()

    def _on_delete(alarm_id: str):
        alarm_manager.remove(alarm_id)
        refresh_list()

    # ---------- Диалог добавления будильника ----------

    hour_field = ft.TextField(
        label="Час (0-23)",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
    )
    minute_field = ft.TextField(
        label="Минута (0-59)",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
    )
    dialog_error = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _open_add_dialog(e):
        hour_field.value = ""
        minute_field.value = ""
        dialog_error.value = ""
        add_dialog.open = True
        page.update()

    def _close_dialog(e):
        add_dialog.open = False
        page.update()

    def _save_alarm(e):
        try:
            h = int(hour_field.value)
            m = int(minute_field.value)
            assert 0 <= h <= 23 and 0 <= m <= 59
        except (ValueError, AssertionError):
            dialog_error.value = "Введите корректное время (ч: 0-23, мин: 0-59)"
            page.update()
            return

        alarm_manager.add(Alarm(hour=h, minute=m))
        add_dialog.open = False
        page.update()
        refresh_list()

    add_dialog = ft.AlertDialog(
        title=ft.Text("Новый будильник"),
        content=ft.Column(
            [
                ft.Row([hour_field, ft.Text(":"), minute_field]),
                dialog_error,
            ],
            tight=True,
            spacing=8,
        ),
        actions=[
            ft.TextButton("Отмена", on_click=_close_dialog),
            ft.FilledButton("Добавить", on_click=_save_alarm),
        ],
    )
    page.overlay.append(add_dialog)

    # ---------- FAB ----------

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=ft.Colors.BLUE_200,
        foreground_color=ft.Colors.WHITE,
        on_click=_open_add_dialog,
    )

    # ---------- View ----------

    return ft.View(
        route="/alarm",
        floating_action_button=fab,
        controls=[
            ft.Column(
                [
                    ft.Text("Будильники", size=25, weight=ft.FontWeight.BOLD),
                    clock_text,
                    alarms_list,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        ],
        navigation_bar=navigation_bar,
    )