"""项目级常量，供 app.py 与各页面模块共享.

避免页面模块直接依赖 app.py（streamlit run 时 app.py 作为 __main__
运行，直接 from app import 可能触发重复加载），因此把项目根目录、
健康档案疾病选项、引导页人群选项等常量集中到此模块。
"""

import os

# 项目根目录，避免多处重复计算
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 六大人群选项（引导页默认疾病选择）
HEALTH_GROUPS = ["糖尿病", "高血压", "脑梗/心血管", "减脂", "过敏", "孕妇/儿童"]

# 健康档案疾病选项（模块级常量，避免每次渲染重复构造）
CONDITION_ITEMS = [
    ("diabetes", "糖尿病", "糖"),
    ("hypertension", "高血压", "压"),
    ("stroke", "脑梗/心血管", "脑"),
    ("fat-loss", "减脂", "减"),
    ("allergy", "过敏", "敏"),
    ("children", "儿童", "儿"),
    ("pregnant", "孕妇", "孕"),
]
CONDITION_NAME_MAP = {k: v for k, v, _ in CONDITION_ITEMS}
