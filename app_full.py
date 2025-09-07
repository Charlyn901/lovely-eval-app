import streamlit as st
import pandas as pd
from pathlib import Path
from uuid import uuid4
from datetime import datetime, date, timedelta
import json
import random
import os
from PIL import Image
import io

# ---------------- CONFIG ----------------
st.set_page_config(page_title="我们的专属小站", page_icon="💖", layout="wide")

BASE_DIR = Path.cwd()
DATA_FILE = BASE_DIR / "data.xlsx"
MSG_FILE = BASE_DIR / "messages.csv"
EVENTS_FILE = BASE_DIR / "events.json"
LOTTERY_FILE = BASE_DIR / "lottery.json"
WISH_FILE = BASE_DIR / "wishes.json"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

COLUMNS = ["时间", "物品类型", "名称", "链接", "情境",
           "主评级1", "次评级1", "主评级2", "次评级2",
           "最终分", "最终推荐", "愉悦度", "备注", "照片文件名", "记录ID"]

BASE_TYPES = ["外卖", "生活用品", "化妆品", "数码", "小事", "其他"]

SUB_MAP = {"S": ["S+", "S", "S-"], "A": ["A+", "A", "A-"], "B": ["B+", "B", "B-"], "C": ["C+", "C", "C-"]}
SCORE_MAP = {"S+": 5.0, "S": 4.7, "S-": 4.4,
             "A+": 4.1, "A": 3.8, "A-": 3.5,
             "B+": 3.0, "B": 2.5, "B-": 2.0,
             "C+": 1.5, "C": 1.0, "C-": 0.5}

DEFAULT_LOTTERY = {"再来一次": ["再试一次", "喝口水深呼吸"], "获得奖励": ["亲亲一个", "看电影一次", "买杯奶茶"]}


# ---------------- Helpers ----------------
def now_str(offset_hours: int = 8):
    return (datetime.utcnow() + timedelta(hours=offset_hours)).strftime("%Y-%m-%d %H:%M:%S")


def load_data():
    if DATA_FILE.exists():
        try:
            df = pd.read_excel(DATA_FILE, engine="openpyxl")
            for c in COLUMNS:
                if c not in df.columns:
                    df[c] = ""
            if "记录ID" not in df.columns:
                df["记录ID"] = ""
            df["记录ID"] = df["记录ID"].apply(lambda x: x if isinstance(x, str) and x.strip() else uuid4().hex)
            return df[COLUMNS]
        except Exception as e:
            st.error(f"读取 {DATA_FILE} 出错：{e}")
            return pd.DataFrame(columns=COLUMNS)
    else:
        return pd.DataFrame(columns=COLUMNS)


def save_data(df):
    try:
        df.to_excel(DATA_FILE, index=False, engine="openpyxl")
    except Exception as e:
        st.error(f"保存失败：{e}")


def load_messages():
    if MSG_FILE.exists():
        try:
            return pd.read_csv(MSG_FILE, encoding="utf-8")
        except:
            return pd.DataFrame(columns=["时间", "留言"])
    else:
        return pd.DataFrame(columns=["时间", "留言"])


def save_message(text, tz_offset=8):
    dfm = load_messages()
    new = {"时间": now_str(tz_offset), "留言": text}
    dfm = pd.concat([dfm, pd.DataFrame([new])], ignore_index=True)
    dfm.to_csv(MSG_FILE, index=False, encoding="utf-8-sig")


def load_events():
    if EVENTS_FILE.exists():
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_events(events_dict):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events_dict, f, ensure_ascii=False, indent=2)


