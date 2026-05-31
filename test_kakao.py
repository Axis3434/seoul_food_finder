import requests
url = "https://dapi.kakao.com/v2/local/search/keyword.json"
headers = {"Authorization": "KakaoAK ccb63a973ba7f41085c8a8220ac2b77d"}
params = {"query": "돈까스", "x": 127.0016, "y": 37.5833, "radius": 2000}
response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.text)
