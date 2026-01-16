
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

file_path = '셰프서바이벌결과요약.csv'
try:
    df = pd.read_csv(file_path)
    df_clean = df[df['food'] != '-'].copy()
    
    print(f"Total rows after cleaning: {len(df_clean)}")
    
    features = ['how_cook', 'food_category', 'ingrediant', 'temperature']
    
    for judge, target in [('An', 'an'), ('Baek', 'back')]:
        print(f"\n--- Analyzing {judge} ---")
        if target == 'an':
            sub = df_clean[df_clean['is_an'] == 1]
        else:
            sub = df_clean[df_clean['is_back'] == 1]
            
        print(f"N = {len(sub)}")
        
        X = pd.get_dummies(sub[features], drop_first=True, dtype=int)
        X = sm.add_constant(X)
        y = sub[target]
        
        try:
            model = sm.Logit(y, X).fit(disp=0)
            print(model.summary())
            
            print("Odds Ratios:")
            print(np.exp(model.params).sort_values(ascending=False).head(5))
            print(np.exp(model.params).sort_values(ascending=True).head(5))
            
        except Exception as e:
            print(f"Error: {e}")

except Exception as e:
    print(e)
