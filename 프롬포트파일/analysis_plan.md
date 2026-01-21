# 흑백요리사 쉐프 식당 유동인구 분석 프로젝트 설계서

## 1️⃣ 문제 재정의 (Problem Definition)
단순한 "유동인구가 몇 명인가?"를 넘어, **"방송 출연(Event)이 오프라인 트래픽(Impact)에 미친 인과 효과"**를 측정하는 문제로 정의합니다.

- **Data Engineering 관점**: 행정동 단위의 거시적 데이터(서울시 생활인구)를 50m 미시적 격자로 **다운스케일링(Down-scaling)**하는 파이프라인 구축.
- **Data Science 관점**: 방송 직후의 **단기 급증(Spike)** 패턴이 실제 방문으로 이어질 수 있는 유효 트래픽인가를 검증.

---

## 2️⃣ 데이터 요구사항 (Data Requirements)
사용자 피드백을 반영하여 데이터 소스를 확정했습니다.

### 2.1 내부 데이터 (Internal Data)
- **Target POI**: 쉐프 식당 마스터 데이터 (이름, 주소 등)
- **Impact Event**: 방송 방영일 정보

### 2.2 외부 데이터 (External Data)
- **유동인구 데이터**: **[서울시 생활인구 데이터](https://data.seoul.go.kr/)** (행정동 단위)
- **공간정보 데이터**: **[국토정보플랫폼](http://map.ngii.go.kr/)** 행정동 경계(SHP) 파일
  - *활용 목적: 행정동 단위 인구를 50m 격자로 할당하기 위한 기준 맵*
- **캘린더/날씨**: 공휴일 및 기상청 날씨 데이터

---

## 3️⃣ 위도·경도 기준 50m 격자 생성 (Spatial Pipeline)
Kakao API를 활용한 지오코딩과 격자 생성 프로세스를 명확히 합니다.

### 3.1 위치 좌표 확보 (Geocoding)
- **도구**: Kakao Local API
- **입력**: 식당 주소 (String)
- **출력**: 위도/경도 (EPSG:4326, WGS84)
- *Note: 이 단계에서는 아직 '미터' 단위 계산이 불가능합니다.*

### 3.2 좌표계 변환 및 격자 생성 (Essential Step)
"50m"라는 물리적 거리를 정확히 계산하기 위해 **투영(Projection)** 과정이 필수입니다.

1. **좌표계 변환 (Projection)**
   - `EPSG:4326` (위경도) ➡ **`EPSG:5179` (UTM-K, 미터 단위)** 변환
   - *이유: 위경도 상태에서 50을 더하면 50도(약 5,500km)가 되므로, 미터 단위 좌표계로 변환해야 50m 계산이 가능함.*

2. **50m 격자 보간 (Spatial Interpolation)**
   - **소스**: 행정동 단위 생활인구 ($Population_{Dong}$)
   - **타겟**: 식당 중심 50m 반경 ($Area_{50m}$)
   - **알고리즘**: **면적 가중 보간법 (Area Weighted Interpolation)**
     - 식: $Pop_{50m} = Pop_{Dong} \times \frac{Area(Intersection_{Dong \cap 50m})}{Area(Dong)}$
     - 설명: 행정동 전체 면적 대비, 내 50m 격자가 차지하는 면적 비율만큼 인구수를 가져옵니다.

---

## 4️⃣ 시간 축 설계 (Temporal Design)
- **Window**: 방영일 기준 ±7일 (총 15일)
- **Time Slot**: 3시간 단위 (00-03, 03-06... 21-24)
- **Seasonality Control**: 요일별/시간대별 비교 필수 (금요일 저녁은 금요일 저녁끼리 비교)

---

## 5️⃣ 데이터 결합 파이프라인 (Data Integration)

1. **Ingestion**: 서울시 생활인구 CSV 다운로드 및 식당 주소 Geocoding (Kakao API)
2. **Preprocessing**: 
   - 행정동 SHP 파일 로딩 및 `EPSG:5179` 변환
   - 식당 좌표 `EPSG:5179` 변환 후 50m 버퍼 생성
3. **Spatial Join**:
   - 행정동 Polygon vs 식당 50m Buffer Polygon 교차 연산 (`overlay`)
   - 겹치는 면적 비율 계산
4. **Metric Calculation**: 비율대로 유동인구수 할당

---

## 6️⃣ 분석 결과 지표 (Analysis Metrics)
1. **Intensity (밀집도)**: 해당 격자의 추정 유동인구 수
2. **Impact Index (방송 효과)**: 방영일 전후 트래픽 증감률 (%)
3. **Hotspot Score**: 주변 행정동 평균 증가율 대비 해당 격자의 초과 증가분 (주변은 조용한데 여기만 떴는가?)

---

## 7️⃣ 시각화 (Visualization)
- **Library**: `Pydeck` (대용량 그리드 렌더링에 최적)
- **Layer**: `PolygonLayer` (50m 격자) 또는 `HeatmapLayer`
- **Insight**: 지도 위에 식당 위치 점(Point)과 유동인구 변화량(Color)을 중첩 표시

---

## 8️⃣ 예상되는 리스크와 해결책
1. **공간 해상도 한계**:
   - **Risk**: 행정동은 너무 넓어서(수 km), 그 안의 50m 격자에 균등하게 인구를 뿌리면(N빵) 실제 핫플레이스를 반영 못 할 수 있음.
   - **Mitigation**: 가능하다면 **'건물통합정보(GIS)'**를 추가로 사용하여, 건물이 있는 곳에만 인구를 가중 할당하는 **'Dasymetric Mapping'** 기법 도입 고려 (고도화 단계).
