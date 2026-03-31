# 当前系统导航

## 文件职责速查

| 文件 | 职责 | 关键函数/类 | 直接使用 yfinance |
|---|---|---|---|
| `app.py` | Flask 路由层，所有 API 入口 | `option_chain()` L161-L276, `validate_ticker()` L279-L303, `validate_tickers_bulk()` L307-L331, `preload_option_chain()` L334-L396, `portfolio_analysis()` L398-L416, `market_review_ts()` L419-L435, `odds_with_vol()` L437-L464, `index()` L79-L160 | ✅ L168, L318 |
| `data_pipeline/downloader.py` | yfinance OHLCV 下载 + DB 写入 | `_download_yf()` L14-L28, `upsert_raw_prices()` L31-L93 | ✅ L17 |
| `data_pipeline/data_service.py` | 数据门面：下载→清洗→处理，并发限流 | `DataService` L13, `manual_update()` L19, `seed_history()` L47, `get_cleaned_daily()` L63 | ❌（委托 downloader） |
| `data_pipeline/db.py` | SQLite WAL 模式连接管理 | `init_db()` L8, `get_conn()` L59, `upsert_many()` L70, `fetch_df()` L81 | ❌ |
| `data_pipeline/cleaning.py` | 日线数据对齐/异常标记/前向填充 | `clean_range()` L32 | ❌ |
| `data_pipeline/processing.py` | 频率聚合 + 技术特征计算 | `process_frequencies()` L49 | ❌ |
| `data_pipeline/scheduler.py` | APScheduler 定时任务 | `UpdateScheduler` L13 | ❌ |
| `services/options_chain_service.py` | 期权链分析编排：建 OptionsChainAnalyzer → 生成全部图表/表格 | `OptionsChainService.generate_options_chain_analysis()` L15 | ❌（委托 core） |
| `services/market_service.py` | 验证 ticker + 市场回顾表格编排 | `MarketService.validate_ticker()` L17, `generate_market_review()` L34 | ❌（委托 core） |
| `services/analysis_service.py` | 主分析流 orchestration | `AnalysisService.generate_complete_analysis()` L10 | ❌ |
| `services/chart_service.py` | matplotlib → base64 PNG 转换 | `ChartService.convert_plot_to_base64()` L10 | ❌ |
| `services/form_service.py` | 表单字段解析 | `FormService.extract_form_data()` L12, `parse_option_data()` L55 | ❌ |
| `services/validation_service.py` | 输入校验 | `ValidationService.validate_input_data()` L7 | ❌ |
| `services/portfolio_analysis_service.py` | 组合分析：Greeks/PnL/Theta/风险/仓位 | `PortfolioAnalysisService.run()` L28, `_get_spots()` L60 | ✅ L63 |
| `core/options_chain_analyzer.py` | 实时 IV 曲面/Skew/OI/预期波动分析 | `OptionsChainAnalyzer.__init__()` L156, `get_snapshot_summary()` L201, `plot_iv_smile()` L222, `plot_iv_surface()`, `plot_skew_analysis()`, `plot_oi_volume_profile()`, `plot_pcr_summary()`, `get_expected_move_table()`, `get_key_metrics_table()` | ✅ L162 |
| `core/options_greeks.py` | 向量化 Black-Scholes Greeks | `greeks_vectorized()` L45, `portfolio_greeks_table()` L100, `theta_decay_path()` L158 | ❌ |
| `core/market_analyzer.py` | 基于 PriceDynamic 的衍生特征计算 + 图表 | `MarketAnalyzer` L47, `generate_scatter_plots()` L90 | ❌ |
| `core/market_review.py` | 多资产回顾：收益率/波动率/相关性 | `market_review()` L5, `market_review_timeseries()` L70 | ✅ L17 |
| `core/price_dynamic.py` | 价格数据下载/重频/技术特征 | `PriceDynamic` L17, `_download_data()` L83 | ✅ L91 |
| `core/correlation_validator.py` | 滚动相关性验证 | `CorrelationValidator` L35 | ❌ |
| `utils/utils.py` | 全局常量 + 日期/格式化工具 | `parse_month_str()` L19, `DateHelper` L38, `DataFormatter` L47 | ❌ |
| `utils/data_utils.py` | 趋势极值百分比计算 | `calculate_recent_extreme_change()` L3 | ❌ |

## option_chain() 路由详情
- **位置**：`app.py` L161-L276
- **输入**：`ticker` (query param)，当前无 `source` 参数
- **核心逻辑**：
  1. `yf.Ticker(ticker)` 获取对象（L183）
  2. `tkr.options` 获取到期日列表（L184）
  3. `tkr.fast_info` 获取 spot 现价（L194-L196）
  4. 遍历每个到期日 `tkr.option_chain(exp)` 获取 calls/puts DataFrame（L233）
  5. 内联 `_liquidity_score()` 计算流动性评分（L207-L228）
  6. DataFrame 逐行转 dict 列表（L237-L261）
- **返回字段**：`expirations`, `chain.{date}.calls`, `chain.{date}.puts`, `spot`
- **calls/puts 每行字段**：`strike`, `lastPrice`, `bid`, `ask`, `volume`, `openInterest`, `iv`, `itm`, `liq_score`, `liq_reason`（共10个字段）
- **yfinance 原始列**：`strike`, `lastPrice`, `bid`, `ask`, `volume`, `openInterest`, `impliedVolatility`, `inTheMoney`

## OptionsChainAnalyzer 输入格式
- **位置**：`core/options_chain_analyzer.py` L156-L197
- **输入**：`ticker: str`（默认 `"^SPX"`）
- **构造函数内部操作**：
  1. `yf.Ticker(ticker)` 创建 yfinance 对象
  2. `tk.fast_info` 获取 spot 价格
  3. `tk.options` 获取所有到期日列表
  4. 遍历到期日调用 `tk.option_chain(exp)` 获取 calls/puts DataFrame
  5. 对 DataFrame 做类型转换 + NaN 填充
- **内部存储结构**：
  - `self.spot: float` — 现价
  - `self.expiries: list` — 到期日字符串列表
  - `self.chain: dict` — `{expiry_str: {"calls": DataFrame, "puts": DataFrame}}`
- **DataFrame 列**：`strike`, `bid`, `ask`, `impliedVolatility`, `openInterest`, `volume`, `lastPrice`

## 直接使用 yfinance 的文件汇总（6个）

| # | 文件 | yfinance 用途 |
|---|---|---|
| 1 | `app.py` L168 | `option_chain()` 路由内联获取期权链 |
| 2 | `app.py` L318 | `validate_tickers_bulk()` 获取价格 |
| 3 | `core/options_chain_analyzer.py` L162 | `OptionsChainAnalyzer.__init__()` 获取 spot + chain |
| 4 | `core/market_review.py` L17 | `market_review()` 下载 OHLCV 数据 |
| 5 | `core/price_dynamic.py` L91 | `PriceDynamic._download_data()` 下载 OHLCV |
| 6 | `services/portfolio_analysis_service.py` L63 | `_get_spots()` 获取现价 |
3. **频率限制**：get_option_chain 每 30 秒最多 10 次 → 多到期日场景需限流策略
4. **US 实时行情权限**：部分动态字段可能受 futu 账户权限限制（期权元数据无此限制）
