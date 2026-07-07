"""内联 SVG 图标常量（关键位置替代 emoji，保证跨平台一致）."""

_ICON_BACK = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M19 12H5M12 19l-7-7 7-7'/></svg>"
_ICON_HEART = "<svg class='icon-svg' viewBox='0 0 24 24' fill='currentColor'><path d='M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z'/></svg>"
_ICON_CAMERA = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><rect x='3' y='6' width='18' height='12' rx='2'/><circle cx='12' cy='13' r='3'/><path d='M8 6h8l-1-2h-6l-1 2z'/></svg>"
_ICON_HOME = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'/></svg>"
_ICON_SPEAKER = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><path d='M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14'/></svg>"
_ICON_HISTORY = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M3 7h18M3 12h18M3 17h18'/></svg>"
_ICON_PROFILE = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='12' cy='8' r='4'/><path d='M4 20c0-4 4-6 8-6s8 2 8 6'/></svg>"
_ICON_CHECK = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polyline points='20 6 9 17 4 12'/></svg>"
_ICON_REFRESH = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M23 4v6h-6M1 20v-6h6'/><path d='M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15'/></svg>"
_ICON_SHARE = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='18' cy='5' r='3'/><circle cx='6' cy='12' r='3'/><circle cx='18' cy='19' r='3'/><path d='M8.59 13.51l6.83 3.98M8.59 10.49l6.83-3.98'/></svg>"
_ICON_EMPTY = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M22 12h-6l-2 3h-4l-2-3H2'/><path d='M5.55 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.55-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.69.11z'/></svg>"
_ICON_FOOD = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M6 8a6 6 0 0 1 12 0c0 7-3 9-3 9H9s-3-2-3-9zm4.5 0V5a2.5 2.5 0 0 1 5 0v3'/><line x1='3' y1='21' x2='21' y2='21'/></svg>"
# 用于嵌入 JS 字符串的 SVG（单引号已转义）
_ICON_SPEAKER_JS = _ICON_SPEAKER.replace("'", "\\'")
_ICON_MUTE_JS = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><line x1='23' y1='9' x2='17' y2='15'/><line x1='17' y1='9' x2='23' y2='15'/></svg>".replace("'", "\\'")
