# futu-api 字段映射表

（本文件由 Step 1-C 基于实机运行输出生成，以实际输出为准）
（更新日期：2026-03-19）

## get_option_expiration_date() 返回字段

实机调用：`ctx.get_option_expiration_date(code='US.AAPL')`
返回：`pd.DataFrame`，shape=(26, 3)

| futu 字段名 | Python 类型 | 示例值 | 对应 yfinance 字段 | 说明 |
|---|---|---|---|---|
| strike_time | str | "2026-03-20" | `tk.options` 列表元素 | 到期日 |
| option_expiry_date_distance | int64 | 1 | （无直接对应） | 距到期日天数 |
| expiration_cycle | str | "MONTH" | （无直接对应） | 到期周期：MONTH / WEEK |

## get_option_chain() 返回字段

实机调用：`ctx.get_option_chain(code='US.AAPL', start='2026-03-20', end='2026-03-20')`
返回：`pd.DataFrame`，shape=(158, 14)

| futu 字段名 | Python 类型 | 示例值 | 对应 yfinance 字段 | 说明 |
|---|---|---|---|---|
| code | str | "US.AAPL260320C90000" | `contractSymbol` | 期权代码 |
| name | str | "AAPL 260320 90.00C" | （无直接对应） | 期权名称 |
| lot_size | int64 | 100 | （无直接对应） | 每手股数 |
| stock_type | str | "DRVT" | （无直接对应） | 证券类型（衍生品） |
| option_type | str | "CALL" | （通过 calls/puts 分表区分） | 期权方向 CALL/PUT |
| stock_owner | str | "US.AAPL" | （无直接对应） | 标的股票代码 |
| strike_time | str | "2026-03-20" | （通过到期日参数区分） | 到期日 |
| strike_price | float64 | 90.0 | `strike` | 行权价 |
| suspension | bool | False | （无直接对应） | 是否停牌 |
| stock_id | int64 | 501274783 | （无直接对应） | 内部股票 ID |
| index_option_type | str | "N/A" | （无直接对应） | 指数期权类型，普通股票为 N/A |
| expiration_cycle | str | "MONTH" | （无直接对应） | 到期周期 |
| option_standard_type | str | "STANDARD" | （无直接对应） | 标准/非标准期权 |
| option_settlement_mode | str | "N/A" | （无直接对应） | 结算模式（AM/PM），普通为 N/A |

注意：此接口仅返回**静态信息**（代码、行权价、到期日等）。动态行情（bid/ask/IV/Greeks）需用返回的期权代码调用 `subscribe` + `get_stock_quote`。

## get_stock_quote() 返回字段（现货价格 + 期权行情）

### 股票行情（subscribe + get_stock_quote）

实机调用：`ctx.subscribe(['HK.00700'], [SubType.QUOTE])` → `ctx.get_stock_quote(['HK.00700'])`
返回：`pd.DataFrame`，共 62 列

以下为对股票有值的字段：

| futu 字段名 | Python 类型 | 示例值 | 对应用途 | 说明 |
|---|---|---|---|---|
| code | str | "HK.00700" | — | 代码 |
| name | str | "腾讯控股" | — | 名称 |
| data_date | str | "2026-03-19" | — | 数据日期 |
| data_time | str | "16:07:59" | — | 数据时间 |
| last_price | float64 | 513.0 | spot price | 最新成交价 ← 用于 get_spot_price() |
| open_price | float64 | 528.0 | — | 开盘价 |
| high_price | float64 | 529.5 | — | 最高价 |
| low_price | float64 | 512.0 | — | 最低价 |
| prev_close_price | float64 | 550.5 | — | 昨收价 |
| volume | int64 | 59432770 | — | 成交量 |
| turnover | float64 | 30817089730.0 | — | 成交额 |
| turnover_rate | float64 | 0.651 | — | 换手率 |
| amplitude | float64 | 3.179 | — | 振幅 |
| suspension | bool | False | — | 是否停牌 |
| listing_date | str | "2004-06-16" | — | 上市日期 |
| price_spread | float64 | 0.5 | — | 价差 |
| sec_status | str | "NORMAL" | — | 股票状态 |

其余 45 列（期权/期货/盘前盘后/夜盘字段）对非期权合约为 "N/A"。

### 期权合约行情（subscribe + get_stock_quote）

实机调用：`ctx.subscribe(['US.AAPL260330C255000'], [SubType.QUOTE])` → `ctx.get_stock_quote(['US.AAPL260330C255000'])`

以下为对期权合约额外有值的字段：

