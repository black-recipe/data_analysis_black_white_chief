
import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager, rc
import os

# --- Page Config ---
st.set_page_config(
    page_title="흑백요리사 분석 보고서",
    page_icon="🍳",
    layout="wide"
)

# --- Korean Font Setup ---
def set_korean_font():
    import matplotlib.font_manager as fm
    import platform

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

# --- Sidebar: Extensibility Answer ---
with st.sidebar:
    st.header("ℹ️ 앱 확장성 정보")
    st.info(
        """
        **Q: 다른 분석 파일도 나중에 합칠 수 있나요?**
        
        **A: 네, 가능합니다!**
        
        Streamlit은 **Multipage App** 기능을 지원합니다.
        
        1. `pages/` 폴더를 만들고,
        2. 그 안에 다른 분석 스크립트(예: `1_other_analysis.py`)를 넣으면,
        3. 자동으로 사이드바에 페이지 메뉴가 생성되어 여러 보고서를 하나의 앱에서 통합 관리할 수 있습니다.
        
        또는 `st.navigation` (Streamlit 1.36+) 기능을 사용하여 더욱 유연하게 페이지 구조를 설계할 수도 있습니다.
        """
    )
    st.markdown("---")
    st.write("Data Analysis by Agent")

# --- Title & Intro ---
st.title("🍳 흑백요리사 시즌2 심사위원 합격 예측 분석")
st.markdown("""
본 분석은 **'흑백요리사 시즌2'**의 라운드별 요리 데이터를 바탕으로, 
두 심사위원(**백종원**, **안성재**)의 심사 성향과 합격 기준을 통계적 기법(로지스틱 회귀분석)으로 분석한 결과입니다.
""")

# --- Data Loading ---
@st.cache_data
def load_data():
    file_path = '3번문제완성본.csv'
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path)
    # Preprocessing
    df_clean = df[df['food'] != '-'].copy()
    return df_clean

df = load_data()

if df is None:
    st.error("데이터 파일('3번문제완성본.csv')을 찾을 수 없습니다.")
    st.stop()

# --- Functions for Analysis ---
def plot_pass_rate(df, judge_col, judge_name):
    features = ['how_cook', 'food_category', 'ingrediant', 'temperature']
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    # fig.suptitle(f'{judge_name} 심사 합격률 분석', fontsize=16)
    
    for i, col in enumerate(features):
        row, col_idx = divmod(i, 2)
        if col in df.columns:
            # Calculate pass rate
            pass_rate = df.groupby(col)[judge_col].mean().sort_values(ascending=False)
            sns.barplot(x=pass_rate.index, y=pass_rate.values, ax=axes[row, col_idx], palette='viridis')
            axes[row, col_idx].set_title(f'{col}별 합격률')
            axes[row, col_idx].set_ylim(0, 1.0)
            axes[row, col_idx].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    return fig

def run_logistic_regression(df, target_col):
    # Filter targets
    if target_col == 'an':
        sub_df = df[df['is_an'] == 1].copy()
    else:
        sub_df = df[df['is_back'] == 1].copy()
        
    features = ['how_cook', 'food_category', 'ingrediant', 'temperature']
    X = pd.get_dummies(sub_df[features], drop_first=True)
    X = X.astype(int)
    y = sub_df[target_col]
    X = sm.add_constant(X)
    
    try:
        model = sm.Logit(y, X).fit(disp=0)
        return model, X, y
    except Exception as e:
        return None, None, None

def calculate_vif(X):
    # Calculate VIF for each feature
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
    return vif_data.sort_values(by="VIF", ascending=False)

def create_summary_df(model):
    if model is None:
        return pd.DataFrame()
    
    # Extract coefficients, p-values, odds ratios
    summary_df = pd.DataFrame({
        "Coef": model.params,
        "P-value": model.pvalues,
        "Odds Ratio": np.exp(model.params)
    })
    
    # Sort by P-value to highlight significant variables
    return summary_df.sort_values(by="P-value")

# --- Tab Layout ---
tab1, tab2, tab3 = st.tabs(["📊 데이터 탐색 (EDA)", "📈 회귀분석 결과", "💡 공략 리포트"])

with tab1:
    st.header("심사위원별 합격률 시각화")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("안성재 심사위원")
        fig_an = plot_pass_rate(df[df['is_an'] == 1], 'an', '안성재')
        st.pyplot(fig_an)
        
    with col2:
        st.subheader("백종원 심사위원")
        fig_back = plot_pass_rate(df[df['is_back'] == 1], 'back', '백종원')
        st.pyplot(fig_back)

