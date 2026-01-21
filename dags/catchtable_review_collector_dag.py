"""
흑백요리사2 - 캐치테이블 리뷰 자동 수집 및 Supabase 적재 DAG
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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================================================================
# Configuration
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESTAURANT_FILE = os.path.join(BASE_DIR, "캐치테이블_가게정보.csv")
REVIEW_HISTORY_FILE = os.path.join(BASE_DIR, "review_count_history.csv")
SUPABASE_CONN_ID = "xoosl033110_supabase_conn"
SUPABASE_TABLE = "catchtable_reviews"


def get_supabase_credentials():
    """Airflow Connection에서 Supabase 인증정보 가져오기"""
    conn = BaseHook.get_connection(SUPABASE_CONN_ID)
    supabase_url = conn.host if conn.host.startswith('http') else f"https://{conn.host}"
    supabase_key = conn.password
    return supabase_url, supabase_key


def setup_driver():
    """Selenium WebDriver 설정"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver


def get_review_count(driver, url, timeout=15):
    """단일 가게의 리뷰 수 가져오기"""
    try:
        driver.get(url)
        time.sleep(2)
        
        try:
            review_tab = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '리뷰') or contains(@class, 'review')]"))
            )
            review_tab.click()
            time.sleep(1)
        except:
            pass
        
        review_count = 0
        selectors = [
            "//span[contains(@class, 'review-count')]",
            "//div[contains(@class, 'review')]//span[contains(text(), '개')]",
            "//span[contains(text(), '리뷰')]/following-sibling::span"
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                text = element.text.replace(',', '').replace('개', '').strip()
                review_count = int(''.join(filter(str.isdigit, text)))
                break
            except:
                continue
        
        return review_count
        
    except Exception as e:
        print(f"[Error] Failed to get review count from {url}: {e}")
        return None


def collect_reviews(**context):
    """리뷰 수 수집"""
    print("=== Starting CatchTable Review Collection ===")
    
    if not os.path.exists(RESTAURANT_FILE):
        print(f"[Error] Restaurant file not found: {RESTAURANT_FILE}")
        return []
    
    df_restaurants = pd.read_csv(RESTAURANT_FILE, encoding='utf-8-sig')
    
    if 'URL' not in df_restaurants.columns:
        print("[Error] URL column not found in restaurant file")
        return []
    
    # 기존 히스토리 로드
    if os.path.exists(REVIEW_HISTORY_FILE):
        df_history = pd.read_csv(REVIEW_HISTORY_FILE, encoding='utf-8-sig')
    else:
        df_history = pd.DataFrame(columns=['url', 'restaurant_name', 'review_count', 'last_updated'])
    
    driver = None
    collected_data = []
    
    try:
        driver = setup_driver()
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for idx, row in df_restaurants.iterrows():
            url = row.get('URL', '')
            restaurant_name = row.get('restaurant', row.get('가게명', f'Restaurant_{idx}'))
            chef_info = row.get('chief_info', row.get('셰프닉네임', ''))
            category = row.get('category', row.get('주요판매요리', ''))
            
            if not url or pd.isna(url):
                continue
            
            print(f"[{idx + 1}/{len(df_restaurants)}] Checking: {restaurant_name}")
            
            review_count = get_review_count(driver, url)
            
            if review_count is not None:
                # 이전 리뷰 수 가져오기
                previous_count = 0
                existing = df_history[df_history['url'] == url]
                if len(existing) > 0:
                    previous_count = existing.iloc[0]['review_count']
                
                record = {
                    'url': url,
                    'restaurant_name': restaurant_name,
                    'chef_info': chef_info,
                    'category': category,
                    'previous_count': previous_count,
                    'review_count': review_count,
                    'change_count': review_count - previous_count,
                    'collected_at': today
                }
                collected_data.append(record)
                
                # 히스토리 업데이트
                if len(existing) > 0:
                    df_history.loc[df_history['url'] == url, ['review_count', 'last_updated']] = [review_count, today]
                else:
                    new_row = pd.DataFrame([{
                        'url': url,
                        'restaurant_name': restaurant_name,
                        'review_count': review_count,
                        'last_updated': today
                    }])
                    df_history = pd.concat([df_history, new_row], ignore_index=True)
            
            time.sleep(1)
        
        # 히스토리 저장
        df_history.to_csv(REVIEW_HISTORY_FILE, index=False, encoding='utf-8-sig')
        
        # XCom으로 데이터 전달
        context['ti'].xcom_push(key='collected_data', value=collected_data)
        
        print(f"=== Collection Complete. Updated: {len(collected_data)} restaurants ===")
        return collected_data
        
    except Exception as e:
        print(f"[Error] Review collection failed: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def load_reviews_to_supabase(**context):
    """수집된 리뷰 데이터를 Supabase에 적재"""
    print("=== Loading Reviews to Supabase ===")
    
    ti = context['ti']
    collected_data = ti.xcom_pull(task_ids='collect_reviews', key='collected_data')
    
    if not collected_data:
        print("[Info] No new review data to load")
        return 0
    
    supabase_url, supabase_key = get_supabase_credentials()
    
    api_url = f"{supabase_url}/rest/v1/{SUPABASE_TABLE}"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # 데이터 변환 및 삽입
    supabase_data = []
    for row in collected_data:
        supabase_data.append({
            "restaurant_name": row["restaurant_name"],
            "chef_info": row["chef_info"],
            "category": row["category"],
            "review_count": row["review_count"],
            "previous_count": row["previous_count"],
            "change_count": row["change_count"],
            "collected_at": row["collected_at"],
            "url": row["url"]
        })
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            data=json.dumps(supabase_data),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print(f"[Supabase] Inserted {len(supabase_data)} rows")
            return len(supabase_data)
        else:
            print(f"[Error] Supabase insert failed: {response.status_code} - {response.text}")
            return 0
            
    except Exception as e:
        print(f"[Error] Supabase request failed: {e}")
        return 0


def save_daily_snapshot(**context):
    """일별 스냅샷 저장"""
    today = datetime.now().strftime("%Y%m%d")
    
    if os.path.exists(REVIEW_HISTORY_FILE):
        df = pd.read_csv(REVIEW_HISTORY_FILE, encoding='utf-8-sig')
        snapshot_file = os.path.join(BASE_DIR, f"review_snapshot_{today}.csv")
        df.to_csv(snapshot_file, index=False, encoding='utf-8-sig')
        print(f"Snapshot saved: {snapshot_file}")
        return snapshot_file
    
    return None


def ensure_table_exists(**context):
    """Supabase(PostgreSQL)에 catchtable_reviews 테이블이 없으면 생성"""
    print("=== Checking/Creating catchtable_reviews Table ===")
    
    # Airflow Connection에서 Supabase 정보 가져오기
    conn = BaseHook.get_connection(SUPABASE_CONN_ID)
    
    # Connection 정보 출력 (디버깅용)
    print(f"[Info] Connection ID: {SUPABASE_CONN_ID}")
    print(f"[Info] Host: {conn.host}")
    
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
    
    # host에서 DB host 추출 시도
    if not db_host and conn.host:
        host = conn.host.replace('https://', '').replace('http://', '')
        if '.supabase.co' in host:
            project_ref = host.split('.')[0]
            db_host = f"db.{project_ref}.supabase.co"
            print(f"[Info] Derived DB host: {db_host}")
    
    if not db_host:
        print("[Error] PostgreSQL host not found in connection")
        print_catchtable_create_sql()
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
        CREATE TABLE IF NOT EXISTS catchtable_reviews (
            id BIGSERIAL PRIMARY KEY,
            restaurant_name VARCHAR(200) NOT NULL,
            chef_info VARCHAR(100),
            category VARCHAR(100),
            review_count INTEGER DEFAULT 0,
            previous_count INTEGER DEFAULT 0,
            change_count INTEGER DEFAULT 0,
            collected_at TIMESTAMP NOT NULL,
            url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_reviews_restaurant 
            ON catchtable_reviews(restaurant_name);
        CREATE INDEX IF NOT EXISTS idx_reviews_collected_at 
            ON catchtable_reviews(collected_at);
        CREATE INDEX IF NOT EXISTS idx_reviews_chef 
            ON catchtable_reviews(chef_info);
        '''
        
        cursor.execute(create_sql)
        pg_conn.commit()
        
        cursor.close()
        pg_conn.close()
        
        print(f"[Success] Table '{SUPABASE_TABLE}' created successfully!")
        return True
        
    except ImportError:
        print("[Warning] psycopg2 not installed.")
        print_catchtable_create_sql()
        return False
        
    except Exception as e:
        print(f"[Error] PostgreSQL connection failed: {e}")
        print_catchtable_create_sql()
        return False


def print_catchtable_create_sql():
    """테이블 생성 SQL 출력"""
    sql = '''
    -- Supabase SQL Editor에서 실행하세요:
    
    CREATE TABLE IF NOT EXISTS catchtable_reviews (
        id BIGSERIAL PRIMARY KEY,
        restaurant_name VARCHAR(200) NOT NULL,
        chef_info VARCHAR(100),
        category VARCHAR(100),
        review_count INTEGER DEFAULT 0,
        previous_count INTEGER DEFAULT 0,
        change_count INTEGER DEFAULT 0,
        collected_at TIMESTAMP NOT NULL,
        url TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_reviews_restaurant 
        ON catchtable_reviews(restaurant_name);
    CREATE INDEX IF NOT EXISTS idx_reviews_collected_at 
        ON catchtable_reviews(collected_at);
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
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    dag_id='catchtable_review_collector',
    default_args=default_args,
    description='캐치테이블 리뷰 수집 및 Supabase 적재',
    schedule='0 6 * * *',  # 매일 오전 6시 실행 (Airflow 3.0+)
    start_date=datetime(2026, 1, 15),
    catchup=False,
    tags=['흑백요리사', '리뷰', '캐치테이블', 'Supabase'],
) as dag:
    
    start = EmptyOperator(task_id='start')
    
    ensure_table = PythonOperator(
        task_id='ensure_table_exists',
        python_callable=ensure_table_exists,
    )
    
    collect_review_data = PythonOperator(
        task_id='collect_reviews',
        python_callable=collect_reviews,
    )
    
    load_supabase = PythonOperator(
        task_id='load_reviews_to_supabase',
        python_callable=load_reviews_to_supabase,
    )
    
    save_snapshot = PythonOperator(
        task_id='save_daily_snapshot',
        python_callable=save_daily_snapshot,
    )
    
    end = EmptyOperator(task_id='end')
    
    start >> ensure_table >> collect_review_data >> load_supabase >> save_snapshot >> end
