import logging
import sys
import threading
from time import localtime, sleep, strftime

import flet as ft

from managers.alarm_manager import AlarmManager
from managers.auto_alarm_service import AutoAlarmService
from managers.config_manager import ConfigManager
from managers.notification_manager import start_daily_checker
from managers.planner_manager import PlannerManager
from managers.schedule_manager import ScheduleManager
from managers.tasks_manager import TasksManager
from views.alarm_view import build_alarm_view
from views.home_view import build_home_view
from views.planner_view import build_planner_view
from views.settings_view import build_settings_view

is_android = hasattr(sys, "getandroidapilevel")

if sys.platform == "win32":
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename = "app.log",
        encoding = "utf-8"
    )
    logger = logging.getLogger(__name__)
else: 
    # Нужно, чтобы в при работе на Android dсе логи писались в терминал, а не в отдельный файлик
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger(__name__)


def main(page: ft.Page):
    try:
        page.title = "University Planner"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER

        config_manager = ConfigManager()
        tasks_manager = TasksManager()

        now = lambda: strftime("%H:%M:%S", localtime())
        clock_text = ft.Text(value=now())

        modes = {
            "light": ft.ThemeMode.LIGHT,
            "dark": ft.ThemeMode.DARK,
            "system": ft.ThemeMode.SYSTEM,
        }
        page.theme_mode = modes.get(config_manager.config.theme, ft.ThemeMode.SYSTEM)

        current_route = {"value": "/"}

        def update_time():
            while True:
                sleep(1)
                if current_route["value"] == "/alarm":
                    clock_text.value = now()
                    try:
                        clock_text.update()
                    except Exception as exc:
                        if "must be added" not in str(exc):
                            logger.error("Failed to update clock text: %s", exc)

        threading.Thread(target=update_time, daemon=True).start()

        from bridges.planner_bridge import is_week_even # ИМПОРТ
        import datetime
        alarm_manager = AlarmManager()
        alarm_manager.set_week_even_fn(
            lambda: is_week_even(
                datetime.date.today(),
                config_manager.config.semester_start,
                config_manager.config.first_week_even,
            )
        )

        def global_alarm_callback(alarm):
            snack = ft.SnackBar(
                content = ft.Text(
                    f"Alarm fired: {alarm.label}!",
                    size = 18,
                    weight = ft.FontWeight.BOLD,
                ),
                bgcolor = ft.Colors.BLUE_700,
                duration = 5000,
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()
            if alarm.is_auto_schedule:
                auto_alarm_service.handle_alarm_triggered(alarm)

        alarm_manager.set_trigger_callback(global_alarm_callback)

        planner_manager = PlannerManager()
        schedule_manager = ScheduleManager()
        if schedule_manager.template.semester_start:
            config_manager.set_semester_start(schedule_manager.template.semester_start)
        config_manager.set_first_week_even(schedule_manager.template.first_week_even)
        schedule_manager.apply_template_to_planner(planner_manager)
        tasks_manager.reconcile_with_lessons(planner_manager.get_all_lessons())
        start_daily_checker(tasks_manager)
        auto_alarm_service = AutoAlarmService(
            alarm_manager = alarm_manager,
            config_manager = config_manager,
            planner_manager = planner_manager,
        )
        alarm_manager.start_background_checker()
        auto_alarm_service.start()

        planner_cleanup = [None]

        def build_home_root():
            return build_home_view(
                navigation_bar = create_navigation_bar(index = 0),
                user_name = config_manager.config.user_name or "Студент",
                tasks_manager = tasks_manager,
                config_manager = config_manager,
                theme = page,
            )
        

        def refresh_home_view():
            home_view = build_home_root()
            if page.views:
                page.views[0] = home_view
            else:
                page.views.append(home_view)
            page.update()

        async def handle_change(e):
            routes = {0: "/", 1: "/planner", 2: "/alarm", 3: "/settings"}
            await page.push_route(routes[e.control.selected_index])

        def create_navigation_bar(index: int = 0) -> ft.NavigationBar:
            return ft.NavigationBar(
                selected_index = index,
                on_change = handle_change,
                destinations = [
                    ft.NavigationBarDestination(
                        icon = ft.Icons.HOME_ROUNDED,
                        label = "Home",
                    ),
                    ft.NavigationBarDestination(
                        icon = ft.Icons.CALENDAR_TODAY_OUTLINED,
                        selected_icon = ft.Icons.CALENDAR_TODAY,
                        label = "Planner",
                    ),
                    ft.NavigationBarDestination(
                        icon = ft.Icons.ACCESS_ALARM,
                        label = "Alarm",
                    ),
                    ft.NavigationBarDestination(
                        icon = ft.Icons.SETTINGS_APPLICATIONS_OUTLINED,
                        selected_icon = ft.Icons.SETTINGS_APPLICATIONS,
                        label = "Settings",
                    ),
                ],
                border = ft.Border(
                    top = ft.BorderSide(
                        color = ft.CupertinoColors.SYSTEM_GREY2,
                        width = 2,
                    )
                ),
            )

        async def view_pop(view):
            page.views.pop()
            top_view = page.views[-1]
            await page.push_route(top_view.route)

        def route_change(route):
            current_route["value"] = page.route

            if planner_cleanup[0]:
                planner_cleanup[0]()
                planner_cleanup[0] = None

            page.views.clear()
            page.views.append(build_home_root())

            if page.route == "/alarm":
                page.views.append(
                    build_alarm_view(
                        navigation_bar = create_navigation_bar(index = 2),
                        clock_text = clock_text,
                        alarm_manager = alarm_manager,
                        config_manager = config_manager,
                        auto_alarm_service = auto_alarm_service,
                        page = page,
                    )
                )
            elif page.route == "/planner":
                view, cleanup = build_planner_view(
                    navigation_bar = create_navigation_bar(index=1),
                    planner_manager = planner_manager,
                    config_manager = config_manager,
                    tasks_manager = tasks_manager,
                    auto_alarm_service = auto_alarm_service,
                    page = page,
                    on_tasks_changed = refresh_home_view,
                )
                page.views.append(view)
                planner_cleanup[0] = cleanup
            elif page.route == "/settings":
                page.views.append(
                    build_settings_view(
                        navigation_bar = create_navigation_bar(index = 3),
                        config_manager = config_manager,
                        schedule_manager = schedule_manager,
                        planner_manager = planner_manager,
                        auto_alarm_service = auto_alarm_service,
                        tasks_manager = tasks_manager,
                        page = page,
                        on_schedule_changed = refresh_home_view,
                    )
                )

            page.update()

        page.on_route_change = route_change
        page.on_view_pop = view_pop
        route_change(page.route)

    except Exception as e:
        import traceback

        error_text = traceback.format_exc()
        page.views.clear()
        page.views.append(
            ft.View(
                controls = [
                    ft.Text(
                        "Critical startup error:",
                        weight = "bold",
                        color = "red",
                        size = 20,
                    ),
                    ft.Text(error_text, selectable = True, size = 12),
                ],
                scroll = ft.ScrollMode.ALWAYS,
            )
        )
        page.update()


if __name__ == "__main__":
    ft.run(main)
