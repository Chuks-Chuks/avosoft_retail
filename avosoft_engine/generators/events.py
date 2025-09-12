# avosoft_retail/avosoft_engine/generators/events.py

import uuid, random
from .base import BaseGenerator, fake

# Browsing + commerce signals (added return_event, refund_event potential)
EVENTS = [
    "page_view","search","click","add_to_cart",
    "checkout_start","wishlist_add","login","logout",
]
DEVICES = ["desktop","mobile","tablet"]

class EventsGenerator(BaseGenerator):
    def generate_browsing(self, ds: str, user_ids: list[str], n: int):
        rows = []
        for _ in range(n):
            uid = random.choice(user_ids)
            rows.append({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "sequence_number": random.randint(1, 10_000),
                "session_id": str(uuid.uuid4())[:8],
                "created_at": f"{ds} {str(random.randint(7,23)).zfill(2)}:{str(random.randint(0,59)).zfill(2)}:00",
                "ip_address": fake.ipv4(),
                "city": fake.city(),
                "state": fake.state(),
                "postal_code": fake.postcode(),
                "browser": fake.user_agent(),
                "traffic_source": random.choice(['google','facebook','twitter','instagram','linkedin','email','direct','referral']),
                "uri": fake.uri(),
                "event_type": random.choice(EVENTS),
                "device_type": random.choice(DEVICES)
            })
        return rows

    def purchase_events(self, ds: str, order_rows: list[dict]):
        # purchase device randomized per your note
        out = []
        for o in order_rows:
            out.append({
                "id": str(uuid.uuid4()),
                "user_id": o["user_id"],
                "sequence_number": 1,
                "session_id": str(uuid.uuid4())[:8],
                "created_at": o["created_at"],
                "ip_address": None,
                "city": None,
                "state": None,
                "postal_code": None,
                "browser": None,
                "traffic_source": "direct",
                "uri": "/purchase",
                "event_type": "purchase",
                "device_type": random.choice(DEVICES)
            })
        return out

    def return_events(self, ds: str, returned_order_items: list[dict]):
        # track returns against specific items/orders
        out = []
        for it in returned_order_items:
            out.append({
                "id": str(uuid.uuid4()),
                "user_id": it["user_id"],
                "sequence_number": 1,
                "session_id": str(uuid.uuid4())[:8],
                "created_at": ds + " 18:00:00",
                "ip_address": None,
                "city": None,
                "state": None,
                "postal_code": None,
                "browser": None,
                "traffic_source": "direct",
                "uri": "/return",
                "event_type": "return_event",
                "device_type": random.choice(DEVICES)
            })
        return out
