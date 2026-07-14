"""添加剂分类服务：把模型识别的添加剂名称映射为风险等级."""

import csv
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

from repositories.additive_risk import (
    AdditiveRisk,
    CsvAdditiveRiskRepository,
    SqliteAdditiveRepository,
    StandardAdditive,
)

# 不应被识别为食品添加剂的基础配料黑名单（避免 AI 误判导致分数虚低）
ADDITIVE_BLOCKLIST = {
    "水",
    "饮用水",
    "纯净水",
    "蒸馏水",
    "矿泉水",
    "白砂糖",
    "白糖",
    "冰糖",
    "红糖",
    "绵白糖",
    "蔗糖",
    "食用盐",
    "食盐",
    "精盐",
    "海盐",
    "岩盐",
    "食用油",
    "植物油",
    "菜籽油",
    "花生油",
    "大豆油",
    "玉米油",
    "葵花籽油",
    "橄榄油",
    "棕榈油",
    "调和油",
    "面粉",
    "小麦粉",
    "大米",
    "糯米粉",
    "淀粉",
    "小麦淀粉",
    "玉米淀粉",
    "马铃薯淀粉",
    "食品用香精",
    "食用香精",
    "香精",
    "酵母",
    "酵母抽提物",
    "蜂蜜",
    "麦芽糖浆",
    "果葡糖浆",
    "葡萄糖浆",
    "乳糖",
}

# 保健品辅料白名单（不参与扣分）
SUPPLEMENT_EXCIPIENTS = {
    "鱼油",
    "明胶",
    "甘油",
    "蜂蜡",
    "卵磷脂",
    "淀粉",
    "麦芽糊精",
    "羧甲基纤维素钠",
}

# 去除括号及其内部内容（如 E202、INS 编号等补充说明）
_PARENTHESES_RE = re.compile(r"[（(].*?[）)]")

# 默认同义词表路径（用于补充 SQLite 别名表）
_DEFAULT_SYNONYMS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "additive_synonyms.csv"
)


class MatchStatus(Enum):
    """添加剂匹配状态."""

    RATED = "rated"  # 已确定风险等级（标准收录且覆盖表已评级 / 规则兜底 A 级）
    PENDING_RATING = "pending_rating"  # 标准已收录，但覆盖表暂无评级
    UNMATCHED = "unmatched"  # 标准库未匹配


@dataclass(frozen=True)
class AdditiveMatchResult:
    """单一添加剂的完整匹配结果."""

    raw_name: str  # 原始输入名称
    canonical_name: str  # 解析后的标准名或最佳名称
    status: MatchStatus  # 匹配状态
    cns: str  # 中国编号（CNS）
    ins: str  # 国际编号（INS）
    function: str  # 功能类别
    scopes_summary: str  # 使用范围摘要
    level: str  # 风险等级 A/B/C（空字符串表示待评级）
    note: str  # 说明文字
    page_ref: str  # 标准页码引用


def _clean_name(name) -> str:
    """清洗名称：去空白、去首尾标点."""
    if not isinstance(name, str):
        name = str(name)
    return name.strip().strip("，,、.;；")


def _strip_parentheses(name: str) -> str:
    """去掉括号及其内部内容，用于处理 E202/INS 残留."""
    return _PARENTHESES_RE.sub("", name).strip()


def _is_blocklisted(name: str) -> bool:
    """判断名称是否为基础配料黑名单."""
    n = _clean_name(name)
    if not n:
        return True
    return n in ADDITIVE_BLOCKLIST


def is_supplement_excipient(name: str) -> bool:
    """判断是否为保健品辅料."""
    n = str(name).strip()
    return n in SUPPLEMENT_EXCIPIENTS or any(k in n for k in ["胶囊壳", "软胶囊"])


def _load_synonyms(path: str) -> Dict[str, str]:
    """加载 additive_synonyms.csv，返回 alias -> canonical 映射."""
    synonyms: Dict[str, str] = {}
    if not os.path.exists(path):
        return synonyms
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                alias = row.get("synonym", "").strip()
                canonical = row.get("canonical_name", "").strip()
                if alias and canonical:
                    synonyms[alias] = canonical
    except FileNotFoundError:
        pass
    return synonyms


