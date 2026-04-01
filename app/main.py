import flet as ft
from time import localtime, strftime, sleep

from views.home_view import build_home_view
from views.alarm_view import build_alarm_view
from views.planner_view import build_planner_view
from views.settings_view import build_settings_view


# --- Глобальные настройки пользователя ---
USER_NAME = "Семён"
get_together_time = 0
user_address = ""
user_faculty = ""


def main(page: ft.Page):
    page.title = "Planner App"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Текст часов — создаётся один раз и переиспользуется в alarm_view
    now = lambda: strftime("%H:%M:%S", localtime())
    clock_text = ft.Text(value=now())

    def update_time():
        while True:
            clock_text.value = now()
            clock_text.update()
            sleep(1)

    # --- Navigation bar ---
    async def handle_change(e):
        routes = {0: "/", 1: "/planner", 2: "/alarm", 3: "/settings"}
        await page.push_route(routes[e.control.selected_index])

    def create_navigation_bar(index: int = 0) -> ft.NavigationBar:
        return ft.NavigationBar(
            selected_index=index,
            on_change=handle_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_ROUNDED, label="Home"),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                    selected_icon=ft.Icons.CALENDAR_TODAY,
                    label="Planner",
                ),
                ft.NavigationBarDestination(icon=ft.Icons.ACCESS_ALARM, label="Alarm"),
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

    # --- Роутинг ---
    async def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)

    def route_change(route):
        page.views.clear()

        # Главная страница — всегда в стеке
        page.views.append(
            build_home_view(
                navigation_bar=create_navigation_bar(index=0),
                user_name=USER_NAME,
            )
        )

        if page.route == "/alarm":
            page.views.append(
                build_alarm_view(
                    navigation_bar=create_navigation_bar(index=2),
                    clock_text=clock_text,
                )
            )

        elif page.route == "/planner":
            page.views.append(
                build_planner_view(
                    navigation_bar=create_navigation_bar(index=1),
                )
            )

        elif page.route == "/settings":
            page.views.append(
                build_settings_view(
                    navigation_bar=create_navigation_bar(index=3),
                    user_name=USER_NAME,
                    get_together_time=get_together_time,
                    user_address=user_address,
                    user_faculty=user_faculty,
                )
            )

        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    route_change(page.route)
    # update_time()


if __name__ == "__main__":
    ft.run(main)
