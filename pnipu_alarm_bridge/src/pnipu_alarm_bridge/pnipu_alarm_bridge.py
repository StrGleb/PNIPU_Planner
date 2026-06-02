import flet as ft


@ft.control("PnipuAlarmBridge")
class PnipuAlarmBridge(ft.Service):
    async def schedule_weekly_queue(self, payload: dict) -> bool:
        return await self._invoke_method("schedule_weekly_queue", payload)

    async def cancel_auto_alarms(self) -> bool:
        return await self._invoke_method("cancel_auto_alarms")

    async def can_schedule_exact_alarms(self) -> bool:
        return await self._invoke_method("can_schedule_exact_alarms")

    async def open_exact_alarm_settings(self) -> bool:
        return await self._invoke_method("open_exact_alarm_settings")

    async def restore_after_boot(self) -> bool:
        return await self._invoke_method("restore_after_boot")
