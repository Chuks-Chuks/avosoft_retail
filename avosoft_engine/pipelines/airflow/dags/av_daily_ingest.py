# avosoft/pipelines/airflow/dags/av_daily_ingest.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

with DAG(
    "av_daily_ingest",
    start_date=datetime(2025,1,1),
    schedule_interval="0 * * * *",
    catchup=False,
    default_args={"retries":1, "retry_delay": timedelta(minutes=5)},
    tags=["avosoft","bronze"]
) as dag:
    BashOperator(
        task_id="generate_daily_bronze",
        bash_command="export TARGET=files && export SIM_DATE={{ ds }} && python -m avosoft_data_engine.cli",
    )
