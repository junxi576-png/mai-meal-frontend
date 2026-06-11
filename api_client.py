import requests
import streamlit as st
import os

BASE_URL = os.getenv("API_URL", "https://mai-api-backend.onrender.com")
# 🚀 核心优化：建立全局 HTTP 连接池，免除每次请求的 TCP 握手开销，大幅提速
http_session = requests.Session()

def register(data):
    res = http_session.post(f"{BASE_URL}/auth/register", json=data)
    if res.status_code == 200: return True, ""
    return False, res.json().get("detail", "Error")

def login(username, password):
    res = http_session.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if res.status_code == 200: return True, res.json()["user"]
    return False, None

def reset_password(username, verify_age, new_password):
    res = http_session.post(f"{BASE_URL}/auth/reset", json={"username": username, "verify_age": verify_age, "new_password": new_password})
    return res.status_code == 200

def update_profile(data):
    res = http_session.put(f"{BASE_URL}/user/profile", json=data)
    return res.status_code == 200

def get_recipes():
    res = http_session.get(f"{BASE_URL}/recipes")
    return res.json() if res.status_code == 200 else []

def save_history(username, meal_type, meal_data):
    res = http_session.post(f"{BASE_URL}/history/save", json={"username": username, "meal_type": meal_type, "meal_data": meal_data})
    return res.status_code == 200

def get_history(username):
    res = http_session.get(f"{BASE_URL}/history/{username}")
    return res.json() if res.status_code == 200 else []

def delete_history(username, timestamps):
    # 💡 修复潜在Bug：对齐 main.py 中的 @app.post("/api/history/delete") 路由
    res = http_session.post(f"{BASE_URL}/history/delete", json={"username": username, "timestamps": timestamps})
    return res.status_code == 200

def get_admin_stats():
    res = http_session.get(f"{BASE_URL}/admin/stats")
    return res.json() if res.status_code == 200 else {}

def get_admin_users():
    res = http_session.get(f"{BASE_URL}/admin/users")
    return res.json() if res.status_code == 200 else []

def get_admin_recipes_list():
    res = http_session.get(f"{BASE_URL}/admin/recipes/list")
    return res.json() if res.status_code == 200 else []

def delete_admin_recipe(recipe_id):
    res = http_session.delete(f"{BASE_URL}/admin/recipes/{recipe_id}")
    return res.status_code == 200

def add_recipe(recipe_data):
    res = http_session.post(f"{BASE_URL}/admin/recipe", json=recipe_data)
    if res.status_code == 200: return True, ""
    return False, res.json().get("detail", "Error")

def get_admin_ingredients():
    res = http_session.get(f"{BASE_URL}/admin/ingredients")
    return res.json() if res.status_code == 200 else []

def add_admin_ingredient(data):
    res = http_session.post(f"{BASE_URL}/admin/ingredients", json=data)
    if res.status_code == 200: return True, res.json()['message']
    return False, res.json().get('detail', 'Error')

def update_admin_ingredient(data):
    res = http_session.put(f"{BASE_URL}/admin/ingredients", json=data)
    if res.status_code == 200: return True, res.json()['message']
    return False, res.json().get('detail', 'Error')

def delete_admin_ingredient(item_id):
    """请求后端删除指定食材"""
    try:
        res = http_session.delete(f"{BASE_URL}/admin/ingredients/{item_id}")
        return res.status_code == 200
    except Exception:
        return False

def generate_meals(payload):
    try:
        res = http_session.post(f"{BASE_URL}/engine/generate", json=payload)
        if res.status_code == 200: 
            data = res.json()
            # 前端需要的是数组，从后端的 {"solutions": [...]} 里把这个数组解包出来
            return data.get("solutions", []) if isinstance(data, dict) else data
        else:
            # 💡 核心修复：当算法因为严格医学限制报错（如404）时，捕获异常信息并提示用户，避免前端卡死或无反应
            error_detail = res.json().get("detail", "智能排餐引擎未能生成有效方案。")
            st.error(f"🚫 排餐失败: {error_detail}")
    except Exception as e:
        st.error(f"💥 无法连接到排餐后端服务: {str(e)}")
    return []

def get_admin_activity_stats():
    """请求后端获取平台活跃度大屏数据"""
    try:
        res = http_session.get(f"{BASE_URL}/admin/stats/activity")
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []