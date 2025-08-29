import uuid, random
from ..config import SETTINGS
from ..log import get_logger
from ..io.file_writer import FileWriter
from ..generators import users, products, distribution_centres, inventory, orders, events, base 
from .repositories import Repo
from datetime import datetime, timedelta

log = get_logger()

class Orchestrator:
    """
    Daily simulator for ALL domains with tight inventory linkage:
    - Seeds DCs/products if empty; adds a few products daily
    - Creates new users
    - Restocks low-stock items
    - Generates orders and allocates real inventory_items to order_items
      * sets shipped_at / delivered_at / returned_at on a portion of items
    - Creates payments aligned to realized (allocated) totals and returns
    - Emits browsing + purchase + return events
    """
    def __init__(self):
        self.ds = SETTINGS.sim_date or base.fake.date_this_year().isoformat()
        self.UsersGenerator = users.UsersGenerator()
        self.ProductsGenerator = products.ProductsGenerator()
        self.InventoryGenerator = inventory.InventoryGenerator()
        self.OrdersGenerator = orders.OrdersGenerator()
        self.EventsGenerator = events.EventsGenerator()
        self.DistributionCentersGenerator = distribution_centres.DistributionCentersGenerator()

    # ------------ Helpers ------------
    @staticmethod
    def _maybe_timestamp(base_iso: str, min_hours: int, max_hours: int, probability: float) -> str | None:
        """Return base + N hours with given probability; else None."""
        if random.random() > probability:
            return None
        base = datetime.fromisoformat(base_iso)
        bump = timedelta(hours=random.randint(min_hours, max_hours))
        return (base + bump).strftime("%Y-%m-%d %H:%M:%S")

    # ------------ Main run (Postgres) ------------
    def _run_pg(self):
        repo = Repo()
        try:
            # --- Seed DCs ---
            repo.ensure_dcs()

            # --- Seed products if empty; add some daily ---
            if len(repo.products_pool()) == 0:
                base_products = self.ProductsGenerator.generate_batch(500)
                repo.insert_products(base_products)
            if SETTINGS.daily_new_products > 0:
                newp = self.ProductsGenerator.generate_batch(SETTINGS.daily_new_products)
                repo.insert_products(newp)

            # --- New users for the day ---
            users = self.UsersGenerator.generate_batch(SETTINGS.daily_users, self.ds)
            repo.insert_users(users)

            # --- Restock low inventory to threshold ---
            inv_gen = self.InventoryGenerator   
            low_pids = repo.low_stock_products(SETTINGS.low_stock_threshold)
            if low_pids:
                pool = {p["product_id"]: p for p in repo.products_pool()}
                restock_rows = []
                for pid in low_pids:
                    p = pool.get(pid)
                    if not p:
                        continue
                    dc = repo.random_dc()
                    qty = random.randint(SETTINGS.restock_min, SETTINGS.restock_max)
                    restock_rows += inv_gen.restock_rows(
                        ds=self.ds,
                        product_id=pid,
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
                if restock_rows:
                    repo.insert_inventory_items(restock_rows)

            # --- Orders ---
            user_ids = repo.users_ids()
            orders = self.OrdersGenerator.generate_orders(self.ds, user_ids, SETTINGS.daily_orders)
            repo.insert_orders(orders)

            # --- Allocate inventory to order_items (tight link) ---
            product_pool = repo.products_pool()
            desired_pairs = self.OrdersGenerator.expand_order_items(orders, product_pool)
            unsold_map = repo.unsold_inventory_by_product()

            order_item_rows = []  # payload for bulk insert
            sold_pairs = []       # (inv_id, sold_at)
            totals_by_order: dict[str, float] = {}
            returns_by_order: dict[str, float] = {}

            # probabilities
            ship_p = 0.85          # % items that ship
            deliver_p = 0.92       # % shipped items that deliver
            return_p = SETTINGS.refund_rate  # align return rate with refund rate knob

            for (order_id, user_id, prod) in desired_pairs:
                inv_list = unsold_map.get(prod["product_id"], [])
                if not inv_list:
                    # out of stock -> skip this item
                    continue

                inv_id = inv_list.pop(0)
                price = float(prod["retail_price"])
                # find the order's created_at once
                created_at = next(o["created_at"] for o in orders if o["order_id"] == order_id)

                # timestamps lifecycle per item
                shipped_at = self._maybe_timestamp(created_at, 2, 48, ship_p)
                delivered_at = None
                if shipped_at:
                    delivered_at = self._maybe_timestamp(shipped_at, 24, 96, deliver_p)
                returned_at = None
                # returns only possible if delivered
                if delivered_at and random.random() < return_p:
                    # returns 1–30 days after delivery
                    delivered_dt = datetime.fromisoformat(delivered_at)
                    returned_dt = delivered_dt + timedelta(days=random.randint(1, 30))
                    # cap to same day 18:00 for simplicity
                    returned_at = returned_dt.strftime("%Y-%m-%d 18:00:00")

                # compose row
                order_item_rows.append((
                    str(uuid.uuid4()),       # id
                    order_id,                # order_id
                    user_id,                 # user_id
                    prod["product_id"],      # product_id
                    inv_id,                  # inventory_item_id
                    # status
                    "returned" if returned_at else ("delivered" if delivered_at else ("shipped" if shipped_at else "pending")),
                    created_at,              # created_at
                    shipped_at,              # shipped_at
                    delivered_at,            # delivered_at
                    returned_at,             # returned_at
                    price                    # sale_price
                ))

                # mark inventory as sold at order time
                sold_pairs.append((inv_id, created_at))

                # aggregate totals
                totals_by_order[order_id] = round(totals_by_order.get(order_id, 0.0) + price, 2)
                if returned_at:
                    # assume full refund for returned items (can be partial if desired)
                    returns_by_order[order_id] = round(returns_by_order.get(order_id, 0.0) + price, 2)

            # write order_items + mark sold inventory
            if order_item_rows:
                repo.insert_order_items(order_item_rows)
                repo.mark_inventory_sold(sold_pairs)

            # --- Payments aligned to realized totals + returns ---
            payments = []
            for o in orders:
                oid = o["order_id"]
                realized_total = float(totals_by_order.get(oid, 0.0))
                if realized_total <= 0:
                    status = "failed"
                    amount = 0.0
                    refund_amt = 0.0
                else:
                    # success/failure independent of returns; refunds applied after
                    status = "success" if random.random() < SETTINGS.payment_success_rate else "failed"
                    amount = realized_total if status == "success" else 0.0
                    refund_amt = 0.0
                    # If items returned, apply refund up to paid amount
                    if status == "success":
                        refund_amt = min(amount, float(returns_by_order.get(oid, 0.0)))

                payments.append({
                    "payment_id": str(uuid.uuid4()),
                    "order_id": oid,
                    "payment_date": self.ds,
                    "status": status,
                    "amount": round(amount, 2),
                    "refund_amount": round(refund_amt, 2),
                    "provider": random.choice(["StripeLike", "PayPalLike"]),
                })
            if payments:
                repo.insert_payments(payments)

            # --- Events: browsing + purchase + return_event ---
            ev = self.EventsGenerator
            browsing = ev.generate_browsing(self.ds, user_ids, SETTINGS.daily_events)

            # successful paid orders (amount > 0, status success) -> purchase events
            paid_success = {p["order_id"] for p in payments if p["status"] == "success" and p["amount"] > 0}
            paid_orders = [o for o in orders if o["order_id"] in paid_success]
            purchases = ev.purchase_events(self.ds, paid_orders)

            # return events for items with returned_at
            returned_items = []
            for row in order_item_rows:
                # row layout:
                # (id, order_id, user_id, product_id, inventory_item_id, status, created_at, shipped_at, delivered_at, returned_at, sale_price)
                if row[9]:  # returned_at present
                    returned_items.append({"user_id": row[2]})
            returns = ev.return_events(self.ds, returned_items) if returned_items else []

            if browsing or purchases or returns:
                cols = ["id","user_id","sequence_number","session_id","created_at","ip_address","city","state","postal_code","browser","traffic_source","uri","event_type","device_type"]
                all_events = browsing + purchases + returns
                rows = [tuple(e.get(c) for c in cols) for e in all_events]
                repo.db.bulk_insert("events", rows, cols)

            repo.commit_close(True)
            log.info(
                f"PG daily OK | users={len(users)} orders={len(orders)} "
                f"items={len(order_item_rows)} paid={sum(1 for p in payments if p['status']=='success')} "
                f"events={len(browsing)+len(purchases)+len(returns)} returns_items={len(returned_items)}"
            )
        except Exception:
            repo.commit_close(False)
            raise

    # ------------ Files mode (kept minimal; primary path is Postgres) ------------
    def _run_files(self):
        fw = FileWriter()
        users = self.UsersGenerator.generate_batch(SETTINGS.daily_users, self.ds)
        products = self.ProductsGenerator.generate_batch(500 + SETTINGS.daily_new_products)
        orders = self.OrdersGenerator.generate_orders(self.ds, [u["id"] for u in users], SETTINGS.daily_orders)

        fw.write_jsonl(f"{SETTINGS.bronze_root}/users/ingestion_date={self.ds}/users.jsonl", users)
        fw.write_jsonl(f"{SETTINGS.bronze_root}/products/ingestion_date={self.ds}/products.jsonl", products)
        fw.write_jsonl(f"{SETTINGS.bronze_root}/orders/ingestion_date={self.ds}/orders.jsonl", orders)
        log.info(f"FILES mode OK: users={len(users)} products={len(products)} orders={len(orders)}")

    # ------------ Entrypoint ------------
    def run(self):
        if SETTINGS.target == "postgres":
            self._run_pg()
        else:
            self._run_files()

