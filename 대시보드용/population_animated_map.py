"""
흑백요리사2 대시보드 - 유동인구 애니메이션 지도 모듈
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import requests
from typing import Optional
import sys
import os

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_processor import (
    load_population, 
    load_restaurants, 
    get_daily_population_by_district,
    BROADCAST_DATES
)

# 서울시 자치구 GeoJSON URL
SEOUL_GU_GEOJSON_URL = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"

# 자치구명 매핑 (GeoJSON의 name -> 데이터의 AUTONOMOUS_DISTRICT)
GU_NAME_MAPPING = {
    '종로구': '종로구', '중구': '중구', '용산구': '용산구', '성동구': '성동구',
    '광진구': '광진구', '동대문구': '동대문구', '중랑구': '중랑구', '성북구': '성북구',
    '강북구': '강북구', '도봉구': '도봉구', '노원구': '노원구', '은평구': '은평구',
    '서대문구': '서대문구', '마포구': '마포구', '양천구': '양천구', '강서구': '강서구',
    '구로구': '구로구', '금천구': '금천구', '영등포구': '영등포구', '동작구': '동작구',
    '관악구': '관악구', '서초구': '서초구', '강남구': '강남구', '송파구': '송파구',
    '강동구': '강동구'
}


def load_seoul_geojson() -> dict:
    """서울시 자치구 GeoJSON 로드"""
    try:
        response = requests.get(SEOUL_GU_GEOJSON_URL)
        response.raise_for_status()
        geojson = response.json()
        return geojson
    except Exception as e:
        print(f"GeoJSON 로드 실패: {e}")
        # 로컬 파일 시도
        local_path = os.path.join(os.path.dirname(__file__), 'seoul_gu.geojson')
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise


def create_animated_population_map(
    df_daily_pop: pd.DataFrame,
    df_restaurants: pd.DataFrame,
    geojson: dict = None,
    start_date: str = None,
    end_date: str = None
) -> go.Figure:
    """
    유동인구 애니메이션 지도 생성 (★ 가게 마커 포함)
    
    Args:
        df_daily_pop: get_daily_population_by_district() 결과
        df_restaurants: load_restaurants() 결과 (lat, lon 포함)
        geojson: 서울시 자치구 GeoJSON
        start_date: 시작일 (None이면 전체)
        end_date: 종료일 (None이면 전체)
    
    Returns:
        Plotly Figure 객체
    """
    if geojson is None:
        geojson = load_seoul_geojson()
    
    # 날짜 필터링
    df = df_daily_pop.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    
    # 날짜 문자열로 변환 (애니메이션용)
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # Choropleth 애니메이션 생성
    # 색상 스케일: 인구수(절대값)이므로 단색 계열(Reds) 사용 권장
    # 애니메이션 흔들림 방지를 위해 range_color 고정
    pop_min = df['population'].min()
    pop_max = df['population'].max()

    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations='district',
        featureidkey='properties.name',
        color='population',
        animation_frame='date_str',
        mapbox_style='carto-positron',
        center={'lat': 37.5665, 'lon': 126.9780},
        zoom=10,
        opacity=0.7,
        color_continuous_scale='Reds',
        range_color=[pop_min, pop_max],
        labels={'population': '유동인구(방문자수)', 'district': '자치구'},
        title='서울시 자치구별 일별 유동인구'
    )
    
    # ★ 가게 마커 추가
    if df_restaurants is not None and len(df_restaurants) > 0:
        # 가게 호버 텍스트 생성
        df_rest = df_restaurants.dropna(subset=['lat', 'lon']).copy()
        df_rest['hover_text'] = df_rest.apply(
            lambda row: (
                f"<b>★ {row['restaurant']}</b><br>"
                f"👨‍🍳 셰프: {row.get('chief_info', 'N/A')}<br>"
                f"🍽️ 카테고리: {row.get('category', 'N/A')}<br>"
                f"📝 리뷰수: {row.get('review_count', 'N/A')}"
            ),
            axis=1
        )
        
        # 마커 레이어 추가 - 연한 회색 원형 마커
        fig.add_trace(go.Scattermapbox(
            lat=df_rest['lat'],
            lon=df_rest['lon'],
            mode='markers+text',
            marker=dict(
                size=10,
                color='#cccccc',  # 연한 회색
                opacity=0.9
            ),
            text=['★'] * len(df_rest),
            textfont=dict(size=12, color='white'),
            textposition='middle center',
            hovertext=df_rest['hover_text'],
            hoverinfo='text',
            name='★ 흑백요리사 출연 가게',
            showlegend=True
        ))
    
    # 레이아웃 업데이트
    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            yanchor='top',
            y=0.99,
            xanchor='left',
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        updatemenus=[
            dict(
                type='buttons',
                showactive=False,
                y=0,
                x=0.1,
                xanchor='right',
                yanchor='top',
                pad=dict(t=0, r=10),
                buttons=[
                    dict(
                        label='▶ 재생',
                        method='animate',
                        args=[None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True}]
                    ),
                    dict(
                        label='⏸ 일시정지',
                        method='animate',
                        args=[[None], {'frame': {'duration': 0, 'redraw': False}, 'mode': 'immediate'}]
                    )
                ]
            )
        ]
    )
    
    return fig


def create_static_choropleth(
    df_pop: pd.DataFrame,
    df_restaurants: pd.DataFrame,
    target_date: str,
    geojson: dict = None
) -> go.Figure:
    """
    특정 날짜의 정적 Choropleth 지도 생성
    
    Args:
        df_pop: 유동인구 데이터
        df_restaurants: 가게 정보
        target_date: 대상 날짜 (YYYY-MM-DD)
        geojson: 서울시 GeoJSON
    
    Returns:
        Plotly Figure 객체
    """
    if geojson is None:
        geojson = load_seoul_geojson()
    
    # 일별 집계
    daily_pop = get_daily_population_by_district(df_pop)
    daily_pop['date'] = pd.to_datetime(daily_pop['date'])
    
    # 특정 날짜 필터링
    target = pd.to_datetime(target_date)
    df_target = daily_pop[daily_pop['date'] == target]
    
    # Choropleth 생성 - 색상 대비 강화
    fig = px.choropleth_mapbox(
        df_target,
        geojson=geojson,
        locations='district',
        featureidkey='properties.name',
        color='population',
        mapbox_style='carto-positron',
        center={'lat': 37.5665, 'lon': 126.9780},
        zoom=10,
        opacity=0.8,
        color_continuous_scale=[[0, '#0000FF'], [0.5, '#FFFFFF'], [1, '#FF0000']],
        labels={'population': '유동인구', 'district': '자치구'},
        title=f'서울시 유동인구 ({target_date})'
    )
    
    # 가게 마커 추가
    if df_restaurants is not None and len(df_restaurants) > 0:
        df_rest = df_restaurants.dropna(subset=['lat', 'lon']).copy()
        df_rest['hover_text'] = df_rest.apply(
            lambda row: (
                f"<b>★ {row['restaurant']}</b><br>"
                f"👨‍🍳 셰프: {row.get('chief_info', 'N/A')}<br>"
                f"🍽️ 카테고리: {row.get('category', 'N/A')}<br>"
                f"📝 리뷰수: {row.get('review_count', 'N/A')}"
            ),
            axis=1
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=df_rest['lat'],
            lon=df_rest['lon'],
            mode='markers+text',
            marker=dict(size=10, color='#cccccc', opacity=0.9),
            text=['★'] * len(df_rest),
            textfont=dict(size=12, color='white'),
            textposition='middle center',
            hovertext=df_rest['hover_text'],
            hoverinfo='text',
            name='★ 흑백요리사 출연 가게'
        ))
    
    fig.update_layout(height=700, margin=dict(l=0, r=0, t=50, b=0))
    
    return fig


def create_broadcast_comparison_map(
    df_pop: pd.DataFrame,
    df_restaurants: pd.DataFrame,
    broadcast_date: str,
    geojson: dict = None
) -> go.Figure:
    """
    방영일 기준 전/후 비교 지도 (side by side)
    
    Args:
        df_pop: 유동인구 데이터
        df_restaurants: 가게 정보
        broadcast_date: 방영일 (YYYY-MM-DD)
        geojson: 서울시 GeoJSON
    
    Returns:
        Plotly Figure 객체
    """
    from datetime import timedelta
    
    if geojson is None:
        geojson = load_seoul_geojson()
    
    bd = pd.to_datetime(broadcast_date)
    before_start = bd - timedelta(days=7)
    before_end = bd - timedelta(days=1)
    after_start = bd
    after_end = bd + timedelta(days=6)
    
    # 일별 집계
    daily_pop = get_daily_population_by_district(df_pop)
    daily_pop['date'] = pd.to_datetime(daily_pop['date'])
    
    # 전/후 기간 필터링 및 평균
    before_df = daily_pop[(daily_pop['date'] >= before_start) & (daily_pop['date'] <= before_end)]
    after_df = daily_pop[(daily_pop['date'] >= after_start) & (daily_pop['date'] <= after_end)]
    
    before_avg = before_df.groupby('district')['population'].mean().reset_index()
    before_avg.columns = ['district', 'population']
    
    after_avg = after_df.groupby('district')['population'].mean().reset_index()
    after_avg.columns = ['district', 'population']
    
    import numpy as np

    # 변화율 계산
    merged = before_avg.merge(after_avg, on='district', suffixes=('_before', '_after'))
    
    # 벡터화 연산으로 안전하게 계산 (Infinity 방지)
    # 1. 분모가 0이 아닌 경우: 일반적인 변화율 계산
    # 2. 분모가 0이고 분자가 0보다 큰 경우: 100% (신규 유입 처리)
    # 3. 그 외 (둘 다 0): 0%
    
    # 일단 기본적인 나눗셈 수행 (0으로 나누면 inf 또는 nan 발생)
    merged['change_rate'] = (merged['population_after'] - merged['population_before']) / merged['population_before'] * 100
    
    # Inf, -Inf, NaN 처리
    merged['change_rate'] = merged['change_rate'].replace([np.inf, -np.inf], 100.0) # 분모 0, 분자 > 0 인 경우로 간주 (단순화)
    merged['change_rate'] = merged['change_rate'].fillna(0.0) # 분모 0, 분자 0 인 경우 등

    
    # 변화율 지도 - 색상 대비 강화 (파랑=감소, 빨강=증가)
    fig = px.choropleth_mapbox(
        merged,
        geojson=geojson,
        locations='district',
        featureidkey='properties.name',
        color='change_rate',
        mapbox_style='carto-positron',
        center={'lat': 37.5665, 'lon': 126.9780},
        zoom=10,
        opacity=0.85,
        color_continuous_scale=[[0, '#0000FF'], [0.5, '#FFFFFF'], [1, '#FF0000']],
        range_color=[-50, 50],  # -50% ~ +50% 범위 고정
        labels={'change_rate': '변화율 (%)'},
        title=f'유동인구 변화율 (방영일: {broadcast_date})'
    )
    
    # 가게 마커 추가
    if df_restaurants is not None and len(df_restaurants) > 0:
        df_rest = df_restaurants.dropna(subset=['lat', 'lon']).copy()
        df_rest['hover_text'] = df_rest.apply(
            lambda row: (
                f"<b>★ {row['restaurant']}</b><br>"
                f"👨‍🍳 셰프: {row.get('chief_info', 'N/A')}<br>"
                f"🍽️ 카테고리: {row.get('category', 'N/A')}<br>"
                f"📝 리뷰수: {row.get('review_count', 'N/A')}"
            ),
            axis=1
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=df_rest['lat'],
            lon=df_rest['lon'],
            mode='markers+text',
            marker=dict(size=10, color='#cccccc', opacity=0.9),
            text=['★'] * len(df_rest),
            textfont=dict(size=12, color='white'),
            textposition='middle center',
            hovertext=df_rest['hover_text'],
            hoverinfo='text',
            name='★ 흑백요리사 출연 가게'
        ))
    
    fig.update_layout(height=700, margin=dict(l=0, r=0, t=50, b=0))
    
    return fig


if __name__ == '__main__':
    print("유동인구 데이터 로드 중...")
    pop = load_population()
    daily_pop = get_daily_population_by_district(pop)
    
    print("가게 정보 로드 중...")
    restaurants = load_restaurants()
    
    print("GeoJSON 로드 중...")
    geojson = load_seoul_geojson()
    print(f"  - 자치구 수: {len(geojson['features'])}")
    
    print("\n애니메이션 지도 생성 중 (시간이 소요됩니다)...")
    fig = create_animated_population_map(
        daily_pop, 
        restaurants, 
        geojson,
        start_date='2025-12-16',
        end_date='2025-12-23'
    )
    fig.write_html('population_map_test.html')
    print("✅ 애니메이션 지도 저장: population_map_test.html")
    
    print("\n방영일 변화율 지도 생성 중...")
    fig2 = create_broadcast_comparison_map(pop, restaurants, '2025-12-16', geojson)
    fig2.write_html('population_change_test.html')
    print("✅ 변화율 지도 저장: population_change_test.html")
"""
흑백요리사2 대시보드 - 유동인구 애니메이션 지도 모듈
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import requests
from typing import Optional
import sys
import os

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_processor import (
    load_population, 
    load_restaurants, 
    get_daily_population_by_district,
    BROADCAST_DATES
)

