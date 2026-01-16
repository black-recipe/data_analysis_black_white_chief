import pandas as pd
from pathlib import Path

# 파일 경로
folder_path = Path(__file__).parent
input_file = folder_path / 'merged_trends.csv'
output_file = folder_path / 'merged_trends_long.csv'

# 데이터 읽기
df = pd.read_csv(input_file, encoding='utf-8-sig')

print(f"원본 데이터 형태: {df.shape}")
print(f"컬럼 수: {len(df.columns)}")

# Long format으로 변환
df_long = df.melt(
    id_vars=['날짜'],
    var_name='출연자_소스',
    value_name='값'
)

# 출연자와 소스 분리
df_long[['출연자', '소스']] = df_long['출연자_소스'].str.rsplit('_', n=1, expand=True)

# 불필요한 컬럼 제거
df_long = df_long.drop('출연자_소스', axis=1)

# 컬럼 순서 정리
df_long = df_long[['날짜', '출연자', '소스', '값']]

# NaN 값 처리 (옵션: 제거하거나 0으로 채우기)
# df_long = df_long.dropna(subset=['값'])  # NaN 제거
df_long['값'] = df_long['값'].fillna(0)  # NaN을 0으로 채우기

# 날짜로 정렬
df_long = df_long.sort_values(['날짜', '출연자', '소스']).reset_index(drop=True)

# 저장
df_long.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\nReshape 완료!")
print(f"Long format 데이터 형태: {df_long.shape}")
print(f"출력 파일: {output_file}")

# 샘플 데이터 출력
print(f"\n샘플 데이터 (처음 15행):")
print(df_long.head(15))

print(f"\n출연자 목록:")
print(df_long['출연자'].unique())

print(f"\n소스 목록:")
print(df_long['소스'].unique())

print(f"\n날짜 범위:")
print(f"시작: {df_long['날짜'].min()}")
print(f"종료: {df_long['날짜'].max()}")
