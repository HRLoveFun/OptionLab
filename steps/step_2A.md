# Step 2-A：理解改造点

## 目标
精读现有系统的改造位置，将 futu 接入点与 `futu_tested_functions.py` 中的函数一一对应，追加到 `docs/nav/system_nav.md`。

## 前置检查
确认 `project_state.md` 中以下产出物已存在：
- `futu_tested_functions.py` ✅
- `docs/field_mapping.md` ✅

如未满足，停止执行，返回错误。

## 加载资源
- `docs/nav/system_nav.md`（已存在，本步骤追加内容）
- `app.py`：只读 `option_chain()` 函数（精确行号来自 `system_nav.md`）
- `futu_tested_functions.py`（查看 P0 函数列表）

**禁止加载**：`app.py` 全文、分析类代码、前端代码

## 执行过程
1. 从 `system_nav.md` 取 `option_chain()` 行号范围，精读该段代码
2. 识别每个数据获取调用（yfinance 的 `tkr.options`、`tkr.option_chain()` 等）
3. 对每个调用，在 `futu_tested_functions.py` 中找到对应的 futu 函数
4. 评估 `OptionsChainAnalyzer` 的输入格式与 `field_mapping.md` 的字段对应关系

## 产出物
**追加到**：`docs/nav/system_nav.md` 末尾的「futu 接入点」节

**写入内容**：
```markdown
## futu 接入点（Step 2-A 补充）

### app.py option_chain() 路由改造点
| 位置 | 当前调用 | futu 替代函数 | 字段对齐需求 |
|---|---|---|---|
| L行 | `tkr.options` | `get_option_expiration_dates()` | 返回格式对齐 |
| L行 | `tkr.option_chain(exp)` | `get_option_chain()` | 见 field_mapping.md |
| L行 | `fi.last_price` | `get_spot_price()` | 直接替换 |

### 改造方案
- 新增参数 `source` (str)，默认 `"yfinance"`
- `source == "futu"` 时调用 `futu_provider.py`（Step 2-B 创建）
- `OptionsChainAnalyzer` 及下游代码无需修改
```

## 完成标准
- [ ] 每个 yfinance 调用点都有对应 futu 函数（来自 `futu_tested_functions.py`）
- [ ] 字段对齐需求明确（引用 `field_mapping.md` 中的具体字段）
- [ ] 改造方案不要求修改 `OptionsChainAnalyzer`

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 2-B
- 已完成 → 追加 Step 2-A
- `docs/nav/system_nav.md` → ✅ futu 接入点节已追加
