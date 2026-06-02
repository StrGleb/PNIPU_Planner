"""
Notification manager: refreshes task ratings and sends desktop notifications.
"""

import datetime
import logging
import threading
from time import sleep
from typing import TYPE_CHECKING

try:
    from plyer import notification
except Exception:
    notification = None

if TYPE_CHECKING:
    from managers.tasks_manager import TasksManager


NOTIFICATION_THRESHOLD = 80.0
logger = logging.getLogger(__name__)


def send_notification(title: str, message: str) -> None:
    """Send a system notification through plyer when available."""
    if notification is None:
        logger.warning("Plyer is unavailable, skipping system notification")
        return
    try:
        notification.notify(
            title = title,
            message = message,
            app_name = "University Planner",
            timeout = 10,
        )
    except Exception as exc:
        logger.error("Failed to send notification: %s", exc)


def check_and_notify(tasks_manager: "TasksManager") -> None:
    """
    Refresh task ratings and notify about the most urgent tasks.

    Rating calculation, urgent filtering and sorting are delegated to the
    tasks manager, which now uses the native C++ core for bulk operations.
    """
    today = datetime.date.today()
    tasks_manager.refresh_all_ratings(today)
    urgent = tasks_manager.get_urgent_tasks(NOTIFICATION_THRESHOLD)
    if not urgent:
        return

    lines = [f"[{task.type_label}] {task.subject}: {task.text}" for task in urgent[:5]]
    send_notification(
        title = f"Important tasks ({len(urgent)})",
        message = "\n".join(lines),
    )


def start_daily_checker(tasks_manager: "TasksManager") -> None:
    """Run notification checks immediately and then every day after midnight."""

    def _loop() -> None:
        check_and_notify(tasks_manager)

        while True:
            now = datetime.datetime.now()
            next_midnight = (now + datetime.timedelta(days = 1)).replace(
                hour = 0,
                minute = 0,
                second = 5,
                microsecond = 0,
            )
            sleep_seconds = (next_midnight - now).total_seconds()
            sleep(max(sleep_seconds, 1))
            check_and_notify(tasks_manager)

    thread = threading.Thread(target = _loop, daemon = True)
    thread.start()
