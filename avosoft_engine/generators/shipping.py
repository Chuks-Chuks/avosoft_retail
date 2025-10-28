# avosoft_engine/generators/shipping.py
import json
import random
import requests
import uuid
from datetime import datetime, timedelta
from .base import BaseGenerator

API_TIMEOUT = 6  # seconds


class APIShippingGenerator(BaseGenerator):
    def __init__(self, api_base_url="http://localhost:8000"):
        super().__init__()
        self.api_base_url = api_base_url

    def create_shipment_via_api(self, order_item: dict, user_address: dict, origin_dc_id: str | None = None):
        """
        Call the carrier API to create a shipment. If the API is down or fails, falls back to a local generator.
        """
        payload = {
            "order_id": order_item["order_id"],
            "order_item_id": order_item["id"],
            "destination": user_address,
            "origin_dc_id": origin_dc_id,
            "service_level": order_item.get("service_level", "STANDARD")
        }

        try:
            resp = requests.post(f"{self.api_base_url}/api/v1/shipments", json=payload, timeout=API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data.get("success"):
                return data["shipment"]
            else:
                # fallback
                return self._create_shipment_direct(order_item, user_address)
        except Exception as e:
            # fallback gracefully
            print(f"Shipment API failed: {e}. Falling back to local generator.")
            return self._create_shipment_direct(order_item, user_address)

    def _create_shipment_direct(self, order_item: dict, user_address: dict):
        """Local generation if API fails — mirrors DB service behaviour."""
        carrier = random.choice(["UPS", "FEDEX", "DHL", "USPS"])
        tracking_number = f"{carrier[:2].upper()}{random.randint(10**14, 10**16 - 1)}"
        now = datetime.utcnow()
        estimated_delivery = (now + timedelta(days=random.randint(2, 7))).isoformat()
        return {
            "shipment_id": str(uuid.uuid4()),
            "order_id": order_item["order_id"],
            "order_item_id": order_item["id"],
            "carrier": carrier,
            "tracking_number": tracking_number,
            "status": "label_created",
            "estimated_delivery": estimated_delivery,
            "shipping_cost": round(random.uniform(5.99, 29.99), 2)
        }
