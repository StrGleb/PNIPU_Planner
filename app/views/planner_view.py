import asyncio
import calendar
import datetime
import inspect
from typing import Any, Callable

import flet as ft

from bridges.planner_bridge import (
    is_week_even,
    normalize_end_minutes_for_day_span,
    time_to_minutes,
)
from managers.config_manager import ConfigManager
from managers.planner_manager import PlannerManager
from managers.tasks_manager import TasksManager
from models.lesson_model import Lesson
from models.task_model import TASK_TYPE_HOMEWORK, TASK_TYPE_LAB, TASK_TYPE_TEST

HOUR_HEIGHT = 80
START_HOUR = 8
END_HOUR = 24
TIME_COL_W = 52

LESSON_BG = ft.Colors.GREEN_200
LESSON_BORDER = ft.Colors.GREEN_400
LESSON_TEXT = ft.Colors.GREEN_900
LESSON_TIME = ft.Colors.GREEN_800

EVENT_BG = ft.Colors.BLUE_200
EVENT_BORDER = ft.Colors.BLUE_400
EVENT_TEXT = ft.Colors.BLUE_900
EVENT_TIME = ft.Colors.BLUE_800

PRIORITY_COLORS = {
    0: ft.Colors.GREY_400,
    1: ft.Colors.BLUE_400,
    2: ft.Colors.ORANGE_400,
    3: ft.Colors.RED_400,
}


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

    def sync_auto_alarm():
        try:
            auto_alarm_service.handle_planner_change()
        except Exception:
            pass

    def refresh_task_views():
        try:
            tasks_manager.refresh_all_ratings()
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

    def open_add_dialog(e = None):
        date_field = ft.TextField(label = "Дата ДД.ММ.ГГГГ", value = active_date().strftime("%d.%m.%Y"))
        start_field = ft.TextField(label = "Начало ЧЧ:ММ", width = 130)
        end_field = ft.TextField(label = "Конец ЧЧ:ММ", width = 130)
        subject_field = ft.TextField(label = "Название события")
        description_field = ft.TextField(label = "Описание", multiline = True, min_lines = 2, max_lines = 4)
        address_field = ft.TextField(label = "Адрес")
        error_text = ft.Text("", color = ft.Colors.RED_400, size = 12)

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

            planner_manager.add_custom_event(
                date = lesson_date,
                time_start = time_start,
                time_end = time_end,
                subject = subject,
                description = (description_field.value or "").strip(),
                address = (address_field.value or "").strip(),
            )
            add_dialog.open = False
            sync_auto_alarm()
            page.update()
            rebuild_view()

        def cancel(_):
            add_dialog.open = False
            page.update()

        add_dialog.title = ft.Text("Новое событие")
        add_dialog.content = ft.Column(
            [
                date_field,
                ft.Row([start_field, ft.Text(" - "), end_field]),
                subject_field,
                description_field,
                address_field,
                error_text,
            ],
            tight = True,
            spacing = 10,
            width = 320,
        )
        add_dialog.actions = [
            ft.TextButton("Отмена", on_click = cancel),
            ft.FilledButton("Добавить", on_click = save),
        ]
        show_dialog(add_dialog)

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
            tasks_manager.remove_tasks_for_lesson(current.id)
            planner_manager.remove_lesson(current.id)
            detail_state["lesson_id"] = None
            detail_sheet.open = False
            sync_auto_alarm()
            refresh_task_views()
            page.update()
            rebuild_view()

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

        task_sections: list[ft.Control] = []
        if not current.is_event:
            task_sections = [
                *section("Домашние работы:", homework_tasks, add_homework),
                *section("Контрольные работы:", test_tasks, add_test),
                *section("Лабораторные работы:", lab_tasks, add_lab),
            ]

        detail_sheet.content = ft.Container(
            content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(expand = True),
                            ft.IconButton(ft.Icons.CLOSE, on_click = lambda e: close_detail_sheet(), icon_size = 20),
                        ]
                    ),
                    ft.Text(current.subject, size = 18, weight = ft.FontWeight.BOLD),
                    ft.Text(
                        f"{current.date_str}   {current.time_start} - {current.time_end}",
                        size = 13,
                        color = ft.Colors.GREY_600,
                    ),
                    *lesson_meta,
                    ft.Divider(),
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

        background = EVENT_BG if lesson.is_event else LESSON_BG
        border_color = EVENT_BORDER if lesson.is_event else LESSON_BORDER
        title_color = EVENT_TEXT if lesson.is_event else LESSON_TEXT
        time_color = EVENT_TIME if lesson.is_event else LESSON_TIME

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
            bgcolor = background,
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
        background = EVENT_BG if lesson.is_event else LESSON_BG
        border_color = EVENT_BORDER if lesson.is_event else LESSON_BORDER
        title_color = EVENT_TEXT if lesson.is_event else LESSON_TEXT
        meta_color = EVENT_TIME if lesson.is_event else LESSON_TIME

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
            bgcolor = background,
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
            return ft.Container(expand = True, height = 64)

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
            border_radius = 14,
            border = ft.Border.all(outer_border_width, outer_border_color),
            bgcolor = outer_bg,
            alignment = ft.Alignment(0, 0),
            on_click = lambda e, target_date = cell_date: open_day_focus(target_date, "month"),
            ink = True,
            content = ft.Text(
                str(cell_date.day),
                size = 15,
                weight = ft.FontWeight.BOLD,
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
                    alignment = ft.Alignment(0, 0),
                    padding = 6,
                )
                for label in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            ],
            spacing = 6,
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
            )

        legend = ft.Row(
            [
                build_legend_item(ft.Colors.GREEN_200, ft.Colors.GREEN_400, "\u041f\u0430\u0440\u044b"),
                build_legend_item(ft.Colors.BLUE_200, ft.Colors.BLUE_400, "\u0421\u043e\u0431\u044b\u0442\u0438\u044f"),
                build_legend_item(ft.Colors.TEAL_200, ft.Colors.TEAL_400, "\u041f\u0430\u0440\u044b + \u0441\u043e\u0431\u044b\u0442\u0438\u044f"),
            ],
            spacing = 14,
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
            week_rows.append(ft.Row(controls, spacing = 6))

        return ft.Column(
            [
                build_mode_nav(prev_month, next_month),
                weekday_header,
                legend,
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
                                content = ft.Text(type_titles.get(task.task_type, "Задача"), size = 11, weight = ft.FontWeight.BOLD),
                                bgcolor = type_colors.get(task.task_type, ft.Colors.GREY_300),
                                border_radius = 999,
                                padding = ft.Padding.symmetric(horizontal = 10, vertical = 6),
                            ),
                            ft.Container(expand = True),
                            ft.IconButton(
                                ft.Icons.OPEN_IN_NEW if lesson is not None else ft.Icons.LINK_OFF,
                                tooltip = "Открыть пару" if lesson is not None else "Пара не найдена",
                                disabled = lesson is None,
                                on_click = (lambda e, lesson_item = lesson: open_detail(lesson_item)) if lesson is not None else None,
                            ),
                        ],
                        vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(task.text, size = 15, weight = ft.FontWeight.BOLD),
                    ft.Text(
                        f"{task.date_str} • {task.time_start} • {task.subject}",
                        size = 12,
                        color = ft.Colors.GREY_600,
                    ),
                ],
                spacing = 6,
            ),
            border = ft.Border.all(1, ft.Colors.GREY_300),
            border_radius = 14,
            padding = 14,
            bgcolor = ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
        )

    def build_tasks_content() -> ft.Column:
        all_tasks = tasks_manager.get_all_tasks()
        if state["task_filter"] != "all":
            all_tasks = [task for task in all_tasks if task.task_type == state["task_filter"]]
        if state["task_sort"] not in {"date", "subject", "priority"}:
            state["task_sort"] = "date"

        def parse_task_date(task) -> datetime.date:
            return datetime.datetime.strptime(task.date_str, "%d.%m.%Y").date()

        def task_sort_key(task):
            date_value = parse_task_date(task)
            time_value = time_to_minutes(task.time_start)
            if state["task_sort"] == "subject":
                return (task.subject.lower(), date_value, time_value, task.text.lower())
            if state["task_sort"] == "priority":
                return (-task.priority, date_value, time_value, task.subject.lower())
            return (date_value, time_value, task.subject.lower(), task.text.lower())

        all_tasks.sort(key = task_sort_key)

        filter_dropdown = ft.Dropdown(
            label = "Тип",
            value = state["task_filter"],
            width = 220,
            options = [
                ft.DropdownOption(key = "all", text = "Все"),
                ft.DropdownOption(key = TASK_TYPE_HOMEWORK, text = "Домашки"),
                ft.DropdownOption(key = TASK_TYPE_TEST, text = "Контрольные"),
                ft.DropdownOption(key = TASK_TYPE_LAB, text = "Лабы"),
            ],
            on_select = lambda e: set_task_filter(e.control.value or "all"),
        )
        sort_dropdown = ft.Dropdown(
            label = "Сортировка",
            value = state["task_sort"],
            width = 220,
            options = [
                ft.DropdownOption(key = "date", text = "По дате"),
                ft.DropdownOption(key = "subject", text = "По предмету"),
                ft.DropdownOption(key = "type", text = "По типу"),
                ft.DropdownOption(key = "priority", text = "По приоритету"),
            ],
            on_select = lambda e: set_task_sort(e.control.value or "date"),
        )
        filter_dropdown.label = None
        filter_dropdown.width = 240
        sort_dropdown.label = None
        sort_dropdown.width = 240
        sort_dropdown.options = [
            ft.DropdownOption(key = "date", text = "\u041f\u043e \u0434\u0430\u0442\u0435"),
            ft.DropdownOption(key = "subject", text = "\u041f\u043e \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u0443"),
            ft.DropdownOption(key = "priority", text = "\u041f\u043e \u043f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442\u0443"),
        ]

        task_cards: list[ft.Control] = [build_task_card(task) for task in all_tasks]
        if not task_cards:
            task_cards = [
                ft.Container(
                    padding = 16,
                    content = ft.Text("Подходящих задач нет.", size = 14, color = ft.Colors.GREY_500),
                )
            ]

        return ft.Column(
            [
                ft.Container(
                    padding = ft.Padding.only(left = 10, right = 10, top = 12),
                    content = ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("\u0422\u0438\u043f \u0437\u0430\u0434\u0430\u0447", size = 12, color = ft.Colors.GREY_600),
                                    filter_dropdown,
                                ],
                                spacing = 6,
                            ),
                            ft.Column(
                                [
                                    ft.Text("\u0421\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0430", size = 12, color = ft.Colors.GREY_600),
                                    sort_dropdown,
                                ],
                                spacing = 6,
                            ),
                        ],
                        wrap = True,
                        spacing = 12,
                        run_spacing = 12,
                    ),
                ),
                ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 10),
                    content = ft.Text(f"\u0412\u0441\u0435\u0433\u043e \u0437\u0430\u0434\u0430\u0447: {len(all_tasks)}", size = 12, color = ft.Colors.GREY_600),
                ),
                ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 10),
                    content = ft.Column(task_cards, spacing = 10),
                ),
            ],
            expand = True,
            spacing = 12,
            scroll = ft.ScrollMode.AUTO,
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

    title_text = ft.Text(current_mode_title(), size = 20, weight = ft.FontWeight.BOLD)
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
        padding = ft.Padding.symmetric(horizontal = 4, vertical = 8),
    )

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
                content = ft.Row(
                    [
                        ft.Text("Меню планера", size = 15, weight = ft.FontWeight.BOLD, expand = True),
                        ft.IconButton(ft.Icons.CLOSE, on_click = lambda e: close_drawer_menu(), icon_size = 20),
                    ]
                ),
                padding = ft.Padding.only(left = 16, top = 12, right = 8, bottom = 8),
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

    def rebuild_view():
        title_text.value = current_mode_title()
        subtitle_text.value = current_mode_subtitle()
        week_label_control.value = week_label()
        week_badge.visible = state["mode"] != "tasks"
        header_right_host.width = 72 if state["mode"] != "tasks" else 48
        header_right_host.content = week_badge if state["mode"] != "tasks" else None
        fab.visible = state["mode"] != "tasks"
        content_host.content = build_current_content()
        rebuild_drawer()
        safe_update(
            title_text,
            subtitle_text,
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
    content_host.content = build_current_content()
    refresh_screen["fn"] = rebuild_view

    view = ft.View(
        route = "/planner",
        drawer = nav_drawer,
        floating_action_button = fab,
        navigation_bar = navigation_bar,
        padding = 0,
        controls = [
            ft.SafeArea(
                expand = True,
                content = ft.Container(
                    expand = True,
                    content = ft.Column(
                        [
                            header,
                            ft.Divider(height = 1, thickness = 0.5),
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
