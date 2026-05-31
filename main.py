import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Windows 터미널에서 이모지 출력을 위해 stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

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
    카카오 플레이스 URL을 BeautifulSoup으로 파싱하여 키워드에 해당하는 메뉴와 가격 정보를 추출합니다.
    매칭되는 메뉴가 있으면 (메뉴문자열, True)를 반환하고, 없으면 (None, False)를 반환합니다.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # 모바일 웹페이지가 구조 파싱이 조금 더 수월할 수 있으므로 모바일 URL로 변환 시도
        mobile_url = place_url.replace("place.map.kakao.com", "place.map.kakao.com/m")
        response = requests.get(mobile_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        menu_items = soup.find_all('div', class_='info_menu') 
        if not menu_items:
             menu_items = soup.find_all('span', class_='loss_word') # 다른 패턴

        for item in menu_items[:10]: # 최대 10개까지 확인
            menu_text = item.get_text(strip=True)
            if menu_text:
                 # 1. 정형화된 메뉴 리스트에서 키워드 확인
                 if keyword.lower() in menu_text.lower():
                     return f"웹 파싱: {menu_text}", True
                     
        # 2. 메뉴 리스트에는 없지만, 페이지 전체 텍스트(메뉴판 등)에서 키워드가 확인되는 경우
        if keyword.lower() in soup.get_text().lower():
             return f"가격 정보 파싱 불가 (상세 링크의 메뉴판에서 '{keyword}' 확인 가능)", True
            
    except Exception as e:
        pass
        
    return None, False

def main():
    print("=" * 55)
    print(" 🍔 서울 주변 맛집 및 착한가격업소 검색 프로그램 🍔 ")
    print("=" * 55)
    
    if not KAKAO_REST_API_KEY:
        print("\n[경고] KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        print(".env 파일을 생성하고 카카오 API 키를 입력해주세요.\n")
        return

    print("\n📍 위치 정보를 입력해주세요.")
    address = input("현재 계신 주소를 입력하세요 (예: 서울특별시 종로구 대학로): ").strip()
    keyword = input("먹고 싶은 음식 키워드를 입력하세요 (예: 떡볶이, 삼겹살): ").strip()

    print(f"\n🌍 입력하신 주소({address})의 좌표를 찾는 중입니다...")
    lat, lng = get_coordinates_from_address(address)
    
    if lat is None or lng is None:
        print("[오류] 해당 주소의 위치를 찾을 수 없습니다. 정확한 주소를 입력해주세요.")
        return

    print(f"\n🔎 [{keyword}] 메뉴가 확인되는 가까운 주변 맛집 5곳을 탐색 중입니다...\n")
    print("-" * 55)
    
    valid_count = 0
    page = 1
    is_end = False
    
    while valid_count < 5 and not is_end:
        restaurants, is_end = search_restaurants_kakao(keyword, lat, lng, page)
        
        if not restaurants and page == 1:
            print("조건에 맞는 식당을 전혀 찾지 못했습니다.")
            return
            
        for r in restaurants:
            name = r.get('place_name')
            address = r.get('road_address_name') or r.get('address_name')
            distance = r.get('distance')
            place_url = r.get('place_url')
            
            # 2. 착한가격업소 매칭 시도
            menu_info, is_matched = check_good_price_store(name, address, keyword)
            
            # 3. 착한가격업소에서 키워드를 찾지 못했다면 웹 파싱 시도
            if not is_matched:
                menu_info, is_matched = parse_kakao_place(place_url, keyword)
                
            # 4. 키워드가 확인된 메뉴만 출력
            if is_matched:
                valid_count += 1
                print(f"[{valid_count}] {name}")
                print(f"  🏢 주소: {address}")
                print(f"  🚶 거리: {distance}m")
                print(f"  🍲 메뉴: {menu_info}")
                print(f"  🔗 링크: {place_url}")
                print("-" * 55)
                
                if valid_count >= 5: # 최대 5개까지만 출력
                    break
                    
        page += 1 # 5개를 못 채웠으면 다음 페이지 검색
        
        # 무한 루프나 과도한 API 호출 방지 (최대 5페이지 = 반경 내 75개 식당까지만 확인)
        if page > 5:
            break
            
    if valid_count == 0:
        print(f"주변 반경 내에 '{keyword}' 메뉴를 확인할 수 있는 식당이 없습니다.")
    elif valid_count < 5:
        print(f"주변 반경 내에서 '{keyword}' 메뉴를 파는 곳을 최대한 찾았으나 {valid_count}곳뿐입니다.")

if __name__ == "__main__":
    main()
