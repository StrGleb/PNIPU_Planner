import flet as ft


def main(page: ft.Page):
    page.title = "Planner App Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    user_name = 'Семён'

    page.add(
        ft.Row(
            alignment = ft.MainAxisAlignment.CENTER,
            controls=[ft.Text(value="Hello")]
        )
    )

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
                    ft.Row([ft.Text(f"Добро пожаловать, \n{user_name}!", size=35)]),
                ],
                navigation_bar=create_navigation_bar(index=0),
            )
        )

        dropdown_value, set_dropdownvalue = "Светлая", ""

        if page.route == "/alarm":
            page.views.append(
                ft.View(
                    route="/alarm",
                    controls=[
                        ft.Text("Welcome to Alarm Page"),
                    ],
                    navigation_bar=create_navigation_bar(index=2),
                )
            )

        if page.route == "/planner":
            page.views.append(
                ft.View(
                    route="/planner",
                    controls=[
                        ft.Text("Welcome to Planner Page"),
                    ],
                    navigation_bar=create_navigation_bar(index=1),
                )
            )

        if page.route == "/settings":
            page.views.append(
                ft.View(
                    route="/settings",
                    controls=[
                        ft.Row(
                            [ft.Text("Настрйоки", size=25)], 
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
                        height=100,
                        ),
                        ft.Divider(),
                        ],
                        
                        navigation_bar=create_navigation_bar(index=3),
                )
            )


    
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    route_change(page.route)

if __name__ == "__main__":
    ft.run(main)