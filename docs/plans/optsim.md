# Development Plan: optsim — 期权组合情景模拟（Position Simulator）

**Status**: 核心 + 标签页已合并（PR #19，2026-10-20，merge `b4458e9`）；ticker 模式与 break-even IV 图（2026-10-21）｜ **ADR**: [0013](../decisions/0013-optsim-scenario-engine.md)（Accepted）｜ **长期设计**: [optsim_design.md](optsim_design.md)（v0.3，参考用，不是工单）

> 给接手的开发者 / Claude Code：先读 §0，再从 §5 挑下一个 PR。§1–§4 是现状，动代码前对照；
> §6 是开工前要先问用户的问题。

---

## 0. 接力须知

### 0.1 要解决的问题

用户在搭建期权交易全流程支撑系统（交易前分析、持仓风险监测、交易后复盘）。optsim 回答的问题：
**一个多腿期权头寸的 value、position Greeks 和 margin 占用，如何随 spot、时间和 IV 变化。**
首要场景是 multi-week VRP 结构（short put / strangle、credit spread、iron condor）。

### 0.2 用户已定案的决策（不要重新讨论）

| # | 决策 | 现状 |
|---|---|---|
| 1 | European 与 American 同等重要，一键切换 | 已实现（grid） |
| 2 | 首要研究周期：multi-week VRP 结构 | 已实现：日期按周切片；MC 未做 |
| 3 | Reg-T 与 portfolio margin 同等重要，一键切换 | 已实现（grid） |
| 4 | futu bid/ask 快照延后；模拟器分析假设的期权 | 已实现：默认输入全部由用户给定；futu 仍延后，ticker 模式（#9）读的是 yfinance 当前链 |
| 5 | 作为 OptionLab 子功能 | 已实现：`core/optsim` + service + route + tab |
| 6 | VRP 校准口径：ATM IV 优先，variance-swap level 留接口 | 未实现（随 MC 一起做，§5 M4） |
| 7 | **先实现核心功能**——用户明确反馈过设计"越写越复杂" | 工作方式，见 §0.3 |
| 8 | 需要前端标签页 | 已实现：Position Simulator |
| 9 | 一个开关，让整页计算改为基于 header 的 ticker（2026-10-21） | 已实现：Market 开关（Hypothetical / Ticker），§1.4 |
| 10 | 按日期的 break-even IV 图：x 为 spot（价格 / 相对百分比两行标签），y 为 IV，多腿时每条腿分开显示（2026-10-21） | 已实现：Break-even IV by date（每腿一张小图 + 表） |
| 11 | Ticker 模式下 rate 用 13 周国库券 `^IRX`（yfinance），dividend yield = 0，margin class 按标的类型自动选（2026-10-21） | 已实现：§1.4；规则见 ADR 0013 |

### 0.3 工作方式

- **精简优先**：每个 PR 一个可验证的增量；不要一次性实现 v0.3 设计的全部内容。v0.3 是方向和参考，
  不是工单。产品层面的取舍不确定时，先问用户（§6 列了已知的问题）。
- **语言**：文档中文正文、英文术语（项目约定）；代码、注释、日志、标识符用英文（仓库约定，见 `CLAUDE.md`）。
- **流程**：每个任务一个 worktree（ADR 0009：`python scripts/worktree.py create <task>`）；
  commit 用 conventional commit 英文标题；PR 描述中文，按 `.github/PULL_REQUEST_TEMPLATE.md`，
  动了 UI 就附上 `docs/frontend_architecture.md` 末尾的 P1–P5 checklist。
- **每个 optsim PR 的完成标准**：
  - 测试：`pytest -m "not network" --ignore=tests/e2e`、`npx vitest run`（动了 JS 时）、
    `pytest tests/e2e/test_optsim.py`（动了标签页时）
  - 检查：`ruff check .`、`ruff format --check .`、`python scripts/doc_guard.py`、
    `python scripts/arch_metrics.py --check`、`python scripts/audit_tags.py`。
    ruff 0.16 的 `format` 也会检查 Markdown 里的 Python 代码块，只改文档时同样要跑
  - 文档：新模块边界 → ADR（或在 0013 追加）+ `scripts/regen_adr_index.py`；新术语 → `docs/glossary.md`；
    本文 §1（现状）和 §7（变更记录）同步更新

---

## 1. 现状（as-built）

### 1.1 代码地图