with tab2:
    st.header("로지스틱 회귀분석 결과")
    
    col_l, col_r = st.columns(2)
    
    # Ahn Analysis
    model_an, X_an, y_an = run_logistic_regression(df, 'an')
    summary_an = create_summary_df(model_an)
    
    with col_l:
        st.subheader("🔹 안성재 심사위원 모델")
        st.write("P-value가 0.05 미만인 변수가 통계적으로 유의미합니다.")
        st.dataframe(summary_an.style.map(lambda x: 'background-color: yellow' if x < 0.05 else '', subset=['P-value']), height=400)
        
        # VIF Analysis
        if X_an is not None:
            with st.expander("다중공선성(VIF) 진단"):
                vif_an = calculate_vif(X_an)
                st.dataframe(vif_an.style.map(lambda x: 'color: red' if x > 10 else '', subset=['VIF']))
                st.caption("VIF가 10 이상이면 다중공선성이 높음")

        # Residual Plot (Simplified)
        if model_an is not None:
            st.markdown("**잔차(Residuals) 분석**")
            residuals = model_an.resid_pearson
            # Fitted vs Residuals
            fig_res, ax = plt.subplots(figsize=(8, 4))
            sns.regplot(x=model_an.predict(), y=residuals, lowess=True, 
                        line_kws={'color': 'red'}, scatter_kws={'alpha': 0.5}, ax=ax)
            ax.set_title("Residuals vs Fitted (안성재)")
            ax.axhline(0, color='black', linestyle='--')
            ax.set_xlabel("Fitted Values")
            ax.set_ylabel("Pearson Residuals")
            st.pyplot(fig_res)

    # Baek Analysis
    model_back, X_back, y_back = run_logistic_regression(df, 'back')
    summary_back = create_summary_df(model_back)

    with col_r:
        st.subheader("🔸 백종원 심사위원 모델")
        st.write("P-value가 0.05 미만인 변수가 통계적으로 유의미합니다.")
        st.dataframe(summary_back.style.map(lambda x: 'background-color: yellow' if x < 0.05 else '', subset=['P-value']), height=400)
        
        # VIF Analysis
        if X_back is not None:
            with st.expander("다중공선성(VIF) 진단"):
                vif_back = calculate_vif(X_back)
                st.dataframe(vif_back.style.map(lambda x: 'color: red' if x > 10 else '', subset=['VIF']))
                st.caption("VIF가 10 이상이면 다중공선성이 높음")
        
        # Residual Plot (Simplified)
        if model_back is not None:
            st.markdown("**잔차(Residuals) 분석**")
            residuals_b = model_back.resid_pearson
            fig_res_b, ax_b = plt.subplots(figsize=(8, 4))
            sns.regplot(x=model_back.predict(), y=residuals_b, lowess=True, 
                        line_kws={'color': 'red'}, scatter_kws={'alpha': 0.5}, ax=ax_b)
            ax_b.set_title("Residuals vs Fitted (백종원)")
            ax_b.axhline(0, color='black', linestyle='--')
            ax_b.set_xlabel("Fitted Values")
            ax_b.set_ylabel("Pearson Residuals")
            st.pyplot(fig_res_b)

with tab3:
    st.header("🏁 최종 공략 리포트")
    
    # Load content from markdown file
    # We will manually format it beautifully here using Streamlit components rather than just dumping raw markdown
    
    col_final_1, col_final_2 = st.columns(2)
    
    with col_final_1:
        st.markdown("### 🤵 안성재 심사위원: '디테일과 깊은 맛'")
        st.success("**✅ 필승 전략**")
        st.markdown("""
        - **조림(Braising)** 🥇: 합격 확률을 가장 유의미하게 높이는 조리법
        - **볶음 & 한식/퓨전**: 상대적으로 높은 합격률
        """)
        
        st.error("**❌ 필패 전략**")
        st.markdown("""
        - **튀김(Frying)** 🚫: 합격률 9%. 디테일 부족 평가 가능성
        - **디저트**: 식사로서의 완성도 중시
        """)
        st.info("💡 **전략**: 단순 튀김은 피하고, 정성이 들어간 한식 조림이나 퓨전 요리로 승부하라.")

    with col_final_2:
        st.markdown("### 👨‍🍳 백종원 심사위원: '직관적인 맛과 대중성'")
        st.success("**✅ 필승 전략**")
        st.markdown("""
        - **튀김(Frying)** 🍤: 합격률 67%. 잘 튀겨진 요리에 높은 점수
        - **중식 & 양식**: 강한 불맛이나 튀김 기술 선호
        - **조림 & 스팀**: 긍정적 평가
        """)
        
        st.warning("**⚠️ 주의 전략**")
        st.markdown("""
        - **구이**: 합격률 35%. 단순 구이보다 소스나 조리법 임팩트 필요
        """)
        st.info("💡 **전략**: 중식 스타일 튀김이나 소스 맛이 확실한 퓨전/양식 요리로 직관적인 맛을 어필하라.")
    
    st.divider()
    
    st.markdown("### 📝 심사위원 비교 요약")
    
    comparison_data = {
        "항목": ["선호 조리법", "비선호 조리법", "유리한 장르", "핵심 키워드"],
        "안성재 (Ahn)": ["조림, 볶음", "튀김 (극혐), 삶기", "퓨전음식, 한식", "#디테일 #깊이 #조림"],
        "백종원 (Baek)": ["튀김, 스팀, 조림", "구이, 삶기", "중식, 양식, 퓨전", "#직관적맛 #대중성 #튀김"]
    }
    st.table(pd.DataFrame(comparison_data).set_index("항목"))

