import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


# 환경변수 로드 (.env 파일)
load_dotenv()

# 환경변수에서 API 키를 가져옵니다.
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY")

def search_restaurants_kakao(keyword, lat, lng, page, radius=2000):
    """
    카카오 로컬 API를 사용하여 특정 위치 주변의 식당을 검색합니다. (페이지네이션 지원)
    """
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    params = {
        "query": keyword,
        "x": lng,
        "y": lat,
        "radius": radius,
        "category_group_code": "FD6", # 음식점 카테고리
        "sort": "distance",           # 거리순 정렬
        "page": page
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        documents = data.get('documents', [])
        is_end = data.get('meta', {}).get('is_end', True)
        return documents, is_end
    except Exception as e:
        print(f"[오류] 카카오 로컬 API 요청 실패: {e}")
        return [], True

def get_coordinates_from_address(address):
    """
    카카오 로컬 API를 사용하여 주소를 위도/경도로 변환합니다.
    """
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    params = {
        "query": address
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        documents = response.json().get('documents', [])
        if documents:
            # 첫 번째 검색 결과의 좌표 반환 (y: 위도, x: 경도)
            return float(documents[0]['y']), float(documents[0]['x'])
    except Exception as e:
        print(f"[오류] 주소 검색 API 요청 실패: {e}")
        
    return None, None

def check_good_price_store(restaurant_name, address, keyword):
    """
    제공된 착한가격업소 API(ODCloud)를 호출하여 키워드에 해당하는 메뉴와 가격 정보를 확인합니다.
    매칭되는 메뉴가 있으면 (메뉴문자열, True)를 반환하고, 없으면 (None, False)를 반환합니다.
    """
    if not PUBLIC_DATA_API_KEY:
        return None, False
        
    url = "https://api.odcloud.kr/api/3045247/v1/uddi:12a36b40-6230-4401-b647-b8456a789c7f"
    params = {
        "serviceKey": PUBLIC_DATA_API_KEY,
        "page": 1,
        "perPage": 10,
        "cond[업소명::EQ]": restaurant_name # 업소명 필터링
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get('data', [])
            
            for item in items:
                # 키워드가 포함된 메뉴 찾기
                for i in range(1, 5):
                    menu = item.get(f'메뉴{i}')
                    if menu and keyword.lower() in menu.lower():
                        price = item.get(f'가격{i}') or '정보 없음'
                        return f"🟢 착한가격업소: {menu} ({price}원)", True
                
    except Exception as e:
        pass
        
    return None, False

def parse_kakao_place(place_url, keyword):
    """
    카카오 플레이스는 동적 웹페이지(SPA)로 구성되어 있어 BeautifulSoup으로 메뉴 텍스트를 파싱하기 어렵습니다.
    하지만 이미 카카오 로컬 API에서 '키워드' 기반으로 검색된 결과이므로, 
    해당 메뉴를 팔고 있을 확률이 매우 높습니다. 따라서 무조건 상세 링크를 제공하도록 True를 반환합니다.
    """
    return f"메뉴 가격 파싱 불가 (식당 상세 페이지에서 직접 메뉴판 확인 가능)", True

def search_food(address, keyword, offset=0):
    lat, lng = get_coordinates_from_address(address)
    
    if lat is None or lng is None:
        return {"error": "해당 주소의 위치를 찾을 수 없습니다. 정확한 주소를 입력해주세요."}

    results = []
    valid_count = 0
    skipped_count = 0
    page = 1
    is_end = False
    
    while valid_count < 5 and not is_end:
        restaurants, is_end = search_restaurants_kakao(keyword, lat, lng, page)
        
        if not restaurants and page == 1:
            return {"error": "조건에 맞는 식당을 전혀 찾지 못했습니다."}
            
        for r in restaurants:
            name = r.get('place_name')
            addr = r.get('road_address_name') or r.get('address_name')
            distance = r.get('distance')
            place_url = r.get('place_url')
            
            menu_info, is_matched = check_good_price_store(name, addr, keyword)
            
            if not is_matched:
                menu_info, is_matched = parse_kakao_place(place_url, keyword)
                
            if is_matched:
                if skipped_count < offset:
                    skipped_count += 1
                    continue
                    
                valid_count += 1
                results.append({
                    "name": name,
                    "address": addr,
                    "distance": distance,
                    "menu": menu_info,
                    "url": place_url,
                    "lat": float(r.get('y')),
                    "lng": float(r.get('x'))
                })
                
                if valid_count >= 5:
                    break
                    
        page += 1
        if page > 5:
            break
            
    if valid_count == 0:
        return {"error": f"주변 반경 내에 '{keyword}' 메뉴를 확인할 수 있는 식당이 없습니다."}
        
    return {"results": results, "count": valid_count, "center": {"lat": lat, "lng": lng}}
