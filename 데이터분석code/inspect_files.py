import pandas as pd
import os

base_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\흑백요리사트렌드추이"

files_to_check = [
    "im_datalab.csv", 
    "im_google.csv",
    "choi_google.csv",
    "choi_datalab.xlsx",
    "아기맹수_네이버.csv",
    "아기맹수_구글.csv"
]

for filename in files_to_check:
    file_path = os.path.join(base_path, filename)
    print(f"\n--- Checking {filename} ---")
    try:
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(file_path)
            except Exception:
                 # Try with different encoding if default fails
                df = pd.read_csv(file_path, encoding='cp949')
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        
        print("Columns:", df.columns.tolist())
        print("Head:")
        print(df.head(3))
    except Exception as e:
        print(f"Error reading {filename}: {e}")