def load_lottery():
    if LOTTERY_FILE.exists():
        try:
            with open(LOTTERY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_LOTTERY.copy()
    return DEFAULT_LOTTERY.copy()


def save_lottery(d):
    with open(LOTTERY_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def load_wishes():
    if WISH_FILE.exists():
        try:
            with open(WISH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


def save_wishes(wishes):
    with open(WISH_FILE, "w", encoding="utf-8") as f:
        json.dump(wishes, f, ensure_ascii=False, indent=2)


def save_uploaded_image(uploaded_file):
    if uploaded_file is None:
        return ""
    filename = f"{uuid4().hex}{Path(uploaded_file.name).suffix}"
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(path.name)


# ---------------- Session init ----------------
if "df" not in st.session_state:
    st.session_state.df = load_data()
if "images" not in st.session_state:
    st.session_state.images = {p.name: str(p) for p in UPLOAD_DIR.glob("*")}
if "tz_offset" not in st.session_state:
    st.session_state.tz_offset = 8
if "theme" not in st.session_state:
    st.session_state.theme = "樱粉清新"

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙ 设置")
    w1 = st.slider("主评级权重（主）", 0.0, 1.0, 0.7, step=0.05)
    w2 = round(1.0 - w1, 2)
    st.text(f"二次评级权重（次）自动为：{w2}")
    thr_rec = st.number_input("推荐阈值（>=）", value=4.2, step=0.1)
    thr_ok = st.number_input("还行阈值（>=）", value=3.0, step=0.1)
    st.markdown("---")
    st.subheader("时间与主题")
    tz = st.number_input("时区偏移（相对 UTC，例如：北京时间=8）", value=st.session_state.tz_offset, step=1)
    st.session_state.tz_offset = int(tz)
    theme = st.selectbox("🎨 主题", ["樱粉清新", "夜间黑银", "极光薄荷"])
    st.session_state.theme = theme
    st.markdown("---")
    st.subheader("重要事件（纪念日）")
    events = load_events()
    if events:
        for k, v in events.items():
            st.write(f"- {k} → {v}")
    new_name = st.text_input("新增事件名称（例：恋爱纪念日）")
    new_date = st.date_input("日期（每年重复）", value=date.today())
    if st.button("添加事件"):
        if new_name.strip():
            events[new_name] = new_date.isoformat()
            save_events(events)
            st.success("已添加事件")
    st.markdown("---")
    st.subheader("数据导出/清理")
    if st.button("导出记录（Excel）"):
        if DATA_FILE.exists():
            with open(DATA_FILE, "rb") as f:
                st.download_button("下载 data.xlsx", data=f, file_name="data.xlsx")
        else:
            st.warning("当前无 data.xlsx")
    if st.button("清空所有记录（慎用）"):
        st.session_state.df = st.session_state.df.iloc[0:0]
        save_data(st.session_state.df)
        st.success("已清空")


# ---------------- Theme CSS ----------------
def get_theme_css(name):
    if name == "樱粉清新":
        return """
        <style>
        body{background:linear-gradient(180deg,#fff8fb,#fff); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;}
        .header{background:linear-gradient(90deg,#ff9a9e,#fecfef); padding:12px; border-radius:12px; color:white; margin-bottom:8px;}
        .card{border-radius:12px; padding:10px; box-shadow:0 4px 10px rgba(0,0,0,0.06); background:linear-gradient(180deg,#ffffff,#fff7fb); margin-bottom:10px;}
        .small-muted{ color:#666; font-size:12px;}
        button, .stButton>button { border-radius:8px; }
        </style>
        """
    if name == "夜间黑银":
        return """
        <style>
        body{background:#0f1113;color:#eaeaea;font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;}
        .header{background:linear-gradient(90deg,#222,#333); padding:12px;border-radius:12px;color:#fff;margin-bottom:8px;}
        .card{border-radius:12px;padding:10px;background:#111218;box-shadow:0 4px 10px rgba(0,0,0,0.6);margin-bottom:10px;}
        .small-muted{ color:#9aa0a6; font-size:12px;}
        .stButton>button{ background:#1f6feb; color:white; }
        </style>
        """
    return """
    <style>
    body{background:linear-gradient(180deg,#f0fffb,#fff);font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;}
    .header{background:linear-gradient(90deg,#00d2ff,#3a7bd5); padding:12px;border-radius:12px;color:#fff;margin-bottom:8px;}
    .card{border-radius:12px;padding:10px;background:linear-gradient(180deg,#ffffff,#f3fdff);box-shadow:0 6px 18px rgba(0,0,0,0.04);margin-bottom:10px;}
    .small-muted{ color:#556; font-size:12px;}
    </style>
    """


st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)
st.markdown('<div class="header"><h2 style="margin:0">💖 我们的专属小站</h2></div>', unsafe_allow_html=True)

# ---------------- Layout ----------------
left, right = st.columns([1, 1.25])

with left:
    st.subheader("➕ 添加记录 / 随手记（小事）")
    with st.form("add_form", clear_on_submit=True):
        itype = st.selectbox("类型", options=BASE_TYPES)
        name = st.text_input("名称 / 事件（例如：奶茶 / 一起散步 / 你今天笑）", max_chars=80)
        link = st.text_input("链接（可选）")
        ctx = st.selectbox("情境", ["在家", "通勤", "旅行", "工作", "约会", "其他"])
        col1, col2 = st.columns(2)
        with col1:
            main1 = st.selectbox("主评级 1", ["S", "A", "B", "C"], index=0, key="m1")
            sub1 = st.selectbox("细分 1", SUB_MAP[main1], key="s1")
        with col2:
            main2 = st.selectbox("主评级 2", ["S", "A", "B", "C"], index=0, key="m2")
            sub2 = st.selectbox("细分 2", SUB_MAP[main2], key="s2")
        mood = st.radio("愉悦度", ["愉悦", "还行", "不愉悦"], index=1)
        remark = st.text_area("备注 / 给对方的话（会保存）", max_chars=300)
        photo = st.file_uploader("上传照片（可选）", type=["png", "jpg", "jpeg"])
        surprise = st.checkbox("显示小情话（保存后）", value=True)
        submitted = st.form_submit_button("添加并保存")

    if submitted:
        if not name.strip():
            st.warning("名称不能为空")
        else:
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
                        photo_name = save_uploaded_image(photo)
                        st.session_state.images[photo_name] = str(UPLOAD_DIR / photo_name)
                    except Exception as e:
                        st.error(f"保存图片失败：{e}")

                new_row = {
                    "时间": now_str(st.session_state.tz_offset),
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
                    "照片文件名": photo_name,
                    "记录ID": uuid4().hex
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

with right:
    st.subheader("📚 记录总览（筛选 / 搜索）")
    df_view = st.session_state.df.copy()

    # 类型选项（保证基础类型始终出现）
    base_type_set = set(BASE_TYPES)
    type_options = ["全部"] + sorted(list(base_type_set.union(set(df_view["物品类型"].dropna().unique().tolist()))))
    f_type = st.selectbox("按类型", options=type_options, index=0)
    f_rec = st.selectbox("按最终推荐", options=["全部", "推荐", "还行", "不推荐"], index=0)
    f_mood = st.selectbox("按愉悦度", options=["全部", "愉悦", "还行", "不愉悦"], index=0)
    kw = st.text_input("关键字搜索（名称/备注/链接/情境）", "")

    if f_type != "全部":
        df_view = df_view[df_view["物品类型"] == f_type]
    if f_rec != "全部":
        df_view = df_view[df_view["最终推荐"] == f_rec]
    if f_mood != "全部":
        df_view = df_view[df_view["愉悦度"] == f_mood]
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
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{row['名称']}**  ·  {row['物品类型']}  ·  {row['情境']}")
            st.markdown(f"<div class='small-muted'>评级：{row['主评级1']}({row['次评级1']})  /  {row['主评级2']}({row[
                '次评级2']})  →  <strong>{row['最终分']}</strong>  · 推荐：<strong>{row['最终推荐']}</strong></div>",
                        unsafe_allow_html=True)
            if row['链接']:
                st.markdown(f"[查看链接]({row['链接']})")
            if row['备注']:
                st.markdown(f"*备注：{row['备注']}*")
        with c2:
            if row['照片文件名'] and row['照片文件名'] in st.session_state.images:
                try:
                    st.image(st.session_state.images[row['照片文件名']], width=140)
                except:
                    st.write("")
            else:
                st.write("")

        rid = row.get("记录ID", "")
        if rid:
            if st.button("🗑 删除该记录", key=f"del_{rid}"):
                df_all = st.session_state.df
                st.session_state.df = df_all[df_all["记录ID"] != rid]
                save_data(st.session_state.df)
                st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 心情中心 ----------------
