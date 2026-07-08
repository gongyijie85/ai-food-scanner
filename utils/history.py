"""历史记录本地 JSON 持久化工具。"""
import json
import os
from datetime import datetime

import streamlit as st

from utils.data import _DATA_DIR

# 历史记录本地文件路径
_HISTORY_PATH = os.path.join(_DATA_DIR, "history.json")
# 最多保留最近 50 条（超出自动删除最旧的）
_HISTORY_MAX = 50

# 完整历史快照路径与上限
_HISTORY_FULL_PATH = os.path.join(_DATA_DIR, "history_full.json")
_HISTORY_FULL_MAX = 20


@st.cache_data(ttl=300)
def load_history():
    """读取本地历史记录 JSON，返回 list[dict].

    文件不存在或损坏时返回空列表，不抛异常（初赛版本：刷新不丢失）。
    每条记录字段：timestamp, product_name, score, type(food/supplement), additives_count。
    """
    try:
        with open(_HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_history(record):
    """追加一条历史记录到本地 JSON 文件，并保留最近 50 条.

    record: dict，至少包含 timestamp/product_name/score/type/additives_count。
    异常时静默忽略（写入失败不阻断识别主流程）。
    """
    try:
        history = load_history()
        history.insert(0, record)
        history = history[:_HISTORY_MAX]  # 截断到最近 50 条
        os.makedirs(_DATA_DIR, exist_ok=True)  # 兜底确保 data 目录存在
        with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        # 写入后清除缓存，确保展示侧立即刷新
        load_history.clear()
    except OSError:
        # 写入失败不阻断主流程
        pass


@st.cache_data(ttl=300)
def load_history_full():
    """读取完整历史快照."""
    try:
        with open(_HISTORY_FULL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_history_full(result):
    """保存完整识别结果快照，最多 _HISTORY_FULL_MAX 条."""
    try:
        history = load_history_full()
        history.insert(0, result)
        history = history[:_HISTORY_FULL_MAX]
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_HISTORY_FULL_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        load_history_full.clear()
    except OSError:
        pass


def add_history(result, default_engine="未知"):
    """识别成功后保存一条历史记录（Phase 4 起改为本地 JSON 持久化，刷新不丢失）.

    不保存图片数据（隐私保护，已在 Phase 0 确认）。
    """
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "product_name": result.get("product_name", "未知"),
        "score": result.get("score", 0),
        "type": str(result.get("type", "food")),
        "additives_count": len(result.get("additives", [])),
        "engine": result.get("engine", default_engine),
    }
    save_history(record)
    # 保存完整识别快照供详情页使用
    save_history_full(result)


def show_history(switch_page_func, safe_func, max_items: int = 3):
    """在侧边栏展示最近 N 条历史记录（调用时需已在 sidebar 上下文内）.

    每条记录整行可点击，跳转详情页；完整历史记录请前往独立历史页面查看。
    """
    st.header("历史记录")
    history = load_history()
    if not history:
        st.caption("暂无记录")
        return
    for idx, item in enumerate(history[:max_items]):
        score = item.get("score", 0)
        status = "safe" if score >= 80 else ("caution" if score >= 60 else "danger")
        # 简短时间显示（YYYY-MM-DD HH:MM），适老化不显示秒
        ts = item.get("timestamp", "")
        time_str = ts[:16].replace("T", " ") if ts else ""
        # 类型标签：保健食品 / 食品
        type_tag = "保健食品" if item.get("type") == "supplement" else "食品"
        name = safe_func(item.get("product_name", "未知"))
        label = f"{name} [{type_tag}]\n{score}分 · {item.get('additives_count', 0)}种添加剂 · {time_str}"
        # 用 marker 给样式提供状态色，整行按钮点击查看详情
        st.markdown(
            f"<div class='sidebar-history-row-marker {status}'></div>",
            unsafe_allow_html=True,
        )
        if st.button(label, key=f"sb_history_{idx}", help="查看详情"):
            st.session_state["selected_history_index"] = idx
            st.session_state["detail_fallback_record"] = item
            switch_page_func("detail")
    if len(history) > max_items:
        if st.button("查看全部历史记录", width="stretch", key="sb_view_all_history"):
            switch_page_func("history")
