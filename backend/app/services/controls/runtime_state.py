from datetime import UTC, datetime


class RuntimeControlState:
    def __init__(self):
        self._kill_switch_enabled = False
        self._kill_switch_reason = ""
        self._updated_at: str | None = None

    def get_kill_switch_status(self) -> dict:
        return {
            "enabled": self._kill_switch_enabled,
            "reason": self._kill_switch_reason,
            "updated_at": self._updated_at,
        }

    def enable_kill_switch(self, reason: str) -> dict:
        self._kill_switch_enabled = True
        self._kill_switch_reason = reason.strip() or "Emergency stop triggered manually."
        self._updated_at = datetime.now(tz=UTC).isoformat()
        return self.get_kill_switch_status()

    def disable_kill_switch(self) -> dict:
        self._kill_switch_enabled = False
        self._kill_switch_reason = ""
        self._updated_at = datetime.now(tz=UTC).isoformat()
        return self.get_kill_switch_status()


runtime_control_state = RuntimeControlState()
