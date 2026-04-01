import flet as ft


FACULTIES = [
    "ЭТФ", "ХТФ", "АКФ", "Гуманитарный", "МТФ",
    "Строительный", "Прикладной математики и механики",
    "Горно-нефтяной", "Автодорожный",
]


def build_settings_view(
    navigation_bar: ft.NavigationBar,
    user_name: str,
    get_together_time: int,
    user_address: str,
    user_faculty: str,
) -> ft.View:

    return ft.View(
        route="/settings",
        scroll=ft.ScrollMode.HIDDEN,
        controls=[
            ft.Row(
                [ft.Text("Настройки", size=25)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),

            # --- Общие ---
            ft.Row(
                [ft.Text("Общие", size=15)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Тема:"),
                            ft.Dropdown(
                                value="Светлая",
                                options=[
                                    ft.DropdownOption("Тёмная"),
                                    ft.DropdownOption("Светлая"),
                                ],
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=0,
                width=400,
                height=80,
            ),

            ft.Divider(),

            # --- Персональные данные ---
            ft.Row(
                [ft.Text("Персональные данные", size=15)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Ваше имя:"),
                            ft.TextField(value=user_name),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.Text("Время на сборы:"),
                            ft.TextField(value=str(get_together_time)),
                            ft.Text("минут"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.Text("Адрес проживания:"),
                            ft.TextField(value=user_address),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.Text("Факультет:"),
                            ft.Dropdown(
                                value=user_faculty if user_faculty else "-",
                                options=[ft.DropdownOption(f) for f in FACULTIES],
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.Checkbox(
                                label="Есть своя машина для поездок в университет",
                                value=False,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                ],
                spacing=5,
                width=400,
                height=300,
            ),

            ft.Divider(),

            # --- Экспорт ---
            ft.Row(
                [ft.Text("Экспорт расписания", size=15)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                [ft.Button(content="Экспорт из xlsx...")]
            ),
        ],
        navigation_bar=navigation_bar,
    )
