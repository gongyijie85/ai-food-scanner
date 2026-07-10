"""GB 2760 食品添加剂风险数据仓库适配器."""

import csv
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AdditiveRisk:
    """单一食品添加剂的风险信息.

    Attributes:
        level: 风险等级 A/B/C
        adi: 每日允许摄入量
        warnings: 特定人群警告，多个用"/"分隔
        note: 功能类别说明
    """

    level: str
    adi: str
    warnings: str
    note: str


class AdditiveRiskRepository(ABC):
    """添加剂风险数据仓库接口.

    实现可以是 CSV 本地文件、数据库、远程 API 等。
    调用方只依赖此接口，不依赖具体数据源。
    """

    @abstractmethod
    def find(self, name: str) -> Optional[AdditiveRisk]:
        """根据添加剂名称查找风险信息.

        实现应处理精确匹配、清洗后匹配和必要的模糊匹配。
        返回 None 表示库中无此添加剂。
        """
        ...


class CsvAdditiveRiskRepository(AdditiveRiskRepository):
    """基于 CSV 文件的 GB 2760 风险库实现."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._data: Dict[str, AdditiveRisk] = {}
        self._load()

    def _load(self):
        """从 CSV 加载全部风险数据."""
        try:
            with open(self.csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = row.get("cn_name", "").strip()
                    if not key:
                        continue
                    self._data[key] = AdditiveRisk(
                        level=row.get("risk_level", "B").strip() or "B",
                        adi=row.get("adi_value", "").strip(),
                        warnings=row.get("health_warnings", "").strip(),
                        note=row.get("note", "").strip(),
                    )
        except FileNotFoundError:
            # CSV 缺失时保持空库，避免启动崩溃
            pass

    def _normalize(self, name: str) -> str:
        """统一名称格式：去除括号、空格、INS 号残留."""
        # 先去掉括号及其内部内容（如 E202、INS202）
        s = re.sub(r"[(（][^）)]*[）)]", "", name)
        # 再去掉剩余空格和常见括号
        s = re.sub(r"[\s()（）\[\]【】]", "", s)
        return s.strip()

    def find(self, name: str) -> Optional[AdditiveRisk]:
        """按名称查找，依次尝试精确匹配、清洗后匹配、模糊匹配."""
        n = name.strip()
        if not n:
            return None

        # 1) 精确匹配
        if n in self._data:
            return self._data[n]

        # 2) 清洗后匹配
        n_clean = self._normalize(n)
        if not n_clean:
            return None
        for k, v in self._data.items():
            if self._normalize(k) == n_clean:
                return v

        # 3) 模糊匹配：长度相近，避免"山梨糖醇"误匹配"山梨糖醇酐单硬脂酸酯"
        for k, v in self._data.items():
            if abs(len(k) - len(n)) > 2:
                continue
            if k in n or n in k:
                return v

        return None
