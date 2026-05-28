import flet as ft
import sys
import pathlib
import logging
import datetime
from managers.config_manager import ConfigManager
from utils.excel_parser.parser_start_point import finally_excel_parser_algorithm
from managers.planner_manager import PlannerManager
from managers.schedule_manager import ScheduleManager

logger = logging.getLogger(__name__)

# if sys.platform == 'win32':
#     from bridges.planner_bridge import lib
#     normalize_duration_minutes = lib.normalize_duration_minutes
# else:
#     from bridges.planner_bridge import normalize_duration_minutes

def normalize_duration_minutes(minutes: int) -> int:
    return max(0, minutes)

FACULTIES = [
    "ЭТФ - Электротехнический факультет", 
    "ХТФ - Факультет химических технологий, промышленной экологии и биотехнологий", 
    "АКФ - Аэрокосмический факультет", 
    "Гуманитарный факультет", 
    "МТФ - Механико-технологический факультет",
    "Строительный факультет", 
    "Прикладной математики и механики факультет",
    "ГНФ - Горно-нефтяной факультет", 
    "Автодорожный факультет",
]

TRANSPORT_TYPE = [
    ft.DropdownOption(key = "public_transport", text = "Общественный транспорт"),
    ft.DropdownOption(key = "driving", text = "Автомобиль"),
    ft.DropdownOption(key = "pedestrian", text = "Пеший ход"),
]

THEME_OPTIONS = [
    ft.DropdownOption(key = "system", text = "Системная"),
    ft.DropdownOption(key = "light", text = "Светлая"),
    ft.DropdownOption(key = "dark", text = "Тёмная"),
]




