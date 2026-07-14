"""数据仓库适配器（Repository Adapters）.

把本地静态数据文件（CSV/JSON/SQLite）封装成可直接使用的仓库对象。
"""

from repositories.additive_risk import (
    AdditiveRisk,
    CsvAdditiveRiskRepository,
    SqliteAdditiveRepository,
    StandardAdditive,
)

__all__ = [
    "AdditiveRisk",
    "CsvAdditiveRiskRepository",
    "SqliteAdditiveRepository",
    "StandardAdditive",
]
