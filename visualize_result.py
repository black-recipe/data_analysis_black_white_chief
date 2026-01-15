import geopandas as gpd
import folium
import os

def create_map(geojson_path, output_html):
    # 1. 데이터 로딩
    if not os.path.exists(geojson_path):
        print(f"❌ 파일이 없습니다: {geojson_path}")
        print("먼저 create_grid.py를 실행해서 격자를 생성해주세요.")
        return

    gdf = gpd.read_file(geojson_path)
    
    # 2. 지도의 중심점 찾기 (데이터의 평균 위경도)
    # GeoJSON은 EPSG:5179(미터)일 수 있으므로, 시각화용 위경도(EPSG:4326)로 변환
    gdf_viz = gdf.to_crs(epsg=4326)
    
    center_lat = gdf_viz.geometry.centroid.y.mean()
    center_lon = gdf_viz.geometry.centroid.x.mean()
    
    print(f"📍 지도 중심: {center_lat}, {center_lon}")
    
    # 3. 지도 생성 (Folium)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    # 4. 격자 데이터 추가
    folium.GeoJson(
        gdf_viz,
        name='50m Grids',
        style_function=lambda x: {'fillColor': '#ff0000', 'color': '#ff0000', 'weight': 1, 'fillOpacity': 0.3},
        tooltip=folium.GeoJsonTooltip(fields=['restaurant', 'area_m2'], aliases=['식당명', '면적'])
    ).add_to(m)
    
    # 5. 결과 저장
    m.save(output_html)
    print(f"✨ 지도가 생성되었습니다! 아래 파일을 브라우저에서 여세요:\n{output_html}")

if __name__ == "__main__":
    # 파일 경로
    input_file = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\result_grid_50m.geojson"
    output_file = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\grid_map.html"
    
    create_map(input_file, output_file)
