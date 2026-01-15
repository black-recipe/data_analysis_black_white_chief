import requests
import pandas as pd
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import time
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, box
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import folium
from folium import plugins
import matplotlib.colors as mcolors

# 시각화 한글 폰트 설정 (Windows 기준)
from matplotlib import font_manager, rc
font_path = "C:/Windows/Fonts/malgun.ttf"
if os.path.exists(font_path):
    font = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font)
plt.rcParams['axes.unicode_minus'] = False

def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# ==============================================================================
# 1. 데이터 수집 (Data Collection)
# ==============================================================================
def collect_data():
    print(">>> 데이터 수집 시작")
    
    # 설정값
    lawd_cd = 41390  # 법정동코드 (시흥시?)
    service_key = 'yQ3x5TpauR4TZTv3VVe7/GtT5ooGmknYKee5L9a5oOM0/oOHiKURlQ0FamByEQFWGM0NYNg204bG9mXY17T6HQ=='  # 디코딩된 키 필요할 수 있음
    
    # 날짜 리스트 생성 (2006-01 ~ 2025-12)
    start_date = '2006-01-01'
    end_date = '2025-12-31'
    dates = pd.date_range(start=start_date, end=end_date, freq='MS') # 월의 시작일
    date_list = dates.strftime('%Y%m').tolist()
    
    print(f"총 요청 개수: {len(date_list)}")
    
    base_url = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    
    all_data = []
    
    create_directory('call_api')
    
    for i, ymd in enumerate(date_list):
        params = {
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': ymd,
            'numOfRows': 10000,
            'serviceKey': service_key # requests는 encoding된 키를 자동으로 처리하기도 하나, 주의 필요
        }
        
        try:
            response = requests.get(base_url, params=params)
            # R 코드에서 xmlTreeParse 사용 -> Python ElementTree 사용
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                for item in items:
                    # XML 태그 값 추출 함수 (None 처리)
                    def get_text(tag):
                        node = item.find(tag)
                        return node.text.strip() if node is not None else None

                    # R코드의 인덱스와 매핑하여 태그 추정 (일반적인 국토부 실거래가 명칭 사용)
                    row = {
                        'year': get_text('년'),
                        'month': get_text('월'),
                        'day': get_text('일'),
                        'price': get_text('거래금액'),
                        'code': get_text('지역코드'),
                        'dong_nm': get_text('법정동'),
                        'jibun': get_text('지번'),
                        'con_year': get_text('건축년도'),
                        'apt_nm': get_text('아파트'),
                        'area': get_text('전용면적'),
                        'floor': get_text('층')
                    }
                    all_data.append(row)
            else:
                print(f"Error {response.status_code} at {ymd}")
                
        except Exception as e:
            print(f"Exception at {ymd}: {e}")
            
        if i % 10 == 0:
            print(f"진행상황: {i}/{len(date_list)}")
            
        time.sleep(0.1) # Sys.sleep(.1)

    df = pd.DataFrame(all_data)
    df.to_csv('apt_price2.csv', index=False, encoding='utf-8-sig')
    print(">>> 데이터 수집 완료 및 저장 (apt_price2.csv)")
    return df

# ==============================================================================
# 2. 데이터 전처리 (Data Preprocessing)
# ==============================================================================
def preprocess_data():
    print(">>> 데이터 전처리 시작")
    if not os.path.exists('apt_price2.csv'):
        print("파일이 없어 수집 단계를 먼저 실행해야 합니다.")
        # collect_data() # 필요시 주석 해제
        return

    price_df = pd.read_csv('apt_price2.csv')
    
    # 컬럼 삭제 (select(-1, -code) 대응) -> index컬럼이 있다면 drop, code는 'code'
    if 'Unnamed: 0' in price_df.columns:
        price_df = price_df.drop(columns=['Unnamed: 0'])
    # if 'code' in price_df.columns: price_df = price_df.drop(columns=['code']) 
    # R코드에서는 code를 지웠으나 로직상 필요할 수도 있음. 따르겠음.
    price_df = price_df.drop(columns=['code'], errors='ignore')

    # 결측값 확인
    print("결측값 수:\n", price_df.isnull().sum())

    # 시계열 날짜 만들기
    # 'price' 컬럼의 콤마 제거 및 숫자 변환
    price_df['price'] = price_df['price'].astype(str).str.replace(',', '').str.strip()
    price_df['price'] = pd.to_numeric(price_df['price'], errors='coerce')
    price_df['area'] = pd.to_numeric(price_df['area'], errors='coerce')

    # 날짜 컬럼 생성
    price_df['ymd'] = pd.to_datetime(price_df[['year', 'month', 'day']])
    price_df['ym'] = price_df['ymd'].dt.to_period('M').dt.to_timestamp()

    # 주소 지번 만들기
    # dong_nm, jibun, apt_nm 결합 (NA 처리 필요)
    price_df['juso_jibun'] = price_df['dong_nm'].fillna('') + " " + \
                             price_df['jibun'].fillna('') + " " + \
                             price_df['apt_nm'].fillna('')
    price_df['juso_jibun'] = price_df['juso_jibun'].str.replace('  ', ' ').str.strip()

    # 평당 가격 (py)
    price_df['py'] = round(price_df['price'] / price_df['area'] * 3.3, 0)
    
    price_df['cnt'] = 1
    
    # 저장
    price_df.to_csv('price_last.csv', index=False, encoding='utf-8-sig')
    print(">>> 전처리 완료 (price_last.csv)")
    return price_df

