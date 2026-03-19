# Step 2-C：Ticker 格式适配

## 目标
实现 Ticker 双向转换工具函数，覆盖美股和港股。

## 加载资源
- `docs/api_syntax_notes.md`（Ticker 格式规则部分，Step 1-A 写入）

## 执行过程
将 Step 1-A 中的伪代码实现为可运行的 Python 函数，并添加单元测试。

## 产出物
**新建**：`utils/ticker_utils.py`

**接口**：
```python
def to_futu_ticker(symbol: str, market: str = "US") -> str:
    """将普通 Ticker 转为 futu 格式。"AAPL" -> "US.AAPL" """

def from_futu_ticker(futu_ticker: str) -> tuple[str, str]:
    """将 futu Ticker 拆分为 (symbol, market)。"US.AAPL" -> ("AAPL", "US") """
```

## 完成标准
- [ ] 覆盖美股（`US.AAPL`）、港股（`HK.00700`）
- [ ] 双向转换均有测试用例
- [ ] 5个边界案例测试通过（含无效输入的异常处理）

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 3-A
- 已完成 → 追加 Step 2-C
- `utils/ticker_utils.py` → ✅ 已创建
