import httpx

from app.core.config import get_settings
from app.core.logging import get_logger


class TelegramNotifier:
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("app.notifications.telegram")

    async def send_message(self, message: str) -> bool:
        if not self.settings.telegram_enabled:
            return False
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            self.logger.warning("Telegram notifications are enabled but bot token/chat id are missing.")
            return False

        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": message,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            return True
        except Exception as exc:  # pragma: no cover - network dependent
            self.logger.exception("Failed to send Telegram notification: %s", exc)
            return False