# 서울시 자치구 GeoJSON URL
SEOUL_GU_GEOJSON_URL = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"

# 자치구명 매핑 (GeoJSON의 name -> 데이터의 AUTONOMOUS_DISTRICT)
GU_NAME_MAPPING = {
    '종로구': '종로구', '중구': '중구', '용산구': '용산구', '성동구': '성동구',
    '광진구': '광진구', '동대문구': '동대문구', '중랑구': '중랑구', '성북구': '성북구',
    '강북구': '강북구', '도봉구': '도봉구', '노원구': '노원구', '은평구': '은평구',
    '서대문구': '서대문구', '마포구': '마포구', '양천구': '양천구', '강서구': '강서구',
    '구로구': '구로구', '금천구': '금천구', '영등포구': '영등포구', '동작구': '동작구',
    '관악구': '관악구', '서초구': '서초구', '강남구': '강남구', '송파구': '송파구',
    '강동구': '강동구'
}


def load_seoul_geojson() -> dict:
    """서울시 자치구 GeoJSON 로드"""
    try:
        response = requests.get(SEOUL_GU_GEOJSON_URL)
        response.raise_for_status()
        geojson = response.json()
        return geojson
    except Exception as e:
        print(f"GeoJSON 로드 실패: {e}")
        # 로컬 파일 시도
        local_path = os.path.join(os.path.dirname(__file__), 'seoul_gu.geojson')
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise


