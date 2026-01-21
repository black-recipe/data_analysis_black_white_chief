# 흑백요리사2 대시보드 구현 완료 보고서

## ✅ 구현 완료 항목

### 생성된 파일

| 파일명 | 설명 |
|--------|------|
| [data_processor.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/data_processor.py) | 데이터 로드 및 전처리 모듈 |
| [review_heatmap.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/review_heatmap.py) | 리뷰 히트맵 시각화 모듈 |
| [population_animated_map.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/population_animated_map.py) | 유동인구 애니메이션 지도 모듈 |
| [streamlit_app.py](file:///c:/Users/USER/Documents/웅진씽크빅kdt/흑백요리사/대시보드용/streamlit_app.py) | Streamlit 메인 앱 |

---

## 🎨 대시보드 기능

### 탭 1: 리뷰 히트맵
- **Plotly Heatmap**: 셰프(가게) x 방영일 매트릭스
- 색상: 증가(빨강) / 감소(파랑), 0 기준 양방향
- 증가율(%) 또는 증가 수 선택 가능
- TOP 10 리뷰 증가 가게 표시

### 탭 2: 유동인구 애니메이션 지도
- **3가지 모드**:
  1. 🎬 애니메이션 지도: 일별 유동인구 변화 재생
  2. 📊 방영일 변화율 지도: 전/후 7일 비교
  3. 📍 특정 날짜 지도
- **★ 가게 마커**: 금색 별 마커로 출연 가게 표시
- **호버 정보**: 가게명, 셰프명, 카테고리, 리뷰수

### 탭 3: 상세 분석
- 개별 가게 선택 시 상세 정보 표시
- 방영 전/후 막대 그래프 비교
- 회차별 상세 데이터 테이블

---

## 📊 데이터 통계

| 항목 | 수치 |
|------|------|
| 총 리뷰 수 | 7,644건 |
| 유동인구 레코드 | 497,055건 |
| 분석 가게 수 | 118개 |
| 데이터 기간 | 2025-12-09 ~ 2026-01-14 |

---

## 🚀 실행 방법

```bash
cd c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\대시보드용
streamlit run streamlit_app.py
```

브라우저에서 http://localhost:8503 접속

---

## ⏭️ 추후 작업 (Airflow DAG)

사용자 요청에 따라 Airflow를 통한 자동 데이터 수집 DAG는 별도로 구현 예정입니다.
- 유동인구 API 연동
- 리뷰 크롤링 자동화
