# futu-api 调用语法笔记

（本文件由 Step 1-A 初始化，Step 1-B 追加内容）

## 1. Ticker 格式规则

（来源：Q15 — Parameter format of stock code，`Futu-API-Doc-en-Python.md` L9522-L9540；Quote Market 枚举，L4785-L4830；期权链输出示例，L2620-L2640）

### 通用格式

Python 用户统一使用 `{market}.{code}` 格式（字符串）。

### 各市场 Ticker 格式

| 市场 | 前缀 | 股票/ETF 示例 | 代码规则 |
|------|------|--------------|---------|
| 美股 | `US` | `US.AAPL`, `US.SPY` | 大写字母 symbol |
| 港股 | `HK` | `HK.00700` | 5 位数字（前补零） |
| 沪市 | `SH` | `SH.600519` | 6 位数字 |
| 深市 | `SZ` | `SZ.000001` | 6 位数字 |
| 新加坡 | `SG` | — | 期货为主 |
| 日本 | `JP` | `JP.NK225main` | 期货为主 |

其他支持的市场前缀：`AU`（澳洲）、`MY`（马来西亚）、`CA`（加拿大）、`FX`（外汇）。

### 期权 Ticker 格式

期权代码由 `get_option_chain()` 返回，格式为：

```
{market}.{underlying_abbr}{YYMMDD}{C|P}{StrikePrice*1000}
```

| 市场 | 示例 | 说明 |
|------|------|------|
| 美股 | `US.AAPL250618P550000` | AAPL 2025-06-18 Put Strike $550.00 |
| 港股 | `HK.TCH210429C350000` | 腾讯 2021-04-29 Call Strike $350.00 |

- `C` = Call, `P` = Put
- 行权价乘以 1000，整数表示（如 350.00 → `350000`，550.00 → `550000`）
- 标的缩写由交易所决定（美股通常与 symbol 相同，港股为缩写如 `TCH`）

### 特殊案例

- **指数/ETF**：与普通股票相同格式，如 `US.SPY`、`HK.02800`（盈富基金）
- **期货**：使用合约简写，如 `JP.NK225main`
- **板块代码**：`HK.Motherboard`、`US.NYSE`、`SH.3000000` 等（用于 `get_plate_stock` 等接口，非行情代码）

### 转换伪代码

```python
# 已知市场前缀集合
FUTU_MARKETS = {"US", "HK", "SH", "SZ", "SG", "JP", "AU", "MY", "CA", "FX"}


def to_futu_ticker(symbol: str, market: str) -> str:
    """将 symbol + market 转为 futu 格式 ticker。

    Args:
        symbol: 纯代码，如 "AAPL"、"00700"、"600519"
        market: 市场前缀，如 "US"、"HK"、"SH"
    Returns:
        futu 格式 ticker，如 "US.AAPL"
    Raises:
        ValueError: market 不在已知集合中
    """
    market = market.upper()
    if market not in FUTU_MARKETS:
        raise ValueError(f"Unknown market: {market}")
    return f"{market}.{symbol}"


def from_futu_ticker(futu_ticker: str) -> tuple[str, str]:
    """将 futu 格式 ticker 拆分为 (symbol, market)。

    Args:
        futu_ticker: 如 "US.AAPL"、"HK.TCH210429C350000"
    Returns:
        (symbol, market) 元组，如 ("AAPL", "US")
    Raises:
        ValueError: 格式不合法或 market 未知
    """
    if "." not in futu_ticker:
        raise ValueError(f"Invalid futu ticker format: {futu_ticker}")
    market, symbol = futu_ticker.split(".", 1)
    market = market.upper()
    if market not in FUTU_MARKETS:
        raise ValueError(f"Unknown market: {market}")
    return symbol, market
```

## 2. 连接管理模式

（来源：Quote Object / Create and Initialize the Connection，`Futu-API-Doc-en-Python.md` L1090-L1143）

