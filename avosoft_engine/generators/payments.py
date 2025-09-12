
# avosoft_retail/avosoft_engine/generators/payments.py
import uuid
import random
from ..config import SETTINGS

class PaymentsGenerator:
    """
    Generates payment records for orders.
    Encapsulates payment rules (success rate, refunds, providers).
    """

    def __init__(self):
        self.providers = ["StripeLike", "PayPalLike", "SquareLike", "AdyenLike"]

    def generate(self, ds: str, orders: list[dict], totals_by_order: dict, returns_by_order: dict) -> list[dict]:
        """
        Generate payment events for given orders.
        - ds: date string
        - orders: list of orders
        - totals_by_order: {order_id -> realized_total}
        - returns_by_order: {order_id -> refund_total}
        """
        payments = []
        for o in orders:
            oid = o["order_id"]
            realized_total = float(totals_by_order.get(oid, 0.0))

            if realized_total <= 0:
                status = "failed"
                amount = 0.0
                refund_amt = 0.0
            else:
                status = "success" if random.random() < SETTINGS.payment_success_rate else "failed"
                amount = realized_total if status == "success" else 0.0
                refund_amt = min(amount, float(returns_by_order.get(oid, 0.0))) if status == "success" else 0.0

            payments.append({
                "payment_id": str(uuid.uuid4()),
                "order_id": oid,
                "payment_date": ds,
                "status": status,
                "amount": round(amount, 2),
                "refund_amount": round(refund_amt, 2),
                "provider": random.choice(self.providers),
            })

        return payments