| 文件 | 职责 | 主要契约 |
|---|---|---|
| `core/optsim/pricing.py` | European：BSM + dividend yield q；American：CRR tree + European control variate，Greeks 取自 lattice，vega 用 ±1 vol pt bump；两种 style 的 implied vol | `european(kind, S, K, T, r, q, sigma)`、`american(..., steps=200)`、`option_greeks(..., style, steps)` → dict(price, delta, gamma, theta, vega)；`implied_vol(kind, price, S, K, T, r, q, style, steps)` → σ（0.5–300 vol pts 内无解为 NaN） |
| `core/optsim/models.py` | 输入数据结构；按 delta 选 strike | `Market(spot, rate, div_yield)`、`Smile(atm_iv, skew, curvature, floor).iv(K, S)`、`Position(legs, style, multiplier, product, name)`、`make_leg(..., steps)`、`strike_for_delta(kind, delta, dte, market, smile, step)` |
| `core/optsim/margin.py` | Reg-T（defined_risk / naked / conservative）与 PM（TIMS-style 10 点 spot shock）；按标的选 margin class | `PRODUCTS`、`regt_bpr(...) -> (bpr, method)`、`pm_offsets(product)`、`pm_bpr(...)`、`margin_class(symbol, instrument_type)` → `PRODUCTS` 的键 |
| `core/optsim/engine.py` | spot × day × IV shift 网格上的 value、P&L、Greeks、两种 margin；每条腿的 break-even IV | `scenario_grid(position, market, *, spot_range, n_spots, days, iv_shifts, steps) -> Grid`、`time_profile(grid, iv_shift)`、`breakevens(spots, pnl)`、`default_days(position, step)`、`breakeven_iv(position, market, spots, days, *, steps)` → 每腿 `{iv[day][spot], expiry_breakeven}` |
| `core/optsim/market.py` | ticker 模式：把期权链快照整理成上市到期日、strike、双边报价和每个到期日的 IV 曲线（纯计算） | `listed_market(ticker, spot, chain, *, today, as_of)`、`nearest_expiry(listed, dte)`、`nearest_quote(quotes, strike)`、`iv_curve(expiry, market)`（`.iv(K, S)` 与 `Smile` 同签名）、`leg_iv(kind, quote, expiry, market, curve, style, steps)` → `(iv, "mid" \| "curve")` |
| `core/optsim/charts.py` | CLI 用的 6 panel PNG（matplotlib） | `render_grid_png(grid)`、`chart_days(days, max_lines=5)` |
| `scripts/optsim.py` | CLI：TOML → 摘要 + PNG + JSON（`data/optsim/`，已 gitignore） | `python scripts/optsim.py <config.toml> [--style] [--product] [--margin] [--out]` |
| `services/options/optsim.py` | `POST /api/optsim` 的校验与 Web 网格裁剪 | `run_optsim(payload) -> dict`、`strike_tick(spot)` |
| `services/options/optsim_ticker.py` | ticker 模式的市场输入：期权链（经 `services/options/preload.py` 的缓存）、`^IRX` 利率、dividend yield 0、按类型选 margin class | `ticker_market(raw_ticker, fallback_rate) -> TickerMarket` |
| `services/market/reference_data.py` | 进程内缓存的参考数据：标的类型（1 天）、`^IRX` 无风险利率（15 分钟） | `instrument_type(symbol)`、`risk_free_rate() -> RiskFreeQuote \| None`、`clear_cache()` |
| `data_pipeline/providers/`（`base.py`、`yf_snapshot.py`） | provider seam 新增 `instrument_type()`（ADR 0011 协议表） | `MarketDataProvider.instrument_type(symbol)` → `index` / `etf` / `equity` / `other` / `None` |
| `routes/strategies.py` | 路由 `POST /api/optsim` | — |
| `templates/partials/tab_optsim.html` + `static/optsim.js` | Position Simulator 标签页（Market / Exercise / Margin 三个开关，每腿 break-even IV 小图） | `window.loadOptsimTab`、`window.runOptsim`、`window.optsimDebug` |
| `static/styles.css`（末尾 optsim 段） | 标签页样式与图表颜色 token（`--optsim-day-1..5`、`--optsim-iv-*`，两套主题） | — |
| `site/pages-shim.js` | Pages 镜像对 `/api/optsim` 返回 demo 提示 | — |
| `docs/optsim/examples/*.toml` | CLI 示例：SPX-like strangle（European）、SPY-like short put（American） | — |

Legs 复用 `core.strategies.models.Leg`（side、option_type、strike、premium、qty、dte、iv），与
`tracked_strategies` 的 `legs_json` 是同一结构。`Leg.premium` 是每股入场价，也是 P&L 基准；
`make_leg` 把它设为模型价，所以入场时 P&L 恰好为 0。

