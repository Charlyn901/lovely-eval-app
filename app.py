import streamlit as st
import pandas as pd
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import json
import random
import pytz

# ---------------- CONFIG ----------------
st.set_page_config(page_title="我们的专属小站", page_icon="💖", layout="wide")

DATA_FILE = "data.csv"
MSG_FILE = "messages.csv"
LOTTERY_FILE = "lottery.json"
WISH_FILE = "wishes.json"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

COLUMNS = [
    "时间","用户","物品类型","名称","链接","情境",
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
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
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
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

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

# ---------------- Sidebar 设置 ----------------
with st.sidebar:
    st.header("⚙ 设置")
    # 权重调整
    w1 = st.slider("主评级权重", 0.0, 1.0, 0.7, step=0.05)
    w2 = round(1.0 - w1, 2)
    st.text(f"次评级权重：{w2}")

    # 主题切换
    theme = st.selectbox("主题切换", ["樱粉清新","夜间黑银","极光薄荷"])
    st.session_state.theme = theme

# ---------------- Theme CSS ----------------
def get_theme_css(name):
    if name == "樱粉清新":
        return """
        <style>
        body, .stApp {background:#fff0f5;}
        .card{border-radius:12px; padding:10px; background:#fff7fb; margin-bottom:10px;}
        </style>
        """
    if name == "夜间黑银":
        return """
        <style>
        body, .stApp {background:#0f1113; color:#eaeaea;}
        .card{border-radius:12px; padding:10px; background:#1a1a1d; margin-bottom:10px;}
        </style>
        """
    return """
    <style>
    body, .stApp {background:#e0fff8;}
    .card{border-radius:12px; padding:10px; background:#f3fdff; margin-bottom:10px;}
    </style>
    """

st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)
st.title("💖 我们的专属小站")

# ---------------- 主页面 ----------------
left, right = st.columns([1,1.25])