- 上下文类：`OpenQuoteContext`（行情），另有 `OpenHKTradeContext` / `OpenUSTradeContext`（交易，本项目暂不涉及）
- 构造函数：`OpenQuoteContext(host='127.0.0.1', port=11111, is_encrypt=None)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | str | `'127.0.0.1'` | OpenD 监听地址 |
| port | int | `11111` | OpenD 监听端口 |
| is_encrypt | bool | `None` | 是否启用加密 |

- 推荐模式（手动 close）：
  ```python
  from futu import *
  quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
  # ... 使用 quote_ctx 调用各种查询 ...
  quote_ctx.close()  # 使用完毕后务必关闭
  ```
- 生命周期方法：
  - `close()` — 关闭连接（必须调用，否则内部线程阻止进程退出）
  - `start()` — 开始异步接收推送数据
  - `stop()` — 停止异步接收推送数据
- 注意：文档示例均使用手动 `close()` 模式，未见 `with` 语句用法。可自行封装 context manager。
- 可通过 `set_all_thread_daemon` 将内部线程设为 daemon，此时不调用 `close()` 进程也可正常退出。

## 3. get_option_expiration_date()

（来源：Get Option Expiration Date，`Futu-API-Doc-en-Python.md` L2511-L2556）

- **签名**：`ret, data = quote_ctx.get_option_expiration_date(code, index_option_type=IndexOptionType.NORMAL)`
- **所属上下文**：`OpenQuoteContext`

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| code | str | （必填） | 标的股票代码，futu 格式如 `'HK.00700'`、`'US.AAPL'` |
| index_option_type | IndexOptionType | `IndexOptionType.NORMAL` | 指数期权类型（NORMAL / SMALL） |

### 返回

- `ret`：`RET_CODE`，成功时 `RET_OK`
- `data`：成功时为 `pd.DataFrame`，失败时为 `str`（错误描述）

### 文档声称字段【待实机确认 Step 1-C】

| 字段 | 类型 | 说明 |
|------|------|------|
| strike_time | str | 行权日期（到期日） |
| option_expiry_date_distance | int | 距到期日的天数 |
| expiration_cycle | ExpirationCycle | 到期周期 |

### 频率限制

- 每 30 秒最多 60 次请求

### 示例代码

```python
from futu import *
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_option_expiration_date(code='HK.00700')
if ret == RET_OK:
    print(data)
    print(data['strike_time'].values.tolist())
else:
    print('error:', data)
quote_ctx.close()
```

### 示例输出

```
   strike_time  option_expiry_date_distance expiration_cycle