# ==============================================================================
# 3. 카카오 API로 지오코딩 (Geocoding)
# ==============================================================================
def geocode_addresses():
    print(">>> 지오코딩 시작")
    # 파일 로드
    if not os.path.exists('price_last.csv'): return
    price_df = pd.read_csv('price_last.csv')
    
    # 고유 주소 추출
    apt_juso = price_df[['juso_jibun']].drop_duplicates().dropna()
    print(f"상위 주소 예시: {apt_juso.head()}")
    
    kakao_key = 'YOUR_KAKAO_API_KEY_HERE' # [사용자 입력 필요]
    headers = {'Authorization': f'KakaoAK {kakao_key}'}
    
    add_list = []
    
    total = len(apt_juso)
    print(f"총 변환 대상: {total}")

    for idx, row in apt_juso.iterrows():
        query = row['juso_jibun']
        url = 'https://dapi.kakao.com/v2/local/search/address.json'
        
        try:
            resp = requests.get(url, headers=headers, params={'query': query})
            if resp.status_code == 200:
                data = resp.json()
                if data['documents']:
                    doc = data['documents'][0]
                    # 주소 정보와 좌표 저장
                    add_list.append({
                        'juso_jibun': query,
                        'coord_x': doc['x'], # 경도 (Longitude)
                        'coord_y': doc['y']  # 위도 (Latitude)
                    })
                    # 진행로그
                    # print(f"[{len(add_list)}/{total}] {query}: {doc['x']}, {doc['y']}")
            else:
                print(f"Error {resp.status_code} for {query}")
        except Exception as e:
            print(f"Error for {query}: {e}")
            
        if len(add_list) % 100 == 0:
            print(f"진행률: {len(add_list)/total*100:.2f}%")
            
    # 결과 저장
    juso_geocoding = pd.DataFrame(add_list)
    # 숫자형 변환
    juso_geocoding['coord_x'] = pd.to_numeric(juso_geocoding['coord_x'])
    juso_geocoding['coord_y'] = pd.to_numeric(juso_geocoding['coord_y'])
    
    juso_geocoding.to_csv('juso_geocoding.csv', index=False, encoding='utf-8-sig')
    print(">>> 지오코딩 완료 (juso_geocoding.csv)")
    return juso_geocoding

