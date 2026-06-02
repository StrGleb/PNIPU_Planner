import pathlib
import logging
import flet as ft
from bridges.planner_bridge import (
    has_native_schedule_parser,
    is_valid_date_text,
    normalize_duration_minutes,
    parse_schedule_xlsx_file,
)
from managers.config_manager import ConfigManager
from managers.planner_manager import PlannerManager
from managers.tasks_manager import TasksManager
from managers.schedule_manager import ScheduleManager, get_schedule_storage_path
from utils.campus_locations import FACULTIES

logger = logging.getLogger(__name__)

def normalize_duration_minutes(minutes: int) -> int:
    return max(0, minutes)

def build_settings_view(
    navigation_bar: ft.NavigationBar,
    config_manager: ConfigManager,
    schedule_manager: ScheduleManager,
    planner_manager: PlannerManager,
    tasks_manager: TasksManager,
    
    page: ft.Page,
    auto_alarm_service = None,
    on_schedule_changed = None,
) -> ft.View:
    cfg = config_manager.config

    def _apply_theme(theme_key: str):
        modes = {
            "light": ft.ThemeMode.LIGHT, 
            "dark": ft.ThemeMode.DARK, 
            "system": ft.ThemeMode.SYSTEM
        }
        page.theme_mode = modes.get(theme_key, ft.ThemeMode.SYSTEM)
        page.update()
    
    def _show_message(text: str):
        page.snack_bar = ft.SnackBar(ft.Text(text))
        page.snack_bar.open = True
        page.update()

    def _refresh_auto_alarm_if_needed():
        if auto_alarm_service is None or not config_manager.config.auto_alarm_enabled:
            return
        try:
            auto_alarm_service.handle_planner_change()
        except Exception:
            ...

    def _show_message(text: str):
        page.snack_bar = ft.SnackBar(ft.Text(text))
        page.snack_bar.open = True
        page.update()

    def _make_selector(
        options: list[tuple[str, str]],
        initial_key: str,
        on_select,
        width: int = 280,
    ) -> ft.Container:
        """
        Заменитель Dropdown, работающий на Android.
        Показывает текущее значение, при тапе открывает AlertDialog со списком.
        """
        current_key = [initial_key]

        label_map = {k: lbl for k, lbl in options}
        display_text = ft.Text(
            label_map.get(initial_key, initial_key),
            size = 14,
            color = ft.Colors.WHITE,
            expand = True,
        )

        selector_dialog = ft.AlertDialog(modal = True, title = ft.Text("Выберите значение"))
        page.overlay.append(selector_dialog)

        def pick(key: str):
            current_key[0] = key
            display_text.value = label_map.get(key, key)
            selector_dialog.open = False
            try:
                display_text.update()
            except Exception:
                pass
            page.update()
            on_select(key)

        def open_selector(e):
            selector_dialog.content = ft.Column(
                [
                    ft.ListTile(
                        title = ft.Text(lbl),
                        on_click = lambda e, k = key: pick(k),
                        selected = (key == current_key[0]),
                    )
                    for key, lbl in options
                ],
                tight = True,
                spacing = 0,
                scroll = ft.ScrollMode.AUTO,
                width = 300,
            )
            selector_dialog.open = True
            page.update()

        return ft.Container(
            content = ft.Row(
                [display_text, ft.Icon(ft.Icons.ARROW_DROP_DOWN, color = ft.Colors.WHITE70)],
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            width = width,
            bgcolor = ft.Colors.GREY_700,
            border_radius = 8,
            padding = ft.Padding.symmetric(horizontal = 12, vertical = 10),
            on_click = open_selector,
            ink = True,
        )

    # ── Тема ─────────────────────────────────────────────────────────────────────
    dd_theme = _make_selector(
        options = [("system", "Системная"), ("light", "Светлая"), ("dark", "Тёмная")],
        initial_key = cfg.theme,
        on_select = lambda key: (config_manager.set_theme(key), _apply_theme(key)),
        width = 200,
    )

    tf_name = ft.TextField(
        value = cfg.user_name,
        width = 280,
        on_blur = lambda e: config_manager.set_user_name(e.control.value.strip()),
    )

    def on_time_blur(e):
        previous_value = config_manager.config.get_together_time
        try:
            value = int(e.control.value)
            config_manager.set_get_together_time(normalize_duration_minutes(value))
        except ValueError:
            pass
        e.control.value = str(config_manager.config.get_together_time)
        if config_manager.config.get_together_time != previous_value:
            _refresh_auto_alarm_if_needed()
        page.update()

    tf_time = ft.TextField(
        value = str(cfg.get_together_time),
        width = 90,
        keyboard_type = ft.KeyboardType.NUMBER,
        on_blur = on_time_blur,
    )

    def on_address_blur(e):
        previous_value = config_manager.config.user_address
        config_manager.set_user_address(e.control.value.strip())
        e.control.value = config_manager.config.user_address
        if config_manager.config.user_address != previous_value:
            _refresh_auto_alarm_if_needed()
        page.update()

    tf_address = ft.TextField(
        value = cfg.user_address,
        width = 280,
        hint_text = "Пример: улица Попова, 1",
        # on_blur = lambda e: config_manager.set_user_address(e.control.value.strip()),
        on_blur = on_address_blur,
    )


    def on_semester_start_blur(e):
        previous_value = config_manager.config.semester_start
        value = e.control.value.strip()
        if is_valid_date_text(value):
            config_manager.set_semester_start(value)
        e.control.value = config_manager.config.semester_start
        if config_manager.config.semester_start != previous_value:
            _refresh_auto_alarm_if_needed()
        page.update()

    tf_semester = ft.TextField(
        value = cfg.semester_start,
        width = 140,
        hint_text = "ДД.ММ.ГГГГ",
        on_blur = on_semester_start_blur,
    )

    def on_first_even_change(e):
        previous_value = config_manager.config.first_week_even
        config_manager.set_first_week_even(e.control.value)
        if config_manager.config.first_week_even != previous_value:
            _refresh_auto_alarm_if_needed()

    cb_first_even = ft.Checkbox(
        label = "Первая неделя семестра чётная",
        value = cfg.first_week_even,
        on_change = lambda e: config_manager.set_first_week_even(e.control.value),
    )
      
    # ── Факультет ────────────────────────────────────────────────────────────────
    dd_faculty = _make_selector(
        options = [(f, f) for f in FACULTIES],
        initial_key = cfg.user_faculty if cfg.user_faculty in FACULTIES else FACULTIES[0],
        on_select = config_manager.set_user_faculty,
        width = 280,
    )

    # ── Способ передвижения ───────────────────────────────────────────────────────────────────
    valid_transport_keys = {"driving", "public_transport", "pedestrian"}
    dd_transport = _make_selector(
        options = [
            ("public_transport", "Общественный транспорт"),
            ("driving",          "Автомобиль"),
            ("pedestrian",       "Пеший ход"),
        ],
        initial_key = cfg.transport_type if cfg.transport_type in valid_transport_keys else "public_transport",
        on_select = config_manager.set_transport_type,
        width = 280,
    )
      

    def on_travel_blur(e):
        previous_value = config_manager.config.travel_time
        try:
            value = int(e.control.value)
            config_manager.set_travel_time(normalize_duration_minutes(value))
        except ValueError:
            pass
        e.control.value = str(config_manager.config.travel_time)
        if config_manager.config.travel_time != previous_value:
            _refresh_auto_alarm_if_needed()
        page.update()

    tf_travel = ft.TextField(
        value = str(cfg.travel_time),
        width = 90,
        keyboard_type = ft.KeyboardType.NUMBER,
        on_blur = on_travel_blur,
    )

    def row(label: str, control, hint: str = "") -> ft.Column:
        items = [
            ft.Text(label, size = 13, color = ft.Colors.GREY_600),
            control,
        ]
        if hint:
            items.append(ft.Text(hint, size = 11, color = ft.Colors.GREY_500, italic = True))
        return ft.Column(items, spacing = 4)

    selected_file_path = [None]

    async def open_file_picker(e: ft.Event[ft.ElevatedButton]):
        files = await ft.FilePicker().pick_files(allowed_extensions = ["xlsx"])
        if not files:
            return

        selected_file_path[0] = files[0].path
        dialog.title = ft.Text(f"Выбран файл: {files[0].name}")
        btn_confirm.disabled = False
        btn_confirm.text = "Подтвердить импорт"
        progress.visible = False
        page.show_dialog(dialog)
        page.update()

    import_note = ft.Text(
        "Первая неделя и дата начала берутся из файла автоматически.",
        size = 12,
        color = ft.Colors.GREY_600,
    )

    def close_import_dialog(e):
        dialog.open = False
        page.update()

    def confirm_import(e):
        if not selected_file_path[0]:
            _show_message("Сначала выберите xlsx-файл.")
            return

        if not has_native_schedule_parser():
            _show_message("Native XLSX-парсер пока недоступен.")
            return

        btn_confirm.disabled = True
        btn_confirm.text = "Загрузка..."
        progress.visible = True
        page.update()

        try:
            import_path = get_schedule_storage_path().with_name("schedule_import.json")
            parse_schedule_xlsx_file(selected_file_path[0], import_path)
            schedule_manager.import_schedule_json(import_path)

            if schedule_manager.template.semester_start:
                config_manager.set_semester_start(schedule_manager.template.semester_start)
            config_manager.set_first_week_even(schedule_manager.template.first_week_even)

            tf_semester.value = config_manager.config.semester_start
            cb_first_even.value = config_manager.config.first_week_even

            applied = schedule_manager.apply_template_to_planner(
                planner_manager,
                clear_existing = True,
            )
            tasks_manager.reconcile_with_lessons(planner_manager.get_all_lessons())
            _refresh_auto_alarm_if_needed()
            if on_schedule_changed is not None:
                try:
                    on_schedule_changed()
                except Exception:
                    pass

            dialog.open = False
            file_name = pathlib.Path(selected_file_path[0]).name
            if applied:
                _show_message(f"Расписание импортировано: {file_name}")
            else:
                _show_message(f"Файл импортирован, но семестр не применён: {file_name}")
        except Exception as exc:
            _show_message(f"Ошибка импорта: {exc}")
        finally:
            if "import_path" in locals() and import_path.exists():
                try:
                    import_path.unlink()
                except OSError:
                    pass
            btn_confirm.disabled = False
            btn_confirm.text = "Подтвердить импорт"
            progress.visible = False
            page.update()

    progress = ft.ProgressRing(visible = False, width = 20, height = 20, stroke_width = 2)

    btn_confirm = ft.ElevatedButton(
        "Подтвердить импорт",
        icon = ft.Icons.CHECK,
        on_click = confirm_import,
    )

    dialog = ft.AlertDialog(
        title = ft.Text(""),
        content = ft.Column(
            [
                import_note,
                ft.Container(height = 10),
                ft.Row([progress, btn_confirm], alignment = ft.MainAxisAlignment.CENTER),
            ],
            tight = True,
        ),
        actions = [
            ft.TextButton("Отмена", on_click = close_import_dialog),
        ],
        actions_alignment = ft.MainAxisAlignment.END,
    )

    btn_import = ft.ElevatedButton(
        "Импортировать из xlsx...",
        icon = ft.Icons.UPLOAD_FILE,
        on_click = open_file_picker,
    )

    def _show_about_dialog(e):
        """Открывает диалог с информацией о приложении"""
        
        about_dialog = ft.AlertDialog(
            modal = True,
            title = ft.Text("О приложении", size = 20, weight = ft.FontWeight.BOLD),
            content = ft.Container(
                width = 400,
                content = ft.Column(
                    [
                        # Блок 1: Инструкция
                        ft.ExpansionTile(
                            title = ft.Text("Инструкция", weight = ft.FontWeight.W_600),
                            subtitle = ft.Text("Как пользоваться приложением", size = 12, color = ft.Colors.GREY_600),
                            controls = [
                                ft.Container(
                                    padding = ft.Padding.only(bottom = 12),
                                    content = ft.Column(
                                        [
                                            ft.Text(
                                                "1. Добавьте расписание через импорт xlsx файла",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "2. Настройте автобудильник в разделе 'Будильники'",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "3. Укажите адрес и факультет для расчёта маршрута",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "4. Следите за заданиями на главной странице",
                                                size = 13,
                                            ),
                                        ],
                                        spacing = 6,
                                    ),
                                ),
                            ],
                        ),
                        
                        # Блок 2: Пользовательское соглашение
                        ft.ExpansionTile(
                            title = ft.Text("Пользовательское соглашение", weight = ft.FontWeight.W_600),
                            subtitle = ft.Text("Условия использования", size = 12, color = ft.Colors.GREY_600),
                            controls=[
                                ft.Container(
                                    padding = ft.Padding.only(bottom = 12),
                                    content = ft.Column(
                                        [
                                            ft.Text(
                                                "Используя это приложение, вы соглашаетесь:\n",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "• Приложение предоставляет информацию о расписании и будильниках",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "• Мы не гарантируем 100% точность данных",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "• Ваши данные хранятся локально на устройстве",
                                                size = 13,
                                            ),
                                            ft.Text(
                                                "• Приложение предоставляется 'как есть'",
                                                size = 13,
                                            ),
                                        ],
                                        spacing = 6,
                                    ),
                                ),
                            ],
                        ),
                        
                        # Блок 3: О нас
                        ft.ExpansionTile(
                            title = ft.Text("О нас", weight = ft.FontWeight.W_600),
                            subtitle = ft.Text("Информация о разработчиках", size = 12, color = ft.Colors.GREY_600),
                            controls = [
                                ft.Container(
                                    padding = ft.Padding.only(bottom = 12),
                                    content = ft.Column(
                                        [
                                            ft.Text(
                                                "University Planner - приложение для студентов,\nпомогающее организовать учебный процесс.\n",
                                                size = 13,
                                                italic = True,
                                            ),
                                            ft.Text(
                                                "Разработано студентами ПНИПУ ЭТФ кафедры ИТАС.\n",
                                                size = 13,
                                                italic = True,
                                            ),
                                            ft.Text(
                                                "Версия: 0.1.0",
                                                size = 13,
                                                weight = ft.FontWeight.W_500,
                                            ),
                                            ft.Text(
                                                "© 2026 Все права защищены",
                                                size = 12,
                                                color = ft.Colors.GREY_600,
                                            ), 
                                        ],
                                        spacing = 8,
                                    ),
                                ),
                            ],
                        ),
                    ],
                    spacing = 8,
                    tight = True,
                    scroll = ft.ScrollMode.AUTO,
                ),
            ),
            actions = [
                ft.TextButton("Закрыть", on_click = lambda e: close_about_dialog(about_dialog)),
            ],
            actions_alignment = ft.MainAxisAlignment.END,
        )
        
        page.overlay.append(about_dialog)
        about_dialog.open = True
        page.update()

    def close_about_dialog(dialog):
        """Закрывает диалог 'О приложении'"""
        dialog.open = False
        page.update()

    return ft.View(
        route = "/settings",
        scroll = ft.ScrollMode.HIDDEN,
        padding = 0,
        controls = [
            ft.SafeArea(
                content = ft.Container(
                    padding = ft.Padding.symmetric(horizontal = 20, vertical = 16),
                    content = ft.Column(
                        controls = [
                            ft.Text("Настройки", size = 26, weight = ft.FontWeight.BOLD),
                            ft.Container(height = 8),
                            ft.Text("Оформление", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            row("Цветовая тема", dd_theme),
                            ft.Container(height = 12),
                            ft.Text("Персональные данные", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            row("Ваше имя", tf_name),
                            row("Время на сборы (мин)", tf_time),
                            row("Адрес проживания", tf_address, "Нужен для расчёта маршрута по API."),
                            row("Факультет", dd_faculty),
                            row("Способ передвижения", dd_transport, "Влияет на расчёт маршрута и авто-будильника."),
                            row("Время до ВУЗа (мин)", tf_travel, "Запасной вариант, если API-маршрут недоступен."),
                            ft.Container(height = 12),
                            ft.Text("Семестр", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            row(
                                "Начало семестра",
                                tf_semester,
                                "Можно изменить вручную, но после импорта значение обновится из файла.",
                            ),
                            cb_first_even,
                            ft.Container(height = 12),
                            ft.Text("Импорт расписания", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            import_note,
                            ft.Container(height = 8),
                            btn_import,
                            ft.Container(height = 12),
                            ft.Text("Сведения о приложении", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            ft.ElevatedButton(
                                "О приложении",
                                icon = ft.Icons.INFO_OUTLINE,
                                on_click = _show_about_dialog,
                            ),
                            ft.Text(
                                "Версия: 0.1.0",
                                size = 12,
                                weight = ft.FontWeight.W_500,
                                color = ft.Colors.GREY_500,
                            ),
                            ft.Container(height = 20),
                        ]
                    ),
                )
            )
        ],
        navigation_bar = navigation_bar,
    )
