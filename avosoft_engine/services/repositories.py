# avosoft_engine/services/repositories.py
import uuid
import time
from typing import Iterable, Mapping, List, Dict, Any
from psycopg2.extras import execute_values
from ..config import SETTINGS
from ..io.pg_writer import PostgresWriter
from ..io.pg_conn import get_conn
import psycopg2
import json
from datetime import datetime

class Repo:
    """Read-only helpers for the generator with connection resilience"""
    
    def __init__(self):
        self.db = PostgresWriter()
        self.max_retries = 3
        self.retry_delay = 2
        self.schema = SETTINGS.db_schema # Fetch schema field here

    def _query_with_retry(self, sql: str, params=None):
        for attempt in range(self.max_retries):
            try:
                with self.db.conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    try:
                        rows = cur.fetchall()
                    except Exception:
                        rows = []
                    return rows
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < self.max_retries - 1:
                    print(f"Query failed, retrying {attempt + 1}/{self.max_retries}: {e}")
                    time.sleep(self.retry_delay)
                    self.db.conn = get_conn()  # Reconnect
                else:
                    raise

    def users_id_list(self) -> List[str]:
        rows = self._query_with_retry(f"SELECT id FROM {self.schema}.users;")
        return [r[0] if isinstance(r, tuple) else r["id"] for r in rows]

    # Added the user_address_map to fetch customer's address.
    def user_addresses_map(self) -> Dict[str, dict]:
        rows = self._query_with_retry(f"""
            SELECT id, street_address, city, state, postal_code, country, latitude, longitude
            FROM {self.schema}.users;
        """)
        out: Dict[str, dict] = {}
        for r in rows:
            if isinstance(r, tuple):
                out[r[0]] = {
                    "street_address": r[1], "city": r[2], "state": r[3],
                    "postal_code": r[4], "country": r[5], "latitude": r[6], "longitude": r[7]
                }
            else:
                out[r["id"]] = {
                    "street_address": r["street_address"], "city": r["city"], "state": r["state"],
                    "postal_code": r["postal_code"], "country": r["country"], "latitude": r["latitude"], "longitude": r["longitude"]
                }
        return out

    def products_pool_dict(self) -> Dict[str, dict]:
        rows = self._query_with_retry(f"""
            SELECT product_id, name, brand, department, category, sku, cost, retail_price, subcategory
            FROM {self.schema}.products;
        """)
        out: Dict[str, dict] = {}
        for r in rows:
            if isinstance(r, tuple):
                out[r[0]] = {
                    "product_id": r[0], "name": r[1], "brand": r[2], "department": r[3],
                    "category": r[4], "sku": r[5], "cost": r[6], "retail_price": r[7], "subcategory": r[8]
                }
            else:
                out[r["product_id"]] = r
        return out

    def dc_ids(self) -> List[str]:
        rows = self._query_with_retry(f"SELECT id FROM {self.schema}.distribution_centers;")
        return [r[0] if isinstance(r, tuple) else r["id"] for r in rows]

    def unsold_inventory_by_product_map(self) -> Dict[str, List[str]]:
        rows = self._query_with_retry(f"""
            SELECT id, product_id
            FROM {self.schema}.inventory_items
            WHERE sold_at IS NULL
            ORDER BY created_at;
        """)
        out: Dict[str, List[str]] = {}
        for r in rows:
            inv_id, pid = (r[0], r[1]) if isinstance(r, tuple) else (r["id"], r["product_id"])
            out.setdefault(pid, []).append(inv_id)
        return out

    def low_stock_product_ids(self, threshold: int) -> List[str]:
        rows = self._query_with_retry(f"""
            WITH c AS (
              SELECT product_id, count(*) as unsold
              FROM {self.schema}.inventory_items
              WHERE sold_at IS NULL
              GROUP BY 1
            )
            SELECT product_id FROM c WHERE unsold < %s;
        """, (threshold,))
        return [r[0] if isinstance(r, tuple) else r["product_id"] for r in rows]


