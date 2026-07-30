"""Agnes API 模型名称排查。"""

import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

AGNES_KEY = os.getenv("AGNES_API_KEY", "")
# 2026-07-30 核實 https://www.agnes-ai.com/zh-Hans/docs/agnes-25-flash：
# 正确 base URL 是 apihub 子域名（旧的 api.agnes-ai.com 对任何路径都返回
# 404 Resource not found，域名本身就是错的，不是模型名问题）。
AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"

# 尝试多种模型名称变体（确认 agnes-2.5-flash 为准确名称后，其余仅作保留排查）
model_names = [
    "agnes-2.5-flash",
    "Agnes-2.5-Flash",
    "agnes-2.0-flash",
    "agnes-20-flash",
]

headers = {"Authorization": f"Bearer {AGNES_KEY}", "Content-Type": "application/json"}

for model in model_names:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 5,
    }
    try:
        resp = requests.post(AGNES_URL, headers=headers, json=payload, timeout=10)
        status = "OK" if resp.status_code == 200 else f"ERR {resp.status_code}"
        print(f"{model:25s} -> {status}")
    except Exception as e:
        print(f"{model:25s} -> EXC {str(e)[:50]}")
