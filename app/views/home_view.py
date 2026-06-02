import datetime

import flet as ft

from bridges.planner_bridge import time_to_minutes
from managers.tasks_manager import TasksManager
from utils.time_utils import greeting_choose
from utils.weather_utils import get_weather_by_coords, get_weather_recommendation

PRIORITY_DOT_COLORS = {
    0: ft.Colors.GREY_400,
    1: ft.Colors.BLUE_400,
    2: ft.Colors.ORANGE_400,
    3: ft.Colors.RED_500,
}

def get_current_theme(page: ft.Page) -> str:
    """
    Возвращает реальную активную тему ("light" или "dark"),
    даже если в настройках приложения выбрана "системная" тема.
    """
    # 1. Если тема жестко зафиксирована в приложении, возвращаем её
    if page.theme_mode == ft.ThemeMode.LIGHT or page.theme_mode == "light":
        return "light"
    if page.theme_mode == ft.ThemeMode.DARK or page.theme_mode == "dark":
        return "dark"
        
    # 2. Если тема системная, опрашиваем реальное состояние ОС Android/Windows
    if page.platform_brightness == "dark":
        return "dark"
    
    return "light"


def build_home_view(
    navigation_bar: ft.NavigationBar,
    user_name: str,
    tasks_manager: TasksManager,
    theme: ft.Page, 
    notifications = None,
    config_manager = None,
) -> ft.View:
    greeting = greeting_choose()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days = 1)

    def _sort_tasks_by_time(items: list) -> list:
        return sorted(
            items,
            key = lambda task: (time_to_minutes(task.time_start), task.subject.lower(), task.text.lower()),
        )

    tests_today = _sort_tasks_by_time(tasks_manager.get_tests_for_date(today))
    tests_tomorrow = _sort_tasks_by_time(tasks_manager.get_tests_for_date(tomorrow))
    homework_tomorrow = _sort_tasks_by_time(tasks_manager.get_homework_for_date(tomorrow))
    labs_tomorrow = _sort_tasks_by_time(tasks_manager.get_labs_for_date(tomorrow))
    
    # Определяем текущую активную тему
    current_theme = get_current_theme(theme)


    # ── Получение погоды ────────────────────────────────────────
    weather_data = None
    weather_widget = None

    if config_manager and config_manager.config.user_address.strip():
        # address = "Пермь, " + config_manager.config.user_address
        coords = 1
        if coords:
            latitude = 58.0105
            longitude = 56.2502
            weather_data = get_weather_by_coords(latitude, longitude)

    if weather_data:
        temp = weather_data["temp"]
        feels_like = weather_data["feels_like"]
        icon = weather_data["icon"]
        description = weather_data["description"]
        recommendation = get_weather_recommendation(temp)

        # Градиент для ТЁМНОЙ темы (глубокий синий)
        dark_theme_gradient = ft.LinearGradient(
            begin = ft.Alignment(0, -1),
            end = ft.Alignment(0, 1),
            colors = [ft.Colors.BLUE_900, ft.Colors.BLUE_800]
        )

        # Градиент для СВЕТЛОЙ темы (нежный светлый переход)
        white_theme_gradient = ft.LinearGradient(
            begin = ft.Alignment(0, -1),
            end = ft.Alignment(0, 1),
            colors = [ft.Colors.BLUE_200, ft.Colors.BLUE_50]
        )

        # Выбираем оформление виджета погоды в зависимости от темы
        active_gradient = dark_theme_gradient if current_theme == "dark" else white_theme_gradient
        text_color = ft.Colors.WHITE if current_theme == "dark" else ft.Colors.GREY_800
        subtext_color = ft.Colors.WHITE70 if current_theme == "dark" else ft.Colors.GREY_600
        recommendation_color = ft.Colors.BLUE_100 if current_theme == "dark" else ft.Colors.BLUE_800

        weather_widget = ft.Container(
            content=ft.Row(
                [
                    # ЛЕВАЯ ЧАСТЬ: Иконка и температура
                    ft.Row(
                        [
                            ft.Text(f"{icon}", size = 40),
                            ft.Column(
                                [
                                    ft.Text(f"{temp}°C", size = 28, weight = ft.FontWeight.BOLD, color = text_color),
                                    ft.Text(f"Ощущается как {feels_like}°C", size = 14, color = subtext_color),
                                ],
                                spacing = 0,
                            ),
                        ],
                        spacing = 10,
                        vertical_alignment = ft.CrossAxisAlignment.CENTER,
                    ),
                    
                    # Красивый нативный вертикальный разделитель
                    ft.VerticalDivider(width = 20, color = ft.Colors.BLUE_100),
                    
                    # ПРАВАЯ ЧАСТЬ: Описание погоды и рекомендация по одежде
                    ft.Column(
                        [
                            ft.Text(
                                description.capitalize(), 
                                size = 16, 
                                color = text_color, 
                                weight = ft.FontWeight.W_500
                            ),
                            ft.Text(
                                f"👔 {recommendation}",
                                size = 13,
                                color = recommendation_color,
                                italic = True,
                            ),
                        ],
                        spacing = 4,
                        expand = True, # Позволяет тексту занимать все свободное место и красиво переноситься
                        alignment = ft.MainAxisAlignment.CENTER,
                    ),
                ],
                alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            gradient=active_gradient,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
            height = 120, # Фиксируем высоту карточки для идеального выравнивания разделителя
        )
    else:
        weather_widget = ft.Container(
            content=ft.Column(
                [
                    ft.Text("⚠️ Не удалось загрузить данные о погоде", size = 14, color = ft.Colors.GREY_500),
                    ft.Text("Проверьте наличие API ключа Яндекс и адрес в настройках", size = 12, color = ft.Colors.GREY_400),
                ],
                spacing = 4,
            ),
            bgcolor = ft.Colors.GREY_100,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _task_row(task) -> ft.Row:
        dot = ft.Container(
            width = 10,
            height = 10,
            border_radius = 5,
            bgcolor = PRIORITY_DOT_COLORS.get(task.priority, ft.Colors.GREY_400),
        )
        return ft.Row(
            [dot, ft.Text(task.display_line, size = 14, expand = True, color = ft.Colors.BLACK)],
            spacing = 8,
            vertical_alignment = ft.CrossAxisAlignment.CENTER,
        )

    def _task_box(items: list, empty_text: str, box_color = ft.Colors.GREY_200) -> ft.Container:
        content_controls = [_task_row(task) for task in items] if items else [
            ft.Text(empty_text, size = 14, italic = True, color = ft.Colors.GREY_500)
        ]
        return ft.Container(
            content = ft.Column(content_controls, spacing = 8),
            bgcolor = box_color,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _dual_task_box(
        today_items: list,
        tomorrow_items: list,
        empty_today_text: str,
        empty_tomorrow_text: str,
        box_color = ft.Colors.GREY_200,
    ) -> ft.Container:
        def _subsection(title: str, items: list, empty_text: str) -> ft.Column:
            content_controls = [_task_row(task) for task in items] if items else [
                ft.Text(empty_text, size = 14, italic = True, color = ft.Colors.GREY_500)
            ]
            return ft.Column(
                [
                    ft.Text(title, size = 13, weight = ft.FontWeight.W_600, color = ft.Colors.GREY_800),
                    ft.Container(height = 4),
                    *content_controls,
                ],
                spacing = 8,
            )

        return ft.Container(
            content = ft.Column(
                [
                    _subsection("Сегодня", today_items, empty_today_text),
                    ft.Divider(height = 18),
                    _subsection("Завтра", tomorrow_items, empty_tomorrow_text),
                ],
                spacing = 0,
            ),
            bgcolor = box_color,
            border_radius = 16,
            padding = ft.Padding.symmetric(horizontal = 16, vertical = 14),
            width = float("inf"),
        )

    def _section(label: str, box: ft.Container) -> ft.Column:
        return ft.Column(
            [ft.Text(label, size = 15, weight = ft.FontWeight.BOLD), ft.Container(height = 6), box],
            spacing = 0,
        )
    
    # ── ДИАЛОГ ПЛАНИРОВАНИЯ УВЕДОМЛЕНИЙ ──────────────────────────────────────────
    notification_dialog = ft.AlertDialog(modal = True, title = ft.Text("Новое уведомление"))
    theme.overlay.append(notification_dialog)

    def open_notification_dialog(e):
        import datetime
        
        time_field = ft.TextField(
            label = "Время (ЧЧ:ММ)", 
            value = datetime.datetime.now().strftime("%H:%M"), 
            width = 140,
            keyboard_type = ft.KeyboardType.NUMBER
        )
        text_field = ft.TextField(
            label = "Текст напоминания", 
            hint_text = "Пример: Пора собираться в университет!",
            width = 300
        )
        error_text = ft.Text("", color = ft.Colors.RED_400, size = 12)

        async def save_notification(e):
            try:
                # 1. Запрашиваем нативные разрешения перед планированием
                await notifications.request_permissions()
                await notifications.request_exact_alarm_permission()

                # 2. Парсим введенное время ЧЧ:ММ
                time_str = time_field.value.strip()
                h, m = map(int, time_str.split(":"))
                assert 0 <= h <= 23 and 0 <= m <= 59
                
                # 3. Рассчитываем точное время запуска
                now = datetime.datetime.now()
                target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                
                # Если введенное время на сегодня уже прошло, планируем на завтра!
                if target_dt < now:
                    target_dt += datetime.timedelta(days=1)
                
                scheduled_time_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
                body_text = text_field.value.strip() or "Университетский Помощник"
                
                # Генерируем уникальный ID уведомления (на основе таймстампа)
                notif_id = int(target_dt.timestamp()) % 100000

                # 4. Вызываем нативный планировщик!
                await notifications.schedule_notification(
                    notification_id = notif_id,
                    title = "⏰ Напоминание",
                    body = body_text,
                    scheduled_time = scheduled_time_str
                )

                # Закрываем диалог
                notification_dialog.open = False
                theme.update()

                # Показываем Snack-бар с подтверждением
                theme.snack_bar = ft.SnackBar(ft.Text(f"Будильник заведен на {target_dt.strftime('%d.%m %H:%M')} ✓"))
                theme.snack_bar.open = True
                theme.update()

            except Exception:
                error_text.value = "Ошибка! Проверьте формат времени (ЧЧ:ММ)."
                theme.update()

        def cancel_notification(e):
            notification_dialog.open = False
            theme.update()

        notification_dialog.content = ft.Column(
            [
                ft.Row([time_field], alignment = ft.MainAxisAlignment.CENTER),
                text_field,
                error_text
            ],
            tight = True,
            spacing = 12,
            width = 300,
        )
        notification_dialog.actions = [
            ft.TextButton("Отмена", on_click = cancel_notification),
            ft.FilledButton("Запланировать", on_click = save_notification),
        ]
        notification_dialog.open = True
        theme.update()

    # Создаем кнопку быстрого напоминания
    btn_notify = ft.ElevatedButton(
        "Запланировать напоминание",
        icon = ft.Icons.NOTIFICATION_ADD,
        on_click = open_notification_dialog,
    )

    return ft.View(
        route = "/",
        scroll = ft.ScrollMode.AUTO, 
        padding = 0,
        controls = [
            ft.SafeArea(
                content = ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 20, vertical = 24),
                    content = ft.Column(
                        [
                            ft.Text(
                                f"{greeting},\n{user_name or 'студент'}!",
                                size = 30,
                                weight = ft.FontWeight.BOLD,
                            ),
                            ft.Container(height = 20),
                            btn_notify,
                            ft.Container(height = 10),
                            weather_widget,
                            ft.Container(height = 16),
                            _section(
                                "Ваши контрольные работы:",
                                _dual_task_box(
                                    tests_today,
                                    tests_tomorrow,
                                    "Контрольных работ сегодня нет",
                                    "Контрольных работ на завтра нет",
                                    ft.Colors.RED_100,
                                ),
                            ),
                            ft.Container(height = 16),
                            _section(
                                "Ваши домашние работы на завтра:",
                                _task_box(
                                    homework_tomorrow,
                                    "Домашних работ на завтра нет",
                                    ft.Colors.BLUE_100,
                                ),
                            ),
                            ft.Container(height = 16),
                            _section(
                                "Ваши лабораторные на завтра:",
                                _task_box(
                                    labs_tomorrow,
                                    "Лабораторных работ на завтра нет",
                                    ft.Colors.GREEN_100,
                                ),
                            ),
                            ft.Container(height = 16),
                        ],
                    )
                )
            )
        ],
        navigation_bar = navigation_bar,
    )