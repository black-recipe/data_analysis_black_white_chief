"""
흑백요리사2 방송 효과 분석 대시보드
Streamlit 메인 앱
"""
import streamlit as st
import pandas as pd
import sys
import os

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_processor import (
    load_reviews, 
    load_population, 
    load_restaurants,
    calculate_review_changes,
    get_daily_population_by_district,
    BROADCAST_DATES
)
from review_heatmap import (
    create_review_heatmap,
    create_review_bar_chart,
    get_top_restaurants_by_change
)
from population_animated_map import (
    load_seoul_geojson,
    create_animated_population_map,
    create_broadcast_comparison_map,
    create_static_choropleth
)

# 페이지 설정
st.set_page_config(
    page_title="흑백요리사2 방송 효과 분석",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f1f1f;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_all_data():
    """데이터 로드 (캐싱)"""
    reviews = load_reviews()
    population = load_population()
    restaurants = load_restaurants()
    return reviews, population, restaurants


@st.cache_data
def get_review_changes(_reviews):
    """리뷰 변화 계산 (캐싱)"""
    return calculate_review_changes(_reviews)


@st.cache_data
def get_daily_pop(_population):
    """일별 유동인구 집계 (캐싱)"""
    return get_daily_population_by_district(_population)


@st.cache_resource
def get_geojson():
    """GeoJSON 로드 (캐싱)"""
    return load_seoul_geojson()


def main():
    # 헤더
    st.markdown('<p class="main-header">🍳 흑백요리사 시즌2 방송 효과 분석</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">방영일 기준 7일 전후 리뷰 및 유동인구 변화 분석</p>', unsafe_allow_html=True)
    
    # 데이터 로드
    with st.spinner("데이터 로드 중..."):
        reviews, population, restaurants = load_all_data()
        review_changes = get_review_changes(reviews)
        daily_pop = get_daily_pop(population)
        geojson = get_geojson()
    
    # 사이드바
    st.sidebar.header("🎛️ 필터 옵션")
    
    # 방영일 선택
    episode_labels = {
        1: "1회 (12/16)",
        2: "2회 (12/23)",
        3: "3회 (12/30)",
        4: "4회 (1/6)",
        5: "5회 (1/13)"
    }
    selected_episode = st.sidebar.selectbox(
        "방영 회차 선택",
        options=list(episode_labels.keys()),
        format_func=lambda x: episode_labels[x],
        index=0
    )
    
    # 날짜 범위 (애니메이션용)
    st.sidebar.subheader("📅 날짜 범위")
    all_dates = sorted(daily_pop['date'].unique())
    date_range = st.sidebar.date_input(
        "분석 기간",
        value=(all_dates[0], all_dates[-1]),
        min_value=all_dates[0],
        max_value=all_dates[-1]
    )
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs([
        "📊 리뷰 히트맵", 
        "🗺️ 유동인구 애니메이션 지도",
        "📈 상세 분석"
    ])
    
    # === 탭 1: 리뷰 히트맵 ===
    with tab1:
        st.header("📊 방영일별 리뷰 변화 히트맵")
        st.info("""
        **💡 이 대시보드는?**
        흑백요리사 출연 가게들의 **리뷰 변화**를 분석합니다. 각 방영일 기준으로 7일 전과 후를 비교하여
        리뷰 증가율과 증가 수를 시각화했습니다. 색이 진할수록 리뷰 증가가 많았던 가게입니다.
        """)

        col1, col2, col3 = st.columns(3)
        
        # 상위 통계
        total_restaurants = len(review_changes['restaurant'].unique())
        avg_change = review_changes['change_rate'].mean()
        max_change = review_changes['change_rate'].max()
        
        with col1:
            st.metric("분석 가게 수", f"{total_restaurants}개")
        with col2:
            st.metric("평균 리뷰 증가율", f"{avg_change:.1f}%")
        with col3:
            st.metric("최대 증가율", f"{max_change:.1f}%")
        
        st.divider()
        
        # 히트맵
        value_option = st.radio(
            "표시 값 선택",
            options=['change_rate', 'change_count'],
            format_func=lambda x: '증가율 (%)' if x == 'change_rate' else '증가 수',
            horizontal=True
        )
        
        fig_heatmap = create_review_heatmap(
            review_changes, 
            restaurants,
            value_column=value_option
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # TOP/BOTTOM 가게
        st.subheader("🏆 리뷰 증가율 TOP 10")
        top10 = get_top_restaurants_by_change(review_changes, episode=selected_episode, top_n=10)
        
        col_top, col_bottom = st.columns(2)
        with col_top:
            st.dataframe(
                top10[['restaurant', 'change_rate', 'before_count', 'after_count']].rename(columns={
                    'restaurant': '가게명',
                    'change_rate': '증가율 (%)',
                    'before_count': '방영 전',
                    'after_count': '방영 후'
                }),
                hide_index=True
            )
    
    # === 탭 2: 유동인구 애니메이션 지도 ===
    with tab2:
        st.header("🗺️ 서울시 유동인구 변화 지도")
        st.info("""
        **💡 이 대시보드는?**
        서울시 자치구별 **유동인구 변화**를 지도 위에 표시합니다.
        - 🎬 **애니메이션**: 날짜별로 유동인구가 어떻게 변화했는지 확인
        - 📊 **방영일 변화율**: 방영 전후 유동인구 증감률 비교 (빨강=증가, 파랑=감소)
        - ★ **회색 마커**: 흑백요리사 출연 가게 위치
        """)

        map_type = st.radio(
            "지도 유형 선택",
            options=['animation', 'comparison', 'static'],
            format_func=lambda x: {
                'animation': '🎬 애니메이션 지도',
                'comparison': '📊 방영일 변화율 지도',
                'static': '📍 특정 날짜 지도'
            }[x],
            horizontal=True
        )
        
        if map_type == 'animation':
            st.info("▶ 재생 버튼을 눌러 일별 유동인구 변화를 확인하세요. ★ 마커는 흑백요리사 출연 가게입니다.")
            
            with st.spinner("애니메이션 지도 생성 중... (시간이 소요될 수 있습니다)"):
                start_str = date_range[0].strftime('%Y-%m-%d') if isinstance(date_range, tuple) else str(date_range[0])
                end_str = date_range[1].strftime('%Y-%m-%d') if isinstance(date_range, tuple) and len(date_range) > 1 else str(date_range[-1])
                
                fig_map = create_animated_population_map(
                    daily_pop,
                    restaurants,
                    geojson,
                    start_date=start_str,
                    end_date=end_str
                )
                st.plotly_chart(fig_map, use_container_width=True)
        
        elif map_type == 'comparison':
            broadcast_date = BROADCAST_DATES[selected_episode - 1]
            st.info(f"📊 방영일 {broadcast_date} 기준 7일 전후 유동인구 변화율")
            
            fig_comp = create_broadcast_comparison_map(
                population, 
                restaurants, 
                broadcast_date, 
                geojson
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        
        else:  # static
            selected_date = st.date_input(
                "날짜 선택",
                value=pd.to_datetime(BROADCAST_DATES[selected_episode - 1])
            )
            
            fig_static = create_static_choropleth(
                population,
                restaurants,
                str(selected_date),
                geojson
            )
            st.plotly_chart(fig_static, use_container_width=True)
        
        # 가게 목록
        st.subheader("★ 흑백요리사 출연 가게 목록")
        rest_display = restaurants[['restaurant', 'chief_info', 'category', 'location', 'review_count']].copy()
        rest_display.columns = ['가게명', '셰프', '카테고리', '위치', '리뷰수']
        st.dataframe(rest_display, hide_index=True)
    
    # === 탭 3: 상세 분석 ===
    with tab3:
        st.header("📈 개별 가게 상세 분석")
        st.info("""
        **💡 이 대시보드는?**
        특정 가게를 선택하여 **회차별 상세 데이터**를 확인합니다.
        각 방영일마다 리뷰가 얼마나 증가했는지 막대그래프와 표로 확인할 수 있습니다.
        """)

        # 가게 선택
        all_restaurants = sorted(review_changes['restaurant'].unique())
        selected_restaurant = st.selectbox("가게 선택", options=all_restaurants)
        
        if selected_restaurant:
            # 해당 가게 정보
            rest_info = restaurants[restaurants['restaurant'] == selected_restaurant]
            if len(rest_info) > 0:
                info = rest_info.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("셰프", info.get('chief_info', 'N/A'))
                with col2:
                    st.metric("카테고리", info.get('category', 'N/A'))
                with col3:
                    st.metric("위치", info.get('location', 'N/A'))
                with col4:
                    st.metric("총 리뷰수", info.get('review_count', 'N/A'))
            
            # 막대 그래프
            fig_bar = create_review_bar_chart(review_changes, selected_restaurant)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # 상세 데이터 테이블
            st.subheader("📋 회차별 상세 데이터")
            rest_changes = review_changes[review_changes['restaurant'] == selected_restaurant]
            display_df = rest_changes[['episode', 'broadcast_date', 'before_count', 'after_count', 'change_count', 'change_rate']]
            display_df.columns = ['회차', '방영일', '방영 전 리뷰', '방영 후 리뷰', '증가 수', '증가율 (%)']
            st.dataframe(display_df, hide_index=True)
    
    # 푸터
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
        데이터 출처: 캐치테이블 리뷰, 서울시 유동인구 IoT 데이터<br>
        분석 기간: 2025-12-09 ~ 2026-01-14
    </div>
    """, unsafe_allow_html=True)


if __name__ == '__main__':
    main()
