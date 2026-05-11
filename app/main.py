import flet as ft
import threading
import datetime
from time import localtime, strftime, sleep

from views.home_view import build_home_view
from views.alarm_view import build_alarm_view
from views.planner_view import build_planner_view
from views.settings_view import build_settings_view
from managers.alarm_manager import AlarmManager
from managers.planner_manager import PlannerManager
from managers.schedule_manager import ScheduleManager
from managers.config_manager import ConfigManager
from managers.tasks_manager import TasksManager


def main(page: ft.Page):
    page.title = "Университетский помощник"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    config_manager = ConfigManager()
    tasks_manager = TasksManager() 

    now = lambda: strftime("%H:%M:%S", localtime())
    clock_text = ft.Text(value=now())

    # Применение темы приложения при старте
    modes = {"light": ft.ThemeMode.LIGHT, "dark": ft.ThemeMode.DARK, "system": ft.ThemeMode.SYSTEM}
    page.theme_mode = modes.get(config_manager.config.theme, ft.ThemeMode.SYSTEM)

    current_route = {"value": "/"}

    def update_time():
        while True:
            sleep(1)
            clock_text.value = now()
            try:
                clock_text.update()
            except Exception:
                pass

    threading.Thread(target=update_time, daemon=True).start()

    alarm_manager = AlarmManager()
    alarm_manager.start_background_checker()


    def global_alarm_callback(alarm):
        snack = ft.SnackBar(
            content=ft.Text(f"⏰ Сработал будильник: {alarm.label}!", size=18, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.BLUE_700,
            duration=5000,
        )
        
        page.overlay.append(snack)
        snack.open = True
        page.update()
        
    alarm_manager.set_trigger_callback(global_alarm_callback)
    # --------------------------

    planner_manager = PlannerManager()
    schedule_manager = ScheduleManager()

    # Демо-данные
    # planner_manager.load_from_dict({
    #     f"{__import__('datetime').date.today().strftime('%d.%m.%Y')} 8:00-9:30":   "Всеобщая история",
    #     f"{__import__('datetime').date.today().strftime('%d.%m.%Y')} 9:40-11:10":  "Математика (лек.)",
    # })

    # При первом запуске заполнить семестр (раскомментировать один раз):
    schedule_manager.apply_semester(
        planner_manager,
        start_date=datetime.date(2026, 3, 30),
        end_date=datetime.date(2026, 6, 30),
        first_week_even=False,   # 1 неделя = нечётная
    )

    # Хранит cleanup-функцию активного planner view
    _planner_cleanup = [None]

    # ── Navigation bar ───────────────────────────────────────────────────────────
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

    # ── Роутинг ──────────────────────────────────────────────────────────────────
    async def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)

    def route_change(route):
        current_route["value"] = page.route

        # Очищаем overlays предыдущего planner view
        if _planner_cleanup[0]:
            _planner_cleanup[0]()
            _planner_cleanup[0] = None

        page.views.clear()

        page.views.append(
            build_home_view(
                navigation_bar=create_navigation_bar(index=0),
                user_name=config_manager.config.user_name or "Студент",
                tasks_manager=tasks_manager,
            )
        )

        if page.route == "/alarm":
            page.views.append(
                build_alarm_view(
                    navigation_bar=create_navigation_bar(index=2),
                    clock_text=clock_text,
                    alarm_manager=alarm_manager,
                    page=page,
                )
            )

        elif page.route == "/planner":
            view, cleanup = build_planner_view(
                navigation_bar=create_navigation_bar(index=1),
                planner_manager=planner_manager,
                config_manager=config_manager,
                tasks_manager=tasks_manager,
                page=page,
            )
            page.views.append(view)
            _planner_cleanup[0] = cleanup

        elif page.route == "/settings":
            page.views.append(
                build_settings_view(
                    navigation_bar=create_navigation_bar(index=3),
                    config_manager=config_manager, # Все настройки переданы через конфиг
                    page=page, # Функционал переключения темы приложения
                )
            )

        page.update()

    page.on_route_change = route_change
    page.on_view_pop     = view_pop
    route_change(page.route)


if __name__ == "__main__":
    ft.run(main)
