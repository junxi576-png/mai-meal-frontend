import streamlit as st
import re
import json
import time
import base64
import io
from PIL import Image
import pandas as pd
from datetime import datetime
from config import APP_TITLE, CUSTOM_CSS
from utils.i18n import t, tf
import api_client

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if 'lang' not in st.session_state: st.session_state.lang = 'zh'
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = {}

c_empty, c_lang = st.columns([8, 2])
with c_lang:
    lang_mode = st.radio("🌐 Language", ["中文", "English"], index=0 if st.session_state.lang=='zh' else 1, horizontal=True, label_visibility="collapsed")
    st.session_state.lang = 'zh' if lang_mode == "中文" else 'en'

# 全局 API 缓存层
@st.cache_data(show_spinner=False, ttl=600)
def cached_recipes(): return api_client.get_recipes()

@st.cache_data(show_spinner=False, ttl=60)
def cached_history(username): return api_client.get_history(username)

@st.cache_data(show_spinner=False, ttl=300)
def fetch_admin_stats(): return api_client.get_admin_stats()

@st.cache_data(show_spinner=False, ttl=300)
def fetch_admin_ings(): return api_client.get_admin_ingredients()

@st.cache_data(show_spinner=False, ttl=300)
def fetch_admin_recipes(): return api_client.get_admin_recipes_list()

@st.cache_data(show_spinner=False, ttl=300)
def fetch_admin_users(): return api_client.get_admin_users()

@st.cache_data(show_spinner=False, ttl=300)
def fetch_admin_activity_stats(): return api_client.get_admin_activity_stats()

# =========================================================================
# 🛡️ 核心强化：前置图片无损压缩机制 (防数据库撑爆)
# =========================================================================
def compress_image_to_b64(uploaded_file, max_size=(256, 256), quality=80):
    """将用户上传的图片进行物理缩放、转为JPEG格式压缩后，再输出为 Base64"""
    try:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        image.thumbnail(max_size)
        
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=quality, optimize=True)
        
        b64_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        st.warning(f"⚠️ 图片压缩失败，正在尝试直接转换原图：{e}")
        bytes_data = uploaded_file.getvalue()
        b64_str = base64.b64encode(bytes_data).decode()
        return f"data:{uploaded_file.type};base64,{b64_str}"

# 🚀 物理销毁残影处理
if not st.session_state.logged_in:
    auth_placeholder = st.empty() 
    
    with auth_placeholder.container():
        st.markdown(f"<h1 style='text-align: center; color: #00c853;'>{t('MAI 临床智能营养师')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #888;'>{t('精准医学营养治疗 (MNT) 排餐引擎')}</p><br>", unsafe_allow_html=True)
        
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            tab1, tab2 = st.tabs([t("🔐 账号登录"), t("📝 新用户注册")])
            with tab1:
                l_user = st.text_input(t("用户名"), key="l_user")
                l_pwd = st.text_input(t("密码"), type="password", key="l_pwd")
                if st.button(t("登 录"), use_container_width=True, type="primary"):
                    success, user_data = api_client.login(l_user, l_pwd)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_profile = user_data
                        auth_placeholder.empty()
                        time.sleep(0.1) 
                        st.rerun()
                    else:
                        st.error(t("用户名或密码错误，请检查！"))
                
                with st.expander(t("🔄 忘记密码？点击这里找回/重置")):
                    st.info(t("🔒 出于安全考虑，重置密码需要进行基础身份验证。"))
                    f_user = st.text_input(t("请输入需要找回的用户名"), key="f_user")
                    f_age = st.number_input(t("请输入注册时预留的【年龄】验证"), 1, 120, 30, key="f_age")
                    f_new_pwd = st.text_input(t("输入新密码"), type="password", key="f_new_pwd")
                    if st.button(t("验证并重置"), use_container_width=True):
                        if not f_user or not f_new_pwd: st.warning(t("请填写完整的用户名和新密码。"))
                        else:
                            if api_client.reset_password(f_user, f_age, f_new_pwd): st.success(t("✅ 密码重置成功！请直接登录。"))
                            else: st.error(t("❌ 用户名不存在，或预留的验证年龄不匹配！"))
            
            with tab2:
                st.info(t("💡 建立您的永久健康档案，AI 营养师将终身为您排忧解难。"))
                r_user = st.text_input(t("设置用户名 (仅限英文、数字、下划线，3-20位)"), key="r_user")
                r_pwd = st.text_input(t("设置密码"), type="password", key="r_pwd")
                
                r_email = st.text_input("邮箱 (可选)" if st.session_state.lang == 'zh' else "Email (Optional)", key="r_email")
                r_avatar_file = st.file_uploader("🖼️ " + ("上传头像 (可选)" if st.session_state.lang == 'zh' else "Upload Avatar (Optional)"), type=["png", "jpg", "jpeg"], key="r_avatar")
                
                st.divider()
                st.markdown(t("#### 👤 基础体征"))
                c1, c2 = st.columns(2)
                r_gender = c1.selectbox(t("性别"), ["男性", "女性"], format_func=lambda x: tf('gender', x), key="rg")
                r_age = c2.number_input(t("年龄"), 1, 120, 30, key="ra")
                c3, c4 = st.columns(2)
                r_height = c3.number_input(t("身高 (cm)"), 50, 250, 170, key="rh")
                r_weight = c4.number_input(t("体重 (kg)"), 20, 300, 70, key="rw")
                st.divider()
                
                st.markdown(t("#### 🩺 临床与过敏筛查"))
                diab_opts = ["健康 (无糖尿病)", "糖尿病前期 / 妊娠期糖尿病", "2型糖尿病"]
                r_diabetes = st.radio(t("您的血糖状况属于："), diab_opts, format_func=lambda x: tf('diabetes', x), key="rd")
                
                comp_opts = [
                    "糖尿病肾病 (需严控蛋白质/钾/磷)", 
                    "高血压 (需清淡低钠)", 
                    "高尿酸血症/痛风 (需低嘌呤)"
                ]
                r_comps = st.multiselect(t("是否伴有以下代谢并发症："), comp_opts, format_func=lambda x: tf('comps', x), key="rc")
                
                allergen_opts = ["Allium (五辛)", "Shellfish (甲壳/贝类)", "Fish (鱼类)", "Peanut (花生)", "Tree Nuts (树坚果)", "Sesame (芝麻)", "Soy (大豆)", "Egg (蛋类)", "Dairy (奶制品)"]
                r_allergens = st.multiselect(t("是否有以下食物过敏史："), allergen_opts, format_func=lambda x: tf('allergens', x), key="ral")
                
                r_halal = st.checkbox(t("☪️ 严格清真 (Halal)"), key="r_halal")
                
                if st.button(t("💾 注册并生成我的健康档案"), use_container_width=True, type="primary"):
                    if not r_user or not r_pwd:
                        st.warning(t("请填写完整的用户名和密码！"))
                    elif not re.match(r'^[a-zA-Z0-9_]{3,20}$', r_user):
                        st.error(t("❌ 用户名格式不符：只能包含英文、数字和下划线，且长度在 3-20 位之间。"))
                    else:
                        avatar_val = f"https://api.dicebear.com/7.x/bottts/svg?seed={r_user}" 
                        if r_avatar_file is not None:
                            avatar_val = compress_image_to_b64(r_avatar_file)
                        
                        default_bio = "这个人很懒，什么都没写~" if st.session_state.lang == 'zh' else "This person is lazy and wrote nothing~"
                        
                        success, msg = api_client.register({
                            "username": r_user, "password": r_pwd, "age": r_age, "height": r_height, 
                            "weight": r_weight, "gender": r_gender, "diabetes": r_diabetes, 
                            "comps": r_comps, "allergens": r_allergens, "is_halal": r_halal,
                            "email": r_email, "avatar": avatar_val, "bio": default_bio
                        })
                        if success: 
                            st.balloons()
                            st.success(t("✅ 注册成功！档案建立完成！请返回【🔐 账号登录】。"))
                        else: st.error(msg)

