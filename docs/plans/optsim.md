# Development Plan: optsim — 期权组合情景模拟（Position Simulator）

**Status**: 核心 + 标签页已合并（PR #19，2026-10-20，merge `b4458e9`）｜ **ADR**: [0013](../decisions/0013-optsim-scenario-engine.md)（Proposed）｜ **长期设计**: [optsim_design.md](optsim_design.md)（v0.3，参考用，不是工单）

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
| 4 | futu bid/ask 快照延后；模拟器分析假设的期权 | 已实现：输入全部由用户给定 |
| 5 | 作为 OptionLab 子功能 | 已实现：`core/optsim` + service + route + tab |
| 6 | VRP 校准口径：ATM IV 优先，variance-swap level 留接口 | 未实现（随 MC 一起做，§5 M4） |
| 7 | **先实现核心功能**——用户明确反馈过设计"越写越复杂" | 工作方式，见 §0.3 |
| 8 | 需要前端标签页 | 已实现：Position Simulator |

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
    `python scripts/arch_metrics.py --check`、`python scripts/audit_tags.py`
  - 文档：新模块边界 → ADR（或在 0013 追加）+ `scripts/regen_adr_index.py`；新术语 → `docs/glossary.md`；
    本文 §1（现状）和 §7（变更记录）同步更新

---

## 1. 现状（as-built）

### 1.1 代码地图

| 文件 | 职责 | 主要契约 |
|---|---|---|
| `core/optsim/pricing.py` | European：BSM + dividend yield q；American：CRR tree + European control variate，Greeks 取自 lattice，vega 用 ±1 vol pt bump | `european(kind, S, K, T, r, q, sigma)`、`american(..., steps=200)`、`option_greeks(..., style, steps)` → dict(price, delta, gamma, theta, vega) |
| `core/optsim/models.py` | 输入数据结构；按 delta 选 strike | `Market(spot, rate, div_yield)`、`Smile(atm_iv, skew, curvature, floor).iv(K, S)`、`Position(legs, style, multiplier, product, name)`、`make_leg(..., steps)`、`strike_for_delta(kind, delta, dte, market, smile, step)` |
| `core/optsim/margin.py` | Reg-T（defined_risk / naked / conservative）与 PM（TIMS-style 10 点 spot shock） | `PRODUCTS`、`regt_bpr(...) -> (bpr, method)`、`pm_offsets(product)`、`pm_bpr(...)` |
| `core/optsim/engine.py` | spot × day × IV shift 网格上的 value、P&L、Greeks、两种 margin | `scenario_grid(position, market, *, spot_range, n_spots, days, iv_shifts, steps) -> Grid`、`time_profile(grid, iv_shift)`、`breakevens(spots, pnl)`、`default_days(position, step)` |
| `core/optsim/charts.py` | CLI 用的 6 panel PNG（matplotlib） | `render_grid_png(grid)`、`chart_days(days, max_lines=5)` |
| `scripts/optsim.py` | CLI：TOML → 摘要 + PNG + JSON（`data/optsim/`，已 gitignore） | `python scripts/optsim.py <config.toml> [--style] [--product] [--margin] [--out]` |
| `services/options/optsim.py` | `POST /api/optsim` 的校验与 Web 网格裁剪 | `run_optsim(payload) -> dict`、`strike_tick(spot)` |
| `routes/strategies.py` | 路由 `POST /api/optsim` | — |
| `templates/partials/tab_optsim.html` + `static/optsim.js` | Position Simulator 标签页 | `window.loadOptsimTab`、`window.runOptsim`、`window.optsimDebug` |
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
        → core.optsim.scenario_grid × 2                  （全日期 × IV 不变；entry × IV shifts）
        → JSON → hero / KPI / Chart.js 三张图 / 逐日表