0  2021-04-29   4                           N/A
1  2021-05-28   33                          N/A
2  2021-06-29   65                          N/A
...
```

## 4. get_option_chain()

（来源：Get Option Chain，`Futu-API-Doc-en-Python.md` L2557-L2700）

- **签名**：`ret, data = quote_ctx.get_option_chain(code, index_option_type=IndexOptionType.NORMAL, start=None, end=None, option_type=OptionType.ALL, option_cond_type=OptionCondType.ALL, data_filter=None)`
- **所属上下文**：`OpenQuoteContext`

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| code | str | （必填） | 标的股票代码 |
| index_option_type | IndexOptionType | `IndexOptionType.NORMAL` | 指数期权类型 |
| start | str \| None | `None` | 起始日期（到期日筛选） |
| end | str \| None | `None` | 结束日期（含当天，到期日筛选） |
| option_type | OptionType | `OptionType.ALL` | 期权方向（ALL / CALL / PUT） |
| option_cond_type | OptionCondType | `OptionCondType.ALL` | 价内/价外（ALL / WITHIN / OUTSIDE） |
| data_filter | OptionDataFilter \| None | `None` | 数据筛选条件 |

### start/end 组合规则

| start | end | 行为 |
|-------|-----|------|
| str | str | 各为指定日期 |
| None | str | start = end 前 30 天 |
| str | None | end = start 后 30 天 |
| None | None | start = 今天，end = 30 天后 |

### OptionDataFilter 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| implied_volatility_min / max | float | 隐含波动率范围 |
| delta_min / max | float | Greek Delta 范围 |
| gamma_min / max | float | Greek Gamma 范围 |
| vega_min / max | float | Greek Vega 范围 |
| theta_min / max | float | Greek Theta 范围 |
| rho_min / max | float | Greek Rho 范围 |
| net_open_interest_min / max | float | 净未平仓合约数范围 |
| open_interest_min / max | float | 未平仓合约数范围 |
| vol_min / max | float | 成交量范围 |

### 返回

- `ret`：`RET_CODE`
- `data`：成功时为 `pd.DataFrame`，失败时为 `str`

### 文档声称字段【待实机确认 Step 1-C】

| 字段 | 类型 | 说明 |
|------|------|------|
| code | str | 期权代码（如 `HK.TCH210429C350000`） |
| name | str | 期权名称 |
| lot_size | int | 每手股数 / 每张合约股数 |
| stock_type | SecurityType | 证券类型 |
| option_type | OptionType | 期权类型（CALL / PUT） |
| stock_owner | str | 标的股票代码 |
| strike_time | str | 行权日期 |
| strike_price | float | 行权价 |
| suspension | bool | 是否停牌 |
| stock_id | int | 股票 ID |
| index_option_type | IndexOptionType | 指数期权类型 |
| expiration_cycle | ExpirationCycle | 到期周期类型 |
| option_standard_type | OptionStandardType | 期权标准类型（STANDARD / NON_STANDARD） |
| option_settlement_mode | OptionSettlementMode | 期权结算模式（AM / PM） |

> ⚠️ 文档中部分字段名格式不一致（如 `stock-owner` vs `stock_owner`、`option_STANDARD_type`），实际 DataFrame 列名以实机输出为准。

### 频率限制

- 每 30 秒最多 10 次请求
- 传入时间跨度上限 30 天
- 不支持查询已到期的期权链，end 参数需为今天或未来日期

### 注意事项

- OI（未平仓合约数）每日更新，具体时间取决于交易所：
  - 美股期权：盘前（PRE_MARKET）更新
  - 港股期权：正常交易时段（Regular Trading Hours）结束后更新
- 本接口仅返回**静态信息**（代码、行权价、到期日等），动态行情需用返回的期权代码去订阅或调用 `get_market_snapshot()`

### 示例代码

```python
from futu import *
import time
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret1, data1 = quote_ctx.get_option_expiration_date(code='HK.00700')

filter1 = OptionDataFilter()
filter1.delta_min = 0
filter1.delta_max = 0.1

if ret1 == RET_OK:
    expiration_date_list = data1['strike_time'].values.tolist()
    for date in expiration_date_list:
        ret2, data2 = quote_ctx.get_option_chain(code='HK.00700', start=date, end=date, data_filter=filter1)
        if ret2 == RET_OK:
            print(data2)
            print(data2['code'][0])
            print(data2['code'].values.tolist())
        else:
            print('error:', data2)
        time.sleep(3)  # 注意频率限制
else:
    print('error:', data1)
