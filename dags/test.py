from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import logging

def success_log():
    logging.info("✅ DAG 실행 성공")

with DAG(
    dag_id="test",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    success_task = PythonOperator(
        task_id="print_success",
        python_callable=success_log
    )
