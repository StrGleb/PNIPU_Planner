import asyncio
import calendar
import datetime
import inspect
import threading
from typing import Any, Callable

import flet as ft

from bridges.planner_bridge import (
    is_week_even,
    normalize_end_minutes_for_day_span,
    time_to_minutes,
)
from managers.config_manager import ConfigManager
from managers.notification_manager import check_and_notify
from managers.planner_manager import PlannerManager
from managers.tasks_manager import TasksManager
from models.lesson_model import (
    DEFAULT_EVENT_REMINDER_LEAD_MINUTES,
    Lesson,
    normalize_event_reminder_lead_minutes,
)
from models.task_model import TASK_TYPE_HOMEWORK, TASK_TYPE_LAB, TASK_TYPE_TEST

HOUR_HEIGHT = 80
START_HOUR = 8
END_HOUR = 24
TIME_COL_W = 52
WEEK_BADGE_WIDTH = 72

# ── Окраска блоков пар в планере ────────────────────────────────────────────────────────
PRIORITY_COLORS = {
    0: ft.Colors.GREY_400,
    1: ft.Colors.BLUE_400,
    2: ft.Colors.ORANGE_400,
    3: ft.Colors.RED_400,
}

_SUBJECT_PALETTE = [
    (ft.Colors.GREEN_200, ft.Colors.GREEN_50, ft.Colors.GREEN_400, ft.Colors.GREEN_900, ft.Colors.GREEN_700),
    (ft.Colors.BLUE_200, ft.Colors.BLUE_50, ft.Colors.BLUE_400, ft.Colors.BLUE_900, ft.Colors.BLUE_700),
    (ft.Colors.PURPLE_200, ft.Colors.PURPLE_50, ft.Colors.PURPLE_400, ft.Colors.PURPLE_900, ft.Colors.PURPLE_700),
    (ft.Colors.ORANGE_200, ft.Colors.ORANGE_50, ft.Colors.ORANGE_400, ft.Colors.ORANGE_900, ft.Colors.ORANGE_700),
    (ft.Colors.PINK_200, ft.Colors.PINK_50, ft.Colors.PINK_400, ft.Colors.PINK_900, ft.Colors.PINK_700),
    (ft.Colors.TEAL_200, ft.Colors.TEAL_50, ft.Colors.TEAL_400, ft.Colors.TEAL_900, ft.Colors.TEAL_700),
    (ft.Colors.RED_200, ft.Colors.RED_50, ft.Colors.RED_400, ft.Colors.RED_900, ft.Colors.RED_700),
    (ft.Colors.CYAN_200, ft.Colors.CYAN_50, ft.Colors.CYAN_400, ft.Colors.CYAN_900, ft.Colors.CYAN_700),
]

def _subject_colors(subject: str) -> tuple:
    """Возвращает (gradient_start, gradient_end, border, text, time) по названию предмета"""
    base = subject.split("(")[0].split("|")[0].strip()
    idx = hash(base) % len(_SUBJECT_PALETTE)
    return _SUBJECT_PALETTE[idx]


def _subject_gradient(subject: str) -> ft.LinearGradient:
    gradient_start, gradient_end, *_ = _subject_colors(subject)
    return ft.LinearGradient(
        begin = ft.Alignment(-1, -1),
        end = ft.Alignment(1, 1),
        colors = [gradient_start, gradient_end],
    )


