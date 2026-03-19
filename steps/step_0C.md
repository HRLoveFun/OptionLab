# Step 0-C：当前系统导航

## 目标
梳理现有 OptionView 系统文件职责，精确标注 futu 改造接入点，供 Phase 2 精准加载。

## 加载资源
- 现有代码库（按需精读，不全量加载）
- 重点文件：`app.py`、`data_pipeline/downloader.py`、`services/options_chain_service.py`、`core/options_chain_analyzer.py`

## 执行过程
1. 阅读 `app.py` 中 `option_chain()` 路由函数（约60行），记录：
   - 函数起止行号
   - 依赖的外部函数/类
   - 返回数据结构（字段名列表）
2. 阅读 `OptionsChainAnalyzer.__init__()` 输入格式
3. 梳理其他关键文件职责（快速扫描，不深读）

## 产出物
**文件**：`docs/nav/system_nav.md`

**格式模板**：
```markdown
# 当前系统导航

## 文件职责速查
| 文件 | 职责 | 关键函数/类 | 改造必要性 |
|---|---|---|---|
| `app.py` | Flask 路由层 | `option_chain()` L行-L行, `validate_ticker()` | 必须改 |
| `data_pipeline/downloader.py` | yfinance 下载 | `upsert_raw_prices()` | 可选改 |
| `services/options_chain_service.py` | 期权链分析编排 | `OptionsChainService.generate_options_chain_analysis()` | 无需改 |
| `core/options_chain_analyzer.py` | IV/Greeks 计算 | `OptionsChainAnalyzer` | 无需改 |
| `core/options_greeks.py` | BS定价 | `greeks_vectorized()` | 无需改 |

## option_chain() 路由详情
- 位置：`app.py` L行-L行
- 输入：`ticker` (query param), 当前无 `source` 参数
- 核心逻辑：调用 yfinance → 格式化 → 返回 JSON
- 返回字段：`expirations`, `chain.{date}.calls`, `chain.{date}.puts`, `spot`
- calls/puts 字段：`strike`, `lastPrice`, `bid`, `ask`, `volume`, `openInterest`, `iv`, `itm`, `liq_score`

## OptionsChainAnalyzer 输入格式
- 输入：ticker (str)，构造函数内部调用 yfinance
- 改造点：需将数据源抽象出来，或新建并行入口

## futu 接入点（Phase 2 改造位置）
（本节由 Step 2-A 追加填写）
```

## 完成标准
- [ ] `option_chain()` 函数行号记录准确
- [ ] 返回字段列表完整（至少9个字段）
- [ ] 新会话只读此文件，30秒内能回答「需要改哪两个文件的哪些函数」

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 1-A
- 已完成 → 追加 Step 0-C
- `docs/nav/system_nav.md` → ✅ 已创建（「futu 接入点」节待 Step 2-A 追加）
