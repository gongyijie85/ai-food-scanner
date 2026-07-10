"""业务服务层（Business Services）.

把领域规则（添加剂匹配、健康风险提示）封装成可独立测试的深度模块。
"""

from services.additive_matcher import AdditiveMatcher
from services.health_warning_engine import HealthWarning, HealthWarningEngine

__all__ = [
    "AdditiveMatcher",
    "HealthWarning",
    "HealthWarningEngine",
]