def build_planner_view(
    navigation_bar: ft.NavigationBar,
    planner_manager: PlannerManager,
    config_manager: ConfigManager,
    tasks_manager: TasksManager,
    auto_alarm_service: Any,
    page: ft.Page,
    on_tasks_changed: Callable[[], None] | None = None,
) -> tuple[ft.View, Callable]:
    state = {
        "date": datetime.date.today(),
        "mode": "day",
        "task_filter": "all",
        "task_sort": "date",
        "focus_date": None,
        "focus_origin_mode": None,
    }
    detail_state = {"lesson_id": None}
    refresh_screen = {"fn": None}

    def safe_update(*controls):
        for control in controls:
            try:
                control.update()
            except Exception:
                pass

    def run_page_call(result):
        if inspect.isawaitable(result):
            try:
                asyncio.create_task(result)
            except RuntimeError:
                pass

    def run_in_background(task: Callable[[], None]) -> None:
        runner = getattr(page, "run_thread", None)
        if callable(runner):
            try:
                runner(task)
                return
            except Exception:
                pass

        threading.Thread(
            target = task,
            daemon = True,
            name = "planner-background-task",
        ).start()

    def sync_auto_alarm(changed_dates: list[datetime.date] | None = None):
        try:
            enqueue_change = getattr(auto_alarm_service, "enqueue_planner_change", None)
            if callable(enqueue_change):
                enqueue_change(changed_dates)
                return

            if changed_dates:
                run_in_background(lambda: auto_alarm_service.handle_planner_change_for_dates(changed_dates))
            else:
                run_in_background(auto_alarm_service.handle_planner_change)
        except Exception:
            pass

    def refresh_task_views():
        try:
            tasks_manager.refresh_all_ratings()
        except Exception:
            pass

        try:
            check_and_notify(tasks_manager)
        except Exception:
            pass

        refresh_fn = refresh_screen.get("fn")
        if refresh_fn is not None:
            try:
                refresh_fn()
            except Exception:
                pass

        if on_tasks_changed is None:
            return

        try:
            on_tasks_changed()
        except Exception:
            pass

    def normalize_time_range(time_start: str, time_end: str) -> tuple[int, int]:
        start_minutes = time_to_minutes(time_start)
        end_minutes = time_to_minutes(time_end)
        if start_minutes < 0 or end_minutes < 0:
            raise ValueError("invalid_time")

        normalized_end_minutes = normalize_end_minutes_for_day_span(start_minutes, end_minutes)
        if normalized_end_minutes <= start_minutes:
            raise ValueError("invalid_range")

        return start_minutes, normalized_end_minutes

    def active_date() -> datetime.date:
        return state["focus_date"] or state["date"]

    def fmt_day(date_value: datetime.date) -> str:
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return f"{names[date_value.weekday()]}  {date_value.strftime('%d.%m')}"

    def week_label() -> str:
        try:
            even = is_week_even(
                active_date(),
                config_manager.config.semester_start,
                config_manager.config.first_week_even,
            )
        except Exception:
            even = active_date().isocalendar()[1] % 2 == 0
        return "ЧЕТ" if even else "НЕЧЕТ"

    def start_of_week(date_value: datetime.date) -> datetime.date:
        return date_value - datetime.timedelta(days = date_value.weekday())

    def shift_month(date_value: datetime.date, delta: int) -> datetime.date:
        month_index = date_value.year * 12 + (date_value.month - 1) + delta
        year = month_index // 12
        month = month_index % 12 + 1
        day = min(date_value.day, calendar.monthrange(year, month)[1])
        return datetime.date(year, month, day)

    def current_mode_title() -> str:
        if state["focus_date"] is not None:
            return "День"
        return {
            "day": "Календарь",
            "week": "Неделя",
            "month": "Месяц",
            "tasks": "Все задачи",
        }.get(state["mode"], "Календарь")

    def current_mode_subtitle() -> str:
        if state["focus_date"] is not None:
            return active_date().strftime("%d.%m.%Y")
        if state["mode"] == "day":
            return fmt_day(state["date"])
        if state["mode"] == "week":
            week_start = start_of_week(state["date"])
            week_end = week_start + datetime.timedelta(days = 6)
            return f"{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}"
        if state["mode"] == "month":
            return state["date"].strftime("%m.%Y")
        return "Домашки, контрольные и лабораторные"

    def is_tasks_mode() -> bool:
        return state["focus_date"] is None and state["mode"] == "tasks"

    add_dialog = ft.AlertDialog(modal = True, title = ft.Text("Новое событие"))
    input_dialog = ft.AlertDialog(modal = True, title = ft.Text(""))
    detail_sheet = ft.BottomSheet(
        content = ft.Container(ft.Text(""), padding = 16),
        dismissible = True,
        on_dismiss = lambda e: detail_state.__setitem__("lesson_id", None),
    )
    page.overlay.append(detail_sheet)

    def cleanup():
        if detail_sheet in page.overlay:
            try:
                page.overlay.remove(detail_sheet)
            except Exception:
                pass

    def close_detail_sheet():
        detail_state["lesson_id"] = None
        detail_sheet.open = False
        page.update()

    def show_dialog(dialog: ft.AlertDialog):
        dialog.open = True
        run_page_call(page.show_dialog(dialog))
        page.update()

    def open_drawer_menu():
        run_page_call(page.show_drawer())

    def close_drawer_menu():
        run_page_call(page.close_drawer())

    def open_event_dialog(existing: Lesson | None = None, e = None):
        form_scroll_host = ft.Column(
            tight = True,
            spacing = 10,
            scroll = ft.ScrollMode.AUTO,
        )
        initial_date = existing.date if existing is not None else active_date()
        initial_address = (existing.address if existing is not None else "").strip()
        initial_description = (existing.description if existing is not None else "").strip()
        initial_subject = (existing.subject if existing is not None else "").strip()
        initial_start = (existing.time_start if existing is not None else "").strip()
        initial_end = (existing.time_end if existing is not None else "").strip()
        initial_reminder_enabled = bool(existing.reminder_enabled) if existing is not None else False

        date_field = ft.TextField(label = "Дата ДД.ММ.ГГГГ", value = initial_date.strftime("%d.%m.%Y"))
        start_field = ft.TextField(label = "Начало ЧЧ:ММ", expand = True, value = initial_start)
        end_field = ft.TextField(label = "Конец ЧЧ:ММ", expand = True, value = initial_end)
        subject_field = ft.TextField(label = "Название события", value = initial_subject)
        description_field = ft.TextField(
            label = "Описание",
            multiline = True,
            min_lines = 2,
            max_lines = 4,
            value = initial_description,
        )
        custom_address_checkbox = ft.Checkbox(value = bool(initial_address))
        custom_address_field = ft.TextField(
            label = "Адрес прибытия",
            multiline = True,
            min_lines = 2,
            max_lines = 3,
            visible = bool(initial_address),
            value = initial_address,
        )
        reminder_checkbox = ft.Checkbox(value = initial_reminder_enabled)
        error_text = ft.Text("", color = ft.Colors.RED_400, size = 12)
        form_sections = {
            "date": ft.Container(key = "date_field", content = date_field),
            "time": ft.Container(
                key = "time_field",
                content = ft.Row([start_field, ft.Text(" - "), end_field]),
            ),
            "subject": ft.Container(key = "subject_field", content = subject_field),
            "description": ft.Container(key = "description_field", content = description_field),
            "custom_address": ft.Container(key = "custom_address_field", content = custom_address_field),
        }

        custom_address_row = ft.Row(
            [
                custom_address_checkbox,
                ft.Text(
                    "Указать другой адрес прибытия",
                    expand = True,
                    no_wrap = False,
                    size = 14,
                ),
            ],
            spacing = 6,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        )
        reminder_row = ft.Row(
            [
                reminder_checkbox,
                ft.Text(
                    "Включить уведомление о событии",
                    expand = True,
                    no_wrap = False,
                    size = 14,
                ),
            ],
            spacing = 6,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        )

        def on_custom_address_toggle(e):
            custom_address_field.visible = bool(e.control.value)
            if not custom_address_field.visible:
                custom_address_field.value = ""
            safe_update(custom_address_field, form_scroll_host)
            if custom_address_field.visible:
                run_page_call(form_scroll_host.scroll_to(key = "custom_address_field", duration = 180))

        def on_reminder_toggle(_):
            return None

        def on_field_focus(section_key: str):
            def handler(_):
                run_page_call(form_scroll_host.scroll_to(key = section_key, duration = 180))
            return handler

        date_field.on_focus = on_field_focus("date_field")
        start_field.on_focus = on_field_focus("time_field")
        end_field.on_focus = on_field_focus("time_field")
        subject_field.on_focus = on_field_focus("subject_field")
        description_field.on_focus = on_field_focus("description_field")
        custom_address_field.on_focus = on_field_focus("custom_address_field")

        custom_address_checkbox.on_change = on_custom_address_toggle
        reminder_checkbox.on_change = on_reminder_toggle

        def save(_):
            try:
                lesson_date = datetime.datetime.strptime(date_field.value.strip(), "%d.%m.%Y").date()
                time_start = start_field.value.strip()
                time_end = end_field.value.strip()
                normalize_time_range(time_start, time_end)
                subject = subject_field.value.strip()
                if not subject:
                    raise ValueError("empty_subject")
            except Exception:
                error_text.value = "Проверь дату и время. Формат: ДД.ММ.ГГГГ и ЧЧ:ММ."
                page.update()
                return

            address_value = (custom_address_field.value or "").strip() if custom_address_checkbox.value else ""
            changed_dates = [lesson_date]
            if existing is None:
                planner_manager.add_custom_event(
                    date = lesson_date,
                    time_start = time_start,
                    time_end = time_end,
                    subject = subject,
                    description = (description_field.value or "").strip(),
                    address = address_value,
                    reminder_enabled = bool(reminder_checkbox.value),
                    reminder_lead_minutes = DEFAULT_EVENT_REMINDER_LEAD_MINUTES,
                )
            else:
                previous_date = existing.date
                updated = planner_manager.update_custom_event(
                    existing.id,
                    date = lesson_date,
                    time_start = time_start,
                    time_end = time_end,
                    subject = subject,
                    description = (description_field.value or "").strip(),
                    address = address_value,
                    reminder_enabled = bool(reminder_checkbox.value),
                    reminder_lead_minutes = normalize_event_reminder_lead_minutes(existing.reminder_lead_minutes),
                )
                if updated is None:
                    error_text.value = "Событие не найдено."
                    page.update()
                    return
                changed_dates = [previous_date, lesson_date]

            add_dialog.open = False
            sync_auto_alarm(changed_dates)
            page.update()
            rebuild_view()
            if existing is not None:
                render_detail(existing.id)

        def cancel(_):
            add_dialog.open = False
            page.update()

        add_dialog.title = ft.Text("Изменить событие" if existing is not None else "Новое событие")
        form_scroll_host.controls = [
            form_sections["date"],
            form_sections["time"],
            form_sections["subject"],
            form_sections["description"],
            custom_address_row,
            form_sections["custom_address"],
            reminder_row,
            error_text,
        ]
        add_dialog.content = ft.Container(
            width = 320,
            height = min(max(getattr(page, "height", 640) * 0.58, 260), 420),
            content = form_scroll_host,
        )
        add_dialog.actions = [
            ft.TextButton("Отмена", on_click = cancel),
            ft.FilledButton("Сохранить" if existing is not None else "Добавить", on_click = save),
        ]
        show_dialog(add_dialog)

    def open_add_dialog(e = None):
        open_event_dialog(None, e)

    def open_input_dialog(title: str, on_save: Callable[[str, int], None], submit_label: str = "Добавить"):
        field = ft.TextField(label = title, autofocus = True)
        error_text = ft.Text("", color = ft.Colors.RED_400, size = 12)
        priority_dropdown = ft.Dropdown(
            value = "0",
            options = [
                ft.DropdownOption(key = "0", text = "0 - Обычная"),
                ft.DropdownOption(key = "1", text = "1 - Важная"),
                ft.DropdownOption(key = "2", text = "2 - Срочная"),
                ft.DropdownOption(key = "3", text = "3 - Критическая"),
            ],
            width = 220,
        )

        def save(_):
            text = (field.value or "").strip()
            if not text:
                error_text.value = "Поле не может быть пустым."
                page.update()
                return

            input_dialog.open = False
            page.update()
            on_save(text, int(priority_dropdown.value or "0"))

        def cancel(_):
            input_dialog.open = False
            page.update()

        input_dialog.title = ft.Text(title)
        input_dialog.content = ft.Column(
            [field, ft.Text("Приоритет:", size = 13), priority_dropdown, error_text],
            tight = True,
            spacing = 8,
            width = 280,
        )
        input_dialog.actions = [
            ft.TextButton("Отмена", on_click = cancel),
            ft.FilledButton(submit_label, on_click = save),
        ]
        show_dialog(input_dialog)

    def render_detail(lesson_id: str):
        current = planner_manager.get_lesson(lesson_id)
        if current is None:
            close_detail_sheet()
            return

        detail_state["lesson_id"] = lesson_id

        def delete_task(task):
            tasks_manager.remove_task(task.id)
            if task.task_type == TASK_TYPE_HOMEWORK and task.text in current.homeworks:
                current.homeworks.remove(task.text)
            elif task.task_type == TASK_TYPE_TEST and task.text in current.test_works:
                current.test_works.remove(task.text)
            elif task.task_type == TASK_TYPE_LAB and task.text in current.lab_works:
                current.lab_works.remove(task.text)
            refresh_task_views()
            render_detail(current.id)

        def open_edit_task_dialog(task):
            def save_edit(text: str, priority: int):
                tasks_manager.update_task(task.id, text, priority)
                refresh_task_views()
                render_detail(current.id)

            open_input_dialog("Редактировать задачу", save_edit, submit_label = "Сохранить")
            if isinstance(input_dialog.content, ft.Column):
                edit_field = input_dialog.content.controls[0]
                priority_dropdown = input_dialog.content.controls[2]
                if isinstance(edit_field, ft.TextField):
                    edit_field.value = task.text
                if isinstance(priority_dropdown, ft.Dropdown):
                    priority_dropdown.value = str(task.priority)
                page.update()

        def task_row(task) -> ft.Row:
            return ft.Row(
                [
                    ft.Container(
                        width = 10,
                        height = 10,
                        border_radius = 5,
                        bgcolor = PRIORITY_COLORS.get(task.priority, ft.Colors.GREY_400),
                    ),
                    ft.Text(task.text, size = 13, expand = True),
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED,
                        icon_size = 16,
                        on_click = lambda e, task_item = task: open_edit_task_dialog(task_item),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size = 16,
                        icon_color = ft.Colors.RED_400,
                        on_click = lambda e, task_item = task: delete_task(task_item),
                    ),
                ],
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
                spacing = 4,
            )

        def section(label: str, tasks: list, on_add: Callable):
            items = [task_row(task) for task in tasks] if tasks else [
                ft.Text("Нет записей.", size = 13, color = ft.Colors.GREY_500, italic = True)
            ]
            return [
                ft.Row(
                    [
                        ft.Text(label, size = 14, weight = ft.FontWeight.W_600, expand = True),
                        ft.IconButton(ft.Icons.ADD, on_click = on_add, icon_size = 20),
                    ]
                ),
                *items,
                ft.Divider(),
            ]

        all_tasks = tasks_manager.get_tasks_for_lesson(current.id)
        homework_tasks = [task for task in all_tasks if task.task_type == TASK_TYPE_HOMEWORK]
        test_tasks = [task for task in all_tasks if task.task_type == TASK_TYPE_TEST]
        lab_tasks = [task for task in all_tasks if task.task_type == TASK_TYPE_LAB]

        def after_add_task(task_type: str, text: str, priority: int = 0):
            lesson_item = planner_manager.get_lesson(current.id)
            if lesson_item is None:
                return

            if task_type == TASK_TYPE_HOMEWORK:
                planner_manager.add_homework(current.id, text)
            elif task_type == TASK_TYPE_TEST:
                planner_manager.add_test_work(current.id, text)
            elif task_type == TASK_TYPE_LAB:
                planner_manager.add_lab_work(current.id, text)

            tasks_manager.add_task(
                task_type = task_type,
                date_str = lesson_item.date_str,
                time_start = lesson_item.time_start,
                subject = lesson_item.subject,
                text = text,
                lesson_id = current.id,
                priority = priority,
            )
            refresh_task_views()
            render_detail(current.id)

        def add_homework(_):
            open_input_dialog(
                "Домашняя работа",
                lambda text, priority: after_add_task(TASK_TYPE_HOMEWORK, text, priority),
            )

        def add_test(_):
            open_input_dialog(
                "Контрольная работа",
                lambda text, priority: after_add_task(TASK_TYPE_TEST, text, priority),
            )

        def add_lab(_):
            open_input_dialog(
                "Лабораторная работа",
                lambda text, priority: after_add_task(TASK_TYPE_LAB, text, priority),
            )

        def delete_lesson(_):
            changed_dates = [current.date]
            tasks_manager.remove_tasks_for_lesson(current.id)
            planner_manager.remove_lesson(current.id)
            detail_state["lesson_id"] = None
            detail_sheet.open = False
            sync_auto_alarm(changed_dates)
            refresh_task_views()
            page.update()
            rebuild_view()

        def edit_event(_):
            detail_sheet.open = False
            page.update()
            open_event_dialog(current)

        lesson_meta: list[ft.Control] = []
        if current.description:
            lesson_meta.append(ft.Text(f"Описание: {current.description}", size = 13, color = ft.Colors.GREY_700))
        if current.teacher:
            lesson_meta.append(ft.Text(f"Преподаватель: {current.teacher}", size = 13, color = ft.Colors.GREY_700))
        if current.location_text:
            lesson_meta.append(ft.Text(f"Локация: {current.location_text}", size = 13, color = ft.Colors.GREY_700))
        if current.auditorium:
            lesson_meta.append(ft.Text(f"Аудитория: {current.auditorium}", size = 13, color = ft.Colors.GREY_700))
        if current.building:
            lesson_meta.append(ft.Text(f"Корпус: {current.building}", size = 13, color = ft.Colors.GREY_700))
        if current.is_event:
            reminder_label = (
                f"Напоминание: за {normalize_event_reminder_lead_minutes(current.reminder_lead_minutes)} мин."
                if current.reminder_enabled
                else "Напоминание: выключено"
            )
            lesson_meta.append(ft.Text(reminder_label, size = 13, color = ft.Colors.GREY_700))

        task_sections: list[ft.Control] = []
        if not current.is_event:
            task_sections = [
                *section("Домашние работы:", homework_tasks, add_homework),
                *section("Контрольные работы:", test_tasks, add_test),
                *section("Лабораторные работы:", lab_tasks, add_lab),
            ]

        event_actions: list[ft.Control] = []
        if current.is_custom and current.is_event:
            event_actions = [
                ft.OutlinedButton(
                    "Изменить событие",
                    on_click = edit_event,
                    expand = True,
                )
            ]

        detail_sheet.content = ft.Container(
            content = ft.Column(
                [
                    ft.Text(current.subject, size = 18, weight = ft.FontWeight.BOLD),
                    ft.Text(
                        f"{current.date_str}   {current.time_start} - {current.time_end}",
                        size = 13,
                        color = ft.Colors.GREY_600,
                    ),
                    *lesson_meta,
                    ft.Divider(),
                    *event_actions,
                    *task_sections,
                    ft.ElevatedButton(
                        "Удалить событие" if current.is_event else "Удалить пару",
                        bgcolor = ft.Colors.RED_400,
                        color = ft.Colors.WHITE,
                        on_click = delete_lesson,
                        expand = True,
                    ),
                ],
                scroll = ft.ScrollMode.AUTO,
                spacing = 6,
            ),
            padding = 16,
            height = 450,
        )
        detail_sheet.open = True
        try:
            detail_sheet.update()
        except Exception:
            page.update()

    def open_detail(lesson: Lesson):
        render_detail(lesson.id)

    def build_grid() -> ft.Column:
        total_height = (END_HOUR - START_HOUR) * HOUR_HEIGHT
        rows = []
        for offset in range(END_HOUR - START_HOUR):
            hour = START_HOUR + offset
            rows.append(
                ft.Row(
                    [
                        ft.Container(
                            content = ft.Text(f"{hour:02d}:00", size = 11, color = ft.Colors.GREY_500),
                            width = TIME_COL_W,
                            height = HOUR_HEIGHT,
                            alignment = ft.Alignment(x = 1.0, y = -1.0),
                            padding = ft.Padding.only(right = 8, top = 2),
                        ),
                        ft.Container(
                            expand = True,
                            height = HOUR_HEIGHT,
                            border = ft.Border.only(top = ft.BorderSide(0.5, ft.Colors.GREY_300)),
                        ),
                    ],
                    spacing = 0,
                    height = HOUR_HEIGHT,
                    vertical_alignment = ft.CrossAxisAlignment.START,
                )
            )
        return ft.Column(rows, spacing = 0, height = total_height)

    def build_lesson_block(lesson: Lesson) -> ft.Container:
        try:
            start_total_minutes, end_total_minutes = normalize_time_range(lesson.time_start, lesson.time_end)
            start_minutes = start_total_minutes - START_HOUR * 60
            end_minutes = end_total_minutes - START_HOUR * 60
            if start_minutes < 0 or end_minutes <= start_minutes:
                raise ValueError("invalid_time")
            top_px = start_minutes / 60 * HOUR_HEIGHT
            height_px = max((end_minutes - start_minutes) / 60 * HOUR_HEIGHT, 36)
        except Exception:
            return ft.Container()
        
        _, _, border_color, title_color, time_color = _subject_colors(lesson.subject)

        return ft.Container(
            content = ft.Column(
                [
                    ft.Text(
                        f"{lesson.time_start} - {lesson.time_end}",
                        size = 11,
                        weight = ft.FontWeight.BOLD,
                        color = time_color,
                    ),
                    ft.Text(
                        lesson.subject,
                        size = 13,
                        weight = ft.FontWeight.BOLD,
                        color = title_color,
                        overflow = ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        lesson.location_text,
                        size = 11,
                        color = time_color,
                        overflow = ft.TextOverflow.ELLIPSIS,
                    ) if lesson.location_text else ft.Container(),
                ],
                spacing = 2,
                tight = True,
            ),
            gradient = _subject_gradient(lesson.subject),
            border = ft.Border.all(1, border_color),
            border_radius = 8,
            padding = ft.Padding.symmetric(horizontal = 8, vertical = 6),
            top = top_px,
            left = TIME_COL_W + 4,
            right = 8,
            height = height_px,
            on_click = lambda e, lesson_item = lesson: open_detail(lesson_item),
            ink = True,
        )

    def build_lesson_list_item(lesson: Lesson) -> ft.Container:
        _, _, border_color, title_color, meta_color = _subject_colors(lesson.subject)

        return ft.Container(
            content = ft.Column(
                [
                    ft.Text(
                        f"{lesson.time_start} - {lesson.time_end}",
                        size = 11,
                        weight = ft.FontWeight.BOLD,
                        color = meta_color,
                    ),
                    ft.Text(lesson.subject, size = 14, weight = ft.FontWeight.BOLD, color = title_color),
                    ft.Text(
                        lesson.location_text or "Без указания аудитории",
                        size = 12,
                        color = meta_color,
                        overflow = ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing = 2,
                tight = True,
            ),
            gradient = _subject_gradient(lesson.subject),
            border = ft.Border.all(1, border_color),
            border_radius = 12,
            padding = 12,
            width = float("inf"),
            on_click = lambda e, lesson_item = lesson: open_detail(lesson_item),
            ink = True,
        )

    def build_timeline_stack_for(date_value: datetime.date) -> ft.Stack:
        total_height = (END_HOUR - START_HOUR) * HOUR_HEIGHT
        blocks = [build_grid()]
        for lesson in planner_manager.get_lessons_for_date(date_value):
            blocks.append(build_lesson_block(lesson))
        return ft.Stack(blocks, height = total_height)

    def build_timeline_stack() -> ft.Stack:
        return build_timeline_stack_for(state["date"])

    def build_mode_nav(prev_handler: Callable, next_handler: Callable) -> ft.Row:
        return ft.Row(
            [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click = prev_handler, icon_size = 22),
                ft.Container(expand = True),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click = next_handler, icon_size = 22),
            ],
            alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
            spacing = 0,
        )

    def build_day_content() -> ft.Column:
        return ft.Column(
            [
                build_mode_nav(prev_day, next_day),
                ft.Column(
                    [build_timeline_stack()],
                    expand = True,
                    spacing = 0,
                    scroll = ft.ScrollMode.AUTO,
                ),
            ],
            expand = True,
            spacing = 0,
        )

    def build_focus_day_content() -> ft.Column:
        focus_date = active_date()
        origin_mode = "неделе" if state["focus_origin_mode"] == "week" else "месяцу"

        return ft.Column(
            [
                ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 4, vertical = 6),
                    content = ft.Row(
                        [
                            ft.IconButton(ft.Icons.ARROW_BACK, on_click = lambda e: close_day_focus(), icon_size = 20),
                            ft.TextButton(
                                f"Назад к {origin_mode}",
                                on_click = lambda e: close_day_focus(),
                            ),
                            ft.Container(expand = True),
                        ],
                        vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                build_mode_nav(prev_focus_day, next_focus_day),
                ft.Column(
                    [build_timeline_stack_for(focus_date)],
                    expand = True,
                    spacing = 0,
                    scroll = ft.ScrollMode.AUTO,
                ),
            ],
            expand = True,
            spacing = 0,
        )

    def build_week_day_card(day_value: datetime.date) -> ft.Container:
        lessons = planner_manager.get_lessons_for_date(day_value)
        content = [build_lesson_list_item(lesson) for lesson in lessons[:6]]
        if len(lessons) > 6:
            content.append(
                ft.Text(
                    f"Еще занятий: {len(lessons) - 6}",
                    size = 12,
                    color = ft.Colors.GREY_600,
                )
            )
        if not content:
            content = [
                ft.Container(
                    padding = ft.Padding.only(left = 2),
                    content = ft.Text("\u041d\u0435\u0442 \u0437\u0430\u043d\u044f\u0442\u0438\u0439", size = 12, color = ft.Colors.GREY_500, italic = True),
                )
            ]

        return ft.Container(
            content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.TextButton(
                                fmt_day(day_value),
                                on_click = lambda e, target_date = day_value: open_day_focus(target_date, "week"),
                            ),
                            ft.Container(expand = True),
                            ft.Text(f"{len(lessons)}", size = 12, color = ft.Colors.GREY_600),
                        ],
                        vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    ),
                    *content,
                ],
                spacing = 8,
                horizontal_alignment = ft.CrossAxisAlignment.STRETCH,
            ),
            bgcolor = ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border = ft.Border.all(1, ft.Colors.GREY_300),
            border_radius = 14,
            padding = 12,
            width = float("inf"),
        )

    def build_week_content() -> ft.Column:
        week_start = start_of_week(state["date"])
        day_cards = [
            build_week_day_card(week_start + datetime.timedelta(days = offset))
            for offset in range(7)
        ]
        return ft.Column(
            [
                build_mode_nav(prev_week, next_week),
                ft.Container(
                    expand = True,
                    content = ft.Column(
                        day_cards,
                        spacing = 10,
                        scroll = ft.ScrollMode.AUTO,
                        horizontal_alignment = ft.CrossAxisAlignment.STRETCH,
                    ),
                ),
            ],
            expand = True,
            spacing = 0,
        )

    def build_month_cell(
        cell_date: datetime.date | None,
        day_markers: dict[str, str],
    ) -> ft.Control:
        if cell_date is None:
            return ft.Container(expand = True, height = 64, margin = ft.Margin.symmetric(horizontal = 3))

        date_key = cell_date.strftime("%d.%m.%Y")
        day_marker = day_markers.get(date_key)
        is_selected = cell_date == state["date"]
        is_today = cell_date == datetime.date.today()

        tile_bg = None
        tile_border = None
        day_text_color = ft.Colors.GREY_500
        if day_marker == "lesson":
            tile_bg = ft.Colors.GREEN_200
            tile_border = ft.Colors.GREEN_400
            day_text_color = ft.Colors.GREEN_900
        elif day_marker == "event":
            tile_bg = ft.Colors.BLUE_200
            tile_border = ft.Colors.BLUE_400
            day_text_color = ft.Colors.BLUE_900
        elif day_marker == "mixed":
            tile_bg = ft.Colors.TEAL_200
            tile_border = ft.Colors.TEAL_400
            day_text_color = ft.Colors.TEAL_900

        outer_border_color = ft.Colors.BLUE_400 if is_selected else ft.Colors.GREEN_300 if is_today else (
            tile_border or ft.Colors.GREY_300
        )
        outer_bg = tile_bg
        outer_border_width = 2 if is_selected else 1

        return ft.Container(
            expand = True,
            height = 64,
            padding = 3,
            margin = ft.Margin.symmetric(horizontal = 3),
            border_radius = 14,
            border = ft.Border.all(outer_border_width, outer_border_color),
            bgcolor = outer_bg,
            alignment = ft.Alignment(0, 0),
            on_click = lambda e, target_date = cell_date: open_day_focus(target_date, "month"),
            ink = True,
            content = ft.Text(
                str(cell_date.day),
                size = 14,
                weight = ft.FontWeight.W_600,
                color = day_text_color,
            ),
        )

    def build_month_content() -> ft.Column:
        month_matrix = calendar.monthcalendar(state["date"].year, state["date"].month)

        day_markers: dict[str, str] = {}
        for lesson in planner_manager.get_all_lessons():
            if lesson.date.year == state["date"].year and lesson.date.month == state["date"].month:
                current_marker = day_markers.get(lesson.date_str)
                next_marker = "event" if lesson.is_event else "lesson"
                if current_marker is None:
                    day_markers[lesson.date_str] = next_marker
                elif current_marker != next_marker:
                    day_markers[lesson.date_str] = "mixed"

        weekday_header = ft.Row(
            [
                ft.Container(
                    content = ft.Text(label, size = 12, weight = ft.FontWeight.BOLD, text_align = ft.TextAlign.CENTER),
                    expand = True,
                    alignment = ft.Alignment(0, -0.2),
                    padding = ft.Padding.only(top = 3, bottom = 7),
                    margin = ft.Margin.symmetric(horizontal = 3),
                )
                for label in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            ],
            spacing = 2,
        )

        def build_legend_item(color: str, border_color: str, label: str) -> ft.Row:
            return ft.Row(
                [
                    ft.Container(
                        width = 14,
                        height = 14,
                        border_radius = 4,
                        bgcolor = color,
                        border = ft.Border.all(1, border_color),
                    ),
                    ft.Text(label, size = 11, color = ft.Colors.GREY_700),
                ],
                spacing = 6,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
                tight = True,
            )

        legend = ft.Row(
            [
                build_legend_item(ft.Colors.GREEN_200, ft.Colors.GREEN_400, "\u041f\u0430\u0440\u044b"),
                build_legend_item(ft.Colors.BLUE_200, ft.Colors.BLUE_400, "\u0421\u043e\u0431\u044b\u0442\u0438\u044f"),
                build_legend_item(ft.Colors.TEAL_200, ft.Colors.TEAL_400, "\u041f\u0430\u0440\u044b + \u0441\u043e\u0431\u044b\u0442\u0438\u044f"),
            ],
            alignment = ft.MainAxisAlignment.CENTER,
            run_alignment = ft.MainAxisAlignment.CENTER,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
            spacing = 16,
            wrap = True,
            run_spacing = 8,
        )

        week_rows = []
        for week in month_matrix:
            controls = []
            for day_value in week:
                controls.append(
                    build_month_cell(
                        datetime.date(state["date"].year, state["date"].month, day_value) if day_value else None,
                        day_markers,
                    )
                )
            week_rows.append(
                ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 2),
                    content = ft.Row(controls, spacing = 2),
                )
            )

        return ft.Column(
            [
                ft.Container(
                    content = build_mode_nav(prev_month, next_month),
                    padding = ft.Padding.symmetric(horizontal = 6),
                ),
                ft.Container(
                    content = weekday_header,
                    padding = ft.Padding.only(left = 12, right = 12, top = 2),
                ),
                ft.Container(
                    content = legend,
                    padding = ft.Padding.only(left = 14, right = 14, bottom = 2),
                ),
                *week_rows,
            ],
            expand = True,
            spacing = 8,
            scroll = ft.ScrollMode.AUTO,
        )

    def build_task_card(task) -> ft.Container:
        lesson = planner_manager.get_lesson(task.lesson_id)
        type_titles = {
            TASK_TYPE_HOMEWORK: "Домашка",
            TASK_TYPE_TEST: "Контрольная",
            TASK_TYPE_LAB: "Лаба",
        }
        type_colors = {
            TASK_TYPE_HOMEWORK: ft.Colors.BLUE_200,
            TASK_TYPE_TEST: ft.Colors.RED_200,
            TASK_TYPE_LAB: ft.Colors.GREEN_200,
        }

        return ft.Container(
            content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content = ft.Text(
                                    type_titles.get(task.task_type, "Задача"),
                                    size = 11,
                                    weight = ft.FontWeight.W_600,
                                    color = ft.Colors.BLACK87,
                                ),
                                bgcolor = type_colors.get(task.task_type, ft.Colors.GREY_300),
                                border_radius = 999,
                                padding = ft.Padding.symmetric(horizontal = 10, vertical = 5),
                            ),
                            ft.Container(expand = True),
                            ft.IconButton(
                                ft.Icons.OPEN_IN_NEW if lesson is not None else ft.Icons.LINK_OFF,
                                tooltip = "Открыть пару" if lesson is not None else "Пара не найдена",
                                disabled = lesson is None,
                                icon_size = 18,
                                style = ft.ButtonStyle(
                                    color = {
                                        ft.ControlState.DEFAULT: ft.Colors.BLACK54,
                                        ft.ControlState.DISABLED: ft.Colors.BLACK26,
                                    }
                                ),
                                on_click = (lambda e, lesson_item = lesson: open_detail(lesson_item)) if lesson is not None else None,
                            ),
                        ],
                        vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(task.text, size = 16, weight = ft.FontWeight.W_600, color = ft.Colors.BLACK87),
                    ft.Text(
                        f"{task.date_str} • {task.time_start} • {task.subject}",
                        size = 12.5,
                        color = ft.Colors.BLACK54,
                    ),
                ],
                spacing = 8,
            ),
            border = ft.Border.all(1, ft.Colors.with_opacity(0.18, ft.Colors.BLACK)),
            border_radius = 18,
            padding = ft.Padding.symmetric(horizontal = 14, vertical = 12),
            bgcolor = ft.Colors.WHITE,
        )

    def build_tasks_content() -> ft.Column:
        all_tasks = list(tasks_manager.get_all_tasks())
        valid_filters = {"all", TASK_TYPE_HOMEWORK, TASK_TYPE_TEST, TASK_TYPE_LAB}
        if state["task_filter"] not in valid_filters:
            state["task_filter"] = "all"
        if state["task_sort"] not in {"date", "subject", "priority"}:
            state["task_sort"] = "date"
        filtered_tasks = all_tasks
        if state["task_filter"] != "all":
            filtered_tasks = [task for task in all_tasks if task.task_type == state["task_filter"]]

        def parse_task_date(task) -> datetime.date:
            try:
                return datetime.datetime.strptime(task.date_str, "%d.%m.%Y").date()
            except Exception:
                return datetime.date.max

        def parse_task_time(task) -> int:
            parsed_time = time_to_minutes((task.time_start or "").strip())
            return parsed_time if parsed_time >= 0 else 24 * 60

        def task_sort_key(task):
            date_value = parse_task_date(task)
            time_value = parse_task_time(task)
            subject_value = (task.subject or "").lower()
            text_value = (task.text or "").lower()
            if state["task_sort"] == "subject":
                return (subject_value, date_value, time_value, text_value)
            if state["task_sort"] == "priority":
                return (-getattr(task, "priority", 0), date_value, time_value, subject_value, text_value)
            return (date_value, time_value, subject_value, text_value)

        filtered_tasks.sort(key = task_sort_key)

        filter_dropdown = ft.Dropdown(
            value = state["task_filter"],
            expand = True,
            dense = True,
            text_size = 16,
            border_radius = 16,
            border_color = ft.Colors.with_opacity(0.7, ft.Colors.BLACK),
            focused_border_color = ft.Colors.BLACK87,
            content_padding = ft.Padding.symmetric(horizontal = 14, vertical = 14),
            bgcolor = ft.Colors.WHITE,
            options = [
                ft.DropdownOption(key = "all", text = "Все"),
                ft.DropdownOption(key = TASK_TYPE_HOMEWORK, text = "Домашки"),
                ft.DropdownOption(key = TASK_TYPE_TEST, text = "Контрольные"),
                ft.DropdownOption(key = TASK_TYPE_LAB, text = "Лабы"),
            ],
            on_select = lambda e: set_task_filter(e.control.value or "all"),
        )
        sort_dropdown = ft.Dropdown(
            value = state["task_sort"],
            expand = True,
            dense = True,
            text_size = 16,
            border_radius = 16,
            border_color = ft.Colors.with_opacity(0.7, ft.Colors.BLACK),
            focused_border_color = ft.Colors.BLACK87,
            content_padding = ft.Padding.symmetric(horizontal = 14, vertical = 14),
            bgcolor = ft.Colors.WHITE,
            options = [
                ft.DropdownOption(key = "date", text = "По дате"),
                ft.DropdownOption(key = "subject", text = "По предмету"),
                ft.DropdownOption(key = "priority", text = "По приоритету"),
            ],
            on_select = lambda e: set_task_sort(e.control.value or "date"),
        )
        filter_dropdown.label = None
        sort_dropdown.label = None

        task_cards: list[ft.Control] = [build_task_card(task) for task in filtered_tasks]
        if not task_cards:
            task_cards = [
                ft.Container(
                    padding = ft.Padding.only(left = 14, top = 10),
                    content = ft.Text("Подходящих задач нет.", size = 15, color = ft.Colors.GREY_500),
                )
            ]

        return ft.Column(
            [
                ft.Container(
                    padding = ft.Padding.only(left = 10, right = 10, top = 10),
                    content = ft.Row(
                        [
                            ft.Container(
                                expand = True,
                                content = ft.Column(
                                    [
                                        ft.Text("Тип задач", size = 12, color = ft.Colors.GREY_500),
                                        filter_dropdown,
                                    ],
                                    spacing = 6,
                                ),
                            ),
                            ft.Container(
                                expand = True,
                                content = ft.Column(
                                    [
                                        ft.Text("Сортировка", size = 12, color = ft.Colors.GREY_500),
                                        sort_dropdown,
                                    ],
                                    spacing = 6,
                                ),
                            ),
                        ],
                        spacing = 10,
                    ),
                ),
                ft.Container(
                    padding = ft.Padding.only(left = 10, right = 10, top = 2),
                    content = ft.Text(
                        f"Всего задач: {len(filtered_tasks)}",
                        size = 12,
                        color = ft.Colors.GREY_600,
                    ),
                ),
                ft.Container(
                    expand = True,
                    padding = ft.Padding.only(left = 10, right = 10, top = 2, bottom = 16),
                    content = ft.Column(task_cards, spacing = 12, scroll = ft.ScrollMode.AUTO),
                ),
            ],
            expand = True,
            spacing = 8,
        )

    def build_current_content() -> ft.Control:
        if state["focus_date"] is not None:
            return build_focus_day_content()
        if state["mode"] == "week":
            return build_week_content()
        if state["mode"] == "month":
            return build_month_content()
        if state["mode"] == "tasks":
            return build_tasks_content()
        return build_day_content()

    title_text = ft.Text(current_mode_title(), size = 20, weight = ft.FontWeight.BOLD, color = ft.Colors.BLACK87)
    subtitle_text = ft.Text(current_mode_subtitle(), size = 12, color = ft.Colors.GREY_600)
    week_label_control = ft.Text(
        week_label(),
        size = 11,
        weight = ft.FontWeight.BOLD,
        color = ft.Colors.GREY_700,
    )
    menu_button = ft.IconButton(ft.Icons.MENU, on_click = lambda e: open_drawer_menu(), icon_size = 24)
    week_badge = ft.Container(
        content = week_label_control,
        width = WEEK_BADGE_WIDTH,
        alignment = ft.Alignment(0, 0),
        bgcolor = ft.Colors.GREY_200,
        border_radius = 8,
        padding = ft.Padding.symmetric(horizontal = 12, vertical = 8),
    )
    header_left_host = ft.Container(
        width = 48,
        alignment = ft.Alignment(-1, 0),
        content = menu_button,
    )
    header_right_host = ft.Container(
        width = 48,
        alignment = ft.Alignment(1, 0),
    )
    content_host = ft.Container(expand = True)

    header = ft.Container(
        content = ft.Row(
            [
                header_left_host,
                ft.Column(
                    [title_text, subtitle_text],
                    spacing = 0,
                    expand = True,
                    horizontal_alignment = ft.CrossAxisAlignment.CENTER,
                ),
                header_right_host,
            ],
            alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor = ft.Colors.SURFACE,
        padding = ft.Padding.only(left = 8, right = 8, top = 10, bottom = 10),
    )
    header_divider = ft.Divider(height = 1, thickness = 0.8, color = ft.Colors.BLACK12)

    def set_task_filter(task_filter: str):
        state["task_filter"] = task_filter
        rebuild_view()

    def set_task_sort(task_sort: str):
        state["task_sort"] = task_sort
        rebuild_view()

    def set_mode(mode: str, close_drawer: bool = True):
        state["mode"] = mode
        state["focus_date"] = None
        state["focus_origin_mode"] = None
        if close_drawer:
            close_drawer_menu()
        rebuild_view()

    def open_day_focus(target_date: datetime.date, origin_mode: str):
        state["focus_date"] = target_date
        state["focus_origin_mode"] = origin_mode
        rebuild_view()

    def close_day_focus():
        state["focus_date"] = None
        state["focus_origin_mode"] = None
        rebuild_view()

    def prev_focus_day(_):
        if state["focus_date"] is None:
            return
        state["focus_date"] -= datetime.timedelta(days = 1)
        rebuild_view()

    def next_focus_day(_):
        if state["focus_date"] is None:
            return
        state["focus_date"] += datetime.timedelta(days = 1)
        rebuild_view()

    def prev_day(_):
        state["date"] -= datetime.timedelta(days = 1)
        rebuild_view()

    def next_day(_):
        state["date"] += datetime.timedelta(days = 1)
        rebuild_view()

    def prev_week(_):
        state["date"] -= datetime.timedelta(days = 7)
        rebuild_view()

    def next_week(_):
        state["date"] += datetime.timedelta(days = 7)
        rebuild_view()

    def prev_month(_):
        state["date"] = shift_month(state["date"], -1)
        rebuild_view()

    def next_month(_):
        state["date"] = shift_month(state["date"], 1)
        rebuild_view()

    def go_to_today(close_drawer: bool = True):
        state["date"] = datetime.date.today()
        state["focus_date"] = None
        state["focus_origin_mode"] = None
        if close_drawer:
            close_drawer_menu()
        rebuild_view()

    def build_drawer_item(title: str, icon: str, mode: str) -> ft.ListTile:
        return ft.ListTile(
            leading = ft.Icon(icon),
            title = ft.Text(title),
            trailing = ft.Icon(ft.Icons.CHECK, color = ft.Colors.BLUE_400) if state["mode"] == mode else None,
            on_click = lambda e, mode_value = mode: set_mode(mode_value),
        )

    nav_drawer = ft.NavigationDrawer(controls = [], on_dismiss = lambda e: None)

    def rebuild_drawer():
        nav_drawer.controls = [
            ft.Container(
                content = ft.Column(
                    [
                        ft.Text("Меню планера", size = 17, weight = ft.FontWeight.BOLD),
                        ft.Text("Выберите режим просмотра", size = 12, color = ft.Colors.GREY_600),
                    ],
                    spacing = 4,
                ),
                padding = ft.Padding.only(left = 16, top = 18, right = 16, bottom = 12),
            ),
            ft.Divider(),
            build_drawer_item("День", ft.Icons.CALENDAR_VIEW_DAY_OUTLINED, "day"),
            build_drawer_item("Неделя", ft.Icons.VIEW_WEEK_OUTLINED, "week"),
            build_drawer_item("Месяц", ft.Icons.CALENDAR_MONTH_OUTLINED, "month"),
            build_drawer_item("Все задачи", ft.Icons.FACT_CHECK_OUTLINED, "tasks"),
        ]

    fab = ft.FloatingActionButton(
        icon = ft.Icons.ADD,
        bgcolor = ft.Colors.BLUE_200,
        on_click = open_add_dialog,
    )

    def sync_week_badge():
        badge_visible = not is_tasks_mode()
        week_label_control.value = week_label()
        week_badge.visible = badge_visible
        header_right_host.width = WEEK_BADGE_WIDTH if badge_visible else 48
        header_right_host.content = week_badge if badge_visible else None

    def rebuild_view():
        tasks_mode = is_tasks_mode()
        title_text.value = current_mode_title()
        title_text.size = 18 if tasks_mode else 20
        subtitle_text.value = "" if tasks_mode else current_mode_subtitle()
        subtitle_text.visible = not tasks_mode
        header.padding = ft.Padding.only(
            left = 8,
            right = 8,
            top = 10,
            bottom = 10,
        )
        sync_week_badge()
        fab.visible = not tasks_mode
        content_host.content = build_current_content()
        rebuild_drawer()
        safe_update(
            title_text,
            subtitle_text,
            header,
            week_label_control,
            week_badge,
            header_right_host,
            fab,
            content_host,
            nav_drawer,
        )

        lesson_id = detail_state["lesson_id"]
        if lesson_id:
            render_detail(lesson_id)

    rebuild_drawer()
    sync_week_badge()
    content_host.content = build_current_content()
    refresh_screen["fn"] = rebuild_view

    view = ft.View(
        route = "/planner",
        drawer = nav_drawer,
        floating_action_button = fab,
        navigation_bar = navigation_bar,
        padding = 0,
        bgcolor = ft.Colors.SURFACE,
        controls = [
            ft.SafeArea(
                expand = True,
                content = ft.Container(
                    expand = True,
                    bgcolor = ft.Colors.SURFACE,
                    content = ft.Column(
                        [
                            header,
                            header_divider,
                            content_host,
                        ],
                        expand = True,
                        spacing = 0,
                    ),
                ),
            )
        ],
    )

    return view, cleanup
