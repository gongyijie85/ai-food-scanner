# Design kit · 拍了就懂

本目录放 **设计契约、Open Design 提示词、静态 HTML 预览**。  
线上样式仍以 `.streamlit/style.css` 为准；改视觉时先更新 `DESIGN.md`，再同步 CSS / 组件。

## 文件

| 文件 | 用途 |
|------|------|
| [`DESIGN.md`](./DESIGN.md) | 品牌与适老契约（给 Open Design / Agent / 工程师） |
| [`open-design-brief-result.md`](./open-design-brief-result.md) | **可粘贴**进 Open Design 的结果页 brief |
| [`DESIGN-vs-CSS-gap.md`](./DESIGN-vs-CSS-gap.md) | 契约 vs `.streamlit/style.css` 对照与缺口优先级（只读清单） |
| `*_preview.html` / `*_v2*.html` | 历史静态预览（参考，非 source of truth） |
| `demo_assets/` | 演示截图与短视频素材脚本 |
| `colors_and_type.css`（仓库根） | **未注入**线上；勿当 token 源，见 gap G11 |

## 本地直达结果页（验收样式）

```text
http://localhost:8501/?page=result&sample=1&device=mobile
```

- `page=result`：打开结果页  
- `sample=1`（或 `preview=1`）：跳过法律/引导，注入示例配料数据（不调 API）  
- `device=mobile`：强制手机布局 CSS  

若端口被占用，以终端打印的 Local URL 为准（如 8502/8503）。

## 推荐工作流（路线 A）

1. 打开 [Open Design](https://github.com/nexu-io/open-design)（桌面端或 agent MCP）。
2. 绑定 / 粘贴 `DESIGN.md` 为当前 design system。
3. 复制 `open-design-brief-result.md` 中的 **Paste-ready prompt** 生成手机结果页原型。
4. 用验收清单点选；满意后把 token / 顺序 / 文案回灌 Streamlit（见 brief 内 handoff 表）。
5. **不要**把 OD HTML 直接当 Streamlit Cloud 生产前端。

## 下一步（可选）

- 结果页方向冻结后：用 brief 文末「三屏流」做首页 + 扫描 + 结果。
- 工程实施：单独开任务「按 DESIGN.md 升级 score_hero / additive_card / voice CTA」。
