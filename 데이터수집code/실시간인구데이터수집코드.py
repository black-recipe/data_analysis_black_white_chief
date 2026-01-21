import requests
import pandas as pd
import datetime
import time
import os
from tqdm import tqdm

# ==============================================================================
# Seoul IoT Data Continuous Collection Script
# ==============================================================================
# Logic:
# 1. Check if the output file exists.
# 2. If exists, identify the latest SENSING_TIME collected.
# 3. Fetch data from API (Latest first).
# 4. Stop fetching if we encounter data older than or equal to the latest collected time.
# 5. Append new data to the file.
# 6. Convert English District names to Korean using provided mapping.
# ==============================================================================

# Configuration
API_KEY = os.environ.get("API_KEY")
SERVICE = "IotVdata018"
BASE_URL = "http://openapi.seoul.go.kr:8088/{key}/json/{service}/{start}/{end}/"
TARGET_START_DATE = datetime.datetime(2025, 12, 9) # Fallback if no file exists
OUTPUT_FILE = "seoul_floating_pop_raw3.csv"

# ==============================================================================
# MAPPINGS (English -> Korean)
# ==============================================================================
 
# 1. Gu (Autonomous District) Mapping - Standard 25 Districts
GU_MAPPING_RAW = {
    'Gangnam-gu': '강남구', 'Gangdong-gu': '강동구', 'Gangbuk-gu': '강북구',
    'Gangseo-gu': '강서구', 'Gwanak-gu': '관악구', 'Gwangjin-gu': '광진구',
    'Guro-gu': '구로구', 'Geumcheon-gu': '금천구', 'Nowon-gu': '노원구',
    'Dobong-gu': '도봉구', 'Dongdaemun-gu': '동대문구', 'Dongjak-gu': '동작구',
    'Mapo-gu': '마포구', 'Seodaemun-gu': '서대문구', 'Seocho-gu': '서초구',
    'Seongdong-gu': '성동구', 'Seongbuk-gu': '성북구', 'Songpa-gu': '송파구',
    'Yangcheon-gu': '양천구', 'Yeongdeungpo-gu': '영등포구', 'Yongsan-gu': '용산구',
    'Eunpyeong-gu': '은평구', 'Jongno-gu': '종로구', 'Jung-gu': '중구', 'Jungnang-gu': '중랑구'
}

