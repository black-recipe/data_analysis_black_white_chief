# -*- coding: utf-8 -*-
import os
import json
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 필수 키 확인
if not all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, SUPABASE_URL, SUPABASE_KEY]):
    print("Error: .env 파일에 필요한 키(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, SUPABASE_URL, SUPABASE_KEY)가 누락되었습니다.")
    exit(1)

# Supabase 헤더
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def fetch_keywords():
    """Supabase에서 키워드 그룹 조회"""
    # name, keyword 컬럼 조회
    url = f"{SUPABASE_URL}/rest/v1/chief_trend_keyword?select=name,keyword"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching keywords: {response.text}")
        return []
    return response.json()

def save_to_supabase(data_list):
    """트렌드 데이터를 Supabase에 저장"""
    if not data_list:
        return
    
    url = f"{SUPABASE_URL}/rest/v1/chief_trend_value"
    
    # 데이터가 많을 경우를 대비해 100개씩 끊어서 저장 권장되나, 
    # 일단 요구사항에 맞춰 단순 구현. (에러 발생 시 분할 로직 추가 고려)
    try:
        response = requests.post(url, headers=headers, json=data_list)
        if response.status_code == 201:
            print(f"✅ Successfully saved {len(data_list)} records.")
        else:
            print(f"❌ Error saving data: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ Exception during save: {e}")

def main():
    print("=== Start Collecting Naver Trend Data ===")
    
    # 1. 키워드 가져오기
    keywords_data = fetch_keywords()
    if not keywords_data:
        print("No keywords found in 'chief_trend_keyword' table.")
        return

    # 2. 키워드 그룹핑 (name 기준으로 keyword 모으기)
    groups_map = {}
    for item in keywords_data:
        name = item.get('name')
        kw = item.get('keyword')
        
        if not name or not kw:
            continue
            
        if name not in groups_map:
            groups_map[name] = []
        
        # 키워드가 콤마로 구분되어 있을 경우 처리, 아니면 단일 추가
        if ',' in kw:
            split_kws = [k.strip() for k in kw.split(',') if k.strip()]
            groups_map[name].extend(split_kws)
        else:
            groups_map[name].append(kw.strip())

    # 그룹별 키워드 리스트 중복 제거
    all_groups = []
    for name, kws in groups_map.items():
        unique_kws = list(set(kws))
        if not unique_kws:
            continue
        all_groups.append({
            "groupName": name,
            "keywords": unique_kws
        })
    
    print(f"Total groups found: {len(all_groups)}")

    # 3. 네이버 API 요청 (최대 5개 그룹씩)
    chunk_size = 5
    for i in range(0, len(all_groups), chunk_size):
        chunk = all_groups[i:i+chunk_size]
        group_names = [g['groupName'] for g in chunk]
        
        print(f"Requesting data for groups: {group_names}")
        
        body = {
            "startDate": "2025-12-09",
            "endDate": "2026-01-20",
            "timeUnit": "date",
            "keywordGroups": chunk,
            # device, gender, ages는 설정 안 함 (전체)
        }
        
        naver_url = "https://openapi.naver.com/v1/datalab/search"
        naver_headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
            "Content-Type": "application/json"
        }
        
        try:
            res = requests.post(naver_url, headers=naver_headers, json=body)
            
            if res.status_code == 200:
                result_json = res.json()
                to_insert = []
                
                # 결과 파싱
                # "results": [{"title": "한글", "keywords": [...], "data": [{"period": "...", "ratio": ...}, ...]}, ...]
                for item in result_json.get('results', []):
                    title = item.get('title') # 출연자 이름
                    
                    for data_point in item.get('data', []):
                        period = data_point.get('period') # 날짜
                        ratio = data_point.get('ratio')   # 값
                        
                        # Supabase 테이블 컬럼 매핑 (한글 컬럼명 사용)
                        row = {
                            "출연자": title,
                            "날짜": period,
                            "값": ratio,
                            "소스": "datalab"
                        }
                        to_insert.append(row)
                
                # 저장
                if to_insert:
                    save_to_supabase(to_insert)
                else:
                    print("No data points returned from Naver API.")
                    
            else:
                print(f"❌ Naver API Error: {res.status_code}")
                try:
                    print(res.json())
                except:
                    print(res.text)

        except Exception as e:
            print(f"❌ Error during Naver API request: {e}")

    print("=== Done ===")

if __name__ == "__main__":
    main()
