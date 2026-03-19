# futu-api 文档导航

> 源文件：`Futu-API-Doc-en-Python.md`（本地副本）
> 所有行号指向该文件内的位置

## 连接管理
- 章节：Quote Object / Create and Initialize the Connection | 行：L1090-L1143 | [has_example] | 说明：`OpenQuoteContext(host, port, is_encrypt)` 生命周期管理，含 `close()`、`start()`、`stop()`

## 订阅管理
- 章节：Subscribe and Unsubscribe / Subscribe to Real-Time Market Data | 行：L1144-L1235 | [has_example] | 说明：`subscribe(code_list, subtype_list, ...)`、`unsubscribe()`，行情订阅与取消

## Ticker 格式
- 章节：Q15：Parameter format of stock code | 行：L9522-L9540 | [no_example] | 说明：Python 格式为 `market.code`，如美股 `US.AAPL`，港股 `HK.00700`

## 期权：到期日查询
- 章节：Get Option Expiration Date | 行：L2511-L2556 | [has_example] | 说明：`get_option_expiration_date(code, index_option_type)` 查询标的所有期权到期日，返回 `strike_time`、`option_expiry_date_distance`、`expiration_cycle`

## 期权：期权链查询
- 章节：Get Option Chain | 行：L2557-L2700 | [has_example] | 说明：`get_option_chain(code, index_option_type, start, end, option_type, option_cond_type, data_filter)` 查询期权链静态信息（代码、行权价、到期日等），支持 `OptionDataFilter` 按 Greeks/OI/Volume 过滤

## 期权：行情快照
- 章节：Get Market Snapshot | 行：L1714-L1790 | [has_example] | 说明：`get_market_snapshot(code_list)` 获取市场快照，含期权专属字段：`option_type`、`strike_time`、`option_strike_price`、`option_contract_size`、`option_open_interest`、`option_implied_volatility`、`option_premium`、`option_delta/gamma/vega/theta/rho`、`option_net_open_interest`、`option_expiry_date_distance`、`option_area_type`、`option_contract_multiplier`

## 历史 K 线
- 章节：Get Historical Candlesticks | 行：L2371-L2452 | [has_example] | 说明：`request_history_kline(code, start, end, ktype, autype, fields, max_count, page_req_key, extended_time)` 获取历史 K 线，期权仅支持日线/1分/5分/15分/60分

## 枚举/类型参考
- 章节：Index Option Category (`IndexOptionType`) | 行：L4257-L4270 | [no_example] | 说明：NORMAL / SMALL
- 章节：Option Type by Exercise Time (`OptionAreaType`) | 行：L4587-L4606 | [no_example] | 说明：AMERICAN / EUROPEAN / BERMUDA
- 章节：Option in/out of The Money (`OptionCondType`) | 行：L4607-L4622 | [no_example] | 说明：ALL / WITHIN / OUTSIDE
- 章节：Option Type by Direction (`OptionType`) | 行：L4623-L4636 | [no_example] | 说明：ALL / CALL / PUT
- 章节：Option Standard Type (`OptionStandardType`) | 行：L6368-L6382 | [no_example] | 说明：STANDARD / NON_STANDARD
- 章节：Option Settlement Mode (`OptionSettlementMode`) | 行：L6384-L6396 | [no_example] | 说明：AM / PM

## Protobuf 结构参考
- 章节：Option Specific Fields of The Underlying Quote (`OptionBasicQotExData`) | 行：L6009-L6040 | [no_example] | 说明：期权行情扩展字段（strikePrice, contractSize, openInterest, impliedVolatility, Greeks 等）
- 章节：Option Additional Static Information (`OptionStaticExData`) | 行：L6156-L6200 | [no_example] | 说明：期权静态信息（type, owner, strikeTime, strikePrice, indexOptionType, expirationCycle 等）
