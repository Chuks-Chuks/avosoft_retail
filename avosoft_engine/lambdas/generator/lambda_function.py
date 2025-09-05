# lambdas/generator/lambda_function.py
import os, gzip, io, json, datetime, boto3
from services import generators
from services.generators.users_generator import UsersGenerator
from avosoft_engine.services.generators.products_generator import ProductsGenerator
from avosoft_engine.services.generators.orders_generator import OrdersGenerator
from avosoft_engine.services.generators.events_generator import EventsGenerator

s3 = boto3.client("s3")
BUCKET = os.getenv("S3_BUCKET", "avosoft-bronze")
PREFIX = os.getenv("S3_PREFIX", "")

def _put_jsonl_gz(bucket, key, rows):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        for r in rows:
            gz.write((json.dumps(r, default=str) + "\n").encode("utf-8"))
    buf.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue(),
                  ContentType="application/json", ContentEncoding="gzip")

def lambda_handler(event, context):
    now = datetime.datetime.utcnow()
    ds = now.strftime("%Y-%m-%d")
    hh = now.strftime("%H")
    base = f"{PREFIX}/ingestion_date={ds}-{hh}" if PREFIX else f"ingestion_date={ds}-{hh}"

    # generate small hourly slices (tune volumes in your generators)
    users    = UsersGenerator().generate_batch()
    products = ProductsGenerator().generate_batch()
    orders   = OrdersGenerator().generate_batch()
    events   = EventsGenerator().generate_batch()

    payloads = {
        "users": users, "products": products, "orders": orders, "events": events
    }
    written = []
    for name, rows in payloads.items():
        if rows:
            key = f"{name}/{base}/{name}.jsonl.gz"
            _put_jsonl_gz(BUCKET, key, rows)
            written.append(key)

    return {"status": "ok", "keys": written}
