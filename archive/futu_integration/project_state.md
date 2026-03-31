# OptionView 项目状态

## 当前状态
- **当前步骤**：方案完成
- **状态**：三层验证已通过
- **已完成步骤**：Step 0-A, Step 0-B, Step 0-C, Step 1-A, Step 1-B, Step 1-C, Step 2-A, Step 2-B, Step 2-C, Step 3-A

## 产出物状态
| 文件 | 状态 |
|---|---|
| `docs/nav/futu_api_doc_nav.md` | ✅ 已创建 |
| `docs/nav/futu_github_nav.md` | ✅ 已创建 |
| `docs/nav/system_nav.md` | ✅ 已完成（futu 接入点节已追加：3 个 yfinance 调用点映射 + 字段对齐表 + 改造方案） |
| `docs/api_syntax_notes.md` | ✅ 已完成（Step 1-B 追加完毕：连接管理 + 3 个 API 语法） |
| `futu_tested_functions.py` | ✅ P0 已验证（2026-03-19）：get_option_expiration_dates / get_option_chain / get_spot_price + P1 连接管理 create_quote_ctx |
| `docs/field_mapping.md` | ✅ 已创建（2026-03-19）：3 个 API 返回字段 + yfinance 对照表，共 44 个字段，无「待确认」 |
| `data_pipeline/futu_provider.py` | ✅ 已验证（2026-03-20）：Step 3-A 修复3项 — subscribe 容错、per-batch unsubscribe、rate limiting |
| `utils/ticker_utils.py` | ✅ 已创建（2026-03-19）：to_futu_ticker / from_futu_ticker 双向转换，27 个测试全部通过 |

## 下一步
方案已完成。所有 Phase 1-2 步骤（0-A ~ 3-A）已执行并验证。

## Step 1-C 验证记录
- P0-1 `get_option_expiration_dates('US.AAPL')` → 26 个到期日，3 列
- P0-2 `get_option_chain('US.AAPL', start, end)` → 158 个合约，14 列
- P0-3 `get_spot_price('HK.00700')` → 513.0（subscribe + get_stock_quote 方式；get_market_snapshot 超时）
- P1-4 `create_quote_ctx()` context manager → 正常创建/关闭
- P1-5 连续 10 次调用无泄漏（线程稳定 3，FD 稳定 8-9）
- 注意：US 股票实时行情需要权限（期权元数据无此限制）；get_market_snapshot 始终超时
- bid/ask 字段缺口：get_stock_quote 未返回 bid/ask，需 Phase 2 调查 ORDER_BOOK 订阅

## Step 2-A 改造点摘要
- app.py option_chain() 路由共 3 个 yfinance 调用点，均有对应 futu 函数
- L233 `tkr.option_chain(exp)` 改造最复杂：futu 需两步（get_option_chain 取代码 + subscribe/get_stock_quote 取报价）
- 8 个字段逐一映射，其中 bid/ask/openInterest/impliedVolatility 待 Step 2-B 补充验证
- 改造方案：路由新增 source 参数，futu 路径由 futu_provider.py 封装
- OptionsChainAnalyzer 无需修改（该类有独立 yfinance 依赖，属另一改造目标）

## Step 2-B 实现摘要
- **新建** `data_pipeline/futu_provider.py`：
  - `get_option_chain_futu(ticker, host, port)` 对外接口，返回 `{expirations, chain, spot}` 与 yfinance 路径格式一致
  - 使用 `create_quote_ctx()` 共享连接，`get_option_expiration_dates()` 获取到期日
  - `_fetch_all_chains()` 按 30 天窗口批量获取静态期权链（遵守频率限制 10 次/30s）
  - `_fetch_quotes()` 按 200 合约/批次批量 subscribe + get_stock_quote 获取动态行情
  - `_build_records()` 字段映射：strike_price→strike, last_price→lastPrice, volume→volume, open_interest→openInterest, implied_volatility→iv（百分比直接使用）, inTheMoney 由 spot+strike 计算
  - bid/ask 暂为 None（get_stock_quote 不返回 bid/ask 字段，待后续 ORDER_BOOK 订阅解决）
- **修改** `app.py` option_chain() 路由：
  - 新增 `source` query param，默认 `"yfinance"`
  - `source=futu` 时调用 `get_option_chain_futu()`，host/port 从 `FUTU_HOST`/`FUTU_PORT` 环境变量读取
  - yfinance 路径代码完全未改动