class InventoryRepository:
    """Write helpers with connection resilience and batch processing"""
    
    def __init__(self):
        self.conn = get_conn()
        self.max_retries = 3
        self.retry_delay = 2
        self.batch_size = 1000
        self.schema = SETTINGS.db_schema

    def ensure_commit(self):
        """Ensure all previous operations are committed"""
        self.conn.commit()

    def _execute_with_retry(self, operation, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < self.max_retries - 1:
                    print(f"Operation failed, retrying {attempt + 1}/{self.max_retries}: {e}")
                    time.sleep(self.retry_delay)
                    self.conn = get_conn()  # Reconnect
                else:
                    raise

    def _chunked_execute(self, cur, sql, values, page_size=1000):
        """Execute in chunks to avoid timeouts"""
        for i in range(0, len(values), page_size):
            chunk = values[i:i + page_size]
            execute_values(cur, sql, chunk, page_size=len(chunk))

    def reserve_stock(self, product_id: str, qty: int) -> List[Dict[str, Any]]:
        def _reserve():
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT id, product_id, cost, product_retail_price
                    FROM {self.schema}.inventory_items
                    WHERE product_id = %s::uuid AND sold_at IS NULL
                    LIMIT %s FOR UPDATE SKIP LOCKED;
                """, (product_id, qty))
                rows = cur.fetchall()
                if not rows:
                    return []

                inv_ids = [r[0] for r in rows]
                cur.execute(f"""
                    UPDATE {self.schema}.inventory_items
                    SET sold_at = NOW()
                    WHERE id = ANY(%s::uuid[]);
                """, (inv_ids,))
                self.conn.commit()

                return [
                    {"id": r[0], "product_id": r[1], "cost": r[2], "product_retail_price": r[3]}
                    for r in rows
                ]
        
        return self._execute_with_retry(_reserve)

    def insert_products(self, products: Iterable[Mapping]):
        products = list(products)
        if not products:
            return
        
        def _insert():
            cols = ["product_id","cost","category","name","retail_price","department","sku","subcategory"]
            vals = [tuple(p.get(c) for c in cols) for p in products]
            
            with self.conn.cursor() as cur:
                sql = f"""
                    INSERT INTO {self.schema}.products ({','.join(cols)}) 
                    VALUES %s 
                    ON CONFLICT (sku) DO UPDATE SET
                        cost = EXCLUDED.cost,
                        category = EXCLUDED.category,
                        name = EXCLUDED.name,
                        retail_price = EXCLUDED.retail_price,
                        department = EXCLUDED.department,
                        subcategory = EXCLUDED.subcategory
                """
                self._chunked_execute(cur, sql, vals, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)

    def insert_distribution_centers(self, dcs: Iterable[Mapping]):
        dcs = list(dcs)
        if not dcs:
            return
        
        def _insert():
            cols = ["id","name","latitude","longitude"]
            vals = [tuple(d.get(c) for c in cols) for d in dcs]
            
            with self.conn.cursor() as cur:
                sql = f"INSERT INTO {self.schema}.distribution_centers ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING"
                self._chunked_execute(cur, sql, vals, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)

    def insert_inventory_rows(self, rows: Iterable[Mapping]):
        rows = list(rows)
        if not rows:
            return
        
        def _insert():
            cols = ["id","product_id","created_at","sold_at","cost","product_category",
                    "product_name","product_brand","product_retail_price","product_department",
                    "product_sku","product_distribution_center_id"]
            vals = [tuple(r.get(col) for col in cols) for r in rows]
            
            with self.conn.cursor() as cur:
                sql = f"INSERT INTO {self.schema}.inventory_items ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING"
                self._chunked_execute(cur, sql, vals, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)

    def insert_orders(self, orders: Iterable[Mapping]):
        orders = list(orders)
        if not orders:
            return
        
        def _insert():
            cols = ["order_id","user_id","status","gender","created_at","num_of_items"]
            vals = [ (o["order_id"], o["user_id"], o.get("status","pending"), o.get("gender"), o["created_at"], o["num_of_items"]) for o in orders ]
            
            with self.conn.cursor() as cur:
                sql = f"INSERT INTO {self.schema}.orders ({','.join(cols)}) VALUES %s ON CONFLICT (order_id) DO NOTHING"
                self._chunked_execute(cur, sql, vals, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)

    def insert_order_items(self, items: Iterable[Mapping]):
        items = list(items)
        if not items:
            return
        
        def _insert():
            if isinstance(items[0], tuple):
                vals = items
            else:
                cols = ["id","order_id","user_id","product_id","inventory_item_id","status",
                        "created_at","shipped_at","delivered_at","returned_at","sale_price"]
                vals = [tuple(i.get(c) for c in cols) for i in items]
            
            with self.conn.cursor() as cur:
                sql = f"INSERT INTO {self.schema}.order_items (id,order_id,user_id,product_id,inventory_item_id,status,created_at,shipped_at,delivered_at,returned_at,sale_price) VALUES %s ON CONFLICT (id) DO NOTHING"
                self._chunked_execute(cur, sql, vals, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)

    def insert_payments(self, payments: Iterable[Mapping]):
        payments = list(payments)
        if not payments:
            return
        
        def _insert():
            cols = ["payment_id","order_id","payment_date","status","amount","refund_amount","provider"]
            vals = [tuple(p.get(c) for c in cols) for p in payments]
            
            with self.conn.cursor() as cur:
                sql = f"INSERT INTO {self.schema}.payments ({','.join(cols)}) VALUES %s ON CONFLICT (payment_id) DO NOTHING"
                self._chunked_execute(cur, sql, vals, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)

    def insert_users(self, users: Iterable[Mapping]):
        users = list(users)
        if not users:
            return
        
        def _insert():
            cols = ["id","first_name","last_name","email","age","gender","state","street_address","postal_code","city","country","latitude","longitude","traffic_source","created_at","dob"]
            rows = [tuple(u[c] for c in cols) for u in users]
            
            with self.conn.cursor() as cur:
                sql = f"INSERT INTO {self.schema}.users ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING"
                self._chunked_execute(cur, sql, rows, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)


    def insert_shipments(self, shipments: list[dict], batch_size: int = 200):
        """
        Insert shipments into avosoft_retail.shipments idempotently.
        shipments: list of dicts with keys:
            shipment_id, order_id, order_item_id, carrier, tracking_number,
            status, created_at, shipped_at, estimated_delivery, actual_delivery,
            shipping_cost, origin_address (dict), destination_address (dict), carrier_id (optional)
        """
        if not shipments:
            return

        sql = f"""
        INSERT INTO {self.schema}.shipments (
            shipment_id, order_id, order_item_id, carrier, tracking_number, status,
            created_at, shipped_at, estimated_delivery, actual_delivery, shipping_cost,
            origin_address, destination_address, last_updated, carrier_id
        ) VALUES %s
        ON CONFLICT (tracking_number) DO UPDATE SET
            status = EXCLUDED.status,
            last_updated = NOW(),
            shipped_at = COALESCE(EXCLUDED.shipped_at, avosoft_retail.shipments.shipped_at),
            estimated_delivery = COALESCE(EXCLUDED.estimated_delivery, avosoft_retail.shipments.estimated_delivery),
            actual_delivery = COALESCE(EXCLUDED.actual_delivery, avosoft_retail.shipments.actual_delivery),
            shipping_cost = COALESCE(EXCLUDED.shipping_cost, avosoft_retail.shipments.shipping_cost),
            origin_address = COALESCE(EXCLUDED.origin_address, avosoft_retail.shipments.origin_address),
            destination_address = COALESCE(EXCLUDED.destination_address, avosoft_retail.shipments.destination_address),
            carrier_id = COALESCE(EXCLUDED.carrier_id, avosoft_retail.shipments.carrier_id)
        ;
        """

        cur = self.conn.cursor()
        vals = []
        for s in shipments:
            vals.append((
                s.get("shipment_id") or str(uuid.uuid4()),
                s["order_id"],
                s["order_item_id"],
                s.get("carrier"),
                s["tracking_number"],
                s.get("status", "label_created"),
                s.get("created_at"),
                s.get("shipped_at"),
                s.get("estimated_delivery"),
                s.get("actual_delivery"),
                s.get("shipping_cost"),
                json.dumps(s.get("origin_address") or {}),
                json.dumps(s.get("destination_address") or {}),
                s.get("last_updated") or s.get("created_at"),
                s.get("carrier_id")
            ))
        # chunked execute pattern (similar to your other methods)
        for i in range(0, len(vals), batch_size):
            chunk = vals[i:i+batch_size]
            execute_values(cur, sql, chunk, page_size=len(chunk))
        self.conn.commit()

    def insert_shipment_events(self, events: list[dict], batch_size: int = 200):
        """
        Insert shipment event rows into avosoft_retail.shipment_events.
        Each event: event_id (optional), shipment_id, carrier_code, status, description, event_time, location, raw_payload
        """
        if not events:
            return
        sql = f"""
        INSERT INTO {self.schema}.shipment_events
        (event_id, shipment_id, carrier_code, status, description, event_time, location, raw_payload, created_at)
        VALUES %s
        ON CONFLICT (event_id) DO NOTHING;
        """
        cur = self.conn.cursor()
        vals = []
        for e in events:
            vals.append((
                e.get("event_id") or str(uuid.uuid4()),
                e["shipment_id"],
                e.get("carrier_code"),
                e.get("status"),
                e.get("description"),
                e.get("event_time"),
                json.dumps(e.get("location") or {}),
                json.dumps(e.get("raw_payload") or {}),
                e.get("created_at") or datetime.utcnow()
            ))
        for i in range(0, len(vals), batch_size):
            execute_values(cur, sql, vals[i:i+batch_size], page_size=len(vals[i:i+batch_size]))
        self.conn.commit()

    # helpful helper: find DC id by country (expects distribution_centres table stores countries as array/json)
    def dc_id_for_country(self, country: str):
        cur = self.conn.cursor()
        cur.execute(f"""
            SELECT id
            FROM {self.schema}.distribution_centres
            WHERE %s = ANY(countries)
            LIMIT 1;
        """, (country,))
        row = cur.fetchone()
        return row[0] if row else None