# ==============================================================================
# 4. 지오 데이터프레임 만들기 & 시흥시 Grid 나누기
# ==============================================================================
def create_geo_data_and_grid():
    print(">>> 지오 데이터프레임 및 그리드 작업 시작")
    
    # 1. 병합
    price_df = pd.read_csv('price_last.csv')
    juso_geocoding = pd.read_csv('juso_geocoding.csv')
    
    # left_join
    apt_price = pd.merge(price_df, juso_geocoding, on='juso_jibun', how='left')
    apt_price = apt_price.dropna(subset=['coord_x', 'coord_y']) # 결측 제거
    
    # 2. GeoDataFrame 생성 (WGS84)
    geometry = [Point(xy) for xy in zip(apt_price['coord_x'], apt_price['coord_y'])]
    geo_apt_price = gpd.GeoDataFrame(apt_price, geometry=geometry, crs="EPSG:4326")
    
    # 저장
    geo_apt_price.to_file('geo_apt_price.geojson', driver='GeoJSON') # CSV대신 GeoJSON이 GIS용으로 더 적합
    
    # 3. 시흥시 Shapefile 로드 (경로 확인 필요)
    shp_path = './시흥시행정동/(B031)국가기본공간정보(경기도 시흥시)_NF_A_G01106/NF_A_G01106.shp'
    if not os.path.exists(shp_path):
        print(f"경고: 쉐이프파일 경로가 존재하지 않습니다: {shp_path}")
        return geo_apt_price, None

    shp1 = gpd.read_file(shp_path, encoding='cp949') # 한글 깨짐 방지
    
    # 좌표계 변환 (EPSG:5186 - 한국 중부원점 등) -> Python에서는 5174 or 5186 주로 사용
    # R코드: shp1 <- st_transform(shp1, crs = 5186)
    shp1_5186 = shp1.to_crs(epsg=5186)
    
    # 4. 그리드 생성 (500m x 500m)
    minx, miny, maxx, maxy = shp1_5186.total_bounds
    step = 500
    
    x_range = np.arange(minx, maxx, step)
    y_range = np.arange(miny, maxy, step)
    
    grid_cells = []
    for x in x_range:
        for y in y_range:
            grid_cells.append(box(x, y, x+step, y+step))
            
    grid = gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs=shp1_5186.crs)
    
    # 시흥시 경계와 교차하는 그리드만 필터링
    grid_filtered = gpd.overlay(grid, shp1_5186, how='intersection')
    
    # 시각화 (Matplotlib)
    fig, ax = plt.subplots(figsize=(10, 10))
    shp1_5186.plot(ax=ax, color='lightblue', edgecolor='black')
    grid_filtered.plot(ax=ax, facecolor='none', edgecolor='red')
    plt.title("0.5km Grid Over 시흥시")
    plt.savefig('grid_map.png')
    
    # 그리드 저장
    grid_filtered.to_file('grid_siheung.geojson', driver='GeoJSON')
    print(">>> GeoDataFrame 및 Grid 생성 완료")
    
    return geo_apt_price, grid_filtered

