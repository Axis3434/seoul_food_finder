import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import concurrent.futures

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY")
TMAP_API_KEY = os.getenv("TMAP_API_KEY")

def get_address_from_coordinates(lat, lng):
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"x": lng, "y": lat}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code in [429, 403]:
            return "LIMIT_EXCEEDED"
        response.raise_for_status()
        docs = response.json().get('documents', [])
        if docs:
            address_info = docs[0].get('road_address') or docs[0].get('address')
            return address_info.get('address_name')
    except Exception as e:
        print(f"[오류] 좌표->주소 변환 실패: {e}")
    return None

def get_coordinates_from_address(query):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": query}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code in [429, 403]:
            return None, None, 'LIMIT_EXCEEDED', '', '', ''
        docs = response.json().get('documents', [])
        if docs:
            addr = docs[0].get('address', {})
            depth1 = addr.get('region_1depth_name', '')
            address_name = docs[0].get('address_name', '')
            address_type = docs[0].get('address_type', '')
            return float(docs[0]['y']), float(docs[0]['x']), depth1, address_name, address_type, 'ADDRESS'
    except:
        pass

    url_kw = "https://dapi.kakao.com/v2/local/search/keyword.json"
    try:
        response = requests.get(url_kw, headers=headers, params=params)
        if response.status_code in [429, 403]:
            return None, None, 'LIMIT_EXCEEDED', '', '', ''
        docs = response.json().get('documents', [])
        if docs:
            addr_name = docs[0].get('address_name', '')
            parts = addr_name.split()
            depth1 = parts[0] if len(parts) > 0 else ''
            return float(docs[0]['y']), float(docs[0]['x']), depth1, addr_name, '', 'KEYWORD'
    except:
        pass
        
    return None, None, '', '', '', ''

