import datetime
from typing import Any, Callable

import flet as ft

from bridges.planner_bridge import is_week_even, time_to_minutes
from managers.config_manager import ConfigManager
from managers.notification_manager import check_and_notify
from managers.planner_manager import PlannerManager
from managers.tasks_manager import TasksManager
from models.lesson_model import Lesson
from models.task_model import TASK_TYPE_HOMEWORK, TASK_TYPE_LAB, TASK_TYPE_TEST

HOUR_HEIGHT = 80
START_HOUR = 8
END_HOUR = 21
TIME_COL_W = 52

LESSON_BG = ft.Colors.GREEN_200
LESSON_BORDER = ft.Colors.GREEN_400
LESSON_TEXT = ft.Colors.GREEN_900
LESSON_TIME = ft.Colors.GREEN_800

EVENT_BG = ft.Colors.BLUE_200
EVENT_BORDER = ft.Colors.BLUE_400
EVENT_TEXT = ft.Colors.BLUE_900
EVENT_TIME = ft.Colors.BLUE_800


def build_planner_view(
    navigation_bar: ft.NavigationBar,
    planner_manager: PlannerManager,
    config_manager: ConfigManager,
    tasks_manager: TasksManager,
    auto_alarm_service: Any,
    page: ft.Page,
) -> tuple[ft.View, Callable]:
    state = {"date": datetime.date.today()}

    def safe_update(*controls):
        for control in controls:
            try:
                control.update()
            except Exception:
                pass

    def sync_auto_alarm():
        try:
            auto_alarm_service.handle_planner_change()
        except Exception:
            pass

    def fmt_day(date_value: datetime.date) -> str:
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return f"{names[date_value.weekday()]}  {date_value.strftime('%d.%m')}"

    def week_label() -> str:
        try:
            even = is_week_even(
                state["date"],
                config_manager.config.semester_start,
                config_manager.config.first_week_even,
            )
        except Exception:
            even = state["date"].isocalendar()[1] % 2 == 0
        return "ЧЕТ" if even else "НЕЧЕТ"

    add_dialog = ft.AlertDialog(modal = True, title = ft.Text("Новое событие"))
    input_dialog = ft.AlertDialog(modal = True, title = ft.Text(""))
    detail_sheet = ft.BottomSheet(
        content = ft.Container(ft.Text(""), padding = 16),
        dismissible = True,
        on_dismiss = lambda e: None,
    )
    page.overlay.extend([add_dialog, input_dialog, detail_sheet])

    def cleanup():
        for item in [add_dialog, input_dialog, detail_sheet]:
            if item in page.overlay:
                try:
                    page.overlay.remove(item)
                except Exception:
                    pass

    def open_add_dialog(e = None):
        date_field = ft.TextField(label = "Дата ДД.ММ.ГГГГ", value = state["date"].strftime("%d.%m.%Y"))
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
                if time_to_minutes(time_start) < 0 or time_to_minutes(time_end) < 0:
                    raise ValueError("invalid_time")
                if time_to_minutes(time_end) <= time_to_minutes(time_start):
                    raise ValueError("invalid_range")
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
            if state["date"] == lesson_date:
                rebuild_timeline()

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
        add_dialog.open = True
        page.update()

    def open_input_dialog(title: str, on_save: Callable[[str, int], None]):
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
            ft.FilledButton("Добавить", on_click = save),
        ]
        input_dialog.open = True
        page.update()

    def open_detail(lesson: Lesson):
        current = planner_manager.get_lesson(lesson.id)
        if current is None:
            return

        def open_edit_task_dialog(task):
            edit_field = ft.TextField(value = task.text, autofocus = True, width = 280)
            edit_error = ft.Text("", color = ft.Colors.RED_400, size = 12)
            priority_dropdown = ft.Dropdown(
                value = str(task.priority),
                options = [
                    ft.DropdownOption(key = "0", text = "0 - Обычная"),
                    ft.DropdownOption(key = "1", text = "1 - Важная"),
                    ft.DropdownOption(key = "2", text = "2 - Срочная"),
                    ft.DropdownOption(key = "3", text = "3 - Критическая"),
                ],
                width = 220,
            )

            def save_edit(_):
                text = (edit_field.value or "").strip()
                if not text:
                    edit_error.value = "Поле не может быть пустым."
                    page.update()
                    return

                tasks_manager.update_task(task.id, text, int(priority_dropdown.value or "0"))
                input_dialog.open = False
                page.update()
                fresh_lesson = planner_manager.get_lesson(current.id)
                if fresh_lesson:
                    open_detail(fresh_lesson)

            def cancel_edit(_):
                input_dialog.open = False
                page.update()

            input_dialog.title = ft.Text("Редактировать задачу")
            input_dialog.content = ft.Column(
                [edit_field, ft.Text("Приоритет:", size = 13), priority_dropdown, edit_error],
                tight = True,
                spacing = 8,
                width = 280,
            )
            input_dialog.actions = [
                ft.TextButton("Отмена", on_click = cancel_edit),
                ft.FilledButton("Сохранить", on_click = save_edit),
            ]
            input_dialog.open = True
            page.update()

        priority_colors = {
            0: ft.Colors.GREY_400,
            1: ft.Colors.BLUE_400,
            2: ft.Colors.ORANGE_400,
            3: ft.Colors.RED_400,
        }

        def task_row(task) -> ft.Row:
            dot = ft.Container(
                width = 10,
                height = 10,
                border_radius = 5,
                bgcolor = priority_colors.get(task.priority, ft.Colors.GREY_400),
            )
            return ft.Row(
                [
                    dot,
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

        def delete_task(task):
            tasks_manager.remove_task(task.id)
            if task.task_type == TASK_TYPE_HOMEWORK and task.text in current.homeworks:
                current.homeworks.remove(task.text)
            elif task.task_type == TASK_TYPE_TEST and task.text in current.test_works:
                current.test_works.remove(task.text)
            elif task.task_type == TASK_TYPE_LAB and task.text in current.lab_works:
                current.lab_works.remove(task.text)
            open_detail(current)

        all_tasks = tasks_manager.get_tasks_for_lesson(current.id)
        homework_tasks = [task for task in all_tasks if task.task_type == TASK_TYPE_HOMEWORK]
        test_tasks = [task for task in all_tasks if task.task_type == TASK_TYPE_TEST]
        lab_tasks = [task for task in all_tasks if task.task_type == TASK_TYPE_LAB]

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

        def close_sheet(_ = None):
            detail_sheet.open = False
            page.update()

        def after_add_hw(lesson_id: str, text: str, priority: int = 0):
            planner_manager.add_homework(lesson_id, text)
            lesson_item = planner_manager.get_lesson(lesson_id)
            if lesson_item:
                tasks_manager.add_task(
                    task_type = TASK_TYPE_HOMEWORK,
                    date_str = lesson_item.date_str,
                    time_start = lesson_item.time_start,
                    subject = lesson_item.subject,
                    text = text,
                    lesson_id = lesson_id,
                    priority = priority,
                )
                check_and_notify(tasks_manager)
            fresh_lesson = planner_manager.get_lesson(lesson_id)
            if fresh_lesson:
                open_detail(fresh_lesson)

        def after_add_test(lesson_id: str, text: str, priority: int = 0):
            planner_manager.add_test_work(lesson_id, text)
            lesson_item = planner_manager.get_lesson(lesson_id)
            if lesson_item:
                tasks_manager.add_task(
                    task_type = TASK_TYPE_TEST,
                    date_str = lesson_item.date_str,
                    time_start = lesson_item.time_start,
                    subject = lesson_item.subject,
                    text = text,
                    lesson_id = lesson_id,
                    priority = priority,
                )
                check_and_notify(tasks_manager)
            fresh_lesson = planner_manager.get_lesson(lesson_id)
            if fresh_lesson:
                open_detail(fresh_lesson)

        def after_add_lab(lesson_id: str, text: str, priority: int = 0):
            planner_manager.add_lab_work(lesson_id, text)
            lesson_item = planner_manager.get_lesson(lesson_id)
            if lesson_item:
                tasks_manager.add_task(
                    task_type = TASK_TYPE_LAB,
                    date_str = lesson_item.date_str,
                    time_start = lesson_item.time_start,
                    subject = lesson_item.subject,
                    text = text,
                    lesson_id = lesson_id,
                    priority = priority,
                )
                check_and_notify(tasks_manager)
            fresh_lesson = planner_manager.get_lesson(lesson_id)
            if fresh_lesson:
                open_detail(fresh_lesson)

        def add_homework(_):
            open_input_dialog("Домашняя работа", lambda text, priority: after_add_hw(current.id, text, priority))

        def add_test(_):
            open_input_dialog("Контрольная работа", lambda text, priority: after_add_test(current.id, text, priority))

        def add_lab(_):
            open_input_dialog("Лабораторная работа", lambda text, priority: after_add_lab(current.id, text, priority))

        def delete_lesson(_):
            tasks_manager.remove_tasks_for_lesson(current.id)
            planner_manager.remove_lesson(current.id)
            detail_sheet.open = False
            sync_auto_alarm()
            page.update()
            rebuild_timeline()

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
                            ft.IconButton(ft.Icons.CLOSE, on_click = close_sheet, icon_size = 20),
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
        page.update()

    timeline_col = ft.Column(scroll = ft.ScrollMode.AUTO, expand = True, spacing = 0)

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
            start_minutes = time_to_minutes(lesson.time_start) - START_HOUR * 60
            end_minutes = time_to_minutes(lesson.time_end) - START_HOUR * 60
            if start_minutes < 0 or end_minutes < 0:
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

    def build_timeline_stack() -> ft.Stack:
        total_height = (END_HOUR - START_HOUR) * HOUR_HEIGHT
        blocks = [build_grid()]
        for lesson in planner_manager.get_lessons_for_date(state["date"]):
            blocks.append(build_lesson_block(lesson))
        return ft.Stack(blocks, height = total_height)

    def rebuild_timeline():
        date_text.value = fmt_day(state["date"])
        week_label_control.value = week_label()
        timeline_col.controls = [build_timeline_stack()]
        safe_update(date_text, week_label_control, timeline_col)

    timeline_col.controls = [build_timeline_stack()]

    date_text = ft.Text(fmt_day(state["date"]), size = 12, color = ft.Colors.GREY_600)
    week_label_control = ft.Text(
        week_label(),
        size = 11,
        weight = ft.FontWeight.BOLD,
        color = ft.Colors.GREY_700,
    )
    week_badge = ft.Container(
        content = week_label_control,
        bgcolor = ft.Colors.GREY_200,
        border_radius = 8,
        padding = ft.Padding.symmetric(horizontal = 12, vertical = 8),
    )

    header = ft.Container(
        content = ft.Row(
            [
                ft.IconButton(ft.Icons.MENU, on_click = lambda e: page.show_drawer(), icon_size = 24),
                ft.Column(
                    [ft.Text("Календарь", size = 20, weight = ft.FontWeight.BOLD), date_text],
                    spacing = 0,
                    expand = True,
                    horizontal_alignment = ft.CrossAxisAlignment.CENTER,
                ),
                week_badge,
            ],
            alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        ),
        padding = ft.Padding.symmetric(horizontal = 4, vertical = 8),
    )

    def prev_day(_):
        state["date"] -= datetime.timedelta(days = 1)
        rebuild_timeline()

    def next_day(_):
        state["date"] += datetime.timedelta(days = 1)
        rebuild_timeline()

    nav_row = ft.Row(
        [
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click = prev_day, icon_size = 22),
            ft.Container(expand = True),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click = next_day, icon_size = 22),
        ]
    )

    def go_to_today():
        state["date"] = datetime.date.today()
        page.close_drawer()
        rebuild_timeline()

    nav_drawer = ft.NavigationDrawer(
        controls = [
            ft.Container(
                content = ft.Row(
                    [
                        ft.Text("Студенческий календарь", size = 15, weight = ft.FontWeight.BOLD, expand = True),
                        ft.IconButton(ft.Icons.CLOSE, on_click = lambda e: page.close_drawer(), icon_size = 20),
                    ]
                ),
                padding = ft.Padding.only(left = 16, top = 12, right = 8, bottom = 8),
            ),
            ft.Divider(),
            ft.ListTile(
                leading = ft.Icon(ft.Icons.VIEW_WEEK_OUTLINED),
                title = ft.Text("Неделя"),
                on_click = lambda e: page.close_drawer(),
            ),
            ft.ListTile(
                leading = ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED),
                title = ft.Text("Месяц"),
                on_click = lambda e: page.close_drawer(),
            ),
            ft.ListTile(
                leading = ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED),
                title = ft.Text("Год"),
                on_click = lambda e: page.close_drawer(),
            ),
            ft.Divider(),
            ft.ListTile(
                leading = ft.Icon(ft.Icons.TODAY),
                title = ft.Text("Текущий день"),
                on_click = lambda e: go_to_today(),
            ),
        ],
        on_dismiss = lambda e: None,
    )

    fab = ft.FloatingActionButton(
        icon = ft.Icons.ADD,
        bgcolor = ft.Colors.BLUE_200,
        on_click = open_add_dialog,
    )

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
                            nav_row,
                            timeline_col,
                        ],
                        expand = True,
                        spacing = 0,
                    ),
                ),
            )
        ],
    )

    return view, cleanup