# ---------------- 左侧：添加记录（含“仅当同名记录存在时才触发二次评级”） ----------------
with left:
    st.subheader("➕ 添加记录")
    with st.form("add_form", clear_on_submit=True):
        user=st.sslectbox("选择用户",["uuu","ooo"],index=0)
        itype = st.selectbox("类型", options=BASE_TYPES)
        name = st.text_input("名称/事件", key="input_name")
        link = st.text_input("链接（可选）", key="input_link")
        ctx = st.selectbox("情境", ["在家", "通勤", "旅行", "工作", "约会", "其他"], key="input_ctx")

        # 主评级与细分（始终显示主评级1 与 细分1）
        main1 = st.selectbox("主评级1", ["S", "A", "B", "C"], key="main1")
        sub1 = st.selectbox("细分1", SUB_MAP[main1], key="sub1")

        # 检查是否存在历史同名记录（不区分大小写）
        update_mode = False
        existing_latest_idx = None
        if name.strip():
            df_all = st.session_state.get("df", pd.DataFrame(columns=COLUMNS))
            mask = df_all["名称"].fillna("").str.lower() == name.strip().lower()
            if mask.any():
                existing = df_all[mask].copy()
                # 解析时间并取最近一条
                existing["__time_parsed"] = pd.to_datetime(existing["时间"], errors="coerce")
                existing = existing.sort_values("__time_parsed")
                latest_row = existing.iloc[-1]
                existing_count = existing.shape[0]
                st.info(f"检测到历史记录（{existing_count} 条）与该名称匹配。")
                op = st.radio("操作选项", ("创建新条目", "把这次作为二次评级，更新最近一条记录"), index=0, key="op_mode")
                if op == "把这次作为二次评级，更新最近一条记录":
                    update_mode = True
                    existing_latest_idx = latest_row.name  # 这是原 DataFrame 的索引
                    st.markdown("将把此次输入作为**二次评级**更新最近一条同名记录。")
                    # 只在更新模式下显示主/细分2（用于更新历史记录）
                    main2 = st.selectbox("主评级2（用于更新）", ["S", "A", "B", "C"], key="main2")
                    sub2 = st.selectbox("细分2（用于更新）", SUB_MAP[main2], key="sub2")
            else:
                # 没有同名历史 —— 不显示二次评级（按你的要求）
                pass

        # 其余字段
        mood = st.radio("愉悦度", ["愉悦", "还行", "不愉悦"], index=1, key="mood_input")
        remark = st.text_area("备注", key="remark_input")
        photo = st.file_uploader("上传照片", type=["png", "jpg", "jpeg"], key="photo_input")

        submitted = st.form_submit_button("保存")

    # 提交处理逻辑
    if submitted:
        if not name.strip():
            st.warning("请输入名称！")
        else:
            # 更新已有记录（把这次作为二次评级）
            if update_mode and existing_latest_idx is not None:
                df_all = st.session_state.df
                # 读取最近一条记录的次评级1（作为 v1）
                prev_sub1 = df_all.at[existing_latest_idx, "次评级1"]
                v1 = SCORE_MAP.get(prev_sub1)
                v2 = SCORE_MAP.get(sub2)
                if v1 is None or v2 is None:
                    st.error("读取历史评级或当前评级失败，无法计算分数。")
                else:
                    final_score = round(w1 * v1 + w2 * v2, 3)
                    if final_score >= 4.2:
                        rec = "推荐"
                    elif final_score >= 3.0:
                        rec = "还行"
                    else:
                        rec = "不推荐"
                    # 更新历史记录对应字段
                    df_all.at[existing_latest_idx, "主评级2"] = main2
                    df_all.at[existing_latest_idx,"用户"]=user
                    df_all.at[existing_latest_idx, "次评级2"] = sub2
                    df_all.at[existing_latest_idx, "最终分"] = final_score
                    df_all.at[existing_latest_idx, "最终推荐"] = rec
                    df_all.at[existing_latest_idx, "时间"] = now_str()
                    # 如果上传了图片，写入并更新照片文件名
                    if photo:
                        fn = save_uploaded_image(photo)
                        df_all.at[existing_latest_idx, "照片文件名"] = fn
                    save_data(df_all)
                    st.session_state.df = df_all
                    st.success("已把此次作为二次评级并更新最近一条记录。")
                    st.rerun()

            # 新增一条记录（只有主评级1/细分1）
            else:
                v1 = SCORE_MAP.get(sub1)
                if v1 is None:
                    st.error("评级解析失败，保存被中止。")
                else:
                    # 如果只有一次评级，我们把最终分设为 v1（更直观），等待将来可能的二次评级合并
                    final_score = round(v1, 3)
                    if final_score >= 4.2:
                        rec = "推荐"
                    elif final_score >= 3.0:
                        rec = "还行"
                    else:
                        rec = "不推荐"
                    photo_name = save_uploaded_image(photo) if photo else ""
                    new_row = {
                        "时间": now_str(),
                        "用户":user,
                        "物品类型": itype,
                        "名称": name,
                        "链接": link,
                        "情境": ctx,
                        "主评级1": main1, "次评级1": sub1,
                        "主评级2": "", "次评级2": "",
                        "最终分": final_score, "最终推荐": rec,
                        "愉悦度": mood, "备注": remark,
                        "照片文件名": photo_name,
                        "记录ID": uuid4().hex
                    }
                    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.df)
                    st.success("已保存新记录！")
                    # 保存时显示情话或安慰（沿用原逻辑）
                    love_data = load_love_lines()
                    if mood == "不愉悦":
                        if love_data.get("comfort"):
                            st.info(random.choice(love_data["comfort"]))
                        else:
                            st.info("别难过，我在你身边。")
                    else:
                        if love_data.get("love"):
                            st.info(random.choice(love_data["love"]))
                        else:
                            st.info("你是我的小确幸。")    if submitted:
        v1, v2 = SCORE_MAP[sub1], SCORE_MAP[sub2]
        final_score = round(w1*v1+w2*v2,3)
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

        # --- 情话 & 安慰 ---
        love_lines = [
            "宝贝，和你在一起的点滴我都想收藏。",
            "看到你笑，我就觉得今天值了。",
            "你就是我心里永远的欢喜。",
            "有你的日子，普通的生活也会发光。"
        ]
        comfort_lines = [
            "别难过啦，我永远在你身边陪着你。",
            "抱抱你，一切都会慢慢好起来的。",
            "小狗希望你能多笑一点，不开心都给我。",
            "今天的乌云，也挡不住我对你满满的爱。"
        ]
        if mood == "不愉悦":
            st.info(random.choice(comfort_lines))
        else:
            st.info(random.choice(love_lines))

