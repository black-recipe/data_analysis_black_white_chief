
import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

CHEF_MAPPING = {
    'akrl': '아기맹수', 'choi': '최강록', 'hoo': '후덕죽', 'im': '임성근',
    'jeong': '정호영', 'sam': '샘킴', 'seon': '선재스님', 'son': '손종원',
    'yo': '요리괴물', 'yoon': '윤주모'
}

def upload_csvs():
    # 경로 설정 (대시보드용/data/흑백요리사트렌드추이)
    base_path = os.path.join(os.getcwd(), '대시보드용', 'data', '흑백요리사트렌드추이')
    
    if not os.path.exists(base_path):
        print(f"Path not found: {base_path}")
        return

    all_data = []

    for prefix, chef_name in CHEF_MAPPING.items():
        for source_type, source_name in [('_google.csv', 'google'), ('_youtube.csv', 'youtube')]:
            f_name = f"{prefix}{source_type}"
            f_path = os.path.join(base_path, f_name)
            
            if not os.path.exists(f_path):
                print(f"Skipping {f_name}, not found.")
                continue
                
            try:
                try:
                    df = pd.read_csv(f_path, encoding='utf-8')
                except:
                    df = pd.read_csv(f_path, encoding='cp949')
                
                if df.shape[1] < 2:
                    continue

                # 첫 컬럼은 날짜, 두번째 컬럼은 값이라고 가정
                # CSV 구조에 따라 다를 수 있으나, 일반적으로 첫 컬럼 Date, 두번째 Value
                date_col = df.columns[0]
                val_col = df.columns[1]

                for _, row in df.iterrows():
                    val = row[val_col]
                    # 값이 숫자가 아니거나 NaN이면 스킵
                    try:
                        val = float(val)
                    except:
                        continue
                        
                    record = {
                        "출연자": chef_name,
                        "날짜": str(row[date_col]),
                        "값": val,
                        "소스": source_name
                    }
                    all_data.append(record)
                    
            except Exception as e:
                print(f"Error processing {f_name}: {e}")

    print(f"Found {len(all_data)} records to upload.")
    
    # Batch upload
    batch_size = 100
    url = f"{SUPABASE_URL}/rest/v1/chief_trend_value"
    
    for i in range(0, len(all_data), batch_size):
        batch = all_data[i:i+batch_size]
        try:
            res = requests.post(url, headers=headers, json=batch)
            if res.status_code == 201:
                print(f"Uploaded batch {i // batch_size + 1}")
            else:
                print(f"Error uploading batch {i}: {res.status_code} {res.text}")
        except Exception as e:
            print(f"Exception batch {i}: {e}")

if __name__ == "__main__":
    upload_csvs()
