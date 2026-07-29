"""用户纠错反馈本地持久化工具."""

import json
import os
from datetime import datetime

from utils.data import _DATA_DIR

_FEEDBACK_MAX = 200


def _feedback_path() -> str:
    return os.path.join(_DATA_DIR, "feedback.json")


def load_feedback():
    """读取本地反馈记录 JSON，返回 list[dict].

    文件不存在或损坏时返回空列表，不抛异常。
    """
    try:
        with open(_feedback_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_feedback(product_name: str, message: str) -> bool:
    """保存一条用户纠错反馈.

    message 为空白时视为无效提交，返回 False 且不写入。
    写入失败（如磁盘异常）时静默返回 False，不阻断主流程。
    """
    message = (message or "").strip()
    if not message:
        return False
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "product_name": product_name or "未知",
        "message": message,
    }
    try:
        history = load_feedback()
        history = [record] + history
        history = history[:_FEEDBACK_MAX]
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_feedback_path(), "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
