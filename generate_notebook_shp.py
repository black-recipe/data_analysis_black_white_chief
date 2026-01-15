import json
import os

# 1. 파일 경로 설정
target_notebook_name = "BlackWhiteChef_GridAnalysis_300m.ipynb"
notebook_path = os.path.join(r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사", target_notebook_name)

# SHP 파일 자동 감지 경로 (find_by_name 결과 반영)
shp_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\(B031)국가기본공간정보()_NF_A_G01106\NF_A_G01106.shp"

# 노트북 셀 리스트
cells = []

# [Cell 1] 제목
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "# 흑백요리사 식당 300m 격자 및 행정동 경계 시각화\n",
        "\n",
        "이 노트북은 다음 작업을 수행합니다.\n",
        "1. **300m 격자 생성**: 식당 위치 기준 반경 300m\n",
        "2. **행정동 경계 로드**: 보유한 SHP 파일을 활용하여 지도에 오버레이\n",
        "3. **시각화**: Folium (격자 + 행정동)"
    ]
})

# [Cell 2] 라이브러리
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

# [Cell 3] 데이터 파일 경로 설정
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 1. 식당 데이터 (CSV)\n",
        "csv_path = r\"c:\\Users\\USER\\Documents\\웅진씽크빅kdt\\흑백요리사\\캐치테이블_가게정보.csv\"\n",
        "\n",
        "# 2. 행정동 경계 데이터 (SHP)\n",
        "shp_path = r\"c:\\Users\\USER\\Documents\\웅진씽크빅kdt\\흑백요리사\\(B031)국가기본공간정보()_NF_A_G01106\\NF_A_G01106.shp\"\n",
        "\n",
        "# 경로 확인\n",
        "print(f\"CSV Exist: {os.path.exists(csv_path)}\")\n",
        "print(f\"SHP Exist: {os.path.exists(shp_path)}\")"
    ]
})

# [Cell 4] 데이터 로드 및 300m 격자 생성 로직
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "def create_300m_grid(df, lat_col, lon_col):\n",
        "    # Point 변환\n",
        "    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]\n",
        "    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=\"EPSG:4326\")\n",
        "    \n",
        "    # 좌표계 변환 및 버퍼 (300m)\n",
        "    gdf_proj = gdf.to_crs(epsg=5179)\n",
        "    gdf_proj['grid_geometry'] = gdf_proj.geometry.buffer(300).envelope\n",
        "    \n",
        "    gdf_grid = gdf_proj.set_geometry('grid_geometry')\n",
        "    gdf_grid = gdf_grid.drop(columns=['geometry'], errors='ignore')\n",
        "    gdf_grid = gdf_grid.rename_geometry('geometry')\n",
        "    return gdf_grid\n",
        "\n",
        "# 실행\n",
        "df = pd.read_csv(csv_path)\n",
        "gdf_grid = create_300m_grid(df, 'lat', 'lon')\n",
        "gdf_grid['area_m2'] = gdf_grid.geometry.area\n",
        "print(\"✅ 300m 격자 생성 완료\")"
    ]
})

# [Cell 5] 행정동 SHP 로드 및 전처리
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "try:\n",
        "    # SHP 파일 읽기 (인코딩 주의: cp949)\n",
        "    print(\"📂 행정동 SHP 로딩 중...\")\n",
        "    gdf_adm = gpd.read_file(shp_path, encoding='cp949')\n",
        "    \n",
        "    # 좌표계 확인 및 변환 (Folium용 WGS84)\n",
        "    if gdf_adm.crs is None:\n",
        "        # 좌표계 정보가 없는 경우, 보통 한국은 EPSG:5174 or 5179인데...\n",
        "        # 일단 5174(Bessel)나 5179일 확률이 높음. 원본 확인 필요.\n",
        "        # 여기선 에러 방지를 위해 User에게 확인 요청 메시지 출력\n",
        "        print(\"⚠️ 경고: SHP 파일에 좌표계(CRS) 정보가 없습니다. 지도에 표시되지 않을 수 있습니다.\")\n",
        "        # 임시로 5179로 가정해봅니다.\n",
        "        gdf_adm.set_crs(epsg=5179, inplace=True)\n",
        "    \n",
        "    gdf_adm_viz = gdf_adm.to_crs(epsg=4326)\n",
        "    \n",
        "    print(f\"✅ 행정동 데이터 로드 완료: {len(gdf_adm_viz)}개 구역\")\n",
        "    display(gdf_adm_viz.head(3))\n",
        "    \n",
        "except Exception as e:\n",
        "    print(f\"❌ SHP 로드 실패: {e}\")\n",
        "    gdf_adm_viz = None"
    ]
})

# [Cell 6] 시각화 (Layering)
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# 시각화 준비\n",
        "gdf_grid_viz = gdf_grid.to_crs(epsg=4326)\n",
        "center_lat = gdf_grid_viz.geometry.centroid.y.mean()\n",
        "center_lon = gdf_grid_viz.geometry.centroid.x.mean()\n",
        "\n",
        "m = folium.Map(location=[center_lat, center_lon], zoom_start=12)\n",
        "\n",
        "# 1. 행정동 경계 레이어 (검은색 실선)\n",
        "if gdf_adm_viz is not None:\n",
        "    folium.GeoJson(\n",
        "        gdf_adm_viz,\n",
        "        name='행정동 경계',\n",
        "        style_function=lambda x: {'fillColor': 'none', 'color': 'gray', 'weight': 2, 'dashArray': '5, 5'},\n",
        "        tooltip=folium.GeoJsonTooltip(fields=list(gdf_adm_viz.columns)[:3]) # 앞 3개 컬럼 툴팁 표시\n",
        "    ).add_to(m)\n",
        "\n",
        "# 2. 300m 격자 레이어 (파란색)\n",
        "folium.GeoJson(\n",
        "    gdf_grid_viz,\n",
        "    name='300m Grid',\n",
        "    style_function=lambda x: {'fillColor': 'blue', 'color': 'blue', 'weight': 1, 'fillOpacity': 0.3},\n",
        "    tooltip=folium.GeoJsonTooltip(fields=['restaurant', 'area_m2'])\n",
        ").add_to(m)\n",
        "\n",
        "folium.LayerControl().add_to(m)\n",
        "m"
    ]
})

# JSON 생성
notebook_content = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
             "display_name": "Python 3",
             "language": "python",
             "name": "python3"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook_content, f, indent=2, ensure_ascii=False)

print(f"Jupyter Notebook generated: {notebook_path}")
