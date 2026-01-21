# 서울시 유동인구 시각화 가이드

이 문서는 **흑백요리사 방영일**을 기준으로 서울시 유동인구 변화를 시각화하기 위해 작성된 파이썬 스크립트 설명과, 향후 **Streamlit** 및 **Airflow** 연동 방안을 다룹니다.

## 1. 시각화 스크립트 (`visualize_seoul_population.py`)

방영일 기준 **7일 전**과 **7일 후**의 유동인구 데이터를 비교하는 HTML 히트맵(Choropleth) 지도를 생성합니다.

### 주요 로직
- **데이터 소스**: `seoul_floating_pop_raw3.csv`
- **집계 방식**: `AUTONOMOUS_DISTRICT` (자치구) 및 `DATE` (일자)별 `VISITOR_COUNT` (방문자 수) 합계.
- **시각화 도구**: `folium` 라이브러리를 사용하여 단계구분도(Choropleth) 작성.
- **레이어 구성**:
    - **레이어 1 (파란색/보라색 계열)**: 방영 7일 전 (Before)
    - **레이어 2 (노란색/빨간색 계열)**: 방영 7일 후 (After)

### 실행 방법
```bash
python visualize_seoul_population.py
```
*스크립트가 실행되면 결과물인 HTML 지도 파일들은 `population_maps/` 폴더에 저장됩니다.*

## 2. 향후 시스템 연동 가이드

### Streamlit 대시보드 연동 시
저장된 스크립트의 `load_data`와 `aggregate_by_date_and_gu`, `create_comparison_map` 함수를 모듈처럼 재사용할 수 있습니다.

```python
import streamlit as st
from visualize_seoul_population import load_data, aggregate_by_date_and_gu, create_comparison_map
from streamlit_folium import st_folium

# Streamlit 앱 내부 코드 예시:
# 데이터는 캐싱(@st.cache_data)을 사용하여 성능을 최적화하는 것이 좋습니다.
@st.cache_data
def get_data():
    return load_data('seoul_floating_pop_raw3.csv')

df = get_data()

# 사용자가 날짜를 선택하면 해당 데이터를 지도에 표시
# (agg_df는 미리 계산해두거나 필요할 때 계산)
target_date = "2025-12-16" # 예시
m = create_comparison_map(agg_df, target_date, geo_data)

st_folium(m, width=800)
```

### Airflow (실시간 파이프라인) 연동 시
1.  **데이터 수집**: 
    - Airflow DAG가 주기적으로 수집 스크립트(예: `realtime_flow_collector.py`)를 실행합니다.
    - 데이터는 CSV나 데이터베이스(PostgreSQL/Supabase)에 최신 상태로 적재됩니다.

2.  **업데이트 반영**:
    - 이 시각화 스크립트나 Streamlit 대시보드는 **데이터 소스(CSV/DB)**만 바라보게 해 두면 됩니다.
    - 데이터 소스가 Airflow에 의해 업데이트되면, 대시보드 새로고침 시 자동으로 최신 결과가 반영됩니다.

## 3. 현재 작업 결과
스크립트 실행이 완료되었으며, 다음 지도 파일들이 생성되었습니다:
- `population_maps/population_comparison_20251216.html`
- `population_maps/population_comparison_20251223.html`
- `population_maps/population_comparison_20251230.html`
- `population_maps/population_comparison_20260106.html`
- `population_maps/population_comparison_20260113.html` 
    - *참고: 1월 13일 방영분의 경우, 비교 대상인 1월 20일 데이터가 아직 수집되지 않아 '7일 전' 데이터만 표시됩니다.*
