import datetime

import flet as ft

from bridges.planner_bridge import time_to_minutes
from managers.tasks_manager import TasksManager
from utils.time_utils import greeting_choose

PRIORITY_DOT_COLORS = {
    0: ft.Colors.GREY_400,
    1: ft.Colors.BLUE_400,
    2: ft.Colors.ORANGE_400,
    3: ft.Colors.RED_500,
}


def build_home_view(
    navigation_bar: ft.NavigationBar,
    user_name: str,
    tasks_manager: TasksManager,
    config_manager = None,
) -> ft.View:
    greeting = greeting_choose()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days = 1)

    def _sort_tasks_by_time(items: list) -> list:
        return sorted(
            items,
            key = lambda task: (time_to_minutes(task.time_start), task.subject.lower(), task.text.lower()),
        )

    tests_today = _sort_tasks_by_time(tasks_manager.get_tests_for_date(today))
    tests_tomorrow = _sort_tasks_by_time(tasks_manager.get_tests_for_date(tomorrow))
    homework_tomorrow = _sort_tasks_by_time(tasks_manager.get_homework_for_date(tomorrow))
    labs_tomorrow = _sort_tasks_by_time(tasks_manager.get_labs_for_date(tomorrow))

    def _task_row(task) -> ft.Row:
        dot = ft.Container(
            width = 10,
            height = 10,
            border_radius = 5,
            bgcolor = PRIORITY_DOT_COLORS.get(task.priority, ft.Colors.GREY_400),
        )
        return ft.Row(
            [dot, ft.Text(task.display_line, size = 14, expand = True, color = ft.Colors.BLACK)],
            spacing = 8,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        )

    def _task_box(items: list, empty_text: str, box_color = ft.Colors.GREY_200) -> ft.Container:
        content_controls = [_task_row(task) for task in items] if items else [
            ft.Text(empty_text, size = 14, italic = True, color = ft.Colors.GREY_500)
        ]
        return ft.Container(
            content = ft.Column(content_controls, spacing = 8),
            bgcolor = box_color,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _dual_task_box(
        today_items: list,
        tomorrow_items: list,
        empty_today_text: str,
        empty_tomorrow_text: str,
        box_color = ft.Colors.GREY_200,
    ) -> ft.Container:
        def _subsection(title: str, items: list, empty_text: str) -> ft.Column:
            content_controls = [_task_row(task) for task in items] if items else [
                ft.Text(empty_text, size = 14, italic = True, color = ft.Colors.GREY_500)
            ]
            return ft.Column(
                [
                    ft.Text(title, size = 13, weight = ft.FontWeight.W_600, color = ft.Colors.GREY_800),
                    ft.Container(height = 4),
                    *content_controls,
                ],
                spacing = 8,
            )

        return ft.Container(
            content = ft.Column(
                [
                    _subsection("\u0421\u0435\u0433\u043e\u0434\u043d\u044f", today_items, empty_today_text),
                    ft.Divider(height = 18),
                    _subsection("\u0417\u0430\u0432\u0442\u0440\u0430", tomorrow_items, empty_tomorrow_text),
                ],
                spacing = 0,
            ),
            bgcolor = box_color,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _section(label: str, box: ft.Container) -> ft.Column:
        return ft.Column(
            [ft.Text(label, size = 15, weight = ft.FontWeight.BOLD), ft.Container(height = 6), box],
            spacing = 0,
        )

    return ft.View(
        route = "/",
        padding = 0,
        controls = [
            ft.SafeArea(
                content = ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 20, vertical = 24),
                    content = ft.Column(
                        [
                            ft.Text(
                                f"{greeting},\n{user_name or '\u0421\u0442\u0443\u0434\u0435\u043d\u0442'}!",
                                size = 30,
                                weight = ft.FontWeight.BOLD,
                            ),
                            ft.Container(height = 20),
                            _section(
                                "\u0412\u0430\u0448\u0438 \u043a/\u0440:",
                                _dual_task_box(
                                    tests_today,
                                    tests_tomorrow,
                                    "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u044c\u043d\u044b\u0445 \u0440\u0430\u0431\u043e\u0442 \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u043d\u0435\u0442",
                                    "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u044c\u043d\u044b\u0445 \u0440\u0430\u0431\u043e\u0442 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430 \u043d\u0435\u0442",
                                    ft.Colors.RED_100,
                                ),
                            ),
                            ft.Container(height = 16),
                            _section(
                                "\u0412\u0430\u0448\u0438 \u0434\u043e\u043c\u0430\u0448\u043d\u0438\u0435 \u0440\u0430\u0431\u043e\u0442\u044b \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430:",
                                _task_box(
                                    homework_tomorrow,
                                    "\u0414\u043e\u043c\u0430\u0448\u043d\u0438\u0445 \u0440\u0430\u0431\u043e\u0442 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430 \u043d\u0435\u0442",
                                    ft.Colors.BLUE_100,
                                ),
                            ),
                            ft.Container(height = 16),
                            _section(
                                "\u0412\u0430\u0448\u0438 \u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u043d\u044b\u0435 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430:",
                                _task_box(
                                    labs_tomorrow,
                                    "\u041b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u043d\u044b\u0445 \u0440\u0430\u0431\u043e\u0442 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430 \u043d\u0435\u0442",
                                    ft.Colors.GREEN_100,
                                ),
                            ),
                            ft.Container(height = 16),
                        ],
                        expand = True,
                        scroll = ft.ScrollMode.HIDDEN,
                    ),
                )
            )
        ],
        navigation_bar = navigation_bar,
    )
