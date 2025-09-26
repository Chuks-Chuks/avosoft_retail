# avosoft_engine/services/orchestrator.py
import uuid, random
from datetime import datetime, timedelta
from ..config import SETTINGS
from ..log import get_logger
from ..io.file_writer import FileWriter
from ..io.s3_writer import S3Writer
from ..generators import users, products, distribution_centres, inventory, orders, events, payments
from ..generators.order_items import OrderItemGenerator
from .repositories import Repo, InventoryRepository
from time import sleep

log = get_logger()


class Orchestrator:
    """
    Strict generator:
    - Optionally reads minimal DB state (users/products/DCs/unsold inventory)
    - Persists inventory/orders/order_items/payments to DB (operational state)
    - Writes full payload to JSONL/S3 for data engineering pipelines
    """

    def __init__(self, read_db_state: bool = True):
        self.now = datetime.now()
        self.ds = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")
        self.ingestion_time = self.now.strftime("%H:%M:%S")

        self.UsersGenerator = users.UsersGenerator()
        self.ProductsGenerator = products.ProductsGenerator()
        self.InventoryGenerator = inventory.InventoryGenerator()
        self.OrdersGenerator = orders.OrdersGenerator()
        self.EventsGenerator = events.EventsGenerator()
        self.DCGenerator = distribution_centres.DistributionCentersGenerator()
        self.OrderItemGenerator = OrderItemGenerator()  
        self.PaymentsGenerator = payments.PaymentsGenerator()  
        self.file_writer = FileWriter()
        self.s3_writer = S3Writer()
        self.read_db_state = read_db_state
        self.repo = Repo() if read_db_state else None
        self.inv_repo = InventoryRepository()  # for DB writes/reservations

    def generate_day(self) -> dict:
        # --- 0) read minimal pools from DB (optional) ---
        #existing_users = self.repo.users_id_list() if self.read_db_state else []
        # we fetch product pool from DB if available, else we'll seed and persist later
        product_pool_dict = self.repo.products_pool_dict() if self.read_db_state else {}
        dc_ids = self.repo.dc_ids() if self.read_db_state else []
        unsold_by_pid = self.repo.unsold_inventory_by_product_map() if self.read_db_state else {}
        log.info(f"DEBUG SETTINGS -> users={SETTINGS.daily_users}, orders={SETTINGS.daily_orders}, events={SETTINGS.daily_events}")

        # --- Distribution centers ---
        existing_dcs = self.repo.dc_ids() if self.read_db_state else []
        new_dcs = []
        if not existing_dcs:
            # seed DCs locally then persist to DB (production ordering)
            new_dcs = self.DCGenerator.generate_seed(10)
            # persist seeded DCs so inventory can reference them
            self.inv_repo.insert_distribution_centers(new_dcs)
            log.info(f"[{self.ds}] Inserted {len(new_dcs)} new DCs ✅")
            dc_ids = [dc["id"] for dc in new_dcs]
            self.inv_repo.ensure_commit()
        else:
            dc_ids = existing_dcs

        # incremental DC growth: every 5 months on day 1
        if (self.now.month % 5 == 0) and (self.now.day == 1):
            extra = self.DCGenerator.generate_seed(1)
            new_dcs.extend(extra)
            # persist the new DC
            self.inv_repo.insert_distribution_centers(extra)
            self.inv_repo.ensure_commit()
            dc_ids.append(extra[0]["id"])

        # --- Users ---
        new_users = self.UsersGenerator.generate_batch(SETTINGS.daily_users, self.ds)
        new_user_ids = [u["id"] for u in new_users]
        if new_users:
            # persist new users to DB (users have no FK dependencies)
            self.inv_repo.insert_users(new_users)   
            log.info(f"[{self.ds}] Inserted {len(new_users)} new users ✅")
            sleep(2)  # initiating sleep to ensure commit
            self.inv_repo.ensure_commit()
        all_user_ids = self.repo.users_id_list() if self.read_db_state else [] + new_user_ids

        # --- Products + initial inventory seed ---
        new_products = []
        initial_inventory = []
        if not product_pool_dict:
            # seed base catalog in-memory
            new_products = self.ProductsGenerator.generate_batch(500)
            # persist products BEFORE any inventory writes (fixes FK violation)
            if new_products:
                self.inv_repo.insert_products(new_products)
                log.info(f"[{self.ds}] Inserted {len(new_products)} new products ✅")
                self.inv_repo.ensure_commit()
            # update local product_pool_dict for rest of run
            for p in new_products:
                product_pool_dict[p["product_id"]] = p

            # seed initial inventory for all new products and persist to DB
            for p in new_products:
                if not dc_ids:
                    seed_dcs = self.DCGenerator.generate_seed(5)
                    self.inv_repo.insert_distribution_centers(seed_dcs)
                    self.inv_repo.ensure_commit()
                    dc_ids = [d["id"] for d in seed_dcs]

                dc = random.choice(dc_ids)
                qty = random.randint(100, 300)
                rows = self.InventoryGenerator.restock_rows(
                    ds=self.ds,
                    product_id=p["product_id"],
                    qty=qty,
                    dc_id=dc,
                    cost=p["cost"],
                    name=p["name"],
                    brand=p["brand"],
                    retail=p["retail_price"],
                    dept=p["department"],
                    category=p["category"],
                    sku=p["sku"],
                )
                if rows:
                    # persist inventory after products & dcs are in DB
                    self.inv_repo.insert_inventory_rows(rows)
                    self.inv_repo.ensure_commit()
                    initial_inventory.extend(rows)
                    unsold_by_pid.setdefault(p["product_id"], []).extend([r["id"] for r in rows])
        else:
            # there is an existing product pool in DB; optionally add daily new products
            if SETTINGS.daily_new_products > 0:
                new_products = self.ProductsGenerator.generate_batch(SETTINGS.daily_new_products)
                if new_products:
                    # persist incremental new products before any inventory referencing them
                    self.inv_repo.insert_products(new_products)
                    self.inv_repo.ensure_commit()
                for p in new_products:
                    product_pool_dict[p["product_id"]] = p

        # --- Restock low inventory ---
        restock_rows = []
        low_pids = self.repo.low_stock_product_ids(SETTINGS.low_stock_threshold) if self.read_db_state else []

        for pid in low_pids:
            prod = product_pool_dict.get(pid)
            if not prod:
                # If product missing from in-memory pool, attempt to pull from DB (defensive)
                product_pool_dict = self.repo.products_pool_dict()
                prod = product_pool_dict.get(pid)
            if not prod:
                continue
            dc = random.choice(dc_ids)
            qty = random.randint(SETTINGS.restock_min, SETTINGS.restock_max)
            rows = self.InventoryGenerator.restock_rows(
                ds=self.ds,
                product_id=pid,
                qty=qty,
                dc_id=dc,
                cost=prod["cost"],
                name=prod["name"],
                brand=prod["brand"],
                retail=prod["retail_price"],
                dept=prod["department"],
                category=prod["category"],
                sku=prod["sku"],
            )
            if rows:
                # persist restock rows
                self.inv_repo.insert_inventory_rows(rows)
                self.inv_repo.ensure_commit()
                restock_rows.extend(rows)
                unsold_by_pid.setdefault(pid, []).extend([r["id"] for r in rows])

        # --- Orders ---
        orders_today = self.OrdersGenerator.generate_orders(self.ds, all_user_ids, SETTINGS.daily_orders)
        if orders_today:
            # persist orders (orders do not have FK to inventory)
            self.inv_repo.insert_orders(orders_today)
            log.info(f"[{self.ds}] Inserted {len(orders_today)} orders ✅")
            self.inv_repo.ensure_commit()
        # --- Allocate inventory to order_items ---
        desired_pairs = self.OrdersGenerator.expand_order_items(orders_today, list(product_pool_dict.values()))
        order_item_rows = []
        totals_by_order = {}
        returns_by_order = {}

        for order_id, user_id, prod in desired_pairs:
            # reserve one unit for the product
            try:
                prod["product_id"] = str(uuid.UUID(prod["product_id"]))
            except ValueError:
                continue  # skip malformed UUIDs

            reserved = self.inv_repo.reserve_stock(prod["product_id"], 1)
            if not reserved:
                # out-of-stock -> skip this item
                continue

            inv = reserved[0]
            # use the order item generator to produce a schema-aligned dict
            items = self.OrderItemGenerator.generate_items(
                ds=self.ds,
                order_id=order_id,
                user_id=user_id,
                product_rows=[inv],
                qty=1
            )

            if not items:
                continue

            item = items[0]
            order_item_rows.append(item)

            totals_by_order[order_id] = round(totals_by_order.get(order_id, 0.0) + item["sale_price"], 2)
            if item["returned_at"]:
                returns_by_order[order_id] = round(returns_by_order.get(order_id, 0.0) + item["sale_price"], 2)

        if order_item_rows:
            # persist order_items (these reference orders & inventory_items which both exist)
            self.inv_repo.insert_order_items(order_item_rows)
            log.info(f"[{self.ds}] Inserted {len(order_item_rows)} order_items ✅")
            self.inv_repo.ensure_commit()

        # --- Payments (moved into generator) ---
        payments = self.PaymentsGenerator.generate(
            ds=self.ds,
            orders=orders_today,
            totals_by_order=totals_by_order,
            returns_by_order=returns_by_order
        )

        if payments:
            self.inv_repo.insert_payments(payments)
            self.inv_repo.ensure_commit()
            log.info(f"[{self.ds}] Inserted {len(payments)} payments ✅")

        # --- Events ---
        ev = self.EventsGenerator
        browsing = ev.generate_browsing(self.ds, all_user_ids, SETTINGS.daily_events)

        paid_success = {p["order_id"] for p in payments if p["status"] == "success" and p["amount"] > 0}
        paid_orders = [o for o in orders_today if o["order_id"] in paid_success]
        purchases = ev.purchase_events(self.ds, paid_orders)

        returned_items = [{"user_id": row["user_id"]} for row in order_item_rows if row["returned_at"]]
        returns = ev.return_events(self.ds, returned_items) if returned_items else []

        payload = {
            "date": self.ds,
            "ingestion_time": self.ingestion_time,
            "users": new_users,
            "distribution_centers": new_dcs or [{"id": i} for i in dc_ids],
            "products": new_products,
            "inventory": restock_rows + (initial_inventory if 'initial_inventory' in locals() else []),
            "orders": orders_today,
            "order_items": order_item_rows,
            "payments": payments,
            "events": browsing + purchases + returns
        }

        log.info(
            f"Generated | users={len(new_users)} products={len(new_products)} "
            f"orders={len(orders_today)} items={len(order_item_rows)} "
            f"paid={sum(1 for p in payments if p['status']=='success')} "
            f"events={len(payload['events'])}"
        )
        return payload


    # ------------ output writers ------------
    def write_bronze(self, payload: dict):
        d = payload["date"]
        t = payload["ingestion_time"]

        def w(path, rows):
            rows_to_write = rows or []

            try:
                self.s3_writer.write_jsonl(f"bronze/{path}", rows_to_write)
                log.info(f"✅ S3 write ok: {path}")
            except Exception as e:
                log.warning(f"Failed to write s3 bronze {path}: {e}")

        w(f"users/ingestion_date={d}/ingestion_time={t}/users.jsonl", payload.get("users"))
        w(f"products/ingestion_date={d}/ingestion_time={t}/products.jsonl", payload.get("products"))
        w(f"distribution_centers/ingestion_date={d}/ingestion_time={t}/dcs.jsonl", payload.get("distribution_centers"))
        w(f"inventory/ingestion_date={d}/ingestion_time={t}/inventory.jsonl", payload.get("inventory"))
        w(f"orders/ingestion_date={d}/ingestion_time={t}/orders.jsonl", payload.get("orders"))
        w(f"order_items/ingestion_date={d}/ingestion_time={t}/order_items.jsonl", payload.get("order_items"))
        w(f"payments/ingestion_date={d}/ingestion_time={t}/payments.jsonl", payload.get("payments"))
        w(f"events/ingestion_date={d}/ingestion_time={t}/events.jsonl", payload.get("events"))

    def run(self):
        payload = self.generate_day()
        self.write_bronze(payload)
        return payload
