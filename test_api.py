import requests
import json

url = "https://api.odcloud.kr/api/3045247/v1/uddi:12a36b40-6230-4401-b647-b8456a789c7f"
params = {
    "serviceKey": "ad11c002be7dc354b59b2714e4f5a5d5ce371402b4bf6e866502700ac267cab6",
    "page": 1,
    "perPage": 10,
    "cond[업소명::EQ]": "돈까스보라"
}

response = requests.get(url, params=params)
with open("test_out2.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=2)
