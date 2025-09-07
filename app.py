# app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import os
from uuid import uuid4
from datetime import datetime, date
from datetime import timedelta
import json
from PIL import Image
import io
import random

# ------------- 配置 -------------
DATA_FILE = "data.xlsx"
MSG_FILE = "messages.csv"
EVENTS_FILE = "events.json"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BASE_TYPES = ["外卖","生活用品","化妆品","数码","其他(小事)"] 
LOTTERY_FILE = "lottery.json"  # 抽奖奖池持久化

COLUMNS = ["时间","物品类型","名称","链接","情境",
           "主评级1","次评级1","主评级2","次评级2",
           "最终分","最终推荐","愉悦度","备注","照片文件名"，“记录ID"]

SUB_MAP = {"S":["S+","S","S-"], "A":["A+","A","A-"], "B":["B+","B","B-"], "C":["C+","C","C-"]}
SCORE_MAP = {"S+":5.0,"S":4.7,"S-":4.4,
             "A+":4.1,"A":3.8,"A-":3.5,
             "B+":3.0,"B":2.5,"B-":2.0,
             "C+":1.5,"C":1.0,"C-":0.5}

st.set_page_config(page_title="小狗给宝宝的专属小站", page_icon="💖", layout="wide")

# Responsive CSS + mobile tweaks
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
.header {
  background: linear-gradient(90deg,#ff9a9e,#fecfef);
  padding: 12px;
  border-radius: 12px;
  color: white;
  margin-bottom: 8px;
}
.card {
  border-radius:12px;
  padding:10px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.06);
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,245,245,0.98));
  margin-bottom:10px;
}
.small-muted { color: #666; font-size:12px; }
@media (max-width:600px){
  .header h2 { font-size:18px !important; }
  .card { padding:8px; }
  .small-muted { font-size:11px; }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header"><h2 style="margin:0">💖 专属小站 — 给宝贝的小工具</h2></div>', unsafe_allow_html=True)

# ------------- I/O helpers -------------
def now_str(offset_hours:int=0):  # 统一产生“本地时间字符串”
    return (datetime.utcnow() + timedelta(hours=offset_hours)).strftime("%Y-%m-%d %H:%M:%S")
def load_data():
    if Path(DATA_FILE).exists():
        try:
            df = pd.read_excel(DATA_FILE, engine="openpyxl")
            for c in COLUMNS:
                if c not in df.columns:
                    df[c] = ""
            return df[COLUMNS]
        except Exception as e:
            st.error(f"读取 {DATA_FILE} 出错：{e}")
            return pd.DataFrame(columns=COLUMNS)
    else:
        return pd.DataFrame(columns=COLUMNS)
            if "记录ID" not in df.columns:  # 旧文件自动补列
                df["记录ID"] = ""
            # 为空ID的行补一个uuid
            df["记录ID"] = df["记录ID"].apply(lambda x: x if isinstance(x,str) and x.strip() else uuid4().hex)  # 
            return df[COLUMNS]
def save_data(df):
    try:
        df.to_excel(DATA_FILE, index=False, engine="openpyxl")
    except Exception as e:
        st.error(f"保存数据失败：{e}")


def load_messages():
    if Path(MSG_FILE).exists():
        try:
            return pd.read_csv(MSG_FILE, encoding="utf-8")
        except:
            return pd.DataFrame(columns=["时间","留言"])
    else:
        return pd.DataFrame(columns=["时间","留言"])

def save_message(text):

    dfm = load_messages()
    new = {"时间": now_str(st.session_state.get("tz_offset", 8)), "留言": text}  # 使用可调时区
    dfm = pd.concat([dfm, pd.DataFrame([new])], ignore_index=True)
    dfm.to_csv(MSG_FILE, index=False, encoding="utf-8-sig")

def load_events():
    if Path(EVENTS_FILE).exists():
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    else:
        return {}

def save_events(events_dict):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events_dict, f, ensure_ascii=False, indent=2)
def load_lottery():  # 【棕红新增】
    if Path(LOTTERY_FILE).exists():
        try:
            with open(LOTTERY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"再来一次": ["再试一次"], "获得奖励": ["亲亲一下","看电影","奶茶一杯"]}
    return {"再来一次": ["再试一次"], "获得奖励": ["亲亲一下","看电影","奶茶一杯"]}

def save_lottery(data:dict):  # 
    with open(LOTTERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ------------- session init -------------
if "df" not in st.session_state:
    st.session_state.df = load_data()
if "images" not in st.session_state:
    st.session_state.images = {}
for f in os.listdir(UPLOAD_DIR):
    st.session_state.images[f] = str(UPLOAD_DIR / f)

# ------------- sidebar -------------
with st.sidebar:
    st.header("⚙ 设置面板")
    w1 = st.slider("主评级权重（主）", 0.0, 1.0, 0.7, step=0.05)
    w2 = round(1.0 - w1, 2)
    st.text(f"二次评级权重（次）自动为：{w2}")
    st.subheader("推荐阈值")
    thr_rec = st.number_input("推荐阈值（>=）", value=4.2, step=0.1)
    thr_ok  = st.number_input("还行阈值（>=）", value=3.0, step=0.1)
    st.markdown("---")
    st.subheader("时间设置")
    tz = st.number_input("时区偏移（相对UTC，例：北京时间=8）", value=8, step=1)  
    st.session_state["tz_offset"] = int(tz)  #
    st.markdown("---")
    st.subheader("重要事件（纪念日/见面）")
    events = load_events()
    if events:
        st.write("当前事件：")
        for k,v in events.items():
            st.write(f"- {k} → {v}")
    else:
        st.write("当前无事件（可新增）")
    new_name = st.text_input("新增事件名称（例：恋爱纪念日）")
    new_date = st.date_input("日期（每年重复）", value=date.today())
    if st.button("添加事件"):
        events[new_name] = new_date.isoformat()
        save_events(events)
        st.success("已添加事件（页面刷新后可见）")
    st.markdown("---")
    st.subheader("导出 / 清理")
    if st.button("导出记录（Excel）"):
        if Path(DATA_FILE).exists():
            with open(DATA_FILE, "rb") as f:
                st.download_button("下载 data.xlsx", data=f, file_name="data.xlsx")
        else:
            st.warning("当前没有 data.xlsx")
    if st.button("清空所有记录（慎用）"):
        st.session_state.df = st.session_state.df.iloc[0:0]
        save_data(st.session_state.df)
        st.success("已清空记录")

# ------------- main: add form & preview -------------
left, right = st.columns([1,1.3])

with left:
    st.subheader("➕ 添加新物品 / 记录")
    with st.form("add_form", clear_on_submit=True):
        itype = st.selectbox("物品类型", ["外卖","生活用品","化妆品","数码","其他(小事)"])
        name = st.text_input("物品 / 店名", max_chars=60)
        link = st.text_input("链接（可选）")
        ctx = st.selectbox("情境", ["在家","通勤","旅行","工作","约会","其他(小事)"])
        col1, col2 = st.columns(2)
        with col1:
            main1 = st.selectbox("主评级 1", ["S","A","B","C"], index=0, key="m1")
            sub1 = st.selectbox("细分 1", SUB_MAP[main1], key="s1")
        with col2:
            main2 = st.selectbox("主评级 2", ["S","A","B","C"], index=0, key="m2")
            sub2 = st.selectbox("细分 2", SUB_MAP[main2], key="s2")
        mood = st.radio("愉悦度", ["愉悦","还行","不愉悦"], index=1)
        remark = st.text_area("备注 / 给对方的话（会保存）", max_chars=300)
        photo = st.file_uploader("上传图片（可选）", type=["png","jpg","jpeg"])
        surprise = st.checkbox("添加一条小情话（成功后显示）", value=True)
        submitted = st.form_submit_button("添加并保存")

    if submitted:
        v1 = SCORE_MAP.get(sub1)
        v2 = SCORE_MAP.get(sub2)
        if v1 is None or v2 is None:
            st.error("评级解析出错，请检查二级评级")
        else:
            final_score = round(w1 * v1 + (1.0 - w1) * v2, 3)
            if final_score >= thr_rec:
                rec = "推荐"
            elif final_score >= thr_ok:
                rec = "还行"
            else:
                rec = "不推荐"

            photo_name = ""
            if photo is not None:
                try:
                    ext = Path(photo.name).suffix
                    filename = f"{uuid4().hex}{ext}"
                    save_path = UPLOAD_DIR / filename
                    with open(save_path, "wb") as f:
                        f.write(photo.getbuffer())
                    st.session_state.images[filename] = str(save_path)
                    photo_name = filename
                except Exception as e:
                    st.error(f"保存图片失败：{e}")

            new_row = {
                "时间": now_str(st.session_state.get("tz_offset", 8)),                  
                "物品类型": itype,
                "名称": name,
                "链接": link,
                "情境": ctx,
                "主评级1": main1,
                "次评级1": sub1,
                "主评级2": main2,
                "次评级2": sub2,
                "最终分": final_score,
                "最终推荐": rec,
                "愉悦度": mood,
                "备注": remark,
                "照片文件名": photo_name
                "记录ID": uuid4().hex,  
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.success(f"已添加：{name} （{rec}）")
            if surprise:
                love_lines = [
                    "宝贝，看到你的小笑容就是我最想收藏的风景。",
                    "我这辈子都愿意替你选最好吃的那一口。",
                    "有你在，一切都刚刚好。"
                ]
                st.info(random.choice(love_lines))
base_type_set = set(BASE_TYPES)  
type_options = ["全部"] + sorted(list(base_type_set.union(set(df_view["物品类型"].dropna().unique().tolist()))))  
f_type = st.selectbox("按物品类型", options=type_options, index=0)  
with right:
    st.subheader("📚 记录总览（可筛选）")
    df_view = st.session_state.df.copy()
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        
    with col2:
        f_rec = st.selectbox("按最终推荐", options=["全部","推荐","还行","不推荐"], index=0)
    with col3:
        f_mood = st.selectbox("按愉悦度", options=["全部","愉悦","还行","不愉悦"], index=0)
    if f_type != "全部":
        df_view = df_view[df_view["物品类型"] == f_type]
    if f_rec != "全部":
        df_view = df_view[df_view["最终推荐"] == f_rec]
    if f_mood != "全部":
        df_view = df_view[df_view["愉悦度"] == f_mood]
kw = st.text_input("🔍 关键字搜索（名称/备注/链接/情境）", "")  
if kw.strip():
    mask = (
        df_view["名称"].fillna("").str.contains(kw, case=False) |
        df_view["备注"].fillna("").str.contains(kw, case=False) |
        df_view["链接"].fillna("").str.contains(kw, case=False) |
        df_view["情境"].fillna("").str.contains(kw, case=False)
    )
    df_view = df_view[mask]  

    st.dataframe(df_view.reset_index(drop=True), use_container_width=True)
    st.markdown("### 小卡片预览（最近 6 条）")
    preview = df_view.tail(6).iloc[::-1]
    for _, row in preview.iterrows():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns([3,1])
        with c1:
            st.markdown(f"**{row['名称']}**  ·  {row['物品类型']}  ·  {row['情境']}")
            st.markdown(f"<div class='small-muted'>评级：{row['主评级1']}({row['次评级1']})  /  {row['主评级2']}({row['次评级2']})  →  <strong>{row['最终分']}</strong>  · 推荐：<strong>{row['最终推荐']}</strong></div>", unsafe_allow_html=True)
            if row['链接']:
                st.markdown(f"[查看链接]({row['链接']})")
            if row['备注']:
                st.markdown(f"*备注：{row['备注']}*")    
rid = row.get("记录ID","")  
    if rid:
        if st.button("🗑 删除该记录", key=f"del_{rid}"): 
            df_all = st.session_state.df
            st.session_state.df = df_all[df_all["记录ID"] != rid]  
            save_data(st.session_state.df)  
            st.experimental_rerun()  

        with c2:
            if row['照片文件名'] and row['照片文件名'] in st.session_state.images:
                try:
                    st.image(st.session_state.images[row['照片文件名']], width=140)
                except:
                    st.write("")
            else:
                st.write("")
        st.markdown('</div>', unsafe_allow_html=True)

# ------------- 心情中心 -------------
st.markdown("---")
st.subheader("💌 心情中心")
mood_today = st.selectbox("今天心情如何？", ["愉悦","还行","不愉悦"], index=1)
ctx_filter = st.selectbox("按情境筛选安慰（可选）", [""] + ["在家","通勤","旅行","工作","约会","其他"])

if mood_today == "不愉悦":
    st.warning("宝宝今天有点不开心哦")
    past_good = st.session_state.df[st.session_state.df["愉悦度"] == "愉悦"]
    if ctx_filter:
        past_good = past_good[past_good["情境"] == ctx_filter]
    names = past_good["名称"].dropna().unique().tolist()
    if names:
        sel = st.selectbox("这些曾经让你愉悦过：", names)
        if sel:
            chosen = past_good[past_good["名称"] == sel].iloc[-1]
            st.success(f"想想 {sel} 的美好吧～ 备注：{chosen.get('备注','')}")
            fn = chosen.get("照片文件名","")
            if fn and fn in st.session_state.images:
                st.image(st.session_state.images[fn], width=300)
    else:
        st.info("还没有宝宝标记为愉悦的记录，先添加几条吧～")
else:
    st.info("今天心情不错，那就去记录下让宝宝愉悦的事物吧！")

# ------------- 留言板 -------------
st.markdown("---")
st.subheader("📝 留言板（写给对方的话）")
msg_text = st.text_area("写下你想对对方说的话（最长 300 字）", max_chars=300)
if st.button("发送留言"):
    if msg_text.strip():
        save_message(msg_text.strip())
        st.success("留言已保存 ✅")
        st.experimental_rerun()
    else:
        st.warning("留言不能为空")

msgs = load_messages()
if not msgs.empty:
    st.markdown("**历史留言**")
    for _, r in msgs.iloc[::-1].iterrows():
        st.markdown(f"> {r['时间']} — {r['留言']}")

# ------------- 分析系统 -------------
st.markdown("---")
st.subheader("📊 喜欢度与推荐分析")
df = st.session_state.df.copy()
if df.empty:
    st.info("当前还没有记录，添加几条试试～")
else:
    rec_counts = df["最终推荐"].value_counts()
    st.write("推荐分布：")
    st.bar_chart(rec_counts)
    top_happy = df[df["愉悦度"]=="愉悦"]["名称"].value_counts().head(10)
    st.write("宝宝特别喜欢（愉悦次数最多的物品）:")
    st.table(top_happy.reset_index().rename(columns={"index":"名称","名称":"次数"}))
# ------------- 抽奖中心 -------------  # 【棕红新增】
st.markdown("---")
st.subheader("🎲 抽奖中心")
lot_data = load_lottery()

tab1, tab2, tab3 = st.tabs(["再来一次","获得奖励","设置奖池"])  

with tab1:
    st.write("点按钮随机结果：")
    if st.button("🎯 抽一次（再来一次）"):
        choice = random.choice(lot_data.get("再来一次", ["再试一次"]))
        st.success(f"结果：{choice}")

with tab2:
    st.write("点按钮随机结果：")
    if st.button("🎁 抽一次（获得奖励）"):
        choice = random.choice(lot_data.get("获得奖励", ["亲亲一下","零食？","奶茶一杯"]))
        st.success(f"结果：{choice}")

with tab3:
    st.write("管理两个奖池（用换行分隔每个条目）：")
    colA, colB = st.columns(2)
    with colA:
        a_text = st.text_area("再来一次 奖池", "\n".join(lot_data.get("再来一次", [])))
    with colB:
        b_text = st.text_area("获得奖励 奖池", "\n".join(lot_data.get("获得奖励", [])))
    if st.button("保存奖池设置"):
        lot_data["再来一次"] = [x.strip() for x in a_text.splitlines() if x.strip()]
        lot_data["获得奖励"] = [x.strip() for x in b_text.splitlines() if x.strip()]
        save_lottery(lot_data)
        st.success("已保存奖池")

# ------------- footer -------------
st.markdown("---")
c1, c2 = st.columns([1,1])
with c1:
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 下载记录 CSV", data=csv, file_name="评价记录.csv", mime="text/csv")
with c2:
    if st.button("清空留言（慎用）"):
        Path(MSG_FILE).unlink(missing_ok=True)
        st.success("留言已清空")