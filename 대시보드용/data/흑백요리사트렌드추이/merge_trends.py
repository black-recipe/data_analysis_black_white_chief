import pandas as pd
import os
from pathlib import Path

# 폴더 경로
folder_path = Path(__file__).parent

# 모든 CSV 파일 찾기 (이미지 파일과 파이썬 파일 제외)
csv_files = [f for f in os.listdir(folder_path)
             if f.endswith('.csv') and f != 'merged_trends.csv']

print(f"발견된 CSV 파일 수: {len(csv_files)}")

# 데이터를 저장할 딕셔너리
all_data = {}

# 각 CSV 파일 읽기
for csv_file in csv_files:
    file_path = folder_path / csv_file

    try:
        # 파일 읽기 (BOM 처리를 위해 encoding 지정)
        df = pd.read_csv(file_path, encoding='utf-8-sig')

        # 첫 행이 카테고리 정보인 경우 건너뛰기
        if df.iloc[0, 0] and '카테고리' in str(df.iloc[0, 0]):
            df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=2)

        # 컬럼명 정리
        df.columns = df.columns.str.strip()

        # 첫 번째 컬럼을 날짜로 사용
        date_col = df.columns[0]

        # 두 번째 컬럼명에서 출연자 이름과 소스 정보 추출
        value_col = df.columns[1]

        # 파일명에서 출연자와 소스 정보 추출
        file_name = csv_file.replace('.csv', '')

        # 영문_소스 형태인지 확인
        if '_' in file_name:
            parts = file_name.split('_')
            person = parts[0]
            source = parts[1] if len(parts) > 1 else 'unknown'

            # 영문 약자를 한글 이름으로 매핑
            name_mapping = {
                'akrl': '아기맹수',
                'choi': '최강록',
                'hoo': '후덕죽',
                'im': '임성근',
                'jeong': '정호영',
                'sam': '샘킴',
                'seon': '선재스님',
                'son': '손종원',
                'yo': '요리괴물',
                'yoon': '윤준모'
            }
            person_name = name_mapping.get(person, person)
        else:
            # 한글 이름 파일
            person_name = file_name
            # 값 컬럼명에서 소스 추정 (실제 데이터를 보고 판단 필요)
            source = 'google'  # 한글 파일은 구글 트렌드로 가정

        # 컬럼명 생성
        col_name = f"{person_name}_{source}"

        # 날짜 컬럼 이름 통일
        df = df.rename(columns={date_col: '날짜', value_col: col_name})

        # 날짜 형식 변환
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')

        # 빈 행 제거
        df = df.dropna(subset=['날짜'])

        # all_data에 추가
        all_data[col_name] = df[['날짜', col_name]].set_index('날짜')

        print(f"✓ {csv_file} -> {col_name}")

    except Exception as e:
        print(f"✗ {csv_file} 읽기 실패: {e}")

# 모든 데이터프레임 병합
if all_data:
    merged_df = pd.concat(all_data.values(), axis=1, join='outer')

    # 인덱스를 컬럼으로 변환
    merged_df = merged_df.reset_index()

    # 날짜로 정렬
    merged_df = merged_df.sort_values('날짜')

    # 날짜를 문자열로 변환 (YYYY-MM-DD 형식)
    merged_df['날짜'] = merged_df['날짜'].dt.strftime('%Y-%m-%d')

    # CSV 파일로 저장
    output_file = folder_path / 'merged_trends.csv'
    merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n병합 완료!")
    print(f"출력 파일: {output_file}")
    print(f"총 행 수: {len(merged_df)}")
    print(f"총 컬럼 수: {len(merged_df.columns)}")
    print(f"\n컬럼 목록:")
    for col in merged_df.columns:
        print(f"  - {col}")
else:
    print("병합할 데이터가 없습니다.")
