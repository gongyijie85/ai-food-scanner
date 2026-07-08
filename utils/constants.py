"""项目级常量，供 app.py 与各页面模块共享.

避免页面模块直接依赖 app.py（streamlit run 时 app.py 作为 __main__
运行，直接 from app import 可能触发重复加载），因此把项目根目录、
健康档案疾病选项、引导页人群选项等常量集中到此模块。
"""

import os

# 项目根目录，避免多处重复计算
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 疾病/人群选项（引导页与健康档案共用）
HEALTH_GROUPS = ["糖尿病", "高血压", "脑梗/心血管", "减脂", "过敏", "儿童", "孕妇"]

# 健康档案疾病选项（模块级常量，避免每次渲染重复构造）
# 第三个字段使用语义化 emoji 小图标，避免与疾病名首字重复
CONDITION_ITEMS = [
    ("diabetes", "糖尿病", "🩺"),
    ("hypertension", "高血压", "🫀"),
    ("stroke", "脑梗/心血管", "🧠"),
    ("fat-loss", "减脂", "🥗"),
    ("allergy", "过敏", "🤧"),
    ("children", "儿童", "🧒"),
    ("pregnant", "孕妇", "🤰"),
]
CONDITION_NAME_MAP = {k: v for k, v, _ in CONDITION_ITEMS}
