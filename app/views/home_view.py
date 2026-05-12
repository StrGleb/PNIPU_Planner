import flet as ft
import datetime
from utils.time_utils import greeting_choose
from managers.tasks_manager import TasksManager
from models.task_model import PRIORITY_COLORS

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
) -> ft.View:

    greeting = greeting_choose()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    tests_today = tasks_manager.get_tests_for_date(today) # к/р сегодня
    homework_tmrw = tasks_manager.get_homework_for_date(tomorrow) # д/з на завтра
    labs_tmrw = tasks_manager.get_labs_for_date(tomorrow) # лаб. на завтра

    # ── Строка задачи с цветовым индикатором ──────────────────────────────────
    def _task_row(task) -> ft.Row:
        dot = ft.Container(
            width = 10,
            height = 10,
            border_radius = 5,
            bgcolor = PRIORITY_DOT_COLORS.get(task.priority, ft.Colors.GREY_400),
        )
        return ft.Row(
            [dot, ft.Text(task.display_line, size = 14, expand = True)],
            spacing = 8,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        )

    # ── Блок с задачами (уже отсортированных по приоритету из tasks_manager) ──
    def _task_box(items: list, empty_text: str, box_color=ft.Colors.GREY_200) -> ft.Container:
        if items:
            content_controls = [_task_row(t) for t in items]
        else:
            content_controls = [
                ft.Text(empty_text, size = 14, italic = True, color = ft.Colors.GREY_500)
            ]

        return ft.Container(
            content = ft.Column(content_controls, spacing = 8),
            bgcolor = box_color,
            border_radius = 16,
            padding = ft.padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _section(label: str, box: ft.Container) -> ft.Column:
        return ft.Column(
            [ft.Text(label, size = 15, weight = ft.FontWeight.BOLD), ft.Container(height = 6), box],
            spacing = 0,
        )

    # ── View ──────────────────────────────────────────────────────────────────
    return ft.View(
        route = "/",
        padding = ft.padding.symmetric(horizontal = 20, vertical = 24),
        controls = [
            ft.Column(
                [
                    ft.Text(
                        f"{greeting},\n{user_name or 'Студент'}!",
                        size = 30, weight = ft.FontWeight.BOLD,
                    ),
                    ft.Container(height = 20),

                    # К/р сегодня — красноватый фон
                    _section(
                        "Ваши к/р сегодня:",
                        _task_box(tests_today, "Контрольных работ сегодня нет",
                                  ft.Colors.RED_100),
                    ),
                    ft.Container(height =  16),

                    # Д/з на завтра — синеватый фон
                    _section(
                        "Ваши домашние работы на завтра:",
                        _task_box(homework_tmrw, "Домашних работ на завтра нет",
                                  ft.Colors.BLUE_100),
                    ),
                    ft.Container(height = 16),

                    # Лабораторные на завтра — зеленоватый фон
                    _section(
                        "Ваши лабораторные на завтра:",
                        _task_box(labs_tmrw, "Лабораторных работ на завтра нет",
                                  ft.Colors.GREEN_100),
                    ),
                ],
                expand = True,
                scroll = ft.ScrollMode.HIDDEN,
            )
        ],
        navigation_bar = navigation_bar,
    )