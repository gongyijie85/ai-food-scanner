"""数据仓库适配器（Repository Adapters）.

把本地静态数据文件（CSV/JSON）封装成可替换的接口，业务层不感知数据源细节。
"""

from repositories.additive_risk import (
    AdditiveRisk,
    AdditiveRiskRepository,
    CsvAdditiveRiskRepository,
)

__all__ = [
    "AdditiveRisk",
    "AdditiveRiskRepository",
    "CsvAdditiveRiskRepository",
]
