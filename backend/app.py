from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import math
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 计算地球对面的坐标
def get_antipode(lat, lon):
    # 对面的纬度是反向的
    antipode_lat = -lat
    
    # 对面的经度需要加减180度
    if lon <= 0:
        antipode_lon = lon + 180
    else:
        antipode_lon = lon - 180
        
    return antipode_lat, antipode_lon

# 从维基百科获取位置信息
def get_wikipedia_info(lat, lon):
    # 使用维基百科的地理搜索API
    endpoint = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": 10000,  # 搜索半径10公里
        "gslimit": 5  # 最多5个结果
    }
    
    try:
        response = requests.get(endpoint, params=params)
        data = response.json()
        
        if "query" in data and "geosearch" in data["query"]:
            results = data["query"]["geosearch"]
            
            # 提取页面信息
            if results:
                page_ids = [str(page["pageid"]) for page in results]
                
                # 获取页面摘要
                summary_params = {
                    "action": "query",
                    "format": "json",
                    "pageids": "|".join(page_ids),
                    "prop": "extracts|info|coordinates",
                    "exintro": True,
                    "explaintext": True,
                    "inprop": "url"
                }
                
                summary_response = requests.get(endpoint, params=summary_params)
                summary_data = summary_response.json()
                
                formatted_results = []
                if "query" in summary_data and "pages" in summary_data["query"]:
                    pages = summary_data["query"]["pages"]
                    
                    for page_id, page_info in pages.items():
                        # 从结果中找到对应的坐标
                        current_coords = {"lat": lat, "lon": lon}
                        for result in results:
                            if str(result["pageid"]) == page_id:
                                current_coords = {"lat": result.get("lat", lat), "lon": result.get("lon", lon)}
                                break
                                
                        formatted_results.append({
                            "title": page_info.get("title", ""),
                            "summary": page_info.get("extract", "")[:300] + "...",
                            "url": page_info.get("fullurl", ""),
                            "coordinates": current_coords
                        })
                
                return formatted_results
            
        return []
    except Exception as e:
        print(f"Error fetching Wikipedia data: {e}")
        return []

@app.route('/api/antipode', methods=['GET'])
def find_antipode():
    try:
        # 从请求获取经纬度
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        
        # 计算对面的位置
        antipode_lat, antipode_lon = get_antipode(lat, lon)
        
        # 获取原始位置和对面位置的维基百科信息
        origin_info = get_wikipedia_info(lat, lon)
        antipode_info = get_wikipedia_info(antipode_lat, antipode_lon)
        
        return jsonify({
            "origin": {
                "lat": lat,
                "lon": lon,
                "info": origin_info
            },
            "antipode": {
                "lat": antipode_lat,
                "lon": antipode_lon,
                "info": antipode_info
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
