
import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager, rc
import os
import glob
import platform
from statsmodels.stats.outliers_influence import variance_inflation_factor

# --- 1. Page Config (Must be first) ---
st.set_page_config(
    page_title="흑백요리사 통합 분석 대시보드 (Ver.2)",
    page_icon="🍳",
    layout="wide"
)

# --- 2. Shared Utilities (Fonts & Style) ---
def set_korean_font():
    import matplotlib.font_manager as fm
    
    system_name = platform.system()
    if system_name == "Windows":
        # Windows에서 한글 폰트 직접 지정
        font_path = "c:/Windows/Fonts/malgun.ttf"
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rcParams['font.family'] = 'Malgun Gothic'
        else:
            plt.rcParams['font.family'] = 'Malgun Gothic'
    elif system_name == "Darwin":
        plt.rcParams['font.family'] = 'AppleGothic'
    else:
        plt.rcParams['font.family'] = 'NanumGothic'
    
    plt.rcParams['axes.unicode_minus'] = False
    
    # 밝은 배경 설정 (가시성 개선)
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['savefig.facecolor'] = 'white'
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['axes.labelcolor'] = 'black'
    plt.rcParams['xtick.color'] = 'black'
    plt.rcParams['ytick.color'] = 'black'
    plt.rcParams['text.color'] = 'black'
    
    # seaborn 폰트 설정
    sns.set_style("whitegrid")
    sns.set_palette("bright")
    sns.set(font='Malgun Gothic', rc={'axes.unicode_minus': False})

set_korean_font()