with right:
    st.subheader("📚 记录总览")
 with right:
    st.subheader("📚 记录总览")
    df_view = st.session_state.df.copy()

    current_user=st.selectbox("查看哪个用户的数据",["uuu","ooo","全部"],index=2)
    if current_user !="全部"
         df_view=df_viewdf_view["用户"]==current_user]
    # 筛选类型 + 关键字搜索
    f_type = st.selectbox("筛选类型", ["全部"] + BASE_TYPES)
    if f_type != "全部":
        df_view = df_view[df_view["物品类型"] == f_type]

    kw = st.text_input("关键字搜索")
    if kw.strip():
        df_view = df_view[df_view["名称"].str.contains(kw, na=False)]

    # 多选删除：显示记录并允许勾选
    st.write("选择要删除的记录（可多选）：")
    selected_ids = st.multiselect(
        "多选记录（显示 名称+时间）",
        options=[
            f"{row['记录ID']}|{row['名称']}|{row['时间']}"
            for _, row in df_view.iterrows()
        ],
        format_func=lambda x: x.split("|")[1] + "（" + x.split("|")[2] + "）"
    )

    if st.button("🗑 删除选中记录"):
        if selected_ids:
            # 解析 ID 部分
            ids = [x.split("|")[0] for x in selected_ids]
            st.session_state.df = st.session_state.df[
                ~st.session_state.df["记录ID"].isin(ids)
            ]
            save_data(st.session_state.df)
            st.success(f"已删除 {len(ids)} 条记录。")
            st.rerun()
        else:
            st.warning("请先选择至少一条记录再删除。")

    st.write("—— 最近 5 条记录预览 ——")
    st.dataframe(df_view.tail(5))
        st.write(f"**{row['名称']}** · {row['物品类型']} · {row['最终推荐']} ({row['愉悦度']})")
        if row["备注"]: st.write(row["备注"])
        rid=row["记录ID"]
        if st.button("🗑 删除", key=f"del_{rid}"):
            st.session_state.df = st.session_state.df[st.session_state.df["记录ID"]!=rid]
            save_data(st.session_state.df)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 心情中心（情话 / 安慰 / 推荐曾让她愉悦的记录） ----------------
st.markdown("---")
st.subheader("💬 心情中心（需要时来这里）")

# 让用户选择当前心情（显示交互）
mood_now = st.selectbox("你现在的心情是？", ["愉悦", "还行", "不愉悦"], index=1)
# 可选：按情境筛选推荐
ctx_filter = st.selectbox("按情境筛选推荐（可选）", ["全部", "在家", "通勤", "旅行", "工作", "约会", "其他"])

# 读取情话/安慰池（如果你已实现 load_love_lines()）
try:
    love_data = load_love_lines()
except Exception:
    love_data = {"love": [], "comfort": []}

if mood_now == "愉悦":
    # 选一句情话展示
    if love_data.get("love"):
        st.success(random.choice(love_data["love"]))
    else:
        st.success("今天很美好，小狗在知道你很开心以后更美好了❤️")

