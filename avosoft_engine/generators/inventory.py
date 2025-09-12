# avosoft_retail/avosoft_engine/generators/inventory.py

import uuid, random
from .base import BaseGenerator

class InventoryGenerator(BaseGenerator):
    def restock_rows(self, ds: str, product_id: str, qty: int, dc_id: str, cost: float,
                     name: str, brand: str, retail: float, dept: str, category: str, sku: str):
        rows = []
        for _ in range(qty):
            rows.append({
                "id": str(uuid.uuid4()),
                "product_id": product_id,
                "created_at": f"{ds} 02:00:00",
                "sold_at": None,
                "cost": cost,
                "product_category": category,
                "product_name": name,
                "product_brand": brand,
                "product_retail_price": retail,
                "product_department": dept,
                "product_sku": sku,
                "product_distribution_center_id": dc_id
            })
        return rows
