import flet as ft
import logging
from models.alarm_model import Alarm
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager

logger = logging.getLogger(__name__)

_DAYS = [(1, "Пн"), (2, "Вт"), (3, "Ср"), (4, "Чт"), (5, "Пт"), (6, "Сб"), (7, "Вс")]


def build_alarm_view(
    navigation_bar: ft.NavigationBar,
    clock_text: ft.Text,
    alarm_manager: AlarmManager,
    config_manager: ConfigManager,
    page: ft.Page,
    ) -> ft.View:

    # ── Список — Column+scroll вместо ListView (обходим баг с bgcolor) ────────
    alarms_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    alarms_container = ft.Container(
        content = alarms_column,
        expand  = True,
        padding = ft.padding.symmetric(horizontal=16),
    )

    def refresh_list():
        alarms_column.controls.clear()
        with alarm_manager._lock:
            alarms_copy = list(alarm_manager.alarms)
        for alarm in alarms_copy:
            alarms_column.controls.append(_build_alarm_tile(alarm))
        try:
            # alarms_column.update()
            page.update()
        except Exception as e:
            logger.error(f"Ошибка обновления списка будильников: {e}")

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
                            ft.Text(alarm.label,     size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.Text(alarm.days_label, size=12, color=ft.Colors.WHITE70),
                        ],
                        spacing=2, tight=True,
                    ),
                    toggle,
                ],
                alignment          = ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor       = ft.Colors.GREY_700,
            border_radius = 16,
            padding       = ft.padding.symmetric(horizontal=20, vertical=14),
            on_click      = lambda e, a = alarm: _open_alarm_dialog(existing=a),
            ink           = True,
        )

        return ft.Dismissible(
            content            = tile,
            dismiss_direction  = ft.DismissDirection.END_TO_START,
            dismiss_thresholds = {ft.DismissDirection.END_TO_START: 0.3},
            background = ft.Container(
                content       = ft.Row([ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE)],
                                       alignment=ft.MainAxisAlignment.END),
                bgcolor       = ft.Colors.RED_400,
                border_radius = 16,
                padding       = ft.padding.only(right=20),
            ),
            on_dismiss = lambda e, aid = alarm.id: _on_delete(aid),
        )

    def _on_toggle(alarm_id: str):
        alarm_manager.toggle(alarm_id)
        refresh_list()

    def _on_delete(alarm_id: str):
        alarm_manager.remove(alarm_id)
        refresh_list()

    # ── Диалог (один экземпляр) ───────────────────────────────────────────────
    alarm_dialog = ft.AlertDialog(
        modal = True,
        title = ft.Text(""),   # перезаписывается в _open_alarm_dialog
    )
    page.overlay.append(alarm_dialog)

    def _open_alarm_dialog(existing: Alarm | None = None):
        is_edit = existing is not None

        hour_f = ft.TextField(
            label         = "Час (0–23)",
            value         = str(existing.hour)   if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER,
            width         = 110,
        )
        minute_f = ft.TextField(
            label         = "Минута (0–59)",
            value         = str(existing.minute) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER,
            width         = 110,
        )
        error_t = ft.Text("", color=ft.Colors.RED_400, size=12)

        selected_days: list[int] = list(existing.days) if is_edit else []
        day_containers: dict[int, ft.Container] = {}

        def _day_bgcolor(d: int) -> str:
            return ft.Colors.BLUE_400 if d in selected_days else ft.Colors.GREY_700

        def _toggle_day(day_num: int):
            if day_num in selected_days:
                selected_days.remove(day_num)
            else:
                selected_days.append(day_num)
            btn = day_containers[day_num]
            btn.bgcolor = _day_bgcolor(day_num)
            try:
                btn.update()
            except Exception as e:
                logger.error(f"Ошибка переключения дня: {e}")

        def _make_day_btn(day_num: int, name: str) -> ft.Container:
            btn = ft.Container(
                content       = ft.Text(name, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor       = _day_bgcolor(day_num),
                border_radius = 20,
                width         = 36,
                height        = 36,
                alignment     = ft.Alignment.CENTER,   # ← исправлено
                on_click      = lambda e, d = day_num: _toggle_day(d),
                ink           = True,
            )
            day_containers[day_num] = btn
            return btn

        days_row = ft.Row([_make_day_btn(d, n) for d, n in _DAYS], spacing=4)

        def _save(e):
            try:
                h = int(hour_f.value)
                m = int(minute_f.value)
                assert 0 <= h <= 23 and 0 <= m <= 59
            except (ValueError, AssertionError):
                error_t.value = "Введите корректное время (ч: 0–23, мин: 0–59)"
                page.update()
                return
            days = sorted(selected_days)
            if is_edit:
                alarm_manager.update(existing.id, h, m, days)
            else:
                alarm_manager.add(Alarm(hour=h, minute=m, days=days))
            alarm_dialog.open = False
            refresh_list()
            page.update()

        def _cancel(e):
            alarm_dialog.open = False
            page.update()

        alarm_dialog.title   = ft.Text("Изменить будильник" if is_edit else "Новый будильник")
        alarm_dialog.content = ft.Column(
            [
                ft.Row(
                    [hour_f, ft.Text(":", size=24, weight=ft.FontWeight.BOLD), minute_f],
                    vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    spacing            = 8,
                ),
                ft.Container(height=4),
                ft.Text("Повторять:", size=13, color=ft.Colors.GREY_500),
                days_row,
                ft.Text("Не выбрано — каждый день", size=11, italic=True, color=ft.Colors.GREY_500),
                error_t,
            ],
            tight=True, spacing=10, width=280,
        )
        alarm_dialog.actions = [
            ft.TextButton("Отмена",                                    on_click=_cancel),
            ft.FilledButton("Сохранить" if is_edit else "Добавить",   on_click=_save),
        ]
        alarm_dialog.open = True
        page.update()

    # ── Snackbar ──────────────────────────────────────────────────────────────
    def show_info(msg: str):
        snack = ft.SnackBar(content=ft.Text(msg), bgcolor=ft.Colors.GREEN_700, duration=3000)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # ── Авто ─────────────────────────────────────────────────────────────────
    def _on_auto(e):
        print("Кнопка Авто")
        ...

    # ── Кнопки внизу ─────────────────────────────────────────────────────────
    btn_auto = ft.Container(
        content = ft.Text("Авто", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor       = ft.Colors.BLUE_GREY_600,
        border_radius = 16,
        padding       = ft.padding.symmetric(horizontal=20, vertical=14),
        on_click      = _on_auto,
        ink           = True,
    )

    btn_add = ft.Container(
        content       = ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE),
        bgcolor       = ft.Colors.BLUE_200,
        border_radius = 16,
        width         = 54,
        height        = 54,
        alignment     = ft.Alignment.CENTER,   # ← исправлено
        on_click      = lambda e: _open_alarm_dialog(existing=None),
        ink           = True,
    )

    bottom_row = ft.Container(
        content = ft.Row(
            [btn_auto, ft.Container(expand=True), btn_add],
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        padding = ft.padding.symmetric(horizontal=16, vertical=12),
    )

    refresh_list()

    # ── View ─────────────────────────────────────────────────────────────────
    return ft.View(
        route  = "/alarm",
        controls = [
            ft.Column(
                [
                    ft.Container(
                        padding = ft.padding.symmetric(horizontal=16, vertical=8),
                        content = ft.Column(
                            [ft.Text("Будильники", size=25, weight=ft.FontWeight.BOLD), clock_text],
                            spacing=2,
                        ),
                    ),
                    alarms_container,   # ← Container вместо ListView
                    bottom_row,
                ],
                expand=True, spacing=0,
            )
        ],
        navigation_bar = navigation_bar,
        padding        = 0,
    )