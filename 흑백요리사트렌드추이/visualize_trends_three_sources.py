"""
흑백요리사 트렌드 추이 시각화 스크립트
- 네이버 데이터랩, 구글 트렌드, 유튜브 트렌드 3가지 소스를 통합하여 시각화
- 유튜브는 빨간색, 네이버는 초록색, 구글은 파란색으로 표시
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import glob

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 쉐프 이름 매핑 (영문 프리픽스 -> 한글 이름)
CHEF_MAPPING = {
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

# 데이터 디렉토리
DATA_DIR = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\흑백요리사트렌드추이"


def convert_youtube_csv_to_standard_format():
    """유튜브 CSV 파일(한글이름.csv)을 표준 형식으로 변환하여 저장"""
    
    for prefix, chef_name in CHEF_MAPPING.items():
        youtube_file = os.path.join(DATA_DIR, f"{chef_name}.csv")
        output_file = os.path.join(DATA_DIR, f"{prefix}_youtube.csv")
        
        if os.path.exists(youtube_file):
            try:
                # 유튜브 파일 읽기 (앞의 2줄 메타데이터 스킵)
                df = pd.read_csv(youtube_file, skiprows=2, encoding='utf-8')
                
                # 컬럼명 정리
                df.columns = ['날짜', chef_name]
                
                # 빈 행 제거
                df = df.dropna(subset=['날짜'])
                df = df[df['날짜'].str.strip() != '']
                
                # 표준 형식으로 저장
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"변환 완료: {youtube_file} -> {output_file}")
                
            except Exception as e:
                print(f"오류 발생 ({youtube_file}): {e}")
        else:
            print(f"파일 없음: {youtube_file}")


def load_all_data():
    """모든 데이터를 로드하여 쉐프별로 정리"""
    
    all_data = {}
    
    for prefix, chef_name in CHEF_MAPPING.items():
        chef_data = {'chef_name': chef_name}
        
        # 네이버 데이터랩
        naver_file = os.path.join(DATA_DIR, f"{prefix}_datalab.csv")
        if os.path.exists(naver_file):
            df = pd.read_csv(naver_file, encoding='utf-8')
            df.columns = ['날짜', 'value']
            df['날짜'] = pd.to_datetime(df['날짜'])
            # NaN 값 제거
            df = df.dropna(subset=['value'])
            chef_data['naver'] = df
        
        # 구글 트렌드
        google_file = os.path.join(DATA_DIR, f"{prefix}_google.csv")
        if os.path.exists(google_file):
            df = pd.read_csv(google_file, encoding='utf-8')
            df.columns = ['날짜', 'value']
            df['날짜'] = pd.to_datetime(df['날짜'])
            chef_data['google'] = df
        
        # 유튜브 (변환된 파일)
        youtube_file = os.path.join(DATA_DIR, f"{prefix}_youtube.csv")
        if os.path.exists(youtube_file):
            df = pd.read_csv(youtube_file, encoding='utf-8-sig')
            df.columns = ['날짜', 'value']
            df['날짜'] = pd.to_datetime(df['날짜'])
            chef_data['youtube'] = df
        
        all_data[prefix] = chef_data
    
    return all_data


def create_visualization(all_data):
    """쉐프별 트렌드 시각화 - 네이버, 구글, 유튜브를 함께 표시"""
    
    # 4x3 서브플롯 생성 (10명 쉐프)
    fig, axes = plt.subplots(3, 4, figsize=(20, 12))
    axes = axes.flatten()
    
    for idx, (prefix, data) in enumerate(all_data.items()):
        if idx >= 12:
            break
            
        ax = axes[idx]
        chef_name = data['chef_name']
        
        # 네이버 데이터랩 (초록색)
        if 'naver' in data:
            df = data['naver']
            ax.plot(df['날짜'], df['value'], color='green', label='Naver', linewidth=1.5)
        
        # 구글 트렌드 (파란색)
        if 'google' in data:
            df = data['google']
            ax.plot(df['날짜'], df['value'], color='blue', label='Google', linewidth=1.5)
        
        # 유튜브 (빨간색)
        if 'youtube' in data:
            df = data['youtube']
            ax.plot(df['날짜'], df['value'], color='red', label='YouTube', linewidth=1.5)
        
        ax.set_title(f'Chef = {chef_name}', fontsize=10)
        ax.set_xlabel('Date', fontsize=8)
        ax.set_ylabel('Value', fontsize=8)
        ax.tick_params(axis='x', rotation=45, labelsize=7)
        ax.tick_params(axis='y', labelsize=7)
        
        # 그리드 추가
        ax.grid(True, alpha=0.3)
    
    # 사용하지 않는 서브플롯 숨기기
    for idx in range(len(all_data), 12):
        axes[idx].set_visible(False)
    
    # 범례 추가 (마지막 보이는 서브플롯에)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', fontsize=10, 
               bbox_to_anchor=(0.98, 0.98))
    
    plt.suptitle('흑백요리사 쉐프별 트렌드 추이\n(Naver: 초록, Google: 파랑, YouTube: 빨강)', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    # 저장
    output_path = os.path.join(DATA_DIR, 'trend_comparison_three_sources.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n시각화 저장 완료: {output_path}")
    
    plt.show()


def main():
    print("=" * 60)
    print("흑백요리사 트렌드 추이 시각화")
    print("=" * 60)
    
    # 1. 유튜브 CSV 파일을 표준 형식으로 변환
    print("\n[1단계] 유튜브 CSV 파일 형식 변환...")
    convert_youtube_csv_to_standard_format()
    
    # 2. 모든 데이터 로드
    print("\n[2단계] 데이터 로드 중...")
    all_data = load_all_data()
    print(f"로드된 쉐프 수: {len(all_data)}")
    
    # 3. 시각화
    print("\n[3단계] 시각화 생성 중...")
    create_visualization(all_data)
    
    print("\n완료!")


if __name__ == "__main__":
    main()