def create_animated_population_map(
    df_daily_pop: pd.DataFrame,
    df_restaurants: pd.DataFrame,
    geojson: dict = None,
    start_date: str = None,
    end_date: str = None
) -> go.Figure:
    """
    유동인구 애니메이션 지도 생성 (★ 가게 마커 포함)
    
    Args:
        df_daily_pop: get_daily_population_by_district() 결과
        df_restaurants: load_restaurants() 결과 (lat, lon 포함)
        geojson: 서울시 자치구 GeoJSON
        start_date: 시작일 (None이면 전체)
        end_date: 종료일 (None이면 전체)
    
    Returns:
        Plotly Figure 객체
    """
    if geojson is None:
        geojson = load_seoul_geojson()
    
    # 날짜 필터링
    df = df_daily_pop.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    
    # 날짜 문자열로 변환 (애니메이션용)
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # Choropleth 애니메이션 생성 - 색상 대비 강화
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations='district',
        featureidkey='properties.name',
        color='population',
        animation_frame='date_str',
        mapbox_style='carto-positron',
        center={'lat': 37.5665, 'lon': 126.9780},
        zoom=10,
        opacity=0.8,
        color_continuous_scale=[[0, '#0000FF'], [0.5, '#FFFFFF'], [1, '#FF0000']],  # 파랑-흰색-빨강
        labels={'population': '유동인구', 'district': '자치구'},
        title='서울시 자치구별 일별 유동인구'
    )
    
    # ★ 가게 마커 추가
    if df_restaurants is not None and len(df_restaurants) > 0:
        # 가게 호버 텍스트 생성
        df_rest = df_restaurants.dropna(subset=['lat', 'lon']).copy()
        df_rest['hover_text'] = df_rest.apply(
            lambda row: (
                f"<b>★ {row['restaurant']}</b><br>"
                f"👨‍🍳 셰프: {row.get('chief_info', 'N/A')}<br>"
                f"🍽️ 카테고리: {row.get('category', 'N/A')}<br>"
                f"📝 리뷰수: {row.get('review_count', 'N/A')}"
            ),
            axis=1
        )
        
        # 마커 레이어 추가 - 연한 회색 원형 마커
        fig.add_trace(go.Scattermapbox(
            lat=df_rest['lat'],
            lon=df_rest['lon'],
            mode='markers+text',
            marker=dict(
                size=10,
                color='#cccccc',  # 연한 회색
                opacity=0.9
            ),
            text=['★'] * len(df_rest),
            textfont=dict(size=12, color='white'),
            textposition='middle center',
            hovertext=df_rest['hover_text'],
            hoverinfo='text',
            name='★ 흑백요리사 출연 가게',
            showlegend=True
        ))
    
    # 레이아웃 업데이트
    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            yanchor='top',
            y=0.99,
            xanchor='left',
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        updatemenus=[
            dict(
                type='buttons',
                showactive=False,
                y=0,
                x=0.1,
                xanchor='right',
                yanchor='top',
                pad=dict(t=0, r=10),
                buttons=[
                    dict(
                        label='▶ 재생',
                        method='animate',
                        args=[None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True}]
                    ),
                    dict(
                        label='⏸ 일시정지',
                        method='animate',
                        args=[[None], {'frame': {'duration': 0, 'redraw': False}, 'mode': 'immediate'}]
                    )
                ]
            )
        ]
    )
    
    return fig


