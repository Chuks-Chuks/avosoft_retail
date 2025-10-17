# avosoft_engine/services/repositories.py
import uuid
import time
from typing import Iterable, Mapping, List, Dict, Any
from psycopg2.extras import execute_values
from ..config import SETTINGS
from ..io.pg_writer import PostgresWriter
from ..io.pg_conn import get_conn
import psycopg2

class Repo:
    """Read-only helpers for the generator with connection resilience"""
    
    def __init__(self):
        self.db = PostgresWriter()
        self.max_retries = 3
        self.retry_delay = 2

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
        rows = self._query_with_retry("SELECT id FROM avosoft_retail.users;")
        return [r[0] if isinstance(r, tuple) else r["id"] for r in rows]

    # Added the user_address_map to fetch customer's address.
    def user_addresses_map(self) -> Dict[str, dict]:
        rows = self._query_with_retry("""
            SELECT id, street_address, city, state, postal_code, country, latitude, longitude
            FROM avosoft_retail.users;
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
        rows = self._query_with_retry("""
            SELECT product_id, name, brand, department, category, sku, cost, retail_price, subcategory
            FROM avosoft_retail.products;
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
        rows = self._query_with_retry("SELECT id FROM avosoft_retail.distribution_centers;")
        return [r[0] if isinstance(r, tuple) else r["id"] for r in rows]

    def unsold_inventory_by_product_map(self) -> Dict[str, List[str]]:
        rows = self._query_with_retry("""
            SELECT id, product_id
            FROM avosoft_retail.inventory_items
            WHERE sold_at IS NULL
            ORDER BY created_at;
        """)
        out: Dict[str, List[str]] = {}
        for r in rows:
            inv_id, pid = (r[0], r[1]) if isinstance(r, tuple) else (r["id"], r["product_id"])
            out.setdefault(pid, []).append(inv_id)
        return out

    def low_stock_product_ids(self, threshold: int) -> List[str]:
        rows = self._query_with_retry("""
            WITH c AS (
              SELECT product_id, count(*) as unsold
              FROM avosoft_retail.inventory_items
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
                cur.execute("""
                    SELECT id, product_id, cost, product_retail_price
                    FROM avosoft_retail.inventory_items
                    WHERE product_id = %s::uuid AND sold_at IS NULL
                    LIMIT %s FOR UPDATE SKIP LOCKED;
                """, (product_id, qty))
                rows = cur.fetchall()
                if not rows:
                    return []

                inv_ids = [r[0] for r in rows]
                cur.execute("""
                    UPDATE avosoft_retail.inventory_items
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
                    INSERT INTO avosoft_retail.products ({','.join(cols)}) 
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
                sql = f"INSERT INTO avosoft_retail.distribution_centers ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING"
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
                sql = f"INSERT INTO avosoft_retail.inventory_items ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING"
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
                sql = f"INSERT INTO avosoft_retail.orders ({','.join(cols)}) VALUES %s ON CONFLICT (order_id) DO NOTHING"
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
                sql = "INSERT INTO avosoft_retail.order_items (id,order_id,user_id,product_id,inventory_item_id,status,created_at,shipped_at,delivered_at,returned_at,sale_price) VALUES %s ON CONFLICT (id) DO NOTHING"
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
                sql = f"INSERT INTO avosoft_retail.payments ({','.join(cols)}) VALUES %s ON CONFLICT (payment_id) DO NOTHING"
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
                sql = f"INSERT INTO avosoft_retail.users ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING"
                self._chunked_execute(cur, sql, rows, self.batch_size)
            self.conn.commit()
        
        self._execute_with_retry(_insert)