# ==============================================================================
# 5. 공간 조인 및 시각화 (Spatial Join & Visualization)
# ==============================================================================
def analyze_and_visualize_kde():
    print(">>> 분석 및 시각화(KDE) 시작")
    
    # 데이터 로드
    if not os.path.exists('geo_apt_price.geojson') or not os.path.exists('grid_siheung.geojson'):
        print("이전 단계 데이터가 없습니다.")
        return

    geo_apt_price = gpd.read_file('geo_apt_price.geojson')
    grid_filtered = gpd.read_file('grid_siheung.geojson')
    
    # 좌표계 통일 (WGS84로 통일하여 지도 시각화 준비)
    grid_wgs84 = grid_filtered.to_crs(epsg=4326)
    geo_apt_127 = geo_apt_price # 이미 4326

    # 필터링 로직 (R코드: price2_last ...)
    # 1. 2021년 전후 가격 차이 계산 -> 그리드별 평균으로
    # 이를 위해 먼저 각 포인트가 어느 그리드에 속하는지 조인
    # Grid(Polygon)에 Point Join
    
    # 좌표계를 투영좌표계(미터 단위)로 바꿔서 조인하는 것이 정확함
    grid_5186 = grid_filtered # 5186
    geo_apt_5186 = geo_apt_price.to_crs(epsg=5186)
    
    # Spatial Join
    joined = gpd.sjoin(geo_apt_5186, grid_5186, how='left', predicate='intersects')
    
    # juso_jibun 별로 그룹화하여 가격 상승 분석
    # R: 2020이전(before), 2021이후(after)
    joined['ymd'] = pd.to_datetime(joined['ymd'])
    
    before = joined[joined['ymd'] <= '2020-12-31'].groupby('juso_jibun')['py'].mean().rename('before')
    after = joined[joined['ymd'] >= '2021-01-01'].groupby('juso_jibun')['py'].mean().rename('after')
    
    diff_df = pd.concat([before, after], axis=1)
    diff_df['diff'] = ((diff_df['after'] - diff_df['before']) / diff_df['before'] * 100).round(0)
    
    # 상승 지역만 (diff > 0)
    hot_df = diff_df[diff_df['diff'] > 0].dropna()
    
    # 원본 좌표와 결합 (시각화를 위해)
    # juso_jibun을 키로 사용하여 좌표 가져오기 (unique)
    coords = geo_apt_price.drop_duplicates('juso_jibun')[['juso_jibun', 'geometry']]
    hot_geo = pd.merge(hot_df, coords, on='juso_jibun', how='inner')
    hot_geo = gpd.GeoDataFrame(hot_geo, geometry='geometry', crs="EPSG:4326")
    
    print(f"가격 상승 지점 수: {len(hot_geo)}")
    
    # ==========================
    # KDE (Kernel Density Estimation)
    # ==========================
    if len(hot_geo) < 2:
        print("데이터가 너무 적어 KDE를 수행할 수 없습니다.")
        return

    # 좌표 추출
    x = hot_geo.geometry.x
    y = hot_geo.geometry.y
    weights = hot_geo['diff'] # 가중치: 상승률
    
    # 1. KDE 모델 생성
    data = np.vstack([x, y])
    kde = gaussian_kde(data, weights=weights) # weights 지원 여부 확인 (scipy 최신버전 지원)
    
    # 2. Grid 생성 (Raster 해상도 결정)
    # 시흥시 범위 (buffer 좀 줘서)
    minx, miny, maxx, maxy = x.min(), y.min(), x.max(), y.max()
    x_grid, y_grid = np.mgrid[minx:maxx:100j, miny:maxy:100j]
    positions = np.vstack([x_grid.ravel(), y_grid.ravel()])
    
    # 3. 밀도 계산
    z = kde(positions)
    z = z.reshape(x_grid.shape)
    
    # 4. 노이즈 제거 (상위 25% 이하 제거 등 R 로직 유사하게)
    # R: d[d < quantile(d)[4] + ...] -> 여기서는 하위 75%를 0(투명)으로
    threshold = np.percentile(z, 75)
    z_masked = np.ma.masked_where(z < threshold, z)
    
    # ==========================
    # 시각화 (Folium)
    # ==========================
    # 중심점
    center = [y.mean(), x.mean()]
    m = folium.Map(location=center, zoom_start=12, tiles='cartodbpositron')
    
    # 경계선 추가 (시흥시)
    # shp_path 로드 필요 (위에서 로드한 shp1 사용 가정, 여기선 재로드 생략하고 grid_filtered의 convex_hull 등을 쓸 수도 있음)
    # 여기선 hot_geo의 범위 정도만 표시하거나 생략
    
    # 1) ImageOverlay 사용 (Raster 느낌)
    # 이미지로 오버레이하려면 컬러맵 적용 후 저장하거나 base64 인코딩 필요
    # 간단하게 이미지 오버레이용 bounds 설정
    # image_overlay = folium.raster_layers.ImageOverlay(
    #     image=z_masked,
    #     bounds=[[miny, minx], [maxy, maxx]],
    #     opacity=0.6,
    #     origin='lower',
    #     colormap=lambda x: (1, 0, 0, x) # 단순 예시
    # )
    # m.add_child(image_overlay)

    # 2) HeatMap 사용 (더 간편하고 예쁨)
    # HeatMap은 포인트 기반이지만, 이미 KDE값(z)을 구했으므로 이를 등고선처럼 그리거나,
    # 그냥 hot_geo 자체를 HeatMap으로 그리는게 가장 정신건강에 좋음 (가중치 포함)
    heat_data = [[row.geometry.y, row.geometry.x, row['diff']] for idx, row in hot_geo.iterrows()]
    
    plugins.HeatMap(heat_data, radius=15, blur=20, max_zoom=1).add_to(m)
    
    # 저장
    m.save('kde_hot_map.html')
    print(">>> KDE 지도 저장 완료 (kde_hot_map.html)")

if __name__ == "__main__":
    # 각 단계별 실행 (필요에 따라 주석 해제)
    # collect_data()      # 1. 데이터 수집
    # preprocess_data()   # 2. 전처리
    # geocode_addresses() # 3. 지오코딩 (API 키 필요)
    # create_geo_data_and_grid() # 4. 공간 데이터 생성
    # analyze_and_visualize_kde() # 5. 분석 및 하이라이트 시각화
    print("모든 함수 정의 완료. 메인 블록에서 필요한 함수를 실행하세요.")
