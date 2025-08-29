# avosoft_retail/avosoft_engine/io/pg_conn.py
import psycopg2
from ..config import SETTINGS

def get_conn():
    return psycopg2.connect(
        host=SETTINGS.db_host,
        port=SETTINGS.db_port,
        dbname=SETTINGS.db_name,
        user=SETTINGS.db_user,
        password=SETTINGS.db_pass,
    )
