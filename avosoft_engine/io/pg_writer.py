# avosoft_retail/avosoft_engine/io/pg_writer.py

from psycopg2.extras import execute_values
from .pg_conn import get_conn
from ..config import SETTINGS

class PostgresWriter:
    def __init__(self):
        self.conn = get_conn()
        self.conn.autocommit = False
        self.cur = self.conn.cursor()
        self.cur.execute(f"SET search_path TO {SETTINGS.db_schema}")

    def bulk_insert(self, table: str, rows: list[tuple], columns: list[str], page_size=5000):
        if not rows: return 0
        cols = ",".join(columns)
        sql = f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(self.cur, sql, rows, page_size=page_size)
        return len(rows)

    def fetchall(self, sql: str, params=None):
        self.cur.execute(sql, params or ())
        return self.cur.fetchall()

    def execute(self, sql: str, params=None):
        self.cur.execute(sql, params or ())

    def commit_close(self, ok=True):
        (self.conn.commit() if ok else self.conn.rollback())
        self.cur.close(); self.conn.close()