| futu 字段名 | Python 类型 | 示例值 | 对应 yfinance 字段 | 说明 |
|---|---|---|---|---|
| last_price | float64 | 2.25 | `lastPrice` | 最新价 |
| open_price | float64 | 2.04 | （无直接对应） | 开盘价 |
| high_price | float64 | 3.18 | （无直接对应） | 最高价 |
| low_price | float64 | 2.04 | （无直接对应） | 最低价 |
| prev_close_price | float64 | 2.515 | （无直接对应） | 昨收价 |
| volume | int64 | 3847 | `volume` | 成交量 |
| strike_price | float64 | 255.0 | `strike` | 行权价 |
| contract_size | float64 | 100.0 | （无直接对应） | 每张合约股数 |
| open_interest | int64 | 227 | `openInterest` | 未平仓合约数 |
| implied_volatility | float64 | 24.359 | `impliedVolatility` | 隐含波动率（futu 为百分比值，yfinance 为小数） |
| premium | float64 | 3.014 | （无直接对应） | 溢价 |
| delta | float64 | 0.336610963 | （无直接对应，需自行计算） | Greek Delta |
| gamma | float64 | 0.034217976 | （无直接对应） | Greek Gamma |
| vega | float64 | 0.159804037 | （无直接对应） | Greek Vega |
| theta | float64 | -0.184805379 | （无直接对应） | Greek Theta |
| rho | float64 | 0.025109542 | （无直接对应） | Greek Rho |
| expiry_date_distance | int64 | 11 | （无直接对应） | 距到期日天数 |
| option_area_type | str | "AMERICAN" | （无直接对应） | 行权类型 |
| contract_multiplier | float64 | 100.0 | （无直接对应） | 合约乘数 |

HK 期权额外字段（US 期权为 N/A）：

| futu 字段名 | Python 类型 | 示例值 | 说明 |
|---|---|---|---|
| net_open_interest | int64 | 2562 | 净未平仓合约数 |
| contract_nominal_value | float64 | 51300.0 | 合约名义金额 |
| owner_lot_multiplier | float64 | 1.0 | 等价标的股数 |

## yfinance → futu 字段对照汇总

本项目 `app.py` option_chain 路由当前使用的 yfinance 字段，与 futu 对应关系：

| yfinance 字段 | futu 对应字段 | 来源接口 | 转换说明 |
|---|---|---|---|
| `strike` | `strike_price` | get_option_chain / get_stock_quote | 直接对应 |
| `lastPrice` | `last_price` | get_stock_quote（需 subscribe） | 直接对应 |
| `bid` | `bid_price`（需进一步验证） | get_stock_quote（需 subscribe ORDER_BOOK） | get_stock_quote 返回中未见 bid/ask 字段 |
| `ask` | `ask_price`（需进一步验证） | get_stock_quote（需 subscribe ORDER_BOOK） | get_stock_quote 返回中未见 bid/ask 字段 |
| `volume` | `volume` | get_stock_quote（需 subscribe） | 直接对应 |
| `openInterest` | `open_interest` | get_stock_quote（需 subscribe） | 直接对应 |
| `impliedVolatility` | `implied_volatility` | get_stock_quote（需 subscribe） | futu 为百分比（24.359），yfinance 为小数（0.24359） |
| `inTheMoney` | （无直接对应） | — | 需根据 strike_price 与 spot 自行计算 |
| spot（`tk.fast_info['lastPrice']`） | `last_price` | get_stock_quote（标的股票） | 直接对应 |

### 字段缺口说明

1. **bid / ask**：`get_stock_quote` 的 62 列中未出现 `bid_price` / `ask_price`。可能需要订阅 `SubType.ORDER_BOOK` 后通过 `get_order_book()` 获取。此为 Phase 2 改造时需解决的问题。
2. **inTheMoney**：futu 无直接字段，需在代码中根据 `strike_price` 与 spot 价格计算。
3. **IV 单位差异**：futu `implied_volatility` 为百分比值（如 24.359 = 24.359%），yfinance 为小数（如 0.24359）。转换时需除以 100。

## get_market_snapshot() 状态说明

`get_market_snapshot()` 在实机测试中始终超时（"获取市场快照请求超时"），无论是否先订阅。
本文件中所有 snapshot 相关字段均通过 `subscribe` + `get_stock_quote` 获取并验证。
`get_market_snapshot` 文档声称的字段名（带 `option_` 前缀，如 `option_delta`、`option_strike_price`）
与 `get_stock_quote` 实际返回的字段名（无 `option_` 前缀，如 `delta`、`strike_price`）不同。
Phase 2 改造时，若需使用 `get_market_snapshot`，需重新实机验证其字段名。
