"""
Менеджер уведомлений: расчёт рейтинга задач и отправка push-уведомлений.
"""
import datetime
import threading
from time import sleep
from typing import TYPE_CHECKING
from plyer import notification

if TYPE_CHECKING:
    from managers.tasks_manager import TasksManager

# Порог рейтинга, при превышении которого отправляется уведомление
NOTIFICATION_THRESHOLD = 80.0


# ── Алгоритм рейтинга ─────────────────────────────────────────────────────────
def calculate_task_rating(task, today: datetime.date) -> float:
    """
    Рейтинг задачи — число от 0 до ~210.
    Чем выше, тем «важнее» задача прямо сейчас.

    Формула:
        priority_score = priority * 30 → 0 / 30 / 60 / 90
        urgency_score:
            просрочено → 150
            сегодня (0 дней) → 120
            ≤ 14 дней → (1 - days/14) * 100
            > 14 дней → 0
        rating = priority_score + urgency_score

    Примеры работы:
        priority = 0, 15+ дней → 0 (нет уведомления)
        priority = 1, 7 дней → 80 (граница, уведомление)
        priority = 3, любой срок → 90+ (всегда уведомление)
        priority = 3, сегодня → 210 (критично)

    """
    try:
        task_date = datetime.datetime.strptime(task.date_str, "%d.%m.%Y").date()
    except Exception:
        return 0.0

    priority_score = task.priority * 30

    days_until = (task_date - today).days
    if days_until < 0:
        urgency_score = 150.0 # просрочено
    elif days_until == 0:
        urgency_score = 120.0 # сегодня
    elif days_until <= 14:
        urgency_score = (1.0 - days_until / 14.0) * 100.0
    else:
        urgency_score = 0.0

    return priority_score + urgency_score

# ── МАТЕМАТИЧЕСКОЕ ЯДРО АЛГОРИТМА РАСЧЁТА РЕЙТИНГА  (Будущий C++) ─────────────────────────────────
def compute_rating_value(priority: int, days_until: int) -> float:
    """
    Эта функция НЕ ЗНАЕТ о существовании объектов Task.
    Она принимает только числа. В будущем мы просто заменим её вызов 
    на вызов модуля core_logic.calculate_rating(priority, days_until)
    (логика для перехода на C++)

    БУДЕТ ПЕРЕПИСАНО НА C++
    """
    priority_score = priority * 30.0
    
    if days_until < 0:
        urgency_score = 150.0  # просрочено
    elif days_until == 0:
        urgency_score = 120.0  # сегодня
    elif days_until <= 14:
        urgency_score = (1.0 - days_until / 14.0) * 100.0
    else:
        urgency_score = 0.0

    return priority_score + urgency_score

# ── АДАПТЕР (Останется в Python) ────────────────────────────────────
def calculate_task_rating(task, today: datetime.date) -> float:
    """
    Адаптер: берет объект, достает из него данные, считает дни,
    и передает их в «ядро»
    (Логика для перехода от пользовательских данных в Python к простым типам данных, читаемывх C++)
    """
    try:
        task_date = datetime.datetime.strptime(task.date_str, "%d.%m.%Y").date()
    except Exception:
        return 0.0

    days_until = (task_date - today).days
    
    # Вызов будущего C++ модуля
    return compute_rating_value(task.priority, days_until)

# ── Отправка уведомления ──────────────────────────────────────────────────────
def send_notification(title: str, message: str) -> None:
    """
    Отправляет системное push-уведомление через plyer.

    Временная реализация через plyer, может не поддерживаться на Android
    """
    try:
        notification.notify(
            title    = title,
            message  = message,
            app_name = "PNIPU Planner",
            timeout  = 10,
        )
    except Exception:
        pass


# ── Основная проверка ─────────────────────────────────────────────────────────
def check_and_notify(tasks_manager: "TasksManager") -> None:
    """
    Логика управления: берет менеджер, итерируется по задачам,
    дергает вычисления и отправляет уведомления.
    БУДЕТ ПЕРЕПИСАНО НА C++
    """
    today = datetime.date.today()
    all_tasks = tasks_manager.get_all_tasks()

    # Пересчёт рейтингов
    for task in all_tasks:
        rating = calculate_task_rating(task, today)
        tasks_manager.update_rating(task.id, rating)

    # Отбор задач с высоким рейтингом
    urgent = [
        t for t in tasks_manager.get_all_tasks()
        if t.rating >= NOTIFICATION_THRESHOLD
    ]
    if not urgent:
        return

    urgent.sort(key=lambda t: t.rating, reverse=True)

    lines = [
        f"[{t.type_label}] {t.subject}: {t.text}"
        for t in urgent[:5]
    ]
    send_notification(
        title   = f"⚠ Важные задачи ({len(urgent)} шт.)",
        message = "\n".join(lines),
    )


# ── Фоновый поток: проверка в 00:00 каждый день ──────────────────────────────
def start_daily_checker(tasks_manager: "TasksManager") -> None:
    """
    Запускает check_and_notify сразу при старте,
    затем повторяет каждый день в 00:00.
    """
    def _loop():
        # Первый запуск — сразу при старте приложения
        check_and_notify(tasks_manager)

        while True:
            now          = datetime.datetime.now()
            next_midnight = (now + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=5, microsecond=0
            )
            sleep_secs = (next_midnight - now).total_seconds()
            sleep(max(sleep_secs, 1))
            check_and_notify(tasks_manager)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()