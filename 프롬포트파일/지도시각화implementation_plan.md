# 흑백요리사2 Streamlit 대시보드 구현 계획

## 개요
Streamlit 기반으로 두 가지 대시보드를 구현합니다:
1. **리뷰수 변화 히트맵**: 방영일 기준 전/후 7일 리뷰 증가율
2. **유동인구 애니메이션 지도**: 방영일별 자치구 유동인구 변화 + ★ 가게 마커

---

## Proposed Changes

### 데이터 처리 모듈

#### [NEW] [data_processor.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/data_processor.py)
- 리뷰 데이터 전처리 함수
- 유동인구 데이터 집계 함수
- 방영일 기준 전/후 기간 필터링 유틸리티

---

### 대시보드 1: 리뷰 히트맵

#### [NEW] [review_heatmap.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/review_heatmap.py)

**기능:**
- `reviews_collected_20260114.csv` 로드 및 전처리
- 방영일(12/16, 12/23, 12/30, 1/6, 1/13) 기준 ±7일 리뷰 수 집계
- Plotly Heatmap으로 셰프 x 방영일 매트릭스 시각화
- 색상: 증가(빨강) / 감소(파랑)

---

### 대시보드 2: 유동인구 애니메이션 지도

#### [NEW] [population_animated_map.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/population_animated_map.py)

**기능:**
- `seoul_floating_pop_raw3.csv` 일별 자치구 집계
- Plotly Express `choropleth_mapbox` + `animation_frame` 활용
- 가게 위치 ★ 마커 오버레이 (scatter_mapbox)
- 호버 정보: 가게명, 셰프명, 유명요리, 리뷰수

**마커 데이터 소스:**
- `캐치테이블_가게정보.csv`: lat, lon, restaurant, chief_info, category, review_count

---

### Streamlit 앱

#### [NEW] [streamlit_app.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/streamlit_app.py)

**구조:**
```
├── 사이드바: 방영일 선택, 필터 옵션
├── 탭 1: 리뷰 히트맵
│   └── review_heatmap.py 호출
├── 탭 2: 유동인구 애니메이션 지도
│   └── population_animated_map.py 호출
```

---

### GeoJSON 파일

#### [NEW] [seoul_gu.geojson](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/seoul_gu.geojson)
- 서울시 25개 자치구 경계 GeoJSON
- 공공데이터포털 또는 GitHub에서 다운로드

---

### Airflow DAG (추후 구현)

#### [MODIFY] [dags/collect_seoul_iot_data.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/dags/collect_seoul_iot_data.py)
- 매일 자동 실행되도록 스케줄 설정
- 수집 데이터를 `seoul_floating_pop_raw3.csv`에 append

---

## Verification Plan

### 로컬 테스트
```bash
cd c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\대시보드용
streamlit run streamlit_app.py
```

### 확인 사항
1. 히트맵에 모든 셰프/가게가 표시되는지
2. 애니메이션 지도가 방영일별로 재생되는지
3. ★ 마커가 올바른 위치에 표시되고 호버 정보가 나타나는지
4. 모바일/데스크톱 반응형 동작
