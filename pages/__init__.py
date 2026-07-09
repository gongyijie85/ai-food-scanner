"""页面渲染模块统一入口.

将 app.py 中的页面渲染函数按页面拆分到独立子模块，避免 app.py 过度膨胀。
"""

from pages.history import render_detail_page, render_history_page
from pages.home import render_home_page
from pages.legal import render_legal_consent, render_legal_pp, render_legal_ua
from pages.onboarding import render_onboarding
from pages.profile import render_health_profile, render_health_profile_page
from pages.result import render_food_page, render_result_page, render_supplement_page
from pages.scan import render_scan_page

__all__ = [
    "render_detail_page",
    "render_history_page",
    "render_home_page",
    "render_legal_consent",
    "render_legal_pp",
    "render_legal_ua",
    "render_onboarding",
    "render_health_profile",
    "render_health_profile_page",
    "render_food_page",
    "render_result_page",
    "render_supplement_page",
    "render_scan_page",
]