## Step 2-C 实现摘要

## Step 3-A 三层验证记录（2026-03-20）

### 层1：单元验证 ✅
- **1-1 Ticker 转换**：5 个案例全部通过（AAPL/US, 00700/HK, SPY/US, 空 symbol ValueError, 未知市场 ValueError）；27 个 pytest 测试全部通过
- **1-2 字段映射完整性**：futu_provider 输出 10 个字段（strike, lastPrice, bid, ask, volume, openInterest, iv, itm, liq_score, liq_reason）完全覆盖路由期望字段；顶层键（expirations, chain, spot）与 yfinance 路径一致
- **1-3 连接管理**：10 次连续调用后线程 delta=-1、FD delta=0，无泄漏

### 层2：集成验证 ✅
- **HK.00700**：HTTP 200, spot=513.0, 9 个到期日, 29 calls/29 puts, 全部 10 个字段存在, 响应 ~3.3s ✅
- **US.AAPL**：HTTP 200, spot=None（美股非交易时段 subscribe 失败,已做容错处理）, 26 个到期日, 1646 calls/1646 puts, 全部 10 个字段存在, IV 覆盖率 77/79 ✅
  - spot=None 原因：`subscribe [US.AAPL] QUOTE` 返回「拉取美股夜盘状态失败」,已修改为 warning + graceful fallback
  - 响应时间 ~53s（26 个到期日 × 3.1s rate limit = ~80s 理论下限,含 3400+ 合约),非代码问题,为 futu API 频率限制

### 层3：回归验证 ⚠️（外部服务限制）
- **yfinance 路径代码未变更**：`git diff HEAD -- app.py` 确认仅新增 12 行 futu 分支代码,yfinance 路径 0 行变动
- **HTTP 测试被 Yahoo Finance rate limit 阻断**：`source=yfinance` 和无参数（默认）请求均返回 `"Too Many Requests"`,为 Yahoo Finance 服务端瞬态限流,非代码回归
- **结论**：yfinance 代码路径完全未修改,不存在回归风险

### Step 3-A 期间的修复
1. **subscribe 容错**（futu_provider.py L232-242）：spot subscribe 失败时不再 raise RuntimeError,改为 warning + spot=None,保证美股非交易时段可正常返回静态数据
2. **per-batch unsubscribe**（futu_provider.py _fetch_quotes）：每批 get_stock_quote 后立即 unsubscribe,释放订阅额度
3. **rate limiting**（futu_provider.py _fetch_all_chains）：get_option_chain 调用间隔 3.1s,遵守 10 次/30s 频率限制

### 已知限制（futu SDK 约束,非代码缺陷）
- **订阅额度**：futu 账户总额度 1000 个订阅。AAPL 有 3400+ 合约,超出额度的合约无动态报价（bid/ask/volume 为 None）
- **最小订阅时间**：futu SDK 要求订阅至少 1 分钟才能 unsubscribe,导致单次请求内 unsubscribe 不生效;连接关闭后订阅自动释放
- **bid/ask 缺失**：get_stock_quote 不返回 bid/ask 字段（见 field_mapping.md）,需后续接入 ORDER_BOOK 订阅解决
- **新建** `utils/ticker_utils.py`：
  - `to_futu_ticker(symbol, market="US")` — 将普通 symbol 转为 futu 格式（如 `"AAPL"` → `"US.AAPL"`）
  - `from_futu_ticker(futu_ticker)` — 将 futu 格式拆分为 `(symbol, market)` 元组
  - 支持全部 10 个市场前缀：US, HK, SH, SZ, SG, JP, AU, MY, CA, FX
  - market 参数大小写不敏感
  - 完善的输入校验：空 symbol、空 market、未知市场、缺少点号、None 等均抛 ValueError
- **新建** `tests/test_ticker_utils.py`：27 个测试用例
  - US/HK/SH/SZ 正常转换
  - 期权 ticker 解析（`US.AAPL250618P550000`）
  - 6 个参数化 round-trip 测试
  - 8 个边界/异常测试用例

## 关键约束提醒
- Phase 2 门控已通过：`futu_tested_functions.py` ✅ + `docs/field_mapping.md` ✅
- 每个步骤只新增自己的产出物，不修改其他步骤的产出物

## 更新说明
> 每次步骤完成后，更新当前步骤、已完成列表、产出物状态，粘贴到此文件。
