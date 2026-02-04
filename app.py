import streamlit as st

# 模拟 10 位用户数据
USERS = {
    "U001": {"name": "张先生", "vin": "LSVAB2024XXXXXX", "model": "宏光 PLUS 2020款", "mileage": 86200, "last_maint": "2026-01-28", "location": "上海浦东", "notes": "客户备注: “这车是不是该换了？”", "maint_records": [{"date": "2026-01-28", "item": "更换底盘衬套", "cost": 1280}], "app_events": [{"time": "2026-02-01 10:23", "event": "打开「置换补贴」页面"}]},
    "U002": {"name": "李女士", "vin": "LZWADAGA3XXXXXX", "model": "五菱宏光 MINIEV 2021款", "mileage": 42000, "last_maint": "2026-02-01", "location": "广州天河", "notes": "多次咨询续航问题", "maint_records": [{"date": "2026-02-01", "item": "电池健康检测", "cost": 0}], "app_events": [{"time": "2026-02-03 14:10", "event": "搜索「MINIEV 升级版」"}]},
    "U003": {"name": "王先生", "vin": "LJDDAA225XXXXXX", "model": "星辰 2022款", "mileage": 68000, "last_maint": "2025-11-15", "location": "成都武侯", "notes": "保险到期未续", "maint_records": [{"date": "2025-11-15", "item": "常规保养", "cost": 320}], "app_events": []},
    "U004": {"name": "赵先生", "vin": "LZWCAAGA7XXXXXX", "model": "缤果 2023款", "mileage": 28500, "last_maint": "2026-01-20", "location": "杭州西湖", "notes": "对智能座舱感兴趣", "maint_records": [{"date": "2026-01-20", "item": "OTA 升级支持", "cost": 0}], "app_events": [{"time": "2026-02-02 19:05", "event": "反复查看「缤果 Pro」配置"}]},
    "U005": {"name": "刘女士", "vin": "LSVAB2025XXXXXX", "model": "宏光 S 2019款", "mileage": 102000, "last_maint": "2025-12-10", "location": "武汉江汉", "notes": "抱怨油耗高、空间小", "maint_records": [{"date": "2025-12-10", "item": "发动机积碳清洗", "cost": 480}], "app_events": []},
    "U006": {"name": "陈先生", "vin": "LJDDAA228XXXXXX", "model": "星光 2024款 PHEV", "mileage": 15200, "last_maint": "2026-01-25", "location": "深圳南山", "notes": "关注充电便利性", "maint_records": [{"date": "2026-01-25", "item": "充电桩兼容性检测", "cost": 0}], "app_events": [{"time": "2026-02-03 08:45", "event": "定位附近超充站"}]},
    "U007": {"name": "孙女士", "vin": "LSVAB2026XXXXXX", "model": "宏光 PLUS 2021款", "mileage": 78000, "last_maint": "2026-01-20", "location": "北京朝阳", "notes": "考虑换车但预算有限", "maint_records": [{"date": "2026-01-20", "item": "空调滤芯更换", "cost": 120}], "app_events": [{"time": "2026-01-30 14:00", "event": "查看老车主置换政策"}]},
    "U008": {"name": "周先生", "vin": "LZWADAGA8XXXXXX", "model": "五菱荣光 2022款", "mileage": 50000, "last_maint": "2026-01-22", "location": "重庆渝中", "notes": "关注车辆保值率", "maint_records": [{"date": "2026-01-22", "item": "轮胎更换", "cost": 800}], "app_events": [{"time": "2026-02-03 10:20", "event": "查看二手车市场行情"}]},
    "U009": {"name": "吴女士", "vin": "LSVAB2027XXXXXX", "model": "宏光 MINIEV 2020款", "mileage": 35000, "last_maint": "2026-01-25", "location": "南京鼓楼", "notes": "希望升级到更高配置", "maint_records": [{"date": "2026-01-25", "item": "电池检查", "cost": 0}], "app_events": [{"time": "2026-02-01 19:45", "event": "询问升级方案"}]},
    "U010": {"name": "郑先生", "vin": "LJDDAA229XXXXXX", "model": "宏光 PLUS 2022款", "mileage": 55000, "last_maint": "2026-01-23", "location": "西安雁塔", "notes": "对车辆性能有要求", "maint_records": [{"date": "2026-01-23", "item": "制动系统检查", "cost": 300}], "app_events": [{"time": "2026-02-02 14:15", "event": "阅读技术文档"}]}
}

# 初始化状态
if 'current_page' not in st.session_state:
    st.session_state.current_page = "user_list"
if 'selected_user_id' not in st.session_state:
    st.session_state.selected_user_id = None
if 'page_num' not in st.session_state:
    st.session_state.page_num = 1
