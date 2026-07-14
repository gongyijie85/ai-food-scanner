"""GB 2760 食品添加剂数据仓库适配器.

- SqliteAdditiveRepository: 只读查询 GB 2760 标准库（法规事实）。
- CsvAdditiveRiskRepository: 读取应用自定义风险覆盖表（A/B/C 等级 + 健康提醒）。
"""

import csv
import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AdditiveRisk:
    """应用自定义风险覆盖表中的单一添加剂风险信息.

    Attributes:
        level: 风险等级 A/B/C
        warnings: 特定人群警告，多个用"/"分隔
        note: 功能类别说明
    """

    level: str
    warnings: str
    note: str


@dataclass(frozen=True)
class StandardAdditive:
    """GB 2760 标准库中的单一添加剂法规事实.

    Attributes:
        canonical_name: 标准中文名
        cns: 中国编号（CNS）
        ins: 国际编号（INS）
        functions: 功能类别
        scopes_summary: 使用范围摘要（前 5 条）
        page_ref: 标准页码引用
    """

    canonical_name: str
    cns: str
    ins: str
    functions: str
    scopes_summary: str
    page_ref: str


class SqliteAdditiveRepository:
    """基于 SQLite 的 GB 2760 标准库只读查询."""

    def __init__(self, db_path: str):
        """以只读模式打开标准库数据库.

        Args:
            db_path: SQLite 数据库文件路径（支持相对路径）
        """
        self.db_path = db_path
        # URI 模式开启只读，避免误写标准库
        self._conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    def _scopes_summary(self, additive_id: int) -> str:
        """取该添加剂前 5 条使用范围，格式化为 'code name max_usage'。"""
        cur = self._conn.execute(
            """
            SELECT food_category_code, food_category_name, max_usage
            FROM additive_usage_scopes
            WHERE additive_id = ?
            LIMIT 5
            """,
            (additive_id,),
        )
        parts = []
        for code, name, usage in cur:
            code = code or ""
            name = name or ""
            usage = usage or ""
            parts.append(f"{code} {name} {usage}".strip())
        return "；".join(parts)

    def find_standard(self, name: str) -> Optional[StandardAdditive]:
        """按标准名精确查询，返回标准添加剂信息."""
        row = self._conn.execute(
            """
            SELECT id, canonical_name, cns, ins, functions, note, pdf_page, print_page
            FROM additives
            WHERE canonical_name = ?
            """,
            (name.strip(),),
        ).fetchone()
        if not row:
            return None
        (
            additive_id,
            canonical_name,
            cns,
            ins,
            functions,
            note,
            pdf_page,
            print_page,
        ) = row
        # 优先用印刷页码，没有则回退 PDF 页码
        page_ref = str(print_page) if print_page else (str(pdf_page) if pdf_page else "")
        return StandardAdditive(
            canonical_name=canonical_name or "",
            cns=cns or "",
            ins=ins or "",
            functions=functions or "",
            scopes_summary=self._scopes_summary(additive_id),
            page_ref=page_ref,
        )

    def find_alias(self, alias: str) -> Optional[str]:
        """查询 additive_aliases 表，返回对应标准名."""
        row = self._conn.execute(
            "SELECT canonical_name FROM additive_aliases WHERE alias = ?",
            (alias.strip(),),
        ).fetchone()
        return row[0] if row else None

    def list_aliases(self) -> Dict[str, str]:
        """返回全部 alias -> canonical 映射字典."""
        cur = self._conn.execute(
            "SELECT alias, canonical_name FROM additive_aliases"
        )
        return {
            alias: canonical for alias, canonical in cur if alias and canonical
        }


class CsvAdditiveRiskRepository:
    """基于 CSV 的应用自定义风险覆盖表.

    该 CSV 只表达应用层自定义的 A/B/C 风险等级和健康提醒，
    不再冒充完整的 GB 2760 标准库。法规事实请查询 SqliteAdditiveRepository。
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._data: Dict[str, AdditiveRisk] = {}
        self._load()

    def _load(self):
        """从 CSV 加载风险覆盖数据."""
        if not os.path.exists(self.csv_path):
            return
        try:
            with open(self.csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = row.get("cn_name", "").strip()
                    if not key:
                        continue
                    self._data[key] = AdditiveRisk(
                        level=row.get("risk_level", "B").strip() or "B",
                        warnings=row.get("health_warnings", "").strip(),
                        note=row.get("note", "").strip(),
                    )
        except FileNotFoundError:
            # CSV 缺失时保持空库，避免启动崩溃
            pass

    def find(self, name: str) -> Optional[AdditiveRisk]:
        """按名称精确查找风险覆盖."""
        n = name.strip() if isinstance(name, str) else ""
        if not n:
            return None
        return self._data.get(n)