### 1.2 数据流

```text
CLI:  TOML → scripts/optsim.py::build → core.optsim.scenario_grid（全网格，200 steps）
           → summarize（stdout）+ render_grid_png + JSON → data/optsim/

Web:  tab_optsim.html / static/optsim.js
        → api.post('/api/optsim')                       （static/api.js，key 'optsim'）
        → routes/strategies.py::optsim_route
        → services/options/optsim.py::run_optsim         （校验、按 |Δ| 选 strike、网格裁剪）
            market=ticker：services/options/optsim_ticker.py
                         → services/options/preload.py   （期权链缓存，15 分钟；miss 时现取）
                         → services/market/reference_data.py（标的类型 → margin_class；^IRX → rate）
                         → core.optsim.market            （上市到期日、strike、mid / 曲线 IV）
        → core.optsim.scenario_grid × 2                  （全日期 × IV 不变；entry × IV shifts）
        → core.optsim.breakeven_iv                       （每腿，图表日期 × spot）
        → JSON → hero / KPI / Chart.js 三张图 + 每腿 break-even IV 小图 / 逐日表
```

Margin 开关只重绘（两种 margin 每次都返回）；Market 与 exercise 开关重新请求。header ticker 变化后，
ticker 模式的标签页在屏幕上就立即重算，否则下次打开时重算（两条 ticker 变化路径都会重置 `optsim` 的
tab flag）。

### 1.3 约定与单位

- 头寸层面：value、P&L 用美元；delta 用股数；gamma 用每 $1 的股数；theta 用每日历日美元；vega 用每 vol point 美元。
- 每股层面的 Greeks 与 `core/options/greeks/black_scholes.py::greeks_vectorized` 单位一致（theta 每日，vega 每 1%）。
- IV 为 sticky-strike：每条腿保留自己的 IV；IV 情景是平行 shift，下限 1 vol point。r、q 为常数，q 为连续股息率。
- Smile：`σ(K) = atm + skew·k + ½·curvature·k²`，`k = ln(K/S)`（相对 spot，不是 forward），低于 floor 截断。
- 到期后的腿按 intrinsic 计价，并退出 margin 计算。
- 两种 margin 都以 **BPR**（buying-power reduction，扣除已收 premium 后占用的资金）报告。
  PM 只在每个日期的 entry spot 处计算（11 个估值点）。
- **CLI 与 API 的单位不同**（已知不一致，§1.6）：

| 字段 | CLI TOML | `POST /api/optsim` |
|---|---|---|
| rate、div_yield、atm_iv | 小数（0.045、0.16） | 百分比（4.5、16） |
| spot 范围 | `[grid] spot_range = 0.15` | `spot_range = 15` |
| IV shift | `iv_shifts = [-0.05, 0.0, 0.05]` | `iv_shift = 5`（vol points，对称） |
| delta | 带符号（put 为 −0.16） | 绝对值 \|Δ\|（0.16，符号由 type 决定） |
| smile floor | `[smile] floor` 可配（示例 0.08） | 固定为 `Smile` 默认 0.05 |
| 每腿 IV 覆盖 | `iv = …` 可选 | 不支持显式覆盖（ticker 模式取链上 IV；§5 M3 需要） |
| 日期切片 | 全部周切片，可用 `days` 指定 | 最多 8 个等距切片（`MAX_SLICES`，步长 `max(7, ⌈最长 DTE / 8⌉)`）+ 各到期日 |
| American 树 | 200 steps | 100 steps（`WEB_TREE_STEPS`） |
| 市场来源 | 只有假设输入 | `market`：`hypothetical`（默认）或 `ticker`（+ `ticker`） |
| Ticker 模式的 rate / dividend / margin class | — | `^IRX`（取不到时用输入的 rate）/ 0 / 按标的类型 |
| ATM strike | 无 | `strike: "atm"` |

### 1.4 `POST /api/optsim` 契约

请求（JSON）：

