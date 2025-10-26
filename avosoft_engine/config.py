# avosoft_retail/avosoft_engine/config.py

from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Ensuring the environment variable loads dynamically. 

app_env = os.getenv("APP_ENV", "dev")  # Before each run I will declare the APP_ENV in the console --Also remember to ensure that the cron job gives this command for production. 

# Mapping the target environment files. Depending on what is declared in the console. 

env_file_map = {
    "dev": ".env.dev",
    "prod": ".env.prod"
    "staging": ".env.staging"
}

# Loading the appropraite .env file

load_dotenv(env_file_map.get(app_env, ".env"))


@dataclass(frozen=True)
class Settings:
    # targets
    target: str = os.getenv("TARGET", "postgres")  # postgres | files
    bronze_root: Path = Path(os.getenv("BRONZE_ROOT", "data_lake/bronze"))

    # scale knobs
    seed: int = int(os.getenv("SEED", "42"))
    sim_date: str | None = os.getenv("SIM_DATE")  # YYYY-MM-DD
    daily_users: int = int(os.getenv("DAILY_USERS", "50"))
    daily_orders: int = int(os.getenv("DAILY_ORDERS", "750"))
    daily_events: int = int(os.getenv("DAILY_EVENTS", "5000"))
    daily_new_products: int = int(os.getenv("DAILY_NEW_PRODUCTS", "5"))

    # business knobs
    low_stock_threshold: int = int(os.getenv("LOW_STOCK_THRESHOLD", "30"))
    restock_min: int = int(os.getenv("RESTOCK_MIN", "50"))
    restock_max: int = int(os.getenv("RESTOCK_MAX", "150"))
    payment_success_rate: float = float(os.getenv("PAYMENT_SUCCESS_RATE", "0.93"))
    refund_rate: float = float(os.getenv("REFUND_RATE", "0.03"))

    # db
    db_host: str | None = os.getenv("DB_HOST")
    db_port: str | None = os.getenv("DB_PORT")
    db_name: str | None = os.getenv("DB_NAME")
    db_user: str | None = os.getenv("DB_USER")
    db_pass: str | None = os.getenv("DB_PASS")
    db_schema: str = os.getenv("DB_SCHEMA")

    # AWS S3
    aws_access_key_id: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region: str | None = os.getenv("AWS_REGION")
    s3_bucket_name: str | None = os.getenv("S3_BUCKET_NAME")

SETTINGS = Settings()
# debug


# Rememeber to declare the APP_ENV in the console
# For example:"
"""
APP_ENV=prod python -m <folder>.<filename>
"""
