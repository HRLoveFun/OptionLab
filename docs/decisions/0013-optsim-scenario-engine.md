# 0013. optsim：假设头寸的 scenario engine（spot × time × IV）

- **Status**: Proposed
- **Date**: 2026-10-19（2026-10-20 追加 Web 入口）
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
加入前端标签页。

## Options Considered

1. **扩展 `core/options/simulation/expiry`** — 可复用现有入口；但其契约是单腿 + 到期 +
   European，改动会牵动 JS twin 和 Pages 构建。
2. **新建纯计算包 `core/optsim/` + CLI `scripts/optsim.py`** — 不碰现有契约，先跑通核心问题。
3. **直接做 Monte Carlo 路径模拟** — 首版不需要；确定性网格已能回答核心问题，MC 以后可以
   复用同一套 pricing / margin。

## Decision

选 **Option 2**。`core/optsim/` 只有 5 个模块：

| 模块 | 职责 |
|---|---|
| `pricing.py` | European：BSM + dividend yield q；American：CRR binomial tree（200 steps），以 European tree 为 control variate，Greeks 取自 lattice，vega 用 ±1 vol pt bump |
| `models.py` | `Market` / `Smile` / `Position`；`make_leg` 以模型价作为 entry premium；`strike_for_delta` 按 delta 选 strike |
| `margin.py` | Reg-T strategy-based（defined_risk / naked / conservative 三类）与 portfolio margin（TIMS-style 10 点 spot shock） |
| `engine.py` | `scenario_grid`：spot × day × IV shift 上的 value、P&L、Greeks、两种 margin；`time_profile`：entry spot 处逐日一行 |
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
- Strike 可直接给，或按 |Δ| 从 smile 反解，取整到约 0.1% spot 的 tick。

## Consequences

- Positive：style 和 margin regime 各一个开关；纯函数 + 测试，结果可复现；不影响现有模块。
- Negative / accepted trade-offs：
  - Margin 是近似值：没有 broker house add-on、concentration charge、TIMS vol shock 和
    class group offset；Reg-T 不检查 long leg 到期日是否晚于 short leg（reverse calendar 会被低估）。
  - 没有 skew dynamics、term structure 和 event vol；IV 只做平行移动。
  - CLI 全网格的 American 较慢：单腿 45 DTE 约 2 s，4 腿 iron condor 约 6 s，365 DTE 约 50 s；
    European 约 0.01–0.05 s。Web 路径靠上面的裁剪控制在约 1 s。
- Follow-up（按需）：variance-swap level 校准接口；MC 路径分析。

## References

- Code：`core/optsim/`、`scripts/optsim.py`、`services/options/optsim.py`、`static/optsim.js`、
  `templates/partials/tab_optsim.html`、`docs/optsim/examples/`
- Tests：`tests/test_optsim.py`、`tests/test_optsim_api.py`、`tests/unit/optsim.test.js`、
  `tests/e2e/test_optsim.py`
- Plan：[`docs/plans/optsim.md`](../plans/optsim.md)（现状、API 契约、路线图）；[`docs/plans/optsim_design.md`](../plans/optsim_design.md)（v0.3 长期设计，参考用）
- Related ADR：0008
- External：Cboe Margin Manual（strategy-based margin）；FINRA Rule 4210(g) 与 Cboe customer
  portfolio margin（OCC TIMS）