def create_static_choropleth(
    df_pop: pd.DataFrame,
    df_restaurants: pd.DataFrame,
    target_date: str,
    geojson: dict = None
) -> go.Figure:
    """
    특정 날짜의 정적 Choropleth 지도 생성
    
    Args:
        df_pop: 유동인구 데이터
        df_restaurants: 가게 정보
        target_date: 대상 날짜 (YYYY-MM-DD)
        geojson: 서울시 GeoJSON
    
    Returns:
        Plotly Figure 객체
    """
    if geojson is None:
        geojson = load_seoul_geojson()
    
    # 일별 집계
    daily_pop = get_daily_population_by_district(df_pop)
    daily_pop['date'] = pd.to_datetime(daily_pop['date'])
    
    # 특정 날짜 필터링
    target = pd.to_datetime(target_date)
    df_target = daily_pop[daily_pop['date'] == target]
    
    # Choropleth 생성 - 색상 대비 강화
    fig = px.choropleth_mapbox(
        df_target,
        geojson=geojson,
        locations='district',
        featureidkey='properties.name',
        color='population',
        mapbox_style='carto-positron',
        center={'lat': 37.5665, 'lon': 126.9780},
        zoom=10,
        opacity=0.8,
        color_continuous_scale=[[0, '#0000FF'], [0.5, '#FFFFFF'], [1, '#FF0000']],
        labels={'population': '유동인구', 'district': '자치구'},
        title=f'서울시 유동인구 ({target_date})'
    )
    
    # 가게 마커 추가
    if df_restaurants is not None and len(df_restaurants) > 0:
        df_rest = df_restaurants.dropna(subset=['lat', 'lon']).copy()
        df_rest['hover_text'] = df_rest.apply(
            lambda row: (
                f"<b>★ {row['restaurant']}</b><br>"
                f"👨‍🍳 셰프: {row.get('chief_info', 'N/A')}<br>"
                f"🍽️ 카테고리: {row.get('category', 'N/A')}<br>"
                f"📝 리뷰수: {row.get('review_count', 'N/A')}"
            ),
            axis=1
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=df_rest['lat'],
            lon=df_rest['lon'],
            mode='markers+text',
            marker=dict(size=10, color='#cccccc', opacity=0.9),
            text=['★'] * len(df_rest),
            textfont=dict(size=12, color='white'),
            textposition='middle center',
            hovertext=df_rest['hover_text'],
            hoverinfo='text',
            name='★ 흑백요리사 출연 가게'
        ))
    
    fig.update_layout(height=700, margin=dict(l=0, r=0, t=50, b=0))
    
    return fig


