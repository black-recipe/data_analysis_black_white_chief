"""
흑백요리사2 방송 효과 분석 대시보드 (Supabase 연동 버전)
실시간으로 Supabase에서 데이터를 가져와 표시
"""
import streamlit as st
import pandas as pd
import sys
import os

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_data_loader import (
    load_reviews_from_supabase,
    load_population_from_supabase,
    load_restaurants_from_supabase,
    calculate_review_changes_supabase,
    get_daily_population_supabase,
    BROADCAST_DATES,
    SUPABASE_URL
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
    page_title="흑백요리사2 분석 (실시간)",
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
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .live-badge {
        background: linear-gradient(135deg, #00c853 0%, #00e676 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # 5분마다 캐시 갱신
def load_review_data():
    """리뷰 데이터 로드 (5분 캐시)"""
    reviews = load_reviews_from_supabase()
    if reviews.empty:
        return pd.DataFrame(), pd.DataFrame()
    changes = calculate_review_changes_supabase(reviews)
    return reviews, changes


@st.cache_data(ttl=300)  # 5분마다 캐시 갱신
def load_population_data():
    """유동인구 데이터 로드 (5분 캐시)"""
    population = load_population_from_supabase()
    if population.empty:
        return pd.DataFrame(), pd.DataFrame()
    daily_pop = get_daily_population_supabase(population)
    return population, daily_pop


@st.cache_data(ttl=3600)  # 1시간 캐시
def load_restaurant_data():
    """가게 정보 로드 (1시간 캐시)"""
    return load_restaurants_from_supabase()


@st.cache_resource
def get_geojson():
    """GeoJSON 로드 (영구 캐시)"""
    return load_seoul_geojson()


def main():
    # 헤더
    col_title, col_badge = st.columns([4, 1])
    with col_title:
        st.markdown('<p class="main-header">🍳 흑백요리사2 방송 효과 분석</p>', unsafe_allow_html=True)
    with col_badge:
        st.markdown('<span class="live-badge">🔴 LIVE (Supabase)</span>', unsafe_allow_html=True)
    
    st.markdown('<p class="sub-header">실시간 Supabase 데이터 연동 | 자동 새로고침 (5분)</p>', unsafe_allow_html=True)
    
    # 연결 상태 확인
    if not SUPABASE_URL:
        st.error("⚠️ Supabase 연결 정보가 없습니다. `.env` 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정하세요.")
        st.code("""
# .env 파일 예시
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJxxxxx...
        """)
        return
    
    # 데이터 로드
    with st.spinner("Supabase에서 데이터 로드 중..."):
        reviews, review_changes = load_review_data()
        population, daily_pop = load_population_data()
        restaurants = load_restaurant_data()
        geojson = get_geojson()
    
    # 데이터 상태 표시
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 리뷰 레코드", f"{len(reviews):,}건")
    with col2:
        st.metric("👥 유동인구 레코드", f"{len(population):,}건")
    with col3:
        st.metric("🏪 분석 가게", f"{len(restaurants)}개")
    with col4:
        st.metric("📅 마지막 업데이트", pd.Timestamp.now().strftime("%H:%M:%S"))
    
    st.divider()
    
    # 사이드바
    st.sidebar.header("🎛️ 필터 옵션")
    
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
    
    # 새로고침 버튼
    if st.sidebar.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    # 자동 새로고침 설정
    auto_refresh = st.sidebar.checkbox("⏰ 자동 새로고침 (5분)", value=False)
    if auto_refresh:
        st.sidebar.info("5분마다 자동으로 새로고침됩니다.")
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs([
        "📊 리뷰 히트맵", 
        "🗺️ 유동인구 지도",
        "📈 상세 분석"
    ])
    
    # === 탭 1: 리뷰 히트맵 ===
    with tab1:
        st.header("📊 방영일별 리뷰 변화 히트맵")
        
        if review_changes.empty:
            st.warning("리뷰 데이터가 없습니다. Airflow DAG를 실행하여 데이터를 수집하세요.")
        else:
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
            
            # TOP 10
            st.subheader("🏆 리뷰 증가율 TOP 10")
            top10 = get_top_restaurants_by_change(review_changes, episode=selected_episode, top_n=10)
            if not top10.empty:
                st.dataframe(
                    top10[['restaurant', 'change_rate', 'before_count', 'after_count']].rename(columns={
                        'restaurant': '가게명',
                        'change_rate': '증가율 (%)',
                        'before_count': '방영 전',
                        'after_count': '방영 후'
                    }),
                    hide_index=True
                )
    
    # === 탭 2: 유동인구 지도 ===
    with tab2:
        st.header("🗺️ 서울시 유동인구 변화 지도")
        
        if daily_pop.empty:
            st.warning("유동인구 데이터가 없습니다. Airflow DAG를 실행하여 데이터를 수집하세요.")
        else:
            map_type = st.radio(
                "지도 유형",
                options=['comparison', 'static'],
                format_func=lambda x: {
                    'comparison': '📊 방영일 변화율 지도',
                    'static': '📍 특정 날짜 지도'
                }[x],
                horizontal=True
            )
            
            if map_type == 'comparison':
                broadcast_date = BROADCAST_DATES[selected_episode - 1]
                st.info(f"📊 방영일 {broadcast_date} 기준 7일 전후 유동인구 변화율")
                
                fig_comp = create_broadcast_comparison_map(
                    population, 
                    restaurants, 
                    broadcast_date, 
                    geojson
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                all_dates = sorted(daily_pop['date'].unique())
                selected_date = st.date_input(
                    "날짜 선택",
                    value=pd.to_datetime(BROADCAST_DATES[selected_episode - 1]),
                    min_value=all_dates[0] if len(all_dates) > 0 else None,
                    max_value=all_dates[-1] if len(all_dates) > 0 else None
                )
                
                fig_static = create_static_choropleth(
                    population,
                    restaurants,
                    str(selected_date),
                    geojson
                )
                st.plotly_chart(fig_static, use_container_width=True)
            
            # 가게 목록
            st.subheader("★ 흑백요리사 출연 가게")
            if not restaurants.empty:
                rest_display = restaurants[['restaurant', 'chief_info', 'category', 'location', 'review_count']].copy()
                rest_display.columns = ['가게명', '셰프', '카테고리', '위치', '리뷰수']
                st.dataframe(rest_display.head(20), hide_index=True)
    
    # === 탭 3: 상세 분석 ===
    with tab3:
        st.header("📈 개별 가게 상세 분석")
        
        if review_changes.empty:
            st.warning("분석할 데이터가 없습니다.")
        else:
            all_restaurants = sorted(review_changes['restaurant'].unique())
            selected_restaurant = st.selectbox("가게 선택", options=all_restaurants)
            
            if selected_restaurant:
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
                
                fig_bar = create_review_bar_chart(review_changes, selected_restaurant)
                st.plotly_chart(fig_bar, use_container_width=True)
                
                st.subheader("📋 회차별 상세 데이터")
                rest_changes = review_changes[review_changes['restaurant'] == selected_restaurant]
                display_df = rest_changes[['episode', 'broadcast_date', 'before_count', 'after_count', 'change_count', 'change_rate']]
                display_df.columns = ['회차', '방영일', '방영 전', '방영 후', '증가 수', '증가율 (%)']
                st.dataframe(display_df, hide_index=True)
    
    # 푸터
    st.divider()
    st.markdown(f"""
    <div style="text-align: center; color: #888; font-size: 0.85rem;">
        🔗 Supabase 연동 | 데이터 갱신: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)
    
    # 자동 새로고침 (5분)
    if auto_refresh:
        import time
        time.sleep(300)  # 5분
        st.rerun()


if __name__ == '__main__':
    main()