| 字段 | 默认 | 范围 / 说明 |
|---|---|---|
| `market` | `hypothetical` | `hypothetical` / `ticker` |
| `ticker` | ticker 模式必填 | 最多 20 个字符、不含空白；按 `normalize_ticker` 规范化 |
| `spot` | 必填（hypothetical） | 0.01–1e7；ticker 模式忽略，用链上 spot |
| `rate`、`div_yield` | 4.5、0 | %；−5–50、0–20。ticker 模式：rate 只在 `^IRX` 不可用时使用，div_yield 忽略（取 0） |
| `atm_iv`、`skew`、`curvature` | 20、0、0 | atm_iv 为 %（1–300）；skew −5–5；curvature −20–50；ticker 模式忽略 |
| `style` | `european` | `european` / `american` |
| `product` | `index` | `index` / `etf` / `index_small` / `equity`（决定 Reg-T 比例与 PM 区间）；ticker 模式忽略，按标的类型选 |
| `multiplier` | 100 | 1–10000 |
| `spot_range`、`iv_shift` | 15、5 | %（5–50）；vol points（0–20，0 表示只算 IV 不变） |
| `legs` | 必填 | 1–6 条：`type`、`side`（默认 long）、`qty`（1–1000）、`dte`（1–730）、`strike`（0.2–3 × spot，或 `"atm"`）或 `delta`（\|Δ\| 0.01–0.99），二选一。ticker 模式：`dte` 换成最近的上市到期日（平手取更晚的），strike 吸附到最近的上市 strike |

响应：`status`、`market`、`style`、`product`、`multiplier`、`spot`、`tree_steps`（American 为 100，European 为 null）、
`legs[]`（解析后的 strike、iv、premium、每股 delta，以及 `expiry`、`iv_source`、`bid`、`ask`、`mid`）、
`entry_value`（负数为净 credit）、`spots`（61 个）、`days`、`chart_days`（≤ 5 个下标）、`pnl_by_day[day][spot]`、
`greeks_by_day.{delta,gamma,theta,vega}[day][spot]`、`iv_shifts`、`pnl_by_iv_at_entry[shift][spot]`、
`breakevens`（最后一个日期）、`profile[]`（entry spot 处逐日：day、value、pnl、Greeks、regt、regt_method、pm）、
`breakeven_iv`。

- `market`：hypothetical 为 `{"source": "hypothetical"}`；ticker 为 `{"source": "ticker", "ticker", "spot", "as_of"
  （链的抓取时间，UTC ISO 8601）, "atm_expiry", "atm_iv"（第一条腿到期日的 IV 曲线在 spot 处的值，小数）, "rate"（小数）,
  "rate_source"（`^IRX` 或 `input`）, "rate_as_of", "div_yield"（0）, "instrument_type"（`index` / `etf` / `equity` /
  `other` / null）, "product"（自动选出的 margin class，与顶层 `product` 相同）}`。
- `legs[]` 的 ticker 字段：`expiry`（YYYY-MM-DD）、`iv_source`（`mid` = 由该合约 mid 反解；`curve` = 没有双边报价，
  读该到期日的 IV 曲线）、`bid` / `ask` / `mid`（没有时为 null）。hypothetical 下 `expiry`、报价为 null，`iv_source` 为 `smile`。
- `breakeven_iv`：`days`（`chart_days` 对应的日期去掉 0）、`legs[]`：`iv[day][spot]`（小数；null = 0.5%–300% 内无解，
  或该腿已到期）、`at_spot[day]`（entry spot 处）、`expiry_breakeven`（`strike ± premium`）。

错误：`{"status": "error", "code", "message"}`。HTTP 400 的 code 有 `spot_required`、`legs_required`、
`too_many_legs`、`invalid_leg`、`invalid_qty`、`invalid_dte`、`invalid_strike`、`invalid_delta`、`invalid_style`、
`invalid_product`、`invalid_spot`、`invalid_rate`、`invalid_div_yield`、`invalid_iv`、`invalid_smile`、
`invalid_multiplier`、`invalid_spot_range`、`invalid_iv_shift`、`invalid_market`、`ticker_required`、`invalid_ticker`。
Ticker 模式取不到可用的链时返回 HTTP 502：`chain_unavailable`（取链失败、没有 spot、没有一天以上的到期日）、
`iv_unavailable`（某个到期日没有可用 IV）、`strike_unavailable`（该到期日没有这一类型的合约）。请求和各腿的格式校验
在取链之前完成，格式错误的请求不会触发 provider 调用；只有 strike 的取值范围（0.2–3 × spot）要等拿到链上的 spot 再校验。

### 1.5 实测性能与精度