st.markdown("---")
st.subheader("💌 心情中心")
mood_today = st.selectbox("今天心情如何？", ["愉悦", "还行", "不愉悦"], index=1)
ctx_filter = st.selectbox("按情境筛选安慰（可选）", [""] + ["在家", "通勤", "旅行", "工作", "约会", "其他"])
if mood_today == "不愉悦":
    past_good = st.session_state.df[st.session_state.df["愉悦度"] == "愉悦"]
    if ctx_filter:
        past_good = past_good[past_good["情境"] == ctx_filter]
    names = past_good["名称"].dropna().unique().tolist()
    if names:
        sel = st.selectbox("这些曾经让你愉悦过：", names)
        if sel:
            chosen = past_good[past_good["名称"] == sel].iloc[-1]
            st.success(f"想想 {sel} 的美好吧～ 备注：{chosen.get('备注', '')}")
            fn = chosen.get("照片文件名", "")
            if fn and fn in st.session_state.images:
                st.image(st.session_state.images[fn], width=300)
    else:
        st.info("还没有你标记为愉悦的记录，先添加几条吧～")
else:
    st.info("今天心情不错，那就去记录下让你愉悦的事物吧！")

# ---------------- 留言板 ----------------
st.markdown("---")
st.subheader("📝 留言板（写给对方）")
msg_text = st.text_area("写下你想对对方说的话（最长 300 字）", max_chars=300)
if st.button("发送留言"):
    if msg_text.strip():
        save_message(msg_text.strip(), st.session_state.tz_offset)
        st.success("留言已保存 ✅")
        st.experimental_rerun()
    else:
        st.warning("留言不能为空")