else:
    recipes_db = cached_recipes()
    unique_ings = {'Veg': set(), 'Meat': set(), 'Staple': set(), 'Other': set()}
    for r in recipes_db:
        for ing in r['ingredients']:
            cat = ing.get('cat', '')
            if cat in ['Grain']: ui_cat = 'Staple'
            elif cat in ['Vegetable', 'Fruit']: ui_cat = 'Veg'
            elif cat in ['Meat', 'Beef', 'Mutton', 'Poultry', 'Pork', 'Seafood', 'Dairy_Egg']: ui_cat = 'Meat'
            else: ui_cat = 'Other'
            unique_ings[ui_cat].add(ing['name'])

    user = st.session_state.user_profile
    is_admin = (user['username'].lower() == 'admin') 

    # =========================================================================
    # 🧠 核心增强：实时统计今日已摄入所有营养素总量及配额，区分不同餐次
    # =========================================================================
    bmr = (10 * user['weight']) + (6.25 * user['height']) - (5 * user['age']) + (5 if user['gender']=="男性" else -161)
    tdee = bmr * 1.2 
    current_deficit = st.session_state.get("deficit_slider", 300) 
    daily_target_kcal = tdee - current_deficit

    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_history_data = cached_history(user['username'])
    
    today_totals = {"k": 0.0, "na": 0.0, "potassium": 0.0, "phosphorus": 0.0, "purine": 0.0, "sugar": 0.0}
    
    today_saved_types = {}
    
    if raw_history_data:
        for rec in raw_history_data:
            ts = rec.get("timestamp", "")
            if ts.startswith(today_str):  
                m_type = rec.get("meal_type", "")
                today_saved_types[m_type] = ts 
                try:
                    m_data = json.loads(rec['meal_data']) if isinstance(rec['meal_data'], str) else rec['meal_data']
                    totals = m_data.get("totals", {})
                    today_totals["k"] += totals.get("k", 0.0)
                    today_totals["na"] += totals.get("na", 0.0)
                    today_totals["potassium"] += totals.get("potassium", 0.0)
                    today_totals["phosphorus"] += totals.get("phosphorus", 0.0)
                    today_totals["purine"] += totals.get("purine", 0.0)
                    today_totals["sugar"] += totals.get("sugar", 0.0)
                except Exception:
                    pass
                    
    today_saves_count = len(today_saved_types)

    with st.sidebar:
        # ==================== 侧边栏：头像与个人简介区 ====================
        avatar_url = user.get('avatar') or f"https://api.dicebear.com/7.x/bottts/svg?seed={user['username']}"
        user_email = user.get('email') or ("未绑定邮箱" if st.session_state.lang == 'zh' else "No Email Bound")
        user_bio = user.get('bio') or ("这个人很懒，什么都没写~" if st.session_state.lang == 'zh' else "This person is lazy and wrote nothing~")
        admin_badge = '[🛡️ Admin]' if is_admin and st.session_state.lang == 'en' else ('[🛡️ 管理员]' if is_admin else '')

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
            <img src="{avatar_url}" width="60" height="60" style="border-radius: 50%; object-fit: cover; background-color: #25262b; border: 2px solid #00c853;">
            <div>
                <div style="font-size: 1.3em; font-weight: bold; color: #00c853;">{user['username']} <span style="font-size: 0.6em; color: #fff;">{admin_badge}</span></div>
                <div style="font-size: 0.85em; color: #aaa; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{user_email}</div>
            </div>
        </div>
        <div style="font-size: 0.85em; font-style: italic; color: #888; margin-bottom: 15px; background: #25262b; padding: 10px; border-radius: 8px; border-left: 3px solid #00c853;">
            "{user_bio}"
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"**年龄**: {user['age']} 岁 | **性别**: {tf('gender', user['gender'])}<br>**身高**: {user['height']} cm | **体重**: {user['weight']} kg", unsafe_allow_html=True)
        st.markdown(f"**健康与体质标签**: <br>🔹 {tf('diabetes', user['diabetes_status'])}", unsafe_allow_html=True)

        if user['complications']:
            comps_options = ["糖尿病肾病 (需严控蛋白质/钾/磷)", "高血压 (需清淡低钠)", "高尿酸血症/痛风 (需低嘌呤)"]
            for c in user['complications']:
                display_c = c
                if "肾病" in c: display_c = "糖尿病肾病 (需严控蛋白质/钾/磷)"
                elif "高血压" in c: display_c = "高血压 (需清淡低钠)"
                st.markdown(f"🔹 {tf('comps', display_c)}")
        
        if user.get('is_halal'):
            st.markdown(f"🔹 {t('☪️ 严格清真 (Halal)')}")
                
        if user.get('allergens'):
            lbl = "🚫 **Blocked Allergens**:" if st.session_state.lang == 'en' else "🚫 **已拦截过敏原**:"
            translated_allergens = [tf('allergens', a) for a in user['allergens']]
            st.markdown(f"{lbl} <br><span style='color:#ff4b4b; font-size:0.9em;'>{', '.join(translated_allergens)}</span>", unsafe_allow_html=True)
        
        st.divider()
        st.markdown(f"#### 📊 {t('今日营养达成看板')}")
        
        k_pct = (today_totals["k"] / daily_target_kcal) if daily_target_kcal > 0 else 0
        st.markdown(f"🌅 {t('热量达成率')}: **{today_totals['k']:.0f}** / {daily_target_kcal:.0f} kcal ({k_pct*100:.0f}%)")
        st.progress(min(k_pct, 1.0))
        
        na_pct = min(today_totals["na"] / 2000.0, 1.0)
        st.markdown(f"🧂 {t('钠安全配额')}: **{today_totals['na']:.0f}** / 2000 mg")
        st.progress(na_pct)
        
        k_limit = 1000.0 if any("肾病" in str(c) for c in user.get('complications', [])) else 2000.0
        pot_pct = min(today_totals["potassium"] / k_limit, 1.0)
        st.markdown(f"🍌 {t('钾安全配额')}: **{today_totals['potassium']:.0f}** / {k_limit:.0f} mg")
        st.progress(pot_pct)
        
        pho_limit = 400.0 if any("肾病" in str(c) for c in user.get('complications', [])) else 800.0
        pho_pct = min(today_totals["phosphorus"] / pho_limit, 1.0)
        st.markdown(f"🦴 {t('磷安全配额')}: **{today_totals['phosphorus']:.0f}** / {pho_limit:.0f} mg")
        st.progress(pho_pct)
        
        pur_limit = 150.0 if any("痛风" in str(c) or "尿酸" in str(c) for c in user.get('complications', [])) else 300.0
        pur_pct = min(today_totals["purine"] / pur_limit, 1.0)
        st.markdown(f"🧬 {t('嘌呤配额')}: **{today_totals['purine']:.0f}** / {pur_limit:.0f} mg")
        st.progress(pur_pct)
        
        sug_limit = 5.0 if "糖尿病" in user.get('diabetes_status', '') or "妊娠" in user.get('diabetes_status', '') else 25.0
        sug_pct = min(today_totals["sugar"] / sug_limit, 1.0)
        st.markdown(f"🍭 {t('糖安全配额')}: **{today_totals['sugar']:.1f}** / {sug_limit:.1f} g")
        st.progress(sug_pct)
        
        save_lbl = "Daily Meal Quota" if st.session_state.lang == 'en' else "今日配餐完成度"
        st.markdown(f"📦 {save_lbl}: **{today_saves_count}** / 3")
        st.progress(min(today_saves_count / 3.0, 1.0))
        
        st.divider()
        if st.button(t("🚪 退出登录"), use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_profile = {}
            st.cache_data.clear() 
            st.rerun()

    # ==================== 全局主导航控制 ====================
    nav_opts = [t("🍽️ 智能排餐控制台"), t("📚 历史选择记录"), t("💬 社区交流大厅"), t("⚙️ 个人档案与体征管理")]
    if is_admin: nav_opts.append(t("📊 系统管理后台"))
    
    selected_nav = st.radio("主导航", nav_opts, horizontal=True, label_visibility="collapsed")
    st.markdown("<hr style='margin-top:0; border-color:#444;'>", unsafe_allow_html=True)

    if selected_nav == t("📚 历史选择记录"):
        st.markdown(t("### 📚 我的历史排餐记录"))
        col_btn1, col_btn2, _ = st.columns([2, 2, 6])
        if col_btn1.button(t("🔄 刷新记录"), use_container_width=True): 
            cached_history.clear()
            st.rerun()
            
        if col_btn2.button(t("🗑️ 删除已选"), type="primary", use_container_width=True):
            to_delete = [rec['timestamp'] for rec in raw_history_data if st.session_state.get(f"chk_{rec['timestamp']}", False)]
            if not to_delete: st.warning(t("⚠️ 请先勾选要删除的记录！"))
            else:
                if api_client.delete_history(user['username'], to_delete):
                    st.success(t("✅ 成功删除记录！"))
                    cached_history.clear()
                    st.rerun() 
                else: st.error(t("❌ 删除失败，请重试。"))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not raw_history_data:
            st.info(t("没有找到历史记录。开始您的第一次排餐吧！"))
        else:
            st.markdown(t("##### 📅 自定义方案追溯时间跨度筛选"))
            c_start, c_end = st.columns(2)
            with c_start:
                start_date = st.date_input(t("起始查询日期"), value=pd.to_datetime("2026-01-01").date(), key="history_start_date")
            with c_end:
                end_date = st.date_input(t("结束查询日期"), value=pd.to_datetime("2026-12-31").date(), key="history_end_date")
            
            filtered_history = []
            for record in raw_history_data:
                ts_str = record.get("timestamp") or record.get("date") or ""
                if ts_str:
                    try:
                        record_date = pd.to_datetime(ts_str[:10]).date()
                        if start_date <= record_date <= end_date:
                            filtered_history.append(record)
                    except Exception:
                        filtered_history.append(record)
                else:
                    filtered_history.append(record)

            st.write(f"{t('💡 在选定时间段内，共为您检索到 ')} **{len(filtered_history)}** {t(' 组排餐临床方案：')}")
            
            for rec in filtered_history:
                c_chk, c_exp = st.columns([0.5, 11])
                with c_chk:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    st.checkbox("", key=f"chk_{rec['timestamp']}", label_visibility="collapsed")
                with c_exp:
                    display_time = rec['timestamp'][:16] 
                    expander_title = f"🕒 {display_time} | {tf('meal', rec['meal_type'])}"
                    with st.expander(expander_title):
                        meal = json.loads(rec['meal_data'])
                        lbl_p = "Protein" if st.session_state.lang == 'en' else "蛋白质"
                        lbl_c = "Carbs" if st.session_state.lang == 'en' else "碳水"
                        lbl_f = "Fat" if st.session_state.lang == 'en' else "脂肪"
                        
                        hist_html = f"""<div style='background-color:#25262b; padding: 15px; border-radius: 8px; margin-bottom: 10px;'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:10px;'>
                            <span style='color:#f39c12; font-weight:bold; font-size:1.2em;'>⚡ {meal['totals']['k']:.0f} kcal</span>
                            <span style='color:#aaa; font-size:0.9em;'>🥩 {lbl_p}: {meal['totals']['p']:.1f}g | 🍚 {lbl_c}: {meal['totals']['c']:.1f}g | 🥑 {lbl_f}: {meal['totals']['f']:.1f}g</span>
                        </div><hr style="border-top: 1px dashed #444; margin: 5px 0;">"""
                        
                        for r in meal['recipes']:
                            disp_name = r.get('name_en') if st.session_state.lang == 'en' and r.get('name_en') else r.get('name_cn', r.get('name'))
                            hist_html += f"<div style='color:#00c853; margin-top:10px;'>🍽️ {disp_name} <span style='color:#888; font-size:0.8em;'>(≈{r['total_weight']:.0f}g)</span></div>"
                            for it in r['items']:
                                disp_ing = it.get('ing_name_en') if st.session_state.lang == 'en' and it.get('ing_name_en') else it.get('ing_name_cn', it.get('ing_name_disp'))
                                hist_html += f"<div style='display:flex; justify-content:space-between; padding-left:20px; font-size:0.9em; color:#ddd;'><span>🔸 {disp_ing}</span><span>{it['w']:.1f}g</span></div>"
                        hist_html += "</div>"
                        st.markdown(hist_html, unsafe_allow_html=True)

    elif selected_nav == t("💬 社区交流大厅"):
        st.markdown(t("### 💬 临床营养互助社区"))
        st.info(t("💡 这是一个慢节奏的留言板。在这里分享您的减脂控糖心得、讨论排餐方案吧！(受限于服务器资源，发言后页面会自动刷新)"))
        
        if st.button(t("🔄 获取最新留言"), use_container_width=True):
            st.rerun()

        st.divider()

        messages = api_client.get_chat_messages()
        chat_container = st.container(height=500)
        
        with chat_container:
            if not messages:
                st.write(t("目前还没有人发言，来抢沙发吧！"))
            else:
                for msg in messages:
                    avatar_url = msg.get('avatar') or f"https://api.dicebear.com/7.x/bottts/svg?seed={msg['username']}"
                    with st.chat_message(name=msg['username'], avatar=avatar_url):
                        st.markdown(f"**{msg['username']}** <span style='font-size: 0.8em; color: #888;'>({msg['timestamp']})</span>", unsafe_allow_html=True)
                        st.write(msg['content'])
        
        if prompt := st.chat_input(t("说点什么吧...")):
            with chat_container:
                with st.chat_message(name=user['username'], avatar=user.get('avatar')):
                    st.write(prompt)
            
            if api_client.send_chat_message(user['username'], prompt):
                st.rerun() 
            else:
                st.error(t("❌ 消息发送失败，可能是网络开小差了。"))

    elif selected_nav == t("⚙️ 个人档案与体征管理"):
        st.markdown(t("### ⚙️ 更新我的健康档案"))
        st.info(t("在此处修改您的体征或过敏指标，更新后左侧状态和底层算法将自动同步生效。"))
        with st.form("profile_update_form"):
            
            e_email = st.text_input("📧 " + (t("邮箱") if st.session_state.lang=='zh' else "Email"), value=user.get('email', ''))
            e_avatar_file = st.file_uploader("🖼️ " + (t("上传新头像 (留空则保持当前头像)") if st.session_state.lang=='zh' else "Upload New Avatar (Leave empty to keep current)"), type=["png", "jpg", "jpeg"])
            e_bio = st.text_area("📝 " + (t("个人简介") if st.session_state.lang=='zh' else "Bio"), value=user.get('bio', ''))
            st.divider()
            
            c1, c2 = st.columns(2)
            e_gender = c1.selectbox(t("性别"), ["男性", "女性"], index=0 if user['gender']=="男性" else 1, format_func=lambda x: tf('gender', x))
            e_age = c2.number_input(t("年龄"), 1, 120, int(user['age']))
            
            c3, c4 = st.columns(2)
            e_height = c3.number_input(t("身高 (cm)"), 50, 250, int(user['height']))
            e_weight = c4.number_input(t("体重 (kg)"), 20, 300, int(user['weight']))
            st.divider()
            
            diabetes_options = ["健康 (无糖尿病)", "糖尿病前期 / 妊娠期糖尿病", "2型糖尿病"]
            e_diabetes = st.radio(t("您的血糖状况属于："), diabetes_options, index=diabetes_options.index(user['diabetes_status']), format_func=lambda x: tf('diabetes', x))
            
            comps_options = ["糖尿病肾病 (需严控蛋白质/钾/磷)", "高血压 (需清淡低钠)", "高尿酸血症/痛风 (需低嘌呤)"]
            safe_comps = []
            for c in user.get('complications', []):
                if c in comps_options: safe_comps.append(c)
                elif "肾病" in c: safe_comps.append("糖尿病肾病 (需严控蛋白质/钾/磷)")
                elif "高血压" in c: safe_comps.append("高血压 (需清淡低钠)")
                    
            e_comps = st.multiselect(t("是否伴有以下代谢并发症："), comps_options, default=safe_comps, format_func=lambda x: tf('comps', x))
            allergens_options = ["Allium (五辛)", "Shellfish (甲壳/贝类)", "Fish (鱼类)", "Peanut (花生)", "Tree Nuts (树坚果)", "Sesame (芝麻)", "Soy (大豆)", "Egg (蛋类)", "Dairy (奶制品)"]
            safe_allergens = [a for a in user.get('allergens', []) if a in allergens_options]
            e_allergens = st.multiselect(t("是否有以下食物过敏史："), allergens_options, default=safe_allergens, format_func=lambda x: tf('allergens', x))
            
            e_halal = st.checkbox(t("☪️ 严格清真 (Halal)"), value=user.get('is_halal', False))
            
            if st.form_submit_button(t("💾 保存档案修改"), type="primary"):
                avatar_val = user.get('avatar', '')
                if e_avatar_file is not None:
                    avatar_val = compress_image_to_b64(e_avatar_file)
                
                if api_client.update_profile({
                    "username": user['username'], "age": e_age, "height": e_height, "weight": e_weight, 
                    "gender": e_gender, "diabetes": e_diabetes, "comps": e_comps, "allergens": e_allergens, 
                    "is_halal": e_halal, "email": e_email, "avatar": avatar_val, "bio": e_bio
                }):
                    st.session_state.user_profile.update({
                        "age": e_age, "height": e_height, "weight": e_weight, "gender": e_gender,
                        "diabetes_status": e_diabetes, "complications": e_comps, "allergens": e_allergens, 
                        "is_halal": e_halal, "email": e_email, "avatar": avatar_val, "bio": e_bio
                    })
                    st.success(t("✅ 档案更新成功！正在为您重新加载..."))
                    time.sleep(0.3)
                    st.rerun()

    elif selected_nav == t("🍽️ 智能排餐控制台"):
        
        @st.dialog(t("⚠️ 覆盖确认"))
        def confirm_overwrite_dialog(username, old_timestamp, new_meal_time, new_meal_data):
            if st.session_state.lang == 'en':
                st.warning(f"You have already saved a plan for [{tf('meal', new_meal_time)}] today.")
                st.write("Do you want to overwrite it with the new plan?")
                btn_yes = "✅ Confirm Overwrite"
                btn_no = "❌ Cancel"
            else:
                st.warning(f"您今天已经保存过【{tf('meal', new_meal_time)}】的排餐方案。")
                st.write("是否要用当前的新方案覆盖原有记录？")
                btn_yes = "✅ 确认覆盖"
                btn_no = "❌ 取消"
                
            c1, c2 = st.columns(2)
            if c1.button(btn_yes, use_container_width=True):
                api_client.delete_history(username, [old_timestamp])
                api_client.save_history(username, new_meal_time, new_meal_data)
                st.success(t("✅ 方案已成功保存到您的历史记录中！"))
                cached_history.clear()
                time.sleep(0.5)
                st.rerun()
            if c2.button(btn_no, use_container_width=True):
                st.rerun()
                
        force_low_gi = False
        if user['diabetes_status'] != "健康 (无糖尿病)":
            force_low_gi = True
            if st.session_state.lang == 'en': st.markdown("<div class='med-alert'>⚠️ <b>Clinical Alert</b>: Low GI constraints forced.</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='med-alert'>⚠️ <b>临床预警</b>：基于您的档案记录（血糖异常），系统已强制开启<b>低GI饮食限制</b>！</div>", unsafe_allow_html=True)

        st.markdown(t("### ⚖️ 步骤一：餐次能量分配"))
        d_c1, d_c2 = st.columns([1, 1])
        
        deficit = d_c1.slider(t("📉 目标能量缺口 (每日减持 kcal)"), 0, 1000, 300, step=50, key="deficit_slider")
        meal_opts = ["早餐 (占全天30%)", "早午餐/Brunch (占全天50%)", "午餐 (占全天40%)", "晚餐 (占全天30%)"]
        meal_time = d_c2.radio(t("🕒 本餐次类别"), meal_opts, index=2, horizontal=True, format_func=lambda x: tf('meal', x))

        is_breakfast_time = "早餐" in meal_time and "早午餐" not in meal_time
        is_brunch_time = "早午餐" in meal_time
        meal_type_payload = "breakfast" if is_breakfast_time else "main"

        if is_brunch_time: meal_ratio = 0.5
        elif "午" in meal_time: meal_ratio = 0.4
        else: meal_ratio = 0.3
        target_kcal = daily_target_kcal * meal_ratio

        if st.session_state.lang == 'en': st.markdown(f"<div class='status-box'>💡 <b>Target locked at: <span style='color:#ff4b4b;'>{target_kcal:.0f} kcal</span></b>.</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='status-box'>💡 <b>目标热量锁定为：<span style='color:#ff4b4b;'>{target_kcal:.0f} kcal</span></b>。</div>", unsafe_allow_html=True)

        c_min, c_max, f_min, f_max, p_min, p_max = 45, 70, 15, 35, 8, 20
        if is_brunch_time: c_min, c_max, f_min, f_max, p_min, p_max = 40, 60, 20, 40, 12, 25
            
        diab_status = user['diabetes_status']
        comps = user.get('complications', [])
        
        if "前期" in diab_status: c_min, c_max, f_min, f_max, p_min, p_max = 40, 65, 20, 35, 12, 25
        elif "妊娠" in diab_status: c_min, c_max, f_min, f_max, p_min, p_max = 35, 55, 25, 40, 12, 25
        elif "2型" in diab_status: c_min, c_max, f_min, f_max, p_min, p_max = 40, 60, 20, 40, 12, 25
        if any("肾病" in str(c) for c in comps): c_min, c_max, f_min, f_max, p_min, p_max = 45, 65, 25, 40, 8, 15
        if is_breakfast_time: f_max = min(f_max, 30)

        ai_ratio = f"AI 临床区间约束 (碳水 {c_min}-{c_max}% | 脂肪 {f_min}-{f_max}% | 蛋白 {p_min}-{p_max}%)" if st.session_state.lang == 'zh' else f"AI Clinical Constraints (C {c_min}-{c_max}% | F {f_min}-{f_max}% | P {p_min}-{p_max}%)"
        ratio_choice = st.radio(t("三大营养素分配策略"), [ai_ratio, t("自定义比例 (手动覆写)")], horizontal=True)

        if "AI" in ratio_choice or "智能" in ratio_choice:
            macro_ranges = {'c': [c_min, c_max], 'f': [f_min, f_max], 'p': [p_min, p_max]}
        else:
            r_c1, r_c2, r_c3 = st.columns(3)
            c_r = r_c1.number_input(t("🍚 碳水占比 (%)"), 10, 80, int((c_min+c_max)/2), step=5)
            f_r = r_c2.number_input(t("🥑 脂肪占比 (%)"), 10, 80, int((f_min+f_max)/2), step=5)
            p_r = r_c3.number_input(t("🥩 蛋白质占比 (%)"), 10, 80, int((p_min+p_max)/2), step=5)
            macro_ranges = {
                'c': [max(0, c_r - 5), min(100, c_r + 5)],
                'f': [max(0, f_r - 5), min(100, f_r + 5)],
                'p': [max(0, p_r - 5), min(100, p_r + 5)]
            }

        st.markdown(t("### 🥘 步骤二：环境食材与信仰禁忌"))
        c_v, c_m, c_s = st.columns(3)
        sel_v = c_v.multiselect(t("🥬 冰箱里的蔬菜"), sorted(list(unique_ings['Veg'])), placeholder=t("选择已有蔬菜..."))
        sel_m = c_m.multiselect(t("🥩 冰箱里的肉类/海鲜"), sorted(list(unique_ings['Meat'])), placeholder=t("选择已有肉类..."))
        sel_s = c_s.multiselect(t("🌾 冰箱里的主食"), sorted(list(unique_ings['Staple'])), placeholder=t("选择已有主食..."))
        total_sel = sel_v + sel_m + sel_s

        src_opts = ["允许增添未有食材 (混合推荐)", "仅使用冰箱已有食材 (严格清理库存)"]
        source_mode = st.radio(t("AI 匹配策略："), src_opts, horizontal=True, format_func=lambda x: tf('mode', x))

        st.markdown(t("##### 🚫 信仰与饮食风俗"))
        h_c1, h_c2 = st.columns(2)
        is_halal = user.get('is_halal', False)
        is_vegan = h_c1.checkbox(t("🥬 纯素食 (Vegan)"))
        is_low_gi = h_c2.checkbox(t("🩸 控糖 (低GI食材)"), value=force_low_gi, disabled=force_low_gi)

        st.markdown(t("### 🍽️ 步骤三：餐盘结构规划"))
        c_dish, c_staple, c_soup = st.columns(3)
        default_dishes = 0 if is_breakfast_time else 2
        num_dishes = c_dish.number_input(t("🥘 几道菜品？"), min_value=0, max_value=5, value=default_dishes)
        num_staples = c_staple.number_input(t("🍚 几份主食？"), min_value=0, max_value=3, value=1)
        num_soups = c_soup.number_input(t("🍲 几份汤水/饮品？"), min_value=0, max_value=2, value=0 if not is_breakfast_time else 1)

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        appetite_opts = {
            t("⚖️ 标准分量 (科学设定上限)"): 1.0,
            t("💪 大分量 (+20% 菜量上限)"): 1.2,
            t("🔥 超大分量 (+50% 菜量上限)"): 1.5
        }
        appetite_label = st.radio(t("您的食量偏好："), list(appetite_opts.keys()), horizontal=True)
        appetite_multiplier = appetite_opts[appetite_label]

        if 'gen_meals' not in st.session_state: st.session_state.gen_meals = []
        if 'hist_ids' not in st.session_state: st.session_state.hist_ids = []

        def run_generation(is_new=True):
            if is_new: st.session_state.hist_ids = []
            
            today_consumed_real = {
                "na": today_totals["na"], "k": today_totals["potassium"], 
                "pho": today_totals["phosphorus"], "purine": today_totals["purine"], "sugar": today_totals["sugar"]
            }
            
            payload = {
                "target_kcal": target_kcal, "macro_ranges": macro_ranges, "num_dishes": num_dishes, 
                "num_staples": num_staples, "num_soups": num_soups, "meal_type": meal_type_payload,
                "source_mode": source_mode, "selected_ings": total_sel, "n_options": 3, 
                "history_ids": st.session_state.hist_ids, "is_halal": is_halal, "is_vegan": is_vegan,
                "is_low_gi": is_low_gi, "user_allergens": user.get("allergens", []),
                "user_comps": user.get("complications", []), "user_diabetes": user.get("diabetes_status", "健康 (无糖尿病)"),
                "appetite_multiplier": appetite_multiplier, "daily_consumed": today_consumed_real
            }
            with st.spinner(t("AI营养师正在根据您的医疗与过敏档案进行线性规划求解...")):
                res = api_client.generate_meals(payload)
            if res:
                st.session_state.gen_meals = res
                for r in res: st.session_state.hist_ids.append(r['ids'])
            else: st.session_state.gen_meals = []

        st.divider()
        if st.button(t("🪄 引擎启动：生成专属 clinical 配餐"), type="primary", use_container_width=True):
            if "严格" in source_mode and not total_sel: st.error(t("❌ 开启了【严格库存模式】，但您未挑选任何已有食材！"))
            else: run_generation(is_new=True)

        def get_progress_color_range(pct, min_p, max_p):
            if min_p <= pct <= max_p: return "#28a745"
            return "#ffc107" if pct > 0 else "#dc3545"

        if st.session_state.gen_meals:
            cols = st.columns(3)
            for idx, meal in enumerate(st.session_state.gen_meals):
                with cols[idx]:
                    actual_kcal = meal['totals']['k']
                    p_pct_real = (meal['totals']['p'] * 4.0 / actual_kcal * 100) if actual_kcal > 0 else 0
                    c_pct_real = (meal['totals']['c'] * 4.0 / actual_kcal * 100) if actual_kcal > 0 else 0
                    f_pct_real = (meal['totals']['f'] * 9.0 / actual_kcal * 100) if actual_kcal > 0 else 0
                    p_color = get_progress_color_range(p_pct_real, macro_ranges['p'][0], macro_ranges['p'][1])
                    c_color = get_progress_color_range(c_pct_real, macro_ranges['c'][0], macro_ranges['c'][1])
                    f_color = get_progress_color_range(f_pct_real, macro_ranges['f'][0], macro_ranges['f'][1])

                    tot_na = meal['totals'].get('na', 0)
                    tot_k_mg = meal['totals'].get('potassium', 0)
                    tot_p_mg = meal['totals'].get('phosphorus', 0)
                    tot_purine = meal['totals'].get('purine', 0)
                    na_class = "na-warning" if tot_na > 800 else "" 
                    na_icon = "🚨" if tot_na > 800 else "🧂"
                    has_kidney = any("肾病" in str(c) for c in user.get('complications', []))
                    has_gout = any("痛风" in str(c) or "尿酸" in str(c) for c in user.get('complications', []))
                    k_icon = "🚨" if tot_k_mg > 1000 and has_kidney else "🍌"
                    purine_icon = "🚨" if tot_purine > 150 and has_gout else "🧬"
                    k_color = "#ff4b4b" if tot_k_mg > 1000 and has_kidney else "#aaa"
                    purine_color = "#ff4b4b" if tot_purine > 150 and has_gout else "#aaa"

                    lbl_opt = "Option" if st.session_state.lang == 'en' else "方案"
                    lbl_p = "Protein" if st.session_state.lang == 'en' else "蛋白质"
                    lbl_c = "Carbs" if st.session_state.lang == 'en' else "碳水"
                    lbl_f = "Fat" if st.session_state.lang == 'en' else "脂肪"
                    lbl_na = "Sodium" if st.session_state.lang == 'en' else "钠总量"
                    lbl_k = "Potassium" if st.session_state.lang == 'en' else "钾"
                    lbl_pho = "Phosphorus" if st.session_state.lang == 'en' else "磷"
                    lbl_pur = "嘌呤" if st.session_state.lang == 'zh' else "Purine"
                    
                    html_content = f"""<div class="meal-card">
                    <div style="display:flex; justify-content:space-between; align-items: center; margin-bottom: 10px;">
                        <h4 style="margin:0;">{lbl_opt} {idx+1}</h4><span class="kcal-badge">{actual_kcal:.0f} kcal</span>
                    </div>
                    <div style="background-color:#25262b; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
                        <div style="font-size: 0.8em; color: #ddd; margin-bottom: 2px; display:flex; justify-content:space-between;">
                            <span>🥩 {lbl_p} ({meal['totals']['p']:.1f}g)</span><span style="color:{p_color}">{p_pct_real:.0f}%</span>
                        </div>
                        <div style="width: 100%; background-color: #444; border-radius: 5px; margin-bottom: 8px;">
                            <div style="width: {min(p_pct_real, 100):.0f}%; background-color: {p_color}; height: 6px; border-radius: 5px;"></div>
                        </div>
                        <div style="font-size: 0.8em; color: #ddd; margin-bottom: 2px; display:flex; justify-content:space-between;">
                            <span>🍚 {lbl_c} ({meal['totals']['c']:.1f}g)</span><span style="color:{c_color}">{c_pct_real:.0f}%</span>
                        </div>
                        <div style="width: 100%; background-color: #444; border-radius: 5px; margin-bottom: 8px;">
                            <div style="width: {min(c_pct_real, 100):.0f}%; background-color: {c_color}; height: 6px; border-radius: 5px;"></div>
                        </div>
                        <div style="font-size: 0.8em; color: #ddd; margin-bottom: 2px; display:flex; justify-content:space-between;">
                            <span>🥑 {lbl_f} ({meal['totals']['f']:.1f}g)</span><span style="color:{f_color}">{f_pct_real:.0f}%</span>
                        </div>
                        <div style="width: 100%; background-color: #444; border-radius: 5px; margin-bottom: 8px;">
                            <div style="width: {min(f_pct_real, 100):.0f}%; background-color: {f_color}; height: 6px; border-radius: 5px;"></div>
                        </div>
                        <div class="micro-row" style="flex-wrap: wrap; gap: 10px;">
                            <span title="全局汇总">{na_icon} {lbl_na}: <span class="{na_class}">{tot_na:.0f} mg</span></span>
                            <span title="钾">{k_icon} {lbl_k}: <span style="color:{k_color}">{tot_k_mg:.0f} mg</span></span>
                            <span title="磷">🦴 {lbl_pho}: <span>{tot_p_mg:.0f} mg</span></span>
                            <span title="嘌呤">{purine_icon} {lbl_pur}: <span style="color:{purine_color}">{tot_purine:.0f} mg</span></span>
                        </div>
                    </div>"""
                    
                    for recipe in meal['recipes']:
                        disp_name = recipe.get('name_en') if st.session_state.lang == 'en' and recipe.get('name_en') else recipe.get('name_cn', recipe.get('name'))
                        html_content += f"<div class='recipe-title'>🍽️ {disp_name} <span style='font-size:0.8em; font-weight:normal; color:#aaa;'>(≈{recipe['total_weight']:.0f}g)</span></div>"
                        for item in recipe['items']:
                            disp_ing = item.get('ing_name_en') if st.session_state.lang == 'en' and item.get('ing_name_en') else item.get('ing_name_cn', item.get('ing_name_disp'))
                            if "隐形" in disp_ing or "Seasoning" in disp_ing:
                                html_content += f"<div class='ing-row ing-virtual'><span>🧪 {disp_ing}</span><span>{item['w']:.1f}g</span></div>"
                            else:
                                icon = '🧊' if item.get('ing_name_cn') in total_sel else '🛒'
                                html_content += f"<div class='ing-row'><span>{icon} {disp_ing}</span><span>{item['w']:.1f}g</span></div>"
                        html_content += "<br>"
                        
                    html_content += "</div>"
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    is_overwrite = meal_time in today_saved_types
                    lbl_save_limit = "Daily Save Limit Reached" if st.session_state.lang == 'en' else "今日保存已达上限"
                    
                    if not is_overwrite and today_saves_count >= 3:
                        st.button(f"🚫 {lbl_save_limit}", key=f"save_btn_disabled_{idx}", disabled=True, use_container_width=True)
                    else:
                        if st.button(f"📥 {t('选择此方案')} {idx+1}", key=f"save_btn_{idx}", use_container_width=True):
                            if is_overwrite:
                                old_ts = today_saved_types[meal_time]
                                confirm_overwrite_dialog(user['username'], old_ts, meal_time, meal)
                            else:
                                if api_client.save_history(user['username'], meal_time, meal):
                                    st.success(t("✅ 方案已成功保存到您的历史记录中！"))
                                    cached_history.clear() 
                                    time.sleep(0.3)
                                    st.rerun()  
                    
            if st.button(t("🔄 换一批组合 (不重复)"), use_container_width=True):
                run_generation(is_new=False)
                st.rerun()

    # 🚨 系统管理后台模块
    elif is_admin and selected_nav == t("📊 系统管理后台"):
        ad_nav = st.radio(t("系统功能导航"), [t("📈 平台数据大屏"), t("🥦 基础食材库管理"), t("🥘 临床配方/菜谱管理"), t("👥 患者画像监管"), t("🍱 智能食材与菜谱资产检索"), t("📊 平台运营大屏")], horizontal=True)
        st.markdown("<hr style='margin-top:0; border-color:#444;'>", unsafe_allow_html=True)
        
        if ad_nav == t("📈 平台数据大屏"):
            st.subheader(t("全局运行数据大屏"))
            stats = fetch_admin_stats()
            if stats:
                col1, col2, col3 = st.columns(3)
                col1.metric(t("注册患者/用户数"), stats.get('user_count', 0))
                col2.metric(t("菜谱知识库容量"), stats.get('recipe_count', 0))
                col3.metric(t("累计生成处方排餐"), stats.get('history_count', 0))
                st.write(t("🩺 糖尿病类型分布基线"))
                st.bar_chart(stats.get('diabetes_dist', {}))
        
        elif ad_nav == t("📊 平台运营大屏"):
            st.subheader(t("📈 平台注册用户排餐活跃度综合看板"))
            activity_data = fetch_admin_activity_stats()
            if activity_data:
                df_act = pd.DataFrame(activity_data)
                df_act.rename(columns={"date": t("排餐日期"), "count": t("系统使用频次 (次)")}, inplace=True)
                df_act.set_index(t("排餐日期"), inplace=True)
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.markdown(t("**📅 每日用户留存与排餐活跃趋势 (折线图)**"))
                    st.line_chart(df_act, use_container_width=True)
                with col_chart2:
                    st.markdown(t("**📊 阶段服务并发压力分析 (柱状图)**"))
                    st.bar_chart(df_act, use_container_width=True)
            else: st.info(t("暂无足够的历史排餐调度日志用于生成活跃度大屏。"))
        
        elif ad_nav == t("🥦 基础食材库管理"):
            st.subheader(t("🥦 基础食材营养素数据库 (CRUD)"))
            @st.dialog(t("🔧 食材详情与编辑"), width="large")
            def ingredient_dialog(default_data=None):
                is_edit = default_data is not None
                def_id = default_data.get(t("食材ID"), "") if is_edit else ""
                def_name_cn = default_data.get(t("中文名"), "") if is_edit else ""
                def_name_en = default_data.get(t("英文名"), "") if is_edit else ""
                def_k = float(default_data.get(t("热量 (kcal)"), 0.0)) if is_edit else 0.0
                def_p = float(default_data.get(t("蛋白质 (g)"), 0.0)) if is_edit else 0.0
                def_f = float(default_data.get(t("脂肪 (g)"), 0.0)) if is_edit else 0.0
                def_c = float(default_data.get(t("碳水 (g)"), 0.0)) if is_edit else 0.0
                def_fiber = float(default_data.get(t("纤维 (g)"), 0.0)) if is_edit else 0.0
                def_sodium = float(default_data.get(t("钠 (mg)"), 0.0)) if is_edit else 0.0
                def_sugar = float(default_data.get(t("糖 (g)"), 0.0)) if is_edit else 0.0
                def_potassium = float(default_data.get(t("钾 (mg)"), 0.0)) if is_edit else 0.0
                def_phosphorus = float(default_data.get(t("磷 (mg)"), 0.0)) if is_edit else 0.0
                def_purine = float(default_data.get(t("嘌呤 (mg)"), 0.0)) if is_edit else 0.0
                def_halal = bool(default_data.get(t("清真"), True)) if is_edit else True
                def_vegan = bool(default_data.get(t("纯素"), False)) if is_edit else False
                def_gi = int(default_data.get(t("GI等级"), 1)) if is_edit else 1

                with st.form("ing_crud_form"):
                    c1, c2, c3 = st.columns([1, 2, 2])
                    i_id = c1.text_input(t("食材ID *"), value=def_id, disabled=is_edit, placeholder="ing_xx")
                    i_name_cn = c2.text_input(t("中文名 *"), value=def_name_cn, placeholder=t("如: 西兰花"))
                    i_name_en = c3.text_input(t("英文名"), value=def_name_en, placeholder="Broccoli")
                    
                    c4, c5, c6, c7 = st.columns(4)
                    i_k = c4.number_input(t("热量 kcal"), 0.0, 1000.0, def_k)
                    i_p = c5.number_input(t("蛋白质 g"), 0.0, 100.0, def_p)
                    i_f = c6.number_input(t("脂肪 g"), 0.0, 100.0, def_f)
                    i_c = c7.number_input(t("碳水 g"), 0.0, 100.0, def_c)
                    
                    c8, c9, c10 = st.columns(3)
                    i_fiber = c8.number_input(t("膳食纤维 (g)"), 0.0, 100.0, def_fiber)
                    i_sodium = c9.number_input(t("钠 (mg)"), 0.0, 5000.0, def_sodium)
                    i_sugar = c10.number_input(t("添加糖 (g)"), 0.0, 100.0, def_sugar)
                    
                    c11, c12, c13 = st.columns(3)
                    i_potassium = c11.number_input(t("钾 (mg)"), 0.0, 5000.0, def_potassium)
                    i_phosphorus = c12.number_input(t("磷 (mg)"), 0.0, 5000.0, def_phosphorus)
                    i_purine = c13.number_input(t("嘌呤 (mg)"), 0.0, 5000.0, def_purine)
                    
                    col_b1, col_b2, col_b3 = st.columns(3)
                    is_h = col_b1.checkbox(t("符合清真(Halal)"), value=def_halal)
                    is_v = col_b2.checkbox(t("属于纯素(Vegan)"), value=def_vegan)
                    gi_opts = [1, 2, 3]
                    gi_l = col_b3.selectbox(t("GI(升糖)等级"), gi_opts, index=gi_opts.index(def_gi) if def_gi in gi_opts else 0)
                    
                    btn_label = t("💾 保存修改") if is_edit else t("✅ 确认入库")
                    if st.form_submit_button(btn_label, type="primary", use_container_width=True):
                        if not i_id or not i_name_cn: st.warning(t("ID和中文名必填！"))
                        else:
                            payload = {
                                "item_id": i_id, "name_cn": i_name_cn, "name_en": i_name_en, "kcal": i_k, "p": i_p, "f": i_f, "c": i_c,
                                "fiber_g": i_fiber, "sodium_mg": i_sodium, "sugar_g": i_sugar,
                                "potassium_mg": i_potassium, "phosphorus_mg": i_phosphorus, "purine_mg": i_purine,
                                "is_halal": is_h, "is_vegan": is_v, "gi_level": gi_l
                            }
                            s, m = api_client.update_admin_ingredient(payload) if is_edit else api_client.add_admin_ingredient(payload)
                            if s: 
                                st.success(t("🎉 操作成功！"))
                                fetch_admin_ings.clear()
                                fetch_admin_stats.clear()
                                time.sleep(0.5)
                                st.rerun()
                            else: st.error(m)

            ings = fetch_admin_ings()
            df_ings = pd.DataFrame(ings) if ings else pd.DataFrame()
            
            if not df_ings.empty:
                display_df = df_ings.rename(columns={
                    "item_id": t("食材ID"), "name_cn": t("中文名"), "name_en": t("英文名"),
                    "kcal": t("热量 (kcal)"), "p": t("蛋白质 (g)"), "f": t("脂肪 (g)"), "c": t("碳水 (g)"),
                    "fiber_g": t("纤维 (g)"), "sodium_mg": t("钠 (mg)"), "sugar_g": t("糖 (g)"),
                    "potassium_mg": t("钾 (mg)"), "phosphorus_mg": t("磷 (mg)"), "purine_mg": t("嘌呤 (mg)"),
                    "is_halal": t("清真"), "is_vegan": t("纯素"), "gi_level": t("GI等级")
                })
                cols_order = [
                    t("食材ID"), t("中文名"), t("英文名"), t("热量 (kcal)"), t("蛋白质 (g)"), t("脂肪 (g)"), t("碳水 (g)"), 
                    t("纤维 (g)"), t("钠 (mg)"), t("糖 (g)"), t("钾 (mg)"), t("磷 (mg)"), t("嘌呤 (mg)"), t("清真"), t("纯素"), t("GI等级")
                ]
                display_df = display_df[[col for col in cols_order if col in display_df.columns]]
            else: display_df = pd.DataFrame()

            t_col1, t_col2 = st.columns([8, 2])
            with t_col1: search_kw = st.text_input("🔍 " + t("搜索当前资产库 (支持中文名或ID)"), placeholder="例如：鸡蛋 / EDN_001")
            with t_col2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ " + t("新增食材"), type="primary", use_container_width=True): ingredient_dialog()

            if search_kw and not display_df.empty:
                mask = display_df[t('中文名')].str.contains(search_kw, case=False, na=False) | display_df[t('食材ID')].str.contains(search_kw, case=False, na=False)
                display_df = display_df[mask]

            st.caption(t("💡 点击选中行数据后，可在下方使用编辑或批量删除功能。"))
            selection_event = st.dataframe(display_df, use_container_width=True, hide_index=True, selection_mode="multi-row", on_select="rerun")
            selected_indices = selection_event.selection.rows
            
            if selected_indices:
                st.markdown("---")
                selected_rows = display_df.iloc[selected_indices]
                a_col1, a_col2, _ = st.columns([2, 2, 6])
                if len(selected_indices) == 1:
                    with a_col1:
                        if st.button("✏️ " + t("查看/编辑所选"), use_container_width=True): ingredient_dialog(selected_rows.iloc[0])
                else:
                    with a_col1: st.button("✏️ " + t("查看/编辑所选"), disabled=True, use_container_width=True)
                
                with a_col2:
                    if st.button(f"🗑️ 批量删除 ({len(selected_indices)}项)", type="primary", use_container_width=True):
                        success_count = sum(1 for target_id in selected_rows[t('食材ID')] if api_client.delete_admin_ingredient(target_id))
                        st.success(f"✅ 成功销毁 {success_count} 条食材记录！")
                        fetch_admin_ings.clear()
                        fetch_admin_stats.clear()
                        time.sleep(0.5)
                        st.rerun()
        
        elif ad_nav == t("🥘 临床配方/菜谱管理"):
            st.subheader(t("🥘 临床配方与菜谱关系网"))

            @st.dialog(t("🥘 临床配方详情与构建"), width="large")
            def recipe_dialog(default_data=None):
                is_view = default_data is not None
                all_ings = fetch_admin_ings()  
                ing_options = {f"{ing['name_cn']} ({ing['item_id']})": ing['item_id'] for ing in all_ings} if all_ings else {}
                
                if is_view:
                    st.markdown(f"#### 📋 {t('系统有效配方拓扑明细')}")
                    v_col1, v_col2 = st.columns(2)
                    v_col1.text_input(t("菜谱ID"), value=default_data.get(t("菜谱ID"), ""), disabled=True)
                    v_col2.text_input(t("菜谱中文名"), value=default_data.get(t("中文名"), ""), disabled=True)
                    v_col3, v_col4 = st.columns(2)
                    v_col3.text_input(t("菜谱英文名"), value=default_data.get(t("英文名"), ""), disabled=True)
                    v_col4.text_input(t("菜品结构定位"), value=default_data.get(t("菜品结构定位"), ""), disabled=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.checkbox(t("允许作为早餐?"), value=bool(default_data.get(t("允许作为早餐?"), False)), disabled=True, key="view_bf")
                    st.checkbox(t("流质/汤羹属性?"), value=bool(default_data.get(t("流质/汤羹属性?"), False)), disabled=True, key="view_soup")
                    st.divider()
                    st.info(t("💡 提示：配方需要调整时，请在列表中勾选移除后重新构建拓扑。"))
                else:
                    with st.form("recipe_dialog_form"):
                        rc1, rc2, rc3 = st.columns(3)
                        r_id = rc1.text_input(t("菜谱ID * (如 rec_10)"), placeholder="rec_xx")
                        r_name_cn = rc2.text_input(t("菜谱中文名 *"))
                        r_name_en = rc3.text_input(t("菜谱英文名"))
                        rc4, rc5, rc6 = st.columns(3)
                        r_cat = rc4.selectbox(t("菜品结构定位"), ["Dish", "Staple"])
                        r_bf = rc5.checkbox(t("允许作为早餐?"))
                        r_soup = rc6.checkbox(t("流质/汤羹属性?"))
                        st.markdown("---")
                        st.write(t("🧪 **物理流变约束：绑定烹饪参数与隐形调料**"))
                        rc7, rc8 = st.columns(2)
                        r_method = rc7.selectbox(t("烹饪工艺 (乘法溢出)"), ["CM_001:清蒸/水煮", "CM_002:清炒/滑炒", "CM_003:红烧/炖煮", "CM_004:油炸/干煸", "CM_005:凉拌/生食"], format_func=lambda x: t(x))
                        r_profile = rc8.selectbox(t("调味基底 (隐形留白)"), ["SP_001:清淡/原味", "SP_002:家常咸鲜", "SP_003:红烧/酱汁", "SP_004:糖醋/茄汁", "SP_005:麻辣/重油"], format_func=lambda x: t(x))
                        st.markdown("---")
                        st.write(t("🔗 **绑定图数据库食材节点 (支持多选联合关联)**"))
                        
                        if not all_ings:
                            st.warning(t("⚠️ 食材库当前为空！"))
                            bind_ing_ids = []
                        else:
                            selected_ing_labels = st.multiselect(t("🥘 关联底层食材"), options=list(ing_options.keys()), placeholder=t("点击或输入关键字搜索..."))
                            bind_ing_ids = [ing_options[lbl] for lbl in selected_ing_labels]
                        
                        if st.form_submit_button(t("构建入图数据库"), type="primary", use_container_width=True):
                            if not r_id or not r_name_cn or not bind_ing_ids: st.warning(t("⚠️ 参数缺失！"))
                            else:
                                ingredients_payload = [{"item_id": ing_id, "weight_ratio": 1.0} for ing_id in bind_ing_ids]
                                s, m = api_client.add_recipe({
                                    "recipe_id": r_id, "name_cn": r_name_cn, "name_en": r_name_en, "category": r_cat,
                                    "is_breakfast": r_bf, "is_soup": r_soup, "method_id": r_method.split(":")[0], "profile_id": r_profile.split(":")[0], "ingredients": ingredients_payload
                                })
                                if s: 
                                    st.success(t("🎉 成功！已成功写入图数据库！"))
                                    fetch_admin_recipes.clear()
                                    fetch_admin_stats.clear()
                                    cached_recipes.clear()
                                    time.sleep(0.5)
                                    st.rerun()
                                else: st.error(m)

            recipes = fetch_admin_recipes()
            df_recipes = pd.DataFrame(recipes) if recipes else pd.DataFrame()
            if not df_recipes.empty:
                display_df = df_recipes.rename(columns={
                    "recipe_id": t("菜谱ID"), "name_cn": t("中文名"), "name_en": t("英文名"),
                    "category": t("菜品结构定位"), "is_breakfast": t("允许作为早餐?"), "is_soup": t("流质/汤羹属性?")
                })
                display_df = display_df[[t("菜谱ID"), t("中文名"), t("英文名"), t("菜品结构定位"), t("允许作为早餐?"), t("流质/汤羹属性?")]]
            else: display_df = pd.DataFrame()

            tr_col1, tr_col2 = st.columns([8, 2])
            with tr_col1: search_recipe_kw = st.text_input("🔍 " + t("搜索已有菜谱组合档案 (支持名称或ID)"), placeholder="例如：梅菜扣肉 / rec_01", key="r_srch_kw")
            with tr_col2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ " + t("构建新配方拓扑"), type="primary", use_container_width=True): recipe_dialog()

            if search_recipe_kw and not display_df.empty:
                mask = display_df[t('中文名')].str.contains(search_recipe_kw, case=False, na=False) | display_df[t('菜谱ID')].str.contains(search_recipe_kw, case=False, na=False)
                display_df = display_df[mask]

            st.caption(t("💡 点击选中行数据后，可在下方快捷查看明细或批量删除。"))
            recipe_selection = st.dataframe(display_df, use_container_width=True, hide_index=True, selection_mode="multi-row", on_select="rerun", key="admin_recipes_df")
            selected_recipe_rows = recipe_selection.selection.rows
            
            if selected_recipe_rows:
                st.markdown("---")
                target_rec_data = display_df.iloc[selected_recipe_rows]
                b_col1, b_col2, _ = st.columns([2, 2, 6])
                if len(selected_recipe_rows) == 1:
                    with b_col1:
                        if st.button("🔍 " + t("查看配方详情"), use_container_width=True): recipe_dialog(target_rec_data.iloc[0])
                else:
                    with b_col1: st.button("🔍 " + t("查看配方详情"), disabled=True, use_container_width=True)
                
                with b_col2:
                    if st.button(f"🗑️ 彻底移出系统 ({len(selected_recipe_rows)}项)", type="primary", use_container_width=True):
                        purged_count = sum(1 for rec_id in target_rec_data[t('菜谱ID')] if api_client.delete_admin_recipe(rec_id))
                        st.success(f"✅ 成功从图数据库中彻底移除 {purged_count} 组临床菜谱资产！")
                        fetch_admin_recipes.clear()
                        fetch_admin_stats.clear()
                        cached_recipes.clear()
                        time.sleep(0.5)
                        st.rerun()
        
        elif ad_nav == t("🍱 智能食材与菜谱资产检索"):
            st.subheader(t("🔍 智能食材与菜谱资产检索"))
            search_kw = st.text_input(t("输入食材名称、菜谱名称或其ID进行实时精确检索："), placeholder=t("例如：鸡胸肉 / 糖尿病低脂餐"))
            tab_rec, tab_ing = st.tabs([t("📋 菜谱资产池"), t("🥦 系统食材库")])
            
            with tab_rec:
                all_recipes = fetch_admin_recipes()
                filtered_recipes = [r for r in all_recipes if search_kw.lower() in str(r.get('name_cn','')).lower() or search_kw.lower() in str(r.get('recipe_id','')).lower()] if search_kw else all_recipes[:10]
                for idx, rec in enumerate(filtered_recipes):
                    r_id = rec.get('recipe_id') or rec.get('id')
                    r_name = rec.get('name_cn', t('未命名菜谱'))
                    c_info, c_action = st.columns([8, 2])
                    c_info.markdown(f"**【{t('菜谱')}】** `{r_id}` | **{r_name}**")
                    if c_action.button(t("移除菜谱"), key=f"btn_del_rec_{r_id}_{idx}"):
                        if api_client.delete_admin_recipe(r_id): st.rerun()
                    st.markdown("---")
            
            with tab_ing:
                all_ingredients = fetch_admin_ings()
                unique_ings_list = list({i.get('item_id') or i.get('id'): i for i in all_ingredients}.values())
                filtered_ings = [i for i in unique_ings_list if search_kw.lower() in str(i.get('name_cn','')).lower() or search_kw.lower() in str(i.get('item_id','')).lower()] if search_kw else unique_ings_list[:10]
                for idx, ing in enumerate(filtered_ings):
                    i_id = ing.get('item_id') or ing.get('id')
                    i_name = ing.get('name_cn', t('未命名食材'))
                    c_info, c_action = st.columns([8, 2])
                    c_info.markdown(f"**【{t('食材')}】** `{i_id}` | **{i_name}** | P: {ing.get('p',0)}g | F: {ing.get('f',0)}g | C: {ing.get('c',0)}g")
                    if c_action.button(t("移除食材"), key=f"btn_del_ing_{i_id}_{idx}"):
                        if api_client.delete_admin_ingredient(i_id): st.rerun()
                    st.markdown("---")
                    
        elif ad_nav == t("👥 患者画像监管"):
            st.subheader(t("👥 平台注册患者临床体征汇总"))
            users = fetch_admin_users()
            if users:
                df_users = pd.DataFrame(users)
                if not df_users.empty:
                    if 'gender' in df_users.columns: df_users['gender'] = df_users['gender'].apply(lambda x: tf('gender', x) if pd.notnull(x) else x)
                    if 'diabetes_status' in df_users.columns: df_users['diabetes_status'] = df_users['diabetes_status'].apply(lambda x: tf('diabetes', x) if pd.notnull(x) else x)
                    if 'complications' in df_users.columns: df_users['complications'] = df_users['complications'].apply(lambda x: ", ".join([tf('comps', i) for i in x]) if isinstance(x, list) else x)
                    if 'allergens' in df_users.columns: df_users['allergens'] = df_users['allergens'].apply(lambda x: ", ".join([tf('allergens', i) for i in x]) if isinstance(x, list) else x)
                    
                    e_trans = t("邮箱") if st.session_state.lang == 'zh' else "Email"
                    b_trans = t("个人简介") if st.session_state.lang == 'zh' else "Bio"
                    
                    df_users.rename(columns={
                        "username": t("用户名"), "email": e_trans, "bio": b_trans, "age": t("年龄"), 
                        "gender": t("性别"), "height": t("身高 (cm)"), "weight": t("体重 (kg)"), 
                        "diabetes_status": t("血糖状况"), "complications": t("并发症"), 
                        "allergens": t("过敏原"), "is_halal": "清真需求"
                    }, inplace=True)
                st.dataframe(df_users, use_container_width=True)