from airflow import DAG
from airflow.operators.python import PythonOperator
import pendulum
import datetime

# DAG 정의
with DAG(
    dag_id='test_execution_check',
    description='실행 확인을 위한 테스트 DAG',
    start_date=pendulum.now('Asia/Seoul').subtract(days=1),
    schedule_interval=None,
    catchup=False,
    tags=['test']
) as dag:

    def print_execution_status():
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] DAG가 정상적으로 실행되었습니다.")

    # 실행 확인 태스크
    check_task = PythonOperator(
        task_id='check_execution_task',
        python_callable=print_execution_status
    )