msgs = load_messages()
if not msgs.empty:
    st.markdown("**历史留言**")
    for _, r in msgs.iloc[::-1].iterrows():
        st.markdown(f"> {r['时间']} — {r['留言']}")

# ---------------- 分析与照片墙 ----------------
st.markdown("---")
st.subheader("📊 喜欢度与推荐分析")
df = st.session_state.df.copy()
if df.empty:
    st.info("当前还没有记录，添加几条试试～")
else:
    rec_counts = df["最终推荐"].value_counts()
    st.write("推荐分布：")
    st.bar_chart(rec_counts)
    top_happy = df[df["愉悦度"] == "愉悦"]["名称"].value_counts().head(10)
    st.write("她特别喜欢（愉悦次数最多的物品）:")
    st.table(top_happy.reset_index().rename(columns={"index": "名称", "名称": "次数"}))

# 心情连击
st.markdown("---")
st.subheader("🔥 心情连击（连续愉悦天数）")
if not df.empty:
    df_mood = df.copy()
    df_mood["日期"] = pd.to_datetime(df_mood["时间"]).dt.date
    daily = df_mood.groupby("日期")["愉悦度"].apply(lambda x: "愉悦" if "愉悦" in x.values else "非愉悦")
    streak = 0
    for mood in reversed(daily.values):
        if mood == "愉悦":
            streak += 1
        else:
            break
    st.write(f"你们已经连续 **{streak} 天愉悦** ✨")
else:
    st.info("还没有数据，快去添加第一条记录吧～")

# 照片墙
st.markdown("---")
st.subheader("📸 照片墙")
imgs = list(UPLOAD_DIR.glob("*"))
if imgs:
    cols = st.columns(3)
    for i, im in enumerate(imgs):
        with cols[i % 3]:
            try:
                st.image(str(im), use_column_width=True)
            except:
                st.write("")
else:
    st.info("还没有上传照片哦～")

# ---------------- 抽奖中心 ----------------
st.markdown("---")
st.subheader("🎲 抽奖中心")
lot = load_lottery()
tab1, tab2, tab3 = st.tabs(["再来一次", "获得奖励", "管理奖池"])
with tab1:
    st.write("点按钮随机一条“再来一次”的建议")
    if st.button("🎯 抽一次（再来一次）"):
        choice = random.choice(lot.get("再来一次", ["再试一次"]))
        st.success(f"结果：{choice}")
with tab2:
    st.write("点按钮随机一条“获得奖励”")
    if st.button("🎁 抽一次（获得奖励）"):
        choice = random.choice(lot.get("获得奖励", ["亲亲一下", "看电影", "奶茶一杯"]))
        st.success(f"结果：{choice}")
with tab3:
    st.write("管理奖池（每行一个条目）")
    colA, colB = st.columns(2)
    with colA:
        a_text = st.text_area("再来一次 奖池", "\n".join(lot.get("再来一次", [])))
    with colB:
        b_text = st.text_area("获得奖励 奖池", "\n".join(lot.get("获得奖励", [])))
    if st.button("保存奖池设置"):
        lot["再来一次"] = [x.strip() for x in a_text.splitlines() if x.strip()]
        lot["获得奖励"] = [x.strip() for x in b_text.splitlines() if x.strip()]
        save_lottery(lot)
        st.success("已保存奖池")

# ---------------- 心愿清单 ----------------
st.markdown("---")
st.subheader("🌠 心愿清单")
wishes = load_wishes()
with st.form("add_wish", clear_on_submit=True):
    new_wish = st.text_input("添加一个心愿（例如：一起看日出）")
    if st.form_submit_button("添加心愿"):
        if new_wish.strip():
            wishes.append({"text": new_wish.strip(), "done": False, "id": uuid4().hex})
            save_wishes(wishes)
            st.success("心愿已添加")
            st.experimental_rerun()

if wishes:
    done_count = sum(1 for w in wishes if w.get("done"))
    st.write(f"完成率：{done_count}/{len(wishes)}")
    for w in wishes:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(("✅ " if w.get("done") else "🔲 ") + w.get("text"))
        with col2:
            if st.button("切换状态", key=f"wish_{w.get('id')}"):
                w["done"] = not w.get("done")
                save_wishes(wishes)
                st.experimental_rerun()
else:
    st.info("还没有心愿，快添加一个吧～")

# ---------------- Footer: 导出 / 清理 ----------------
st.markdown("---")
c1, c2 = st.columns([1, 1])
with c1:
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 下载记录 CSV", data=csv, file_name="评价记录.csv", mime="text/csv")
with c2:
    if st.button("清空留言（慎用）"):
        MSG_FILE.unlink(missing_ok=True)
        st.success("留言已清空")