```

Margin 开关只重绘（两种 margin 每次都返回）；exercise 开关重新请求。

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
| 每腿 IV 覆盖 | `iv = …` 可选 | 不支持（§5 M3 需要） |
| 日期切片 | 全部周切片，可用 `days` 指定 | 约 8 个切片（`MAX_SLICES`）+ 各到期日 |
| American 树 | 200 steps | 100 steps（`WEB_TREE_STEPS`） |

### 1.4 `POST /api/optsim` 契约

请求（JSON）：

| 字段 | 默认 | 范围 / 说明 |
|---|---|---|
| `spot` | 必填 | 0.01–1e7 |
| `rate`、`div_yield` | 4.5、0 | %；−5–50、0–20 |
| `atm_iv`、`skew`、`curvature` | 20、0、0 | atm_iv 为 %（1–300）；skew −5–5；curvature −20–50 |
| `style` | `european` | `european` / `american` |
| `product` | `index` | `index` / `etf` / `index_small` / `equity`（决定 Reg-T 比例与 PM 区间） |
| `multiplier` | 100 | 1–10000 |
| `spot_range`、`iv_shift` | 15、5 | %（5–50）；vol points（0–20，0 表示只算 IV 不变） |
| `legs` | 必填 | 1–6 条：`type`、`side`（默认 long）、`qty`（1–1000）、`dte`（1–730）、`strike`（0.2–3 × spot）或 `delta`（\|Δ\| 0.01–0.99），二选一 |

响应：`status`、`style`、`product`、`multiplier`、`spot`、`tree_steps`（American 为 100，European 为 null）、
`legs[]`（解析后的 strike、iv、premium、每股 delta）、`entry_value`（负数为净 credit）、`spots`（61 个）、
`days`、`chart_days`（≤ 5 个下标）、`pnl_by_day[day][spot]`、`greeks_by_day.{delta,gamma,theta,vega}[day][spot]`、
`iv_shifts`、`pnl_by_iv_at_entry[shift][spot]`、`breakevens`（最后一个日期）、
`profile[]`（entry spot 处逐日：day、value、pnl、Greeks、regt、regt_method、pm）。

错误：HTTP 400 + `{"status": "error", "code", "message"}`。code 有 `spot_required`、`legs_required`、
`too_many_legs`、`invalid_leg`、`invalid_qty`、`invalid_dte`、`invalid_strike`、`invalid_delta`、`invalid_style`、
`invalid_product`、`invalid_spot`、`invalid_rate`、`invalid_div_yield`、`invalid_iv`、`invalid_smile`、
`invalid_multiplier`、`invalid_spot_range`、`invalid_iv_shift`。

### 1.5 实测性能与精度

| 场景 | 耗时 |
|---|---|
| European，任意网格 | 0.01–0.05 s |
| Web，American，1 腿 / 4 腿（45–365 DTE） | 约 0.25 s / 约 1 s |
| CLI 全网格，American，1 腿 45 DTE | 约 2 s |
| CLI 全网格，American，4 腿 45 / 120 / 365 DTE | 约 6 s / 17 s / 49 s |

American 精度（400 个随机状态，对 2000-step 树，按行权价 100 计）：100 steps 最大误差 0.018、平均 0.0027；
200 steps 最大 0.0069、平均 0.0013（put）；call ≤ 0.0003。European 与 `greeks_vectorized` 一致到 1e-10。

### 1.6 测试

| 文件 | 数量 | 覆盖 |
|---|---|---|
| `tests/test_optsim.py` | 24 | pricing（parity、American 界限与收敛、到期）、Reg-T / PM 规则、网格不变量、style 切换、`strike_for_delta`、PNG、CLI |
| `tests/test_optsim_api.py` | 20 | route 正常路径、Reg-T 规则、American ≥ European、零 IV shift、长期限切片、11 种 400 错误、strike tick |
| `tests/unit/optsim.test.js` | 10 | payload、渲染、margin 开关不重算、style 开关重算、Greek 切换、腿编辑、preset、错误态 |
| `tests/e2e/test_optsim.py` | 3 | 首次打开自动运行、两个开关、服务端校验错误 |

另有 `tests/unit/coverage.test.js` 导入 `static/optsim.js`，`tests/test_pages_build.py` 检查 `tab-optsim`。
测试只做已知答案比较（恒等式、规则算术、现有 BSM 实现），不用 mock 数据。

### 1.7 已知限制与技术债

1. Margin 是近似：没有 broker house add-on、concentration、TIMS vol shock、class group offset。
2. Reg-T 按类型数腿数判断 cover，不看到期日：long 腿早于 short 腿到期（reverse calendar）会被当成 defined_risk，占用被低估。（§5 M1.1）
3. Reg-T 的 conservative 档（比例价差等混合结构）是保守近似：未被覆盖的 short 按裸卖，long 按全额。
4. PM 只在每个日期的 entry spot 处计算，不覆盖整个 spot 网格。
5. 没有 skew dynamics、term structure、event vol、离散股息（所以除息日前 American call 的提前行权没有建模）。
6. American 只做估值：不输出行权边界，网格上也没有指派。
7. CLI 与 Web 的数值有小差异（树的步数、切片、IV shift 只在 entry），以及 §1.3 的单位不一致。
8. 标签页输入不持久化，刷新后回到默认 preset。（§5 M1.2）
9. 手机宽度：`.app-body { align-items: flex-start }` 让 main panel 以内容最小宽度为下限。本标签页用
   `contain: inline-size` 处理了；Option Pricing Matrix 标签页仍有横向溢出（390 px 下页面宽约 3,100 px），
   是既有问题。
10. GitHub Pages 镜像没有后端，标签页只显示 demo 提示。

---

## 2. 与 v0.3 设计的对应关系

v0.3（[optsim_design.md](optsim_design.md)）是长期设计。已实现的只是其中最小的确定性部分，且有几处有意简化：

| v0.3 设计 | 现状 |
|---|---|
| 三种模式：Grid、Monte Carlo、Program | 只有 Grid |
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

**M1.1 Reg-T：cover 要求 long 腿到期不早于 short 腿**
- 改动：`core/optsim/margin.py::regt_bpr` 增加每腿 dte 参数；同类型的 long 只有在到期日 ≥ 被覆盖的 short 时才计入 cover；`engine.py` 传参。
- 验收：reverse calendar（short 60 DTE / long 30 DTE）不再是 `defined_risk`；正常 calendar 与现有测试结果不变。
- 不做：house 规则、covered call / collar。

**M1.2 标签页输入持久化**
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

---

## 7. 变更记录

| 日期 | 内容 |
|---|---|
| 2026-10-19 | 核心：`core/optsim/`、CLI、示例、ADR 0013（commit `fda7011`） |
| 2026-10-20 | Position Simulator 标签页与 `POST /api/optsim`（commit `fb32ea6`）；PR #19 合并（`b4458e9`） |
| 2026-10-20 | 本文与 v0.3 参考设计入库，供后续接力开发 |