def get_walking_distance(start_lat, start_lng, end_lat, end_lng):
    if not TMAP_API_KEY:
        return None, None
        
    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
    headers = {
        "appkey": TMAP_API_KEY,
        "Accept": "application/json"
    }
    payload = {
        "startX": start_lng, "startY": start_lat,
        "endX": end_lng, "endY": end_lat,
        "startName": "출발", "endName": "도착",
        "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=3)
        if response.status_code in [429, 403]:
            return "LIMIT_EXCEEDED", None
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            if features:
                props = features[0].get('properties', {})
                return props.get('totalDistance'), props.get('totalTime')
    except Exception as e:
        print(f"[오류] TMAP API 실패: {e}")
    return None, None

def search_restaurants_kakao(keyword, lat, lng, page, radius=2000):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "query": keyword, "x": lng, "y": lat, "radius": radius,
        "category_group_code": "FD6", "sort": "distance", "page": page
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code in [429, 403]:
            return "LIMIT_EXCEEDED", True
        data = response.json()
        return data.get('documents', []), data.get('meta', {}).get('is_end', True)
    except:
        return [], True

def check_good_price_store(restaurant_name, address, keyword):
    if not PUBLIC_DATA_API_KEY: return None, False
    url = "https://api.odcloud.kr/api/3045247/v1/uddi:12a36b40-6230-4401-b647-b8456a789c7f"
    
    short_name = restaurant_name.replace("식당", "").replace("가든", "").replace("본점", "").strip()
    if len(short_name) == 0: short_name = restaurant_name
    search_query = short_name[:3] if len(short_name) >= 2 else short_name
    
    params = {"serviceKey": PUBLIC_DATA_API_KEY, "page": 1, "perPage": 20, "cond[업소명::LIKE]": search_query}
    try:
        response = requests.get(url, params=params, timeout=3)
        if response.status_code == 200:
            items = response.json().get('data', [])
            for item in items:
                store_name = str(item.get("업소명", "")).strip().replace(" ", "")
                store_address = str(item.get("주소", "")).strip()
                name_b = restaurant_name.replace(" ", "")
                
                if store_name in name_b or name_b in store_name:
                    addr_parts = address.split()
                    store_addr_parts = store_address.split()
                    
                    if len(addr_parts) >= 2 and len(store_addr_parts) >= 2:
                        if addr_parts[0] in store_addr_parts[0] and addr_parts[1] in store_addr_parts[1]:
                            best_menu = None
                            best_price = None
                            
                            for i in range(1, 5):
                                menu = item.get(f'메뉴{i}')
                                if menu:
                                    price = item.get(f'가격{i}') or '정보 없음'
                                    if not best_menu:
                                        best_menu, best_price = menu, price
                                    if keyword.lower() in str(menu).lower():
                                        return f"🟢 착한가격업소: {menu} ({price}원)", True
                            
                            if best_menu:
                                return f"🟢 착한가격업소: {best_menu} ({best_price}원) 등", True
                            else:
                                return f"🟢 착한가격업소 지정 식당", True
    except:
        pass
    return None, False

def parse_kakao_place(place_url, keyword):
    return f"메뉴 가격 파싱 불가 (식당 상세 페이지에서 직접 메뉴판 확인 가능)", True

def search_food(location_data, keyword, offset=0):
    warning_msg = None
    
    if 'lat' in location_data and 'lng' in location_data:
        lat, lng = float(location_data['lat']), float(location_data['lng'])
        address_name = get_address_from_coordinates(lat, lng)
        if address_name == "LIMIT_EXCEEDED":
            return {"error": "오늘 제공 가능한 무료 검색 한도가 모두 소진되었습니다. 매일 자정(밤 12시)에 초기화되니 내일 다시 이용해주세요!"}
        if not address_name:
            return {"error": "GPS 좌표를 주소로 변환할 수 없습니다."}
        
        parts = address_name.split()
        depth1 = parts[0] if len(parts) > 0 else ''
        depth2 = parts[1] if len(parts) > 1 else ''
    else:
        address = location_data.get('address', '')
        lat, lng, depth1, address_name, address_type, search_mode = get_coordinates_from_address(address)
        if depth1 == "LIMIT_EXCEEDED":
            return {"error": "오늘 제공 가능한 무료 검색 한도가 모두 소진되었습니다. 매일 자정(밤 12시)에 초기화되니 내일 다시 이용해주세요!"}
        if lat is None:
            return {"error": "해당 위치를 찾을 수 없습니다. 정확한 주소나 장소명을 입력해주세요."}

    if not depth1.startswith("서울"):
        return {"error": "서울 지역이 아닙니다. 서울 내의 위치만 검색 가능합니다."}
        
    if 'address' in location_data and search_mode == 'ADDRESS' and address_type == 'REGION':
        warning_msg = f"현재 [{address_name}]의 중심 좌표를 기준으로 검색된 결과입니다. '동'이나 '도로명' 등 주소를 조금 더 구체적으로 적어주시면 훨씬 더 정확한 추천을 받아보실 수 있어요!"

    results = []
    valid_count = 0
    skipped_count = 0
    page = 1
    is_end = False
    
    while valid_count < 5 and not is_end:
        restaurants, is_end = search_restaurants_kakao(keyword, lat, lng, page)
        
        if restaurants == "LIMIT_EXCEEDED":
            return {"error": "오늘 제공 가능한 무료 검색 한도가 모두 소진되었습니다. 매일 자정(밤 12시)에 초기화되니 내일 다시 이용해주세요!"}
            
        if not restaurants and page == 1:
            return {"error": "조건에 맞는 식당을 전혀 찾지 못했습니다."}
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_r = {}
            for r in restaurants:
                future = executor.submit(get_walking_distance, lat, lng, float(r.get('y')), float(r.get('x')))
                future_to_r[future] = r
                
            for future in concurrent.futures.as_completed(future_to_r):
                r = future_to_r[future]
                dist, time_sec = future.result()
                if dist == "LIMIT_EXCEEDED":
                    return {"error": "오늘 제공 가능한 무료 길찾기 한도가 모두 소진되었습니다. 매일 자정(밤 12시)에 초기화되니 내일 다시 이용해주세요!"}
                r['tmap_dist'] = dist if dist is not None else 999999
                r['tmap_time'] = time_sec
                
        restaurants.sort(key=lambda x: x['tmap_dist'])

        for r in restaurants:
            name = r.get('place_name')
            addr = r.get('road_address_name') or r.get('address_name')
            place_url = r.get('place_url')
            
            menu_info, is_matched = check_good_price_store(name, addr, keyword)
            if not is_matched:
                menu_info, is_matched = parse_kakao_place(place_url, keyword)
                
            if is_matched:
                if skipped_count < offset:
                    skipped_count += 1
                    continue
                    
                valid_count += 1
                
                t_dist = r.get('tmap_dist')
                t_time = r.get('tmap_time')
                
                dist_str = f"도보 {t_dist}m" if t_dist != 999999 else f"직선 {r.get('distance')}m"
                time_str = f"약 {t_time // 60}분 소요" if t_time else ""
                
                results.append({
                    "name": name,
                    "address": addr,
                    "distance": dist_str,
                    "walk_time": time_str,
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
        
    response_data = {"results": results, "count": valid_count, "center": {"lat": lat, "lng": lng}}
    if warning_msg:
        response_data["warning"] = warning_msg
        
    return response_data
