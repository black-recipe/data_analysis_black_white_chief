# 🍽 흑백요리사 시즌2 데이터 프로젝트

## 1. 프로젝트 개요
  ## 1. 문제 정의 (Why)

최근 외식업계는 단순한 ‘맛’의 경쟁을 넘어, **퍼스널 브랜딩**과 **미디어 노출**이 생존의 핵심 요소로 부상하고 있습니다.  
넷플릭스 예능 프로그램 **《흑백요리사》 시즌 1**은 출연 셰프들의 식당에 *예약 대란*을 불러일으키며 침체된 외식 시장에 활력을 불어넣었습니다.

시즌 2가 종료된 시점에서,
본 프로젝트는 단순한 시청률·화제성 분석이 아니라,

① 셰프 개인의 디지털 영향력,
② 지역 경제에 미치는 실질적 파급효과,
③ 우승을 결정짓는 정량·정성적 패턴을 데이터로 구조화하는 데 목적이 있습니다.


---


## 2. 핵심 목표 (Goals)

본 분석은 다음과 같은 3가지 핵심 질문을 해결하는 데 목적이 있습니다:

### 1️. 전략 분석  
- 셰프별로 어떤 **플랫폼(네이버, 유튜브, 구글)** 에서 강세를 보이는지 파악  
- 트렌드 기반 **퍼스널 브랜딩 및 마케팅 전략** 도출

### 2️. 경제적 파급력  
- 방송 출연 셰프의 식당이 위치한 **지역(Local)의 유동인구 변화** 측정  
- **상권 활성화**와의 연관성 분석

### 3️. 승리 공식 도출  
- 합격/우승 요리에 공통된 **조리 방식, 재료, 심사자 선택 패턴** 분석  
- 심사위원(백종원, 안성재)의 **취향 기반 '우승 메뉴 공식'** 정리


---


## 2. 데이터 소개 및 정의

### 🔗 데이터 출처

