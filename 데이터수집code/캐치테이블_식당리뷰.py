import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import os
import re
import glob

# ==========================================
# 설정
# ==========================================
INPUT_FILE = "캐치테이블_가게정보.csv"
HISTORY_FILE = "review_count_history.csv"
OUTPUT_FILE = f"reviews_collected_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
CUTOFF_DATE = datetime.datetime(2025, 12, 9)  # 이 날짜 이전 리뷰는 수집 중단
FORCE_CRAWL = False # True: 히스토리 무시하고 무조건 크롤링, False: 변경된 것만 크롤링

# ==========================================
# 함수 정의
# ==========================================

def get_driver():
    options = Options()
    #options.add_argument("--headless") # Airflow 등 서버 환경에서는 주석 해제 필요
    options.add_argument("--window-size=1600,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    else:
        return pd.DataFrame(columns=['url', 'restaurant_name', 'review_count', 'last_updated'])

def save_history(df):
    df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

def modify_url_for_reviews(url):
    """
    가게 상세 URL을 리뷰 모아보기 URL로 변환
    규칙: '?type' 앞에 'review' 추가, 끝에 '&sortingFilter=D' (최신순) 추가
    """
    if "/review" in url:
        if "sortingFilter=D" not in url:
             return url + "&sortingFilter=D"
        return url
    if "?" in url:
        base, query = url.split("?", 1)
        if base.endswith("/"): base = base[:-1]
        new_url = f"{base}/review?{query}&sortingFilter=D"
    else:
        if url.endswith("/"): url = url[:-1]
        new_url = f"{url}/review?sortingFilter=D"
    return new_url

def parse_date(date_str):
    today = datetime.datetime.now()
    try:
        if "일 전" in date_str:
            days = int(re.search(r'(\d+)', date_str).group(1))
            return today - datetime.timedelta(days=days)
        elif "시간 전" in date_str or "분 전" in date_str or "방금" in date_str:
            return today
        elif "어제" in date_str:
            return today - datetime.timedelta(days=1)
        else:
            return datetime.datetime.strptime(date_str, "%Y.%m.%d")
    except:
        return today

def scrape_reviews(driver, url, restaurant_name, existing_reviews_set=None):
    """리뷰 상세 페이지 크롤링 함수 - 최적화 버전
    
    최적화 포인트:
    1. 기준일 이전 리뷰 발견 시 즉시 반환 (조기 종료)
    2. 이미 처리한 카드 인덱스 추적으로 중복 처리 방지
    3. 연속 오래된 리뷰 감지로 조기 중단
    """
    review_url = modify_url_for_reviews(url)
    driver.get(review_url)
    time.sleep(5)

    collected_reviews = []
    processed_hashes = set()
    # ★ 핵심: 기존 리뷰 1개만 발견해도 즉시 중단 (최신순 정렬이므로 이전 리뷰는 이미 수집됨)
    consecutive_old_reviews = 0  # 연속 오래된 리뷰 카운터
    max_consecutive_old = 3  # 연속 3개 오래된 리뷰면 조기 중단
    
    last_processed_index = 0  # 마지막으로 처리한 카드 인덱스 추적

    scroll_count = 0
    max_scrolls = 50 
    
    while scroll_count < max_scrolls:
        try:
            # 검증된 카드 셀렉터 (Notebook과 동일)
            cards = driver.find_elements(By.CSS_SELECTOR, "#main > div.container.gutter-sm > div > div > div > div")
        except:
            cards = []
            
        # 첫 시도 시 카드 없으면 로딩 대기
        if not cards and scroll_count == 0:
            time.sleep(3)
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, "#main > div.container.gutter-sm > div > div > div > div")
            except:
                pass
        
        # 새로 로드된 카드만 처리 (이전에 처리한 카드 스킵)
        if len(cards) <= last_processed_index:
            # 새 카드가 없으면 스크롤 시도
            scroll_count += 1
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                time.sleep(1)
            except:
                pass
            continue
        
        should_stop = False
        
        for i, card in enumerate(cards[last_processed_index:], start=last_processed_index):
            try:
                # ★ 리뷰 카드 유효성 검증: article 태그가 없으면 리뷰 카드가 아님 (광고, 빈 div 등)
                try:
                    article = card.find_element(By.CSS_SELECTOR, "article")
                except:
                    continue  # 리뷰 카드가 아니면 스킵

                # 1. 작성자
                try:
                    reviewer = card.find_element(By.CSS_SELECTOR, "article > div.__header > div.__user-info > a > h4 > span").text.strip()
                except:
                    try:
                        # 대체 셀렉터 시도
                        reviewer = card.find_element(By.CSS_SELECTOR, "article h4 span").text.strip()
                    except:
                        continue  # 작성자 없으면 스킵 (유효한 리뷰가 아님)

                # 작성자가 비어있으면 스킵
                if not reviewer or reviewer == "":
                    continue

                # 2. 평점
                try:
                    rating_el = card.find_element(By.CSS_SELECTOR, "article > div.__header > div.__review-meta.__review-meta--with-rating > div > a > div")
                    rating = rating_el.text.strip()
                except:
                    try:
                        # 대체 셀렉터 시도
                        rating_el = card.find_element(By.CSS_SELECTOR, "article div.__review-meta div")
                        rating = rating_el.text.strip()
                    except:
                        rating = ""  # 평점 없으면 빈 문자열

                # 3. 날짜
                try:
                    date_el = card.find_element(By.CSS_SELECTOR, "article > div.__header > div.__review-meta.__review-meta--with-rating > span")
                    date_text = date_el.text.strip()
                except:
                    # 대체: 카드 텍스트에서 날짜 패턴 추출
                    match = re.search(r'\d{4}\.\d{1,2}\.\d{1,2}|\d+일 전|어제|방금|시간 전|분 전', card.text)
                    date_text = match.group(0) if match else ""

                # 날짜가 없으면 스킵 (유효한 리뷰가 아님)
                if not date_text or date_text == "":
                    continue

                # ★ 핵심 최적화: 기준일 이전 리뷰 발견 시 즉시 함수 반환
                review_date = parse_date(date_text)
                if review_date < CUTOFF_DATE:
                    consecutive_old_reviews += 1
                    if consecutive_old_reviews >= max_consecutive_old:
                        print(f"\n   >>> 기준일({CUTOFF_DATE.strftime('%Y-%m-%d')}) 이전 리뷰 {max_consecutive_old}개 연속 발견 - 즉시 중단")
                        return collected_reviews  # 즉시 함수 반환!
                    continue
                else:
                    consecutive_old_reviews = 0  # 새로운 리뷰면 리셋

                # 4. 방문 유형(점심/저녁)
                try:
                    day_night = card.find_element(By.CSS_SELECTOR, "article > div.__header > div.__review-meta.__review-meta--with-rating > div > p").text.strip()
                except:
                    day_night = ""  # 방문 유형 없으면 빈 문자열

                # 중복 수집 방지
                msg_hash = hash(f"{reviewer}_{date_text}_{restaurant_name}")
                review_key = (restaurant_name, reviewer, date_text)

                # ★ 핵심: 이미 수집된 리뷰 1개만 발견해도 즉시 중단!
                # 최신순 정렬이므로, 기존 리뷰가 나타나면 그 이후는 모두 수집된 것임
                if existing_reviews_set and review_key in existing_reviews_set:
                    print(f"\n   >>> 기존 수집 리뷰 발견 ({reviewer}, {date_text}) - 이 가게 수집 즉시 종료")
                    return collected_reviews  # 즉시 함수 반환!

                # 새로운 리뷰 발견
                if msg_hash not in processed_hashes:
                    processed_hashes.add(msg_hash)
                    collected_reviews.append({
                        "restaurant": restaurant_name,
                        "reviewer": reviewer,
                        "review_date": date_text,
                        "reviewer_rating": rating,
                        "day_night": day_night
                    })
            except:
                continue
        
        # 처리한 인덱스 업데이트
        last_processed_index = len(cards)
            
        # 스크롤 동작 (ActionChains)
        try:
            if cards:
                last_card = cards[-1]
                actions = ActionChains(driver)
                actions.move_to_element(last_card).perform()
                time.sleep(0.5)
                actions.send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(1.5)
            else:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                time.sleep(1)
        except:
             driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        
        scroll_count += 1
        
    return collected_reviews

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"오류: {INPUT_FILE} 파일이 없습니다.")
        return

    df = pd.read_csv(INPUT_FILE)
    history_df = load_history()

    # ★ 핵심: 기존 수집된 리뷰 모두 로드 (모든 reviews_collected_*.csv 파일)
    existing_reviews_set = set()
    existing_files = glob.glob("reviews_collected_*.csv")
    
    if existing_files:
        print(f"기존 수집 파일 {len(existing_files)}개 발견, 로드 중...")
        for file_path in existing_files:
            try:
                temp_df = pd.read_csv(file_path, encoding='utf-8-sig')
                for _, row in temp_df.iterrows():
                    key = (row['restaurant'], row['reviewer'], str(row['review_date']))
                    existing_reviews_set.add(key)
                print(f"  - {file_path}: {len(temp_df)}개 리뷰 로드")
            except Exception as e:
                print(f"  - {file_path}: 로드 실패 ({e})")
        print(f"총 {len(existing_reviews_set)}개 기존 리뷰 로드 완료 (중복 방지용)\n")
    else:
        print("기존 수집 파일 없음 - 전체 수집 시작\n")

    driver = get_driver()

    all_collected_data = []
    history_updates = []

    print(f"총 {len(df)}개 식당 처리 시작...")
    
    try:
        for idx, row in df.iterrows():
            url = row['URL']
            restaurant_name = row['restaurant'] if 'restaurant' in row else str(idx)
            
            try:
                # 1. 메인 접속
                driver.get(url)
                time.sleep(3)
                
                # 2. 리뷰 개수 확인 (Notebook의 검증된 XPath 사용)
                try:
                    count_el = driver.find_element(By.XPATH, '//*[@id="wrapperDiv"]/div[1]/div[1]/div[3]/div/span[3]')
                    count_text = count_el.text
                    review_count = int(re.search(r'(\d+)', count_text.replace(',', '')).group(1))
                except:
                    review_count = 0
                
                print(f"[{idx+1}/{len(df)}] {restaurant_name}: {review_count}개", end=" ")
                
                # 3. 변경 감지
                prev_record = history_df[history_df['url'] == url]
                need_crawl = False

                if FORCE_CRAWL:
                    print("-> [강제 수집]", end=" ")
                    need_crawl = True
                elif prev_record.empty:
                    print("-> [신규]", end=" ")
                    need_crawl = True
                else:
                    last_count = int(prev_record.iloc[0]['review_count'])
                    if last_count != review_count:
                        print(f"-> [변동: {last_count}->{review_count}]", end=" ")
                        if review_count > 0: need_crawl = True
                    else:
                        print("-> [변동없음]", end=" ")
                
                history_updates.append({
                    'url': url,
                    'restaurant_name': restaurant_name,
                    'review_count': review_count,
                    'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # 4. 크롤링 수행
                if need_crawl:
                    print("-> 수집 시작")
                    reviews = scrape_reviews(driver, url, restaurant_name, existing_reviews_set)
                    if reviews:
                        all_collected_data.extend(reviews)
                        print(f"   >>> {len(reviews)}건 수집 완료")
                    else:
                        print("   >>> 수집된 리뷰 없음")
                else:
                    print("") 
                    
            except Exception as e:
                print(f"\n   !!! 에러 발생: {e}")

    finally:
        driver.quit()

    # 결과 저장 (기존 데이터 + 새 데이터 병합)
    if all_collected_data:
        new_df = pd.DataFrame(all_collected_data)

        # 기존 파일이 있으면 병합
        if os.path.exists(OUTPUT_FILE):
            try:
                existing_df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
                result_df = pd.concat([existing_df, new_df], ignore_index=True)
                # 중복 제거 (혹시 모를 중복 방지)
                result_df = result_df.drop_duplicates(subset=['restaurant', 'reviewer', 'review_date'], keep='first')
                print(f"\n기존 {len(existing_df)}건 + 신규 {len(new_df)}건 = 총 {len(result_df)}건")
            except:
                result_df = new_df
                print(f"\n신규 수집: {len(result_df)}건")
        else:
            result_df = new_df
            print(f"\n신규 수집: {len(result_df)}건")

        result_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"결과 저장 완료: {OUTPUT_FILE}")
    else:
        print("\n새로 수집된 리뷰가 없습니다.")
        
    # 히스토리 업데이트
    if history_updates:
        new_history = pd.DataFrame(history_updates)
        if not history_df.empty:
            history_df = history_df[~history_df['url'].isin(new_history['url'])]
            final_history = pd.concat([history_df, new_history], ignore_index=True)
        else:
            final_history = new_history
        save_history(final_history)
        print("히스토리 업데이트 완료")

if __name__ == "__main__":
    main()
