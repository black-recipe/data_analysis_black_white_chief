from curl_cffi import requests
import json

url = "https://ct-api.catchtable.co.kr/api/v6/search/curation/list"

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://app.catchtable.co.kr",
    "pragma": "no-cache",
    "referer": "https://app.catchtable.co.kr/",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36"
    ),
    "x-device-id": "056de229-ce37-40c9-b19f-ce0d832645ac",
    "x-requested-with": "XMLHttpRequest",
    "x-transaction-id": "6",
    "search-list-page-visit-id": "1768358332824"
}

# ▶ DevTools에서 그대로 복사한 Cookie 문자열 사용
cookies = {
    "_hackle_hid": "244dc554-302d-4337-965c-c4e7a5e433ba",
    "_hackle_did_7dQgTKfweH0n436c9aJLVh84yOncuWxD": "244dc554-302d-4337-965c-c4e7a5e433ba",
    "_ga": "GA1.3.817996455.1768292094",
    "_gid": "GA1.3.527876262.1768292095",
    "ab180ClientId": "c64a1dd2-6841-416a-8a19-5555e4886f76",
    "_hackle_session_id_eH0n436c9aJLVh84yOncuWxD": "1768355246635.284673c5",
    "__cf_bm": "l96j2kWG15HyVJMYmPwJKgypmM7z7kxVGrEwz1cX5Aw-1768358298-1.0.1.1-GPufpHLzhwZ6s6chkrCZvOoHeqQhaHojmruwieL53CIfkd7D_1towOKPol8KkR4lfsb3QltIloZGoBPGpVp8vtXz_9wlrBEERCLYHXrKml4"
}

payload = {
    "paging": {"offset": "0", "size": 20},
    "divideType": "NON_DIVIDE",
    "serviceType": None,
    "curation": {"curationKey": "classwars2-all"},
    "filters": {
        "displayRegionCodes": [
            "CAT011","CAT011001","CAT011002","CAT011003","CAT011004",
            "CAT011005","CAT011006","CAT011007","CAT011008","CAT011009","CAT011010"
        ],
        "contractedType": "ALL",
        "includeNotContracted": True
    },
    "sort": {"sortType": "recommended"},
    "userInfo": {
        "clientGeoPoint": {
            "lat": 37.568620024258024,
            "lon": 126.98024088704886
        }
    },
    "aggregations": [
        {"type": "LEGAL_SIDO", "method": "COUNT"},
        {"type": "FACILITY", "method": "COUNT"},
        {"type": "BENEFIT", "method": "COUNT"},
        {"type": "SHOP_GEO_POINT", "method": "GEO_BOUND"}
    ]
}

response = requests.post(
    url,
    headers=headers,
    cookies=cookies,
    json=payload,
    impersonate="chrome",
    timeout=10
)

response.raise_for_status()


data = response.json()

# JSON 파일로 저장
with open('catchtable_result.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Saved result to catchtable_result.json")
