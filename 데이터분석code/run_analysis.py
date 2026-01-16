
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings

warnings.filterwarnings('ignore')

# 데이터 로드
file_path = '3번문제완성본.csv'
try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    print(f"Error: {file_path} not found.")
    exit()

# 데이터 전처리
df_clean = df[df['food'] != '-'].copy()
features = ['how_cook', 'food_category', 'ingrediant', 'temperature']

# --- 함수 정의 ---

def run_logit_analysis(df, target_col, name, features):
    print(f"\n{'='*50}")
    print(f"  {name} 심사위원 분석 결과")
    print(f"{'='*50}")
    
    # 해당 심사위원이 심사한 데이터만 추출
    if target_col == 'an':
        sub_df = df[df['is_an'] == 1].copy()
    else:
        sub_df = df[df['is_back'] == 1].copy()
        
    print(f"데이터 개수: {len(sub_df)}")
    
    # One-Hot Encoding
    X = pd.get_dummies(sub_df[features], drop_first=True)
    X = X.astype(int)
    y = sub_df[target_col]
    
    # 상수항 추가
    X = sm.add_constant(X)
    
    # 모델 학습
    try:
        model = sm.Logit(y, X).fit(disp=0)
        # print(model.summary()) # 너무 길어서 생략하거나 요약본만 출력
        
        # 유의미한 변수 추출 (p < 0.1)
        p_values = model.pvalues
        sig_vars = p_values[p_values < 0.1].sort_values()
        
        if not sig_vars.empty:
            print("\n[유의미한 변수 (p < 0.1)]")
            for var, p in sig_vars.items():
                print(f"- {var}: p-value = {p:.4f}")
        else:
            print("\n[통계적으로 유의미한 변수(p<0.1)가 발견되지 않았습니다.]")
            
        # 오즈비(Odds Ratio) 확인
        params = model.params
        odds_ratios = np.exp(params)
        
        print("\n[합격 확률을 높이는 주요 요인 (Odds Ratio Top 5)]")
        print(odds_ratios.sort_values(ascending=False).head(5))
        
        print("\n[합격 확률을 낮추는 주요 요인 (Odds Ratio Bottom 5)]")
        print(odds_ratios.sort_values(ascending=True).head(5))
        
        return model, X
        
    except Exception as e:
        print(f"모델 학습 중 오류 발생: {e}")
        return None, None

def check_vif(X, name):
    print(f"\n--- {name} 모델 다중공선성(VIF) 진단 ---")
    vif_data = pd.DataFrame()
    vif_data["feature"] = X.columns
    try:
        vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
        print(vif_data.sort_values(by="VIF", ascending=False).head(5))
    except Exception as e:
        print(f"VIF 계산 중 오류 (상수항 등의 문제일 수 있음): {e}")

# --- 실행 ---

# 1. 안성재 분석
model_an, X_an = run_logit_analysis(df_clean, 'an', '안성재 (Ahn)', features)
if X_an is not None:
    check_vif(X_an, '안성재')

# 2. 백종원 분석
model_back, X_back = run_logit_analysis(df_clean, 'back', '백종원 (Baek)', features)
if X_back is not None:
    check_vif(X_back, '백종원')

