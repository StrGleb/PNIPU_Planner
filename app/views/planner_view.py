import flet as ft
import datetime
from typing import Callable
from managers.planner_manager import PlannerManager
from models.lesson_model import Lesson

# ── Константы таймлайна ────────────────────────────────────────────────────────
HOUR_HEIGHT = 80    # пикселей на 1 час
START_HOUR = 8     # таймлайн начинается в 08:00
END_HOUR = 21    # таймлайн заканчивается в 20:00 (21 — не включается)
TIME_COL_W = 52    # ширина колонки с временем

LESSON_BG = ft.Colors.GREEN_200
LESSON_BORDER = ft.Colors.GREEN_400
LESSON_TEXT = ft.Colors.GREEN_900
LESSON_TIME = ft.Colors.GREEN_800


def build_planner_view(
    navigation_bar: ft.NavigationBar,
    planner_manager: PlannerManager,
    page: ft.Page,
) -> tuple[ft.View, Callable]:
    """
    Возвращает (View, cleanup_fn).
    cleanup_fn нужно вызвать при уходе с маршрута /planner,
    чтобы убрать overlays из page.overlay.
    """

    _mounted = {"value": False}

    state = {
        "date":       datetime.date.today(),
        "week_even":  True,   # True = чётная неделя
    }

    # ── Утилиты ──────────────────────────────────────────────────────────────────

    def safe_update(*controls):
        if not _mounted["value"]:
            return
        for c in controls:
            try:
                c.update()
            except Exception:
                pass

    def mins(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    def fmt_day(d: datetime.date) -> str:
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return f"{names[d.weekday()]}  {d.strftime('%d.%m')}"

    def week_label() -> str:
        return "ЧЁТ" if state["week_even"] else "НЕЧЁТ"

    # ── Overlays ─────────────────────────────────────────────────────────────────
    # Создаём один раз, переиспользуем — обновляем content перед открытием.

    add_dialog = ft.AlertDialog(modal=True, title=ft.Text("Новая пара"))
    input_dialog = ft.AlertDialog(modal=True, title=ft.Text(""))
    detail_sheet = ft.BottomSheet(
        content=ft.Container(ft.Text(""), padding=16),
        dismissible=True,
        on_dismiss=lambda e: None,
    )

    page.overlay.extend([add_dialog, input_dialog, detail_sheet])

    def cleanup():
        for item in [add_dialog, input_dialog, detail_sheet]:
            if item in page.overlay:
                try:
                    page.overlay.remove(item)
                except Exception:
                    pass

    # ── Диалог добавления пары ───────────────────────────────────────────────────

    def open_add_dialog(e=None):
        date_f = ft.TextField(label="Дата  ДД.ММ.ГГГГ",  value=state["date"].strftime("%d.%m.%Y"))
        ts_f = ft.TextField(label="Начало  ЧЧ:ММ", width=130)
        te_f = ft.TextField(label="Конец   ЧЧ:ММ", width=130)
        subj_f = ft.TextField(label="Предмет")
        err = ft.Text("", color=ft.Colors.RED_400, size=12)

        def save(e):
            try:
                d = datetime.datetime.strptime(date_f.value.strip(), "%d.%m.%Y").date()
                ts = ts_f.value.strip()
                te = te_f.value.strip()
                datetime.datetime.strptime(ts, "%H:%M")
                datetime.datetime.strptime(te, "%H:%M")
                subj = subj_f.value.strip()
                if not subj:
                    raise ValueError("empty subject")
            except Exception:
                err.value = "Неверный формат. Дата: ДД.ММ.ГГГГ,  время: ЧЧ:ММ"
                page.update()
                return

            planner_manager.add_lesson(d, ts, te, subj)
            add_dialog.open = False
            page.update()
            if state["date"] == d:
                rebuild_timeline()

        def cancel(e):
            add_dialog.open = False
            page.update()

        add_dialog.content = ft.Column(
            [date_f, ft.Row([ts_f, ft.Text(" – "), te_f]), subj_f, err],
            tight=True, spacing=10, width=290,
        )
        add_dialog.actions = [
            ft.TextButton("Отмена",    on_click=cancel),
            ft.FilledButton("Добавить", on_click=save),
        ]
        add_dialog.open = True
        page.update()

    # ── Диалог ввода одной строки (домашняя / контрольная) ───────────────────────

    def open_input_dialog(title: str, on_save: Callable[[str], None]):
        field = ft.TextField(label=title, autofocus=True)
        err   = ft.Text("", color=ft.Colors.RED_400, size=12)

        def save(e):
            text = (field.value or "").strip()
            if not text:
                err.value = "Поле не может быть пустым"
                page.update()
                return
            input_dialog.open = False
            page.update()
            on_save(text)

        def cancel(e):
            input_dialog.open = False
            page.update()

        input_dialog.title = ft.Text(title)
        input_dialog.content = ft.Column([field, err], tight=True, spacing=8, width=280)
        input_dialog.actions = [
            ft.TextButton("Отмена",    on_click=cancel),
            ft.FilledButton("Добавить", on_click=save),
        ]
        input_dialog.open = True
        page.update()

    # ── Детальная панель пары (BottomSheet) ──────────────────────────────────────

    def open_detail(lesson: Lesson):
        # Берём актуальную версию урока из менеджера
        current = planner_manager.get_lesson(lesson.id)
        if current is None:
            return

        def close_sheet(e=None):
            detail_sheet.open = False
            page.update()

        def add_hw(e):
            open_input_dialog(
                "Домашняя работа",
                lambda text: _after_add_hw(current.id, text),
            )

        def add_tw(e):
            open_input_dialog(
                "Контрольная работа",
                lambda text: _after_add_tw(current.id, text),
            )

        def _after_add_hw(lid, text):
            planner_manager.add_homework(lid, text)
            lesson_fresh = planner_manager.get_lesson(lid)
            if lesson_fresh:
                open_detail(lesson_fresh)

        def _after_add_tw(lid, text):
            planner_manager.add_test_work(lid, text)
            lesson_fresh = planner_manager.get_lesson(lid)
            if lesson_fresh:
                open_detail(lesson_fresh)

        def delete_lesson(e):
            planner_manager.remove_lesson(current.id)
            detail_sheet.open = False
            page.update()
            rebuild_timeline()

        # Домашние работы
        if current.homeworks:
            hw_items = [ft.Text(f"• {h}", size=13) for h in current.homeworks]
        else:
            hw_items = [ft.Text("отсутствуют", size=13, color=ft.Colors.GREY_500, italic=True)]

        # Контрольные
        if current.test_works:
            tw_items = [ft.Text(f"• {t}", size=13) for t in current.test_works]
        else:
            tw_items = [ft.Text("отсутствуют", size=13, color=ft.Colors.GREY_500, italic=True)]

        detail_sheet.content = ft.Container(
            content=ft.Column(
                [
                    # Заголовок + крестик
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(ft.Icons.CLOSE, on_click=close_sheet, icon_size=20),
                    ]),
                    ft.Text(current.subject, size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{current.date_str}   {current.time_start} – {current.time_end}",
                        size=13, color=ft.Colors.GREY_600,
                    ),
                    ft.Divider(),
                    # Домашние работы
                    ft.Row([
                        ft.Text("Домашние работы:", size=14, weight=ft.FontWeight.W_600, expand=True),
                        ft.IconButton(ft.Icons.ADD, on_click=add_hw, icon_size=20),
                    ]),
                    *hw_items,
                    ft.Divider(),
                    # Контрольные
                    ft.Row([
                        ft.Text("Контрольные работы:", size=14, weight=ft.FontWeight.W_600, expand=True),
                        ft.IconButton(ft.Icons.ADD, on_click=add_tw, icon_size=20),
                    ]),
                    *tw_items,
                    ft.Divider(),
                    # Удалить
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Удалить пару",
                                bgcolor=ft.Colors.RED_400,
                                color=ft.Colors.WHITE,
                                on_click=delete_lesson,
                                expand=True,
                            )
                        ],
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=6,
            ),
            padding=16,
            height=420,
        )
        detail_sheet.open = True
        page.update()

    # ── Таймлайн ────────────────────────────────────────────────────────────────

    timeline_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)

    def _build_grid() -> ft.Column:
        total_h = (END_HOUR - START_HOUR) * HOUR_HEIGHT
        rows = []
        for i in range(END_HOUR - START_HOUR):
            hour = START_HOUR + i
            rows.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(f"{hour:02d}:00", size=11, color=ft.Colors.GREY_500),
                            width=TIME_COL_W,
                            height=HOUR_HEIGHT,
                            alignment=ft.Alignment(x=1.0, y=-1.0),
                            padding=ft.padding.only(right=8, top=2),
                        ),
                        ft.Container(
                            expand=True,
                            height=HOUR_HEIGHT,
                            border=ft.border.only(top=ft.BorderSide(0.5, ft.Colors.GREY_300)),
                        ),
                    ],
                    spacing=0,
                    height=HOUR_HEIGHT,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
        return ft.Column(rows, spacing=0, height=total_h)

    def _build_lesson_block(lesson: Lesson) -> ft.Container:
        try:
            s      = mins(lesson.time_start) - START_HOUR * 60
            e_m    = mins(lesson.time_end)   - START_HOUR * 60
            top_px = s / 60 * HOUR_HEIGHT
            h_px   = max((e_m - s) / 60 * HOUR_HEIGHT, 36)
        except Exception:
            return ft.Container()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"{lesson.time_start} – {lesson.time_end}",
                        size=11, weight=ft.FontWeight.BOLD, color=LESSON_TIME,
                    ),
                    ft.Text(
                        lesson.subject,
                        size=13, weight=ft.FontWeight.BOLD, color=LESSON_TEXT,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=2, tight=True,
            ),
            bgcolor=LESSON_BG,
            border=ft.border.all(1, LESSON_BORDER),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            top=top_px, left=TIME_COL_W + 4, right=8, height=h_px,
            on_click=lambda e, l=lesson: open_detail(l),
            ink=True,
        )

    def build_timeline_stack() -> ft.Stack:
        total_h = (END_HOUR - START_HOUR) * HOUR_HEIGHT
        blocks = [_build_grid()]
        for lesson in planner_manager.get_lessons_for_date(state["date"]):
            blocks.append(_build_lesson_block(lesson))
        return ft.Stack(blocks, height=total_h)

    def rebuild_timeline():
        date_text.value = fmt_day(state["date"])
        timeline_col.controls = [build_timeline_stack()]
        safe_update(date_text, timeline_col)

    # Первоначальное заполнение (без .update())
    timeline_col.controls = [build_timeline_stack()]

    # ── Шапка ────────────────────────────────────────────────────────────────────

    date_text = ft.Text(fmt_day(state["date"]), size=12, color=ft.Colors.GREY_600)
    week_label_ctrl = ft.Text(week_label(), size=11, weight=ft.FontWeight.BOLD)

    def toggle_week(e):
        state["week_even"] = not state["week_even"]
        week_label_ctrl.value = week_label()
        safe_update(week_label_ctrl)

    week_btn = ft.Container(
        content=week_label_ctrl,
        bgcolor=ft.Colors.GREY_200,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        on_click=toggle_week,
        ink=True,
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(
                    ft.Icons.MENU,
                    on_click=lambda e: page.show_drawer(),
                    icon_size=24,
                ),
                ft.Column(
                    [ft.Text("Календарь", size=20, weight=ft.FontWeight.BOLD), date_text],
                    spacing=0, expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                week_btn,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=4, vertical=8),
    )

    # ── Навигация по дням (стрелки) ──────────────────────────────────────────────

    def prev_day(e):
        state["date"] -= datetime.timedelta(days=1)
        rebuild_timeline()

    def next_day(e):
        state["date"] += datetime.timedelta(days=1)
        rebuild_timeline()

    nav_row = ft.Row(
        [
            ft.IconButton(ft.Icons.CHEVRON_LEFT,  on_click=prev_day,  icon_size=22),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=next_day, icon_size=22),
        ],
    )

    # ── Боковое меню (NavigationDrawer) ──────────────────────────────────────────

    def go_to_today():
        state["date"] = datetime.date.today()
        page.close_drawer()
        rebuild_timeline()

    nav_drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(
                content=ft.Row([
                    ft.Text(
                        "Студенческий календарь",
                        size=15, weight=ft.FontWeight.BOLD, expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        on_click=lambda e: page.close_drawer(),
                        icon_size=20,
                    ),
                ]),
                padding=ft.padding.only(left=16, top=12, right=8, bottom=8),
            ),
            ft.Divider(),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.VIEW_WEEK_OUTLINED),
                title=ft.Text("Неделя"),
                on_click=lambda e: page.close_drawer(),   # будет реализовано позже
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED),
                title=ft.Text("Месяц"),
                on_click=lambda e: page.close_drawer(),
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED),
                title=ft.Text("Год"),
                on_click=lambda e: page.close_drawer(),
            ),
            ft.Divider(),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.TODAY),
                title=ft.Text("Текущий день"),
                on_click=lambda e: go_to_today(),
            ),
        ],
        on_dismiss=lambda e: None,
    )

    # ── FAB ──────────────────────────────────────────────────────────────────────

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=ft.Colors.BLUE_200,
        on_click=open_add_dialog,
    )

    # ── Флаг монтирования ────────────────────────────────────────────────────────

    def on_page_updated(e):
        _mounted["value"] = True
        page.on_update = None

    page.on_update = on_page_updated

    # ── View ─────────────────────────────────────────────────────────────────────

    view = ft.View(
        route="/planner",
        drawer=nav_drawer,
        floating_action_button=fab,
        controls=[
            ft.Column(
                [header, ft.Divider(height=1, thickness=0.5), nav_row, timeline_col],
                expand=True,
                spacing=0,
            )
        ],
        navigation_bar=navigation_bar,
        padding=0,
    )

    return view, cleanup