| 场景 | 耗时 |
|---|---|
| European，任意网格 | 0.01–0.05 s |
| Web，American，1 腿 / 4 腿（45–365 DTE） | 约 0.25 s / 约 1 s |
| CLI 全网格，American，1 腿 45 DTE | 约 2 s |
| CLI 全网格，American，4 腿 45 / 120 / 365 DTE | 约 6 s / 17 s / 49 s |
| Web，ticker 模式，链已缓存，European 2–3 腿 | 约 0.03–0.05 s |
| Web，ticker 模式，American 3 腿（含 break-even IV） | 约 0.75 s |
| Web，ticker 模式，SPY 实盘链，American 2 腿，链已缓存（2026-10-21） | 约 1.3 s |
| Web，ticker 模式，链未缓存 | 再加 yfinance 取全链的时间（逐个到期日、2 个线程、每次约 2 s）；header 校验 ticker 时通常已预热 |
| Break-even IV（61 spots × ≤ 4 个日期） | European 每腿 < 0.01 s；American 每腿约 0.05–0.1 s |

American 精度（400 个随机状态，对 2000-step 树，按行权价 100 计）：100 steps 最大误差 0.018、平均 0.0027；
200 steps 最大 0.0069、平均 0.0013（put）；call ≤ 0.0003。European 与 `greeks_vectorized` 一致到 1e-10。

### 1.6 测试

| 文件 | 数量 | 覆盖 |
|---|---|---|
| `tests/test_optsim.py` | 52 | margin class 按标的类型、Reg-T cover 看到期日（calendar / reverse calendar、多腿匹配）、pricing（parity、American 界限与收敛、到期）、implied vol（两种 style 往返、无解为 NaN）、break-even IV（重新定价到 premium、随时间上升）、上市市场（到期日 / 报价解析、平手规则、IV 曲线还原已知 smile、报价 IV 回退、mid 定价）、Reg-T / PM 规则、网格不变量、style 切换、`strike_for_delta`、PNG、CLI |
| `tests/test_optsim_api.py` | 37 | route 正常路径、Reg-T 规则、American ≥ European、零 IV shift、长期限切片、18 个 400 错误用例、strike tick、`"atm"`、break-even IV 输出；ticker 模式：上市到期日 / strike / mid、ATM 与 strike 吸附、复用缓存、忽略假设输入（含股息与 margin class）、`^IRX` 利率与按类型的 margin class、`^IRX` 不可用时退回输入 rate、无报价回退、取链前校验、502 且不缓存空链 |
| `tests/test_reference_data.py` | 7 | `^IRX` 百分比转小数并缓存、缺失 / 异常 / 超范围报价为 None 且不缓存、标的类型规范化与缓存（不缓存失败） |
| `tests/unit/optsim.test.js` | 20 | 状态持久化（保存、恢复含 ticker 模式、垃圾数据与存储抛错时回退）、payload、渲染、margin 开关不重算、style 开关重算、Greek 切换、腿编辑、preset、错误态、Market 开关（锁定 / 恢复输入框、来源说明、Expiry 与 Bid / ask 列）、ticker 模式锁定 rate / dividend / margin class 且请求带输入值、`^IRX` 不可用与类型未知的说明、ticker 模式的 `"atm"`、没有 ticker 时的 empty 态、ticker 变化重算、break-even IV 小图与表 |
| `tests/e2e/test_optsim.py` | 5 | 刷新后保留腿数与开关、首次打开自动运行（含 break-even IV 小图与表）、两个开关、服务端校验错误、ticker 模式（`yf_stub` 的链；其 `^IRX` 不合理、类型未知，验证退回输入 rate 与 single stock margin） |

另外 `tests/test_provider_seam.py` 覆盖 `fetch_instrument_type` 对 yfinance quote type 的映射。

另有 `tests/unit/coverage.test.js` 导入 `static/optsim.js`，`tests/test_pages_build.py` 检查 `tab-optsim`。
测试只做已知答案比较（恒等式、规则算术、现有 BSM 实现）。Ticker 模式的 API 测试用按已知 smile 定价的合成期权链
（patch `services.options.preload.fetch_option_chain`，经过真实的 preload 缓存），e2e 用 `tests/e2e/conftest.py`
的 `yf_stub`。

### 1.7 已知限制与技术债

1. Margin 是近似：没有 broker house add-on、concentration、TIMS vol shock、class group offset。
2. ~~Reg-T 不看到期日判断 cover~~ —— 已修（2026-10-23，M1.1）：long 腿只有在到期不早于 short 时才算 cover，
   reverse calendar 按 naked short + long 计（`conservative`），long 到期后按 naked。