class AdditiveMatcher:
    """添加剂分类器：结合 GB 2760 标准库、应用覆盖表和业务规则判定等级."""

    def __init__(
        self,
        standard_repo: SqliteAdditiveRepository,
        override_repo: CsvAdditiveRiskRepository,
        synonyms_path: Optional[str] = None,
    ):
        self.standard_repo = standard_repo
        self.override_repo = override_repo
        self._synonyms = _load_synonyms(synonyms_path or _DEFAULT_SYNONYMS_PATH)

    def _resolve_alias(self, name: str) -> Optional[str]:
        """先查 SQLite 别名表，再查本地同义词表."""
        canonical = self.standard_repo.find_alias(name)
        if canonical:
            return canonical
        return self._synonyms.get(name)

    def _find_standard(self, name: str) -> Optional[StandardAdditive]:
        """按名称精确查询标准库."""
        return self.standard_repo.find_standard(name)

    def _resolve_canonical_and_standard(
        self, name: str
    ) -> Tuple[str, Optional[StandardAdditive]]:
        """把输入名称解析成 (canonical_name, standard_record).

        解析顺序：标准名精确 -> 别名 -> 去括号后标准名 -> 去括号后别名.
        """
        clean = _clean_name(name)
        # 1. 标准名精确匹配
        standard = self._find_standard(clean)
        if standard is not None:
            return standard.canonical_name, standard

        # 2. 显式别名匹配
        alias = self._resolve_alias(clean)
        if alias:
            standard = self._find_standard(alias)
            return alias, standard

        # 3. 去括号/INS 残留后精确匹配
        cleaned_no_paren = _strip_parentheses(clean)
        if cleaned_no_paren and cleaned_no_paren != clean:
            standard = self._find_standard(cleaned_no_paren)
            if standard is not None:
                return standard.canonical_name, standard
            alias = self._resolve_alias(cleaned_no_paren)
            if alias:
                standard = self._find_standard(alias)
                return alias, standard

        return clean, None

    def match(self, name) -> AdditiveMatchResult:
        """返回 AdditiveMatchResult，包含风险等级和匹配状态."""
        raw_name = name if isinstance(name, str) else str(name)
        clean = _clean_name(raw_name)

        # 空名称保持与旧 classify 一致，返回 B 兜底
        if not clean:
            return AdditiveMatchResult(
                raw_name=raw_name,
                canonical_name=raw_name,
                status=MatchStatus.UNMATCHED,
                cns="",
                ins="",
                function="",
                scopes_summary="",
                level="B",
                note="名称待核对（未在 GB 2760 标准库中命中）",
                page_ref="",
            )

        # 1. 黑名单基础配料 -> A 级
        if _is_blocklisted(clean):
            return AdditiveMatchResult(
                raw_name=raw_name,
                canonical_name=clean,
                status=MatchStatus.RATED,
                cns="",
                ins="",
                function="",
                scopes_summary="",
                level="A",
                note="基础配料，不扣分",
                page_ref="",
            )

        # 2. 保健品辅料 -> A 级
        if is_supplement_excipient(clean):
            return AdditiveMatchResult(
                raw_name=raw_name,
                canonical_name=clean,
                status=MatchStatus.RATED,
                cns="",
                ins="",
                function="",
                scopes_summary="",
                level="A",
                note="保健品辅料，不扣分",
                page_ref="",
            )

        # 3-5. 解析标准名或别名
        canonical, standard = self._resolve_canonical_and_standard(raw_name)

        if standard is not None:
            # 标准已收录，查覆盖表确定等级
            override = self.override_repo.find(canonical)
            if override is not None:
                return AdditiveMatchResult(
                    raw_name=raw_name,
                    canonical_name=canonical,
                    status=MatchStatus.RATED,
                    cns=standard.cns,
                    ins=standard.ins,
                    function=standard.functions,
                    scopes_summary=standard.scopes_summary,
                    level=override.level,
                    note=override.note,
                    page_ref=standard.page_ref,
                )
            return AdditiveMatchResult(
                raw_name=raw_name,
                canonical_name=canonical,
                status=MatchStatus.PENDING_RATING,
                cns=standard.cns,
                ins=standard.ins,
                function=standard.functions,
                scopes_summary=standard.scopes_summary,
                level="B",  # 兼容旧接口：待评级按保守 B 返回
                note="标准已收录，应用待评级",
                page_ref=standard.page_ref,
            )

        # 标准库未命中：尝试覆盖表兜底（兼容 TBHQ 等 CSV 中已评级条目）
        override = self.override_repo.find(clean) or self.override_repo.find(canonical)
        if override is not None:
            return AdditiveMatchResult(
                raw_name=raw_name,
                canonical_name=canonical if canonical != clean else clean,
                status=MatchStatus.RATED,
                cns="",
                ins="",
                function="",
                scopes_summary="",
                level=override.level,
                note=override.note,
                page_ref="",
            )

        # 6. 完全未命中 -> B 级
        return AdditiveMatchResult(
            raw_name=raw_name,
            canonical_name=raw_name,
            status=MatchStatus.UNMATCHED,
            cns="",
            ins="",
            function="",
            scopes_summary="",
            level="B",
            note="名称待核对（未在 GB 2760 标准库中命中）",
            page_ref="",
        )

    def classify(self, name) -> Tuple[str, str, str]:
        """返回 (level, ins_no, note)，保留以兼容旧调用方.

        内部调用 match()，level 为空时按保守策略返回 B.
        """
        result = self.match(name)
        level = result.level
        return level, result.ins, result.note
