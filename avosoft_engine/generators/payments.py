# avosoft/avosoft_data_engine/generators/payments.py
import uuid, random
from .base import BaseGenerator

STATUSES = ["success", "failed"]

class PaymentGenerator(BaseGenerator):
    def generate(self, ds: str | None, orders: list[dict]):
        payments = []
        ds = self.within_day(ds, orders[0]["order_date"] if orders else None)
        for o in orders:
            status = random.choices(STATUSES, weights=[0.93, 0.07])[0]
            amount = o["order_total"] if status == "success" else 0.0
            refund = 0.0
            if status == "success" and random.random() < 0.03:
                refund = round(amount * random.choice([0.25, 0.5, 1.0]), 2)
            payments.append({
                "payment_id": str(uuid.uuid4()),
                "order_id": o["order_id"],
                "payment_date": ds,
                "status": status,
                "amount": round(amount, 2),
                "refund_amount": refund,
                "provider": random.choice(["StripeLike", "PayPalLike"])
            })
        return payments
