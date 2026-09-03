import os
import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VENTEBOT_BASE_URL = os.getenv("VENTEBOT_BASE_URL", "https://ventetelegrambotrailway-production.up.railway.app")

class VenteBotClient:
    def __init__(self, api_key: str = None, base_url: str = None):
        self._api_key = api_key
        self.base_url = (base_url or VENTEBOT_BASE_URL).rstrip("/")

    async def get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        env_key = os.getenv("VENTEBOT_API_KEY", "").strip()
        if env_key:
            return env_key
        try:
            from database.queries import get_system_setting
            return await get_system_setting("ventebot_api_key", "")
        except Exception:
            return ""

    async def set_api_key(self, key: str):
        self._api_key = key.strip()
        try:
            from database.queries import set_system_setting
            await set_system_setting("ventebot_api_key", self._api_key)
        except Exception as e:
            logger.error(f"Failed to persist VenteBot API key: {e}")

    async def _headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        api_key = await self.get_api_key()
        if api_key:
            headers["X-Reseller-Key"] = api_key
            headers["X-API-Key"] = api_key
        return headers

    async def get_me(self) -> Dict[str, Any]:
        """Check authentication and wallet balance on VenteBot."""
        url = f"{self.base_url}/api/reseller/me"
        headers = await self._headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=12) as resp:
                    return await resp.json()
            except Exception as e:
                logger.error(f"VenteBot get_me failed: {e}")
                return {"success": False, "error": str(e)}

    async def get_products(self) -> Dict[str, Any]:
        """List all active products in VenteBot catalog."""
        url = f"{self.base_url}/api/reseller/products"
        headers = await self._headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=12) as resp:
                    return await resp.json()
            except Exception as e:
                logger.error(f"VenteBot get_products failed: {e}")
                return {"success": False, "error": str(e)}

    async def get_quote(self, product_id: int, quantity: int = 1) -> Dict[str, Any]:
        """Get quote before buying."""
        url = f"{self.base_url}/api/reseller/quote"
        headers = await self._headers()
        payload = {"product_id": product_id, "quantity": quantity}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload, timeout=12) as resp:
                    return await resp.json()
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def create_order(
        self,
        product_id: int,
        quantity: int = 1,
        customer_reference: str = "",
        activation_identifier: str = None,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        """
        Create an order on VenteBot. Debits reseller wallet and delivers accounts/keys.
        """
        url = f"{self.base_url}/api/reseller/orders"
        headers = await self._headers()
        payload = {
            "product_id": product_id,
            "quantity": quantity,
            "customer_reference": customer_reference,
            "idempotency_key": idempotency_key or f"ord_{product_id}_{os.urandom(6).hex()}"
        }
        if activation_identifier:
            payload["activation_identifier"] = activation_identifier

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload, timeout=18) as resp:
                    return await resp.json()
            except Exception as e:
                logger.error(f"VenteBot create_order failed: {e}")
                return {"success": False, "error": str(e)}

    async def get_order(self, order_id: int) -> Dict[str, Any]:
        """Get order status and delivered credentials."""
        url = f"{self.base_url}/api/reseller/orders/{order_id}"
        headers = await self._headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=12) as resp:
                    return await resp.json()
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def sync_catalog_to_database(self) -> Dict[str, Any]:
        """
        Fetches live products from VenteBot Reseller API and syncs them into our local SQLite catalog.
        """
        api_key = await self.get_api_key()
        if not api_key:
            return {"success": False, "code": "MISSING_KEY", "message": "VenteBot API key is not set. Use /set_ventebot_key <KEY>"}

        data = await self.get_products()
        if not data:
            return {"success": False, "message": "Empty response from VenteBot"}

        if isinstance(data, dict) and not data.get("success", True):
            return {"success": False, "code": data.get("code"), "message": data.get("message", "API Error")}

        items = data if isinstance(data, list) else data.get("products", [])
        if not items:
            return {"success": False, "message": "No products returned in catalog"}

        from database.db import get_db
        synced = 0
        async with get_db() as db:
            for p in items:
                pid = p.get("id")
                name = p.get("name")
                desc = p.get("description", "")
                price = float(p.get("price_usd", 0.0))
                warr = int(p.get("warranty_days", 30))
                stock = int(p.get("stock") or 10)
                img = p.get("image_url") or "static/banners/gemini_18m.jpg"

                await db.execute("""
                    INSERT INTO products (id, category_id, name, description, price, warranty_days, is_active, image_url)
                    VALUES (?, 1, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        description = excluded.description,
                        price = excluded.price,
                        warranty_days = excluded.warranty_days,
                        is_active = 1,
                        image_url = excluded.image_url
                """, (pid, name, desc, price, warr, img))

                cur = await db.execute("SELECT COUNT(*) FROM stock_items WHERE product_id = ? AND is_sold = 0", (pid,))
                cur_stock = (await cur.fetchone())[0]
                if cur_stock < stock:
                    for i in range(stock - cur_stock):
                        await db.execute("""
                            INSERT INTO stock_items (product_id, content, is_sold)
                            VALUES (?, ?, 0)
                        """, (pid, f"ventebot_live_item_{pid}_{i+1}"))

                synced += 1
            await db.commit()

        return {"success": True, "count": synced}

ventebot_client = VenteBotClient()

