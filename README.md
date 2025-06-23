# Market Observation Dashboard

A comprehensive tool for market analysis and options strategy, providing statistics on index returns and oscillations across multiple frequencies.

## Features

- **Market Analysis**: Download/process stock data from Yahoo Finance; analyze daily, weekly, monthly, and quarterly frequencies.
- **Oscillation & Returns**: Calculate price oscillations (with/without overnight effect) and returns.
- **Statistical Analysis**: Tail statistics, distribution, and volatility dynamics with rolling windows.
- **Period Segmentation**: Analyze 1Y, 3Y, 5Y, or all data.
- **Risk Threshold & Bias**: Configurable percentile for projections; choose Natural or Neutral bias.
- **Visualization**: Scatter plots, cumulative distributions, volatility, and projection charts.
- **Options Strategy**: Analyze portfolios with multiple positions; visualize P&L, breakeven, and risk.
- **UI/UX**: Fixed parameter bar, responsive design, collapsible options, and form state persistence.

## Project Structure

```
OptionStrategy/
├── app.py                # Main Flask entry, API routing
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├── core/                 # Core market analysis logic
│   ├── market_analyzer.py    # MarketAnalyzer: high-level analysis, stats, plots
│   ├── market_review.py      # market_review: multi-asset review table
│   └── price_dynamic.py      # PriceDynamic: data download, oscillation, returns
├── services/             # Service layer (business logic)
│   ├── analysis_service.py   # AnalysisService: orchestrates all analysis
│   ├── chart_service.py      # ChartService: matplotlib/seaborn to base64
│   ├── form_service.py       # FormService: form extraction, option parsing
│   ├── market_service.py     # MarketService: ticker validation, review
│   └── validation_service.py # ValidationService: input validation
├── utils/                # Utility functions
│   ├── data_utils.py         # calculate_recent_extreme_change, etc.
│   └── utils.py              # DataFormatter, helpers, constants
├── templates/            # Jinja2 HTML templates
│   └── index.html
├── static/               # CSS, JS, images
│   └── styles.css
```

## API Endpoints

- `/` (GET/POST): Main dashboard. Accepts form data, returns rendered HTML with analysis results.
    - POST参数：
        - `ticker` (str): 股票代码
        - `horizon` (str): 起始时间，格式 YYYYMM
        - `frequency` (str): 频率，D/W/ME/QE
        - `periods` (list): 分析区间 [12, 36, 60, "ALL"]
        - `risk_threshold` (int): 风险阈值百分位
        - `side_bias` (str): "Natural" 或 "Neutral"
        - `option_position` (JSON): 期权持仓列表
    - 返回：渲染后的 index.html，包含分析表格、图表、错误信息等，所有 key 统一下划线风格
- `/api/validate_ticker` (POST): Validate ticker symbol.
    - 请求体：`{"ticker": "AAPL"}`
    - 返回：`{"valid": true, "message": "valid_ticker"}`

## Key Classes & Responsibilities

- **core/price_dynamic.py**
  - `PriceDynamic`: Handles price data download, frequency conversion, oscillation/return calculation.
- **core/market_analyzer.py**
  - `MarketAnalyzer`: High-level analysis, feature engineering, visualization, projections.
- **core/market_review.py**
  - `market_review`: Multi-asset review table (returns, volatility, correlation).
- **services/analysis_service.py**
  - `AnalysisService`: Orchestrates all analysis, combines market review, stats, projections, options。
    - `generate_complete_analysis(form_data: dict) -> dict`：主分析入口，参数与前端表单字段一致，返回所有分析结果，key 统一下划线风格。
- **services/chart_service.py**
  - `ChartService`: 图表生成与 base64 编码。
    - `convert_plot_to_base64(fig)`：matplotlib 图转 base64。
- **services/form_service.py**
  - `FormService`: 表单数据提取与期权持仓解析。
    - `extract_form_data(request)`：提取表单字段，key 与前端一致。
    - `parse_option_data(request)`：解析 option_position 字段。
- **services/market_service.py**
  - `MarketService`: 市场数据校验与综述。
    - `validate_ticker(ticker)`：校验 ticker 合法性，返回 (bool, message)。
    - `generate_market_review(form_data)`：生成市场综述表。
- **services/validation_service.py**
  - `ValidationService`: 表单输入校验。
    - `validate_input_data(form_data)`：校验所有字段，返回错误信息（下划线风格）或 None。

## 命名与风格规范

- 所有 API、服务方法参数与前端字段一致（如 ticker, start_time, frequency）。
- 所有 dict 返回值 key 统一为下划线风格。
- 所有服务类静态方法均加 @staticmethod。
- 日志记录统一 logger = logging.getLogger(__name__)，异常处理风格一致。
