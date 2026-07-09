"""内联 SVG 图标常量（关键位置替代 emoji，保证跨平台一致）.

只保留实际被使用的图标：
- _ICON_CAMERA  扫描页标题、相机入口
- _ICON_EMPTY   空状态默认图标
- _ICON_ALERT   错误状态警告图标
- _ICON_SPEAKER / _ICON_SPEAKER_JS / _ICON_MUTE_JS  语音播报按钮
"""

# 相机图标（扫描页标题、相机入口）
_ICON_CAMERA = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><rect x='3' y='6' width='18' height='12' rx='2'/><circle cx='12' cy='13' r='3'/><path d='M8 6h8l-1-2h-6l-1 2z'/></svg>"
# 喇叭图标（语音播报按钮）
_ICON_SPEAKER = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><path d='M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14'/></svg>"
# 空盒子图标（空状态默认）
_ICON_EMPTY = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M22 12h-6l-2 3h-4l-2-3H2'/><path d='M5.55 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.55-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.69.11z'/></svg>"
# 警告图标（错误状态）
_ICON_ALERT = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z'/><line x1='12' y1='9' x2='12' y2='13'/><line x1='12' y1='17' x2='12.01' y2='17'/></svg>"
# 用于嵌入 JS 字符串的 SVG（单引号已转义）
_ICON_SPEAKER_JS = _ICON_SPEAKER.replace("'", "\\'")
_ICON_MUTE_JS = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><line x1='23' y1='9' x2='17' y2='15'/><line x1='17' y1='9' x2='23' y2='15'/></svg>".replace(
    "'", "\\'"
)
