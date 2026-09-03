import os
import time
import json
import random
import string
import hmac
import hashlib
import logging
import aiohttp
from database.queries import get_system_setting, set_system_setting

logger = logging.getLogger(__name__)

class BinancePayService:
    BASE_URL = "https://bpay.binanceapi.com"

    def __init__(self):
        self._api_key = os.getenv("BINANCE_API_KEY", "")
        self._api_secret = os.getenv("BINANCE_API_SECRET", "")
        self._pay_id = os.getenv("BINANCE_PAY_ID", "")

    async def get_credentials(self) -> tuple[str, str, str]:
        key = await get_system_setting("BINANCE_API_KEY", self._api_key)
        secret = await get_system_setting("BINANCE_API_SECRET", self._api_secret)
        pay_id = await get_system_setting("BINANCE_PAY_ID", self._pay_id)
        return key, secret, pay_id

    async def set_credentials(self, api_key: str = None, api_secret: str = None, pay_id: str = None):
        if api_key is not None:
            self._api_key = api_key
            await set_system_setting("BINANCE_API_KEY", api_key)
        if api_secret is not None:
            self._api_secret = api_secret
            await set_system_setting("BINANCE_API_SECRET", api_secret)
        if pay_id is not None:
            self._pay_id = pay_id
            await set_system_setting("BINANCE_PAY_ID", pay_id)

    @staticmethod
    def _random_nonce(length=32) -> str:
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def _generate_signature(secret: str, timestamp: int, nonce: str, body_str: str) -> str:
        payload = f"{timestamp}\n{nonce}\n{body_str}\n"
        sig = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha512).hexdigest().upper()
        return sig

    async def create_order(self, order_id: str, amount: float, currency: str = "USDT", description: str = "Store Topup") -> dict:
        """Create a Binance Pay order via Merchant OpenAPI or fallback to Pay ID instructions."""
        api_key, api_secret, pay_id = await self.get_credentials()

        if api_key and api_secret:
            timestamp = int(time.time() * 1000)
            nonce = self._random_nonce(32)
            body = {
                "env": {"terminalType": "WEB"},
                "merchantTradeNo": str(order_id),
                "orderAmount": f"{amount:.2f}",
                "currency": currency,
                "goods": {
                    "goodsType": "02",
                    "goodsCategory": "Z000",
                    "referenceGoodsId": str(order_id),
                    "goodsName": description[:50]
                }
            }
            body_str = json.dumps(body)
            sig = self._generate_signature(api_secret, timestamp, nonce, body_str)

            headers = {
                "Content-Type": "application/json",
                "BinancePay-Timestamp": str(timestamp),
                "BinancePay-Nonce": nonce,
                "BinancePay-Certificate-SN": api_key,
                "BinancePay-Signature": sig
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.BASE_URL}/binancepay/openapi/v2/order", headers=headers, data=body_str, timeout=10) as resp:
                        res = await resp.json()
                        if res.get("status") == "SUCCESS" and "data" in res:
                            d = res["data"]
                            return {
                                "success": True,
                                "type": "api",
                                "order_id": order_id,
                                "prepay_id": d.get("prepayId"),
                                "checkout_url": d.get("checkoutUrl"),
                                "deeplink": d.get("deeplink"),
                                "qrcode_url": d.get("qrcodeLink"),
                                "amount": amount,
                                "currency": currency
                            }
                        else:
                            logger.warning(f"Binance Pay API response non-success: {res}")
            except Exception as e:
                logger.error(f"Binance Pay API error: {e}")

        # Fallback to direct Pay ID transfer mode
        return {
            "success": True,
            "type": "pay_id",
            "order_id": order_id,
            "pay_id": pay_id or "Configure in /admin",
            "amount": amount,
            "currency": currency,
            "instructions": f"Send {amount:.2f} {currency} to Binance Pay ID: {pay_id or 'NOT_SET'}\nReference: {order_id}"
        }

    async def query_order(self, order_id: str) -> dict:
        """Query order status on Binance Pay OpenAPI for 100% automated credit."""
        api_key, api_secret, _ = await self.get_credentials()
        if not (api_key and api_secret):
            return {"success": False, "message": "API keys not configured"}

        timestamp = int(time.time() * 1000)
        nonce = self._random_nonce(32)
        body = {"merchantTradeNo": str(order_id)}
        body_str = json.dumps(body)
        sig = self._generate_signature(api_secret, timestamp, nonce, body_str)

        headers = {
            "Content-Type": "application/json",
            "BinancePay-Timestamp": str(timestamp),
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-SN": api_key,
            "BinancePay-Signature": sig
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.BASE_URL}/binancepay/openapi/v2/order/query", headers=headers, data=body_str, timeout=10) as resp:
                    res = await resp.json()
                    if res.get("status") == "SUCCESS" and "data" in res:
                        d = res["data"]
                        return {
                            "success": True,
                            "status": d.get("status"),  # PAID, INITIAL, EXPIRED
                            "amount": float(d.get("orderAmount", 0)),
                            "currency": d.get("currency", "USDT"),
                            "raw": d
                        }
                    return {"success": False, "message": res.get("errorMessage", str(res))}
        except Exception as e:
            return {"success": False, "message": str(e)}

binance_pay_service = BinancePayService()

