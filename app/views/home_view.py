import flet as ft
from utils.time_utils import greeting_choose


def build_home_view(navigation_bar: ft.NavigationBar, user_name: str) -> ft.View:
    greeting = greeting_choose()

    return ft.View(
        route="/",
        controls=[
            ft.Row(
                [ft.Text(f"{greeting},\n{user_name}!", size=35)]
            ),
        ],
        navigation_bar=navigation_bar,
    )
