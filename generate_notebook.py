import json
import os

# 노트북 파일 경로 (500m 버전)
notebook_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\BlackWhiteChef_GridAnalysis_500m.ipynb"

# 노트북 셀 정의
cells = []

# 1. 제목 및 설명 (Markdown)
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "# 흑백요리사 식당 500m 격자 생성 및 시각화\n",
        "\n",
        "이 노트북은 `캐치테이블_가게정보.csv` 파일의 위도/경도 정보를 활용하여 다음 작업을 수행합니다.\n",
        "1. **좌표계 변환**: WGS84(위경도) -> EPSG:5179(미터 좌표계)\n",
        "2. **격자 생성**: 각 식당 기준 반경 500m를 커버하는 정사각형 격자 생성 (가로세로 1km)\n",
        "3. **시각화**: Folium을 이용한 지도 시각화"
    ]
})

# 2. 라이브러리 임포트
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "import geopandas as gpd\n",
        "import pandas as pd\n",
        "import folium\n",
        "from shapely.geometry import Point\n",
        "import os"
    ]
})

# 3. 데이터 로드
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 데이터 파일 경로\n",
        "file_path = r\"c:\\Users\\USER\\Documents\\웅진씽크빅kdt\\흑백요리사\\캐치테이블_가게정보.csv\"\n",
        "\n",
        "# CSV 읽기\n",
        "df = pd.read_csv(file_path)\n",
        "print(f\"✅ 데이터 로드 완료: {len(df)}개 식당\")\n",
        "df[['restaurant', 'lat', 'lon']].head()"
    ]
})

# 4. 격자 생성 함수 정의 (500m)
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "def create_500m_grid_from_locations(df, lat_col, lon_col):\n",
        "    \"\"\"\n",
        "    위경도 데이터를 받아 500m 반경 기반 격자(EPSG:5179)를 생성하는 함수\n",
        "    \"\"\"\n",
        "    # 1. GeoDataFrame 생성 (EPSG:4326)\n",
        "    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]\n",
        "    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=\"EPSG:4326\")\n",
        "    \n",
        "    # 2. 좌표계 변환 (EPSG:5179)\n",
        "    gdf_proj = gdf.to_crs(epsg=5179)\n",
        "    \n",
        "    # 3. 500m 버퍼 -> 사각형(Envelope) 변환\n",
        "    # 반경 500m이므로 지름은 1000m (1km)가 됩니다.\n",
        "    gdf_proj['grid_geometry'] = gdf_proj.geometry.buffer(500).envelope\n",
        "    \n",
        "    # 4. grid_geometry를 메인으로 설정하고 정리\n",
        "    gdf_grid = gdf_proj.set_geometry('grid_geometry')\n",
        "    gdf_grid = gdf_grid.drop(columns=['geometry'], errors='ignore') # 기존 Point 컬럼 삭제\n",
        "    gdf_grid = gdf_grid.rename_geometry('geometry')\n",
        "    \n",
        "    return gdf_grid"
    ]
})

# 5. 실행 및 결과 검증
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 함수 실행\n",
        "try:\n",
        "    gdf_result = create_500m_grid_from_locations(df, 'lat', 'lon')\n",
        "    \n",
        "    # 면적 계산 (검증)\n",
        "    # 1000m * 1000m = 1,000,000 m2 이어야 함\n",
        "    gdf_result['area_m2'] = gdf_result.geometry.area\n",
        "    \n",
        "    print(\"✅ 500m 반경(1km 격자) 생성 완료!\")\n",
        "    display(gdf_result[['restaurant', 'area_m2', 'geometry']].head())\n",
        "    \n",
        "except Exception as e:\n",
        "    print(f\"❌ 오류 발생: {e}\")"
    ]
})

# 6. 지도 시각화
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 시각화를 위해 다시 위경도 좌표계(EPSG:4326)로 변환\n",
        "gdf_viz = gdf_result.to_crs(epsg=4326)\n",
        "\n",
        "# 중심점 계산\n",
        "center_lat = gdf_viz.geometry.centroid.y.mean()\n",
        "center_lon = gdf_viz.geometry.centroid.x.mean()\n",
        "\n",
        "# 지도 생성 (줌 레벨 조정)\n",
        "m = folium.Map(location=[center_lat, center_lon], zoom_start=11)\n",
        "\n",
        "# 격자 추가\n",
        "folium.GeoJson(\n",
        "    gdf_viz,\n",
        "    name='500m Grid',\n",
        "    style_function=lambda x: {'fillColor': '#0000ff', 'color': 'blue', 'weight': 1, 'fillOpacity': 0.2},\n",
        "    tooltip=folium.GeoJsonTooltip(fields=['restaurant', 'area_m2'], aliases=['식당명', '면적(m2)'])\n",
        ").add_to(m)\n",
        "\n",
        "# 지도 출력\n",
        "m"
    ]
})

# 7. 파일 저장 (선택 사항)
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 결과 저장\n",
        "output_geojson = r\"c:\\Users\\USER\\Documents\\웅진씽크빅kdt\\흑백요리사\\result_grid_500m.geojson\"\n",
        "gdf_result.to_file(output_geojson, driver='GeoJSON')\n",
        "print(f\"💾 파일 저장 완료: {output_geojson}\")"
    ]
})


# 노트북 구조 생성
notebook_content = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.10"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

# 파일 쓰기
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook_content, f, indent=2, ensure_ascii=False)

print(f"Jupyter Notebook generated at: {notebook_path}")
