# futu-api GitHub 导航

## 仓库根目录
- 仓库 URL：https://github.com/FutunnOpen/py-futu-api
- 分支：`master`
- 主要子目录：`/futu/`（核心库）、`/futu/examples/`（示例）

## 期权相关示例

### 无独立期权示例文件

仓库 `futu/examples/` 目录下无专门的期权示例脚本。期权相关 API 的使用方式需从以下文件及源码中提取：

- 文件：`futu/examples/quote_and_trade_demo.py`（302行）
  - 包含 API：`OpenQuoteContext` 初始化、`subscribe`、`get_market_snapshot`（注释中）、`request_history_kline`（注释中）
  - 说明：综合行情 + 交易演示，含 Handler 回调模式示例
  - URL：https://github.com/FutunnOpen/py-futu-api/blob/master/futu/examples/quote_and_trade_demo.py

- 文件：`futu/examples/get_mkt_snapshot_demo.py`（52行）
  - 包含 API：`OpenQuoteContext`、`get_stock_basicinfo`、`get_market_snapshot`
  - 说明：批量获取市场快照（按频率限制分批请求），演示了 `get_market_snapshot` 的用法
  - URL：https://github.com/FutunnOpen/py-futu-api/blob/master/futu/examples/get_mkt_snapshot_demo.py

### 源码内嵌示例（docstring）

以下方法在源码 docstring 中包含 `:example:` 代码块，可直接提取为可运行示例：

- `get_option_chain()` — 在 `futu/quote/open_quote_context.py` 中定义
- `get_option_expiration_date()` — 在 `futu/quote/open_quote_context.py` 中定义
- `get_market_snapshot()` — 在 `futu/quote/open_quote_context.py` 中定义
- `get_stock_basicinfo()` — docstring 含 `SecurityType.DRVT`（衍生品类型）示例
- `request_history_kline()` — docstring 含完整分页示例
- `subscribe()` — docstring 含订阅示例

## 连接管理示例

- 文件：`futu/examples/quote_and_trade_demo.py`
  - 说明：`OpenQuoteContext(host, port)` 创建、`set_handler()` 注册回调、`start()` / `stop()` / `close()` 生命周期管理
  - 配置示例：`SysConfig.set_init_rsa_file()`、`SysConfig.enable_proto_encrypt()`、`SysConfig.set_proto_fmt()`

- 文件：`futu/examples/get_mkt_snapshot_demo.py`
  - 说明：简洁的 `OpenQuoteContext` → 调用 → `close()` 模式

## 核心模块位置

### 行情接口（期权核心）
- `futu/quote/open_quote_context.py`（2674行）— `OpenQuoteContext` 类，包含所有行情 API 方法：
  - `get_option_chain()` — 期权链查询
  - `get_option_expiration_date()` — 期权到期日查询
  - `get_market_snapshot()` — 市场快照（含期权 Greeks 字段）
  - `request_history_kline()` — 历史 K 线
  - `subscribe()` / `unsubscribe()` — 订阅管理
- `futu/quote/quote_query.py` — 请求打包/解包逻辑
- `futu/quote/quote_response_handler.py` — 推送回调处理

### 连接管理
- `futu/common/open_context_base.py` — `OpenContextBase` 基类，Socket 连接、重连、异步消息循环
- `futu/common/conn_mng.py` — 连接管理器

### 常量与枚举
- `futu/common/constant.py` — 所有枚举定义：
  - `IndexOptionType`（NORMAL / SMALL）
  - `OptionType`（ALL / CALL / PUT）
  - `OptionCondType`（ALL / WITHIN / OUTSIDE）
  - `OptionAreaType`（AMERICAN / EUROPEAN / BERMUDA）
  - `SecurityType`（含 DRVT 衍生品类型）
  - `SubType`、`KLType`、`AuType` 等

### 其他
- `futu/common/sys_config.py` — 系统配置（加密、协议格式、RSA 密钥）
- `futu/common/utils.py` — 工具函数
- `futu/common/ft_logger.py` — 日志模块

## examples 目录完整列表
| 文件 | 说明 |
|---|---|
| `futu/examples/__init__.py` | 包初始化 |
| `futu/examples/get_mkt_snapshot_demo.py` | 批量市场快照获取 |
| `futu/examples/macd_strategy.py` | MACD 策略示例 |
| `futu/examples/quote_and_trade_demo.py` | 行情 + 交易综合演示 |
| `futu/examples/quote_push.py` | 行情推送回调示例 |
| `futu/examples/simple_filter_demo.py` | 股票筛选示例 |
| `futu/examples/stocksell_demo.py` | 股票卖出示例 |
