import flet as ft
import logging
import json
import pathlib
import sys
from models.alarm_model import Alarm, WEEK_ANY, WEEK_ODD, WEEK_EVEN, WEEK_NAMES
from managers.alarm_manager import AlarmManager
from managers.config_manager import ConfigManager

if sys.platform == 'win32':
    from bridges.planner_bridge import lib
    make_alarm = lib.make_alarm
else:
    from bridges.planner_bridge import make_alarm

logger = logging.getLogger(__name__)

_DAYS = [(1, "Пн"), (2, "Вт"), (3, "Ср"), (4, "Чт"), (5, "Пт"), (6, "Сб"), (7, "Вс")]
_WEEKS = [(WEEK_ANY, "Любая"), (WEEK_ODD, "Нечёт."), (WEEK_EVEN, "Чётная")]


def build_alarm_view(
    navigation_bar: ft.NavigationBar,
    clock_text: ft.Text,
    alarm_manager: AlarmManager,
    config_manager: ConfigManager,
    page: ft.Page,
    ) -> ft.View:

    # ── Список ────────
    alarms_column = ft.Column(spacing = 10, scroll = ft.ScrollMode.AUTO)

    alarms_container = ft.Container(
        content = alarms_column,
        expand = True,
        padding = ft.Padding.symmetric(horizontal = 16),
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
                        spacing = 2, tight = True,
                    ),
                    toggle,
                ],
                alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor = ft.Colors.GREY_700,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 20, vertical = 14),
            on_click = lambda e, a = alarm: _open_alarm_dialog(existing = a),
            ink = True,
        )

        return ft.Dismissible(
            content = tile,
            dismiss_direction  = ft.DismissDirection.END_TO_START,
            dismiss_thresholds = {ft.DismissDirection.END_TO_START: 0.3},
            background = ft.Container(
                content = ft.Row([ft.Icon(ft.Icons.DELETE, color = ft.Colors.WHITE)], alignment = ft.MainAxisAlignment.END),
                bgcolor = ft.Colors.RED_400,
                border_radius = 16,
                padding = ft.Padding.only(right = 20),
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
        title = ft.Text(""),
    )
    page.overlay.append(alarm_dialog)

    def _open_alarm_dialog(existing: Alarm | None = None):
        is_edit = existing is not None

        hour_f = ft.TextField(
            label = "Час (0–23)",
            value = str(existing.hour) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER, width = 110
        )

        minute_f = ft.TextField(
            label = "Минута (0–59)",
            value = str(existing.minute) if is_edit else "",
            keyboard_type = ft.KeyboardType.NUMBER, width = 110
        )

        error_t = ft.Text("", color = ft.Colors.RED_400, size = 12)

        selected_days: list[int] = list(existing.days) if is_edit else []
        selected_week: list[str] = [existing.week_type] if is_edit else [WEEK_ANY]

        # ── Кнопки дней ──────────────────────────────────────────────────────────
        day_btns: dict[int, ft.Container] = {}

        def _day_color(d):
            return ft.Colors.BLUE_400 if d in selected_days else ft.Colors.GREY_700

        def _toggle_day(d):
            if d in selected_days: selected_days.remove(d)
            else: selected_days.append(d)
            day_btns[d].bgcolor = _day_color(d)
            try: day_btns[d].update()
            except: pass

        def _make_day_btn(d, name):
            btn = ft.Container(
                    content=ft.Text(
                        name, 
                        size = 11, 
                        weight = ft.FontWeight.BOLD,
                        color = ft.Colors.WHITE
                    ),
                bgcolor = _day_color(d), border_radius = 20,
                width = 36, height = 36, alignment = ft.Alignment.CENTER,
                on_click = lambda e, day = d: _toggle_day(day), ink = True,
            )
            day_btns[d] = btn
            return btn

        days_row = ft.Row([_make_day_btn(d, n) for d, n in _DAYS], spacing = 4)

        # ── Кнопки чётности ───────────────────────────────────────────────────────
        week_btns: dict[str, ft.Container] = {}

        def _week_color(wt):
            return ft.Colors.BLUE_400 if wt == selected_week[0] else ft.Colors.GREY_700

        def _select_week(wt):
            selected_week[0] = wt
            for k, btn in week_btns.items():
                btn.bgcolor = _week_color(k)
                try: btn.update()
                except: pass

        def _make_week_btn(wt, name):
            btn = ft.Container(
                content = ft.Text(
                    name, 
                    size = 11, 
                    weight = ft.FontWeight.BOLD,
                    color = ft.Colors.WHITE
                ),
                bgcolor = _week_color(wt), border_radius = 12,
                padding = ft.Padding.symmetric(horizontal = 12, vertical = 8),
                on_click = lambda e, w = wt: _select_week(w), ink = True,
            )
            week_btns[wt] = btn
            return btn

        weeks_row = ft.Row(
            [_make_week_btn(wt, name) for wt, name in _WEEKS],
            spacing = 8,
        )

        # ── Сохранение ────────────────────────────────────────────────────────────
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
            wt = selected_week[0]

            if is_edit:
                alarm_manager.update(existing.id, h, m, days, wt)
            else:
                alarm_manager.add(Alarm(hour = h, minute = m, days = days, week_type = wt))

            alarm_dialog.open = False
            refresh_list()
            page.update()

        def _cancel(e):
            alarm_dialog.open = False
            page.update()

        alarm_dialog.title = ft.Text("Изменить будильник" if is_edit else "Новый будильник")
        alarm_dialog.content = ft.Column(
            [
                ft.Row([hour_f, ft.Text(":", size = 24, weight = ft.FontWeight.BOLD), minute_f],
                    vertical_alignment = ft.CrossAxisAlignment.CENTER, spacing = 8),
                ft.Container(height = 4),
                ft.Text("Повторять:", size = 13, color = ft.Colors.GREY_500),
                days_row,
                ft.Text("Неделя:", size = 13, color = ft.Colors.GREY_500),
                weeks_row,
                ft.Text("Дни не выбраны — каждый день", size = 11,
                        italic = True, color = ft.Colors.GREY_500),
                error_t,
            ],
            tight = True, spacing = 10, width = 300,
        )
        alarm_dialog.actions = [
            ft.TextButton("Отмена", on_click = _cancel),
            ft.FilledButton("Сохранить" if is_edit else "Добавить", on_click = _save),
        ]
        alarm_dialog.open = True
        page.update()

    # ── Snackbar ──────────────────────────────────────────────────────────────
    def show_info(msg: str):
        snack = ft.SnackBar(
            content = ft.Text(msg), 
            bgcolor = ft.Colors.GREEN_700, 
            duration = 3000
        )
        page.overlay.append(snack)
        snack.open = True
        
    def show_error(msg: str):
        snack = ft.SnackBar(
            content = ft.Text(msg),
            bgcolor = ft.Colors.RED_700,
            duration = 4000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # ── Авто ─────────────────────────────────────────────────────────────────
    def _on_auto(e):
        cfg = config_manager.config
        schedule_path = pathlib.Path.home() / ".pnipu_planner" / "schedule.json"

        if not schedule_path.exists():
            show_error("Расписание не загружено. Импортируйте xlsx в Настройках.")
            return

        try:
            with open(schedule_path, encoding = "utf-8") as f:
                schedule = json.load(f)
        except Exception:
            show_error("Не удалось прочитать файл расписания.")
            return

        if not schedule.get("odd") and not schedule.get("even"):
            show_error("Файл расписания пуст.")
            return

        if cfg.get_together_time <= 0:
            show_error("Укажите время на сборы в Настройках.")
            return

        if cfg.travel_time <= 0:
            show_error("Укажите время до ВУЗа в Настройках.")
            return

        # Дни с парами по типу недели
        odd_days: dict[int, int] = {}
        even_days: dict[int, int] = {}

        for lesson in schedule.get("odd", []):
            day = int(lesson["day"])
            try:
                h, m = map(int, lesson["time_start"].split(":"))
            except Exception:
                continue
            t = h * 60 + m
            if day not in odd_days or t < odd_days[day]:
                odd_days[day] = t

        for lesson in schedule.get("even", []):
            day = int(lesson["day"])
            try:
                h, m = map(int, lesson["time_start"].split(":"))
            except Exception:
                continue
            t = h * 60 + m
            if day not in even_days or t < even_days[day]:
                even_days[day] = t

        all_days = set(odd_days) | set(even_days)

        # Для каждого дня определяем week_type и время первой пары
        # alarm_key -> (hour, minute, week_type, days_list)
        alarm_map: dict[tuple, list[int]] = {}

        for day in all_days:
            in_odd = day in odd_days
            in_even = day in even_days

            if in_odd and in_even:
                week_type = WEEK_ANY
                first_lesson = min(odd_days[day], even_days[day])
            elif in_odd:
                week_type = WEEK_ODD
                first_lesson = odd_days[day]
            else:
                week_type = WEEK_EVEN
                first_lesson = even_days[day]

            fh = first_lesson // 60
            fm = first_lesson % 60
            alarm_mins = make_alarm(fh, fm, cfg.get_together_time, cfg.travel_time)
            alarm_mins = ((alarm_mins % 1440) + 1440) % 1440

            ah = alarm_mins // 60
            am = alarm_mins % 60
            key = (ah, am, week_type)

            if key not in alarm_map:
                alarm_map[key] = []
            alarm_map[key].append(day)

        # Добавляем, пропуская дубликаты
        with alarm_manager._lock:
            existing_keys = {
                (a.hour, a.minute, a.week_type, tuple(sorted(a.days)))
                for a in alarm_manager.alarms
            }

        added = 0
        for (ah, am, wt), days in alarm_map.items():
            days_sorted = sorted(days)
            key = (ah, am, wt, tuple(days_sorted))
            if key not in existing_keys:
                alarm_manager.add(Alarm(hour = ah, minute = am,
                                        days = days_sorted, week_type = wt))
                existing_keys.add(key)
                added += 1

        refresh_list()
        if added > 0:
            show_info(f"Добавлено {added} будильник(ов) по расписанию ✓")
        else:
            show_info("Все будильники по расписанию уже существуют")


    # ── Кнопки внизу ─────────────────────────────────────────────────────────
    btn_auto = ft.Container(
        content = ft.Text("Авто", size = 14, weight = ft.FontWeight.BOLD, color = ft.Colors.WHITE),
        bgcolor = ft.Colors.BLUE_GREY_600,
        border_radius = 16,
        padding = ft.Padding.symmetric(horizontal = 20, vertical = 14),
        on_click = _on_auto,
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
            [btn_auto, ft.Container(expand=True), btn_add],
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        padding = ft.Padding.symmetric(horizontal = 16, vertical = 12),
    )

    refresh_list()

    # ── View ─────────────────────────────────────────────────────────────────
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
                                    clock_text
                                ],
                                spacing = 2,
                            ),
                        ),
                        alarms_container,
                        bottom_row,
                    ],
                    expand = True, 
                    spacing = 0,
                )
            )
        ],
    )
