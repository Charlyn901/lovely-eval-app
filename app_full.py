import streamlit as st
import pandas as pd
from pathlib import Path
from uuid import uuid4
from datetime import datetime, date, timedelta
import json
import random
import pytz

# ---------------- CONFIG ----------------
st.set_page_config(page_title="我们的专属小站", page_icon="💖", layout="wide")

DATA_FILE = "data.xlsx"
MSG_FILE = "messages.csv"
LOTTERY_FILE = "lottery.json"
WISH_FILE = "wishes.json"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

COLUMNS = [
    "时间","物品类型","名称","链接","情境",
    "主评级1","次评级1","主评级2","次评级2",
    "最终分","最终推荐","愉悦度","备注","照片文件名","记录ID"
]

BASE_TYPES = ["外卖","生活用品","化妆品","数码","小事","其他"]

SUB_MAP = {"S":["S+","S","S-"],"A":["A+","A","A-"],"B":["B+","B","B-"],"C":["C+","C","C-"]}
SCORE_MAP = {"S+":5.0,"S":4.7,"S-":4.4,
             "A+":4.1,"A":3.8,"A-":3.5,
             "B+":3.0,"B":2.5,"B-":2.0,
             "C+":1.5,"C":1.0,"C-":0.5}

DEFAULT_LOTTERY = {"再来一次":["再试一次","喝口水深呼吸"],"获得奖励":["亲亲一个","看电影一次","买杯奶茶"]}

# ---------------- Helpers ----------------
def now_str():
    tz = pytz.timezone("Asia/Shanghai")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    if Path(DATA_FILE).exists():
        df = pd.read_excel(DATA_FILE, engine="openpyxl")
        for c in COLUMNS:
            if c not in df.columns:
                df[c] = ""
        if "记录ID" not in df.columns:
            df["记录ID"] = ""
        df["记录ID"] = df["记录ID"].apply(lambda x: x if isinstance(x,str) and x.strip() else uuid4().hex)
        return df[COLUMNS]
    else:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    df.to_excel(DATA_FILE, index=False, engine="openpyxl")

def load_messages():
    if Path(MSG_FILE).exists():
        return pd.read_csv(MSG_FILE, encoding="utf-8")
    return pd.DataFrame(columns=["时间","留言"])

def save_message(text):
    dfm = load_messages()
    new = {"时间": now_str(), "留言": text}
    dfm = pd.concat([dfm, pd.DataFrame([new])], ignore_index=True)
    dfm.to_csv(MSG_FILE, index=False, encoding="utf-8-sig")

