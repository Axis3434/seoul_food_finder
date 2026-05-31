from flask import Flask, request, jsonify, render_template
from finder import search_food

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    address = data.get('address')
    keyword = data.get('keyword')
    offset = data.get('offset', 0)
    
    if not address or not keyword:
        return jsonify({"error": "주소와 키워드를 모두 입력해주세요."}), 400
        
    result = search_food(address, keyword, offset)
    
    if "error" in result:
        return jsonify(result), 400
        
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=True)
