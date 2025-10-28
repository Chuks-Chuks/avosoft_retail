# avosoft_engine/services/carrier_service.py
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from avosoft_engine.io.pg_conn import get_conn


class DatabaseCarrierService:
    def __init__(self):
        self.conn = get_conn()

    def list_carriers(self) -> List[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT carrier_id, carrier_code, carrier_name, supported_countries, service_levels, is_active
                FROM avosoft_retail.carriers
                WHERE is_active = TRUE
                ORDER BY carrier_code;
            """)
            rows = cur.fetchall()
            return [
                {
                    "carrier_id": r[0],
                    "carrier_code": r[1],
                    "carrier_name": r[2],
                    "supported_countries": r[3],
                    "service_levels": r[4],
                    "is_active": r[5]
                } for r in rows
            ]

    def get_carriers_for_country(self, country: str) -> List[Dict]:
        """Return carriers that list the destination country"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT carrier_id, carrier_code, carrier_name, supported_countries, service_levels
                FROM avosoft_retail.carriers
                WHERE is_active = TRUE AND %s = ANY(supported_countries);
            """, (country,))
            rows = cur.fetchall()
            return [
                {
                    "carrier_id": r[0],
                    "carrier_code": r[1],
                    "carrier_name": r[2],
                    "supported_countries": r[3],
                    "service_levels": r[4]
                } for r in rows
            ]

    def choose_carrier(self, country: str) -> Dict:
        """Choose a carrier for a country; fall back to any active carrier."""
        candidates = self.get_carriers_for_country(country)
        if not candidates:
            candidates = self.list_carriers()
            if not candidates:
                raise RuntimeError("No carriers configured in DB.")
        # simple: weighted random or round-robin; here random.choice
        return random.choice(candidates)

    def _generate_tracking(self, carrier_code: str) -> str:
        prefixes = {
            "UPS": "1Z",
            "FEDEX": "FD",
            "DHL": "DH",
            "USPS": "US",
        }
        prefix = prefixes.get(carrier_code.upper(), "TR")
        return f"{prefix}{random.randint(10**14, 10**16 - 1)}"

    def create_shipment(self, order_id: str, order_item_id: str, destination: dict, origin_dc_id: Optional[str] = None, service_level: Optional[str] = None) -> Dict:
        """
        Create shipment record and a first shipment_event.
        Returns a dict describing the shipment.
        """
        country = destination.get("country") or destination.get("country_name") or "United States"
        carrier = self.choose_carrier(country)
        tracking_number = self._generate_tracking(carrier["carrier_code"])
        shipment_id = str(uuid.uuid4())
        now = datetime.utcnow()

        shipping_cost = round(random.uniform(5.99, 25.99), 2)
        estimated_delivery = (now + timedelta(days=random.randint(2, 7))).isoformat()

        with self.conn.cursor() as cur:
            # Insert shipment
            cur.execute("""
                INSERT INTO avosoft_retail.shipments
                (shipment_id, order_id, order_item_id, carrier, tracking_number, status,
                 created_at, shipped_at, estimated_delivery, shipping_cost, origin_address, destination_address, last_updated, carrier_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
                ON CONFLICT (tracking_number) DO NOTHING;
            """, (
                shipment_id, order_id, order_item_id, carrier["carrier_code"], tracking_number,
                "label_created", now, now, estimated_delivery, shipping_cost,
                json.dumps({}), json.dumps(destination), now, carrier["carrier_id"]
            ))

            # insert initial event
            cur.execute("""
                INSERT INTO avosoft_retail.shipment_events
                (event_id, shipment_id, carrier_code, status, description, event_time, location, raw_payload)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb);
            """, (
                shipment_id, carrier["carrier_code"], "label_created",
                "Label created", now, json.dumps({}), json.dumps({"tracking": tracking_number})
            ))

        self.conn.commit()

        return {
            "shipment_id": shipment_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
            "carrier": carrier["carrier_code"],
            "tracking_number": tracking_number,
            "status": "label_created",
            "estimated_delivery": estimated_delivery,
            "shipping_cost": shipping_cost
        }

    def get_tracking(self, tracking_number: str) -> Dict:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT shipment_id, order_id, order_item_id, carrier, tracking_number, status,
                       created_at, shipped_at, estimated_delivery, actual_delivery, shipping_cost, origin_address, destination_address
                FROM avosoft_retail.shipments
                WHERE tracking_number = %s;
            """, (tracking_number,))
            row = cur.fetchone()
            if not row:
                return {}
            return {
                "shipment_id": row[0],
                "order_id": row[1],
                "order_item_id": row[2],
                "carrier": row[3],
                "tracking_number": row[4],
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "shipped_at": row[7].isoformat() if row[7] else None,
                "estimated_delivery": row[8].isoformat() if row[8] else None,
                "actual_delivery": row[9].isoformat() if row[9] else None,
                "shipping_cost": float(row[10]) if row[10] is not None else None,
                "origin_address": row[11],
                "destination_address": row[12]
            }

    def apply_webhook_update(self, payload: dict) -> Dict:
        """
        Called by webhook receiver to update shipment by tracking number.
        Expects payload contains: tracking_number, status, description?, location?
        """
        tracking = payload.get("tracking_number")
        status = payload.get("status")
        description = payload.get("description", "")
        location = payload.get("location", {})
        event_time = payload.get("event_time", None) or datetime.utcnow()

        with self.conn.cursor() as cur:
            # log webhook
            cur.execute("""
                INSERT INTO avosoft_retail.webhook_logs (event_source, payload)
                VALUES (%s, %s::jsonb)
            """, ("carrier_webhook", json.dumps(payload)))

            # Update shipments
            cur.execute("""
                UPDATE avosoft_retail.shipments
                SET status = %s,
                    last_updated = NOW(),
                    actual_delivery = CASE WHEN %s = 'delivered' THEN NOW() ELSE actual_delivery END
                WHERE tracking_number = %s
                RETURNING shipment_id, order_id, order_item_id, carrier;
            """, (status, status, tracking))

            row = cur.fetchone()
            shipment_id = row[0] if row else None

            if shipment_id:
                # add event
                cur.execute("""
                    INSERT INTO avosoft_retail.shipment_events
                    (event_id, shipment_id, carrier_code, status, description, event_time, location, raw_payload)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                """, (shipment_id, row[3], status, description, event_time, json.dumps(location), json.dumps(payload)))

        self.conn.commit()
        return {"ok": True, "updated_tracking": tracking}

