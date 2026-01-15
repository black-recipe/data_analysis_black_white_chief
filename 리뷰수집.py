import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import os
import re

# ==========================================
# 설정
# ==========================================
INPUT_FILE = "캐치테이블_가게정보.csv"
HISTORY_FILE = "review_count_history.csv"
OUTPUT_FILE = f"reviews_collected_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
CUTOFF_DATE = datetime.datetime(2025, 12, 9)

# ==========================================
# 함수 정의
# ==========================================

def get_driver():
    """Selenium WebDriver 설정 및 반환"""
    options = Options()
    # options.add_argument("--headless") # 필요 시 주석 해제 (스크롤 동작을 위해 visible 모드 권장)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

def load_previous_history():
    """이전 리뷰 개수 기록 불러오기"""
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    else:
        return pd.DataFrame(columns=['url', 'restaurant_name', 'review_count', 'display_name', 'last_updated'])

def save_history(history_df):
    """리뷰 개수 기록 저장"""
    history_df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

def modify_url_for_reviews(url):
    """
    가게 상세 URL을 리뷰 모아보기 URL로 변환
    규칙: '?type' 앞에 'review' 추가, 끝에 '&sortingFilter=D' (최신순) 추가
    예: https://app.catchtable.co.kr/ct/shop/tteoksan?type=DINING
    -> https://app.catchtable.co.kr/ct/shop/tteoksan/review?type=DINING&sortingFilter=D
    """
    if "/review" in url:
        return url + "&sortingFilter=D"
    
    # ?가 있는 경우
    if "?" in url:
        base, query = url.split("?", 1)
        # base 끝에 /review가 없으면 추가 (혹시 모를 슬래시 처리)
        if base.endswith("/"):
            base = base[:-1]
        new_url = f"{base}/review?{query}&sortingFilter=D"
    else:
        if url.endswith("/"):
            url = url[:-1]
        new_url = f"{url}/review?sortingFilter=D"
        
    return new_url

def parse_date(date_str):
    """
    날짜 문자열 파싱
    형식 예: '2025.12.09', '3일 전', '어제', '오늘' 등 처리 필요
    캐치테이블의 날짜 형식을 확인해야 하나, 일반적인 경우를 대비해 작성.
    보통 'YYYY.MM.DD' 형식이 많음.
    """
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
            # 2025.12.09 형식 가정
            return datetime.datetime.strptime(date_str, "%Y.%m.%d")
    except Exception as e:
        print(f"날짜 파싱 에러 ({date_str}): {e}")
        return today # 에러 시 오늘로 간주하여 수집 포함

