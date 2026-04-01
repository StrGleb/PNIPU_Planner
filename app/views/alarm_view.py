import flet as ft


def build_alarm_view(navigation_bar: ft.NavigationBar, clock_text: ft.Text) -> ft.View:
    return ft.View(
        route="/alarm",
        controls=[
            ft.Row(
                [ft.Text("Будильники", size=25)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                [clock_text],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        navigation_bar=navigation_bar,
    )
