# 0013. optsim：假设头寸的 scenario engine（spot × time × IV）

- **Status**: Accepted（2026-10-21，核心、CLI 与标签页均已合并到 main）
- **Date**: 2026-10-19（2026-10-20 追加 Web 入口；2026-10-21 追加 ticker 模式与 break-even IV）
- **Deciders**: repo owner

## Context

下单前要回答的问题是：一个**假设的**多腿期权头寸，它的 value、position Greeks 和
margin 占用，如何随 spot、时间和 IV 变化。现有模块都不覆盖这个问题：

- `core/options/simulation/expiry`（ADR 0008）只算单腿、到期日、European、无 dividend，
  且有 `static/sim/` JS twin，要求与 Python 1e-6 parity。
- `core/strategies/` 只有到期 payoff 和 probability of profit，没有到期前的中间状态。

用户约束：European 与 American 同等重要、整个头寸一键切换；Reg-T 与 portfolio margin
同等重要、一键切换；首要场景是 multi-week VRP 结构（short put / strangle、credit spread、
iron condor）；输入是假设期权，不读行情。核心先以 CLI 交付，随后（2026-10-20）按用户要求
加入前端标签页；2026-10-21 用户又要求一个开关，让整页计算改为基于 header 的 ticker，并加一张
按日期的 break-even IV 图。

## Options Considered

1. **扩展 `core/options/simulation/expiry`** — 可复用现有入口；但其契约是单腿 + 到期 +
   European，改动会牵动 JS twin 和 Pages 构建。
2. **新建纯计算包 `core/optsim/` + CLI `scripts/optsim.py`** — 不碰现有契约，先跑通核心问题。
3. **直接做 Monte Carlo 路径模拟** — 首版不需要；确定性网格已能回答核心问题，MC 以后可以
   复用同一套 pricing / margin。

## Decision

选 **Option 2**。`core/optsim/` 共 6 个模块（`market.py` 为 2026-10-21 新增）：

| 模块 | 职责 |
|---|---|
| `pricing.py` | European：BSM + dividend yield q；American：CRR binomial tree（200 steps），以 European tree 为 control variate，Greeks 取自 lattice，vega 用 ±1 vol pt bump；`implied_vol` 在 0.5–300 vol pts 内反解两种 style |
| `models.py` | `Market` / `Smile` / `Position`；`make_leg` 以模型价作为 entry premium；`strike_for_delta` 按 delta 选 strike |
| `margin.py` | Reg-T strategy-based（defined_risk / naked / conservative 三类）与 portfolio margin（TIMS-style 10 点 spot shock）；`margin_class` 按标的的 symbol 和类型选 margin class（ticker 模式） |
| `engine.py` | `scenario_grid`：spot × day × IV shift 上的 value、P&L、Greeks、两种 margin；`time_profile`：entry spot 处逐日一行；`breakeven_iv`：每条腿在 day × spot 上的 break-even IV |
| `market.py` | ticker 模式的上市期权市场：把期权链快照整理成上市到期日、行权价、双边报价和每个到期日的 IV 曲线（纯计算，链由 services 层取） |
| `charts.py` | 一张 6 panel PNG（P&L by date、P&L under IV shifts、Delta、Gamma、Theta、Vega） |

关键约定：

- IV 为 sticky-strike，每条腿保留自己的 IV；IV 情景是平行 shift（vol points）；r、q 为常数。
- 到期后的腿按 intrinsic 计价，并退出 margin 计算。
- 两种 margin 都以 **BPR**（buying-power reduction，扣除已收 premium 之后占用的资金）报告。
- PM 只在每天的 entry spot 处计算（11 个 revaluation 点），控制 American 的计算量。
- CLI 读 TOML，打印摘要，写 PNG + JSON 到 `data/optsim/`（已 gitignore）。

**Web 入口（2026-10-20）**：Position Simulator 标签页（`templates/partials/tab_optsim.html` +
`static/optsim.js`）→ `POST /api/optsim`（`routes/strategies.py`）→ `services/options/optsim.py`
→ `core/optsim`，与 Simulation tab 的服务端路径（ADR 0008）同一分层。

