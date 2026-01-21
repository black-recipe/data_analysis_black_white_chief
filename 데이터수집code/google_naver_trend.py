
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import glob
import os
from matplotlib import font_manager, rc
import platform

# 1. Font Settings for Korean
def set_korean_font():
    system_name = platform.system()
    if system_name == "Windows":
        # Check standard Windows font paths
        font_path = "c:/Windows/Fonts/malgun.ttf"
        try:
            font_name = font_manager.FontProperties(fname=font_path).get_name()
            rc('font', family=font_name)
        except:
            # Fallback if specific file not found
            plt.rcParams['font.family'] = 'Malgun Gothic'
    elif system_name == "Darwin":  # Mac
        rc('font', family="AppleGothic")
    else:  # Linux
        rc('font', family="NanumGothic")
        
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# 2. Path Setup
base_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\흑백요리사트렌드추이"
datalab_files = glob.glob(os.path.join(base_path, "*_datalab.csv"))

all_data = []

# 3. Process Files
for f_naver in datalab_files:
    try:
        # Extract Chef ID (e.g., 'akrl' from 'akrl_datalab.csv')
        filename = os.path.basename(f_naver)
        chef_id = filename.replace("_datalab.csv", "")
        
        # Determine corresponding Google file
        f_google = os.path.join(base_path, f"{chef_id}_google.csv")
        
        if not os.path.exists(f_google):
            print(f"Warning: Google file not found for {chef_id}")
            continue
            
        # Read Naver Data
        try:
            df_naver = pd.read_csv(f_naver, encoding='utf-8')
        except UnicodeDecodeError:
            df_naver = pd.read_csv(f_naver, encoding='cp949')
            
        # Validating structure
        if df_naver.shape[1] < 2:
            continue
            
        chef_name = df_naver.columns[1] # Assume 2nd column is the chef name
        
        # Standardize Naver
        df_naver = df_naver.rename(columns={df_naver.columns[0]: 'Date', df_naver.columns[1]: 'Value'})
        df_naver['Source'] = 'Naver'
        df_naver['Chef'] = chef_name
        
        # Read Google Data
        try:
            df_google = pd.read_csv(f_google, encoding='utf-8')
        except UnicodeDecodeError:
            df_google = pd.read_csv(f_google, encoding='cp949')
            
        if df_google.shape[1] < 2:
            continue
            
        # Standardize Google
        df_google = df_google.rename(columns={df_google.columns[0]: 'Date', df_google.columns[1]: 'Value'})
        df_google['Source'] = 'Google'
        df_google['Chef'] = chef_name # Use the name from Naver file to ensure consistency
        
        # Clean Data (Drop NaNs)
        df_naver = df_naver.dropna(subset=['Value'])
        df_google = df_google.dropna(subset=['Value'])
        
        # Ensure numeric
        df_naver['Value'] = pd.to_numeric(df_naver['Value'], errors='coerce')
        df_google['Value'] = pd.to_numeric(df_google['Value'], errors='coerce')
        
        all_data.extend([df_naver, df_google])
        
    except Exception as e:
        print(f"Error processing {f_naver}: {e}")

# 4. Combine
if not all_data:
    print("No data found.")
    exit()

final_df = pd.concat(all_data, ignore_index=True)

# 5. Convert Date
final_df['Date'] = pd.to_datetime(final_df['Date'])

# 6. Plotting
# Using FacetGrid to show all chefs in one figure (sub-charts)
# Adjust col_wrap based on number of chefs (approx 10 -> 3 or 4 columns)
g = sns.relplot(
    data=final_df,
    x="Date", y="Value",
    hue="Source",
    col="Chef",
    kind="line",
    col_wrap=4,
    height=4,
    aspect=1.5,
    facet_kws={'sharey': False, 'sharex': True}
)

g.fig.suptitle('흑백요리사 쉐프별 검색 트렌드 (Naver vs Google)', size=16)
g.fig.subplots_adjust(top=0.92) # Make room for title

# Rotate x-axis labels for better readability
for axes in g.axes.flat:
    _ = axes.tick_params(axis='x', rotation=45)

# Save
output_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\chef_trends_combined.png"
g.savefig(output_path)
print(f"Plot saved to {output_path}")