elif mood_now == "不愉悦":
    # 推荐曾经标注为“愉悦”的记录
    df_all = st.session_state.get("df", pd.DataFrame(columns=COLUMNS)).copy()
    # 过滤出标注为愉悦的条目
    past_good = df_all[df_all["愉悦度"] == "愉悦"]
    if ctx_filter != "全部":
        past_good = past_good[past_good["情境"] == ctx_filter]

    if past_good.empty:
        st.info("还没有标注为“愉悦”的记录，先添加几条我好给你推荐～")
        # 同时也给一句安慰
        if love_data.get("comfort"):
            st.info(random.choice(love_data["comfort"]))
        else:
            st.info("小狗来抱抱你，可以吗？一切都会慢慢好起来。")
    else:
        st.write("下面是曾让你愉悦的记录（选一条回味/看图安慰）：")
        names = past_good["名称"].fillna("").unique().tolist()
        sel = st.selectbox("选择一条记录查看详情", ["不选"] + names)
        if sel and sel != "不选":
            chosen = past_good[past_good["名称"] == sel].iloc[-1]  # 取最近一条同名记录
            st.markdown(f"**{chosen['名称']}** · {chosen['物品类型']}  ·  {chosen['情境']}")
            if pd.notna(chosen.get("备注")) and chosen.get("备注"):
                st.markdown(f"> {chosen['备注']}")
            if pd.notna(chosen.get("链接")) and chosen.get("链接"):
                st.markdown(f"[打开链接]({chosen['链接']})")
            # 显示图片（如果有并且加载成功）
            fn = chosen.get("照片文件名", "")
            if fn and fn in st.session_state.get("images", {}):
                try:
                    st.image(st.session_state["images"][fn], width=320)
                except Exception:
                    pass
            # 最后再给一句安慰话（或鼓励）
            if love_data.get("comfort"):
                st.info(random.choice(love_data["comfort"]))
            else:
                st.info("会好起来的，我永远在你身边。")

else:
    st.info("如果需要一句甜言或一些小建议，随时来这里告诉我～")
# ---------------- 心情中心 结束 ----------------

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
        st.rerun()
for w in wishes:
    col1,col2=st.columns([6,1])
    with col1: st.write(("✅" if w["done"] else "🔲")+w["text"])
    with col2:
        if st.button("切换", key=w["id"]):
            w["done"]=not w["done"]
            save_wishes(wishes)
            st.rerun()

# ---------------- 留言板（增强版，可浏览/搜索） ----------------
st.markdown("---")
st.subheader("📝 留言板")

# 输入与保存留言
msg_text = st.text_area("写下想说的话")
if st.button("发送留言"):
    if msg_text.strip():
        save_message(msg_text.strip())
        st.success("已保存")
        st.rerun()

# 读取历史留言
msgs = load_messages()

# 浏览功能：按关键字搜索 + 选择显示最近多少条
colA, colB = st.columns([1,1])
with colA:
    kw_msg = st.text_input("搜索留言关键字", "")
with colB:
    limit = st.selectbox("显示最近多少条", [5,10,20,50,100], index=1)

if kw_msg.strip():
    msgs_view = msgs[msgs["留言"].str.contains(kw_msg, na=False)]
else:
    msgs_view = msgs

if not msgs_view.empty:
    st.write(f"共 {len(msgs_view)} 条留言，显示最近 {limit} 条：")
    # 倒序显示最近 limit 条
    for _, r in msgs_view.iloc[::-1].head(limit).iterrows():
        st.markdown(f"""
        <div style='padding:8px;margin:4px 0;border-bottom:1px solid #ddd;'>
            <b>{r['时间']}</b><br>{r['留言']}
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("暂无留言")
# ---------------- 全局美化CSS ----------------
st.markdown("""
<style>
/* 统一按钮风格 */
button[data-baseweb="button"] {
    background: linear-gradient(135deg, #f78ca0 0%, #f9748f 100%);
    color: white !important;
    border-radius: 8px;
    border: none;
    padding: 0.4rem 0.9rem;
    font-weight: 600;
    transition: 0.2s;
}
button[data-baseweb="button"]:hover {
    background: linear-gradient(135deg, #f9748f 0%, #f78ca0 100%);
    transform: scale(1.03);
}
/* 卡片风格 */
.card {
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    border-radius: 10px;
    padding: 10px;
    background: #ffffffcc;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)