"""
흑백요리사2 - Supabase 연동 데이터 로더
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# 방영일 정의 (2025-2026 시즌2)
BROADCAST_DATES = [
    '2025-12-16',  # 1회
    '2025-12-23',  # 2회
    '2025-12-30',  # 3회
    '2026-01-06',  # 4회
    '2026-01-13',  # 5회
]


def get_supabase_headers():
    """Supabase API 헤더 생성"""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }


def fetch_from_supabase(table: str, select: str = "*", filters: dict = None, limit: int = None) -> pd.DataFrame:
    """
    Supabase에서 데이터 조회
    
    Args:
        table: 테이블명
        select: 선택할 컬럼 (기본: 전체)
        filters: 필터 조건 (예: {"autonomous_district": "eq.강남구"})
        limit: 최대 레코드 수
    
    Returns:
        DataFrame
    """
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {"select": select}
    
    if filters:
        params.update(filters)
    if limit:
        params["limit"] = limit
    
    try:
        response = requests.get(url, headers=get_supabase_headers(), params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"[Error] Supabase fetch failed: {e}")
        return pd.DataFrame()


def load_reviews_from_supabase() -> pd.DataFrame:
    """Supabase에서 리뷰 데이터 로드"""
    df = fetch_from_supabase("catchtable_reviews")
    
    if df.empty:
        return df
    
    # 날짜 변환
    df['collected_at'] = pd.to_datetime(df['collected_at'])
    df['review_date'] = df['collected_at'].dt.date
    
    return df


def load_population_from_supabase(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Supabase에서 유동인구 데이터 로드"""
    filters = {}
    
    if start_date:
        filters["sensing_time"] = f"gte.{start_date}"
    if end_date:
        filters["sensing_time"] = f"lte.{end_date}"
    
    df = fetch_from_supabase("seoul_floating_population", filters=filters)
    
    if df.empty:
        return df
    
    # 컬럼명 통일
    df.columns = [col.upper() if col != 'id' else col for col in df.columns]
    df['SENSING_TIME'] = pd.to_datetime(df['SENSING_TIME'])
    df['date'] = df['SENSING_TIME'].dt.date
    
    return df


def load_restaurants_from_supabase() -> pd.DataFrame:
    """Supabase에서 가게 정보 로드 (또는 로컬 CSV 사용)"""
    # 가게 정보는 자주 변경되지 않으므로 로컬 CSV 사용 가능
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, '캐치테이블_가게정보.csv')
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df = df.dropna(subset=['lat', 'lon'])
        
        if 'review_count' in df.columns:
            df['review_count'] = df['review_count'].astype(str).str.replace(',', '').str.replace('"', '')
            df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce').fillna(0).astype(int)
        
        return df
    
    return pd.DataFrame()


def get_period_range(broadcast_date: str, days_before: int = 7, days_after: int = 7) -> Tuple[datetime, datetime, datetime, datetime]:
    """방영일 기준 전/후 기간 계산"""
    bd = pd.to_datetime(broadcast_date)
    
    before_start = bd - timedelta(days=days_before)
    before_end = bd - timedelta(days=1)
    after_start = bd
    after_end = bd + timedelta(days=days_after - 1)
    
    return before_start, before_end, after_start, after_end


def calculate_review_changes_supabase(df_reviews: pd.DataFrame) -> pd.DataFrame:
    """Supabase 리뷰 데이터에서 방영일별 변화 계산"""
    results = []
    
    if df_reviews.empty:
        return pd.DataFrame()
    
    restaurants = df_reviews['restaurant_name'].unique()
    
    for restaurant in restaurants:
        rest_reviews = df_reviews[df_reviews['restaurant_name'] == restaurant]
        
        for i, bd in enumerate(BROADCAST_DATES, 1):
            before_start, before_end, after_start, after_end = get_period_range(bd)
            
            # 전/후 리뷰 수 계산
            before_data = rest_reviews[
                (rest_reviews['collected_at'] >= before_start) & 
                (rest_reviews['collected_at'] <= before_end)
            ]
            after_data = rest_reviews[
                (rest_reviews['collected_at'] >= after_start) & 
                (rest_reviews['collected_at'] <= after_end)
            ]
            
            before_count = before_data['review_count'].sum() if len(before_data) > 0 else 0
            after_count = after_data['review_count'].sum() if len(after_data) > 0 else 0
            
            # 증가율 계산
            if before_count > 0:
                change_rate = ((after_count - before_count) / before_count) * 100
            else:
                change_rate = 100.0 if after_count > 0 else 0.0
            
            results.append({
                'restaurant': restaurant,
                'episode': i,
                'broadcast_date': bd,
                'before_count': before_count,
                'after_count': after_count,
                'change_count': after_count - before_count,
                'change_rate': change_rate
            })
    
    return pd.DataFrame(results)


def get_daily_population_supabase(df_pop: pd.DataFrame) -> pd.DataFrame:
    """일별 자치구별 유동인구 집계"""
    if df_pop.empty:
        return pd.DataFrame()
    
    df_pop['date'] = pd.to_datetime(df_pop['SENSING_TIME']).dt.date
    
    daily_pop = df_pop.groupby(['date', 'AUTONOMOUS_DISTRICT']).agg({
        'VISITOR_COUNT': 'sum'
    }).reset_index()
    
    daily_pop.columns = ['date', 'district', 'population']
    daily_pop['date'] = pd.to_datetime(daily_pop['date'])
    
    return daily_pop


if __name__ == '__main__':
    print("=== Supabase 연결 테스트 ===")
    print(f"URL: {SUPABASE_URL[:30]}...")
    print(f"Key: {SUPABASE_KEY[:10]}...")
    
    print("\n리뷰 데이터 로드 중...")
    reviews = load_reviews_from_supabase()
    print(f"  - 레코드 수: {len(reviews)}")
    
    print("\n유동인구 데이터 로드 중...")
    pop = load_population_from_supabase()
    print(f"  - 레코드 수: {len(pop)}")
    
    print("\n가게 정보 로드 중...")
    restaurants = load_restaurants_from_supabase()
    print(f"  - 가게 수: {len(restaurants)}")