# 2. Dong (Administrative District) Mapping - Reference: seoul_iot_flow_analysis.py
DONG_MAPPING_RAW = {
    '가락동': ['Garak-dong', 'Garak1-dong', 'Garak2-dong', 'Garakbon-dong'],
    '가산동': ['Gasan-dong'],
    '가양1동': ['Gayang1(il)-dong'],
    '개포2동': ['Gaepo2(i)-dong'],
    '경운동': ['Gyeongun-dong'],
    '고척2동': ['Gocheok2(i)-dong'],
    '공릉1동': ['Gongneung1(il)-dong'],
    '공항동': ['Gwanghang-dong', 'Gonghang-dong'],
    '광장동': ['Gwangjang-dong'],
    '광희동': ['Gwanghui-dong'],
    '구로4동': ['Gu-ro4(sa)-dong'],
    '구의1동': ['Guui1(il)-dong'],
    '구의2동': ['Guui2(i)-dong'],
    '낙성대동': ['Nakseongdae-dong'],
    '남영동': ['Namyeong-dong'],
    '남창동': ['Namchang-dong'],
    '녹번동': ['Nokbeon-dong'],
    '논현1동': ['Nonhyeon1(il)-dong'],
    '논현동': ['Nonhyeon-dong', 'Nonhyeon1-dong', 'Nonhyeon2-dong'],
    '누하동': ['Nuha-dong'],
    '대조동': ['Daejo-dong'],
    '대치2동': ['Daechi2(i)-dong'],
    '대치4동': ['Daechi4(sa)-dong'],
    '대치동': ['Daechi-dong', 'Daechi1-dong', 'Daechi2-dong', 'Daechi4-dong'],
    '대흥동': ['Daeheung-dong'],
    '도화동': ['Dohwa-dong'],
    '독산4동': ['Doksan4(sa)-dong'],
    '동교동': ['Donggyo-dong', 'Yeonnam-dong'],
    '동선동': ['Dongseon-dong'],
    '동숭동': ['Dongsung-dong', 'Ihwa-dong'],
    '둔촌1동': ['Dunchon1(il)-dong'],
    '등촌1동': ['Deungchon1(il)-dong'],
    '마곡동': ['Magok-dong'],
    '망원동': ['Mangwon-dong', 'Mangwon1(il)-dong', 'Mangwon2(i)-dong'],
    '명동1가': ['Myeong-dong'],
    '명륜4가': ['Myeongnyun-dong', 'Hyehwa-dong'],
    '목3동': ['Mok3(sam)-dong'],
    '묵2동': ['Muk2(i)-dong'],
    '문래동': ['Munllae-dong'],
    '문래동2가': ['Munlae-dong', 'Munlae2-ga'],
    '미아동': ['Mia-dong'],
    '반포2동': ['Banpo2(i)-dong'],
    '반포3동': ['Banpo3(sam)-dong'],
    '반포동': ['Banpo-dong', 'Banpo1-dong', 'Banpo2-dong', 'Banpo3-dong', 'Banpo4-dong', 'Banpubon-dong'],
    '방배2동': ['Bangbae2(i)-dong'],
    '방배동': ['Bangbae-dong', 'Bangbae1-dong', 'Bangbae4-dong', 'Bangbaeojoun-dong'],
    '방화1동': ['Banghwa1(il)-dong'],
    '방화3동': ['Banghwa3(sam)-dong'],
    '번3동': ['Beon3(sam)-dong'],
    '불광동': ['Bulgwang-dong', 'Bulgwang1-dong', 'Bulgwang2-dong'],
    '사당2동': ['Sadang2(i)-dong'],
    '삼성동': ['Samseong-dong', 'Samseong1-dong', 'Samseong2-dong'],
    '상계2동': ['Sanggye2(i)-dong'],
    '상도1동': ['Sang-do1(il)-dong'],
    '상도4동': ['Sang-do4(sa)-dong'],
    '서교동': ['Seogyo-dong'],
    '서초3동': ['Seocho3(sam)-dong'],
    '서초4동': ['Seocho4(sa)-dong'],
    '성내1동': ['Seongnae1(il)-dong'],
    '성산2동': ['Seongsan2(i)-dong'],
    '성수1가1동': ['Seongsu1ga1(il)-dong'],
    '성수1가2동': ['Seongsu1ga2(i)-dong'],
    '성수2가3동': ['Seongsu2ga3(sam)-dong'],
    '성수동1가': ['Seongsu-dong', 'Seongsu1-ga'],
    '성수동2가': ['Seongsu-dong', 'Seongsu2-ga'],
    '세종로': ['Sejongno', 'Sajik-dong'],
    '소격동': ['Sogyeok-dong', 'Samcheong-dong'],
    '소공동': ['Sogong-dong'],
    '송정동': ['Songjeong-dong'],
    '수서동': ['Suseo-dong'],
    '수유1동': ['Suyu1(il)-dong'],
    '수유3동': ['Suyu3(sam)-dong'],
    '시흥2동': ['Siheung2(i)-dong'],
    '신당동': ['Sindang-dong'],
    '신문로1가': ['Sinmunno-dong'],
    '신사동': ['Sinsa-dong'],
    '신원동': ['Sinwon-dong'],
    '신월1동': ['Sinwol1(il)-dong'],
    '신정4동': ['Sinjeong4(sa)-dong'],
    '신천동': ['Sincheon-dong', 'Jamsil4-dong', 'Jamsil6-dong'],
    '안국동': ['Anguk-dong'],
    '암사1동': ['Amsa1(il)-dong'],
    '압구정동': ['Apgujeong-dong'],
    '양재1동': ['Yangjae1(il)-dong'],
    '양재동': ['Yangjae-dong', 'Yangjae1-dong', 'Yangjae2-dong'],
    '여의도동': ['Yeouido-dong'],
    '역삼1동': ['Yeoksam1(il)-dong'],
    '역삼2동': ['Yeoksam2(i)-dong'],
    '역삼동': ['Yeoksam-dong', 'Yeoksam1-dong', 'Yeoksam2-dong'],
    '연희동': ['Yeonhui-dong'],
    '외발산동': ['Oebalsan-dong', 'Balsan-dong'],
    '용산동2가': ['Yongsan-dong', 'Yongsan2-ga'],
    '원서동': ['Wonseo-dong', 'Gahoe-dong'],
    '을지로3가': ['Euljiro-dong', 'Euljiro3-ga'],
    '이촌2동': ['Ichon2(i)-dong'],
    '이태원2동': ['Itaewon2(i)-dong'],
    '이태원동': ['Itaewon-dong', 'Itaewon1-dong', 'Itaewon2-dong'],
    '자양1동': ['Jayang1(il)-dong'],
    '잠실3동': ['Jamsil3(sam)-dong'],
    '잠실6동': ['Jamsil6(yuk)-dong'],
    '잠실동': ['Jamsil-dong', 'Jamsil2-dong', 'Jamsil3-dong', 'Jamsil7-dong', 'Jamsilbon-dong'],
    '잠원동': ['Jamwon-dong'],
    '장충동2가': ['Jangchung-dong', 'Jangchung2-ga'],
    '재동': ['Jae-dong', 'Gahoe-dong'],
    '종로1·2·3·4가동': ['Jong-ro1(il).2(i).3(sam).4(sa)-ga-dong'],
    '종로1·2·3가동': ['Jong-ro1(il).2(i).3(sam'],
    '중곡1동': ['Junggok1(il)-dong'],
    '중화2동': ['Junghwa2(i)-dong'],
    '중화동': ['Junghwa-dong', 'Junghwa1-dong', 'Junghwa2-dong'],
    '창1동': ['Chang1(il)-dong'],
    '창2동': ['Chang2(i)-dong'],
    '창3동': ['Chang3(sam)-dong'],
    '창성동': ['Changseong-dong'],
    '창신1동': ['Changsin1(il)-dong'],
    '천연동': ['Cheonyeon-dong'],
    '천호1동': ['Cheonho1(il)-dong'],
    '청담동': ['Cheongdam-dong'],
    '청운동': ['Cheongun-dong'],
    '청진동': ['Cheongjin-dong', 'Jongno1.2.3.4-ga-dong'],
    '한강로2가': ['Hangangno-dong', 'Hangangno2-ga'],
    '한남동': ['Hannam-dong'],
    '합정동': ['Hapjeong-dong'],
    '홍제3동': ['Hongje3(sam)-dong'],
    '화곡1동': ['Hwagok1(il)-dong'],
    '화양동': ['Hwayang-dong'],
    '회현동1가': ['Hoehyeon-dong', 'Hoehyeon1-ga'],
    '효자동': ['Hyoja-dong', 'Cheongunhyoja-dong'],
}

