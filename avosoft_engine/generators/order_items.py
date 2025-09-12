# avosoft_retail/avosoft_engine/generators/order_items.py

import uuid, random
from datetime import datetime, timedelta
from .base import BaseGenerator

class OrderItemGenerator(BaseGenerator):
    def _maybe_timestamp(self, base_iso: str, min_hours: int, max_hours: int, probability: float) -> str | None:
        """Utility to randomly add timestamps for shipped/delivered events."""
        if random.random() > probability:
            return None
        base = datetime.fromisoformat(base_iso)
        bump = timedelta(hours=random.randint(min_hours, max_hours))
        return (base + bump).strftime("%Y-%m-%d %H:%M:%S")

    def generate_items(self, ds: str, order_id: str, user_id: str, product_rows: list, qty: int):
        """
        Generate order_items aligned with schema.
        Takes product rows (inventory entries) and consumes them.
        """
        items = []
        for _ in range(qty):
            if not product_rows:
                break  # no stock left

            product = product_rows.pop()  # take one inventory unit
            created_at = f"{ds} 12:00:00"

            # probabilistic shipping/delivery/return
            shipped_at = self._maybe_timestamp(created_at, 2, 48, 0.85)
            delivered_at = self._maybe_timestamp(shipped_at, 24, 96, 0.92) if shipped_at else None
            returned_at = None
            if delivered_at and random.random() < 0.05:  # 5% return rate
                returned_dt = datetime.fromisoformat(delivered_at) + timedelta(days=random.randint(1, 30))
                returned_at = returned_dt.strftime("%Y-%m-%d 18:00:00")

            status = (
                "returned" if returned_at else
                ("delivered" if delivered_at else
                 ("shipped" if shipped_at else "pending"))
            )

            items.append({
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "user_id": user_id,
                "product_id": product["product_id"],
                "inventory_item_id": product["id"],
                "status": status,
                "created_at": created_at,
                "shipped_at": shipped_at,
                "delivered_at": delivered_at,
                "returned_at": returned_at,
                "sale_price": float(product["product_retail_price"]),
            })

        return items
