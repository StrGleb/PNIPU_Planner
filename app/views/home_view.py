import flet as ft
import datetime
from utils.time_utils import greeting_choose
from managers.tasks_manager import TasksManager


def build_home_view(
    navigation_bar: ft.NavigationBar,
    user_name: str,
    tasks_manager: TasksManager,
) -> ft.View:

    greeting = greeting_choose()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    tests_today = tasks_manager.get_tests_for_date(today)
    homework_tmrw = tasks_manager.get_homework_for_date(tomorrow)

    # ── Блок с задачами ───────────────────────────────────────────────────────
    def _task_box(items: list, empty_text: str) -> ft.Container:
        if items:
            content_controls = [
                ft.Text(f"- {t.display_line}", size = 14, color = ft.Colors.GREY_800)
                for t in items
            ]
        else:
            content_controls = [
                ft.Text(empty_text, size = 14, italic = True, color = ft.Colors.GREY_800)
            ]

        return ft.Container(
            content = ft.Column(content_controls, spacing = 6),
            bgcolor = ft.Colors.GREY_200,
            border_radius = 16,
            padding = ft.padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _section(label: str, box: ft.Container) -> ft.Column:
        return ft.Column(
            [
                ft.Text(label, size = 15, weight = ft.FontWeight.BOLD),
                ft.Container(height = 6),
                box,
            ],
            spacing = 0,
        )

    # ── View ──────────────────────────────────────────────────────────────────
    return ft.View(
        route = "/",
        padding = ft.padding.symmetric(horizontal = 20, vertical = 24),
        controls = [
            ft.Column(
                [
                    # Приветствие
                    ft.Text(
                        f"{greeting},\n{user_name or 'Студент'}!",
                        size = 30,
                        weight = ft.FontWeight.BOLD,
                    ),
                    ft.Container(height = 24),

                    # К/р сегодня
                    _section(
                        "Ваши к/р сегодня:",
                        _task_box(tests_today, "Контрольных работ сегодня нет"),
                    ),
                    ft.Container(height = 20),

                    # Д/з на завтра
                    _section(
                        "Ваши работы на завтра:",
                        _task_box(homework_tmrw, "Домашних работ на завтра нет"),
                    ),
                ],
                expand = True,
                scroll = ft.ScrollMode.HIDDEN,
            )
        ],
        navigation_bar = navigation_bar,
    )