def load_lottery():
    if Path(LOTTERY_FILE).exists():
        with open(LOTTERY_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_LOTTERY.copy()

def save_lottery(d):
    with open(LOTTERY_FILE,"w",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2)

def load_wishes():
    if Path(WISH_FILE).exists():
        with open(WISH_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return []

def save_wishes(wishes):
    with open(WISH_FILE,"w",encoding="utf-8") as f:
        json.dump(wishes,f,ensure_ascii=False,indent=2)

def save_uploaded_image(uploaded_file):
    filename = f"{uuid4().hex}{Path(uploaded_file.name).suffix}"
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(path.name)

# ---------------- Session init ----------------
if "df" not in st.session_state:
    st.session_state.df = load_data()
if "images" not in st.session_state:
    st.session_state.images = {p.name:str(p) for p in UPLOAD_DIR.glob("*")}
if "theme" not in st.session_state:
    st.session_state.theme = "樱粉清新"

# ---------------- Theme CSS ----------------
def get_theme_css(name):
    if name == "樱粉清新":
        return """
        <style>
        body{background:#fff0f5;}
        .card{border-radius:12px; padding:10px; background:#fff7fb; margin-bottom:10px;}
        </style>
        """
    if name == "夜间黑银":
        return """
        <style>
        body{background:#0f1113; color:#eaeaea;}
        .card{border-radius:12px; padding:10px; background:#1a1a1d; margin-bottom:10px;}
        </style>
        """
    return """
    <style>
    body{background:#e0fff8;}
    .card{border-radius:12px; padding:10px; background:#f3fdff; margin-bottom:10px;}
    </style>
    """

st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)
st.title("💖 我们的专属小站")

# ---------------- 主页面 ----------------
left, right = st.columns([1,1.25])

with left:
    st.subheader("➕ 添加记录")
    with st.form("add_form", clear_on_submit=True):
        itype = st.selectbox("类型", options=BASE_TYPES)
        name = st.text_input("名称/事件")
        link = st.text_input("链接（可选）")
        ctx = st.selectbox("情境", ["在家","通勤","旅行","工作","约会","其他"])
        main1 = st.selectbox("主评级1", ["S","A","B","C"])
        sub1 = st.selectbox("细分1", SUB_MAP[main1])
        main2 = st.selectbox("主评级2", ["S","A","B","C"])
        sub2 = st.selectbox("细分2", SUB_MAP[main2])
        mood = st.radio("愉悦度", ["愉悦","还行","不愉悦"])
        remark = st.text_area("备注")
        photo = st.file_uploader("上传照片", type=["png","jpg","jpeg"])
        submitted = st.form_submit_button("保存")
    if submitted:
        v1, v2 = SCORE_MAP[sub1], SCORE_MAP[sub2]
        final_score = round(0.7*v1+0.3*v2,3)
        if final_score>=4.2: rec="推荐"
        elif final_score>=3.0: rec="还行"
        else: rec="不推荐"
        photo_name = save_uploaded_image(photo) if photo else ""
        new_row = {
            "时间": now_str(),
            "物品类型": itype,
            "名称": name,
            "链接": link,
            "情境": ctx,
            "主评级1": main1,"次评级1": sub1,
            "主评级2": main2,"次评级2": sub2,
            "最终分": final_score,"最终推荐": rec,
            "愉悦度": mood,"备注": remark,
            "照片文件名": photo_name,
            "记录ID": uuid4().hex
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(st.session_state.df)
        st.success("保存成功！")

with right:
    st.subheader("📚 记录总览")
    df_view = st.session_state.df.copy()
    f_type = st.selectbox("筛选类型", ["全部"]+BASE_TYPES)
    if f_type!="全部":
        df_view = df_view[df_view["物品类型"]==f_type]
    kw = st.text_input("关键字搜索")
    if kw.strip():
        df_view = df_view[df_view["名称"].str.contains(kw,na=False)]
    st.dataframe(df_view)
    for _, row in df_view.tail(5).iterrows():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write(f"**{row['名称']}** · {row['物品类型']} · {row['最终推荐']} ({row['愉悦度']})")
        if row["备注"]: st.write(row["备注"])
        rid=row["记录ID"]
        if st.button("🗑 删除", key=f"del_{rid}"):
            st.session_state.df = st.session_state.df[st.session_state.df["记录ID"]!=rid]
            save_data(st.session_state.df)
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 心情连击 ----------------
st.markdown("---")
st.subheader("🔥 心情连击")
df = st.session_state.df
if not df.empty:
    df["日期"]=pd.to_datetime(df["时间"]).dt.date
    daily = df.groupby("日期")["愉悦度"].apply(lambda x:"愉悦" if "愉悦" in x.values else "非愉悦")
    streak=0
    for mood in reversed(daily.values):
        if mood=="愉悦": streak+=1
        else: break
    st.write(f"已经连续 **{streak} 天愉悦** ✨")
else:
    st.info("暂无数据")

# ---------------- 抽奖中心 ----------------
st.markdown("---")
st.subheader("🎲 抽奖中心")
lot = load_lottery()
tab1, tab2, tab3 = st.tabs(["再来一次","获得奖励","管理奖池"])
with tab1:
    if st.button("🎯 抽一次"):
        st.success(random.choice(lot.get("再来一次",["再试一次"])))
with tab2:
    if st.button("🎁 获得奖励"):
        st.success(random.choice(lot.get("获得奖励",["亲亲一下"])))
with tab3:
    a_text = st.text_area("再来一次奖池", "\n".join(lot.get("再来一次",[])))
    b_text = st.text_area("获得奖励奖池", "\n".join(lot.get("获得奖励",[])))
    if st.button("保存奖池"):
        lot["再来一次"] = [x.strip() for x in a_text.splitlines() if x.strip()]
        lot["获得奖励"] = [x.strip() for x in b_text.splitlines() if x.strip()]
        save_lottery(lot)
        st.success("已保存")

# ---------------- 心愿清单 ----------------
st.markdown("---")
st.subheader("🌠 心愿清单")
wishes = load_wishes()
new_wish = st.text_input("添加心愿")
if st.button("添加心愿"):
    if new_wish.strip():
        wishes.append({"text":new_wish.strip(),"done":False,"id":uuid4().hex})
        save_wishes(wishes)
        st.experimental_rerun()
for w in wishes:
    col1,col2=st.columns([6,1])
    with col1: st.write(("✅" if w["done"] else "🔲")+w["text"])
    with col2:
        if st.button("切换", key=w["id"]):
            w["done"]=not w["done"]
            save_wishes(wishes)
            st.experimental_rerun()

# ---------------- 留言板 ----------------
st.markdown("---")
st.subheader("📝 留言板")
msg_text = st.text_area("写下想说的话")
if st.button("发送留言"):
    if msg_text.strip():
        save_message(msg_text.strip())
        st.success("已保存")
        st.experimental_rerun()
msgs = load_messages()
for _, r in msgs.iloc[::-1].iterrows():
    st.write(f"> {r['时间']} — {r['留言']}")