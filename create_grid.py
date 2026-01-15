import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

def create_50m_grid_from_locations(df: pd.DataFrame, lat_col: str, lon_col: str):
    """
    주어진 위도/경도 데이터프레임을 받아 50m 격자(Grid) 폴리곤을 생성하는 함수
    
    Args:
        df: 식당 정보가 담긴 DataFrame
        lat_col: 위도 컬럼명
        lon_col: 경도 컬럼명
        
    Returns:
        gdf_grid: 50m 격자 폴리곤이 포함된 GeoDataFrame (EPSG:5179)
    """
    
    # 1. 위도/경도를 Point 객체로 변환하여 GeoDataFrame 생성 (좌표계: EPSG: 4326 - WGS84)
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    
    print(f"✅ 원본 데이터 좌표계: {gdf.crs}")
    
    # 2. 미터 단위 계산을 위해 투영 좌표계로 변환 (EPSG: 5179 - Korea Central Belt 2010)
    # 대한민국에서 가장 일반적으로 쓰이는 미터 좌표계입니다.
    gdf_proj = gdf.to_crs(epsg=5179)
    
    print(f"✅ 변환된 좌표계: {gdf_proj.crs} (미터 단위)")
    
    # 3. 50m 반경 버퍼 생성 후 Envelop(사각형) 처리하여 격자 생성
    # buffer(50): 반경 50m 원 생성
    # envelope: 해당 원을 감싸는 정사각형(Bounding Box) 생성 (100m x 100m)
    # 만약 정확히 중심점 기준 50m x 50m를 원하면 buffer(25)를 해야 함.
    # 설계서에 따라 '반경 50m'를 커버하는 영역으로 설정 (buffer 50 -> envelope)
    
    # 50m 반경의 원을 만듭니다.
    gdf_proj['buffer_geometry'] = gdf_proj.geometry.buffer(50)
    
    # 원을 감싸는 정사각형 격자(Grid)로 변환합니다.
    gdf_proj['grid_geometry'] = gdf_proj['buffer_geometry'].envelope
    
    # 4. 분석용 최종 GeoDataFrame 생성 (Grid Geometry를 메인으로 설정)
    gdf_grid = gdf_proj.set_geometry('grid_geometry')
    
    # 필요없는 중간 컬럼 및 원본 Point Geometry 삭제
    # 'geometry'는 원본 Point 컬럼, 'buffer_geometry'는 원형 버퍼
    cols_to_drop = ['buffer_geometry', 'geometry']
    gdf_grid = gdf_grid.drop(columns=cols_to_drop, errors='ignore')
    
    # 결과가 grid_geometry 하나만 남도록 이름 변경 (선택사항, 호환성을 위해 geometry로 다시 변경 추천)
    gdf_grid = gdf_grid.rename_geometry('geometry')
    
    return gdf_grid

if __name__ == "__main__":
    # 1. 실제 파일 경로 설정
    file_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\캐치테이블_가게정보.csv"
    
    print(f"📂 데이터 파일 로딩 중: {file_path}")
    
    try:
        # CSV 파일 읽기
        df = pd.read_csv(file_path)
        
        # 컬럼 이름 확인 (lat, lon 인지 확인)
        print(f"✅ 컬럼 목록: {list(df.columns)}")
        
        # 2. 50m 격자 생성 실행
        # CSV의 컬럼명이 'lat', 'lon' 이므로 그대로 전달
        grid_result = create_50m_grid_from_locations(df, lat_col='lat', lon_col='lon')
        
        print("\n🚀 [성공] 50m 격자 생성 완료!")
        print(grid_result[['restaurant', 'geometry']].head())
        
        # 면적 검증
        grid_result['area_m2'] = grid_result.geometry.area
        print(f"\n📏 격자 면적 검증 (Head 5):\n{grid_result['area_m2'].head()}")
        
        # 3. 결과 저장 (GeoJSON or CSV)
        # GeoJSON은 시각화 툴(QGIS, Kepler.gl)에서 바로 열립니다.
        output_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\result_grid_50m.geojson"
        grid_result.to_file(output_path, driver='GeoJSON')
        print(f"\n💾 결과 파일 저장 완료: {output_path}")

    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    except KeyError as e:
        print(f"❌ 컬럼명을 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
