import uuid, random
from typing import Iterable, Mapping
from ..config import SETTINGS
from ..io.pg_writer import PostgresWriter
from psycopg2.extras import execute_values

class Repo:
    def __init__(self):
        self.db = PostgresWriter()

    # ------------- seed & fetch -------------
    def ensure_dcs(self):
        cnt = self.db.fetchall("select count(*) from distribution_centers")[0][0]
        if cnt == 0:
            # minimal 5 DCs if empty
            rows = []
            for i in range(5):
                rows.append((str(uuid.uuid4()), f"DC-{100+i}", 6.45+i, 3.36+i))
            self.db.bulk_insert("distribution_centers",
                                rows, ["id","name","latitude","longitude"])

    def users_ids(self) -> list[str]:
        return [r[0] for r in self.db.fetchall("select id from users")]

    def products_pool(self) -> list[dict]:
        rows = self.db.fetchall("select product_id, cost, category, name, brand, retail_price, department, sku from products")
        return [dict(zip(["product_id","cost","category","name","brand","retail_price","department","sku"], r)) for r in rows]

    def unsold_inventory_by_product(self) -> dict[str, list[str]]:
        rows = self.db.fetchall("select id, product_id from inventory_items where sold_at is null order by created_at")
        out = {}
        for inv_id, pid in rows:
            out.setdefault(pid, []).append(inv_id)
        return out

    def low_stock_products(self, threshold: int) -> list[str]:
        sql = """
        with c as (
          select product_id, count(*) as unsold
          from inventory_items
          where sold_at is null
          group by 1
        )
        select product_id from c where unsold < %s
        """
        return [r[0] for r in self.db.fetchall(sql, (threshold,))]

    def random_dc(self) -> str:
        rows = self.db.fetchall("select id from distribution_centers")
        return random.choice(rows)[0]

    # ------------- inserts -------------
    def insert_users(self, users: Iterable[Mapping]):
        cols = ["id","first_name","last_name","email","age","gender","state","street_address","postal_code","city","country","latitude","longitude","traffic_source","created_at","dob"]
        rows = [tuple(u[c] for c in cols) for u in users]
        return self.db.bulk_insert("users", rows, cols)

    def insert_products(self, products: Iterable[Mapping]):
        cols = ["product_id","cost","category","name","brand","retail_price","department","sku","subcategory"]
        rows = [tuple(p[c] for c in cols) for p in products]
        return self.db.bulk_insert("products", rows, cols)

    def insert_inventory_items(self, items: Iterable[Mapping]):
        cols = ["id","product_id","created_at","sold_at","cost","product_category","product_name","product_brand","product_retail_price","product_department","product_sku","product_distribution_center_id"]
        rows = [tuple(i[c] for c in cols) for i in items]
        return self.db.bulk_insert("inventory_items", rows, cols)

    def insert_orders(self, orders):
        cols = ["order_id","user_id","status","gender","created_at","num_of_items"]
        rows = [(
            o["order_id"], o["user_id"], o.get("status","pending"),
            o.get("gender"), o["created_at"], o["num_of_items"]
        ) for o in orders]
        return self.db.bulk_insert("orders", rows, cols)

    def insert_order_items(self, items: list[tuple]):
        cols = ["id","order_id","user_id","product_id","inventory_item_id","status",
                "created_at","shipped_at","delivered_at","returned_at","sale_price"]
        return self.db.bulk_insert("order_items", items, cols)


    def insert_payments(self, payments: Iterable[Mapping]):
        cols = ["payment_id","order_id","payment_date","status","amount","refund_amount","provider"]
        rows = [tuple(p[c] for c in cols) for p in payments]
        return self.db.bulk_insert("payments", rows, cols)

    def mark_inventory_sold(self, sold_pairs: list[tuple[str, str]]):
        # sold_pairs: [(inv_id, sold_at), ...]
        self.db.execute("create temp table if not exists tmp_sold(inv_id uuid primary key, sold_at timestamp)")
        execute_values(self.db.cur, "insert into tmp_sold(inv_id, sold_at) values %s on conflict do nothing", sold_pairs, page_size=5000)
        self.db.execute("""
            update inventory_items i
            set sold_at = t.sold_at
            from tmp_sold t
            where i.id = t.inv_id and i.sold_at is null
        """)

    def commit_close(self, ok=True):
        self.db.commit_close(ok)