- [넷플릭스 흑백요리사 시즌2](https://www.netflix.com/search?q=%ED%9D%91%EB%B0%B1%EC%9A%94%EB%A6%AC%EC%82%AC2)
- [나무위키: 흑백요리사2 요리 계급 전쟁](https://namu.wiki/w/%ED%9D%91%EB%B0%B1%EC%9A%94%EB%A6%AC%EC%82%AC:%20%EC%9A%94%EB%A6%AC%20%EA%B3%84%EA%B8%89%20%EC%A0%84%EC%9F%81(%EC%8B%9C%EC%A6%8C%202))
- [캐치테이블: 흑백요리사 시즌2 식당 리스트](https://app.catchtable.co.kr/ct/curation/culinaryclasswars2?tabIndex=0&uniqueListId=1768525392228&hasShopRefsFromClient=1&curationQuickFilterKey=1)
- [서울시 스마트도시데이터 S-DoT 유동인구](https://data.seoul.go.kr/dataList/OA-15964/S/1/datasetView.do)
- 구글 트렌드 검색
- 유튜브 트렌드 검색
- 네이버 데이터랩


---

### 🗓 수집 기간 및 범위

- **수집 기간:** 2025년 12월 9일 ~ 2026년 1월 16일
- **수집 범위:**  
  - 흑백요리사2 방영 전후의 데이터 전체 수집
    - 자체 수집 : 방송 회차 내용, 셰프 정보, 요리 정보, 라운드 결과
    - API 수집 : 위치 기반 유동인구, 온라인 트렌드 데이터
    - 크롤링 : 출연 셰프의 식당 정보, 출연 셰프의 식당 리뷰

---


### 📑 데이터 정의 및 해석

| 테이블명 | 설명 | 주요 컬럼 | 특이사항 |
|----------|------|-----------|-----------|
| `chief_raw_data` | 셰프 기본 정보 | `name`, `team`, `final_round` | `name`은 PK. `team`, `final_round`는 결측 가능성 있음 |
| `competition_result_raw_data` | 셰프별 요리 결과 및 경기 정보 | `name`, `food`, `round`, `is_winner`, `how_cook`, `match_type`, `ingrediant`, `is_alive`<br>`back`, `an`, `is_back`, `is_an` | `name`은 외래키로 `chief_raw_data`와 연결됨<br>`back`, `an`, `is_back`, `is_an`은 백종원, 안성재 심사/합격 여부를 나타내는 이진 변수(0/1). 상관관계 분석 등에 활용 가능 |
| `geometry_result` | 위치 및 유동인구 데이터 | `lat`, `lot`, `address`, `VISITOR_COUNT`, `SENSING_TIME` | 위경도 기반 위치 분석 가능. KST 기준 타임스탬프 포함 |
| `result_raw` | 회차별 방송 정보 및 결과 | `회차`, `공개일`, `분량`, `라운드`, `진행 내용`, `결과`, `탈락자` | 컬럼명에 한글 포함 → SQL 사용 시 `"컬럼명"` 형식 인용 필요 |
| `reviews_collected_catch` | 식당 리뷰 데이터 | `restaurant`, `reviewer`, `review_date`, `reviewer_rating`, `day_night` | PK 3컬럼(식당, 작성자, 날짜). 감성 분석, 평점 통계 등에 활용 가능 |
| `chief_trend_raw` | 출연자별 트렌드 변화 데이터 | `날짜`, `출연자`, `소스`, `값` | 출연자의 검색/언급 트렌드를 시계열로 기록. 소스는 네이버/유튜브 등 플랫폼 명.|

---

### ✅ 분석 시 유의사항

- `competition_result_raw_data` 내 이진 컬럼(`back`, `an`, `is_back`, `is_an`)은 상관계수 분석, 회귀 모델링용도
- `how_cook`, `ingrediant` 등 일부 텍스트 컬럼은 자유 형식 → NLP 전처리 필요
- `result_raw`의 컬럼명에 한글 포함 → SQL 쿼리 시 반드시 인용 처리
- 위치 기반 데이터(`geometry_result`)는 외부 공공데이터와 연계 분석 가능

---

## 3. 아키텍처 및 엔지니어링 (Engineering)
<img width="2768" height="1450" alt="image" src="https://github.com/user-attachments/assets/93b28355-ae14-48fe-b802-b7f8b247ea71" />

## 🛠 사용한 기술 스택 및 도구 (Tech Stack & Tools)

| 도구 | 사용 이유 |
|------|-----------|
| **Docker** | 프로젝트 환경을 표준화하여 로컬과 서버 간의 일관성을 유지하고, 모든 구성요소(Airflow, Streamlit 등)를 컨테이너로 손쉽게 배포/관리하기 위함 |
| **Apache Airflow** | 다양한 데이터 소스(유동인구, 트렌드 등)에서 수집/가공/적재되는 일련의 작업을 DAG(Directed Acyclic Graph)로 정의하여 **스케줄링 및 워크플로우 자동화**를 위해 사용 |
| **Streamlit** | 분석 결과를 접근 가능한 인터랙티브 웹 앱 형태로 제공하기 위해 사용|
| **Supabase** | 데이터 저장소 |


---

## 4.  트러블 슈팅 (Problem Solving)

• *문제 상황*: 크롤링이 원활하게 되지 않은 경우가 많았다.

<img width="2879" height="1620" alt="image" src="https://github.com/user-attachments/assets/a1f74817-5183-4c5b-8917-f3837331d442" />


1. 캐치테이블의 경우에는 스크롤을 내리려면 가운데 화면의 빈 공간에 마우스 클릭이 되어야만 스크롤이 가능하다.
   하지만 셀레니움으로 크롤링을 할 때 이를 설정하지 않아서 데이터 수집이 안되었다. 
    - 해결방법 : 현재 위의 사진에서 “135개의 매장 부분”에 마우스를 클릭하는 코드 추가
    
    ```python
        try:
                # 검증된 카드 셀렉터
                cards = driver.find_elements(By.CSS_SELECTOR, "#main > div.container.gutter-sm > div > div > div > div")
            except:
                cards = []
    ```

3. 무한 스크롤 방식으로 웹이 만들어져 있으며 홈페이지 메모리 절약을 위해 스크롤이 많이 내려가면 그 이전 식당의 정보는 추출할 수 없다.
    - 해결방법 : page down actions를 이용하여 스크롤이 많이 되지 않도록 설정하고 데이터를 조금씩 수집

```python
        try:
            if cards:
                last_card = cards[-1]
                actions = ActionChains(driver)
                actions.move_to_element(last_card).perform()
                time.sleep(0.5)
                actions.send_keys(Keys.PAGE_DOWN).pause(0.5).send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(1.5)
            else:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                time.sleep(1)
        except:
             driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
             
```

1. 식당 리뷰를 수집하기 위해서는 각각의 가게 사이트에 접근해야하지만 다들 형식이 달라서 자동화의 어려움이 있었음, 거기에 지도 시각화를 위한 경도, 위도가 필요했지만 이를 수집하는데 시간이 많이 걸릴 것으로 추측되었다.

```markdown
https://app.catchtable.co.kr/ct/shop/okdongsik?type=WAITING
# 아래와 같은 사항들이 118개 모든 가게별로 다르게 설정되어 있어서 자동화가 어려움 

# type=WAITING -> 웨이팅 여부
# okdongsik -> 가게의 별명
```

- 해결방법 : html “미리보기”항목을 이용하여 정보가 있는 요소를 찾은 뒤 페이로드를 통해서 가게의 alias와 type을 수집할 수 있음을 확인
- 아래의 사진을 보면 offset, size가 존재한다. 이 offset이 일정 규칙을 가지고 있어서 이를 가지고 자동화 수집이 가능하였다.

<img width="2879" height="1477" alt="image" src="https://github.com/user-attachments/assets/8a46aa8d-dd94-4493-855c-5db3fad98eb4" />


```markdown
    if current_count == 0:
        offset_str = "0"
    else:
        # 20:99:91-20:37:27-20:0:0 형식
        offset_str = f"{current_count}:99:91-{current_count}:37:27-{current_count}:0:0"
        
    print(f"\n[데이터 {current_count}번부터 요청 중...] Offset: {offset_str}")
    
    payload = {
        "paging": {"offset": offset_str, "size": 20},
        "divideType": "NON_DIVIDE",
        "curation": {"curationKey": TARGET_CURATION_KEY},
        "sort": {"sortType": "recommended"},
        "userInfo": {"clientGeoPoint": {"lat": 37.563398, "lon": 126.9863309}}
    }

```

- 수집을 진행하고 나니 위도와 경도가 포함된 파일이 생성이 되어서 따로 가게의 위치 정보를 수집할 필요가 없어져 데이터 수집이 한층 수월했다.

## 배운점

- 셀레니움을 이용하면 모든 데이터가 수집이 가능할 줄 알았지만 약간의 제약사항들을 잘 지켜야 한다는 것을 깨달았다.
- 겉으로 보이지 않는 데이터더라도 ‘개발자 도구’에서 요소들을 잘 찾아보면 필요한 데이터들이 수집이 가능하다.
- AI Agent가 크롤링을 원활하게 할 수 있도록 프롬포트를 작성하기 위해서는 CSS SELECTOR 인자는 사용자가 지정을 해야지 디버깅 없이 빠르게 수집 코드를 작성할 수 있다는 것을 알았다.

## 5. 회고 및 결론 (Retrospective)

• *잘한 점* : 데이터를 너무 다양한 소스에서 수집을 하다보니 통합하는 과정에서 전처리 요구사항이 많았다. 특히 서울시 유동인구 데이터를 수집했을 때 주소가 영어로 적혀있어서 이를 한글로 바꾸는데제약사항이 많았으며 지도 맵핑이 수월하게 될지 걱정이였다. 하지만 전처리를 완료한 뒤 AI Agent를 이용하여 지도 시각화를 진행할 때 요구사항에 대한 프롬포트를 잘 작성했기에 지도 시각화가 아주 수월하게 가능했다.

[서울시유동인구(IoT).md](%EC%84%9C%EC%9A%B8%EC%8B%9C%EC%9C%A0%EB%8F%99%EC%9D%B8%EA%B5%AC(IoT).md)


<img width="2169" height="1153" alt="image" src="https://github.com/user-attachments/assets/ced28b98-f32c-47b6-81fa-411713efd9e4" />


• 아쉬운 점 &* 개선 계획

- 심사위원 합격 예측 분석을 진행 할 때 수집 데이터가 너무 적어서  실제로 쓸 만한 로지스틱 회귀분석이 모델이 나오지 못했다.
- 흑백요리사1의 데이터도 수집을 하게 되서 이를 현재 데이터와 통합한다면 더욱 좋은 모델링을 만들고 유의미한 결과를 낼 수 있을 것 같다.
- 상권분석을 위해서는 매출 데이터가 존재해야 더욱 낙수효과를 분석할 수 있을 것 같은데 매출 데이터는 신한카드로 한정이 되어있어서 제대로된 낙수효과를 측정하지 못한게 아쉽다.
- ‘행정동’ 단위가 아닌 ‘동’단위로 분석을 했으면 낙수효과를 제대로 측정이 가능했을 텐데 행정동 단위로 밖에 수집이 안되어서 아쉬웠다.
- 데이터 라벨링을 수기로 작성해야 하는데 사람 기준에 따라 애매하게 요리들이 존재하여 정확한 라벨링이 불가능해 아쉬웠다.
