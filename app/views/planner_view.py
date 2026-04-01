import flet as ft


def build_planner_view(navigation_bar: ft.NavigationBar) -> ft.View:
    return ft.View(
        route="/planner",
        controls=[
            ft.Row(
                [ft.Text("Расписание", size=25)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        navigation_bar=navigation_bar,
    )
