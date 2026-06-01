import logging
import pathlib
import threading

import flet as ft

from bridges.planner_bridge import (
    has_native_schedule_parser,
    is_valid_date_text,
    normalize_duration_minutes,
    parse_schedule_xlsx_file,
)
from managers.config_manager import ConfigManager
from managers.planner_manager import PlannerManager
from managers.schedule_manager import ScheduleManager, get_schedule_storage_path
from managers.tasks_manager import TasksManager
from utils.campus_locations import FACULTIES
from utils.weather_utils import get_weather_for_config


logger = logging.getLogger(__name__)


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
    selected_file_path = [None]
    import_in_progress = [False]

    def _apply_theme(theme_key: str) -> None:
        modes = {
            "light": ft.ThemeMode.LIGHT,
            "dark": ft.ThemeMode.DARK,
            "system": ft.ThemeMode.SYSTEM,
        }
        page.theme_mode = modes.get(theme_key, ft.ThemeMode.SYSTEM)
        page.update()

    def _safe_page_update() -> None:
        try:
            page.update()
        except Exception as exc:
            logger.debug("Settings view update skipped: %s", exc)

    def _show_message(text: str) -> None:
        page.snack_bar = ft.SnackBar(ft.Text(text))
        page.snack_bar.open = True
        _safe_page_update()

    def _refresh_auto_alarm_if_needed() -> None:
        if auto_alarm_service is None or not config_manager.config.auto_alarm_enabled:
            return

        def _job() -> None:
            try:
                auto_alarm_service.handle_planner_change()
            except Exception:
                logger.exception("Failed to refresh auto alarm queue after settings change")

        threading.Thread(target = _job, daemon = True).start()

    def _refresh_location_and_weather() -> None:
        if not str(config_manager.config.user_address or "").strip():
            return

        def _job() -> None:
            try:
                get_weather_for_config(
                    config_manager,
                    force_refresh = True,
                    force_geocode = True,
                )
            except Exception:
                logger.exception("Failed to update coordinates and weather cache after address change")

        threading.Thread(target = _job, daemon = True).start()

    def _make_selector(
        options: list[tuple[str, str]],
        initial_key: str,
        on_select,
        width: int = 280,
    ) -> ft.Container:
        current_key = [initial_key]
        label_map = {key: label for key, label in options}
        display_text = ft.Text(
            label_map.get(initial_key, initial_key),
            size = 14,
            color = ft.Colors.WHITE,
            expand = True,
        )

        selector_dialog = ft.AlertDialog(modal = True, title = ft.Text("Выберите значение"))
        page.overlay.append(selector_dialog)
        selector_dialog.modal = False

        def pick(key: str) -> None:
            current_key[0] = key
            display_text.value = label_map.get(key, key)
            selector_dialog.open = False
            try:
                display_text.update()
            except Exception:
                pass
            page.update()
            on_select(key)

        def open_selector(e) -> None:
            selector_dialog.content = ft.Column(
                [
                    ft.ListTile(
                        title = ft.Text(label),
                        on_click = lambda e, selected_key = key: pick(selected_key),
                        selected = key == current_key[0],
                    )
                    for key, label in options
                ],
                tight = True,
                spacing = 0,
                scroll = ft.ScrollMode.AUTO,
                width = 300,
            )
            selector_dialog.open = True
            _safe_page_update()

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

    def on_time_blur(e) -> None:
        previous_value = config_manager.config.get_together_time
        try:
            value = int(e.control.value)
            config_manager.set_get_together_time(normalize_duration_minutes(value))
        except ValueError:
            pass
        e.control.value = str(config_manager.config.get_together_time)
        if config_manager.config.get_together_time != previous_value:
            _refresh_auto_alarm_if_needed()
        _safe_page_update()

    tf_time = ft.TextField(
        value = str(cfg.get_together_time),
        width = 90,
        keyboard_type = ft.KeyboardType.NUMBER,
        on_blur = on_time_blur,
    )

    def on_address_blur(e) -> None:
        previous_value = str(config_manager.config.user_address or "").strip()
        new_value = e.control.value.strip()
        config_manager.set_user_address(new_value)
        e.control.value = config_manager.config.user_address
        if new_value != previous_value:
            config_manager.clear_location_cache()
            _refresh_location_and_weather()
            _refresh_auto_alarm_if_needed()
        _safe_page_update()

    tf_address = ft.TextField(
        value = cfg.user_address,
        width = 280,
        hint_text = "Пример: улица Попова, 1",
        on_blur = on_address_blur,
    )

    def on_semester_start_blur(e) -> None:
        previous_value = config_manager.config.semester_start
        value = e.control.value.strip()
        if is_valid_date_text(value):
            config_manager.set_semester_start(value)
        e.control.value = config_manager.config.semester_start
        if config_manager.config.semester_start != previous_value:
            _refresh_auto_alarm_if_needed()
        _safe_page_update()

    tf_semester = ft.TextField(
        value = cfg.semester_start,
        width = 140,
        hint_text = "ДД.ММ.ГГГГ",
        on_blur = on_semester_start_blur,
    )

    def on_first_even_change(e) -> None:
        previous_value = config_manager.config.first_week_even
        config_manager.set_first_week_even(e.control.value)
        if config_manager.config.first_week_even != previous_value:
            _refresh_auto_alarm_if_needed()

    cb_first_even = ft.Checkbox(
        label = "Первая неделя семестра чётная",
        value = cfg.first_week_even,
        on_change = on_first_even_change,
    )

    def on_faculty_select(value: str) -> None:
        previous_value = config_manager.config.user_faculty
        config_manager.set_user_faculty(value)
        if config_manager.config.user_faculty != previous_value:
            _refresh_auto_alarm_if_needed()

    dd_faculty = _make_selector(
        options = [(faculty, faculty) for faculty in FACULTIES],
        initial_key = cfg.user_faculty if cfg.user_faculty in FACULTIES else FACULTIES[0],
        on_select = on_faculty_select,
        width = 280,
    )

    valid_transport_keys = {"driving", "public_transport", "pedestrian"}

    def on_transport_select(value: str) -> None:
        previous_value = config_manager.config.transport_type
        config_manager.set_transport_type(value)
        if config_manager.config.transport_type != previous_value:
            _refresh_auto_alarm_if_needed()

    dd_transport = _make_selector(
        options = [
            ("public_transport", "Общественный транспорт"),
            ("driving", "Автомобиль"),
            ("pedestrian", "Пешком"),
        ],
        initial_key = cfg.transport_type if cfg.transport_type in valid_transport_keys else "public_transport",
        on_select = on_transport_select,
        width = 280,
    )

    def on_travel_blur(e) -> None:
        previous_value = config_manager.config.travel_time
        try:
            value = int(e.control.value)
            config_manager.set_travel_time(normalize_duration_minutes(value))
        except ValueError:
            pass
        e.control.value = str(config_manager.config.travel_time)
        if config_manager.config.travel_time != previous_value:
            _refresh_auto_alarm_if_needed()
        _safe_page_update()

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

    import_file_title = ft.Text(
        "Файл ещё не выбран",
        size = 18,
        weight = ft.FontWeight.W_600,
        max_lines = 5,
    )
    import_status = ft.Text(
        "Первая неделя и дата начала берутся из файла автоматически.",
        size = 12,
        color = ft.Colors.GREY_600,
    )
    import_progress = ft.ProgressRing(visible = False, width = 20, height = 20, stroke_width = 2)

    btn_confirm = ft.FilledButton(
        "Подтвердить импорт",
        icon = ft.Icons.CHECK,
        disabled = True,
    )
    btn_cancel = ft.TextButton("Отмена")

    dialog = ft.AlertDialog(
        title = ft.Text("Импорт расписания / сессии"),
        content = ft.Column(
            [
                import_file_title,
                ft.Container(height = 8),
                import_status,
                ft.Container(height = 12),
                ft.Row(
                    [import_progress, btn_confirm],
                    spacing = 12,
                    vertical_alignment = ft.CrossAxisAlignment.CENTER,
                ),
            ],
            tight = True,
            width = 360,
        ),
        actions = [btn_cancel],
        actions_alignment = ft.MainAxisAlignment.END,
    )

    async def open_file_picker(e: ft.Event[ft.ElevatedButton]):
        files = await ft.FilePicker().pick_files(allowed_extensions = ["xlsx"])
        if not files:
            return

        selected_file_path[0] = files[0].path
        import_file_title.value = files[0].name
        import_status.value = "Файл готов к импорту. Во время обработки интерфейс останется отзывчивым."
        import_progress.visible = False
        btn_confirm.disabled = False
        btn_confirm.text = "Подтвердить импорт"
        btn_cancel.disabled = False
        page.show_dialog(dialog)
        _safe_page_update()

    def _set_import_state(*, loading: bool, status_text: str, confirm_enabled: bool, confirm_text: str) -> None:
        import_in_progress[0] = loading
        import_progress.visible = loading
        import_status.value = status_text
        btn_confirm.disabled = not confirm_enabled
        btn_confirm.text = confirm_text
        btn_cancel.disabled = loading
        try:
            if page.route == "/settings":
                page.update()
        except Exception as exc:
            logger.debug("Import dialog update skipped: %s", exc)

    def close_import_dialog(e) -> None:
        if import_in_progress[0]:
            return
        dialog.open = False
        _safe_page_update()

    def confirm_import(e) -> None:
        if not selected_file_path[0]:
            _show_message("Сначала выберите xlsx-файл.")
            return

        if not has_native_schedule_parser():
            _show_message("Native XLSX-парсер пока недоступен.")
            return

        def _import_job() -> None:
            import_path = None
            file_name = pathlib.Path(selected_file_path[0]).name
            applied = False
            try:
                _set_import_state(
                    loading = True,
                    status_text = "Импортируем файл и собираем шаблон расписания...",
                    confirm_enabled = False,
                    confirm_text = "Импортируем...",
                )
                import_path = get_schedule_storage_path().with_name("schedule_import.json")
                parse_schedule_xlsx_file(selected_file_path[0], import_path)
                schedule_manager.import_schedule_json(import_path)

                if schedule_manager.template.semester_start:
                    config_manager.set_semester_start(schedule_manager.template.semester_start)
                config_manager.set_first_week_even(schedule_manager.template.first_week_even)

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
                        logger.exception("Failed to refresh home view after import")

                tf_semester.value = config_manager.config.semester_start
                cb_first_even.value = config_manager.config.first_week_even
                dialog.open = False
                message = (
                    f"Расписание импортировано: {file_name}"
                    if applied
                    else f"Файл импортирован, но семестр не был применён: {file_name}"
                )
                _show_message(message)
            except Exception as exc:
                logger.exception("Import failed")
                _set_import_state(
                    loading = False,
                    status_text = f"Ошибка импорта: {exc}",
                    confirm_enabled = True,
                    confirm_text = "Повторить импорт",
                )
                return
            finally:
                if import_path is not None and import_path.exists():
                    try:
                        import_path.unlink()
                    except OSError:
                        pass

            _set_import_state(
                loading = False,
                status_text = "Импорт завершён.",
                confirm_enabled = True,
                confirm_text = "Подтвердить импорт",
            )
            _safe_page_update()

        threading.Thread(target = _import_job, daemon = True).start()

    btn_confirm.on_click = confirm_import
    btn_cancel.on_click = close_import_dialog

    import_note = ft.Text(
        "Первая неделя, дата начала, а также файлы сессии подхватываются автоматически из выбранного XLSX.",
        size = 12,
        color = ft.Colors.GREY_600,
    )

    btn_import = ft.ElevatedButton(
        "Импортировать расписание / сессию",
        icon = ft.Icons.UPLOAD_FILE,
        on_click = open_file_picker,
    )

    coordinates = config_manager.get_user_coordinates()
    coordinates_hint = "Координаты сохраняются автоматически после изменения адреса."
    if coordinates is not None:
        coordinates_hint = f"Текущие координаты: {coordinates[1]:.6f}, {coordinates[0]:.6f}"

    weather_hint = "Погода и координаты обновляются не чаще одного раза в 6 часов."

    return ft.View(
        route = "/settings",
        scroll = ft.ScrollMode.AUTO,
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
                            row("Адрес проживания", tf_address, "Нужен для маршрута, кэша координат и погодного виджета."),
                            ft.Text(coordinates_hint, size = 11, color = ft.Colors.GREY_500, italic = True),
                            ft.Text(weather_hint, size = 11, color = ft.Colors.GREY_500, italic = True),
                            row("Факультет", dd_faculty),
                            row("Способ передвижения", dd_transport, "Влияет на расчёт маршрута и авто-будильника."),
                            row("Время до ВУЗа (мин)", tf_travel, "Запасной вариант, если API-маршрут недоступен."),
                            ft.Container(height = 12),
                            ft.Text("Семестр", size = 16, weight = ft.FontWeight.W_600),
                            ft.Divider(height = 1),
                            row(
                                "Начало семестра",
                                tf_semester,
                                "Можно менять вручную, но после нового импорта значение обновится из файла.",
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
                            ),
                            ft.Text(
                                "Версия: 0.1_beta",
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
