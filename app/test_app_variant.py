import flet as ft
import datetime
from random import choice

USER_NAME = 'Семён' # Имя пользователя 
get_together_time = 0 # Время на сборы
user_address = "" # Адрес проживания пользователя
user_faculty = "" # Факультет пользователя  


def gretting_chose() -> str:
    """
    Выводит рандомное приветствие на главном экране
    23:00-05:59 - Доброй ночи
    06:00-10:59 - Доброе утро
    11:00-16:59 - Добрый день
    18:00-22:59 - Добрый вечер
    """
    grettings = ["Приветствую", "Добро пожаловать", "time"]
    gretting = choice(grettings)
    time_now = datetime.datetime.now().replace(microsecond=0, second=0)
    if gretting == "time":
        if 23 == time_now.hour or 0 <= time_now.hour <= 5:
            gretting = "Доброй ночи"
        elif 6 <= time_now.hour <= 10:
            gretting = "Доброе утро"
        elif 11 <= time_now.hour <= 16: 
            gretting = "Добрый день"
        else: 
            gretting = "Добрый вечер"
    return gretting


def main(page: ft.Page):
    page.title = "Planner App Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    gretting = gretting_chose()

    async def handle_change(e):
        if e.control.selected_index == 0:
            await page.push_route("/")
        elif e.control.selected_index == 1:
            await page.push_route("/planner")
        elif e.control.selected_index == 2:
            await page.push_route("/alarm")
        elif e.control.selected_index == 3:
            await page.push_route("/settings")

    def create_navigation_bar(index=0):
        return ft.NavigationBar(
            selected_index=index,
            on_change=handle_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.HOME_ROUNDED,
                    label="Home",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALENDAR_TODAY_OUTLINED, 
                    selected_icon=ft.Icons.CALENDAR_TODAY, 
                    label="Planner"),
                ft.NavigationBarDestination(
                    icon=ft.Icons.ACCESS_ALARM, 
                    label="Alarm"),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SETTINGS_APPLICATIONS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS_APPLICATIONS,
                    label="Settings",
                ),
            ],
            border=ft.Border(
                top=ft.BorderSide(color=ft.CupertinoColors.SYSTEM_GREY2, width=2)
            ),
        )

    async def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)

    def route_change(route):
        page.views.clear()
        page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.Row(
                        [ft.Text(f"{gretting}, \n{USER_NAME}!", size=35)]
                        ),
                ],
                navigation_bar=create_navigation_bar(index=0),
            )
        )

        dropdown_value, set_dropdownvalue = "Светлая", ""
        faculty_dropdown_value = "-"

        # Статус чекбокса
        # checkbox_car_value, set_checkbox_car_value = ft.use_state(False)

        if page.route == "/alarm":
            page.views.append(
                ft.View(
                    route="/alarm",
                    controls=[
                        ft.Row(
                            [ft.Text("Будильники", size=25)], 
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                    ],
                    navigation_bar=create_navigation_bar(index=2),
                )
            )

        if page.route == "/planner":
            page.views.append(
                ft.View(
                    route="/planner",
                    controls=[
                        ft.Row(
                            [ft.Text("Расписание", size=25)], 
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                    ],
                    navigation_bar=create_navigation_bar(index=1),
                )
            )

        if page.route == "/settings":
            page.views.append(
                ft.View(
                    route="/settings",
                    scroll=ft.ScrollMode.HIDDEN,
                    controls=[
                        ft.Row(
                            [ft.Text("Настройки", size=25)], 
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        ft.Row(
                            [ft.Text("Общие", size=15)], 
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        ft.Column([
                            ft.Row(
                                [
                                    ft.Text("Тема:"),
                                    ft.Dropdown(
                                        value=dropdown_value,
                                        options=[
                                            ft.DropdownOption("Тёмная"),
                                            ft.DropdownOption("Светлая"),
                                        ],
                                        # on_text_change=lambda e: set_dropdownvalue(e.control.value),
                                    ), 
                                ], 
                                alignment=ft.MainAxisAlignment.CENTER),
                        ],
                        spacing=0,
                        width=400,
                        height=80,
                        ),
                        ft.Divider(),
                        ft.Row(
                            [ft.Text("Персональные данные", size=15)], 
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        ft.Column([
                            ft.Row(
                                [
                                    ft.Text("Ваше имя:"),
                                    ft.TextField(
                                        value=USER_NAME,
                                        # on_change=lambda e: set_tb1_value(e.control.value),
                                    ),
                                    
                                ],
                                alignment=ft.MainAxisAlignment.CENTER),
                            ft.Row(
                                [
                                    ft.Text("Какое время вы затрачиваете на сборы:"),
                                    ft.TextField(
                                        value=0,
                                        # hint_text="минут",
                                        # on_change=lambda e: set_tb1_value(e.control.value),
                                    ),
                                    ft.Text(" минут"),
                                ], 
                                alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            ft.Row(
                                [
                                    ft.Text("Адрес проживания:"),
                                    ft.TextField(
                                        value="",
                                        # on_change=lambda e: set_tb1_value(e.control.value),
                                    ),
                                ], 
                                alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            ft.Row(
                                [
                                    ft.Text("Факультет:"),
                                    ft.Dropdown(
                                        value=faculty_dropdown_value,
                                        options=[
                                            ft.DropdownOption("ЭТФ"),
                                            ft.DropdownOption("ХТФ"),
                                            ft.DropdownOption("АКФ"),
                                            ft.DropdownOption("Гуманитарный"),
                                            ft.DropdownOption("МТФ"),
                                            ft.DropdownOption("Стройительный"),
                                            ft.DropdownOption("Прикладной математики и механики"),
                                            ft.DropdownOption("Горно-нефтяной"),
                                            ft.DropdownOption("Автодорожный"),
                                        ],
                                        # on_text_change=lambda e: set_dropdownvalue(e.control.value),
                                    ),
                                ], 
                                alignment=ft.MainAxisAlignment.CENTER, spacing=10
                            ),
                            ft.Row(
                                [
                                    ft.Checkbox(
                                        label="Имеется ли у вас своя машина, на которой вы ездите в университет",
                                        value=False
                                        # on_change=lambda e: set_checkbox_car_value(e.control.value),
                                    ),
                                ], 
                                alignment=ft.MainAxisAlignment.CENTER, spacing=10
                            ),
                        ],
                        spacing=5,
                        width=400,
                        height=300,
                        ),
                        ft.Divider(),
                        ft.Row(
                            [ft.Text("Экспорт расписания", size=15)], 
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        ft.Row(
                            [ft.Button(content="Экспорт из xlsx...")]
                        )
                        ],
                        
                        navigation_bar=create_navigation_bar(index=3),
                )
            )


    
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    route_change(page.route)

if __name__ == "__main__":
    ft.run(main)