# Invert DONG_MAPPING for lookup: English(normalized) -> Korean
ENGLISH_TO_KOREAN_DONG = {}
for k_name, e_list in DONG_MAPPING_RAW.items():
    for e_name in e_list:
        norm_key = e_name.lower().replace(' ', '')
        ENGLISH_TO_KOREAN_DONG[norm_key] = k_name

# Invert GU_MAPPING: English(normalized) -> Korean
ENGLISH_TO_KOREAN_GU = {}
for e_name, k_name in GU_MAPPING_RAW.items():
    norm_key = e_name.lower().replace(' ', '')
    ENGLISH_TO_KOREAN_GU[norm_key] = k_name


def translate_name(name, mapping_dict):
    """
    Normalizes the input name and looks it up in the mapping dictionary.
    Returns the mapped Korean name if found, otherwise returns the original name.
    """
    if not name:
        return ""
    norm_name = name.lower().replace(' ', '')
    return mapping_dict.get(norm_name, name)


def get_url(start, end):
    return BASE_URL.format(key=API_KEY, service=SERVICE, start=start, end=end)

def parse_sensing_time(time_str):
    """
    Parses SENSING_TIME string into datetime object.
    Supports formats: 'YYYY-MM-DD_HH:MM:SS', 'YYYY-MM-DD HH:MM:SS'
    """
    if not time_str:
        return None
    try:
        return datetime.datetime.strptime(time_str, "%Y-%m-%d_%H:%M:%S")
    except ValueError:
        try:
            return datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

def fetch_data_batch(start_idx, end_idx, retries=3):
    url = get_url(start_idx, end_idx)
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if SERVICE in data and 'row' in data[SERVICE]:
                return data[SERVICE]['row']
            elif 'RESULT' in data and data['RESULT'].get('CODE') == 'INFO-200':
                return []
            else:
                if attempt == retries - 1:
                    print(f"[Error] API Response content issue: {data}")
                time.sleep(1)
                continue
                
        except Exception as e:
            if attempt == retries - 1:
                print(f"[Error] Failed to fetch {start_idx}-{end_idx} after {retries} attempts: {e}")
            time.sleep(2)
    return []

