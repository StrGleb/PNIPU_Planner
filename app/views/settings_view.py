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
            # Заголовок
            ft.Row(
                [ft.Text("Настройки", size=28, weight=ft.FontWeight.BOLD)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Container(height=20),
            
            # --- Общие ---
            ft.Row(
                [ft.Text("Общие", size=18, weight=ft.FontWeight.W_600)],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Container(height=10),
            ft.Row(
                [
                    ft.Text("Тема:", width=120, text_align=ft.TextAlign.RIGHT),
                    ft.Dropdown(
                        value="Светлая",
                        options=[
                            ft.DropdownOption("Тёмная"),
                            ft.DropdownOption("Светлая"),
                        ],
                        width=200,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            
            ft.Divider(),
            
            # --- Персональные данные ---
            ft.Row(
                [ft.Text("Персональные данные", size=18, weight=ft.FontWeight.W_600)],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Container(height=10),
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Ваше имя:", width=120, text_align=ft.TextAlign.RIGHT),
                            ft.TextField(value=user_name, width=300),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row(
                        [
                            ft.Text("Время на сборы:", width=120, text_align=ft.TextAlign.RIGHT),
                            ft.TextField(value=str(get_together_time), width=100),
                            ft.Text("минут", size=14),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.Text("Адрес проживания:", width=120, text_align=ft.TextAlign.RIGHT),
                            ft.TextField(value=user_address, width=300),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row(
                        [
                            ft.Text("Факультет:", width=120, text_align=ft.TextAlign.RIGHT),
                            ft.Dropdown(
                                value=user_faculty if user_faculty else "-",
                                options=[ft.DropdownOption(f) for f in FACULTIES],
                                width=300,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row(
                        [
                            ft.Container(width=120),
                            ft.Checkbox(
                                label="Есть своя машина для поездок в университет",
                                value=False,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                spacing=10,
            ),
            
            ft.Divider(),
            
            # --- Экспорт ---
            ft.Row(
                [ft.Text("Экспорт расписания", size=18, weight=ft.FontWeight.W_600)],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Container(height=10),
            ft.Row(
                [
                    ft.Container(width=120),
                    ft.ElevatedButton("Экспорт из xlsx..."),  # Убрал иконку
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
        ],
        navigation_bar=navigation_bar,
    )