import requests
import streamlit as st
import os

BASE_URL = os.getenv("API_URL", "https://mai-api-backend.onrender.com/api") 
# 🚀 建立全局 HTTP 连接池，免除每次请求的 TCP 握手开销
http_session = requests.Session()

# 统一常规请求超时时间（秒）
REQ_TIMEOUT = 12

def register(data):
    try:
        res = http_session.post(f"{BASE_URL}/auth/register", json=data, timeout=REQ_TIMEOUT)
        if res.status_code == 200: return True, ""
        return False, res.json().get("detail", "Error")
    except Exception as e: return False, f"请求超时或失败: {e}"

def login(username, password):
    try:
        # 给登录接口足足 60 秒的超时，专门用来等 Render 免费实例“冷启动”醒过来
        res = http_session.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=60)
        if res.status_code == 200: return True, res.json()["user"]
        return False, None
    except Exception as e: 
        st.error(f"登录超时 (可能服务器正在休眠唤醒中，请稍等片刻后重试): {e}")
        return False, None

def reset_password(username, verify_age, new_password):
    try:
        res = http_session.post(f"{BASE_URL}/auth/reset", json={"username": username, "verify_age": verify_age, "new_password": new_password}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def update_profile(data):
    try:
        res = http_session.put(f"{BASE_URL}/user/profile", json=data, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def get_recipes():
    try:
        res = http_session.get(f"{BASE_URL}/recipes", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

def save_history(username, meal_type, meal_data):
    try:
        res = http_session.post(f"{BASE_URL}/history/save", json={"username": username, "meal_type": meal_type, "meal_data": meal_data}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def get_history(username):
    try:
        res = http_session.get(f"{BASE_URL}/history/{username}", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

def delete_history(username, timestamps):
    try:
        res = http_session.post(f"{BASE_URL}/history/delete", json={"username": username, "timestamps": timestamps}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def get_admin_stats():
    try:
        res = http_session.get(f"{BASE_URL}/admin/stats", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except Exception: return {}

def get_admin_users():
    try:
        res = http_session.get(f"{BASE_URL}/admin/users", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

def get_admin_recipes_list():
    try:
        res = http_session.get(f"{BASE_URL}/admin/recipes/list", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

def delete_admin_recipe(recipe_id):
    try:
        res = http_session.delete(f"{BASE_URL}/admin/recipes/{recipe_id}", timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def add_recipe(recipe_data):
    try:
        res = http_session.post(f"{BASE_URL}/admin/recipe", json=recipe_data, timeout=REQ_TIMEOUT)
        if res.status_code == 200: return True, ""
        return False, res.json().get("detail", "Error")
    except Exception as e: return False, str(e)

def get_admin_ingredients():
    try:
        res = http_session.get(f"{BASE_URL}/admin/ingredients", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

def add_admin_ingredient(data):
    try:
        res = http_session.post(f"{BASE_URL}/admin/ingredients", json=data, timeout=REQ_TIMEOUT)
        if res.status_code == 200: return True, res.json()['message']
        return False, res.json().get('detail', 'Error')
    except Exception as e: return False, str(e)

def update_admin_ingredient(data):
    try:
        res = http_session.put(f"{BASE_URL}/admin/ingredients", json=data, timeout=REQ_TIMEOUT)
        if res.status_code == 200: return True, res.json()['message']
        return False, res.json().get('detail', 'Error')
    except Exception as e: return False, str(e)

def delete_admin_ingredient(item_id):
    try:
        res = http_session.delete(f"{BASE_URL}/admin/ingredients/{item_id}", timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def generate_meals(payload):
    try:
        # 引擎求解给 15 秒超时
        res = http_session.post(f"{BASE_URL}/engine/generate", json=payload, timeout=15)
        if res.status_code == 200: 
            data = res.json()
            return data.get("solutions", []) if isinstance(data, dict) else data
        else:
            error_detail = res.json().get("detail", "智能排餐引擎未能生成有效方案。")
            st.error(f"🚫 排餐失败: {error_detail}")
    except requests.exceptions.Timeout:
        st.error("⏳ 排餐超时：算法未能在限时内找到完美方案，请尝试放宽比例。")
    except Exception as e:
        st.error(f"💥 无法连接到排餐后端服务: {str(e)}")
    return []

def get_admin_activity_stats():
    try:
        res = http_session.get(f"{BASE_URL}/admin/stats/activity", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

# ==================== 💬 社区留言板 API 调用 ====================
def get_chat_messages():
    try:
        res = http_session.get(f"{BASE_URL}/chat/messages", timeout=REQ_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

def send_chat_message(username, content):
    try:
        res = http_session.post(f"{BASE_URL}/chat/send", json={"username": username, "content": content}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

# ==================== 🛠️ 管理员对用户专属操作 API 调用 ====================
def admin_reset_user_password(username):
    try:
        res = http_session.post(f"{BASE_URL}/admin/users/reset", json={"username": username}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def admin_send_user_message(username, message):
    try:
        res = http_session.post(f"{BASE_URL}/admin/users/message", json={"username": username, "message": message}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False

def clear_user_message(username):
    try:
        res = http_session.post(f"{BASE_URL}/user/clear_message", json={"username": username}, timeout=REQ_TIMEOUT)
        return res.status_code == 200
    except Exception: return False