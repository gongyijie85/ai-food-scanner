# 验证执行看板

> 更新日期：2026-08-03  
> 地图：[#26](https://github.com/gongyijie85/ai-food-scanner/issues/26)  
> 规格：[#53 扩招与真人证据](https://github.com/gongyijie85/ai-food-scanner/issues/53)  
> 手册：[validation-recruitment-kit.md](validation-recruitment-kit.md)  
> 门槛：[validation-publish-gate.md](validation-publish-gate.md)  
> 记录表：[validation-sample-log.csv](validation-sample-log.csv)  
> 纸质单：[validation-field-sheet.md](validation-field-sheet.md)  
> 校验代码：`utils/validation_evidence.py`

## 状态总览

| 阶段 | 状态 |
|------|------|
| 决策（假设/闸门/冻结/架构/iOS） | ✅ 已完成 |
| 研究（变现/合规/获客） | ✅ 已入库 main |
| 信任止血 A–E（呈现契约/清单/门槛） | ✅ #48–#52 已关 |
| 证据账本接缝（#53） | ✅ 字段 + 校验 + 场次单 |
| 公开链接探活 | ⏳ 扩招前 owner 再测 |
| 招募执行 | ⏳ **待 owner**（有条件允许扩招） |
| 有效子女样本 ≥8 | ⏳ 未开始 |
| Go / Pivot / Stop 判定 | ⏳ 样本达标后 |

## 每波扩招前（5 分钟）

- [ ] G1–G5 仍成立（无分数主结论、无吃/不吃判决、部分识别诚实、历史无分叙事、预检 P0）  
- [ ] G6：本地/Cloud `MIMO_API_KEY` 有效  
- [ ] 用 `default_wechat_invite` 口径发邀（或 kit 话术），禁医疗承诺  
- [ ] 复制 CSV 新 wave 行；纸质场用 field-sheet  

## 本周 checklist（owner）

- [ ] 自己手机完整走通 L2（**不要**用 `?demo=1` 冒充真样本）  
- [ ] 列出 30–50 名可邀请子女  
- [ ] 发出 ≥15 条微信 1v1  
- [ ] 每完成 1 人：脚本 + 写入 CSV（含 recognition_honesty / gate_incident）  
- [ ] 第 5–7 天跟进复扫  
- [ ] 每波结束：评论 #40 附 `summarize` 口径（有效 n / 再用 / 付费信号 / 事故）  

## 链接

- 公开：https://gongyijie85-ai-food-scanner-app-w4mpmt.streamlit.app/  
- 仓库 main：https://github.com/gongyijie85/ai-food-scanner  

## 判定公式（#28，样本≥8 后）

- 再用率 = 再用人数 / 有效样本（再用=口头会再用 **或** 7 日复扫）  
- 付费人数 = 假门选 ②或③ 的人数（年费约 ¥68–99）  
- **Go**：再用率≥≈1/3 且说得清增量 且付费≥2  
- **Stop**：再用弱 + 说不清 + 付费≈0  
- **Pivot**：角色/价值错位（见 #28）  

代码速算（可选）：`summarize_valid_children(rows)` in `utils/validation_evidence.py`。  
最终判定请评论到 #26 / #40。
