import flet as ft
import sys
import pathlib
import logging
from managers.config_manager import ConfigManager
from utils.excel_parser.parsaer_start_point import finally_excel_parser_algorithm

logger = logging.getLogger(__name__)

if sys.platform == 'win32':
    from bridges.planner_bridge import lib
    normalize_duration_minutes = lib.normalize_duration_minutes
else:
    from bridges.planner_bridge import normalize_duration_minutes

FACULTIES = [
    "ЭТФ - Электротехнический факультет", "ХТФ - Факультет химических технологий, промышленной экологии и биотехнологий", "АКФ - Аэрокосмический факультет", "Гуманитарный факультет", "МТФ - Механико-технологический факультет",
    "Строительный факультет", "Прикладной математики и механики факультет",
    "ГНФ - Горно-нефтяной факультет", "Автодорожный факультет",
]

TRANSPORT_TYPE = [
    "Автомобиль",
    "Общественный транспорт",
    "Пеший ход",
]

FACULTIES_COORDS = {
    "ЭТФ - Электротехнический факультет": [58.054531, 56.222769], 
    "ХТФ - Факультет химических технологий, промышленной экологии и биотехнологий": [58.054541, 56.223820],
    "АКФ - Аэрокосмический факультет": [58.054355, 56.231653], 
    "Гуманитарный факультет": [58.002134, 56.247455], 
    "МТФ - Механико-технологический факультет": [58.008495, 56.239190],
    "Строительный факультет": [57.984680, 56.247428], 
    "Прикладной математики и механики": [58.054531, 56.224898],
    "ГНФ - Горно-нефтяной факультет": [58.008295, 56.240250],
    "Автодорожный факультет": [58.056593, 56.235830],
}

THEME_OPTIONS = [
    ft.DropdownOption(key = "system", text = "Системная"),
    ft.DropdownOption(key = "light",  text = "Светлая"),
    ft.DropdownOption(key = "dark",   text = "Тёмная"),
]


def build_settings_view(
    navigation_bar: ft.NavigationBar,
    config_manager: ConfigManager,
    page: ft.Page,
) -> ft.View:
    cfg = config_manager.config

    def _apply_theme(theme_key: str):
        modes = {"light": ft.ThemeMode.LIGHT, "dark": ft.ThemeMode.DARK, "system": ft.ThemeMode.SYSTEM}
        page.theme_mode = modes.get(theme_key, ft.ThemeMode.SYSTEM)
        page.update()

    # ── Тема ─────────────────────────────────────────────────────────────────────
    def on_theme_change(e):
        config_manager.set_theme(e.control.value)
        _apply_theme(e.control.value)

    dd_theme = ft.Dropdown(
        value = cfg.theme,
        options = THEME_OPTIONS,
        width = 200,
    )
    dd_theme.on_change = on_theme_change

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
    dd_faculty = ft.Dropdown(
        value = cfg.user_faculty if cfg.user_faculty in FACULTIES else FACULTIES[0],
        options = [ft.DropdownOption(f) for f in FACULTIES],
        width = 280,
    )
    dd_faculty.on_change = lambda e: config_manager.set_user_faculty(e.control.value)

    # ── Способ передвижения ───────────────────────────────────────────────────────────────────
    dd_transport = ft.Dropdown(
        value = cfg.user_faculty if cfg.user_faculty in TRANSPORT_TYPE else TRANSPORT_TYPE[0],
        options = [ft.DropdownOption(f) for f in TRANSPORT_TYPE],
        width = 280,
    )
    # dd_transport.on_change = lambda e: config_manager.set_user_faculty(e.control.value)

    # ── Начало семестра ───────────────────────────────────────────────────────────
    def on_semester_start_blur(e):
        import re
        v = e.control.value.strip()
        if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v):
            config_manager.set_semester_start(v)
        else:
            e.control.value = cfg.semester_start
            page.update()

    tf_semester = ft.TextField(
        value = cfg.semester_start,
        width = 140,
        hint_text = "ДД.ММ.ГГГГ",
        on_blur = on_semester_start_blur,
    )

    cb_first_even = ft.Checkbox(
        label = "Первая неделя семестра чётная",
        value = cfg.first_week_even,
        on_change = lambda e: config_manager.set_first_week_even(e.control.value),
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

    # Инициализируем абсолютно пустой FilePicker (без on_result)
    file_picker = ft.FilePicker()

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

    # ── Диалог импорта ────────────────────────────────────────────────────────────
    dd_semester = ft.Dropdown(
        label = "Выберите период",
        options = [
            ft.DropdownOption(text = "1 семестр - первая половина"),
            ft.DropdownOption(text = "1 семестр - вторая половина"),
            ft.DropdownOption(text = "2 семестр - первая половина"),
            ft.DropdownOption(text = "2 семестр - вторая половина"),
        ],
        width = 300,
    )

    def close_import_dialog(e):
        dialog.open = False
        page.update()

    def confirm_import(e):
        # Имитация визуальной загрузки
        btn_confirm.disabled = True
        btn_confirm.text = "Загрузка..."
        progress.visible = True
        page.update()

        import threading
        import time

        def finish_import():
            # Обработка парсером
            finally_excel_parser_algorithm(selected_file_path[0])

            logger.debug(f"[EXCEL IMPORT] Путь к файлу на Android: {selected_file_path[0]}")
            dialog.open = False
            file_name = pathlib.Path(selected_file_path[0]).name
            page.snack_bar = ft.SnackBar(ft.Text(f"Импорт завершён! Файл: {file_name}"))
            page.snack_bar.open = True
            page.update()

        threading.Thread(target = finish_import, daemon = True).start()

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
        on_click = open_file_picker, # Теперь открывает FilePicker вместо прямого диалога
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
                            ft.Text("Сведения о приложении", size = 16, weight = ft.FontWeight.W_600),
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