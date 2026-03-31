> 版本：v1.03 | 范围：完整业务链路（入参 → 获取数据 → 处理数据 → 可视化 → 前端）
>

---

## 目录

1. [入参（Input Parameters）](https://www.notion.so/OptionLab-32734bfbbb55800081d9deaef3766277?pvs=21)
2. [获取数据（Data Acquisition）](https://www.notion.so/OptionLab-32734bfbbb55800081d9deaef3766277?pvs=21)
3. [处理数据（Data Processing）](https://www.notion.so/OptionLab-32734bfbbb55800081d9deaef3766277?pvs=21)
4. [可视化（Visualization）](https://www.notion.so/OptionLab-32734bfbbb55800081d9deaef3766277?pvs=21)
5. [前端（Frontend）](https://www.notion.so/OptionLab-32734bfbbb55800081d9deaef3766277?pvs=21)
6. [附录](https://www.notion.so/OptionLab-32734bfbbb55800081d9deaef3766277?pvs=21)

---

## 1. 入参

### 1.1 参数清单

**Parameter Tab（主表单）**

| 参数 | 类型 | 用途分类 | 说明 |
| --- | --- | --- | --- |
| `ticker` | string | 获取数据 | 标的代码，yahoo 格式（AAPL / 0700.HK / ^SPX） |
| `start_date` | YYYY-MM | 获取数据 | Horizon 起始月份 |
| `end_date` | YYYY-MM（可选） | 获取数据 | Horizon 结束月份；留空默认最新可用期 |

**Config Tab（高级配置，localStorage 持久化）**

| 参数 | 类型 | 用途分类 | 说明 |
| --- | --- | --- | --- |
| `frequency` | enum: D / W / ME / QE | 分析处理 | 数据重采样频率（日/周/月/季） |
| `side_bias` | enum: Natural / Neutral | 分析处理 | 振荡投影方向偏差模式 |
| `risk_threshold` | int 0–100 | 分析处理 | 滚动投影百分位阈值（%），默认 90 |
| `rolling_window` | int ≥ 1 | 分析处理 | 滚动投影回看周期数，默认 120 |

> Config 参数通过 localStorage 持久化，提交时通过 hidden fields 注入主表单。

### 1.2 参数验证规则

- `ticker`：非空；格式须通过 [§6.1 正则表达式](https://claude.ai/chat/37070213-f0fa-4c24-8f2f-26b6b4bca272#61-ticker-%E6%AD%A3%E5%88%99%E8%A1%A8%E8%BE%BE%E5%BC%8F) 校验
- `start_date`：必填，格式 YYYYMM 或 YYYY-MM，可解析为月份首日
- `end_date`：可选；若填写，须 ≥ `start_date`
- `frequency`：枚举值之一
- `risk_threshold`：0 ≤ value ≤ 100
- `rolling_window`：正整数
- `side_bias`：`Natural` 或 `Neutral`

> **实现位置**：`services/validation_service.py → ValidationService.validate_input_data()utils/utils.py → parse_month_str()` 解析月份字符串
>

---

## 2. 获取数据

### 2.1 Ticker 输入设置与格式校验

### 2.1.1 Ticker 输入

| Ticker | 默认 | 输入示例 | 说明 |
| --- | --- | --- | --- |
| **yahoo 模式** | ✅ 默认 | `AAPL`, `0700.HK`, `^SPX` | 以 yfinance 标准格式输入 |

### 2.1.2 格式校验（正则表达式）

见 [§6.1 附录](https://claude.ai/chat/37070213-f0fa-4c24-8f2f-26b6b4bca272#61-ticker-%E6%AD%A3%E5%88%99%E8%A1%A8%E8%BE%BE%E5%BC%8F)。校验未通过时，前端实时展示错误提示（红色角标），阻止提交。

> **实现位置**：`utils/ticker_utils.py`；前端 `static/main.js → validateTicker()`
>

---

### 2.2 Ticker 转换与赋值

| 输入模式 | 已知量 | 转换目标 | 说明 |
| --- | --- | --- | --- |
| yahoo 模式 | `ticker_yahoo` | （唯一模式） | 直接用于 yfinance 下载与期权查询 |

**支持的市场**：US、HK
**不支持市场**：SH、SZ 等其他市场——提示用户暂不支持。

> **实现位置**：`utils/ticker_utils.py → normalize_ticker()`
>

---

### 2.3 获取量价数据（ticker_yahoo → data_pv）

### 2.3.1 下载流程

```
ticker_yahoo
    │
    ├─① 优先查询本地数据库（SQLite: clean_prices）
    │      PriceDynamic._fetch_daily_from_db()
    │      → DataService.get_cleaned_daily(ticker, start=1900-01-01, end=today)
    │      · 触发 manual_update(ticker, days=7)（60 秒冷却）
    │      · DB 有数据 → 直接使用（不做覆盖检查）
    │      · DB 无数据 → fallback yfinance
    │
    └─② yfinance fallback（仅在 DB 无数据时触发）
           PriceDynamic._download_data()
           → downloader._download_yf(ticker, start, end)
           → yf.download(ticker, start=start, end=end+1d,
                         interval='1d', auto_adjust=False)
           返回列：Open, High, Low, Close, Adj Close, Volume
           · 若 yfinance 也失败且 DB 有部分数据 → 降级使用 DB 数据
```

### 2.3.2 缓存写入（data_pv）

| 表名 | 内容 | 触发时机 |
| --- | --- | --- |
| `raw_prices` | 原始 OHLCV + provider | `upsert_raw_prices()` 增量写入 |
| `clean_prices` | 对齐到交易日、标记异常 | `clean_range()` 处理后写入 |
| `processed_prices` | 派生特征（多频率） | `process_frequencies()` 计算后写入 |
| `market_review_prices` | 基准资产收盘价 | Market Review 查询时增量 upsert |

**更新节奏**：每次访问触发 `DataService.manual_update(ticker, days=7)`（60 秒冷却）；可通过 `UpdateScheduler` 配置每日 16:15 自动更新。

> **实现位置**：`data_pipeline/data_service.py`, `downloader.py`, `cleaning.py`, `processing.py`, `scheduler.py`
>

---

### 2.4 获取期权数据（ticker_yahoo → data_option）

### 2.4.1 期权链快照（yfinance）

```
ticker_yahoo
    │
    ├─① yf.Ticker(ticker).options
    │      → expirations: tuple[str]  (格式 YYYY-MM-DD)
    │
    ├─② tkr.option_chain(exp)
    │      逐个到期日获取 calls / puts DataFrame
    │      → opt.calls, opt.puts
    │
    ├─③ tkr.fast_info → spot price
    │      last_price / regularMarketPrice
    │
    └─④ df_to_records() + _liquidity_score()
           转换为 JSON-safe records，附加流动性评分
```

**字段映射**（yfinance → 统一格式）：

| 统一字段 | yfinance 来源 | 说明 |
| --- | --- | --- |
| `strike` | `strike` | 行权价 |
| `lastPrice` | `lastPrice` | 最新成交价 |
| `volume` | `volume` | 成交量 |
| `openInterest` | `openInterest` | 未平仓量 |
| `iv` | `impliedVolatility × 100` | 隐含波动率（yfinance 返回小数，×100 转 %） |
| `itm` | `inTheMoney` | 是否价内 |
| `liq_score` | `_liquidity_score()` | GOOD / FAIR / AVOID |

### 2.4.2 期权链数据源

> **yfinance-only**：期权链数据通过 yfinance 获取，无需外部服务。
> 所有期权相关功能（Option Chain / Expiry Odds / Volatility Analysis）均使用 yfinance。

### 2.4.3 期权数据过滤（Option Filter Setting）

在 Config 页面 **Option Filter Panel** 设置，运行时加载：

| 过滤条件 | 默认值 | 说明 |
| --- | --- | --- |
| Moneyness 范围 | 70% ～ 130% spot | 只保留此范围内的行权价 |
| 到期日范围 | ≤ 60 天 | DTE 超过 60 天的合约不纳入初始分析 |

> **实现位置**：`app.py → _filter_option_chain()` + `option_chain()` 端点；`core/options_chain_analyzer.py`
>

---

## 3. 处理数据

### 3.1 量价数据重采样（Refrequency）

```
data_pv (daily OHLCV)
    │
    └─ PriceDynamic._refrequency(df, frequency)
           frequency='D' → 原始日线，补 LastClose = Close.shift(1)
           frequency='W'  → resample('W')，取 O:first, H:max, L:min, C:last, V:sum
           frequency='ME' → resample('ME')，同上
           frequency='QE' → resample('QE')，同上
           → 追加 LastClose, LastAdjClose, OpenDate, HighDate, LowDate, CloseDate
```

**Horizon 过滤**：计算始终基于**全量历史数据**，仅在输出阶段通过 `_apply_horizon()` 裁剪到 `[user_start_date, effective_end_date]`，确保滚动指标有足够前置数据。

> **注意**：QE（季度）频率不经 `data_pipeline/processing.py` 缓存到 `processed_prices` 表，而是由 `PriceDynamic._refrequency()` 实时计算。D/W/ME 三种频率会写入 `processed_prices` 用于后续查询。

> **实现位置**：`core/price_dynamic.py → PriceDynamic._refrequency() / _apply_horizon()`
>

---

### 3.2 基础价格特征计算

| 特征 | 计算公式 | 单位 |
| --- | --- | --- |
| `Oscillation`（含 on_effect） | `(max(H, LastAdjC) - min(L, LastAdjC)) / LastAdjC × 100` | % |
| `Oscillation`（不含 on_effect） | `(H - L) / LastAdjC × 100` | % |
| `Osc_high` | `(H / LastAdjC - 1) × 100` | % |
| `Osc_low` | `(L / LastAdjC - 1) × 100` | % |
| `Returns` | `(AdjC - LastAdjC) / LastAdjC × 100` | % |
| `Difference` | `AdjC - LastAdjC` | 价格单位 |
| `log_return` | `log(1 + ret_pct/100)` | — |

> **实现位置**：`core/price_dynamic.py → osc() / osc_high() / osc_low() / ret() / dif()`
全量派生特征另见：`data_pipeline/processing.py → _features()`
>

---

### 3.3 波动率计算

### 3.3.1 历史波动率（HV）

```
daily log returns = log(AdjClose_t / AdjClose_{t-1})
rolling std × √252 × 100 = 年化 HV（%）
```

| 窗口 | 对应频率 | 用途 |
| --- | --- | --- |
| 5 日 | D / W | 短期 HV |
| 21 日 | ME | 月度 HV |
| 63 日 | QE | 季度 HV |

多窗口 HV（10d / 20d / 60d / 252d）用于 HV Rank 计算：
`hv_rank = P(hv_20d_series ≤ current_hv_20d)` 过去 252 个滚动值

### 3.3.2 波动率溢价（Vol Premium）

```
vol_premium = ATM_IV / HV_20d

信号判断：
  vol_premium > 1.2 且 hv_rank > 0.5  → "Seller environment"
  vol_premium < 0.85 且 hv_rank < 0.4 → "Buyer environment"
  其他组合                             → "Neutral / watch"
```

> **实现位置**：`core/price_dynamic.py → calculate_hv_context() / build_vol_premium_context()`
>

---

### 3.4 牛熊分段

```
df['CumMax'] = Close.cummax()
df['IsBull'] = Close ≥ 0.8 × CumMax   # 从最高点回落 ≤20% 为牛市
分段输出：bull_segments, bear_segments（list of pd.Series）
```

> **实现位置**：`core/price_dynamic.py → bull_bear_plot()`
>

---

### 3.5 滚动相关性（Correlation Validation）

| 指标 | 计算方法 | 窗口 |
| --- | --- | --- |
| 收益率自相关 | `rolling_corr(log_return_t, log_return_{t-1})` | 1Y / 5Y |
| Osc_high vs Osc_low 相关 | `rolling_corr(osc_high, osc_low)` | 1Y / 5Y |

窗口换算：

| frequency | 1Y 窗口 | 5Y 窗口 |
| --- | --- | --- |
| D | 252 | 1260 |
| W | 52 | 260 |
| ME | 12 | 60 |
| QE | 4 | 20 |

最小周期：`max(10, window // 2)`；计算在全量数据上进行，Horizon 过滤仅作用于输出。

> **实现位置**：`core/correlation_validator.py`
>

---

### 3.6 滚动投影（Rolling Projections）

```
对每个时间点 i（i ≥ rolling_window）：
    historical_window = series[i-rolling_window : i]
    high_proj[i] = historical_window.quantile(risk_threshold / 100)
    low_proj[i]  = historical_window.quantile(1 - risk_threshold / 100)
```

- 投影基于**全量历史**计算，Horizon 过滤后 reindex 到显示区间
- `osc_high` → high_proj；`osc_low` → low_proj

> **实现位置**：`core/market_analyzer.py → _calculate_rolling_projections()`
>

---

### 3.7 振荡投影（Oscillation Projection）

```
proj_volatility = Oscillation.quantile(percentile)   # percentile = risk_threshold/100

Side Bias = Natural  → proj_high_weight = _calculate_natural_bias_weight()
                         · Walk-forward：70% train / 30% validation
                         · 向量化遍历 weights∈[0.3,0.7] 步长0.05
                         · 选 OOS hit rate 最高的权重
Side Bias = Neutral  → _optimize_projection_weight(target_bias=0)
                         · 遍历 weights∈[0.4,0.6] 步长0.05
                         · 选 realized_bias 最接近 0 的权重

proj_high_cur  = LastClose × (1 + proj_vol/100 × w)
proj_low_cur   = LastClose × (1 - proj_vol/100 × (1-w))
proj_high_next = Close     × (1 + proj_vol/100 × w)
proj_low_next  = Close     × (1 - proj_vol/100 × (1-w))
```

投影轨迹按平方根进度插值（模拟非线性扩散）：
`value[i] = start_price + (proj_target - start_price) × √(i/n)`

> **实现位置**：`core/market_analyzer.py → generate_oscillation_projection() / _create_oscillation_projection_plot()`
>

---

### 3.8 期权 Greeks 计算（Black-Scholes）

```
输入：S（现价）, K（行权价）, T（到期年份）, r（无风险利率=0.05）, σ（IV decimal）, option_type

d1 = (ln(S/K) + (r + σ²/2)×T) / (σ×√T)
d2 = d1 - σ×√T

Call：delta=N(d1),   theta=(-S·n(d1)·σ/(2√T) - r·K·e^{-rT}·N(d2)) / 365
Put： delta=N(d1)-1, theta=(-S·n(d1)·σ/(2√T) + r·K·e^{-rT}·N(-d2)) / 365

gamma = n(d1) / (S·σ·√T)
vega  = S·n(d1)·√T / 100
```

无效输入（T<1d, σ<0.1%, σ>2000%）输出 `np.nan`，不抛异常。

> **实现位置**：`core/options_greeks.py → greeks_vectorized()`
>

---

### 3.9 期权组合分析

| 分析项 | 计算方法 |
| --- | --- |
| Net Greeks | `portfolio_greeks_table(positions, spot)` 汇总各腿 |
| Theta 衰减路径 | `theta_decay_path()`：对每条腿向量化各剩余 DTE |
| P&L at expiry | `Σ [(intrinsic - premium) × sign × qty × 100]` 扫描价格区间 |
| 盈亏平衡点 | PnL 曲线过零点线性插值 |
| Delta-近似 VaR (1d, 95%) | `abs(delta) × S × σ_1d × z_0.95 × 100`，其中 `σ_1d = avg_iv / √252` |

> **实现位置**：`core/options_greeks.py`, `services/portfolio_analysis_service.py`
>

---

### 3.10 Put Option 决策流程（Put Selector）

```
Module 1  fetch_market_data(ticker)
               → spot, IV rank, IV percentile, term structure {dte: atm_iv}

Module 2  build_candidate_matrix(analyzer)
               → NxM 矩阵：delta ∈ [-0.25, -0.40, -0.55, -0.70]
                            DTE ∈ [21, 45, 60, 90]

Module 3  enrich_contract(contract, budget, spot, target_move_pct)
               → delta_per_dollar, payoff_at_target, total_payoff,
                  odds_ratio, vega_theta_ratio, vega_per_dollar

Module 4  compute_ev(contract, dir_conviction, vol_conviction, budget, horizon)
               → EV = P × net_if_right - (1-P) × loss_if_wrong
                  EV_ratio = EV / budget

Module 5  select_dte_range(vol_timing, horizon)
               vol_timing = FAST   → [horizon, horizon+14]
               vol_timing = MEDIUM → [horizon, horizon+30]
               vol_timing = SLOW   → [horizon+14, horizon+60]

Module 6  filter_and_rank(enriched, min_dte, max_dte)
               过滤：EV≥0, vega/theta≥2, contracts≥1
               排序：-EV_ratio, -vega_theta_ratio

Module 7  get_heuristic_notes(dir_conv, vol_conv, vol_timing, iv_rank)
               → 人类可读的决策提示列表
```

> **实现位置**：`core/option_decision.py`, `services/game_service.py`
>

---

## 4. 可视化

### 4.1 散点图 + 边缘直方图（Oscillation vs Returns）

**图表类型**：`matplotlib` 2×2 GridSpec，主图 + 上方/右侧直方图

| 元素 | 说明 |
| --- | --- |
| 主散点 | `Oscillation`（X轴）vs `Returns`（Y轴），橙色半透明点 |
| 分位线 | X/Y 轴各 4 条虚线（20/40/60/80 百分位），蓝色 |
| 高亮点 | 最近5期：蓝色；最大Osc前5：红色；两者重叠：紫色 |
| 标注 | 最近期标月份（蓝）；最大Osc期标年+月（红） |
| 边缘直方图 | 自适应 bins（步长=1，边界以 x.5 结尾） |
| 百分位标注 | 右上角：当前 Osc/Return 在历史中的百分位 |
| 统计表 | 左上角内嵌：Stronger Osc 下的 Overall / Risk 统计（#No, Freq, Ret Median） |

> **实现位置**：`core/market_analyzer.py → _create_scatter_hist_plot()`
>

---

### 4.2 高低散点图（Osc_high vs Osc_low）

与 §4.1 相同框架，X 轴改为 `Osc_low`，Y 轴改为 `Osc_high`；高亮点为 Spread (Osc_high - Osc_low) 最大的前5期。

> **实现位置**：`core/market_analyzer.py → generate_high_low_scatter()`
>

---

### 4.3 Return-Oscillation 动态图

**图表类型**：`matplotlib` 折线+散点混合，单坐标轴

| 系列 | 样式 | 说明 |
| --- | --- | --- |
| Returns | 橙色圆点（s=25） | 期收益率 |
| Osc_high | 空心紫色方块（s=40） | 当期高点振荡 |
| Osc_low | 空心蓝色方块（s=40） | 当期低点振荡 |
| High Proj | 深绿色虚线 | 基于全量历史的滚动 `risk_threshold` 分位数 |
| Low Proj | 深红色虚线 | 基于全量历史的滚动 `1-risk_threshold` 分位数 |

图例中显示投影线末端值（`*{value:.2f}`）；X 轴约每20点标注一个日期（格式 `YYMon`）。

> **实现位置**：`core/market_analyzer.py → _create_return_osc_high_low_plot()`
>

---

### 4.4 波动率动态图

**图表类型**：`matplotlib` 双 Y 轴

| 轴 | 内容 | 比例尺 |
| --- | --- | --- |
| 左 Y（黑色） | 收盘价，牛段绿色/熊段红色折线 | 对数 |
| 右 Y（蓝色） | 历史波动率滚动线（橙色）+ 当前值紫色圆点 | 线性 |

对数轴刻度：base=10，subs=[1.0, 2.0, 4.0]，格式化为逗号分隔整数。

> **实现位置**：`core/market_analyzer.py → generate_volatility_dynamics()`
>

---

### 4.5 相关性动态图（Consolidated）

**图表类型**：`matplotlib` 单坐标轴，4 条滚动相关线

| 系列 | 颜色 | 样式 |
| --- | --- | --- |
| 收益率连续相关（1Y） | 蓝色 `#1f77b4` | 实线 |
| 收益率连续相关（5Y） | 淡蓝 `#4d94d6` | 虚线 |
| High-Low 相关（1Y） | 橙色 `#ff7f0e` | 实线 + 圆点标记（每10步） |
| High-Low 相关（5Y） | 淡橙 `#ffb366` | 虚线 + 方块标记（每10步） |

Y 轴范围 [-1, 1]；0 线灰色点线参考。

> **实现位置**：`core/correlation_validator.py → generate_consolidated_correlation_chart()`
>

---

### 4.6 振荡投影图

**图表类型**：`matplotlib` 散点图，X 轴为日期序号，Y 轴为价格

| 系列 | 颜色 | 标记 |
| --- | --- | --- |
| Close | 绿色 | 实心圆 + 连线 |
| High | 紫色 | 上三角 + 连线 |
| Low | 蓝色 | 下三角 + 连线 |
| Proj High（当期） | 红色 | 空心圆（edgecolors） |
| Proj Low（当期） | 红色 | 空心圆 |
| Proj High（下期） | 橙色 | 空心圆 |
| Proj Low（下期） | 橙色 | 空心圆 |

左上角参数框：Threshold, Volatility, Bias, OOS Hit Rate, Train/Valid 周期数。

> **实现位置**：`core/market_analyzer.py → _plot_oscillation_projection()`
>

---

### 4.7 期权 P&L 图

**图表类型**：`matplotlib` 折线 + 填充

- X 轴：价格区间 [0.7×spot, 1.3×spot]，301 点
- 蓝色折线：组合总 P&L
- 绿色填充（profit zone）/ 红色填充（loss zone）
- 红色竖虚线：当前价
- 左上角统计框：Max Profit / Max Loss / Breakeven
- 右上角：组合 Greeks（delta/gamma/theta/vega），若有 dte+iv 数据

> **实现位置**：`core/market_analyzer.py → _create_option_pnl_chart()`
>

---

### 4.8 IV 分析图组（Volatility Analysis Tab）

| 子图 | 图表 | 关键元素 |
| --- | --- | --- |
| IV Smile | 折线 | Calls IV（蓝虚线）+ Puts IV（橙实线）+ ATM 竖线 + Spot 竖线 |
| IV Term Structure | 折线 + 颜色分段 | 各到期日 ATM Put IV；contango=绿，backwardation=红 |
| IV Surface | 3D 散点 | Moneyness × DTE × Put IV，颜色映射 RdYlGn_r |
| Skew Analysis | 双子图 | 上：Put Skew（OTM Put IV - ATM IV）折线；下：Risk Reversal 柱状图 |
| OI/Volume Profile | 双子图 | 左：OI 蝴蝶图（Call+/Put-）；右：Volume 蝴蝶图；标注 Max Pain 和 Spot |
| PCR Summary | 水平柱状图 | 各到期日 Vol/OI PCR，红>1.3/绿<0.7 |

> **实现位置**：`core/options_chain_analyzer.py`
>

---

### 4.9 市场回顾互动图（Market Review Chart）

**图表类型**：Chart.js `line` 图，前端渲染，时间轴

- **模式切换**：Cumulative Return（%）/ Rolling 20d Vol（%）/ Rolling 20d Correlation
- **时间窗口**：1M / 1Q / YTD / ETD（起始点归一）
- **资产显示**：主 ticker（橙色粗线）+ 8 个基准（SPX/USD/Gold/US10Y/CSI300/HSI/NKY/STOXX）
- **资产切换按钮**：每个资产对应一个 toggle 按钮，颜色与折线一致

> **实现位置**：`static/market_review_chart.js`；后端 API：`/api/market_review_ts`
>

---

### 4.10 Expiry Odds 图

**图表类型**：Chart.js `line` 图，多到期日叠加

```
Call Odd = (max(call_target - strike, 0) - ask_price) / ask_price
Put Odd  = (max(strike - put_target, 0) - bid_price) / bid_price
```

- X 轴：行权价（线性，限制在 [spot×(1±move%), ±5%] 范围内）
- Y 轴：Odd 倍数，`toFixed(1)+'x'`
- 每条到期日一种颜色（15 色循环）
- Spot 竖线：金色虚线插件（chartjs plugin）

> **实现位置**：`static/main.js → _oddsRenderCharts()`
>

---

### 4.11 图表输出格式

所有 matplotlib 图表统一以 base64 PNG 字符串返回：

```python
buffer = io.BytesIO()
fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
base64_str = base64.b64encode(buffer.getvalue()).decode()
plt.close(fig)
```

前端通过 `<img src="data:image/png;base64,{{ chart_data }}">` 渲染。

---

## 5. 前端

### 5.1 页面结构

```
site-header
    └─ 标题 + ticker/frequency/side_bias 角标

app-body
    ├─ sidebar（sticky）
    │   ├─ tab-nav（9 个 tab 按钮）
    │   └─ ticker-tab-nav（多 ticker 时显示）
    │
    └─ main-panel
        ├─ tab-parameter        # 参数输入（ticker + horizon + Position Sizing + Positions）
        ├─ tab-market-review    # 市场回顾
        ├─ tab-statistical-analysis  # 统计分析
        ├─ tab-market-assessment    # 评估与投影
        ├─ tab-option-chain     # 期权链 T 格式（自动加载，yfinance）
        ├─ tab-options-chain    # 波动率分析（yfinance）
        ├─ tab-odds             # 到期 Odds（自动加载，yfinance）
        └─ tab-config           # 高级配置（frequency / side_bias / risk / rolling）

```

---

### 5.2 Tab 导航

| Tab | 图标 | 触发条件 | 默认激活 |
| --- | --- | --- | --- |
| Parameter | `fa-sliders-h` | 始终显示 | 无分析结果时 |
| 综合（Summary） | `fa-layer-group` | 仅多 ticker 时显示 | — |
| Market Review | `fa-table` | 始终显示 | 有分析结果时 |
| Statistical Analysis | `fa-chart-scatter` | 始终显示 | — |
| Assessment & Projections | `fa-binoculars` | 始终显示 | — |
| Option Chain | `fa-th` | 始终显示（自动加载） | — |
| Volatility Analysis | `fa-link` | 始终显示 | — |
| Expiry Odds | `fa-dice` | 始终显示（自动加载） | — |
| Put Selector | `fa-crosshairs` | 始终显示 | — |
| Config | `fa-cog` | 始终显示（sidebar 末位） | — |

**自动加载行为**：
- **Market Review**：首次切换时自动触发 `loadMarketReviewChart(ticker)`
- **Option Chain**：首次切换时自动触发 `loadOptionChain()`（yfinance）
- **Expiry Odds**：首次切换时自动触发 `loadOddsData()`（yfinance）
- Ticker 变更后自动重置加载标记，下次切换时重新加载

---

### 5.3 参数表单（Parameter Tab）

### 5.3.1 主表单字段（Analysis Settings）

| 字段 | HTML 类型 | 实时行为 |
| --- | --- | --- |
| ticker | text | 500ms 防抖后调用 `/api/validate_tickers`，展示角标（valid/invalid + 价格）；valid 后自动 preload 期权链 |
| start_time / end_time | month | 联动校验（end ≥ start），展示警告条 |

> frequency / side_bias / risk_threshold / rolling_window 已移至 **Config Tab**，通过 hidden fields 注入主表单。
> "Run" 按钮位于 Analysis Settings 卡片标题右侧（内联）。

### 5.3.1a Position Sizing（始终展开）

| 字段 | 说明 |
| --- | --- |
| account_size | 账户总资金（$） |
| max_risk_pct | 单笔最大风险比例（%，0.1–20） |

> Position Sizing 和 Positions 面板不再折叠，始终展开显示。

### 5.3.2 Positions 面板

输入ticker后，后台自动获取加载对应的期权信息，映射到Positions各个对应item

```
Positions
│
├─ Table：Ticker | Type | Expiry | Strike | Side | Price | Qty | [删除]
│   · Ticker  → onPositionTickerChange()：调用 /api/preload_option_chain，填充 Expiry 下拉
│   · Type    → onPositionTypeChange()：刷新 Strike 下拉
│   · Expiry  → onPositionExpiryChange()：根据链缓存填充 Strike（含 IV% / Mid 信息）
│   · Strike  → onPositionStrikeChange()：自动填入 Mid 价格
│
├─ [Add Position] → 插入新行
└─ [组合分析] → runPortfolioAnalysis() 调用 /api/portfolio_analysis
```

**期权链缓存**：`window._chainCache[ticker]`（内存），preload 后可离线使用。

### 5.3.3 Config Tab

| 字段 | HTML 类型 | 说明 |
| --- | --- | --- |
| frequency | select | 数据重采样频率（D/W/ME/QE），默认 D |
| side_bias | select | 振荡投影方向偏差（Natural/Neutral），默认 Natural |
| risk_threshold | number | 滚动投影百分位阈值（%），默认 90 |
| rolling_window | number | 滚动投影回看周期数，默认 120 |

> 所有 Config 字段通过 `FormManager.saveConfig()` 持久化到 `localStorage['marketAnalysisConfig']`。
> 提交表单前 `syncConfigToForm()` 将值写入主表单的 hidden fields。

---

### 5.4 表单持久化（FormManager）

```jsx
FormManager.saveState()  → localStorage['marketAnalysisForm']
FormManager.loadState()  ← DOMContentLoaded 时自动恢复
FormManager.saveConfig() → localStorage['marketAnalysisConfig']
FormManager.loadConfig() ← DOMContentLoaded 时自动恢复
FormManager.syncConfigToForm() ← 表单提交前同步 Config → hidden fields

存储内容（saveState）：ticker, start_time, end_time, positions[]
存储内容（saveConfig）：frequency, side_bias, risk_threshold, rolling_window
```

日期格式标准化：存储为 `YYYYMM`，`<input type="month">` 显示为 `YYYY-MM`。

---

### 5.5 表单提交流程

```
用户点击 [Run Analysis]
    │
    ├─ FormManager.validateHorizon()：end ≥ start？
    ├─ FormManager.saveState()
    ├─ FormManager.getOptionsData() → JSON → hidden input #option_position
    ├─ 按钮改为 "Analyzing..." + disabled
    │
    └─ form.submit()（POST /）
           30s 超时后恢复按钮
```

---

### 5.6 Option Chain Tab（T 格式）

> **数据源**：yfinance
> **加载方式**：切换到此 tab 时自动加载（首次），ticker 变更后重新加载

```
自动触发 → fetch /api/option_chain?ticker=xxx
    │
    ├─ 构建到期日 subtabs（oc-exp-btn）
    └─ _ocSelectExp(exp) → _ocRenderChain(calls, puts)
           按 strike 合并 calls/puts → T 格式行
           · Calls 列（右对齐）：IV% | OI | Vol | Bid | Ask | Last | Prem%
           · Strike 列（居中）
           · Puts 列（左对齐）：Prem% | Last | Bid | Ask | Vol | OI | IV%
           · Spot 分隔行：金黄色虚线 + Spot 价格
           · ITM 行：蓝色背景高亮
           · AVOID 行：半透明 + 删除线
```

**Prem%（溢价方向）**：

- Call：`(last + strike - spot) / spot × 100`（需涨多少才回本）
- Put：`(last - strike + spot) / spot × 100`（需跌多少才回本）

---

### 5.7 Expiry Odds Tab

> **数据源**：yfinance
> **加载方式**：切换到此 tab 时自动加载（首次），ticker 变更后重新加载

```
自动触发 → fetch /api/option_chain?ticker=xxx
    │
    ├─ 用户调整 est. move（%）→ 实时重绘
    ├─ _oddsRenderCharts()
    │   ├─ 构建 Call datasets（用 ask 价格）
    │   ├─ 构建 Put datasets（用 bid 价格）
    │   └─ new Chart()（call-chart + put-chart）
    │
    └─ _oddsLoadVolContext() → POST /api/odds_with_vol
           → renderVolContextTable()：Implied RV vs ATM IV, vol ratio, signal
```

---

### 5.8 Market Review 互动图（Tab）

```
首次激活 Market Review tab → loadMarketReviewChart(ticker)
    │
    └─ POST /api/market_review_ts
           → mrData { dates, assets{prices/cum_returns/rolling_vol/rolling_corr}, periods }
           → renderMarketReviewChart()
           → renderAssetToggleButtons()

用户交互：
    · setMrMode('return'|'vol'|'corr') → 重绘
    · setMrPeriod('1M'|'1Q'|'YTD'|'ETD') → 重绘（切换起始点）
    · 资产 toggle 按钮 → mrVisibleAssets 增删 → 重绘
    · [Data Table] → 切换显示/隐藏原始统计表格
```

---

### 5.10 Market Review 表格增强（enhanceMarketReviewTable）

- **内联柱状图**：每个数值单元格下方添加 4px 色条
    - 有负值列：发散型（绿色正 / 红色负，0 为中心）
    - 纯正值列：简单正向条（紫色）
    - Last Close 列：不显示柱状图
- **可排序列头**：点击列头升序/降序排列，图标 ⇅ → ↑/↓

---

### 5.11 组合分析结果面板（Portfolio Analysis）

点击 [组合分析] 后，结果面板就地展开：

| 区块 | 内容 |
| --- | --- |
| Greeks Summary | Delta / Gamma / Theta/d / Vega/1% / Net Premium / VaR(1d,95%) 6 格网格 |
| P&L at Expiration | `<img>` 显示 base64 折线图 |
| Theta Decay Path | `<img>` 显示 base64 折线图 |
| Breakeven Points | meta-chip 标签列表 |
| Risk Metrics | VaR 数值 |

---

## 6. 附录

### 6.1 Ticker 正则表达式

### yahoo 格式

| 市场 | 正则 | 示例 |
| --- | --- | --- |
| US 股票 | `^[A-Z\-]+$` | `AAPL`, `BRK-B` |
| US 指数 | `^\^[A-Z]+$` | `^SPX`, `^VIX` |
| HK 股票 | `^\d{4,5}\.HK$` | `0700.HK`, `9988.HK` |
| 期货等 | `^[A-Z]+=F$` | `GC=F`, `CL=F` |
| 其他市场 | 不校验 | — |

### futu 格式

| 市场 | 正则 | 示例 |
| --- | --- | --- |
| US 股票 | `^US\.[A-Z.\-]+$` | `US.AAPL`, `US.BRK.B` |
| US 指数 | `^US\..[A-Z.\-]+$` | `US..SPX` |
| HK 股票 | `^HK\.\d{5}$` | `HK.00700` |
| 其他市场 | — | 提示不支持，阻止提交 |

---

### 6.2 Option Filter Setting（默认值）

| 过滤条件 | 默认值 | 可配置 |
| --- | --- | --- |
| Moneyness 下限 | 70%（0.7 × spot） | Config → Option Filter Panel |
| Moneyness 上限 | 130%（1.3 × spot） | Config → Option Filter Panel |
| 最大 DTE | 60 天 | Config → Option Filter Panel |

---

### 6.3 frequency 与窗口对照表

| frequency | 显示名 | 1Y 窗口 | 5Y 窗口 | 波动率窗口（日） | 投影 period_days |
| --- | --- | --- | --- | --- | --- |
| D | Daily | 252 | 1260 | 5 | 21 |
| W | Weekly | 52 | 260 | 5 | 5 |
| ME | Monthly | 12 | 60 | 21 | 22 |
| QE | Quarterly | 4 | 20 | 63 | 65 |

---

### 6.4 API 端点一览

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/` | POST | 主分析提交，返回完整结果页面 |
| `/api/validate_ticker` | POST | 校验单个 ticker（yahoo 格式） |
| `/api/validate_tickers` | POST | 批量校验 ticker（最多 10 个）并返回价格 |
| `/api/preload_option_chain` | POST | 预加载期权链到内存缓存 |
| `/api/option_chain` | GET | 返回完整期权链（T 格式） |
| `/api/portfolio_analysis` | POST | 组合 Greeks / P&L / Theta Decay |
| `/api/market_review_ts` | POST | 市场回顾时间序列数据 |
| `/api/odds_with_vol` | POST | Odds + Vol 上下文 |
| `/api/game` | POST | Put Selector 决策流程 |

---

### 6.5 数据库表结构摘要

| 表名 | 主键 | 核心字段 |
| --- | --- | --- |
| `raw_prices` | (ticker, date) | OHLCV, adj_close, provider |
| `clean_prices` | (ticker, date) | OHLCV, adj_close, is_trading_day, missing_any, 异常标志 |
| `processed_prices` | (ticker, date, frequency) | OHLCV, last_close, log_return, amplitude, 波动率代理, MA系列, 动量, osc_high/low/osc |
| `market_review_prices` | (ticker, date) | close — Market Review 基准资产收盘价缓存，按日期增量更新 |

数据库路径：`$MARKET_DB_PATH`，默认 `{cwd}/market_data.sqlite`；WAL 模式，5s busy_timeout。

---

*文档末尾 — 如需扩展，请按模块编号追加章节。*
