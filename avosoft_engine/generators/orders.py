# avosoft_retail/avosoft_engine/generators/orders.py

import uuid, random
from .base import BaseGenerator

class OrdersGenerator(BaseGenerator):
    def generate_orders(self, ds: str, user_ids: list[str], order_count: int):
        orders = []
        for _ in range(order_count):
            uid = random.choice(user_ids)
            created = f"{ds} {str(random.randint(8,21)).zfill(2)}:{str(random.randint(0,59)).zfill(2)}:00"
            orders.append({
                "order_id": str(uuid.uuid4()),
                "user_id": uid,
                "status": "pending",
                "created_at": created,
                "gender": None,
                "num_of_items": random.randint(1, 4),
            })
        return orders

    def expand_order_items(self, orders, product_pool: list[dict]):
        pairs = []
        for o in orders:
            for _ in range(o["num_of_items"]):
                p = random.choice(product_pool)
                pairs.append((o["order_id"], o["user_id"], p))
        return pairs
