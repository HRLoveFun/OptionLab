# Step 2-B：核心改造

## 目标
创建 `data_pipeline/futu_provider.py`，修改 `app.py` 增加 `source` 参数，对齐字段格式。

## 前置检查
确认以下文件存在：
- `futu_tested_functions.py` ✅
- `docs/field_mapping.md` ✅
- `docs/nav/system_nav.md` 含「futu 接入点」节 ✅

## 加载资源
- `docs/nav/system_nav.md`（含改造接入点）
- `futu_tested_functions.py`（完整）
- `docs/field_mapping.md`（完整）
- `app.py`：只读 `option_chain()` 函数段（行号来自 `system_nav.md`）

**禁止加载**：`app.py` 全文、前端代码、分析类代码

## 执行过程

### 任务1：创建 `data_pipeline/futu_provider.py`
- 直接 `from futu_tested_functions import ...` 调用已验证函数
- 不重写底层调用逻辑
- 实现字段换算：依据 `field_mapping.md` 将 futu 字段名转换为 `option_chain()` 路由期望的字段名
- 实现连接生命周期管理（使用 `futu_tested_functions.py` 中的连接管理函数）
- 对外接口与 yfinance 路径返回相同的数据结构

**关键接口**：
```python
def get_option_chain_futu(ticker: str, host: str, port: int) -> dict:
    """
    返回与 yfinance 路径相同格式的期权链数据：
    {
        "expirations": [...],
        "chain": {
            "YYYY-MM-DD": {
                "calls": [...],  # 与 app.py 中 df_to_records() 输出格式一致
                "puts": [...]
            }
        },
        "spot": float
    }
    """
```

### 任务2：修改 `app.py`
- 在 `option_chain()` 路由增加 `source` 参数（query param，默认 `"yfinance"`）
- `source == "futu"` 时调用 `futu_provider.get_option_chain_futu()`
- `source == "yfinance"` 时保持原有逻辑完全不变
- 修改范围：只在 `option_chain()` 函数内，不动其他路由

## 产出物
**新建**：`data_pipeline/futu_provider.py`
**修改**：`app.py`（`option_chain()` 函数段）

## 完成标准
- [ ] `GET /api/option_chain?ticker=US.AAPL&source=futu` 返回非空 JSON
- [ ] 返回 JSON 包含 `expirations`, `chain`, `spot` 三个顶层字段
- [ ] `GET /api/option_chain?ticker=AAPL&source=yfinance` 行为与改造前完全一致（回归）
- [ ] `futu_provider.py` 中无重复的底层 futu API 调用逻辑（全部来自 `futu_tested_functions.py`）

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 2-C
- 已完成 → 追加 Step 2-B
- `data_pipeline/futu_provider.py` → ✅ 已创建
