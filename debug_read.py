import pandas as pd
file_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\트렌드분석\샘킴_google.csv"

print("--- Reading with header=1 ---")
try:
    df = pd.read_csv(file_path, header=1)
    print(df.columns)
    print(df.head(2))
except Exception as e:
    print(e)

print("\n--- Reading with header=2 ---")
try:
    df = pd.read_csv(file_path, header=2)
    print(df.columns)
    print(df.head(2))
except Exception as e:
    print(e)
