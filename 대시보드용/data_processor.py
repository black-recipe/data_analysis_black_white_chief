"""
흑백요리사2 대시보드 - 데이터 전처리 모듈
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os

# 방영일 정의 (2025-2026 시즌2)
BROADCAST_DATES = [
    '2025-12-16',  # 1회
    '2025-12-23',  # 2회
    '2025-12-30',  # 3회
    '2026-01-06',  # 4회
    '2026-01-13',  # 5회
]

# 데이터 경로 설정 (Streamlit Cloud 호환)
# 현재 스크립트 위치 기준
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 상위 폴더 (로컬 환경용)
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
# data 폴더 (Streamlit Cloud 배포용)
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

def get_data_path(filename):
    """데이터 파일 경로 찾기 (data/ 폴더 우선, 없으면 상위 폴더)"""
    # 1순위: 대시보드용/data/ 폴더
    data_folder_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(data_folder_path):
        return data_folder_path
    # 2순위: 상위 폴더 (로컬)
    parent_path = os.path.join(PARENT_DIR, filename)
    if os.path.exists(parent_path):
        return parent_path
    # 3순위: 현재 폴더
    current_path = os.path.join(SCRIPT_DIR, filename)
    if os.path.exists(current_path):
        return current_path
    # 없으면 기본값 반환 (에러 발생 예정)
    return data_folder_path

REVIEWS_PATH = get_data_path('reviews_collected_20260114.csv')
POPULATION_PATH = get_data_path('seoul_floating_pop_raw3.csv')
RESTAURANT_PATH = get_data_path('캐치테이블_가게정보.csv')


def load_reviews() -> pd.DataFrame:
    """리뷰 데이터 로드 및 전처리"""
    df = pd.read_csv(REVIEWS_PATH, encoding='utf-8-sig')
    
    # Unknown 값 제거
    df = df[df['review_date'] != 'Unknown']
    
    # 날짜 형식 변환 (2026.01.13 -> 2026-01-13)
    df['review_date'] = pd.to_datetime(df['review_date'], format='%Y.%m.%d', errors='coerce')
    df = df.dropna(subset=['review_date'])
    
    return df


def load_population() -> pd.DataFrame:
    """유동인구 데이터 로드 및 전처리"""
    df = pd.read_csv(POPULATION_PATH, encoding='utf-8-sig')
    
    # 날짜/시간 변환
    df['SENSING_TIME'] = pd.to_datetime(df['SENSING_TIME'])
    df['date'] = df['SENSING_TIME'].dt.date
    
    return df


def load_restaurants() -> pd.DataFrame:
    """가게 정보 로드 및 전처리"""
    df = pd.read_csv(RESTAURANT_PATH, encoding='utf-8-sig')
    
    # 좌표가 있는 가게만 필터링
    df = df.dropna(subset=['lat', 'lon'])
    
    # 리뷰 수 숫자 변환 (쉼표 제거)
    if 'review_count' in df.columns:
        df['review_count'] = df['review_count'].astype(str).str.replace(',', '').str.replace('"', '')
        df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce').fillna(0).astype(int)
    
    return df


def get_period_range(broadcast_date: str, days_before: int = 7, days_after: int = 7) -> Tuple[datetime, datetime, datetime, datetime]:
    """방영일 기준 전/후 기간 계산"""
    bd = pd.to_datetime(broadcast_date)
    
    before_start = bd - timedelta(days=days_before)
    before_end = bd - timedelta(days=1)
    after_start = bd
    after_end = bd + timedelta(days=days_after - 1)
    
    return before_start, before_end, after_start, after_end


def calculate_review_changes(df_reviews: pd.DataFrame) -> pd.DataFrame:
    """방영일별 가게별 리뷰 증가율 계산"""
    results = []
    
    restaurants = df_reviews['restaurant'].unique()
    
    for restaurant in restaurants:
        rest_reviews = df_reviews[df_reviews['restaurant'] == restaurant]
        
        for i, bd in enumerate(BROADCAST_DATES, 1):
            before_start, before_end, after_start, after_end = get_period_range(bd)
            
            # 전/후 리뷰 수 계산
            before_count = len(rest_reviews[
                (rest_reviews['review_date'] >= before_start) & 
                (rest_reviews['review_date'] <= before_end)
            ])
            
            after_count = len(rest_reviews[
                (rest_reviews['review_date'] >= after_start) & 
                (rest_reviews['review_date'] <= after_end)
            ])
            
            # 증가율 계산 (0으로 나누기 방지)
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


def calculate_population_changes(df_pop: pd.DataFrame) -> pd.DataFrame:
    """방영일별 자치구별 유동인구 증가율 계산"""
    results = []
    
    districts = df_pop['AUTONOMOUS_DISTRICT'].unique()
    
    for district in districts:
        dist_pop = df_pop[df_pop['AUTONOMOUS_DISTRICT'] == district]
        
        for i, bd in enumerate(BROADCAST_DATES, 1):
            before_start, before_end, after_start, after_end = get_period_range(bd)
            
            # 일별 집계 후 평균
            before_data = dist_pop[
                (pd.to_datetime(dist_pop['date']) >= before_start) & 
                (pd.to_datetime(dist_pop['date']) <= before_end)
            ]
            after_data = dist_pop[
                (pd.to_datetime(dist_pop['date']) >= after_start) & 
                (pd.to_datetime(dist_pop['date']) <= after_end)
            ]
            
            before_total = before_data['VISITOR_COUNT'].sum()
            after_total = after_data['VISITOR_COUNT'].sum()
            
            # 증가율 계산
            if before_total > 0:
                change_rate = ((after_total - before_total) / before_total) * 100
            else:
                change_rate = 0.0
            
            results.append({
                'district': district,
                'episode': i,
                'broadcast_date': bd,
                'before_total': before_total,
                'after_total': after_total,
                'change_rate': change_rate
            })
    
    return pd.DataFrame(results)


def get_daily_population_by_district(df_pop: pd.DataFrame) -> pd.DataFrame:
    """일별 자치구별 유동인구 집계 (애니메이션용)"""
    df_pop['date'] = pd.to_datetime(df_pop['SENSING_TIME']).dt.date
    
    daily_pop = df_pop.groupby(['date', 'AUTONOMOUS_DISTRICT']).agg({
        'VISITOR_COUNT': 'sum'
    }).reset_index()
    
    daily_pop.columns = ['date', 'district', 'population']
    daily_pop['date'] = pd.to_datetime(daily_pop['date'])
    
    return daily_pop


if __name__ == '__main__':
    # 테스트
    print("리뷰 데이터 로드 중...")
    reviews = load_reviews()
    print(f"  - 총 리뷰 수: {len(reviews)}")
    print(f"  - 날짜 범위: {reviews['review_date'].min()} ~ {reviews['review_date'].max()}")
    
    print("\n유동인구 데이터 로드 중...")
    pop = load_population()
    print(f"  - 총 레코드 수: {len(pop)}")
    
    print("\n가게 정보 로드 중...")
    restaurants = load_restaurants()
    print(f"  - 총 가게 수: {len(restaurants)}")
    print(f"  - 좌표 있는 가게: {len(restaurants.dropna(subset=['lat', 'lon']))}")
