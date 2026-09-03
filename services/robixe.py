import os
import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class RobixeClient:
    def __init__(self, token: str = None):
        self._token = token
        self.base_url = "https://seller.robixe.com"

    async def get_token(self) -> str:
        if self._token:
            return self._token
        env_token = os.getenv("ROBIXE_TOKEN", "").strip()
        if env_token:
            return env_token
        try:
            from database.queries import get_system_setting
            return await get_system_setting("robixe_token", "")
        except Exception:
            return ""

    async def set_token(self, token: str):
        self._token = token.strip()
        try:
            from database.queries import set_system_setting
            await set_system_setting("robixe_token", self._token)
        except Exception as e:
            logger.error(f"Failed to persist Robixe token: {e}")

    async def login_with_telegram_url(self, telegram_url: str) -> Optional[str]:
        """
        Authenticate with the one-time URL obtained from @Robixe_bot on Telegram.
        Returns the Bearer token.
        """
        url = f"{self.base_url}/apiii/auth/login"
        payload = {"telegram_url": telegram_url.strip()}
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=12) as resp:
                    data = await resp.json()
                    token = data.get("token")
                    if token:
                        await self.set_token(token)
                        return token
                    logger.error(f"Robixe login response without token: {data}")
            except Exception as e:
                logger.error(f"Robixe login failed: {e}")
        return None

    async def create_activation_link(self) -> Dict[str, Any]:
        """
        Generates a live 12-Month Coursera Premium client activation URL.
        """
        token = await self.get_token()
        if not token:
            return {"error": "ROBIXE_TOKEN_NOT_CONFIGURED"}

        url = f"{self.base_url}/apiii/link/create"
        headers = {
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json={}, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        err_text = await resp.text()
                        logger.error(f"Robixe create link error {resp.status}: {err_text}")
                        return {"error": f"HTTP_{resp.status}", "detail": err_text}
            except Exception as e:
                logger.error(f"Robixe link generation failed: {e}")
                return {"error": str(e)}

robixe_client = RobixeClient()