quote_ctx.close()
```

## 5. get_market_snapshot()

（来源：Get Market Snapshot，`Futu-API-Doc-en-Python.md` L1714-L1790）

- **签名**：`ret, data = quote_ctx.get_market_snapshot(code_list)`
- **所属上下文**：`OpenQuoteContext`

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| code_list | list[str] | 股票代码列表，futu 格式 |

### 返回

- `ret`：`RET_CODE`
- `data`：成功时为 `pd.DataFrame`，失败时为 `str`

### 文档声称字段 — 通用字段【待实机确认 Step 1-C】

| 字段 | 类型 | 说明 |
|------|------|------|
| code | str | 股票代码 |
| name | str | 股票名称 |
| update_time | str | 更新时间 |
| last_price | float | 最新价 |
| open_price | float | 开盘价 |
| high_price | float | 最高价 |
| low_price | float | 最低价 |
| prev_close_price | float | 昨收价 |
| volume | int | 成交量 |
| turnover | float | 成交额 |
| turnover_rate | float | 换手率 |
| suspension | bool | 是否停牌 |
| listing_date | str | 上市日期 |
| lot_size | int | 每手股数 |
| ask_price | float | 卖一价 |
| bid_price | float | 买一价 |
| ask_vol | float | 卖一量 |
| bid_vol | float | 买一量 |
| price_spread | float | 当前向上价差 |
| sec_status | SecurityStatus | 股票状态 |
| amplitude | float | 振幅 |
| avg_price | float | 均价 |
| volume_ratio | float | 量比 |
| highest52weeks_price | float | 52 周最高价 |
| lowest52weeks_price | float | 52 周最低价 |

### 文档声称字段 — 期权专属字段【待实机确认 Step 1-C】

| 字段 | 类型 | 说明 |
|------|------|------|
| option_valid | bool | 是否为期权 |
| option_type | OptionType | 期权类型（CALL / PUT） |
| strike_time | str | 行权日期 |
| option_strike_price | float | 行权价 |
| option_contract_size | float | 每张合约股数 |
| option_open_interest | int | 总未平仓合约数 |
| option_implied_volatility | float | 隐含波动率 |
| option_premium | float | 溢价 |
| option_delta | float | Greek Delta |
| option_gamma | float | Greek Gamma |
| option_vega | float | Greek Vega |
| option_theta | float | Greek Theta |
| option_rho | float | Greek Rho |
| index_option_type | IndexOptionType | 指数期权类型 |
| option_net_open_interest | int | 净未平仓合约数 |
| option_expiry_date_distance | int | 距到期日天数（负数表示已到期） |
| option_contract_nominal_value | float | 合约名义金额 |
| option_owner_lot_multiplier | float | 等价标的股数 |
| option_area_type | OptionAreaType | 期权类型（按行权时间：AMERICAN / EUROPEAN / BERMUDA） |
| option_contract_multiplier | float | 合约乘数 |
| stock_owner | str | 标的股票代码（期权/窝轮共用字段） |

> ⚠️ 文档中存在字段名格式不一致（如 `option Strike_price`、`option delta`、`wrt delta` 等含空格），实际 DataFrame 列名以实机输出为准。`stock-owner` 在实际代码中可能为 `stock_owner`。

### 文档声称字段 — 盘前/盘后字段（摘录）【待实机确认 Step 1-C】

| 字段 | 类型 | 说明 |
|------|------|------|
| pre_price | float | 盘前价 |
| pre_high_price / pre_low_price | float | 盘前最高/最低 |
| pre_volume | int | 盘前成交量 |
| pre_turnover | float | 盘前成交额 |
| after_price | float | 盘后价 |
| after_high_price / after_low_price | float | 盘后最高/最低 |
| after_volume | int | 盘后成交量 |
| after_turnover | float | 盘后成交额 |

### 频率限制

- 每 30 秒最多 60 次快照请求
- 每次请求 `code_list` 最多 400 个代码
- 港股 BMP 权限下，港股证券（含窝轮/牛熊证/界内证）单次最多 20 个
- 港股期货期权 BMP 权限下，单次最多 20 个

### 示例代码

```python
from futu import *
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_market_snapshot(['HK.00700', 'US.AAPL'])
if ret == RET_OK:
    print(data)
    print(data['code'][0])
    print(data['code'].values.tolist())
else:
    print('error:', data)
quote_ctx.close()
```

### 注意事项

- 返回的 DataFrame 包含**所有字段**（通用 + 窝轮 + 期权 + 板块 + 指数 + 期货 + 基金），非相关字段为 `NaN`
- 查询期权合约行情时，先从 `get_option_chain()` 获取期权代码，再传入 `code_list`
- 对本项目而言，核心关注字段为：通用行情字段 + 期权专属字段