3. Reg-T 的 conservative 档（比例价差等混合结构）是保守近似：未被覆盖的 short 按裸卖，long 按全额。
4. PM 只在每个日期的 entry spot 处计算，不覆盖整个 spot 网格。
5. 没有 skew dynamics、term structure、event vol、离散股息（所以除息日前 American call 的提前行权没有建模）。
6. American 只做估值：不输出行权边界，网格上也没有指派。
7. CLI 与 Web 的数值有小差异（树的步数、切片、IV shift 只在 entry），以及 §1.3 的单位不一致。
8. ~~标签页输入不持久化~~ —— 已修（2026-10-23，M1.2）：legs、输入和三个开关存在 `localStorage['optsim.v1']`；
   Greek 图的选择不保存。
9. 手机宽度：`.app-body { align-items: flex-start }` 让 main panel 以内容最小宽度为下限。本标签页用
   `contain: inline-size` 处理了；Option Pricing Matrix 标签页仍有横向溢出（390 px 下页面宽约 3,100 px），
   是既有问题。
10. GitHub Pages 镜像没有后端，标签页只显示 demo 提示（两种模式都是）。
11. Ticker 模式：
    - 依赖 yfinance 当前链的质量：收盘后 bid/ask 常为 0，IV 退回链上报价的 IV（结果表里以 `*` 标出）；
      报价可能有最多 15 分钟的缓存延迟（页面显示抓取时间）。
    - 请求的 DTE 换成最近的上市到期日，calendar 的间隔可能变；不在到期日之间插值 term structure。
    - Rate 取 `^IRX`（贴现收益率按原值用，比连续复利利率低几个基点）；dividend yield 恒为 0（派息标的的
      forward 偏高，由 mid 反解的 IV 吸收）；margin class 按标的类型和名单自动选，未列出的宽基 ETF 按 `equity`
      计（偏保守），杠杆 ETF 的实际要求仍被低估。（§6 Q7，已定）
    - IV 曲线用 European 模型从 mid 反解；腿本身的 IV 按所选 style 反解。
12. Break-even IV 只按腿定义，不按头寸。深度实值、立即行权最优的 American 腿在一段 vol 上价值恒为 intrinsic，
    此时 break-even IV 不唯一，返回其中最高的一个。

---

## 2. 与 v0.3 设计的对应关系

v0.3（[optsim_design.md](optsim_design.md)）是长期设计。已实现的只是其中最小的确定性部分，且有几处有意简化：

| v0.3 设计 | 现状 |
|---|---|
| 三种模式：Grid、Monte Carlo、Program | 只有 Grid |
| 场景来源 `hypothetical` / `calibrated` / `observed`（原则 9） | `hypothetical` 与 ticker 模式；ticker 模式接近 `observed`：yfinance 当前链快照，逐个上市 strike 取 IV，不做 SSVI 拟合，也不持久化 |
| `core/optsim/` 分十几个子包，另有 `services/optsim/`、`data_pipeline/store` 的 optsim 表 | 5 个平铺模块 + `services/options/optsim.py`；无持久化 |
| American：`table` 引擎为默认，`tree` 为参考，`bs2002` 交叉检查 | 只有 `tree`（CRR + control variate） |
| 曲面：`σ(k, τ)`，k 相对 forward，skew 按 τ 幂律衰减，SSR 与时间规则 | 单一 smile，k 相对 spot，无期限结构，sticky-strike |
| product profile（`index_eu_cash` 等）一次切换 style、交割、股息、margin 类别 | `product` 只决定 margin 类别；style 单独切换 |
| variance clock、事件方差 | 日历时间；无事件 |
| `ImpliedMeasure`（ATM IV / VS level） | 未实现 |
| Reg-T 规则表（covered call、collar、杠杆 ETF 等） | defined_risk / naked / conservative 三档 |
| PM 沿路径计算、IV 冲击规则 | entry spot 处的 10 点 spot shock |
| CLI 子命令 grid / mc / sweep / compare / program | 单一命令（grid） |
| ADR 名 `0013-optsim-offline-simulation-engine.md` | 实际为 `0013-optsim-scenario-engine.md` |

扩展时按 §5 的顺序逐步靠近 v0.3，不要为对齐 v0.3 而重构现有模块。

---

## 3. 环境提示（云端沙箱）

