네이버 API와 pytrend를 사용하여 데이터를 수집하여 supabase에 저장하는 코드를 작성해주세요.

1. 각 API의 key값은 .env 파일에 저장되어 있습니다.
2. #-*- coding: utf-8 -*-
import os
import sys
import urllib.request
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
url = "https://openapi.naver.com/v1/datalab/search";
body = "{\"startDate\":\"2017-01-01\",\"endDate\":\"2017-04-30\",\"timeUnit\":\"month\",\"keywordGroups\":[{\"groupName\":\"한글\",\"keywords\":[\"한글\",\"korean\"]},{\"groupName\":\"영어\",\"keywords\":[\"영어\",\"english\"]}],\"device\":\"pc\",\"ages\":[\"1\",\"2\"],\"gender\":\"f\"}";

request = urllib.request.Request(url)
request.add_header("X-Naver-Client-Id",client_id)
request.add_header("X-Naver-Client-S₩ecret",client_secret)
request.add_header("Content-Type","application/json")
response = urllib.request.urlopen(request, data=body.encode("utf-8"))
rescode = response.getcode()
if(rescode==200):
    response_body = response.read()
    print(response_body.decode('utf-8'))
else:
    print("Error Code:" + rescode)


3. startDate는 무조건 2025년 12월 9일

4. endDate는 무조건 2026년 1월 20일

5. timeUnit는 일간

keywordGroups는 supabase의 chief_trend_keyword 테이블의 name컬럼을 활용하여 key값, keyword의 value를 활용하여 keywordGroups를 구성합니다. 

keywordGroups.groupName은 supabase의 chief_trend_keyword 테이블의 name컬럼의 값
keywordGroups.keywords는 supabase의 chief_trend_keyword 테이블의 keyword컬럼의 값

device, gender, ages는 무조건 설정 안함 : 모든환경

6. 값을 가져온 후 

"results": [
    {
      "title": "한글",
      "keywords": [
        "한글",
        "korean"
      ],
      "data": [
        {
          "period": "2017-01-01",
          "ratio": 47.0
        },
        {
          "period": "2017-02-01",
          "ratio": 53.23
        },
        {
          "period": "2017-03-01",
          "ratio": 100.0
        },
        {
          "period": "2017-04-01",
          "ratio": 85.32
        }
      ]
    },
에서 title의 값을 supabase의 chief_trend_value 테이블의 '출연자' 컬럼에,
data의 period의 값을 chief_trend_value 테이블의 날짜 컬럼에,
data의 ratio의 값을 chief_trend_value 테이블의 값 컬럼에 
그리고 '소스' 컬럼에는 'datalab'를 입력합니다.

이렇게 데이터를 supabase의 chief_trend_value 테이블에 저장합니다.

반드시 supabase의 chief_trend_value 테이블에 데이터를 저장하는 코드를 작성해주세요.

제가 확인할 수 있게 코드를 작성해주세요.
