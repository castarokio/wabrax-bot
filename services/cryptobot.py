import os
import logging
import aiohttp
from database.queries import get_system_setting, set_system_setting

logger = logging.getLogger(__name__)

class CryptoBotService:
    BASE_URL = "https://pay.crypt.bot/api"

    def __init__(self):
        self._token = os.getenv("CRYPTOBOT_TOKEN", "")

    async def get_token(self) -> str:
        return await get_system_setting("CRYPTOBOT_TOKEN", self._token)

    async def set_token(self, token: str):
        self._token = token
        await set_system_setting("CRYPTOBOT_TOKEN", token)

    async def create_invoice(self, amount: float, asset: str = "USDT", description: str = "Wallet Top-up") -> dict:
        token = await self.get_token()
        if not token:
            return {"success": False, "message": "CryptoBot token not configured"}

        headers = {"Crypto-Pay-API-Token": token}
        payload = {
            "asset": asset,
            "amount": str(amount),
            "description": description[:100],
            "paid_btn_name": "openBot",
            "paid_btn_url": "https://t.me/Hidta3zbibot"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.BASE_URL}/createInvoice", headers=headers, json=payload, timeout=10) as resp:
                    res = await resp.json()
                    if res.get("ok") and "result" in res:
                        r = res["result"]
                        return {
                            "success": True,
                            "invoice_id": r.get("invoice_id"),
                            "pay_url": r.get("bot_invoice_url") or r.get("pay_url"),
                            "amount": amount,
                            "asset": asset
                        }
                    return {"success": False, "message": res.get("description", str(res))}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def check_invoice(self, invoice_id: int) -> dict:
        token = await self.get_token()
        if not token:
            return {"success": False, "message": "CryptoBot token not configured"}

        headers = {"Crypto-Pay-API-Token": token}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/getInvoices?invoice_ids={invoice_id}", headers=headers, timeout=10) as resp:
                    res = await resp.json()
                    if res.get("ok") and "result" in res and res["result"].get("items"):
                        item = res["result"]["items"][0]
                        return {
                            "success": True,
                            "status": item.get("status"), # active, paid, expired
                            "amount": float(item.get("amount", 0)),
                            "is_paid": (item.get("status") == "paid")
                        }
                    return {"success": False, "message": "Invoice not found"}
        except Exception as e:
            return {"success": False, "message": str(e)}

cryptobot_service = CryptoBotService()
