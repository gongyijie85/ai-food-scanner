"""本地数据加载工具（GB 2760、健康档案、Markdown 文档）。"""

import json
import os

import streamlit as st

from repositories.additive_risk import (
    CsvAdditiveRiskRepository,
    SqliteAdditiveRepository,
)

# 项目根目录
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")

_GB2760_DB_PATH = os.path.join(_DATA_DIR, "gb2760_2024.sqlite")
_GB2760_RISK_PATH = os.path.join(_DATA_DIR, "gb2760_risk.csv")
_DISEASES_PATH = os.path.join(_DATA_DIR, "common_diseases.json")
_ALLERGENS_PATH = os.path.join(_DATA_DIR, "allergens.json")
_DRUGS_PATH = os.path.join(_DATA_DIR, "common_drugs.json")
_CONFLICTS_PATH = os.path.join(_DATA_DIR, "drug_food_conflicts.json")


def _load_json(path):
    """读取 JSON 文件，失败返回空 dict."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


@st.cache_data(ttl=300)
def _load_markdown(path):
    """读取 Markdown 文件，失败返回提示文本."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "文件暂未找到，请稍后刷新页面重试。"


@st.cache_resource
def load_health_data():
    """加载所有健康档案数据（疾病/过敏原/药物/冲突），缓存一次."""
    return {
        "diseases": _load_json(_DISEASES_PATH).get("categories", []),
        "allergens": _load_json(_ALLERGENS_PATH).get("categories", []),
        "drugs": _load_json(_DRUGS_PATH).get("categories", []),
        "conflicts": _load_json(_CONFLICTS_PATH).get("conflicts", []),
    }


@st.cache_resource
def get_additive_risk_repository():
    """返回 GB 2760 标准库仓库实例（只读 SQLite，带 Streamlit 缓存）."""
    return SqliteAdditiveRepository(_GB2760_DB_PATH)


@st.cache_resource
def get_additive_override_repository():
    """返回应用自定义风险覆盖表仓库实例（CSV，带 Streamlit 缓存）."""
    return CsvAdditiveRiskRepository(_GB2760_RISK_PATH)


@st.cache_resource
def load_gb2760_risk():
    """加载 GB 2760 添加剂风险覆盖表，返回 dict[中文名] -> {level, warnings, note}.

    保留此函数以兼容现有调用方；数据来自应用自定义覆盖表，不再包含 ADI。
    """
    repo = get_additive_override_repository()
    return {
        name: {
            "level": risk.level,
            "warnings": risk.warnings,
            "note": risk.note,
        }
        for name, risk in repo._data.items()
    }
