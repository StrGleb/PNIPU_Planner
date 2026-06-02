import json
import logging
import pathlib
import sys
import tempfile
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any


logger = logging.getLogger(__name__)


def _storage_path() -> pathlib.Path:
    if hasattr(sys, "getandroidapilevel"):
        cache_dir = pathlib.Path(tempfile.gettempdir())
        base_dir = cache_dir.parent / "files"
        storage_dir = base_dir / ".pnipu_planner"
    else:
        storage_dir = pathlib.Path.home() / ".pnipu_planner"

    storage_dir.mkdir(parents = True, exist_ok = True)
    return storage_dir / "auto_alarm_queue.json"


class AutoAlarmBridgeManager:
    def __init__(self, page, bridge_service = None, enabled: bool = False) -> None:
        self._page = page
        self._bridge_service = bridge_service
        self._enabled = enabled
        self._path = _storage_path()
        self._exact_alarm_available: bool | None = None

    @property
    def is_android_bridge_enabled(self) -> bool:
        return self._enabled and self._bridge_service is not None

    @property
    def use_system_schedule(self) -> bool:
        # Временная заглушка: системное расписание через Android AlarmManager
        # отключено, пока не будет утверждена финальная схема интеграции.
        return False

    def _load_payload(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"version": 1, "generated_at": 0, "alarms": []}

        try:
            with open(self._path, encoding = "utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                alarms = data.get("alarms", [])
                return {
                    "version": int(data.get("version", 1)),
                    "generated_at": int(data.get("generated_at", 0)),
                    "alarms": alarms if isinstance(alarms, list) else [],
                }
        except Exception:
            logger.exception("Не удалось загрузить локальную очередь авто-будильников")

        return {"version": 1, "generated_at": 0, "alarms": []}

    def _save_payload(self, payload: dict[str, Any]) -> None:
        normalized = {
            "version": int(payload.get("version", 1)),
            "generated_at": int(payload.get("generated_at", 0)),
            "alarms": self._sorted_alarm_payloads(payload.get("alarms", [])),
        }
        with open(self._path, "w", encoding = "utf-8") as handle:
            json.dump(normalized, handle, ensure_ascii = False, indent = 2)

    @staticmethod
    def _sorted_alarm_payloads(items: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []

        normalized_items = [item for item in items if isinstance(item, dict)]
        return sorted(
            normalized_items,
            key = lambda item: int(item.get("alarm_timestamp", 0) or 0),
        )

    def _run_service_call(
        self,
        method,
        *args,
        wait: bool = True,
        timeout: float = 15.0,
        default = None,
    ):
        if not self.is_android_bridge_enabled:
            return default

        try:
            future = self._page.run_task(method, *args)
            if not wait:
                return future
            return future.result(timeout = timeout)
        except FutureTimeoutError:
            logger.warning("Таймаут при вызове Android alarm bridge")
        except Exception:
            logger.exception("Ошибка при вызове Android alarm bridge")
        return default

    def get_queue_payload(self, prune_expired: bool = False, now_timestamp: int | None = None) -> dict[str, Any]:
        payload = self._load_payload()
        if not prune_expired:
            return payload
        return self.prune_expired(now_timestamp = now_timestamp)

    def prune_expired(self, now_timestamp: int | None = None) -> dict[str, Any]:
        payload = self._load_payload()
        cutoff = int(now_timestamp or 0)
        if cutoff <= 0:
            return payload

        payload["alarms"] = [
            item
            for item in self._sorted_alarm_payloads(payload.get("alarms", []))
            if int(item.get("alarm_timestamp", 0) or 0) > cutoff
        ]
        self._save_payload(payload)
        return payload

    def replace_first_alarm(self, item: dict[str, Any] | None) -> dict[str, Any]:
        payload = self._load_payload()
        alarms = self._sorted_alarm_payloads(payload.get("alarms", []))
        if alarms:
            alarms = alarms[1:]
        if item:
            alarms.insert(0, item)
        payload["alarms"] = self._sorted_alarm_payloads(alarms)
        self._save_payload(payload)
        if self.use_system_schedule:
            self._run_service_call(self._bridge_service.schedule_weekly_queue, payload, default = False)
        return payload

    def pop_due_alarm(self, now_timestamp: int) -> dict[str, Any]:
        payload = self._load_payload()
        payload["alarms"] = [
            item
            for item in self._sorted_alarm_payloads(payload.get("alarms", []))
            if int(item.get("alarm_timestamp", 0) or 0) > int(now_timestamp)
        ]
        self._save_payload(payload)
        if self.use_system_schedule:
            self._run_service_call(self._bridge_service.schedule_weekly_queue, payload, default = False)
        return payload

    def schedule_weekly_queue(self, payload: dict[str, Any]) -> bool:
        self._save_payload(payload)
        if not self.use_system_schedule:
            return True
        return bool(
            self._run_service_call(
                self._bridge_service.schedule_weekly_queue,
                payload,
                default = False,
            )
        )

    def cancel_auto_alarms(self) -> None:
        self._save_payload({"version": 1, "generated_at": 0, "alarms": []})
        if self.use_system_schedule:
            self._run_service_call(self._bridge_service.cancel_auto_alarms, default = False)

    def restore_after_boot(self) -> bool:
        payload = self._load_payload()
        if not payload.get("alarms"):
            if self.use_system_schedule:
                self._run_service_call(self._bridge_service.cancel_auto_alarms, default = False)
            return True

        if not self.use_system_schedule:
            return True

        return bool(self._run_service_call(self._bridge_service.restore_after_boot, default = False))

    def can_schedule_exact_alarms(self, refresh: bool = False) -> bool:
        if not self.is_android_bridge_enabled:
            return True

        if self._exact_alarm_available is not None and not refresh:
            return self._exact_alarm_available

        result = bool(
            self._run_service_call(
                self._bridge_service.can_schedule_exact_alarms,
                default = False,
            )
        )
        self._exact_alarm_available = result
        return result

    def open_exact_alarm_settings(self) -> bool:
        if not self.is_android_bridge_enabled:
            return True

        opened = bool(
            self._run_service_call(
                self._bridge_service.open_exact_alarm_settings,
                default = False,
            )
        )
        self._exact_alarm_available = None
        self.can_schedule_exact_alarms(refresh = True)
        return opened