# --- 3. Page 1 Logic: Survival Prediction Report (Ver.2 Data) ---
def show_survival_analysis():
    st.header("🏁 심사위원 합격 예측 분석 (Ver.2)")
    st.markdown("""
    본 분석은 **'셰프서바이벌결과요약.csv'** 데이터를 바탕으로, 
    두 심사위원(**백종원**, **안성재**)의 심사 성향과 합격 기준을 통계적 기법(로지스틱 회귀분석)으로 분석한 결과입니다.
    """)

    # --- Data Loading ---
    @st.cache_data
    def load_survival_data():
        # Changed to new file
        file_path = '../셰프서바이벌결과요약.csv'
        if not os.path.exists(file_path):
            return None
        df = pd.read_csv(file_path)
        df_clean = df[df['food'] != '-'].copy()
        return df_clean

    df = load_survival_data()

    if df is None:
        st.error("데이터 파일('셰프서바이벌결과요약.csv')을 찾을 수 없습니다.")
        return

    # --- Helper Functions ---
    def plot_pass_rate(df, judge_col, judge_name):
        features = ['how_cook', 'food_category', 'ingrediant', 'temperature']
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        for i, col in enumerate(features):
            row, col_idx = divmod(i, 2)
            if col in df.columns:
                pass_rate = df.groupby(col)[judge_col].mean().sort_values(ascending=False)
                sns.barplot(x=pass_rate.index, y=pass_rate.values, ax=axes[row, col_idx], palette='viridis')
                axes[row, col_idx].set_title(f'{col}별 합격률')
                axes[row, col_idx].set_ylim(0, 1.0)
                axes[row, col_idx].tick_params(axis='x', rotation=45)
        plt.tight_layout()
        return fig

    def run_logistic_regression(df, target_col):
        if target_col == 'an':
            sub_df = df[df['is_an'] == 1].copy()
        else:
            sub_df = df[df['is_back'] == 1].copy()
            
        features = ['how_cook', 'food_category', 'ingrediant', 'temperature']
        X = pd.get_dummies(sub_df[features], drop_first=True, dtype=int)
        X = sm.add_constant(X)
        y = sub_df[target_col]
        try:
            model = sm.Logit(y, X).fit(disp=0)
            return model, X, y
        except:
            return None, None, None

    def calculate_vif(X):
        vif_data = pd.DataFrame()
        vif_data["Feature"] = X.columns
        vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
        return vif_data.sort_values(by="VIF", ascending=False)

    def create_summary_df(model):
        if model is None: return pd.DataFrame()
        summary_df = pd.DataFrame({
            "Coef": model.params,
            "P-value": model.pvalues,
            "Odds Ratio": np.exp(model.params)
        })
        return summary_df.sort_values(by="P-value")

    # --- Content Layout ---
    tab1, tab2, tab3 = st.tabs(["📊 데이터 탐색 (EDA)", "📈 회귀분석 결과", "💡 공략 리포트"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("안성재 심사위원")
            fig_an = plot_pass_rate(df[df['is_an'] == 1], 'an', '안성재')
            st.pyplot(fig_an)
            st.caption("📝 **해석**: 각 막대의 높이는 합격률을 의미합니다. 안성재 심사위원은 특정 조리법(조림 등)에서 확연히 높은 합격률을 보이는 경향이 있습니다.")

        with col2:
            st.subheader("백종원 심사위원")
            fig_back = plot_pass_rate(df[df['is_back'] == 1], 'back', '백종원')
            st.pyplot(fig_back)
            st.caption("📝 **해석**: 백종원 심사위원은 퓨전 및 다양한 조리법에서 상대적으로 고른 합격률을 보이지만, 특정 '맛'의 포인트(예: 중식 튀김)를 선호함을 알 수 있습니다.")

    with tab2:
        col_l, col_r = st.columns(2)
        
        # Ahn Analysis
        model_an, X_an, y_an = run_logistic_regression(df, 'an')
        summary_an = create_summary_df(model_an)
        with col_l:
            st.subheader("🔹 안성재 심사위원 모델")
            st.markdown("##### 📋 통계 분석 결과표")
            st.dataframe(summary_an.style.map(lambda x: 'background-color: yellow' if x < 0.05 else '', subset=['P-value']), height=400)
            st.info("""
            💡 **결과 해석 가이드**:
            - **P-value (노란색)**: 0.05 미만이면 결과가 통계적으로 매우 유의미함을 뜻합니다.
            - **Odds Ratio**: 1보다 크면 합격 확률을 **높이는** 요인, 1보다 작으면 **낮추는** 요인입니다.
            """)
            
            if X_an is not None:
                with st.expander("다중공선성(VIF) 진단"):
                    vif_an = calculate_vif(X_an)
                    st.dataframe(vif_an.style.map(lambda x: 'color: red' if x > 10 else '', subset=['VIF']))
                    st.caption("🔎 **VIF란?**: 변수들 간의 상관관계입니다. 10 이상(빨간색)이면 신뢰도가 떨어질 수 있습니다.")

            if model_an:
                st.markdown("##### 📉 잔차(오차) 분석")
                fig_res, ax = plt.subplots(figsize=(8, 4))
                # Use numpy arrays to prevent index alignment issues with seaborn regplot lowess
                sns.regplot(x=np.array(model_an.predict()), y=np.array(model_an.resid_pearson), lowess=True, 
                            line_kws={'color': 'red'}, scatter_kws={'alpha': 0.5}, ax=ax)
                ax.set_title("Residuals vs Fitted (안성재)")
                ax.axhline(0, color='blue', linestyle='--') # Blue dashed line
                st.pyplot(fig_res)
                st.caption("🔎 **그래프 보는 법**: 빨간 실선(데이터 추세)이 파란 점선(0)에 가깝고 평평할수록, 모델이 데이터를 편향 없이 잘 설명하고 있다는 뜻입니다.")

        # Baek Analysis
        model_back, X_back, y_back = run_logistic_regression(df, 'back')
        summary_back = create_summary_df(model_back)
        with col_r:
            st.subheader("🔸 백종원 심사위원 모델")
            st.markdown("##### 📋 통계 분석 결과표")
            st.dataframe(summary_back.style.map(lambda x: 'background-color: yellow' if x < 0.05 else '', subset=['P-value']), height=400)
            st.info("""
            💡 **결과 해석 가이드**:
            - **P-value (노란색)**: 이 값이 작을수록 해당 변수가 합격/불합격에 미치는 영향이 확실합니다.
            - **Odds Ratio**: 숫자가 클수록 해당 요리를 했을 때 합격할 확률이 압도적으로 높아집니다.
            """)
            
            if X_back is not None:
                with st.expander("다중공선성(VIF) 진단"):
                    vif_back = calculate_vif(X_back)
                    st.dataframe(vif_back.style.map(lambda x: 'color: red' if x > 10 else '', subset=['VIF']))
                    st.caption("🔎 **VIF란?**: 10 이하가 이상적입니다. 너무 높으면 '같은 의미의 변수'가 여러 개 들어갔다는 뜻입니다.")

            if model_back:
                st.markdown("##### 📉 잔차(오차) 분석")
                fig_res_b, ax_b = plt.subplots(figsize=(8, 4))
                # Use numpy arrays to prevent index alignment issues
                sns.regplot(x=np.array(model_back.predict()), y=np.array(model_back.resid_pearson), lowess=True, 
                            line_kws={'color': 'red'}, scatter_kws={'alpha': 0.5}, ax=ax_b)
                ax_b.set_title("Residuals vs Fitted (백종원)")
                ax_b.axhline(0, color='blue', linestyle='--') # Blue dashed line
                st.pyplot(fig_res_b)
                st.caption("🔎 **그래프 보는 법**: 데이터들(점들)이 위아래로 고르게 퍼져 있어야 좋은 모델입니다. 특정 패턴이 보이면 모델 개선이 필요할 수 있습니다.")

    with tab3:
        col_final_1, col_final_2 = st.columns(2)
        with col_final_1:
            st.markdown("### 🤵 안성재 심사위원 (Ver.2)")
            st.success("**✅ 필승 전략**: 조림(Braising)")
            st.error("**❌ 필패 전략**: 튀김(Frying)")
            st.info("💡 **전략**: 기본에 충실한 '조림'으로 깊은 맛을 어필하세요. 튀김은 피하는 것이 좋습니다.")
        with col_final_2:
            st.markdown("### 👨‍🍳 백종원 심사위원 (Ver.2)")
            st.success("**✅ 필승 전략**: 퓨전(Fusion), 튀김(Frying)")
            st.warning("**⚠️ 참고**: 중식 스타일 선호")
            st.info("💡 **전략**: 창의적인 '퓨전' 메뉴나 강력한 화력의 '튀김/볶음' 요리로 승부하세요.")
        
        st.divider()
        st.markdown("### 📝 심사위원 비교 (Ver.2)")
        comparison_data = {
            "항목": ["선호 조리법", "비선호 조리법", "핵심 키워드"],
            "안성재 (Ahn)": ["조림", "튀김", "#깊은맛 #기본기 #조림"],
            "백종원 (Baek)": ["퓨전, 튀김", "평범한 한식", "#창의성 #퓨전 #직관적맛"]
        }
        st.table(pd.DataFrame(comparison_data).set_index("항목"))


# --- 쉐프 이름 매핑 (프리픽스 -> 한글 이름) ---
CHEF_MAPPING = {
    'akrl': '아기맹수',
    'choi': '최강록',
    'hoo': '후덕죽',
    'im': '임성근',
    'jeong': '정호영',
    'sam': '샘킴',
    'seon': '선재스님',
    'son': '손종원',
    'yo': '요리괴물',
    'yoon': '윤준모'
}

# --- 4. Page 2 Logic: Trend Analysis Report (3 Sources: Naver, Google, YouTube) ---
def show_trend_analysis():
    st.header("📈 쉐프 검색 트렌드 분석 (Naver vs Google vs YouTube)")
    st.markdown("""
    **네이버(초록)**, **구글(파랑)**, **유튜브(빨강)** 3가지 소스를 통합하여 쉐프별 검색 트렌드를 시각화합니다.
    """)
    
    # --- Data Loading ---
    @st.cache_data
    def load_trend_data():
        base_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\흑백요리사트렌드추이"
        if not os.path.exists(base_path):
            st.error(f"데이터 경로를 찾을 수 없습니다: {base_path}")
            return pd.DataFrame()

        all_data = []

        for prefix, chef_name in CHEF_MAPPING.items():
            # 네이버 데이터랩
            f_naver = os.path.join(base_path, f"{prefix}_datalab.csv")
            if os.path.exists(f_naver):
                try:
                    try: df_naver = pd.read_csv(f_naver, encoding='utf-8')
                    except: df_naver = pd.read_csv(f_naver, encoding='cp949')
                    if df_naver.shape[1] >= 2:
                        df_naver = df_naver.rename(columns={df_naver.columns[0]: 'Date', df_naver.columns[1]: 'Value'})
                        df_naver['Source'] = 'Naver'
                        df_naver['Chef'] = chef_name
                        df_naver = df_naver.dropna(subset=['Value'])
                        df_naver['Value'] = pd.to_numeric(df_naver['Value'], errors='coerce')
                        all_data.append(df_naver)
                except Exception as e:
                    print(f"Naver Error ({prefix}): {e}")
            
            # 구글 트렌드
            f_google = os.path.join(base_path, f"{prefix}_google.csv")
            if os.path.exists(f_google):
                try:
                    try: df_google = pd.read_csv(f_google, encoding='utf-8')
                    except: df_google = pd.read_csv(f_google, encoding='cp949')
                    if df_google.shape[1] >= 2:
                        df_google = df_google.rename(columns={df_google.columns[0]: 'Date', df_google.columns[1]: 'Value'})
                        df_google['Source'] = 'Google'
                        df_google['Chef'] = chef_name
                        df_google = df_google.dropna(subset=['Value'])
                        df_google['Value'] = pd.to_numeric(df_google['Value'], errors='coerce')
                        all_data.append(df_google)
                except Exception as e:
                    print(f"Google Error ({prefix}): {e}")
            
            # 유튜브 (변환된 파일)
            f_youtube = os.path.join(base_path, f"{prefix}_youtube.csv")
            if os.path.exists(f_youtube):
                try:
                    df_youtube = pd.read_csv(f_youtube, encoding='utf-8-sig')
                    if df_youtube.shape[1] >= 2:
                        df_youtube = df_youtube.rename(columns={df_youtube.columns[0]: 'Date', df_youtube.columns[1]: 'Value'})
                        df_youtube['Source'] = 'YouTube'
                        df_youtube['Chef'] = chef_name
                        df_youtube = df_youtube.dropna(subset=['Value'])
                        df_youtube['Value'] = pd.to_numeric(df_youtube['Value'], errors='coerce')
                        all_data.append(df_youtube)
                except Exception as e:
                    print(f"YouTube Error ({prefix}): {e}")

        if not all_data: return pd.DataFrame()
        final_df = pd.concat(all_data, ignore_index=True)
        final_df['Date'] = pd.to_datetime(final_df['Date'])
        return final_df

    df = load_trend_data()

    if df.empty:
        st.warning("데이터가 없거나 불러오지 못했습니다.")
        return

    # --- Filters ---
    st.subheader("⚙️ 설정 및 필터")
    col1, col2 = st.columns(2)
    
    with col1:
        all_chefs = sorted(df['Chef'].unique())
        selected_chefs = st.multiselect("쉐프 선택 (전체 보기는 비워두세요)", options=all_chefs, default=[])
    
    with col2:
        all_sources = ['Naver', 'Google', 'YouTube']
        selected_sources = st.multiselect("데이터 소스 선택", options=all_sources, default=all_sources)
    
    # Filter data
    plot_df = df.copy()
    if selected_chefs:
        plot_df = plot_df[plot_df['Chef'].isin(selected_chefs)]
    if selected_sources:
        plot_df = plot_df[plot_df['Source'].isin(selected_sources)]
        
    # --- Visualization ---
    if not plot_df.empty:
        st.subheader("📊 트렌드 시각화")
        
        # 색상 팔레트 (유튜브: 빨강, 네이버: 초록, 구글: 파랑)
        color_palette = {'Google': 'blue', 'Naver': 'green', 'YouTube': 'red'}
        
        col_wrap = 4
        g = sns.relplot(
            data=plot_df, x="Date", y="Value", hue="Source", col="Chef",
            kind="line", palette=color_palette,
            col_wrap=col_wrap, height=4, aspect=1.5,
            facet_kws={'sharey': False, 'sharex': True}
        )
        g.fig.subplots_adjust(top=0.9)
        g.fig.suptitle("흑백요리사 쉐프별 트렌드 추이\n(Naver: 초록, Google: 파랑, YouTube: 빨강)", fontsize=14, fontweight='bold')
        for axes in g.axes.flat:
            _ = axes.tick_params(axis='x', rotation=45)
        st.pyplot(g.fig)
        
        # 소스별 색상 범례 설명
        st.markdown("""
        **🎨 색상 가이드:**
        - 🟢 **Naver (초록)**: 네이버 데이터랩 검색량
        - 🔵 **Google (파랑)**: 구글 트렌드 검색량
        - 🔴 **YouTube (빨강)**: 유튜브 검색량
        """)
    else:
        st.info("선택된 데이터가 없습니다.")

    with st.expander("📊 원본 데이터 테이블"):
        st.dataframe(plot_df)


# --- 5. Page 3 Logic: Genre Survival Analysis Report ---
def show_genre_survival_report():
    st.header("📊 요리 장르별 생존율 분석 보고서")
    st.markdown("""
    본 분석은 TV 서바이벌 요리 프로그램의 참가자 데이터를 바탕으로 수행되는 데이터 분석 프로젝트입니다.  
    데이터 분석가로서 단순한 승패 기록을 넘어, **'요리 장르(Food Category)'가 생존에 미치는 영향**을 통계적 관점에서 해석하고 인사이트를 도출합니다.
    
    **[분석 목적]**
    1. 요리 장르(`food_category`)에 따른 서바이벌 생존율 차이 분석
    2. 라운드별(`round`) 가장 유리한 요리 장르 탐색
    3. 경기 유형(`match_type`: 개인전/팀전)에 따른 장르별 유불리 파악
    """)
    
    # --- Data Loading ---
    @st.cache_data
    def load_genre_survival_data():
        file_path = '../3번문제완성본.csv'
        if not os.path.exists(file_path):
            return None
        df = pd.read_csv(file_path)
        
        # 생존 여부 바이너리 변환
        df['is_survived'] = df['is_alive'].apply(lambda x: 1 if x in ['생존'] else 0)
        
        # 분석에 필요한 주요 컬럼 선택
        cols = ['round', 'name', 'match_type', 'food_category', 'is_survived', 'is_alive']
        df_analysis = df[cols].copy()
        
        # 요리 장르(food_category) 결측치 제거
        df_clean = df_analysis.dropna(subset=['food_category'])
        df_clean = df_clean[df_clean['food_category'] != '-']
        
        return df_clean
    
    df_clean = load_genre_survival_data()
    
    if df_clean is None:
        st.error("데이터 파일('3번문제완성본.csv')을 찾을 수 없습니다.")
        return
    
    # --- Content Layout with Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(["📈 라운드별 생존율", "🏆 최고 생존율 장르", "⚔️ 경기 유형별 분석", "📝 결론 및 인사이트"])
    
    with tab1:
        st.subheader("라운드 × 요리 장르별 생존율 분석")
        st.markdown("""
        각 라운드에서 어떤 요리 장르가 강세를 보였는지 확인하기 위해 교차 분석표를 생성합니다.
        - **분모**: 해당 라운드 & 장르의 총 참가자 수
        - **분자**: 해당 라운드 & 장르의 생존자 수
        """)
        
        # 라운드 및 장르별 그룹화
        survival_rates = df_clean.groupby(['round', 'food_category'])['is_survived'].agg(['count', 'sum', 'mean']).reset_index()
        survival_rates.columns = ['round', 'food_category', 'participants', 'survivors', 'survival_rate']
        survival_rates['survival_rate_pct'] = survival_rates['survival_rate'] * 100
        
        # 피벗 테이블 형태로 변환
        pivot_survival = survival_rates.pivot_table(
            index='round', 
            columns='food_category', 
            values='survival_rate_pct'
        )
        
        # 히트맵 시각화
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(pivot_survival, annot=True, fmt='.1f', cmap='RdYlGn', vmin=0, vmax=100, ax=ax)
        ax.set_title('라운드별 요리 장르 생존율 (%)', fontsize=14)
        ax.set_ylabel('라운드')
        ax.set_xlabel('요리 장르')
        st.pyplot(fig)
        
        st.caption("🔎 **그래프 보는 법**: 초록색이 짙을수록 생존율이 높습니다. 빨간색에 가까울수록 생존율이 낮습니다.")
        
        # 데이터 테이블
        with st.expander("📊 상세 데이터 테이블"):
            st.dataframe(pivot_survival.round(2).fillna('-'))
    
    with tab2:
        st.subheader("라운드별 최고 생존율 요리 장르")
        st.markdown("""
        각 라운드에서 **가장 높은 생존율**을 기록한 요리 장르를 요약합니다.
        
        ⚠️ **주의**: 참가자 수가 극히 적은 경우(예: 1명) 생존율 100%나 0%가 나올 수 있음에 유의해야 합니다.
        """)
        
        # 다시 survival_rates 계산
        survival_rates = df_clean.groupby(['round', 'food_category'])['is_survived'].agg(['count', 'sum', 'mean']).reset_index()
        survival_rates.columns = ['round', 'food_category', 'participants', 'survivors', 'survival_rate']
        
        # 각 라운드별 최고 생존율 찾기
        best_performers = []
        for r in survival_rates['round'].unique():
            round_data = survival_rates[survival_rates['round'] == r]
            max_rate = round_data['survival_rate'].max()
            best_genres = round_data[round_data['survival_rate'] == max_rate]
            
            genres_str = ", ".join(best_genres['food_category'].tolist())
            participants_str = ", ".join(best_genres['participants'].astype(str).tolist())
            
            best_performers.append({
                'Round': r,
                'Best Genre': genres_str,
                'Survival Rate (%)': round(max_rate * 100, 2),
                'Participants Count': participants_str
            })
        
        df_best = pd.DataFrame(best_performers)
        # 라운드 순서 정렬
        round_order = {'1R':1, '2R':2, '3-1R':3, '3-2R':4, '4-1R':5, '4-2R':6, '5-1R':7, '5-2R':8, '6R':9}
        df_best['round_idx'] = df_best['Round'].map(round_order)
        df_best = df_best.sort_values('round_idx').drop('round_idx', axis=1).reset_index(drop=True)
        
        st.dataframe(df_best, use_container_width=True)
        
        # 요약 메트릭
        col1, col2, col3 = st.columns(3)
        with col1:
            most_common_genre = df_best['Best Genre'].value_counts().idxmax()
            st.metric("🥇 가장 자주 1위한 장르", most_common_genre)
        with col2:
            max_rate = df_best['Survival Rate (%)'].max()
            st.metric("📈 최고 생존율", f"{max_rate}%")
        with col3:
            total_rounds = len(df_best)
            st.metric("🔢 분석된 라운드 수", total_rounds)
    
    with tab3:
        st.subheader("경기 유형(팀전 vs 개인전)에 따른 장르별 생존율")
        st.markdown("""
        '개인전'과 '팀전'에서 특정 요리 장르가 더 유리하게 작용하는지 분석합니다.
        """)
        
        # 경기 유형별 그룹화
        match_type_stats = df_clean.groupby(['match_type', 'food_category'])['is_survived'].agg(['count', 'mean']).reset_index()
        match_type_stats['survival_rate_pct'] = match_type_stats['mean'] * 100
        
        # 시각화
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(data=match_type_stats, x='food_category', y='survival_rate_pct', hue='match_type', palette='muted', ax=ax)
        ax.set_title('경기 유형(팀전/개인전)에 따른 요리 장르별 생존율', fontsize=14)
        ax.set_ylabel('생존율 (%)')
        ax.set_xlabel('요리 장르')
        ax.legend(title='경기 유형')
        ax.set_ylim(0, 110)
        
        # 수치 표시
        for p in ax.patches:
            height = p.get_height()
            if height > 0:
                ax.text(p.get_x() + p.get_width()/2., height + 1, f'{int(height)}%', ha='center')
        
        st.pyplot(fig)
        
        st.caption("🔎 **그래프 보는 법**: 막대 높이가 높을수록 해당 장르의 생존율이 높습니다.")
        
        # 피벗 테이블
        pivot_match = match_type_stats.pivot_table(
            index='food_category', 
            columns='match_type', 
            values='survival_rate_pct'
        ).round(2)
        
        with st.expander("📊 경기 유형별 상세 데이터"):
            st.dataframe(pivot_match)
    
    with tab4:
        st.subheader("결론 및 인사이트")
        
        st.markdown("### 1) 데이터 해석")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            **🔵 1R (흑수저 결정전 등)**  
            다양한 장르가 출전했으나, 초기 라운드 특성상 기본기가 탄탄한 장르들이 생존하는 경향을 보입니다.
            """)
            
            st.info("""
            **🔵 팀전 (3-1R, 4-1R 등)**  
            개인의 기량보다 팀의 조화가 중요한 라운드입니다. 퓨전음식이나 양식 등 다양한 재료와 조리법을 포용할 수 있는 장르가 팀전에서 유연하게 대처하여 높은 생존율을 보였습니다.
            """)
        
        with col2:
            st.warning("""
            **🟡 후반부 (5R 이후)**  
            참가자 수가 줄어들면서 특정 개인의 승패가 장르 전체의 생존율에 큰 영향을 미칩니다. (예: 1명 출전하여 생존 시 100%)
            """)
            
            st.warning("""
            **🟡 데이터 해석 주의점**  
            표본 크기가 작은 경우 극단적인 생존율(0% 또는 100%)이 나타날 수 있으므로 참가자 수를 함께 고려해야 합니다.
            """)
        
        st.markdown("### 2) 구조적 유리함과 전략적 시사점")
        st.success("""
        **✅ 장르의 유불리**  
        특정 라운드 미션(예: 재료 제한, 대량 조리 등)에 따라 특정 장르가 유리할 수 있습니다. 예를 들어 3-1R(재료 대결)이나 5-2R(무한 요리 지옥)에서는 창의성이 요구되는 **퓨전음식**이나 다양한 조리법을 가진 장르가 생존에 유리했을 가능성이 높습니다.
        """)
        
        st.success("""
        **✅ 전략 제안**  
        서바이벌 초반에는 **본인의 주력 장르(정통성)**로 어필하고, 중반 이후 팀전 및 변수 미션에서는 **퓨전/창의적 접근**을 가미하는 것이 생존 확률을 높이는 전략으로 데이터상 관측됩니다.
        """)
        
        st.divider()
        st.markdown("""
        **[분석 요약]**  
        본 분석은 요리 서바이벌 프로그램 데이터를 통해 라운드별 요리 장르와 생존율의 관계를 정량적으로 확인했습니다. 
        라운드가 거듭될수록 단순한 맛뿐만 아니라, 미션의 성격(개인/팀)에 따라 장르별 생존 유불리가 달라짐을 확인할 수 있었습니다.
        """)


# --- Main App Structure ---
def main():
    st.sidebar.title("🍳 흑백요리사 분석 (Ver.2)")
    st.sidebar.markdown("---")
    
    # Navigation
    menu = st.sidebar.radio(
        "분석 메뉴 선택",
        ["1. 쉐프 검색 트렌드", "3-1. 요리 장르별 생존율 보고서", "3-2. 심사위원 서바이벌 예측"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("흑백요리사 데이터 분석 대시보드입니다.")

    # Routing
    if menu == "1. 쉐프 검색 트렌드":
        show_trend_analysis()
    elif menu == "3-1. 요리 장르별 생존율 보고서":
        show_genre_survival_report()
    elif menu == "3-2. 심사위원 서바이벌 예측":
        show_survival_analysis()

if __name__ == "__main__":
    main()