def build_settings_view(
    navigation_bar: ft.NavigationBar,
    config_manager: ConfigManager,
    planner_manager: PlannerManager,
    schedule_manager: ScheduleManager,
    page: ft.Page,
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

    def _make_selector(
        options: list[tuple[str, str]],  # [(key, label), ...]
        initial_key: str,
        on_select,  # callback(key: str)
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

    # ── Имя ──────────────────────────────────────────────────────────────────────
    tf_name = ft.TextField(
        value = cfg.user_name,
        width = 280,
        on_blur = lambda e: config_manager.set_user_name(e.control.value.strip()),
    )

    # ── Время на сборы ────────────────────────────────────────────────────────────
    def on_time_blur(e):
        try:
            v = int(e.control.value)
            config_manager.set_get_together_time(normalize_duration_minutes(v))
        except ValueError:
            e.control.value = str(cfg.get_together_time)
            page.update()

    tf_time = ft.TextField(
        value = str(cfg.get_together_time),
        width = 90,
        keyboard_type = ft.KeyboardType.NUMBER,
        on_blur = on_time_blur,
    )

    # ── Адрес ────────────────────────────────────────────────────────────────────
    tf_address = ft.TextField(
        value = cfg.user_address,
        width = 280,
        hint_text="Пример: улица Попова, 1",
        on_blur = lambda e: config_manager.set_user_address(e.control.value.strip()),
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

    # ── Время до ВУЗа ────────────────────────────────────────────────────────────
    def on_travel_blur(e):
        try:
            v = int(e.control.value)
            config_manager.set_travel_time(normalize_duration_minutes(v))
        except ValueError:
            e.control.value = str(cfg.travel_time)
            page.update()

    tf_travel = ft.TextField(
        value = str(cfg.travel_time),
        width = 90,
        keyboard_type = ft.KeyboardType.NUMBER,
        on_blur = on_travel_blur,
    )

    # ── Вспомогательная функция разметки ─────────────────────────────────────────
    def row(label: str, control, hint: str = "") -> ft.Column:
        items = [
            ft.Text(label, size = 13, color = ft.Colors.GREY_600),
            control,
        ]
        if hint:
            items.append(ft.Text(hint, size = 11, color = ft.Colors.GREY_500, italic = True))
        return ft.Column(items, spacing = 4)

    # ── Переменная для сохранения пути к выбранному файлу ──────────────────────────
    selected_file_path = [None]
    async def open_file_picker(e: ft.Event[ft.ElevatedButton]):
        files = await ft.FilePicker().pick_files(allowed_extensions = ["xlsx"])
        
        # Если пользователь выбрал файл
        if files:
            selected_file_path[0] = files[0].path # Сохраняем локальный путь к файлу на телефоне
            dialog.title = ft.Text(f"Выбран файл: {files[0].name}") # Меняем заголовок диалога на имя выбранного файла
            # Сбрасываем визуальное состояние элементов диалога
            btn_confirm.disabled = False
            btn_confirm.text = "Подтвердить импорт"
            progress.visible = False
            
            # Открываем диалоговое окно подтверждения выбора
            page.show_dialog(dialog)
            page.update()
        else: return

    # ── Диалог импорта ────────────────────────────────────────────────────────────
    dd_semester = ft.Dropdown(
        label = "Выберите период",
        options = [
            ft.DropdownOption(text = "1 семестр - первая половина"),
            ft.DropdownOption(text = "1 семестр - вторая половина"),
            ft.DropdownOption(text = "2 семестр - первая половина"),
            ft.DropdownOption(text = "2 семестр - вторая половина"),
            ft.DropdownOption(text = "Экзамены"),
        ],
        width = 300,
    )

    def close_import_dialog(e):
        dialog.open = False
        page.update()

    def confirm_import(e):
        if not selected_file_path[0]:
            _show_message("Сначала выберите xlsx-файл.")
            return
        
        btn_confirm.disabled = True
        btn_confirm.text = "Загрузка..."
        progress.visible = True
        page.update()

    def confirm_import(e):
        # 1. Проверяем, выбран ли файл в проводнике
        if not selected_file_path[0]:
            _show_message("Сначала выберите xlsx-файл.")
            return
        
        # Визуально блокируем кнопку и показываем анимацию загрузки
        btn_confirm.disabled = True
        btn_confirm.text = "Загрузка..."
        progress.visible = True
        page.update()

        def finish_import():
            # 2. Запуск парсера на чистом Python (через вашу функцию и openpyxl)
            try:
                finally_excel_parser_algorithm(selected_file_path[0])
            except Exception as e:
                logger.error(f"Не удалось спарсить расписание из excel-файла: {e}")
                # Сбрасываем интерфейс в исходное состояние при ошибке
                progress.visible = False
                btn_confirm.disabled = False
                btn_confirm.text = "Подтвердить импорт"
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Ошибка импорта: {e}"),
                    bgcolor = ft.Colors.RED_700,
                )
                page.snack_bar.open = True
                page.update()
                return

            logger.info(f"[EXCEL IMPORT] Путь к файлу на Android: {selected_file_path[0]}")
            file_name = pathlib.Path(selected_file_path[0]).name

            # 3. Применение расписания (Динамически на основе ваших настроек!)
            try:
                logger.info("Начало применения расписания в приложение")
                schedule_manager.reload()
                # Применяем расписание к календарю
                schedule_manager.apply_semester(
                    planner_manager,
                    start_date = datetime.date(2026, 3, 30),
                    end_date = datetime.date(2026, 6, 30),
                    first_week_even = False,
                )
                logger.info("Окончание применения расписания в приложение")
            except Exception as e:
                logger.error(f"Не удалось применить расписание на необходимый семестр: {e}")

            logger.info("Успешное применения расписания в приложение")
            
            # Закрываем диалог и сбрасываем состояние кнопки загрузки
            page.pop_dialog()
            progress.visible = False
            btn_confirm.disabled = False
            btn_confirm.text = "Подтвердить импорт"
            
            # Показываем уведомление об успехе
            page.snack_bar = ft.SnackBar(ft.Text(f"Импорт завершён! Файл: {file_name}"))
            page.snack_bar.open = True
            page.update()
            return
        
        finish_import()

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
                dd_semester,
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

                            # Оформление
                            ft.Text("Оформление", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            row("Цветовая тема", dd_theme),
                            ft.Container(height = 12),

                            # Персональные данные
                            ft.Text("Персональные данные", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            row("Ваше имя", tf_name),
                            row("Время на сборы (мин)", tf_time),
                            row("Адрес проживания", tf_address),
                            row("Факультет", dd_faculty),
                            row("Время до ВУЗа (мин)", tf_travel, "временное решение"),
                            row("Способ передвижения", dd_transport),
                            # dd_transport,
                            ft.Container(height = 12),

                            # Экспорт
                            ft.Text("Экспорт расписания", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            btn_import,
                            ft.Container(height = 12),

                            # Раздел "О приложении"
                            ft.Divider(height = 1),
                            ft.ElevatedButton(
                                "О приложении",
                                icon = ft.Icons.INFO_OUTLINE,
                            ),
                            ft.Text("Версия: 0.1_beta", size = 12, weight = ft.FontWeight.W_500, color = ft.Colors.GREY_500),
                            ft.Container(height = 20),
                        ]
                    )
                )
            )
        ],
        navigation_bar = navigation_bar,
    )