"""
카카오 API를 이용한 역지오코딩 (Reverse Geocoding)
경도, 위도를 도로명 주소로 변환하는 스크립트
"""

import pandas as pd
import requests
import time
from tqdm import tqdm

# ============================================================
# 카카오 REST API 키 설정
# https://developers.kakao.com 에서 발급받은 REST API 키를 입력하세요
# ============================================================
KAKAO_API_KEY = "4f6c32c41ec2eea6d42afdc7430c769b"  # 여기에 본인의 API 키를 입력하세요


def reverse_geocode_kakao(lon: float, lat: float, api_key: str) -> dict:
    """
    카카오 로컬 API를 이용하여 경도/위도를 주소로 변환합니다.
    
    Args:
        lon: 경도 (longitude)
        lat: 위도 (latitude)
        api_key: 카카오 REST API 키
    
    Returns:
        dict: 도로명 주소, 지번 주소 정보가 담긴 딕셔너리
    """
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    
    headers = {
        "Authorization": f"KakaoAK {api_key}"
    }
    
    params = {
        "x": lon,  # 경도
        "y": lat,  # 위도
        "input_coord": "WGS84"  # 좌표계 (기본값: WGS84)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("documents"):
            doc = result["documents"][0]
            
            # 도로명 주소
            road_address = None
            if doc.get("road_address"):
                road_address = doc["road_address"]["address_name"]
            
            # 지번 주소
            address = None
            if doc.get("address"):
                address = doc["address"]["address_name"]
            
            return {
                "road_address": road_address,  # 도로명 주소
                "address": address,            # 지번 주소
                "success": True
            }
        else:
            return {
                "road_address": None,
                "address": None,
                "success": False
            }
    
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        return {
            "road_address": None,
            "address": None,
            "success": False
        }


def process_csv_with_geocoding(input_path: str, output_path: str, api_key: str):
    """
    CSV 파일을 읽어 역지오코딩을 수행하고 결과를 저장합니다.
    
    Args:
        input_path: 입력 CSV 파일 경로
        output_path: 출력 CSV 파일 경로
        api_key: 카카오 REST API 키
    """
    # CSV 파일 로드
    print(f"📂 CSV 파일 로드 중: {input_path}")
    df = pd.read_csv(input_path, encoding='utf-8-sig')
    
    print(f"📊 총 {len(df)}개의 레코드가 있습니다.")
    print(f"📌 컬럼: {list(df.columns)}")
    
    # 결과를 저장할 새로운 컬럼 추가
    df['road_address'] = None  # 도로명 주소
    df['jibun_address'] = None  # 지번 주소
    df['geocoding_success'] = False  # 변환 성공 여부
    
    # 각 행에 대해 역지오코딩 수행
    print("\n🔄 역지오코딩 시작...")
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="주소 변환 중"):
        lat = row['lat']
        lon = row['lon']
        
        # lat, lon이 유효한 경우에만 처리
        if pd.notna(lat) and pd.notna(lon):
            result = reverse_geocode_kakao(lon, lat, api_key)
            
            df.at[idx, 'road_address'] = result['road_address']
            df.at[idx, 'jibun_address'] = result['address']
            df.at[idx, 'geocoding_success'] = result['success']
            
            # API 호출 제한을 피하기 위해 잠시 대기 (초당 10건 제한)
            time.sleep(0.1)
        else:
            print(f"⚠️ 행 {idx}: 위도/경도 값이 없습니다. (restaurant: {row.get('restaurant', 'N/A')})")
    
    # 결과 저장
    print(f"\n💾 결과 저장 중: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    # 결과 요약
    success_count = df['geocoding_success'].sum()
    print(f"\n✅ 완료!")
    print(f"   - 성공: {success_count}건")
    print(f"   - 실패: {len(df) - success_count}건")
    
    # 결과 미리보기
    print("\n📋 결과 미리보기 (상위 10개):")
    preview_columns = ['restaurant', 'lat', 'lon', 'road_address', 'jibun_address']
    print(df[preview_columns].head(10).to_string())
    
    return df


def main():
    # 파일 경로 설정
    input_file = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\캐치테이블_가게정보.csv"
    output_file = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\캐치테이블_가게정보_주소변환.csv"
    
    # API 키 확인
    if KAKAO_API_KEY == "YOUR_KAKAO_REST_API_KEY":
        print("=" * 60)
        print("⚠️  카카오 REST API 키를 설정해주세요!")
        print("=" * 60)
        print("\n1. https://developers.kakao.com 에 접속합니다.")
        print("2. 로그인 후 '내 애플리케이션'에서 앱을 생성합니다.")
        print("3. 앱 설정 > 앱 키 > REST API 키를 복사합니다.")
        print("4. 이 스크립트의 KAKAO_API_KEY 변수에 붙여넣기합니다.")
        print("\n" + "=" * 60)
        return
    
    # 역지오코딩 실행
    result_df = process_csv_with_geocoding(input_file, output_file, KAKAO_API_KEY)
    

if __name__ == "__main__":
    main()
