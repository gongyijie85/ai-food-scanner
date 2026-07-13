"""项目级常量，供 app.py 与各页面模块共享.

避免页面模块直接依赖 app.py（streamlit run 时 app.py 作为 __main__
运行，直接 from app import 可能触发重复加载），因此把项目根目录、
健康档案疾病选项、引导页人群选项等常量集中到此模块。
"""

import os

# 项目根目录，避免多处重复计算
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 健康档案疾病选项（模块级常量，避免每次渲染重复构造）
# 第三个字段使用语义化 emoji 小图标，与档案页、引导页保持一致
CONDITION_ITEMS = [
    ("stroke", "脑梗/心血管", "❤️"),
    ("diabetes", "糖尿病", "💉"),
    ("hypertension", "高血压", "🫀"),
    ("gout", "痛风", "🦴"),
    ("lactose", "乳糖不耐", "🍼"),
    ("kidney", "肾病", "🫘"),
]
CONDITION_NAME_MAP = {k: v for k, v, _ in CONDITION_ITEMS}
