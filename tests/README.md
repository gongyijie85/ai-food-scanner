# tests/

默认 `pytest` 只收集本目录下与 **当前 main 已实现代码** 对齐的用例。

## 已移除 / 迁出

| 路径 | 原因 |
|------|------|
| `test_async_api.py`（已删） | 依赖 `call_api_async` / `ApiResult`，main 未实现；会导致收集阶段 ImportError |
| `diagnose_api*.py`、`verify_v014.py` | 迁至 `scripts/local/`，非 pytest 用例 |

## P2 异步 API

若日后实现 `utils.api.call_api_async`，再新增对应测试；不要在未实现前恢复旧文件。