- `.venv` 可能没有 pip：用 `uv pip install --python .venv/bin/python <pkg>`（例如 `pytest-playwright`）。
- 沙箱一般无法访问 CDN（jsdelivr、unpkg）：浏览器里 Chart.js、Alpine、HTMX 加载失败。`static/optsim.js` 仍会把
  hero / KPI / 表格写进 DOM（e2e 断言依赖这一点），但 Alpine 控制的显隐和图表不可见。本地跑 e2e 时，可以 `npm install chart.js@4 alpinejs@3.14.1 htmx.org@1.9.12
  chartjs-adapter-date-fns@3 date-fns` 到临时目录，再用一个本地 pytest 插件在 `context.route()` 里把 4 个 CDN URL
  映射到这些文件（只在本地用，不提交）。CI 能访问 CDN，不需要。
- Playwright Python 版本可能和 `/opt/pw-browsers` 里的 Chromium 版本不匹配：启动时传
  `executable_path="/opt/pw-browsers/chromium"`，或用 `PLAYWRIGHT_BROWSERS_PATH` 指向一个按期望目录结构做好符号链接的目录。
- 以 root 运行时 `tests/test_db_errors.py::test_readonly_path_raises` 会失败（root 能写只读目录），与 optsim 无关。
- 单分支 clone 推送新分支后，本地不会有 `origin/<branch>`：
  `git config --add remote.origin.fetch +refs/heads/<branch>:refs/remotes/origin/<branch>`，再 `git fetch` 并
  `git branch --set-upstream-to=origin/<branch>`。

---

## 4. 示例结果（回归参考，45 DTE，r 4.5%，q 1.3%）

| 头寸 | 入口 | 净 credit | Reg-T | PM |
|---|---|---|---|---|
| SPX-like 16Δ short strangle（S = 6000，smile atm 16% / skew −0.77 / curv 1.0 / floor 0.08），European | CLI 示例 | 6,129 | 60,500 | 13,883 |
| SPY-like 16Δ short strangle（S = 600，同 smile，floor 0.05），European | 标签页默认 | 613 | 6,050 | 1,388 |
| SPY-like 30Δ short put（584P），American | CLI 示例 | 765 | 7,400 | 2,679 |

---

## 5. 路线图（按优先级，PR 粒度）

### M1 — 小步加固（相互独立，可先做）

**M1.1 Reg-T：cover 要求 long 腿到期不早于 short 腿** —— ✅ 2026-10-23
- 改动：`core/optsim/margin.py::regt_bpr` 增加每腿 dte 参数；同类型的 long 只有在到期日 ≥ 被覆盖的 short 时才计入 cover；`engine.py` 传参。
- 验收：reverse calendar（short 60 DTE / long 30 DTE）不再是 `defined_risk`；正常 calendar 与现有测试结果不变。
- 不做：house 规则、covered call / collar。

**M1.2 标签页输入持久化** —— ✅ 2026-10-23（另外保存了 Market / Exercise / Margin 开关）
- 改动：`static/optsim.js` 把 legs 与市场输入存进一个 `localStorage` key（读写都包 try/catch，存储不可用时退化为不持久化）；首次打开先恢复，没有记录才用默认 preset。
- 验收：vitest 覆盖保存 / 恢复 / 存储抛错三种情况；e2e 刷新后腿数不变。

### M2 — 交易前分析：Monte Carlo v1（v0.3 Phase 2 的最小子集）

目标：回答"按离场规则管理，持有期内和离场时的 P&L 分布是什么样"。开工前先问用户 §6 Q1–Q2。

- **路径**：GBM，日步长，μ 默认 r − q；已实现波动率 σ_R = ATM IV − VRP（VRP 由用户声明，vol points）。
- **IV 动态**：v1 保持 sticky-strike 曲面不变（与 grid 一致）；structural IV link（v0.3 §5.6）留到后续。
- **管理规则**：止盈（credit 的 %）、止损（credit 的倍数）、DTE 离场；每日收盘检查一次。
- **估值**：European 在 paths × legs 上向量化；American 方案待定（§6 Q1）。
- **输出**：离场 P&L 分布（均值、分位数、P(P&L > 0)、VaR95 / ES95）、按日的 P&L 分位数扇形、离场原因占比、
  峰值 margin（Reg-T 全路径；PM 子样本）。style / margin 对比用 common random numbers。
- **入口**：先 CLI（`scripts/optsim.py` 增加 `mc` 子命令或 TOML `[mc]` 段），稳定后再加到标签页。
- **文件**：`core/optsim/montecarlo.py`（路径、规则、主循环）；新模块边界 → 在 ADR 0013 追加，或新开 ADR 0014。
- **验收（已知答案）**：
  - 鞅性：μ = r − q、σ_R = IV、无离场规则时，折现后的期望 value 等于入场 value（3 个标准误以内）
  - 零优势：VRP = 0 且无成本时，期望 P&L ≈ 0（3 个标准误以内）
  - 离场记账：触发后 P&L 冻结，等于触发时的 mark
  - 同一 seed 结果完全可复现
