from flask import Flask, request, jsonify, render_template
from finder import search_food, get_address_from_coordinates

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    if not lat or not lng:
        return jsonify({"error": "위도와 경도가 필요합니다."}), 400
        
    address = get_address_from_coordinates(lat, lng)
    if not address:
        return jsonify({"error": "주소를 찾을 수 없습니다."}), 400
        
    return jsonify({"address": address})

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    keyword = data.get('keyword')
    offset = data.get('offset', 0)
    
    if not keyword:
        return jsonify({"error": "키워드를 입력해주세요."}), 400
        
    result = search_food(data, keyword, offset)
    
    if "error" in result:
        return jsonify(result), 400
        
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=True)
