"""车型销量预测看板。

预测逻辑完全委托给各车型目录下自己的 predict_*.py（每个模型的特征处理不同，
以各脚本为准）。本文件只负责扫描月份、调用脚本的 predict_month(year, month)、
把结果按月拼接展示。

注意：目标环境需安装 TensorFlow（模型为 Keras 2 HDF5，需 TF <= 2.15）才能真实推理；
本地无 TF 时可用占位 tensorflow 模块（predict 返回 [100, 110, ...]）走通界面。
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ============================ 车型配置 ============================
# 每个车型 = 一个目录，目录下放它自己的 predict_*.py 脚本（含特征处理）与月度模型文件夹
MODELS = {
    "bingo": {"folder": "bingo", "script": "predict_bingo.py"},
    "MINI": {"folder": "MINI", "script": "predict_mini.py"},
    "星光": {"folder": "xingguang", "script": "predict_xingguang.py"},  # 目录名 xingguang
    "微货": {"folder": "微货", "script": "predict_weihuo.py"},
}

st.set_page_config(page_title="车型销量预测看板", layout="wide")
st.title("车型销量预测看板")


# ============================ 工具 ============================
@st.cache_data(show_spinner=False)
def scan_months(data_dir_str: str, model_key: str) -> list[tuple[int, int]]:
    """扫描某车型下形如 YYYY_MM 的月度文件夹（要求该月文件夹里有 keras 模型文件）。"""
    cfg = MODELS[model_key]
    root = Path(data_dir_str) / cfg["folder"]
    script = root / cfg["script"]
    if not (root.is_dir() and script.is_file()):
        return []
    months = []
    for sub in sorted(root.iterdir()):
        if sub.is_dir() and len(sub.name) == 7 and sub.name[4] == "_":
            try:
                year, month = int(sub.name[:4]), int(sub.name[5:])
            except ValueError:
                continue
            if any(sub.glob("*.keras")):
                months.append((year, month))
    return months


def load_predict_namespace(script_path: Path):
    """加载某车型自己的预测脚本，返回其命名空间。

    每个模型文件夹下的 predict_*.py 末尾都有演示代码（直接调用 predict_month），
    import 时会真的跑预测。这里用 AST 把这些尾部演示语句剥掉，只保留函数定义，
    从而安全地拿到脚本里的 read_file_model / predict_month / 特征处理逻辑。
    """
    src = script_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(script_path))
    # Python 3.7 的 AST 节点没有 end_lineno，按最后一个函数/类在 body 中的位置截断
    last_def_index = max(
        i for i, node in enumerate(tree.body) if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    )
    keep = tree.body[: last_def_index + 1]
    new_tree = ast.Module(body=keep, type_ignores=[])
    ast.fix_missing_locations(new_tree)
    namespace = {"__name__": script_path.stem}
    exec(compile(new_tree, str(script_path), "exec"), namespace)  # noqa: S102
    return namespace, hashlib.md5(src.encode("utf-8")).hexdigest()


def read_fill_config(root: Path, year: int, month: int) -> pd.Series:
    fc = pd.read_excel(root / "fill_config.xlsx", engine="openpyxl")
    mask = (fc["年份"] == year) & (fc["月份"] == month)
    return fc[mask].iloc[0]


@st.cache_data(show_spinner=False)
def month_meta(data_dir_str: str, model_key: str, year: int, month: int, script_md5: str) -> tuple:
    """读取某月的日期与真实销量（用于折线参考），返回 (日期列表, 真实值列表, 行区间)。"""
    cfg = MODELS[model_key]
    root = Path(data_dir_str) / cfg["folder"]
    row = read_fill_config(root, year, month)
    start_row, end_row = int(row.iloc[4]), int(row.iloc[5])
    month_dir = root / f"{year}_{month:02d}"

    def _data_xlsx(directory: Path):
        for candidate in sorted(directory.glob("*.xlsx")):
            if candidate.name != "fill_config.xlsx" and "zhengce" not in candidate.name:
                return candidate
        return None

    # 优先用月度文件夹里的 xlsx（最新数据），退回车型根目录的
    xlsx = _data_xlsx(month_dir) or _data_xlsx(root)
    if not xlsx.is_file():
        return [], None, (start_row, end_row)
    df = pd.read_excel(xlsx, engine="openpyxl").iloc[start_row:end_row]
    dates = pd.to_datetime(df["月份"]).dt.strftime("%m-%d").tolist()
    target_col = "invoicing_count" if model_key == "bingo" else "销量"
    actual = df[target_col].tolist() if target_col in df.columns else None
    return dates, actual, (start_row, end_row)


@st.cache_data(show_spinner=False)
def actual_month_total(data_dir_str: str, model_key: str, year: int, month: int) -> float | None:
    """当月真实销量总和（没有真实数据时返回 None）。"""
    cfg = MODELS[model_key]
    root = Path(data_dir_str) / cfg["folder"]
    try:
        row = read_fill_config(root, year, month)
    except Exception:
        return None
    start_row, end_row = int(row.iloc[4]), int(row.iloc[5])
    month_dir = root / f"{year}_{month:02d}"

    def _data_xlsx(directory: Path):
        for candidate in sorted(directory.glob("*.xlsx")):
            if candidate.name != "fill_config.xlsx" and "zhengce" not in candidate.name:
                return candidate
        return None

    xlsx = _data_xlsx(month_dir) or _data_xlsx(root)
    if xlsx is None or not xlsx.is_file():
        return None
    df = pd.read_excel(xlsx, engine="openpyxl").iloc[start_row:end_row]
    target_col = "invoicing_count" if model_key == "bingo" else "销量"
    if target_col not in df.columns:
        return None
    return float(pd.to_numeric(df[target_col], errors="coerce").sum())


@st.cache_data(show_spinner=False)
def predict_month(
    data_dir_str: str, model_key: str, year: int, month: int, script_md5: str
) -> list[float]:
    """调用某车型自己的 predict_*.py 的 predict_month(year, month)，返回每日预测值。

    script_md5 只作缓存键（脚本内容变了缓存自动失效）。
    """
    cfg = MODELS[model_key]
    root = Path(data_dir_str) / cfg["folder"]
    script_path = root / cfg["script"]
    namespace, _ = load_predict_namespace(script_path)

    cwd = os.getcwd()
    os.chdir(root)  # 脚本内部用相对路径读 ./fill_config.xlsx、./YYYY_MM/...
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            preds = namespace["predict_month"](year, month)
    finally:
        os.chdir(cwd)
    arr = np.asarray(preds, dtype=float).reshape(-1)
    return arr.tolist()


# ============================ 侧边栏 ============================
st.sidebar.header("数据与筛选")
# 部署到 Streamlit Cloud 时把 4 个车型文件夹放到仓库的 data/ 下；
# 本地开发仍用 D 盘路径（也可用环境变量 DATA_DIR 指定）
if os.environ.get("DATA_DIR"):
    default_data_dir = os.environ["DATA_DIR"]
elif Path("./data").exists():
    default_data_dir = "./data"
else:
    default_data_dir = r"D:\app\新建文件夹 (4)\新建文件夹 (6)"
with st.sidebar.expander("数据根目录（一般不用改）"):
    data_dir_str = st.text_input("数据根目录", value=default_data_dir)

model_key = st.sidebar.selectbox("选择车型", options=list(MODELS.keys()))
avail_months = scan_months(data_dir_str, model_key)
years = sorted({y for y, _ in avail_months})
if not years:
    st.error(
        f"在 {data_dir_str}\\{MODELS[model_key]['folder']} 下没有找到月度模型文件夹，"
        "请检查数据根目录是否正确。"
    )
    st.stop()
year = st.sidebar.selectbox("选择年份", options=years)
month = st.sidebar.selectbox(
    "选择月份", options=sorted(m for y, m in avail_months if y == year), format_func=lambda m: f"{m}月"
)


# ============================ 主区域 ============================
if not avail_months:
    st.stop()

script_path = Path(data_dir_str) / MODELS[model_key]["folder"] / MODELS[model_key]["script"]
if not script_path.is_file():
    st.error(f"未找到预测脚本 {script_path}，无法预测。")
    st.stop()

# 预测 + 元数据（预测脚本里已含真实环境的特征处理）
preds = predict_month(data_dir_str, model_key, year, month, script_path.stat().st_mtime_ns)
dates, actual, (start_row, end_row) = month_meta(
    data_dir_str, model_key, year, month, script_path.stat().st_mtime_ns
)

if not dates or len(preds) != len(dates):
    st.error(f"预测长度({len(preds)})与日期数({len(dates)})不一致，月份行区间 {start_row}:{end_row}。")
    st.stop()

df_day = pd.DataFrame({"日期": dates, "预测销量": np.round(preds, 1)})
if actual is not None:
    df_day["真实销量"] = actual

total = float(np.sum(preds))
avg = float(np.mean(preds))
has_actual = actual is not None
actual_total = float(np.nansum(np.asarray(actual, dtype=float))) if has_actual else None

st.subheader(f"{model_key} · {year} 年 {month} 月")
m1, m2, m3, m4 = st.columns(4)
if has_actual:
    diff = total - actual_total
    diff_pct = diff / actual_total * 100 if actual_total else float("nan")
    m1.metric("预测总量", f"{total:,.0f}", delta=f"偏差 {diff:+,.0f}（{diff_pct:+.1f}%）")
    m2.metric("实际总量", f"{actual_total:,.0f}")
else:
    m1.metric("预测总量", f"{total:,.0f}")
    m2.metric("实际总量", "—")
m3.metric("日均预测", f"{avg:,.1f}")
m4.metric("天数", f"{len(preds)} 天")

import altair as alt

base = alt.Chart(df_day).encode(x=alt.X("日期:N", sort=None, title=None))
bar = base.mark_bar(color="#2E6BE6", size=max(6, 340 // max(len(df_day), 1))).encode(
    y=alt.Y("预测销量:Q", title="日销量"), tooltip=list(df_day.columns)
)
charts = bar
if has_actual:
    line = base.mark_line(color="#E4572E", point=True, strokeWidth=2).encode(
        y=alt.Y("真实销量:Q", title="日销量")
    )
    charts = charts + line
st.altair_chart(charts.properties(height=430), use_container_width=True)

with st.expander("查看日度明细"):
    st.dataframe(df_day, use_container_width=True)

# ============================ 全年各月对比 ============================
st.divider()
st.subheader(f"{year} 年各月总量：预测 vs 实际")
month_options = sorted(m for y, m in avail_months if y == year)
rows = []
with st.spinner("正在逐月预测..."):
    for m in month_options:
        pm = predict_month(data_dir_str, model_key, year, m, script_path.stat().st_mtime_ns)
        rows.append({"月份": f"{m}月", "类别": "预测", "总量": round(float(np.sum(pm)), 1)})
        at = actual_month_total(data_dir_str, model_key, year, m)
        if at is not None:
            rows.append({"月份": f"{m}月", "类别": "实际", "总量": round(at, 1)})
df_long = pd.DataFrame(rows)
# altair 4（线上环境）没有 xOffset 分组柱状图，把“月份·类别”合成一个类目轴，实现真正的蓝橙并列
df_long["标签"] = df_long["月份"] + "·" + df_long["类别"]
label_order = [lb for lb in (f"{m}月·{c}" for m in month_options for c in ("预测", "实际")) if lb in set(df_long["标签"])]
color_scale = alt.Scale(domain=["预测", "实际"], range=["#2E6BE6", "#E4572E"])
month_chart = (
    alt.Chart(df_long)
    .mark_bar(size=30)
    .encode(
        x=alt.X(
            "标签:N", sort=label_order, title=None,
            axis=alt.Axis(labelAngle=45, labelFontSize=11),
        ),
        y=alt.Y("总量:Q", title="月总量"),
        color=alt.Color("类别:N", scale=color_scale, legend=None),
        tooltip=["月份", "类别", "总量"],
    )
    .properties(height=350)
)
st.altair_chart(month_chart, use_container_width=True)