- 服务端只有一份定价与 margin 逻辑，没有 JS twin；GitHub Pages 镜像没有后端，
  `site/pages-shim.js` 对该接口返回 demo 提示。
- 为保持交互，Web 网格做了裁剪：日期切片约 8 个（外加各到期日）；IV shift 只在 entry 重估；
  American 树用 100 steps（最大误差约 0.02 / 100 strike，CLI 的 200 steps 约 0.007）。
  4 腿 American 一次请求约 1 s，European 约 0.03 s。
- Margin 开关只重绘（两种 margin 每次都返回），exercise 开关重新请求。
- 标签页把 legs、输入（ticker 模式下为用户原先输入的值）和 Market / Exercise / Margin 三个开关存进一个
  localStorage key（`optsim.v1`），刷新后恢复；存储不可用时不持久化（2026-10-23）。
- Strike 可直接给、写 `"atm"`，或按 |Δ| 从 smile 反解；按 |Δ| 和 ATM 选出的 strike 取整到固定 tick 阶梯
  （$0.01–$50）中不超过 0.1% spot 的最粗一档，spot 低于 $10 时为 $0.01。

**Ticker 模式与 break-even IV（2026-10-21）**：

- 标签页在 Exercise 左边加一个 **Market** 开关：`Hypothetical`（默认，即上面的行为）/ `Ticker`。
  Ticker 模式取 header ticker 输入框的第一个 symbol（与 Option Chain 标签页一致），请求带
  `market: "ticker"` 和 `ticker`；切换会重新请求，header ticker 变化后，屏幕上的 ticker 模式标签页
  立即重算，不在屏幕上的在下次打开时重算。
- 数据：`services/options/optsim.py` 经 `services/options/preload.py` 的期权链 preload 缓存取链
  （15 分钟 TTL，miss 时现取；空链不缓存），payload 带 `fetched_at` 供页面标注时间。
  `core/optsim/market.py` 保持纯计算。
- 每条腿：DTE 换成最近的上市到期日（平手取更晚的）；strike 按 |Δ| 时在该到期日的 IV 曲线上反解，
  再吸附到最近的上市 strike，直接给的 strike 和 `"atm"` 同样吸附；IV 取该合约自己的 mid 反解
  （与 exercise style 一致的模型），没有双边报价时读该到期日的 IV 曲线。IV 曲线在每个上市 strike
  取 OTM 一侧（spot 以下用 put，以上用 call）的 mid 反解 IV（European），没有双边报价时用链上报价的 IV，
  strike 之间线性插值、两端外推为常数。Premium 是该 IV 下的模型价（有 mid 时就等于 mid），
  所以入场 P&L 仍为 0。
- Rate、dividend yield 和 margin class（用户 2026-10-21 定案）：Ticker 模式下 rate 取 13 周国库券
  `^IRX`（yfinance，以百分比报价，原值当作年化利率使用，缓存 15 分钟；取不到或超出 −5%–50% 时退回请求里
  输入的 rate，并在响应的 `rate_source` 标明）；dividend yield 取 0；margin class 按标的类型自动选
  （`core/optsim/margin.py::margin_class`）：高市值宽基指数（SPX、XSP、NDX、DJX、OEX 等）及跟踪它们的 ETF
  （SPY、IVV、VOO、QQQ、DIA 等）用 `index` / `etf`，其他宽基 ETF（IWM、MDY、IJH、IJR）和其余指数用
  `index_small`，其余 ETF（行业、杠杆、单一国家）、个股和类型未知的标的用最保守的 `equity`——窄基 ETF
  的期权按个股要求计保证金。标的类型经 provider seam 新增的 `instrument_type()` 取（ADR 0011 的协议表已补），
  由 `services/market/reference_data.py` 缓存一天。Hypothetical 模式下这三项仍取自输入。
  Ticker 模式下 Spot、Rate、Dividend、Margin class、ATM IV 输入框只读显示服务端用的值（请求仍带输入值，
  rate 作 `^IRX` 的后备），Skew、Curvature 不使用。