def get_latest_collected_time(file_path):
    """
    Reads the existing CSV to find the maximum SENSING_TIME.
    Returns TARGET_START_DATE if file doesn't exist or is empty.
    """
    if not os.path.exists(file_path):
        return TARGET_START_DATE
    
    try:
        print(f"[Info] Reading existing file to find latest data...")
        # Read only the SENSING_TIME column to save memory
        df = pd.read_csv(file_path, usecols=['SENSING_TIME'])
        if df.empty:
            return TARGET_START_DATE
            
        # Parse dates
        df['SENSING_TIME'] = pd.to_datetime(df['SENSING_TIME'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
        max_time = df['SENSING_TIME'].max()
        
        if pd.isnull(max_time):
            return TARGET_START_DATE
            
        return max_time
        
    except Exception as e:
        print(f"[Warning] Could not read existing file correctly: {e}. Starting from default date.")
        return TARGET_START_DATE

def main():
    print(f"=== Starting Seoul IoT Data Continuous Collection ===")
    
    # 1. Determine where to stop
    last_collected_time = get_latest_collected_time(OUTPUT_FILE)
    print(f"Latest collected time found: {last_collected_time}")
    print(f"New data will be collected until: {last_collected_time}")

    # Initialize file if not exists
    if not os.path.exists(OUTPUT_FILE):
        print(f"[Info] Output file not found. Creating {OUTPUT_FILE}")
        header = ["SENSING_TIME", "AUTONOMOUS_DISTRICT", "ADMINISTRATIVE_DISTRICT", "VISITOR_COUNT", "REG_DTTM"]
        pd.DataFrame(columns=header).to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    start_idx = 1
    batch_size = 1000
    collecting = True
    total_new_rows = 0
    
    pbar = tqdm(desc="Checking/Collecting Rows", unit="rows")
    
    while collecting:
        end_idx = start_idx + batch_size - 1
        rows = fetch_data_batch(start_idx, end_idx)
        
        if not rows:
            print("\n[Info] No more data returned from API.")
            break
            
        valid_rows = []
        stop_signal = False
        
        for row in rows:
            sensing_raw = row.get('SENSING_TIME') or row.get('REG_DTTM')
            dt = parse_sensing_time(sensing_raw)
            
            if not dt:
                continue

            # CRITICAL LOGIC: Stop if we hit data that is older or equal to what we have
            if dt <= last_collected_time:
                stop_signal = True
                # Don't break immediately if you want to ensure no mixed batches, 
                # but since API is descending, logic holds.
                # All subsequent rows in this batch (and future batches) will be older.
                break 
            
            # Convert to Korean
            raw_gu = row.get('AUTONOMOUS_DISTRICT', '')
            raw_dong = row.get('ADMINISTRATIVE_DISTRICT', '')
            
            # If the raw data is already Korean, the map logic returns it as is (since keys in map are normalized lower english).
            # But wait, if raw data is Korean, 'Korean'.lower() matches nothing in map keys usually (as keys are english).
            # So translate_name returns original, which is correct.
            kor_gu = translate_name(raw_gu, ENGLISH_TO_KOREAN_GU)
            kor_dong = translate_name(raw_dong, ENGLISH_TO_KOREAN_DONG)

            # If newer, keep it
            valid_rows.append({
                "SENSING_TIME": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "AUTONOMOUS_DISTRICT": kor_gu,
                "ADMINISTRATIVE_DISTRICT": kor_dong,
                "VISITOR_COUNT": row.get('VISITOR_COUNT', 0),
                "REG_DTTM": row.get('REG_DTTM', '')
            })
        
        # Append new rows (if any)
        if valid_rows:
            df_batch = pd.DataFrame(valid_rows)
            # Append mode
            df_batch.to_csv(OUTPUT_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            total_new_rows += len(valid_rows)
            pbar.update(len(valid_rows))
        
        if stop_signal:
            print(f"\n[Info] Encountered data from {last_collected_time} (or older). Stopping updates.")
            collecting = False
            break
            
        start_idx += batch_size
        time.sleep(0.1)

    pbar.close()
    print("="*50)
    print(f"Update Complete.")
    print(f"New rows added: {total_new_rows}")
    print(f"File updated: {os.path.abspath(OUTPUT_FILE)}")
    print("="*50)

if __name__ == "__main__":
    main()
