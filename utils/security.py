"""安全工具函数。"""
import html


def _safe(text: str) -> str:
    """对动态文本做 HTML 转义，防止 XSS."""
    return html.escape(str(text), quote=True)