- **Break-even IV**：每条腿单独计算，即在之后某天、某个 spot 下，使该腿价值仍等于入场 premium 的 IV。
  日期取 "P&L by date" 图的日期（去掉 entry），spot 用同一网格，rate、dividend yield、style 与页面一致；
  搜索区间 0.5%–300%，区间内无解记为空。到期日价值只剩 intrinsic，没有 IV 曲线，用到期盈亏平衡点
  `K ± premium` 的竖线表示。组合层面不定义：多空混合的头寸没有一个统一的 IV 能回答这个问题。
  American 的反解从 European 解向下做 safeguarded secant，再用 bisection 收尾。

## Consequences

- Positive：style 和 margin regime 各一个开关；纯函数 + 测试，结果可复现；不影响现有模块。
- Negative / accepted trade-offs：
  - Margin 是近似值：没有 broker house add-on、concentration charge、TIMS vol shock 和
    class group offset。Reg-T 只把到期不早于 short 的同类型 long 算作 cover（2026-10-23 起；之前 reverse
    calendar 被当成 defined_risk，占用被低估）。
  - 没有 skew dynamics、term structure 和 event vol；IV 只做平行移动。
  - CLI 全网格的 American 较慢：单腿 45 DTE 约 2 s，4 腿 iron condor 约 6 s，4 腿 365 DTE 约 50 s；
    European 约 0.01–0.05 s。Web 路径靠上面的裁剪控制在约 1 s（break-even IV 另加每腿约 0.1 s）。
  - Ticker 模式依赖 yfinance 期权链的质量：收盘后 bid/ask 常为 0，这时 IV 退回链上报价的 IV；
    报价可能有最多 15 分钟的缓存延迟；请求的 DTE 会被换成上市到期日（calendar 的间隔可能变）；
    不在到期日之间插值 term structure。
  - 深度实值、立即行权最优的 American 腿，价值在一段 vol 上恒为 intrinsic，break-even IV 不唯一，
    反解返回其中最高的一个。
  - `^IRX` 是贴现收益率，按原值当连续复利利率用，比模型假设的利率低几个基点（4% 水平约 5–10 bp）。
  - Ticker 模式的 dividend yield 恒为 0：对派息标的，call 估值偏高、put 偏低（forward 偏高），
    mid 反解出的 IV 会吸收这部分差异；Hypothetical 模式可手填股息。
  - Margin class 的名单是有限的：未列出的宽基 ETF 按 `equity` 计，保证金偏保守；杠杆 ETF 的实际要求
    （按杠杆倍数放大）高于任何一档，仍被低估。
- Follow-up（按需）：variance-swap level 校准接口；MC 路径分析。

## References

- Code：`core/optsim/`（含 `market.py`）、`scripts/optsim.py`、`services/options/optsim.py`、
  `services/options/optsim_ticker.py`（ticker 模式的市场输入）、`services/options/preload.py`（期权链缓存）、
  `services/market/reference_data.py`（标的类型与 `^IRX` 缓存）、`data_pipeline/providers/`（`instrument_type()`）、
  `static/optsim.js`、`templates/partials/tab_optsim.html`、`docs/optsim/examples/`
- Tests：`tests/test_optsim.py`、`tests/test_optsim_api.py`、`tests/test_reference_data.py`、
  `tests/test_provider_seam.py`（`fetch_instrument_type`）、`tests/unit/optsim.test.js`、`tests/e2e/test_optsim.py`
- Plan：[`docs/plans/optsim.md`](../plans/optsim.md)（现状、API 契约、路线图）；[`docs/plans/optsim_design.md`](../plans/optsim_design.md)（v0.3 长期设计，参考用）
- Related ADR：0008；0011（provider seam：2026-10-21 加 `instrument_type()`）
- External：Cboe Margin Manual（strategy-based margin）；FINRA Rule 4210(g) 与 Cboe customer
  portfolio margin（OCC TIMS）
