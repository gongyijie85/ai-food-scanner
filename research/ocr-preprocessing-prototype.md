# OCR 预处理交互原型设计

## 目标

验证"OCR 前置提取文字 + VLM 结构化"是否比"直接把图片丢给 VLM"在**准确率、耗时、成本**上更有优势，并确定最终接入主流程的交互与回退策略。

## 用户侧流程（保持不变）

```text
用户拍照/上传图片
        ↓
  点击「开始识别」大按钮
        ↓
  页面显示："正在提取配料文字…"（OCR 阶段）
        ↓
  页面显示："正在分析成分…"（VLM 阶段）
        ↓
  结果页：评分、风险等级、健康建议
```

老人用户无感知，流程仍是一键识别，只是后台变成两步。

## 后台流程

```text
上传图片
  ↓
encode_image_to_base64()（压缩）
  ↓
OCR 预处理层（可插拔）
  ├─ 默认：百度 OCR 云 API（BAIDU_OCR_APP_KEY / SECRET_KEY）
  ├─ 降级 1：Tesseract.js / PaddleOCR 本地识别
  └─ 降级 2：跳过 OCR，直接把图片给 VLM
  ↓
提取到 ocr_text（配料表原始文字）
  ↓
把 ocr_text 作为上下文放进 system prompt / user content
  ↓
调用 VLM（MiMo / Agnes）做结构化输出
  ↓
解析 JSON → 评分 → 结果页
```

## prompt 变化示例

**旧 prompt（纯图片）**：

> 你是中国食品/保健食品标签解读助手。用户上传标签图片，请按规则返回纯 JSON……

**新 prompt（图片 + OCR 文字）**：

> 你是中国食品/保健食品标签解读助手。我已通过 OCR 提前提取到配料表文字如下：
> ```
> 配料：水、果葡糖浆、白砂糖、浓缩苹果汁、食品添加剂（山梨酸钾、阿斯巴甜）……
> ```
> 图片仅作为校对。请基于 OCR 文字返回纯 JSON，不要编造未出现的配料……

## 交互原型要点

1. **识别按钮**：保持 56px 大按钮，文案从「开始识别」可细化为「先提取文字，再分析成分」。
2. **进度提示**：`st.spinner` 分两段显示：
   - 第一段："正在读取配料表文字…"
   - 第二段："正在分析成分风险…"
3. **失败回退**：
   - OCR 失败或返回空 → 自动走原流程（直接传图给 VLM）。
   - VLM 结构化失败 → 展示"识别失败，请重试或换一张清晰照片"。
4. **高级设置页选项**：
   - OCR 提供方切换：百度 OCR / 本地 PaddleOCR / 关闭（纯 VLM）
   - OCR 置信度阈值（默认 0.6）

## 评估指标

| 指标 | 测试方法 | 期望 |
|---|---|---|
| 准确率 | 对 20 张测试图分别跑「纯 VLM」和「OCR+VLM」，对比 ingredients/additives 召回率 | OCR+VLM 提升 ≥10% |
| 耗时 | 记录端到端耗时 | 增加 OCR 阶段后总耗时 ≤ 35 秒 |
| 成本 | 统计 MiMo token 消耗 | OCR 成本 + VLM 成本 ≤ 原 VLM 成本的 120% |
| 幻觉率 | 统计 VLM 编造的添加剂数量 | OCR+VLM 幻觉率明显下降 |

## 原型脚本结构（research/ocr_prototype.py）

```python
"""OCR 预处理原型：对比纯 VLM vs OCR+VLM。"""
import os
from PIL import Image
from utils.api import encode_image_to_base64, call_api, build_system_prompt

# 1. 加载测试图
image_path = "test_label.jpg"
image_b64 = encode_image_to_base64(image_path)

# 2. OCR 预处理（可替换为百度 OCR / PaddleOCR）
ocr_text = ocr_extract(image_b64)  # 返回配料表原始文字

# 3. 构造增强 prompt
system_prompt = build_system_prompt(groups=[])
user_content = [
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
    {"type": "text", "text": f"OCR 已提取配料文字：\n{ocr_text}\n请基于上述文字返回 JSON。"},
]

# 4. 调用 VLM
result = call_api_with_content(api_key, user_content, system_prompt)

# 5. 解析并打印
print(result)
```

## 结论与建议

- **交互层**：用户流程保持不变，仅在识别中加入 OCR 阶段进度提示和自动回退。
- **实现层**：新增 `services/ocr_provider.py` 抽象 OCR 接口，默认百度 OCR，支持本地 PaddleOCR 和关闭。
- **测试层**：先使用 10-20 张本地测试图跑原型脚本，确认准确率和成本后再接入主流程。
- **风险**：百度 OCR 需要额外 App Key/Secret；如不想新增密钥，可先用本地 Tesseract 做原型验证。