def scrape_restaurant_reviews(driver, url, restaurant_name):
    """개별 식당 리뷰 스크랩"""
    review_url = modify_url_for_reviews(url)
    driver.get(review_url)
    time.sleep(3) # 페이지 로드 대기
    
    collected_reviews = []
    processed_hashes = set() # 중복 방지용 (작성자+내용+날짜 해시)
    
    scrolling = True
    
    while scrolling:
        # 현재 보이는 리뷰 카드들 수집
        try:
            # 리뷰 카드 클래스명은 실제 사이트 구조에 따라 다를 수 있으나, 
            # 일반적인 구조나 text 기반으로 탐색.
            # 여기서는 review-item 또는 유사 구조를 찾음.
            # *실제 클래스명을 모르므로 포괄적인 div 탐색 후 내부 요소 확인 전략 사용*
            # 캐치테이블 구조상 보통 `div[class*="ReviewItem"]` 형태일 가능성 높음.
            # 하지만 안전하게 가시적인 카드들을 찾기 위해 CSS Selector 사용
            cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'ReviewItem')]") # 가상 클래스명
            
            # 만약 클래스명을 못찾으면 좀 더 broad한 검색 (디버깅 필요할 수 있음)
            if not cards:
                # 구조가 다를 수 있으니 body 안의 텍스트가 있는 div들 중 추정
                cards = driver.find_elements(By.CSS_SELECTOR, "div.saved-restaurant-list-item") # 예시
            
            # 실제 캐치테이블 리뷰 구조 추정 (id나 특정 클래스 활용)
            # 팁: 페이지 소스를 볼 수 없으므로, driver.page_source를 덤프하는게 좋지만, 
            # 여기서는 스크립트 작성이므로 일반적인 순서로 작성.
            
            # 수정: driver.find_elements(By.CLASS_NAME, "css-1... ") 같은 랜덤 클래스일 수 있음.
            # 식당 상세 페이지의 리뷰 섹션은 보통 일정한 패턴이 있음.
            # 일단 cards를 가져왔다고 가정하고 진행. 
            pass
            
        except Exception as e:
            print(f"카드 찾기 에러: {e}")
            break

        visible_cards = driver.find_elements(By.CSS_SELECTOR, "div > div > div.css-170k82y") # 예시 selector (수정 필요 가능성 높음)
        # 더 범용적인 selector: 리뷰 텍스트가 포함된 컨테이너
        # 캐치테이블 리뷰 리스트 컨테이너
        
        # 실제 DOM 구조를 모르기 때문에 XPATH로 넓게 잡습니다.
        # "더보기"가 없는 전체 노출 상태여야 함.
        
        # *** 중요: 스크롤 로직 구현 ***
        # 프롬프트에서 제공된 스크롤 로직 사용
        
        # 데이터를 긁기 위한 요소 탐색 (현재 화면에 보이는 것만)
        # 구체적인 selector가 없으므로 CSS selector는 가상의 것을 사용하되, 
        # 사용자가 필요시 수정할 수 있도록 주석 처리
        
        # (임시) 리뷰 컨테이너 찾기
        # review_cards = driver.find_elements(By.CSS_SELECTOR, ".review-item-container") 
        
        # **실제 캐치테이블 구조에 맞춘 추정 (최근 구조 감안)**
        review_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'shop-review-card')] | //div[contains(@class, 'ReviewCard')]")
        
        # 만약 못 찾으면... 일단 스크롤만 진행하며 에러 발생 여부 확인
        if not review_cards:
            # 혹시 모르니 포괄적인 div 탐색 (li 태그 등)
            review_cards = driver.find_elements(By.XPATH, "//div[contains(@style, 'cursor: pointer')]//span[contains(text(), '202')]")
            # 부모 요소 찾기
            review_cards = [el.find_element(By.XPATH, "./../../..") for el in review_cards]

        found_new_data = False
        
        for card in review_cards:
            try:
                # 텍스트 추출
                text_content = card.text
                
                # 데이터 파싱 (단순 텍스트 분리 시도)
                lines = text_content.split('\n')
                
                # 데이터 추출 로직 (구조에 따라 수정 필요)
                # 예: 
                # Reviewer Name
                # Rating
                # Date
                # Content ...
                
                # 여기서는 element 내의 class 별로 찾는 정석적인 방법 시도
                try:
                    reviewer = card.find_element(By.CSS_SELECTOR, ".name").text
                except:
                    reviewer = "Unknown"
                    
                try:
                    rating_el = card.find_element(By.CSS_SELECTOR, ".rating") # 별점 등
                    rating = rating_el.get_attribute("aria-label") or rating_el.text
                except:
                    rating = "Unknown"
                    
                try:
                    # 날짜 찾기 (2025.12.09 형태 찾기)
                    date_el = card.find_element(By.CSS_SELECTOR, ".date")
                    date_text = date_el.text
                    review_date = parse_date(date_text)
                except:
                    # 텍스트에서 날짜 패턴 찾기
                    import re
                    match = re.search(r'\d{4}\.\d{1,2}\.\d{1,2}', text_content)
                    if match:
                        date_text = match.group(0)
                        review_date = parse_date(date_text)
                    else:
                        review_date = datetime.datetime.now() # 못 찾으면 최신으로 가정
                
                # 날짜 필터링
                if review_date < CUTOFF_DATE:
                    scrolling = False # 기준일 이전 데이터 도달 시 중단
                    break
                
                # 방문 유형 (점심/저녁) - 보통 리뷰에 포함되거나 메타데이터에 있음
                try:
                    day_night = card.find_element(By.CSS_SELECTOR, ".visit-type").text
                except:
                    day_night = "Unknown"
                
                # 데이터 중복 검사
                msg_hash = hash(f"{reviewer}_{date_text}_{restaurant_name}")
                if msg_hash not in processed_hashes:
                    processed_hashes.add(msg_hash)
                    collected_reviews.append({
                        "restaurant": restaurant_name,
                        "reviewer": reviewer,
                        "review_date": date_text, # 원본 텍스트 저장
                        "reviewer_rating": rating,
                        "day_night": day_night
                    })
                    found_new_data = True
                    
            except Exception as e:
                continue
        
        if not scrolling:
            break
            
        # 3. 스크롤 (가장 마지막 요소로 이동 -> PageDown x 2)
        try:
            # 현재 보이는 마지막 카드로 이동
            # cards 변수를 갱신해야 함
            visible_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'ReviewCard')]") # 위와 동일한 selector 사용
            
            if visible_cards:
                last_card = visible_cards[-1]
                
                actions = ActionChains(driver)
                actions.move_to_element(last_card).perform()
                time.sleep(0.5)
                
                # PageDown 입력
                # body에 보내는 게 안전할 수 있으나, 지침대로 actions 사용
                actions.send_keys(Keys.PAGE_DOWN).pause(0.5).send_keys(Keys.PAGE_DOWN).perform()
                
                time.sleep(1.5)
            else:
                # 카드가 안보이면 강제 스크롤
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                time.sleep(1)

        except Exception as e:
            print(f"스크롤 중 에러: {e}")
            # 실패 시 body를 대상으로 시도
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(.5)
            
    return collected_reviews

