# Market Dashboard

基于 Flask 的市场分析仪表盘，集成振荡统计、多资产横向比较、期权损益分析、隐含波动率曲面以及盈亏赔率评估等功能。数据来源于 Yahoo Finance，可选 SQLite 缓存；后端使用 matplotlib 生成图表，前端采用原生 JavaScript。

## 功能概览

| 标签页 | 功能说明 |
|---|---|
| **Parameter** | 配置分析参数（标的、频率、时间区间、风险阈值、偏差模式）及可选期权持仓 |
| **Market Review** | 以目标标的为锚，与 USD、US10Y、黄金、SPX、CSI300、HSI、NKY、STOXX 等全球基准横向比较收益率、波动率和相关性 |
| **Statistical Analysis** | 振荡-收益率散点图（含边际分布）、高低振荡散点图、收益率-振荡动态图（滚动分位预测）、波动率动态图（牛熊分段）、滚动相关性动态图 |
| **Assessment & Projections** | 基于历史振荡分位数的价格投影图表与明细表，期权组合到期损益图 |
| **Option Chain** | 实时 T 型期权链（IV、OI、成交量、买卖价、时间价值），支持按到期日切换 |
| **Volatility Analysis** | IV Smile、IV 期限结构、3D IV 曲面、偏度分析、OI/成交量分布、PCR 摘要、预期波动幅度和关键指标快照 |
| **Odds** | 给定目标价，计算各行权价多头看涨 / 看跌期权的盈亏赔率，按到期日分色展示 |

> 详细的公式推导与使用说明请参阅 [USER_GUIDE.md](USER_GUIDE.md)。

## 项目结构

```
app.py                 # Flask 入口，路由与调度器启动
core/                  # 核心分析逻辑
  price_dynamic.py     #   价格数据获取、频率重采样、振荡 / 收益率 / 波动率计算
  market_analyzer.py   #   散点图、动态图、投影、期权 P&L 图表生成
  market_review.py     #   多资产横向比较（收益率、波动率、相关性）
  correlation_validator.py  # 滚动相关性验证（收益率自相关 + 高低振荡相关）
  options_chain_analyzer.py # IV 曲面、偏度、OI 分布、PCR、预期波动
services/              # 请求编排层
  form_service.py      #   表单数据提取与解析
  validation_service.py#   输入校验
  analysis_service.py  #   完整分析流程编排
  market_service.py    #   标的验证 + Market Review 生成
  options_chain_service.py # Options Chain 分析编排
  chart_service.py     #   图表服务
data_pipeline/         # 数据管道（下载 → 清洗 → 加工 → 服务）
  downloader.py        #   通过 yfinance 下载 OHLCV 并写入 raw_prices
  cleaning.py          #   对齐交易日、标记异常（5σ 波动、成交量异常）、前向填充
  processing.py        #   日/周/月级聚合及衍生指标（收益率、振幅、Parkinson/GK 方差、动量等）
  data_service.py      #   数据门面：初始化 DB，按需 7 日增量刷新
  scheduler.py         #   可选 APScheduler 定时任务（每日 16:15 刷新、月度相关性刷新）
  db.py                #   SQLite 数据库操作
utils/                 # 工具函数
static/ & templates/   # 前端（原生 JS + CSS + Jinja2 模板）
tests/                 # 回归测试
```

## 数据管道

```
Yahoo Finance ──▶ downloader (upsert raw_prices)
                     │
                     ▼
              cleaning (对齐交易日, 异常标记, 前向填充)
                     │
                     ▼
              processing (多频率聚合 + 衍生指标)
                     │
                     ▼
              data_service (统一查询接口, 自动增量刷新)
```

### 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `MARKET_DB_PATH` | SQLite 数据库路径 | `./market_data.sqlite` |
| `AUTO_UPDATE_TICKERS` | 定时刷新的标的列表（逗号分隔） | 空 |
| `SCHED_TZ` | 调度器时区 | `UTC` |
| `PORT` | 服务端口 | `5000` |

### 可选：手动数据预载

```python
import datetime as dt
from data_pipeline.data_service import DataService
from data_pipeline.downloader import upsert_raw_prices
from data_pipeline.cleaning import clean_range
from data_pipeline.processing import process_frequencies

DataService.initialize()
start = dt.date.today() - dt.timedelta(days=730)
end = dt.date.today()
for t in ["AAPL", "MSFT", "SPY"]:
    upsert_raw_prices(t, start, end)
    clean_range(t, start, end)
    process_frequencies(t, start, end)
```

## 本地运行

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3.（可选）配置环境变量
cp .env.example .env   # 设置 PORT, FLASK_ENV, SECRET_KEY, LOG_LEVEL 等

# 4. 启动
python app.py
# 访问 http://localhost:5000
```

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET / POST | `/` | 主页面；POST 提交分析参数并返回完整结果 |
| GET | `/api/option_chain?ticker=AAPL` | 获取实时期权链数据（JSON） |
| POST | `/api/validate_ticker` | 校验标的代码有效性，请求体 `{ "ticker": "AAPL" }` |

### POST `/` 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `ticker` | string | 是 | Yahoo Finance 标的代码 |
| `start_time` | string | 是 | 起始月份（YYYYMM 或 YYYY-MM） |
| `end_time` | string | 否 | 结束月份，留空则至最新 |
| `frequency` | string | 否 | D / W / ME / QE，默认 ME |
| `risk_threshold` | int | 否 | 0–100，默认 90 |
| `rolling_window` | int | 否 | 滚动窗口期数，默认 120 |
| `side_bias` | string | 否 | Natural / Neutral，默认 Neutral |
| `option_position` | JSON | 否 | 期权持仓列表 |

## 技术栈

| 组件 | 技术 |
|---|---|
| 后端 | Flask 3.1, Python 3.11 |
| 数据源 | yfinance |
| 数据库 | SQLite |
| 图表 | matplotlib, Chart.js (前端 Odds) |
| 调度 | APScheduler |
| 前端 | 原生 JavaScript, CSS, Jinja2 |
| 部署 | Gunicorn / Netlify |

## 测试

```bash
python tests/test_chart_time_range.py
```

## 部署

```bash
# Gunicorn 示例
gunicorn --bind 0.0.0.0:8000 app:application
```

Netlify 配置已包含在 `netlify.toml`，使用 Python 3.11 构建。

## License

MIT License. 如有问题请提交 GitHub Issue。