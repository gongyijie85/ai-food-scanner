# AI食品配料表识别工具 - 原型运行说明

## 文件说明

| 文件 | 用途 |
|------|------|
| `prototype_mimo.py` | 最小验证原型,调用 MiMo Vision API 识别配料表 |
| `test_label.jpg` | 测试用配料表图片(需你自己准备) |
| `last_api_response.txt` | 运行后自动生成,保存 API 原始响应 |

## 运行步骤

### 第一步：安装依赖

```powershell
pip install requests
```

### 第二步：准备 API 密钥

**推荐方式：环境变量(安全)**

在 PowerShell 中临时设置(当前窗口有效)：
```powershell
$env:MIMO_API_KEY="你的MiMo API密钥"
```

永久设置：
- 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
- 新建用户变量：`MIMO_API_KEY`, 值为你的密钥

**不推荐但简单的方式：**
打开 `prototype_mimo.py`, 把第21行改成：
```python
API_KEY = "你的MiMo API密钥"
```
注意：这种方式不要把代码上传到公开仓库。

### 第三步：准备测试图片

把一张清晰的配料表照片放到 `d:\GBT\ai-food-scanner\` 目录下,重命名为 `test_label.jpg`。

**如果你没有现成图片：**
- 用手机拍一张家里食品的配料表
- 确保文字清晰、光线均匀、无反光
- 推荐食品：酱油、饼干、饮料、方便面(配料表内容较丰富)

### 第四步：运行原型

```powershell
cd d:\GBT\ai-food-scanner
python prototype_mimo.py
```

### 第五步：查看结果

运行成功后会打印：
- 产品名称
- 综合评分
- 全部配料
- 食品添加剂清单(带安全等级)
- 健康建议

同时会生成 `last_api_response.txt`,保存模型返回的原始 JSON。

## 常见问题

### 1. 提示"错误：缺少 MIMO_API_KEY 环境变量"

说明你还没设置密钥。请按第二步操作。

### 2. 提示"错误：找不到图片文件 test_label.jpg"

说明测试图片还没放。请按第三步操作。

### 3. API 返回 401

密钥无效或过期。请检查密钥是否正确,或到 MiMo 平台重新生成。

### 4. API 返回 404

可能是 API 地址或模型名称不对。请打开 MiMo 官方文档确认：
https://mimo.mi.com/docs/zh-CN/usage-guide/multimodal-understanding/image-understanding

然后修改 `prototype_mimo.py` 中的：
```python
API_URL = "https://api.mimo.mi.com/v1/chat/completions"  # 以官方文档为准
MODEL_NAME = "mimo-vision"  # 以官方文档为准
```

### 5. 模型返回的不是 JSON

程序会打印原始内容并保存到 `last_api_response.txt`。把文件内容发给我,我帮你调整提示词。

## 注意事项

- 这是最小验证原型,只验证 API 能不能识别配料表
- 还没做 UI、语音、历史记录、本地数据库等功能
- 这些功能等 API 验证通过后再逐步添加