def main():
    # 1. 파일 로드
    if not os.path.exists(INPUT_FILE):
        print(f"오류: {INPUT_FILE} 파일이 없습니다.")
        return

    df = pd.read_csv(INPUT_FILE)
    history_df = load_previous_history()
    
    driver = get_driver()
    all_reviews = []
    
    updates = [] # history 업데이트용
    
    print(f"총 {len(df)}개의 식당을 확인합니다.")
    
    for idx, row in df.iterrows():
        url = row['URL']
        # 가게명은 CSV에 없으면 URL 등에서 추출하거나, 사이트에서 가져와야 함.
        # 일단 CSV에 있다고 가정하거나, 사이트 접속 후 가져옴.
        
        try:
            # 1. 가게 메인 접속 및 정보 확인
            driver.get(url)
            time.sleep(3)
            
            # 가게명 추출 (div class명은 사이트마다 다르나 h1, h2 등 시도)
            try:
                name_el = driver.find_element(By.CSS_SELECTOR, "h1") # 보통 헤더에 있음
                restaurant_name = name_el.text
            except:
                restaurant_name = f"Unknown_{idx}"
            
            # 리뷰 개수 추출
            # "리뷰 123개" 또는 별점 옆 숫자 등
            try:
                # text에서 '리뷰'와 숫자가 포함된 요소 찾기
                count_el = driver.find_element(By.XPATH, "//*[contains(text(), '리뷰')]/parent::*")
                count_text = count_el.text
                # 숫자만 추출
                review_count = int(re.search(r'(\d+)', count_text.replace(',', '')).group(1))
            except:
                review_count = 0 # 못 찾으면 0으로 간주 (항상 크롤링 시도 가능성)

            print(f"[{idx+1}/{len(df)}] {restaurant_name}: 현재 {review_count}개")
            
            # 비교
            prev_record = history_df[history_df['url'] == url]
            need_crawl = False
            
            if prev_record.empty:
                need_crawl = True
                print(" -> 신규/기록없음, 크롤링 진행")
            else:
                last_count = int(prev_record.iloc[0]['review_count'])
                if last_count != review_count:
                    need_crawl = True
                    print(f" -> 변동있음 ({last_count} -> {review_count}), 크롤링 진행")
                else:
                    print(" -> 변동없음, 건너뜀")
            
            # 히스토리 업데이트 준비
            updates.append({
                'url': url,
                'restaurant_name': restaurant_name,
                'review_count': review_count,
                'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 2. 크롤링 진행
            if need_crawl:
                reviews = scrape_restaurant_reviews(driver, url, restaurant_name)
                all_reviews.extend(reviews)
                print(f" -> {len(reviews)}개 리뷰 수집 완료")
                
        except Exception as e:
            print(f"에러 발생 ({url}): {e}")
            
    driver.quit()
    
    # 결과 저장
    if all_reviews:
        result_df = pd.DataFrame(all_reviews)
        result_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"수집 완료: {OUTPUT_FILE} 저장됨 ({len(result_df)}건)")
    else:
        print("수집된 새로운 리뷰가 없습니다.")

    # 히스토리 갱신
    new_history = pd.DataFrame(updates)
    # 기존 히스토리와 병합 (URL 기준 덮어쓰기)
    if not history_df.empty:
        # 기존 것 중 이번에 업데이트 안된 것만 남김
        history_df = history_df[~history_df['url'].isin(new_history['url'])]
        final_history = pd.concat([history_df, new_history], ignore_index=True)
    else:
        final_history = new_history
        
    save_history(final_history)
    print("히스토리 업데이트 완료")

if __name__ == "__main__":
    main()