if 'call_result' not in st.session_state:
    st.session_state.call_result = {}  # {uid: "interested" | "declined"}

# 侧边栏导航
with st.sidebar:
    st.title("🧭 导航")
    if st.button("🏠 用户管理中心"):
        st.session_state.current_page = "user_list"
        st.session_state.selected_user_id = None

    if st.session_state.selected_user_id and st.button("👤 客户详情"):
        st.session_state.current_page = "user_detail"

    # AI 和触达页的导航（可选，保持简洁也可删）
    if st.session_state.current_page == "ai_result":
        st.button("🔍 AI分析结果", disabled=True)
    if st.session_state.current_page == "touch_page":
        st.button("📞 触达分发", disabled=True)

    # ✅ 新增：重置所有状态按钮
    st.divider()
    if st.button("🔄 重置所有状态", type="secondary"):
        # 清除关键状态
        st.session_state.call_result = {}
        st.session_state.selected_user_id = None
        st.session_state.current_page = "user_list"
        st.session_state.page_num = 1  # 可选：重置回第一页
        st.rerun()

st.title("🚗 高潜客户识别系统 Demo")
st.caption("*模拟界面 · 数据脱敏*")

# ========== 用户管理中心（带分页） ==========
if st.session_state.current_page == "user_list":
    st.subheader(f"👥 基盘客户池（共 {len(USERS)} 位）")
    
    page_size = 5
    total_pages = (len(USERS) + page_size - 1) // page_size
    start_idx = (st.session_state.page_num - 1) * page_size
    end_idx = start_idx + page_size
    user_subset = list(USERS.items())[start_idx:end_idx]
    
    for idx, (uid, user) in enumerate(user_subset):
        col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])
        with col1:
            st.write(f"**{user['name']}**")
        with col2:
            st.write(user["model"])
        with col3:
            st.write(f"{user['mileage']:,} km")
        with col4:
            status = st.session_state.call_result.get(uid, "待触达")
            color = "green" if status == "interested" else ("red" if status == "declined" else "gray")
            st.markdown(f"<span style='color:{color}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
        
        # ✅ 关键修复：按钮独立一行 + 唯一 key
        btn_key = f"userlist_p{st.session_state.page_num}_i{idx}_u{uid}"
        if st.button(f"👤 查看 {user['name']} 详情", key=btn_key):
            st.session_state.selected_user_id = uid
            st.session_state.current_page = "user_detail"
            st.rerun()
        
        st.divider()

    # 分页控件
    col_prev, col_center, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.session_state.page_num > 1:
            if st.button("⬅️ 上一页", key="btn_prev"):
                st.session_state.page_num -= 1
                st.rerun()
    with col_center:
        st.markdown(
            f"<div style='text-align: center; margin-top: 8px;'>第 {st.session_state.page_num} 页 / 共 {total_pages} 页</div>",
            unsafe_allow_html=True
        )
    with col_next:
        if st.session_state.page_num < total_pages:
            if st.button("➡️ 下一页", key="btn_next"):
                st.session_state.page_num += 1
                st.rerun()

# ========== 客户详情页 ==========
elif st.session_state.current_page == "user_detail":
    user = USERS[st.session_state.selected_user_id]
    st.subheader(f"👤 {user['name']} 的客户档案")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        **基本信息**  
        - VIN: `{user['vin']}`  
        - 车型: {user['model']}  
        - 当前里程: {user['mileage']:,} km  
        - 所在地: {user['location']}  
        - 最后进店: {user['last_maint']}
        """)
    with c2:
        st.markdown(f"**最新反馈**\n> {user['notes']}")

    st.subheader("🔧 近期维修记录")
    for rec in user["maint_records"]:
        st.text(f"{rec['date']} | {rec['item']} | ¥{rec['cost']}")

    st.subheader("📱 APP 行为埋点记录")
    if user["app_events"]:
        for evt in user["app_events"]:
            st.text(f"{evt['time']} | {evt['event']}")
    else:
        st.info("该用户暂无 APP 行为记录")

    st.divider()
    if st.button("🔍 AI 智能分析（评估换购倾向）"):
        st.session_state.current_page = "ai_result"
        st.rerun()
    if st.button("← 返回客户列表"):
        st.session_state.current_page = "user_list"
        # ✅ 不重置 page_num，保持当前位置
        st.rerun()

# ========== AI 分析结果页 ==========
elif st.session_state.current_page == "ai_result":
    user = USERS[st.session_state.selected_user_id]
    score_map = {"U001": 82, "U002": 76, "U004": 70, "U006": 68, "U007": 65, "U009": 55, "U010": 72, "U003": 45, "U005": 58, "U008": 60}
    score = score_map.get(st.session_state.selected_user_id, 50)
    status_label = "高潜" if score >= 70 else ("中潜" if score >= 50 else "低潜")

    st.success(f"⭐ AI 评估得分：{score} / 100 → **{status_label}客户**")
    st.subheader("主导原因")
    reasons = {
        "U001": "- 车龄老化 + 明确换车意向\n- APP 浏览置换页面",
        "U002": "- 新能源车主关注升级\n- 多次查看新车型",
        "U004": "- 年轻用户偏好智能配置\n- 反复查看高配版",
        "U006": "- PHEV 用户关注生态\n- 主动查找充电设施",
        "U007": "- 预算有限但仍考虑换车\n- 关注优惠活动",
        "U009": "- 希望升级到更高配置\n- 询问升级方案",
        "U010": "- 对车辆性能有要求\n- 阅读技术文档",
        "U003": "- 无 APP 行为\n- 保险断档",
        "U005": "- 车龄老、里程高\n- 抱怨产品力",
        "U008": "- 关注保值率\n- 查看二手车行情"
    }
    st.markdown(reasons.get(st.session_state.selected_user_id, "- 综合用车行为分析"))

    st.subheader("🎯 推荐策略")
    if status_label == "高潜":
        st.markdown("""
        - 发放老车主置换补贴 5,000 元  
        - 安排就近门店新能源试驾  
        - 赠送延保5折券
        """)
    elif status_label == "中潜":
        st.markdown("""
        - 推送专属车型对比报告  
        - 邀请参加线下品鉴会
        """)

    if st.button("📞 生成触达任务（电话沟通）"):
        st.session_state.current_page = "touch_page"
        st.rerun()
    if st.button("← 返回客户详情"):
        st.session_state.current_page = "user_detail"
        st.rerun()

# ========== 触达分发页（电话沟通） ==========
elif st.session_state.current_page == "touch_page":
    user = USERS[st.session_state.selected_user_id]
    uid = st.session_state.selected_user_id

    if uid not in st.session_state.call_result:
        st.subheader("📞 模拟电话沟通结果")
        st.info(f"正在呼叫 {user['name']}（{user['location']}）...")
        st.write("请选择客户反馈：")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 客户有兴趣，继续推进", key="btn_interested"):
                st.session_state.call_result[uid] = "interested"
                st.rerun()
        with col2:
            if st.button("❌ 客户明确表示：暂不换车", key="btn_declined"):
                st.session_state.call_result[uid] = "declined"
                st.rerun()
    else:
        result = st.session_state.call_result[uid]
        if result == "declined":
            st.error("❌ 客户在电话中明确表示：**暂不考虑换车**")
            st.warning("系统已记录该状态，**不会下发门店任务**，避免重复打扰。")
            if st.button("← 返回AI分析"):
                st.session_state.current_page = "ai_result"
                st.rerun()
        else:
            # 生成详细地点
            detailed_location = {
                "上海浦东": "上海浦东金桥",
                "广州天河": "广州天河体育中心",
                "杭州西湖": "杭州西湖文三路",
                "深圳南山": "深圳南山科技园",
                "北京朝阳": "北京朝阳望京",
                "南京鼓楼": "南京鼓楼新街口",
                "西安雁塔": "西安雁塔大雁塔",
                "成都武侯": "成都武侯祠附近",
                "武汉江汉": "武汉江汉路步行街",
                "重庆渝中": "重庆渝中解放碑"
            }.get(user["location"], user["location"])

            st.subheader("【动态画像更新】")
            st.info(f"📞 通话摘要：\n“住在{detailed_location}…近期考虑换车，希望了解新能源选项”")
            st.markdown(f"""
            ✅ 自动更新字段：
            - 居住地 → {detailed_location}
            - 购车意向 → 高（预计30天内）
            - 车型偏好 → 新能源 MPV / SUV
            """)

            st.subheader("📍 就近门店智能分发")
            location_map = {
                "上海浦东": (31.23, 121.5),
                "广州天河": (23.13, 113.33),
                "成都武侯": (30.60, 104.06),
                "杭州西湖": (30.25, 120.15),
                "武汉江汉": (30.58, 114.27),
                "深圳南山": (22.52, 113.93),
                "北京朝阳": (39.93, 116.46),
                "重庆渝中": (29.56, 106.55),
                "南京鼓楼": (32.06, 118.78),
                "西安雁塔": (34.21, 108.94)
            }
            lat, lon = location_map[user["location"]]
            st.map(data=[{"lat": lat, "lon": lon}], zoom=10)
            st.markdown(f"**推荐门店**：五菱{user['location'][:2]}店（约1.5km内）\n\n**负责人**：金牌顾问")

            st.success("✅ 任务已推送至飞书，24小时内跟进")

            if st.button("← 返回AI分析"):
                st.session_state.current_page = "ai_result"
                st.rerun()