- **性能预算**：European，1 万路径 × 60 日步 × 4 腿 < 约 2 s。

### M3 — 持仓监测（v0.3 Phase 4 子集）

把 Portfolio 里的 `tracked_strategies` 载入模拟器，用当前 spot 看现有持仓的风险随时间和 spot 的变化。
ticker 模式（2026-10-21）已经提供了 spot、上市合约和链上 IV 的取数（§1.4）；M3 剩下的是载入持仓、
用实际入场价作 P&L 基准，以及按到期日期而不是 DTE 指定腿。

- **API 扩展**：legs 接受可选的 `iv`（覆盖 smile）和 `premium`（实际入场价，作为 P&L 基准，不再用模型价）。
- **数据**：dte 由 `expiry` 日期计算；spot 在 services 层取（`fetch_spots_bulk` / `DataService`），core 保持纯计算。
- **UI**：Portfolio 标签页每个持仓加 "Simulate"，或在 Position Simulator 加 "Load tracked position"（二选一，问用户）。
- **验收**：载入后 day-0 P&L = 当前 mark − 入场成本；expiry → dte 转换有单测。

### M4 — VRP 口径接口（决策 6，随 M2 一起做）

- `ImpliedMeasure` 协议：`atm_iv` 实现；`var_swap` 预留，配置为 `var_swap` 时在启动阶段明确报错，不静默回退。

### M5 — 性能：American `table` 引擎（v0.3 §5.1）

- 只在 M2 需要大量 American 路径估值时做。验收：对 tree 的价格误差 ≤ 0.005（按行权价 100 计），速度约为 European 的 2–3 倍。

### 暂不做（v0.3 Phase 3–5，等用户提出再排期）

Heston / Bates、reduced-form IV link、edge ledger / Shapley、Program 模式、Kelly 仓位、离散股息、
futu 快照与价差表、PIT 复盘、SQLite run registry 与 `.npz` 产出物。

---

## 6. 开工前要问用户的问题

1. **M2 的 American 处理**：v1 能否接受"路径上按 European 估值、不建模提前指派"，还是要先做 M5 的 `table` 引擎？
2. **离场规则默认值**：例如止盈 50% credit、止损 2× credit、21 DTE 离场，是否合适？
3. **以哪家券商的 margin 规则为准**：Reg-T 的 house add-on、PM 的 IV 冲击与最低权益要求。
4. **CLI 与 API 单位是否统一**（§1.3）：统一会改变 CLI 的 TOML 格式和示例。
5. **American 引擎是否提升为 `core/options/` 公共模块**：会影响现有 `greeks_vectorized` 的使用方，需要单独 ADR。
6. **M3 的入口**：Portfolio 里加 "Simulate"，还是在 Position Simulator 里加载持仓。
7. ~~**Ticker 模式的 dividend yield 与 margin class**~~ —— 已定（2026-10-21）：dividend yield = 0，margin class 按标的
   类型自动选，rate 用 `^IRX`（决策 11）。

---

## 7. 变更记录

| 日期 | 内容 |
|---|---|
| 2026-10-19 | 核心：`core/optsim/`、CLI、示例、ADR 0013（commit `fda7011`） |
| 2026-10-20 | Position Simulator 标签页与 `POST /api/optsim`（commit `fb32ea6`）；PR #19 合并（`b4458e9`） |
| 2026-10-20 | 本文与 v0.3 参考设计入库，供后续接力开发 |
| 2026-10-21 | Market 开关（ticker 模式：spot、上市到期日 / strike、mid 反解的 IV 来自 header ticker 的期权链）；每腿 break-even IV 图与表；`implied_vol`、`breakeven_iv`、`core/optsim/market.py`；`strike: "atm"`；preload payload 带 `fetched_at`；ADR 0013 改为 Accepted；修正与代码不一致的文档 |
| 2026-10-21 | Ticker 模式：rate 取 `^IRX`（不可用时退回输入）、dividend yield = 0、margin class 按标的类型自动选（`margin_class`）；provider seam 加 `instrument_type()`；`services/market/reference_data.py`、`services/options/optsim_ticker.py` |
| 2026-10-23 | M1.1：Reg-T cover 要求 long 腿到期不早于 short（`regt_bpr(..., dtes)`，Hall 条件匹配）；M1.2：标签页状态存进 `localStorage['optsim.v1']` |