def create_broadcast_comparison_map(
    df_pop: pd.DataFrame,
    df_restaurants: pd.DataFrame,
    broadcast_date: str,
    geojson: dict = None
) -> go.Figure:
    """
    방영일 기준 전/후 비교 지도 (side by side)
    
    Args:
        df_pop: 유동인구 데이터
        df_restaurants: 가게 정보
        broadcast_date: 방영일 (YYYY-MM-DD)
        geojson: 서울시 GeoJSON
    
    Returns:
        Plotly Figure 객체
    """
    from datetime import timedelta
    
    if geojson is None:
        geojson = load_seoul_geojson()
    
    bd = pd.to_datetime(broadcast_date)
    before_start = bd - timedelta(days=7)
    before_end = bd - timedelta(days=1)
    after_start = bd
    after_end = bd + timedelta(days=6)
    
    # 일별 집계
    daily_pop = get_daily_population_by_district(df_pop)
    daily_pop['date'] = pd.to_datetime(daily_pop['date'])
    
    # 전/후 기간 필터링 및 평균
    before_df = daily_pop[(daily_pop['date'] >= before_start) & (daily_pop['date'] <= before_end)]
    after_df = daily_pop[(daily_pop['date'] >= after_start) & (daily_pop['date'] <= after_end)]
    
    before_avg = before_df.groupby('district')['population'].mean().reset_index()
    before_avg.columns = ['district', 'population']
    
    after_avg = after_df.groupby('district')['population'].mean().reset_index()
    after_avg.columns = ['district', 'population']
    
    # 변화율 계산
    merged = before_avg.merge(after_avg, on='district', suffixes=('_before', '_after'))
    merged['change_rate'] = ((merged['population_after'] - merged['population_before']) / merged['population_before']) * 100
    
    # 변화율 지도 - 색상 대비 강화 (파랑=감소, 빨강=증가)
    fig = px.choropleth_mapbox(
        merged,
        geojson=geojson,
        locations='district',
        featureidkey='properties.name',
        color='change_rate',
        mapbox_style='carto-positron',
        center={'lat': 37.5665, 'lon': 126.9780},
        zoom=10,
        opacity=0.85,
        color_continuous_scale=[[0, '#0000FF'], [0.5, '#FFFFFF'], [1, '#FF0000']],
        range_color=[-50, 50],  # -50% ~ +50% 범위 고정
        labels={'change_rate': '변화율 (%)'},
        title=f'유동인구 변화율 (방영일: {broadcast_date})'
    )
    
    # 가게 마커 추가
    if df_restaurants is not None and len(df_restaurants) > 0:
        df_rest = df_restaurants.dropna(subset=['lat', 'lon']).copy()
        df_rest['hover_text'] = df_rest.apply(
            lambda row: (
                f"<b>★ {row['restaurant']}</b><br>"
                f"👨‍🍳 셰프: {row.get('chief_info', 'N/A')}<br>"
                f"🍽️ 카테고리: {row.get('category', 'N/A')}<br>"
                f"📝 리뷰수: {row.get('review_count', 'N/A')}"
            ),
            axis=1
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=df_rest['lat'],
            lon=df_rest['lon'],
            mode='markers+text',
            marker=dict(size=10, color='#cccccc', opacity=0.9),
            text=['★'] * len(df_rest),
            textfont=dict(size=12, color='white'),
            textposition='middle center',
            hovertext=df_rest['hover_text'],
            hoverinfo='text',
            name='★ 흑백요리사 출연 가게'
        ))
    
    fig.update_layout(height=700, margin=dict(l=0, r=0, t=50, b=0))
    
    return fig


if __name__ == '__main__':
    print("유동인구 데이터 로드 중...")
    pop = load_population()
    daily_pop = get_daily_population_by_district(pop)
    
    print("가게 정보 로드 중...")
    restaurants = load_restaurants()
    
    print("GeoJSON 로드 중...")
    geojson = load_seoul_geojson()
    print(f"  - 자치구 수: {len(geojson['features'])}")
    
    print("\n애니메이션 지도 생성 중 (시간이 소요됩니다)...")
    fig = create_animated_population_map(
        daily_pop, 
        restaurants, 
        geojson,
        start_date='2025-12-16',
        end_date='2025-12-23'
    )
    fig.write_html('population_map_test.html')
    print("✅ 애니메이션 지도 저장: population_map_test.html")
    
    print("\n방영일 변화율 지도 생성 중...")
    fig2 = create_broadcast_comparison_map(pop, restaurants, '2025-12-16', geojson)
    fig2.write_html('population_change_test.html')
    print("✅ 변화율 지도 저장: population_change_test.html")
