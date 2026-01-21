"""
흑백요리사2 - 서울시 유동인구 자동 수집 및 Supabase 적재 DAG
Airflow 3.0+ 호환 버전
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.hooks.base import BaseHook
from airflow.models import Variable
import requests
import pandas as pd
import os
import time
import json

# ==============================================================================
# Configuration
# ==============================================================================
SERVICE = "IotVdata018"
BASE_URL = "http://openapi.seoul.go.kr:8088/{key}/json/{service}/{start}/{end}/"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "seoul_floating_pop_raw3.csv")
SUPABASE_CONN_ID = "xoosl033110_supabase_conn"
SUPABASE_TABLE = "seoul_floating_population"

# 자치구 영-한 매핑
GU_MAPPING = {
    'gangnam-gu': '강남구', 'gangdong-gu': '강동구', 'gangbuk-gu': '강북구',
    'gangseo-gu': '강서구', 'gwanak-gu': '관악구', 'gwangjin-gu': '광진구',
    'guro-gu': '구로구', 'geumcheon-gu': '금천구', 'nowon-gu': '노원구',
    'dobong-gu': '도봉구', 'dongdaemun-gu': '동대문구', 'dongjak-gu': '동작구',
    'mapo-gu': '마포구', 'seodaemun-gu': '서대문구', 'seocho-gu': '서초구',
    'seongdong-gu': '성동구', 'seongbuk-gu': '성북구', 'songpa-gu': '송파구',
    'yangcheon-gu': '양천구', 'yeongdeungpo-gu': '영등포구', 'yongsan-gu': '용산구',
    'eunpyeong-gu': '은평구', 'jongno-gu': '종로구', 'jung-gu': '중구', 'jungnang-gu': '중랑구'
}


def get_seoul_api_key():
    """Airflow Variable에서 Seoul API Key 가져오기"""
    return Variable.get('seoul_api')


def get_supabase_credentials():
    """Airflow Connection에서 Supabase 인증정보 가져오기"""
    conn = BaseHook.get_connection(SUPABASE_CONN_ID)
    supabase_url = conn.host if conn.host.startswith('http') else f"https://{conn.host}"
    supabase_key = conn.password
    return supabase_url, supabase_key


def translate_name(name, mapping_dict):
    """영문 지명을 한글로 변환"""
    if not name:
        return ""
    norm_name = name.lower().replace(' ', '')
    return mapping_dict.get(norm_name, name)


def parse_sensing_time(time_str):
    """시간 문자열 파싱"""
    if not time_str:
        return None
    for fmt in ["%Y-%m-%d_%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def fetch_data_batch(api_key, start_idx, end_idx, retries=3):
    """API에서 데이터 배치 가져오기"""
    url = BASE_URL.format(key=api_key, service=SERVICE, start=start_idx, end=end_idx)
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if SERVICE in data and 'row' in data[SERVICE]:
                return data[SERVICE]['row']
            elif 'RESULT' in data and data['RESULT'].get('CODE') == 'INFO-200':
                return []
            else:
                time.sleep(1)
                continue
        except Exception as e:
            if attempt == retries - 1:
                print(f"[Error] Failed to fetch {start_idx}-{end_idx}: {e}")
            time.sleep(2)
    return []


def get_latest_collected_time():
    """Supabase 또는 로컬 파일에서 최신 수집 시간 조회"""
    
    # 1. 먼저 Supabase에서 최신 시간 조회 시도
    try:
        supabase_url, supabase_key = get_supabase_credentials()
        
        # 최신 sensing_time 조회 (내림차순 정렬, 1개만)
        query_url = f"{supabase_url}/rest/v1/{SUPABASE_TABLE}?select=sensing_time&order=sensing_time.desc&limit=1"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
        }
        
        response = requests.get(query_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                latest_time_str = data[0].get('sensing_time')
                if latest_time_str:
                    latest_time = pd.to_datetime(latest_time_str)
                    print(f"[Info] Latest time from Supabase: {latest_time}")
                    return latest_time
            print("[Info] Supabase table is empty, starting from 2025-12-09")
        else:
            print(f"[Warning] Supabase query failed: {response.status_code}")
            
    except Exception as e:
        print(f"[Warning] Could not query Supabase: {e}")
    
    # 2. Supabase 실패 시 로컬 파일 확인 (fallback)
    if os.path.exists(OUTPUT_FILE):
        try:
            df = pd.read_csv(OUTPUT_FILE, usecols=['SENSING_TIME'])
            if not df.empty:
                df['SENSING_TIME'] = pd.to_datetime(df['SENSING_TIME'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
                max_time = df['SENSING_TIME'].max()
                if pd.notna(max_time):
                    print(f"[Info] Latest time from local CSV: {max_time}")
                    return max_time
        except Exception as e:
            print(f"[Warning] Could not read local file: {e}")
    
    # 3. 둘 다 실패 시 기본값 (2025-12-09부터 수집)
    default_time = datetime(2025, 12, 9)
    print(f"[Info] Using default start time: {default_time}")
    return default_time


def collect_population_data(**context):
    """유동인구 데이터 수집"""
    print("=== Starting Seoul IoT Population Data Collection ===")
    
    # Seoul API Key 가져오기
    api_key = get_seoul_api_key()
    print(f"[Info] Seoul API Key loaded from Airflow Variable")
    
    last_collected_time = get_latest_collected_time()
    print(f"Latest collected time: {last_collected_time}")
    
    if not os.path.exists(OUTPUT_FILE):
        header = ["SENSING_TIME", "AUTONOMOUS_DISTRICT", "ADMINISTRATIVE_DISTRICT", "VISITOR_COUNT", "REG_DTTM"]
        pd.DataFrame(columns=header).to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    start_idx = 1
    batch_size = 1000
    total_new_rows = 0
    all_new_data = []
    max_batches = 100
    
    for batch_num in range(max_batches):
        end_idx = start_idx + batch_size - 1
        rows = fetch_data_batch(api_key, start_idx, end_idx)
        
        if not rows:
            print(f"[Info] No more data at index {start_idx}")
            break
        
        valid_rows = []
        stop_signal = False
        
        for row in rows:
            sensing_raw = row.get('SENSING_TIME') or row.get('REG_DTTM')
            dt = parse_sensing_time(sensing_raw)
            
            if not dt:
                continue
            
            if dt <= last_collected_time:
                stop_signal = True
                break
            
            raw_gu = row.get('AUTONOMOUS_DISTRICT', '')
            kor_gu = translate_name(raw_gu, GU_MAPPING)
            
            valid_rows.append({
                "SENSING_TIME": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "AUTONOMOUS_DISTRICT": kor_gu,
                "ADMINISTRATIVE_DISTRICT": row.get('ADMINISTRATIVE_DISTRICT', ''),
                "VISITOR_COUNT": row.get('VISITOR_COUNT', 0),
                "REG_DTTM": row.get('REG_DTTM', '')
            })
        
        if valid_rows:
            df_batch = pd.DataFrame(valid_rows)
            df_batch.to_csv(OUTPUT_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            all_new_data.extend(valid_rows)
            total_new_rows += len(valid_rows)
            print(f"[Batch {batch_num + 1}] Added {len(valid_rows)} rows")
        
        if stop_signal:
            print(f"[Info] Reached already collected data. Stopping.")
            break
        
        start_idx += batch_size
        time.sleep(0.2)
    
    # XCom으로 새 데이터 전달 (Supabase 적재용)
    context['ti'].xcom_push(key='new_data', value=all_new_data)
    context['ti'].xcom_push(key='total_rows', value=total_new_rows)
    
    print(f"=== Collection Complete. New rows: {total_new_rows} ===")
    return total_new_rows


def load_to_supabase(**context):
    """수집된 데이터를 Supabase에 적재"""
    print("=== Loading Data to Supabase ===")
    
    # XCom에서 데이터 가져오기
    ti = context['ti']
    new_data = ti.xcom_pull(task_ids='collect_population_data', key='new_data')
    total_rows = ti.xcom_pull(task_ids='collect_population_data', key='total_rows')
    
    if not new_data or total_rows == 0:
        print("[Info] No new data to load to Supabase")
        return 0
    
    # Supabase 인증정보 가져오기
    supabase_url, supabase_key = get_supabase_credentials()
    
    # Supabase REST API 엔드포인트
    api_url = f"{supabase_url}/rest/v1/{SUPABASE_TABLE}"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # 배치 단위로 삽입 (500개씩)
    batch_size = 500
    inserted_count = 0
    
    for i in range(0, len(new_data), batch_size):
        batch = new_data[i:i + batch_size]
        
        # 컬럼명을 Supabase 테이블에 맞게 변환
        supabase_batch = []
        for row in batch:
            supabase_batch.append({
                "sensing_time": row["SENSING_TIME"],
                "autonomous_district": row["AUTONOMOUS_DISTRICT"],
                "administrative_district": row["ADMINISTRATIVE_DISTRICT"],
                "visitor_count": row["VISITOR_COUNT"],
                "reg_dttm": row["REG_DTTM"],
                "created_at": datetime.now().isoformat()
            })
        
        try:
            response = requests.post(
                api_url,
                headers=headers,
                data=json.dumps(supabase_batch),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                inserted_count += len(batch)
                print(f"[Supabase] Inserted batch {i // batch_size + 1}: {len(batch)} rows")
            else:
                print(f"[Error] Supabase insert failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"[Error] Supabase request failed: {e}")
    
    print(f"=== Supabase Load Complete. Inserted: {inserted_count} rows ===")
    return inserted_count


def ensure_table_exists(**context):
    """Supabase(PostgreSQL)에 테이블이 없으면 생성"""
    print("=== Checking/Creating Supabase Table ===")
    
    # Airflow Connection에서 Supabase 정보 가져오기
    conn = BaseHook.get_connection(SUPABASE_CONN_ID)
    
    # Connection 정보 출력 (디버깅용)
    print(f"[Info] Connection ID: {SUPABASE_CONN_ID}")
    print(f"[Info] Host: {conn.host}")
    print(f"[Info] Schema: {conn.schema}")
    print(f"[Info] Login: {conn.login}")
    print(f"[Info] Port: {conn.port}")
    
    # Supabase REST API로 테이블 존재 확인
    supabase_url = conn.host if conn.host.startswith('http') else f"https://{conn.host}"
    supabase_key = conn.password
    
    check_url = f"{supabase_url}/rest/v1/{SUPABASE_TABLE}?limit=0"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }
    
    try:
        response = requests.get(check_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"[Info] Table '{SUPABASE_TABLE}' already exists")
            return True
        else:
            print(f"[Info] Table check response: {response.status_code}")
            print(f"[Info] Response: {response.text[:500] if response.text else 'empty'}")
            
    except Exception as e:
        print(f"[Warning] Table check failed: {e}")
    
    # 테이블이 없거나 확인 실패 시 - PostgreSQL 직접 연결 시도
    print("[Info] Attempting to create table via PostgreSQL direct connection...")
    
    # Extra에서 PostgreSQL 연결 정보 파싱
    extra = {}
    if conn.extra:
        try:
            extra = json.loads(conn.extra)
        except:
            pass
    
    # PostgreSQL 연결 정보 구성
    db_host = extra.get('db_host') or extra.get('postgres_host')
    db_port = extra.get('db_port', 5432) or conn.port or 5432
    db_name = extra.get('db_name', 'postgres') or conn.schema or 'postgres'
    db_user = extra.get('db_user', 'postgres') or conn.login or 'postgres'
    db_password = extra.get('db_password') or conn.password
    
    # host에서 DB host 추출 시도 (https://xxx.supabase.co -> db.xxx.supabase.co)
    if not db_host and conn.host:
        host = conn.host.replace('https://', '').replace('http://', '')
        if '.supabase.co' in host:
            project_ref = host.split('.')[0]
            db_host = f"db.{project_ref}.supabase.co"
            print(f"[Info] Derived DB host: {db_host}")
    
    if not db_host:
        print("[Error] PostgreSQL host not found in connection")
        print_create_table_sql()
        return False
    
    # PostgreSQL 연결 시도
    try:
        import psycopg2
        
        print(f"[Info] Connecting to PostgreSQL: {db_host}:{db_port}/{db_name}")
        
        pg_conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            sslmode='require'
        )
        
        cursor = pg_conn.cursor()
        
        # 테이블 생성 SQL
        create_sql = '''
        CREATE TABLE IF NOT EXISTS seoul_floating_population (
            id BIGSERIAL PRIMARY KEY,
            sensing_time TIMESTAMP NOT NULL,
            autonomous_district VARCHAR(50) NOT NULL,
            administrative_district VARCHAR(100),
            visitor_count INTEGER DEFAULT 0,
            reg_dttm VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_pop_sensing_time 
            ON seoul_floating_population(sensing_time);
        CREATE INDEX IF NOT EXISTS idx_pop_district 
            ON seoul_floating_population(autonomous_district);
        '''
        
        cursor.execute(create_sql)
        pg_conn.commit()
        
        cursor.close()
        pg_conn.close()
        
        print(f"[Success] Table '{SUPABASE_TABLE}' created successfully!")
        return True
        
    except ImportError:
        print("[Warning] psycopg2 not installed. Cannot connect to PostgreSQL directly.")
        print_create_table_sql()
        return False
        
    except Exception as e:
        print(f"[Error] PostgreSQL connection failed: {e}")
        print_create_table_sql()
        return False


def print_create_table_sql():
    """테이블 생성 SQL 출력"""
    sql = '''
    -- Supabase SQL Editor에서 실행하세요:
    
    CREATE TABLE IF NOT EXISTS seoul_floating_population (
        id BIGSERIAL PRIMARY KEY,
        sensing_time TIMESTAMP NOT NULL,
        autonomous_district VARCHAR(50) NOT NULL,
        administrative_district VARCHAR(100),
        visitor_count INTEGER DEFAULT 0,
        reg_dttm VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_pop_sensing_time 
        ON seoul_floating_population(sensing_time);
    CREATE INDEX IF NOT EXISTS idx_pop_district 
        ON seoul_floating_population(autonomous_district);
    '''
    print(sql)


# ==============================================================================
# DAG Definition (Airflow 3.0+)
# ==============================================================================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='seoul_population_collector',
    default_args=default_args,
    description='서울시 유동인구 IoT 데이터 수집 및 Supabase 적재',
    schedule='0 */6 * * *',  # 6시간마다 실행 (Airflow 3.0+)
    start_date=datetime(2026, 1, 15),
    catchup=False,
    tags=['흑백요리사', '유동인구', 'IoT', 'Supabase'],
) as dag:
    
    start = EmptyOperator(task_id='start')
    
    ensure_table = PythonOperator(
        task_id='ensure_table_exists',
        python_callable=ensure_table_exists,
    )
    
    collect_data = PythonOperator(
        task_id='collect_population_data',
        python_callable=collect_population_data,
    )
    
    load_supabase = PythonOperator(
        task_id='load_to_supabase',
        python_callable=load_to_supabase,
    )
    
    end = EmptyOperator(task_id='end')
    
    start >> ensure_table >> collect_data >> load_supabase >> end
