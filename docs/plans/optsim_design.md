# optsim — 期权组合模拟器（Option Portfolio Simulator）

**架构与功能设计 · v0.3 · 暂不含 UI**

- 归属：OptionLab（`HRLoveFun/OptionLab`）子功能；2026-10-19；取代 v0.2
- 仓库位置：`docs/plans/optsim_design.md`（2026-10-20 入库）；现状与下一步见 [optsim.md](optsim.md)
- v0.3 处理了一份计划审查报告的 6 条意见：采纳 4 条，另 2 条修正前提或部分采纳（§11.3）

> **状态（2026-10-20）**：本文是长期设计，**不是现状，也不是工单**。已实现的只是最小的确定性部分：
> §5.1 的 European / American 估值（只有 `tree` 引擎）、§5.8 的 Reg-T / PM（简化版）、Grid 模式，
> 以 `core/optsim/`、CLI `scripts/optsim.py` 和 Position Simulator 标签页（`POST /api/optsim`）交付。
> 实现与本文的差异见 [optsim.md](optsim.md) §2，下一步见 [optsim.md](optsim.md) §5。
> 用户明确要求先实现核心、避免过度设计：按 optsim.md 的顺序增量推进，不要一次实现本文全部内容，
> 也不要为了对齐本文去重构已实现的模块。

> **核心问题**：一个多腿期权组合的**价值**与**风险**，如何随时间推移和市场变动而演化——既看确定性的 what-if 网格，也看模拟路径上的分布？

---

## 0. 摘要

- **三种运行模式**
    1. **Grid**：在 spot × 日期 × IV 上做 full revaluation，输出不同时间切片的 risk graph、Greeks 曲线、压力表和两种保证金。
    2. **Monte Carlo**：在显式的 real-world 模型下联合模拟 spot 与 IV 曲面，输出 P&L 分布随时间的演化、路径风险、对冲/离场/行权策略、成本、归因。
    3. **Program**：在长路径上按规则滚动开仓，输出无条件策略的权益曲线、回撤与资金占用。这是多周 VRP 结构研究的主模式。
- **已定案的 6 项决策**（v0.2）

| # | 决策 | 结论 | 设计落点 |
|---|---|---|---|
| 1 | 行权方式 | European 与 American 同等重要，一键切换 | `style` 开关 + `compare`（§5.1） |
| 2 | 首要研究周期 | 多周 VRP 结构 | 日频步长；Program 模式提前；intraday 延后（§5.4、§10） |
| 3 | 保证金制度 | Reg-T 与 portfolio margin 同等重要，一键切换 | `margin.model` 开关，默认并列计算（§5.8） |
| 4 | futu 买卖价快照 | 延后；模拟器针对假设期权分析 | `MarketScenario` 完全参数化；spread 参数化（§3.1、§5.7） |
| 5 | 存储 | 作为 OptionLab 子功能 | `core/optsim` + `services/optsim` + SQLite + `.npz`；CLI 离线运行（§4） |
| 6 | VRP 校准口径 | ATM IV 优先，variance-swap level 留接口 | `ImpliedMeasure` 协议（§5.6） |

- **Edge in, edge out**：模型完备的模拟器发现不了优势，它只是把**声明的**溢价转换成策略 P&L。每个溢价因子都有精确的关闭态（§5.11）；每次 Monte Carlo 都附带共同随机数下的对照组、按因子拆分的 edge ledger、单列的「未声明残差」，以及扣除成本后的盈亏平衡溢价。
- **v0.3 的主要变化**
    - Phase 1 拆为 1a（European 基线）与 1b（American 增量），更早得到可验证的 European 基线。
    - American 的估值与行权决策分开：默认估值引擎改为 `table`（由 tree 一次构建、按状态查表）；行权与指派一律按 tree 算出的边界表判定，不再用 BS2002。
    - 性能预算分 European、American、American + PM 三档。
    - 四个溢价因子（drift、variance、skew_dynamic、skew_static）逐一给出关闭态；ledger 增加残差行。
    - Structural IV 联动写成显式不动点并加参数域校验；VRP 区分「积分方差」与「估计量」两个口径；事件方差只计一次（v0.2 重复计入）。
    - 指标存储改为规范化的多表结构，variant、时间序列、配对差值各有一张表。
- **设计期验算的关键发现**（§8）
    - BS2002 的行权边界比真实边界高 0.45%–5.7%。用它判定指派会让 short put 过早被指派，P&L 偏乐观；这与审查报告推测的「低估尾部指派」方向相反，但同样说明 BS2002 不能用于决策。
    - `table` 引擎：构建 1.9 秒（33 个 σ × 90 天），单次查表约为 European 的 2.2 倍；在 400 个随机状态上最大误差 0.0028（按行权价 100 计），BS2002 为 0.16；边界误差在 ±0.22% 以内。
    - 同一个 SPX-like 16Δ short strangle，Reg-T 现金占用 60,000 美元，PM 为 13,731 美元（4.4 倍）。
    - 默认假设曲面下，30 天 variance-swap level 比 ATM IV 高约 3 vol points；文献中 VS 口径的 VRP 不能直接当作 ATM 口径的默认值。
    - 21 个交易日 close-to-close 已实现波动率估计量自身有偏：GBM（16%）下 −0.19 vol points，Heston（ξ = 0.6）下 −0.78 vol points。这与 VRP 本身同一量级，所以 VRP 必须注明估计量口径。

---

## 1. 目的与范围

### 1.1 要回答的问题

| 阶段 | 问题 | 关键输出 | 版本 |
|---|---|---|---|
| 交易前（假设场景） | P&L 和风险在整个持有期如何演化？需要多大的溢价才能覆盖成本和尾部？American 与 European、Reg-T 与 PM 各差多少？仓位多大？ | 随时间的 risk graph、MC 分布、盈亏平衡溢价、style/margin 对比、Kelly 仓位 | v0.2 主线 |
| 持仓监测 | 现在的风险是多少？明天、周末后、事件后、价格不动时呢？在哪里会失效？ | Greeks、decay 投影、压力网格、两种保证金 | 后续（Phase 4） |
| 交易后复盘 | 是优势还是运气？P&L 来自哪里？模拟器本身是否校准？ | 归因（implied vs realized）、相对交易前分布的 PIT | 后续（Phase 4） |

### 1.2 非目标

- 不生成信号，不做入场择时优化。
- 不验证微观结构效应（开盘 IV 在 mid 上的错位、成交概率、逆向选择）。它们只能作为参数进入，参数待买卖价数据采集恢复后估计。
- 不下单，不写入任何券商系统。
- v0.2 不做 UI；Monte Carlo 不在 HTTP 请求内运行（OptionLab constraints 第 6 节：计算必须在一个请求内完成，且没有后台任务队列）。
- 不依赖期权历史数据。OptionLab 通过 yfinance 拿不到期权链历史（ADR 0004），所以 optsim 的输入是假设场景，而不是历史期权价格。
- 研究对象不等于可交易清单。学习期宪章 v1.2 第 3 节目前只允许单腿 long，卖方 VRP 结构属于研究范畴；每份报告都标注宪章状态（F14）。

---

## 2. 设计原则

1. **Q 定价，P 生成路径**：头寸始终用定价模型在（模拟的）IV 曲面上估值；spot 和方差路径来自 real-world 模型。溢价存在于两者的差距中，所以这个差距是显式命名的参数，绝不是模型选择的副产品。
2. **Edge in, edge out**：每份 MC 报告都包含共同随机数下的零溢价对照组、按溢价拆分 EV 的 edge ledger、EV 对每种溢价的曲线及其盈亏平衡值。无法追溯到某个声明溢价的 EV 不得被吸收进其他项：它在 ledger 中单列为「未声明残差」（§5.11）；残差显著不为零，说明场景曲面与 P 过程不一致，必须解释或声明。
3. **风险用 full revaluation，Taylor 展开只用于解释**：网格和路径全部重新定价；Greeks 展开只用于归因，并始终给出显式残差。
4. **Greeks 依赖动力学假设**：Delta 和 vega 取决于曲面如何随 spot 和时间移动，所以每个 Greek 都注明它采用的规则——固定 IV 的 *model* Greeks，或与动力学一致的 *effective* Greeks。
5. **两类不确定性**：过程不确定性（给定参数下的路径随机性）和参数不确定性（未知的 VRP、跳跃强度、SSR）都要模拟；参数按批次从先验分布抽取。Mack & Sinclair（2024）第 2 章做了同样的区分，第 19 章演示了带参数不确定性的 Monte Carlo。
6. **按可成交价格，而不是 mid**：每个 P&L 都同时给出 mid 估值和可成交价格两个版本；成本同时换算成 vol points，与要收割的溢价放在同一尺度上。
7. **单一职责，产出物命名即接口**：每个阶段都是「类型化配置 + 命名输入产出物」的纯函数，只写一个命名输出。代码分层严格遵守 OptionLab 的单向依赖（§4.1）。配置 + seed + 代码版本即可精确复现任一次运行。
8. **验证优先**：一个模型只有连同它的已知答案测试和证伪测试一起，才能进入默认流程（§8）。
9. **假设优先（hypothetical-first）**：所有输入都可以完全由参数给定。场景来源（`hypothetical` / `calibrated` / `observed`）随结果一起存储并在报告中显示。假设场景是显式的模型输入，不是替代真实行情的 mock 数据，也永远不写入 OptionLab 的行情表。
10. **一键切换 = 单一配置键 + 配对比较**：切换只改变被切换的那个维度（例如 `style` 只改变行权权利），其他输入和随机数保持不变；`compare` 模式在同一组随机数上并列输出两个版本及其差值。

---

## 3. 变量体系

组合在时刻 `t` 的价值：

```text
V(t) = Σ_i n_i·m_i·P_i(S, τ_i, σ_i, r, q; K_i, type_i, style_i)
       + h·S + C

τ_i = T_i − t             剩余期限（两种时钟，§5.4）
σ_i = Σ(k_i, τ_i; f)      曲面在因子 f 下给出的腿 IV
k_i = ln(K_i / F(T_i))    相对远期的 log-moneyness
```

`n_i` 是带符号的数量，`m_i` 是合约乘数，`style_i` 是行权方式；`h` 是标的持仓（对冲，以及 American 实物交割被指派后形成的股票头寸），`C` 是现金（权利金、成本、融资、行权现金流）。所有**输入**都是这个函数的自变量；所有**输出**都是它的泛函——在网格上、随时间、或跨路径。

```text
自变量（输入）                       因变量（输出）
A 合约结构   --+                 +--> E 估值
B 市场场景   --+                 +--> F 敏感度
C 动力学     --+---- V(t) ------+--> G 情景网格
D 管理与执行 --+                 +--> H 分布与路径
                                 +--> I 优势与模型风险
```

### 3.1 自变量（输入）

**A. 合约结构**：入场时确定，是决策变量

| 变量 | 说明 |
|---|---|
| 工具 | call、put、标的、期货 |
| 带符号数量 `n` | 允许比例结构 |
| 行权价 `K` | 绝对值，或入场时按 delta / moneyness 选取 |
| 到期 `T` | 绝对日期，或按 DTE 选取 |
| **行权方式 `style`** | `european` / `american`；一键切换（§5.1） |
| 交割方式 | `cash` / `physical`；AM 或 PM 结算（SPX vs SPXW） |
| 产品类别 | `broad_index` / `broad_etf` / `narrow_index` / `equity`，外加杠杆倍数；决定 Reg-T 比例与 PM 区间 |
| 合约乘数 `m`、最小报价单位 | 例如 100；0.01 / 0.05 |
| 股息 | 连续股息率 `q`，或离散股息表（Phase 3） |
| 入场价格 / IV | 由场景曲面给出；mid 或可成交价 |

一个策略是**规则**而不是一组合约：「卖 16Δ put，45 DTE」在每次入场时对着当时的曲面解析成具体合约。无条件 Program 和公平比较都依赖这一点。

**产品族预设（product profile）**：一次切换多个相关属性

| profile | 原型 | style | 交割 | 股息 | Reg-T 类别 | PM 区间 |
|---|---|---|---|---|---|---|
| `index_eu_cash` | SPX | european | cash | 隐含于远期 | broad_index（15%） | −8% / +6% |
| `etf_am_phys` | SPY | american | physical | 连续 `q`（离散：Phase 3） | broad_etf（15%） | −8% / +6% |
| `equity_am_phys` | 大盘个股 | american | physical | 连续 `q` | equity（20%） | ±15% |
| `custom` | 任意 | 任意 | 任意 | 任意 | 任意 | 任意 |

PM 区间按标的所跟踪的指数决定：SPY、QQQ 这类高市值 broad-based 用 −8% / +6%；IWM 这类非高市值 broad-based 用 ±10%。

**B. 市场场景（`MarketScenario`）**：任意时刻的估值自变量，v0.2 全部由参数给定

| 变量 | 说明 |
|---|---|
| Spot `S`、远期 `F` | `F` 由 `S`、`r`、`q`（或离散股息）导出；两种 style 共用同一个远期 |
| 估值时间 `t` | 决定每条腿的 `τ` |
| IV 曲面 `Σ(k, τ; f)` | 用小因子向量 `f` 表示（见下表） |
| 利率 `r(τ)` | 贴现、carry |
| 股息、借券成本 `q` | 连续或离散；影响提前行权 |
| 流动性参数 | 参数化 half-spread（§5.7） |
| 事件日历 | FOMC、CPI、财报：额外方差（§5.3） |
| Regime 标签（可选） | 来自 OptionLab 的 `regime_log`（VIX × SPY 20 日斜率） |
| 来源标签 | `hypothetical`（默认）、`calibrated`、`observed` |

| 曲面因子 | 含义 |
|---|---|
| `σ_ATM(τ)` | ATM 水平与期限结构形状 |
| `β(τ)` | ATM skew `∂σ/∂k`；幂律 `β_ref·(τ/τ_ref)^(−α)`，α ≈ 0.4 |
| `γ(τ)` | smile 曲率 |

本文验算使用的默认假设曲面：`σ_ATM` 16%（期限结构平坦），`β_ref` −0.9（τ_ref = 30 天），α = 0.4，γ = 1.0，wing 截断在 `[0.5, 3] × σ_ATM`。这是假设参数，不是校准结果。

**C. 动力学**：B 在 real-world 测度 P 下如何演化

| 组 | 参数 | 为什么重要 |
|---|---|---|
| Drift | `μ`；默认 `r − q` | 方向性溢价，默认关闭 |
| 方差 | `σ_R`，或方差过程：Heston（κ, θ, ξ, ρ, v₀）、rough Bergomi（H, η, ρ, ξ₀(·)） | gamma 收益的来源 |
| 跳跃 / 跳空 | 强度 λ、跳幅分布、隔夜跳空分布 | 尾部 |
| IV–RV 联动 | VRP 及其动态；**口径默认 ATM IV** | 声明的溢价（§5.6） |
| 曲面动力学 | 实现与定价的 SSR、时间规则、事件方差 | 曲面如何移动（§5.3） |
| IV 噪声 | vol-of-IV η、均值回复 κ_σ | 与 spot 无关的 IV 变化 |
| 先验 | 以上全部参数的分布 | 参数不确定性 |

**D. 管理与执行**

| 变量 | 例子 |
|---|---|
| 对冲策略 | 不对冲、每 Δt、delta 区间；对冲用 model、effective 或 minimum-variance delta |
| 离场规则 | 止盈（权利金的 %）、止损（权利金的倍数）、DTE、最长持有时间、事件、Greek 上限 |
| 展期 | 被测试的一侧；到某个 DTE |
| **提前行权（long American 腿）** | `rational`（spot 越过边界表给出的行权边界即行权）/ `never`（卖出平仓） |
| **被指派（short American 腿）** | `rational`（按边界表）/ `conservative(ε)` / `none`；指派后 `close` 或 `hold` 股票；到期 pin risk 区间；在全部路径上执行 |
| 成本 | 每张合约费用、成交激进度 α、滑点 |
| **保证金制度** | `regt` / `pm`；一键切换，默认并列计算另一种 |
| 仓位 | 合约数、资本、Kelly 的比例 |
| 时间网格 | 默认 1 天步长；horizon（intraday：Phase 4） |
| Ledger 因子 | 参与 Shapley 分解的溢价因子及其关闭态（§5.11） |
| 子样本 | `subsample.greeks`、`subsample.pm`、`subsample.engine_check` 分别控制诊断量；行权与指派不抽样（§4.7） |
| 随机数子流 | 根种子派生的独立子流：主路径、先验、Jensen 预计算、子样本、引擎抽检（§4.4） |

### 3.2 因变量（输出）

**E. 估值**

| 输出 | 定义 |
|---|---|
| `V_mid`、`V_exec` | mid 估值；按可成交价格的清算价值 |
| P&L（mid、exec） | 相对入场，含对冲、行权与现金 |
| **EEP** | 每条 American 腿的提前行权溢价（American − European），入场时与沿路径 |
| 到期 payoff | 分腿与合计；多到期组合取第一个到期日的价值 |
| 盈亏平衡点 | 任意指定日期 P&L = 0 的 spot 水平，不只看到期 |
| 最大盈利 / 亏损 | 理论边界，带 `unbounded` 标记 |
| **保证金（两种制度）** | Reg-T 与 PM 并列；`binding` 一种用于仓位与资金约束（§5.8） |
| Return on margin | 两种制度各一份 |
| 往返成本 | 美元与 vol points 两种单位（§5.7） |

**F. 敏感度**：头寸层面（× n × m），符号按持有人视角

| Greek | 定义 | 报告单位 |
|---|---|---|
| Delta Δ | ∂V/∂S | 股数；dollar delta = Δ·S |
| Gamma Γ | ∂²V/∂S² | Γ·S²/100 = 1% 价格变动带来的 dollar delta 变化 |
| Theta Θ | ∂V/∂t | 每个日历日；拆成 carry 与 variance decay |
| Vega | ∂V/∂σ | 每 vol point；按到期分桶；加权 |
| Rho ρ | ∂V/∂r | 每 1% 利率变动 |
| Vanna | ∂Δ/∂σ = ∂Vega/∂S | 每 vol point 的股数 |
| Volga | ∂Vega/∂σ | 每 vol point 的 vega 变化 |
| Charm | ∂Δ/∂t | 每日股数：价格不动时的 delta 漂移 |
| Veta | ∂Vega/∂t | 每日 vega 变化 |
| Speed | ∂Γ/∂S | 每 1% 价格变动 |
| Color | ∂Γ/∂t | 每日 |
| Zomma | ∂Γ/∂σ | 每 vol point |

European 腿用解析 Greeks；American 腿用中心差分重定价（§5.1）。

派生指标：

- **Effective delta** `Δ_eff = Δ + Σ_i Vega_i·∂σ_i/∂S`，使用当前生效的曲面动力学规则（§5.3）；同时提供经验 minimum-variance delta。
- **加权 vega** `Σ_i Vega_i·(τ_ref/τ_i)^p`，p = 0.5，τ_ref = 30 天。短期限 IV 波动更大，加权后不同期限的 vega 才可比。
- **盈亏平衡已实现波动率** `σ_BE = √(−2·Θ_var / (Γ·S²))`：gamma 收益恰好覆盖 variance decay `Θ_var`（按年，不含 carry）时的已实现波动率。单个期权时它等于该期权的 IV；各腿 gamma 同号的组合，`σ_BE²` 是各腿 IV² 的 gamma 加权平均。这是用来对照已实现波动率预测的那一个数。
- **以 vol points 计的成本** = 往返成本 ÷ 每 vol point 的 vega（§5.7）。

**G. 情景网格**：确定性，full revaluation

- P&L 曲面：spot × 日期、spot × IV 冲击、IV 冲击 × 日期。
- 各时间切片 {现在、+1d、+1w、…、第一个到期日} 上的 Greek–spot 曲线；固定 spot 下 Greeks 随日期的变化。
- 压力集：参数化冲击（spot ±x%，IV 按 SSR 联动外加额外冲击）、因子冲击（水平、期限、skew）、历史类比（例如 2008-10、2018-02、2020-03、2024-08 的单日 spot 与 VIX 变动）、PM 式 10 点网格。
- 价格不动时的 decay 投影：明天、下周一、下一个事件之后。
- 对比网格：同一网格上 European vs American、Reg-T vs PM 的差值。

**H. 分布与路径**：Monte Carlo

- 期末 P&L：均值、中位数、标准差、偏度、峰度、分位数（1/5/25/50/75/95/99）、P(P&L > 0)、95% 与 99% 的 VaR 和 expected shortfall。
- 随时间的扇形图：每一步上 P&L、价值、Δ、Γ、vega、两种保证金的分位数；仍持有的路径比例。
- 路径统计：MAE、MFE、最大回撤、水下时间、离场时间与离场原因构成、峰值保证金、P(保证金 > 资本)。
- **行权与指派统计**：每条 American 腿的提前行权 / 被指派概率、时间分布、对 P&L 的影响；指派后股票头寸的规模与持有时间。在全部路径上统计。
- 逐步与累计归因（§5.10）。
- 仓位：在模拟分布上求 log-optimal Kelly 比例，再做实用折减——减半两次；负偏、超额峰度或样本少时再缩小（Mack & Sinclair 第 17 章）——并给出增长率与破产风险。Kelly 的分母使用 binding 保证金制度下的资本占用。
- Program 模式：权益曲线分位数、回撤分布、选定仓位下的增长率、资金占用、重叠交易的合计 Greeks。

**I. 优势与模型风险诊断**

- **Edge ledger**：在共同随机数下，对当前模式中可开关的溢价因子（drift、variance；reduced_form 下加 skew_dynamic，consistent_q 下加 skew_static）的 2^k 种组合做 Shapley 分解，结果与开启顺序无关。成本与「未声明残差」单独列示；各因子的关闭态见 §5.11。Ledger 标注 VRP 的 measure 与 basis。
- **溢价曲线**：EV 关于每种溢价的函数，以及扣除成本后的盈亏平衡值，与溢价的经验分布对照。参照点：SPY 一个月 VRP（variance swap strike 减去其后 21 天已实现波动率）均值约 3.6 vol points（中位数 4.3，标准差 7.4），约 82% 的日子为正（Mack & Sinclair 表 10.1）。**这是 VS 口径**，换算到 ATM 口径要先扣除 VS–ATM gap（§5.6）。
- **Tornado**：每个先验 ±1 标准差对 EV 与 expected shortfall 的影响。
- **模型分歧**：同一策略至少在两个过程族下运行；尾部指标的分散度就是模型风险。
- **引擎抽检（默认开启）**：从路径上抽取一组状态（默认 200 个，含 ITM 区域），比较 `table` 与 `tree` 的价格和行权判定，并用 `bs2002` 作独立交叉检查；超出阈值时报告给出警告，用于判断结论是否依赖定价近似。
- **Monte Carlo 诊断**：每个指标的标准误、达到目标误差所需路径数、方差在过程与参数两部分之间的分解。

### 3.3 约定

- 贴现与 carry 用 ACT/365 日历时间；扩散与 IV 用 variance clock（§5.4）。时间戳用 America/New_York，与 OptionLab 的到期日历一致。
- 波动率内部为年化小数；1 vol point = 0.01。
- Greeks 为头寸层面，符号按持有人视角（long 为正）；vega 按每 1%、theta 按每日，与 OptionLab 现有 `greeks_vectorized` 的单位一致。
- Spot 冲击以 S 的 % 表示；IV 冲击以 vol points 或因子单位表示。
- 每个 P&L 都有两个版本：mid 估值与可成交价格。
- 默认值：`style` 由 product profile 决定；`pricing.american_engine = "table"`；`margin.model = "regt"`，`margin.compare = true`；`vrp.measure = "atm_iv"`，`vrp.basis = "estimator"`（21 个交易日 close-to-close），单位 vol points。

### 3.4 时间如何改变价值与风险

模拟器要展示的「随时间演化」通过六个通道发生，每个通道都有对应输出。

| # | 通道 | 机制 | 输出位置 |
|---|---|---|---|
| 1 | Decay | 时间价值沿 variance clock 流失；周末和事件日不是普通的一天 | Θ 拆分（carry vs variance）；decay 投影 |
| 2 | Greeks 迁移 | 平值附近 Γ 与 Θ 按 1/√τ 增大，vega 按 √τ 缩小；价格不动时 delta 与 gamma 也会漂移（charm、color） | 各时间切片的 Greek–spot 曲线；Greeks 随日期 |
| 3 | 曲面 roll-down | 在固定期限曲面上，腿的 IV 沿期限结构滑动，skew 随 τ 缩短而变陡 | 归因中的 roll-down；时间规则对比 |
| 4 | 日历事件 | 事件方差先进入、后离开总方差（IV crush）；除息日；到期与结算（pin risk、AM 跳空）；**American：提前行权区域随 τ 变化，除息日前深度 ITM call 有被指派风险** | 事件感知网格；MC 中的到期、行权与指派处理 |
| 5 | 路径依赖 | 实现的价格变动改变 moneyness，从而改变所有 Greeks；对冲、离场、展期、行权改变头寸本身 | P&L 与 Greeks 扇形图；离场原因构成；指派统计 |
| 6 | 资本 | 保证金随 spot、IV 和 τ 变化；**两种制度的变化速度不同**，约束可能在持有期中途才出现 | 两种制度的保证金路径；P(保证金 > 资本) |

---

## 4. 架构：作为 OptionLab 的子功能（决策 5）

> 本节是**目标架构**。已实现的是平铺的 `core/optsim/`（5 个模块）+ `services/options/optsim.py` +
> `routes/strategies.py` 的 `POST /api/optsim`，没有 `services/optsim/` 和 optsim 表，见 [optsim.md](optsim.md) §1.1。

### 4.1 在 OptionLab 分层中的位置

OptionLab 的依赖主干是单向的，由 `scripts/doc_guard.py` 的 `import-direction`、`core-purity` 规则和 `tests/test_architecture_purity.py` 强制执行：

```text
app.py → routes/ → services/ → core/ → data_pipeline/ → utils/
```

optsim 按业务域嵌入这条主干，不新增顶层层级：

```text
scripts/optsim.py          CLI 薄适配层（同 app.py 的角色）
  └─▶ services/optsim/     编排：配置、场景、校准、运行、持久化
        ├─▶ core/optsim/   纯计算：无 Flask、无 DB、无网络
        └─▶ data_pipeline/
              read/        DataService：SPY / ^VIX 等 OHLCV（校准用）
              store/       optsim_* 表、repos、产出物写入
routes/optsim.py           Phase 5：只读已持久化的运行结果
```

- `core/optsim/` 只依赖 numpy、scipy、pandas 和 `utils/`；校准所需的历史数据由 `services/` 取来再传入，符合 `core-purity`。
- `services/optsim/` 不直接写 SQL；所有 SQL 都在 `data_pipeline/store/repos.py`（仓库约定：repos 是唯一构造 SQL 的地方）。
- 文件 I/O（`.npz`、图表、报告）也属于 I/O 边界，放在 `data_pipeline/store/artifacts.py`。
- 不新增运行时依赖：只用 OptionLab 已锁定的 numpy 1.26.2、scipy 1.13.1、pandas 2.2.3、matplotlib 3.9.2，加上标准库的 `tomllib`。

层内的「Q 定价，P 生成路径」分离仍然保留：`core/optsim/pricing` 不知道路径如何生成；`core/optsim/process` 只产出市场状态，只有某些 IV 联动模式需要模型价格时才调用 pricing。

### 4.2 包结构

```text
core/optsim/
  domain/      合约、product profile、组合、场景、配置 dataclass
  presets.py   产品族与场景预设（纯 Python，无文件读取）
  rng.py       SeedStreams：从根种子派生独立子流
  clock/       日历时间 ↔ variance time、事件
  surface/     参数化曲面、SSR 与时间规则、无套利检查
  pricing/     european、american（tree、table、bs2002）、greeks、
               measures（atm_iv；var_swap 预留）
  process/     gbm、merton、heston、bates、rbergomi、
               bootstrap、replay、ivlink、priors
  policy/      hedge、exit、roll、exercise、schedule、sizing
  execution/   spread、costs
  margin/      regt、pm、compare
  engine/      grid、montecarlo、program、compare、ledger、
               attribution
  metrics/     distribution、paths、edge、kelly、mcdiag
  charts/      matplotlib 渲染：数据进，PNG bytes 出
services/optsim/
  facade.py    run_grid、run_mc、run_sweep、run_compare、
               run_program、build_report
  config.py    TOML → 类型化配置；校验；resolved config 哈希
  scenario.py  场景解析；从 DataService 历史数据校准先验
  persist.py   调用 store 的 repos 与 artifacts
data_pipeline/store/
  db.py        init_db() 中新增 optsim_* 表
  repos.py     新增 optsim 读写函数（仍是唯一的 SQL）
  artifacts.py data/optsim/{run_id}/ 下的 npz、png、md
scripts/optsim.py   grid | mc | sweep | compare | program |
                    report | list | prune
tests/test_optsim_*.py
docs/decisions/0013-optsim-scenario-engine.md（已存在；引入 MC 等新边界时在其中追加或新开 ADR）
```

OptionLab 中同名模块（`facade.py`、`models.py`、`greeks.py` 等）按设计重复出现，一律按包限定名导入，例如 `from core.optsim.pricing import …`。每个新模块的顶部 docstring 采用 `Domain / Context / Contracts / Dependencies` 格式（`doc_guard` 的 `module-docstring` 规则）。

### 4.3 模块契约

| 模块 | 职责 | 不得 |
|---|---|---|
| `domain` | 不可变 dataclass；配置校验 | 包含数学计算 |
| `clock` | 日历 ↔ variance time；事件；交易日历 | 定价 |
| `surface` | `Σ(k, τ; f)`、无套利检查、动力学规则 | 知道路径 |
| `pricing` | 两种 style 的价格与 Greeks，在「腿 × 状态」上向量化 | 读数据或模拟 |
| `process` | spot、方差状态、曲面因子的联合 P 路径 | 给头寸估值 |
| `policy` | 纯函数 `state → actions`（含行权、指派） | 修改状态 |
| `execution` | 可成交价格、费用 | 决定动作 |
| `margin` | 两种制度的保证金及其分解 | 决定仓位 |
| `engine` | 在网格或时间上循环；应用策略；重新估值 | 定义模型 |
| `metrics` | 由运行结果计算统计量 | 重新运行模拟 |
| `services/optsim` | 配置、场景、校准、编排、持久化调用 | 重计算、直接写 SQL |
| `data_pipeline/store` | 表结构、SQL、产出物文件 | 业务逻辑 |

### 4.4 核心接口

```python
# core/optsim/pricing: pure, vectorized over legs x states
class Pricer(Protocol):
    def price(self, legs, states, clock) -> np.ndarray: ...
    def greeks(self, legs, states, clock, rule) -> GreekTable: ...

def pricer_for(style: Style, engine: str = "default") -> Pricer: ...

# core/optsim/pricing/american: built once per (r, q, kind, t_max)
class AmericanTables(Protocol):
    def eep(self, x, tau, sigma) -> np.ndarray: ...    # EEP / K
    def boundary(self, tau, sigma) -> np.ndarray: ...  # ln(B / K)

def build_tables(r, q, kind, t_max, sigma_grid) -> AmericanTables: ...

# core/optsim/margin
class MarginModel(Protocol):
    name: str  # "regt" | "pm"
    def requirement(self, book, state, pricer) -> MarginBreakdown: ...

# core/optsim/pricing/measures: the VRP anchor
class ImpliedMeasure(Protocol):
    name: str  # "atm_iv" | "var_swap"
    def value(self, surface, tau) -> np.ndarray: ...

# core/optsim/rng + engine
streams = SeedStreams(root_seed)  # independent child streams
run_grid(book, scenario, axes, cfg) -> GridResult
simulate(process, ivlink, timegrid, n, streams.paths) -> MarketPaths
run_mc(book, paths, policies, costs, margins, cfg) -> SimResult
run_ledger(cfg, factors, streams) -> Ledger  # 2^k combos
run_compare(run, cfg, switch) -> CompareResult
attribute(sim) -> Attribution
summarize(sim, ledger) -> Summary
```

`SimResult` 按路径 × 步保存：`V_mid`、`V_exec`、对冲、现金、P&L、选定的 Greeks、两种保证金、存活掩码、离场原因、行权 / 指派事件。

`SeedStreams` 用 numpy 的 `SeedSequence.spawn` 从根种子派生互相独立的子流：主路径、参数先验、Jensen 预计算、子样本选择、引擎抽检各用一条。任何一条子流的样本量变化都不会改变其他子流的抽样，所以主路径与预计算解耦（§5.6）。

### 4.5 数据流

Grid 运行：

```text
config.toml -> services.optsim.config -> resolved config + hash
r, q, t_max -> build_tables (American legs only) -> AmericanTables
scenario + book -> core.optsim.engine.run_grid -> GridResult
GridResult -> store: runs, variants, metrics
           -> artifacts: grid.npz, figures/*.png
```

Monte Carlo 运行：

```text
config -> SeedStreams(seed)
process params -> jensen(streams.jensen)      -> jensen.npz
config -> simulate(streams.paths) -> run_mc   -> SimResult
ledger: 2^k factor combos on the same streams -> SimResult x 2^k
sims -> attribute, summarize, compare         -> Summary
Summary -> store: runs, variants, metrics, series, compare, ledger
        -> artifacts: sim.npz, attrib.npz, jensen.npz, report.md
```

对照组就是 ledger 中所有因子都关闭的那个组合（§5.11），与其他组合使用同一组随机数，所以差值是配对差值，路径噪声大部分相互抵消。两种结构的比较、以及 `compare` 模式的 style / margin 切换，也都是同一路径上的配对差值。

### 4.6 存储与产出物

**SQLite**（ADR 0003：单机 SQLite + WAL）。optsim 表与行情表共用 `MARKET_DB_PATH` 指向的数据库文件，由 `init_db()` 用 `CREATE TABLE IF NOT EXISTS` 创建（仓库不用 migration 框架）。表结构按查询维度规范化，维度不编码进指标名：

| 表 | 主键 | 内容 |
|---|---|---|
| `optsim_runs` | `run_id` | 创建时间、运行类型、策略、场景来源、`config_json`、`config_hash`、根种子、代码版本（git SHA）、状态、产出物目录、父运行、备注 |
| `optsim_variants` | `(run_id, variant_id)` | 同一次运行中的每个变体：`style`、`margin_model`、`premia`（full、control 或因子组合）、`engine`、`process` |
| `optsim_metrics` | `(run_id, variant_id, metric, stat)` | 与时间步无关的标量，附标准误；例如 `metric = "pnl_exit"`、`stat = "q05"` |
| `optsim_series` | `(run_id, variant_id, step, metric, stat)` | 时间序列与扇形图：每一步的分位数、存活比例、两种保证金；附 `t_days` |
| `optsim_compare` | `(run_id, base_variant, alt_variant, metric, stat)` | 配对差值及其标准误 |
| `optsim_ledger` | `(run_id, variant_id, factor)` | 各溢价因子的 Shapley 贡献、`residual`、`costs`，附标准误 |
| `optsim_links` | `(run_id, kind, ref)` | 外部关联（后续）：`tracked_strategies.id`、Notion 页面 |

- 配对差值单独成表，因为它的标准误不能由两个变体各自的标准误推出：共同随机数让两者高度相关，差值的标准误要按逐路径差值直接计算。
- `step` 为整数时间步，`t_days` 为对应的日历天数；入场时的点风险和期末 P&L 分布这类与时间步无关的量放在 `optsim_metrics`，不用哨兵值占位。
- `stat` 取固定词表：`mean`、`median`、`sd`、`q01` 到 `q99`、`es95`、`es99`、`p_gt0` 等；`metric` 同样有固定词表，由 schema 测试锁定。

**产出物文件**：`data/optsim/{run_id}/` 下的 `grid.npz`、`sim.npz`（逐路径 P&L、两种保证金、离场与指派信息）、`attrib.npz`、`jensen.npz`、`figures/*.png`、`report.md`、`config.resolved.json`。

- `run_id = {yyyymmdd}-{strategy}-{cfghash8}`；产出物不可变，只有输入哈希变化时才重跑对应阶段。
- 用 numpy 自带的压缩 `.npz`，不用 v0.1 设想的 parquet / netCDF：后者需要 pyarrow / xarray，而它们不在 `requirements.txt` 中。
- 配置文件用 TOML（标准库 `tomllib`，只读），不用 YAML：PyYAML 同样不在依赖中。展开后的配置以 JSON 存入 `config_json`。
- 默认保存全部路径的 P&L 与保证金，Greeks 只保存分位数（`greeks = "full"` 时保存全部）；市场路径只保存种子，按需重新生成。American 表在内存中重建，不落盘。
- `.gitignore` 新增 `data/optsim/`；`scripts/optsim.py prune` 清理旧产出物。
- 未来 UI 的契约是上述各表加上 `report.md`；UI 不解析指标名，也不需要了解引擎内部。

### 4.7 执行模型与性能预算

OptionLab constraints 第 6 节规定计算必须在一次 HTTP 请求内完成，并且没有后台任务队列。因此：

- Monte Carlo、ledger、sweep、Program 只通过 CLI 离线运行，结果持久化；未来的 UI 只读结果。
- Grid：European 在 1 秒内完成；American 加上表格构建约 2–3 秒。两者以后都可以在请求内同步提供。

**单次估值吞吐**（开发容器，numpy 2.x，单线程；OptionLab 锁定 numpy 1.26.2，量级一致）：

| 估值 | 每百万次耗时 | 相对 European |
|---|---|---|
| European（解析式） | 0.12–0.14 秒 | 1× |
| American `table`（查表，含 European 部分） | 0.30 秒 | 约 2.2× |
| American `bs2002`（交叉检查） | 6–9 秒 | 约 60–80× |
| American `table` 构建（33 个 σ × 90 天，每种期权类型一次） | 1.9 秒 | — |

**一次完整研究的预算**：基准规模为 2 万路径 × 60 个日步 × 4 条腿，即每次 MC 480 万次估值。一次完整研究 = ledger（structural 模式 2² = 4 个组合，其中「全开」即主运行）+ 10 点 sweep（默认 5,000 路径，约合 2.5 次 MC）+ 1 次 compare，约合 7.5 次 MC。下表是「估值次数 × 吞吐」的估算，不含路径生成与策略逻辑的开销，实际耗时在 Phase 2 实测。

| 模式 | 每次 MC 的估值 | PM 路径（10 个估值点） | 一次完整研究 |
|---|---|---|---|
| European | 约 0.6 秒 | 主运行全部路径约 6 秒 | 约 0.5–1 分钟 |
| American（`table`） | 约 1.5 秒，另加一次构建约 2 秒 | 主运行全部路径约 15 秒 | 约 1–2 分钟 |
| American，PM 为约束制度 | 同上 | 每次 MC 全部路径约 15 秒 | 约 3–5 分钟 |
| 强制 `bs2002`（只用于交叉检查） | 约 35 秒 | 主运行全部路径约 6 分钟 | 10 分钟以上，PM 必须抽样 |

reduced_form 模式的 ledger 为 2³ = 8 个组合，完整研究约合 11.5 次 MC，各档按比例增加约一半。

- **ledger 与 sweep 默认按腿的原生 style 运行**。`table` 引擎让 American 的成本降到 European 的约 2 倍，不必像审查建议那样默认降级为 European。`ledger.style_override = "european"` 保留为提速选项，但对 EEP 敏感的结构（深度 ITM、高股息）不应使用。
- **sweep 默认 5,000 路径**：共同随机数下配对差值的标准误远小于各自独立估计的标准误，路径数可以更少。
- **子样本只用于诊断量**，三个开关分别生效：
    - `subsample.greeks`（默认 2,000）：Greeks 扇形图。
    - `subsample.pm`（默认 2,000）：PM 保证金路径。PM 为约束制度、并且存在由保证金触发的离场或减仓规则时，自动改为全部路径，因为此时保证金会改变 P&L。`pm.path_mode = "slices"` 时只在报告的时间切片上计算。
    - `subsample.engine_check`（默认 200 个状态）：引擎抽检（§5.1）。
- **行权与指派不抽样**：它们改变路径 P&L，判定与统计都在全部路径上执行。用边界表判定的成本可以忽略：每条腿每一步一次插值。
- Reg-T 是公式计算，始终在全部路径上进行。
- numba 可以再快一个数量级，但它是新依赖，需要单独的 ADR；有了 `table` 引擎后已无必要。

---

## 5. 核心模型

### 5.1 定价与行权方式切换（决策 1）

**共同输入**：两种 style 共用同一组 `S`、`r`、`q`（或离散股息）和同一个曲面，远期 `F = S·e^{(r−q)τ}` 由它们导出。因此切换 style 时唯一的变化是行权权利。

**European 引擎**：在远期上用 Black-76（等价于带 carry `b = r − q` 的 generalized BSM），Greeks 解析计算。SPX 类产品若给出期权报价，可由 put–call parity 反推隐含远期（Phase 4）。

**American：估值与行权决策分开**

BS2002 的误差集中在 ITM 区域，而行权与指派恰恰发生在那里。v0.3 把两件事分开：估值默认用 `table` 引擎，决策只用边界表，两者来自同一次 tree 计算。

| 引擎 | 方法 | 精度（相对参考） | 成本 | 用途 |
|---|---|---|---|---|
| `tree`（参考） | CRR 二叉树，以 European 为 control variate，N 与 N+1 两次取平均 | 与 QuantLib QD+ fixed-point 引擎相差 ≤ 6e-4（put）、≤ 5e-5（call），按行权价 100 计 | 每个期权 O(N²) | golden 值、引擎抽检、构建 `table` |
| `table`（默认） | 一棵延长期限的 CRR 树（在 σ 网格上向量化），每个交易日记录一层 EEP(x, τ; σ) 与边界 B(τ; σ)；估值 = European 解析价 + 插值得到的 EEP，下限截断为内在价值 | 400 个随机状态（S/K 0.7–1.3，1–90 天，IV 8–80%）：最大误差 0.0028，平均 0.0002（按行权价 100 计）；边界误差 ±0.22% 以内 | 构建 1.9 秒；查表约为 European 的 2.2 倍 | Grid、MC 估值、PM 重估、差分 Greeks |
| `bs2002`（交叉检查） | Bjerksund–Stensland（2002）闭式近似，下限截断为 max(European, 内在价值) | 同一组状态：最大误差 0.16，平均 0.0074；系统性低估 put；行权边界偏高 0.45%–5.7% | European 的 60–80 倍 | 与 tree 没有共同数值核心的独立检查 |

- **一张表覆盖所有行权价**：连续股息率（或按比例的离散股息）下，American 价格对 (S, K) 一次齐次，EEP/K 只依赖 x = ln(S/K)、τ、σ、r、q。所以每次运行每种期权类型（put、call）只需一张表，覆盖期限上限 T_max 内的全部腿和行权价。
- **表的构建**：树的总期限取 T_max 的约 1.35 倍，使每个记录期限上的节点覆盖足够宽的 x 区间；每个交易日记录一层，与日频 MC 的时间步对齐，所以 τ 方向不需要插值。x 方向线性插值，σ 方向在对数网格（默认 33 点，5%–150%）上线性插值。节点区间以外，深度 ITM 一侧按行权区域处理，深度 OTM 一侧 EEP 取 0。超出 σ 网格的状态截断，并在引擎抽检中标记。一张表约 30 MB，在内存中重建，不落盘。
- **行权与指派决策只用边界表**：spot 低于 B(τ; σ)（put）即处于行权区域。不用 BS2002 的原因是它的边界比真实边界高 0.45%–5.7%（§8），会让 short put **过早**被指派。过早指派意味着对手方放弃了时间价值，这对卖方有利，所以 P&L 会偏乐观。审查报告推测的是「低估尾部指派」，实测方向相反，但结论相同：BS2002 不能用于决策。
- **引擎抽检默认开启**：每次运行从路径上抽取状态（默认 200 个，含 ITM 区域），比较 `table` 与 `tree` 的价格和行权判定，`bs2002` 作独立交叉检查；价格差超过 0.005（按行权价 100 计）或边界差超过 0.5% 时，报告给出警告。
- American Greeks：在 `table` 上做中心差分，默认步长为 S 的 0.5%、0.5 vol point、一个交易日。
- Variance clock 映射：表按日历期限构建，传入 `σ_eff = √(w / τ_cal)`，其中 `w` 为总方差（§5.3、§5.4）；贴现与 carry 仍用日历时间。
- 离散股息（Phase 3）：按比例的离散股息保持齐次性，可以继续用同一套表；绝对金额的股息需要按标的价位分表，或改用 escrowed dividend 模型。call 在除息日前一日的行权由带股息的边界表给出。
- 到期与交割：现金交割的腿在到期步按内在价值结算；AM 结算的 SPX 在下一个开盘结算，因而带隔夜跳空；实物交割的腿在到期时转为股票头寸，行权价附近标记 pin risk。

**一键切换的语义**

| 开关 | 改变的内容 | 不变的内容 |
|---|---|---|
| `style`（CLI `--style european` 或 `american`） | 定价引擎、Greeks 方法、提前行权与指派逻辑 | 交割、股息、产品类别、曲面、随机数 |
| `product.profile`（CLI `--profile …`） | style、交割、股息模型、Reg-T 类别、PM 区间、乘数、最小报价单位 | 策略规则、场景参数、随机数 |
| `compare = "style"` | 在同一组路径上并列运行两种 style | 其余全部 |

`compare = "style"` 的报告给出：每条腿入场时与沿路径的 EEP、Greeks 差值、提前行权 / 指派概率及时间、配对 P&L 分布差、保证金差。

**默认假设下的 EEP**（S = 100，45 天，IV 20%，r 4.5%，q 1.3%）：ATM put 为 0.029（价格的 1.1%），10% ITM put 为 0.21（2.1%）；连续股息率且 q < r 时，call 的 EEP 约为 0。call 的提前行权风险集中在离散除息日，由 Phase 3 处理。

### 5.2 波动率曲面

统一接口 `Σ(k, τ; f)`，两种表示形式：

```text
参数化（场景与模拟），k = ln(K/F)：
  σ(k, τ) = σ_ATM(τ) + β(τ)·k + ½·γ(τ)·k²
  β(τ)    = β_ref·(τ/τ_ref)^(−α)      默认 α ≈ 0.4
  σ_ATM(τ)：水平加期限结构形状
```

- **参数化形式是 v0.2 的主要表示**，假设场景直接给出因子。
- **拟合形式**（Phase 4）：对期权链做逐到期 SVI 或 SSVI（Gatheral & Jacquier 2014）拟合，再投影到因子向量 `f = (level, term, skew, curvature)`，使拟合曲面与模拟曲面共用坐标。数据来源可以是 OptionLab 已有的 yfinance 当前链（只有快照，ADR 0004），或恢复采集后的 futu 快照。
- Wing 设下限与上限。引擎产生的每一个曲面——拟合、冲击或模拟——都要通过静态无套利检查（butterfly 密度非负；总方差随 τ 不减）。
- α ≈ 0.4 反映指数 ATM skew 的经验幂律衰减（约 T^−0.4），与 H ≈ 0.1 的 rough volatility 一致。

### 5.3 曲面动力学

**Spot：skew stickiness ratio（SSR）。** 一个参数覆盖经典的几种情形（Derman 1999；Bergomi 2016）：

```text
dσ_ATM = SSR·β·dlnS
dσ(K)  = (SSR − 1)·β·dlnS        固定行权价

SSR = 0  sticky moneyness
SSR = 1  sticky strike
SSR = 2  local vol（"sticky implied tree"）
```

有意区分两个 SSR：

- **SSR_priced = 2**：如果 spot–vol 动态完全解释 skew 的形状，skew 应有的斜率（Mack & Sinclair 第 7 章：隐含 skew 斜率约为 spot–vol 斜率的一半）。
- **SSR_realized**：ATM IV 实际随 spot 移动的幅度。Mack & Sinclair 的 SPY 一个月例子约为 1.06（IV 变化对收益的回归斜率 −0.95，skew 斜率 −0.90）；Bergomi 报告短期限指数约为 1.5。

两者之差就是 skew 的动态溢价，对应 edge ledger 中的 `skew_dynamic` 因子（§5.11），与 variance 溢价分开声明。差距的一部分可能是跳跃补偿，所以配置项 `skew_gap_attribution` 要写明它归因于跳跃（过程）还是溢价（ledger），二者只能选一，由配置校验强制。

由此得到 effective delta：`Δ_eff = Δ + Vega·(SSR − 1)·β / S`（vega 以单位波动率计）。已用重定价验证：S = 6000、σ = 15%、β = −0.9、SSR = 1.5 的 30 天 ATM call，BS Δ 0.509 变为 Δ_eff 0.457；5% OTM put（IV 19.6%）从 −0.174 变为 −0.207。American 腿用同样的重定价方式计算 effective Greeks。

**时间：「曲面不变」指什么。**

- `constant_maturity`（默认）：曲面在 τ 上保持稳定。每条腿的 IV 沿期限结构滑动，skew 随 τ 缩短而变陡（β ∝ τ^−α），产生 roll-down P&L。
- `fixed_expiry`：每个到期日保留自己的 IV，没有 roll-down。

两种规则之差在报告中记为 roll-down。

**事件。** 预定事件 e（FOMC、CPI、财报）给其后的每个到期增加方差 `v_e`，并且只在这一处计入：

```text
w(t, T) = σ_I(T)²·τ_cal(T)
        = σ_base²·τ_var(t, T) + Σ_{t < t_e ≤ T} v_e
```

- `τ_var` 只按普通交易日与非交易日计权（§5.4），不给事件日加权。v0.2 同时在 variance clock 和上式中计入事件方差，会重复计算；v0.3 改为只在上式中计入。
- 事件过后 `v_e` 离开总方差：对晚于事件的到期，`w(t, T)` 在事件时刻恰好下降 `v_e`（另加当天普通的方差流逝），其余时刻连续。IV crush 因此是模型的输出，而不是假设。
- P 测度一侧：事件日的已实现方差为 `v_e^P = v_e × p_var_ratio`，默认 1.0，即不假设事件溢价。认为事件隐含波动高于实际时把它设为小于 1；它属于 variance 因子（§5.11）。如果 P 过程忽略事件方差，卖出事件波动会显示出虚假的优势。

### 5.4 时间模型

- **日历时间** `τ_cal`（ACT/365）驱动贴现与 carry。
- **Variance time** `τ_var = Σ_d w_d / 252`，对剩余每一天求和：交易日 w = 1，非交易日取一个小权重（默认 0.1；周末带来的方差远小于交易日，French & Roll 1986）。事件方差不进入 `τ_var`，只按 §5.3 的加法项计入一次。
- 交易日历复用 OptionLab `core/options/simulation/expiry_calendar.py` 中的 NYSE 假日近似；Phase 1 把它提升为 `core/_shared` 中的公共函数，现有测试继续覆盖。
- IV 换算使总方差与报价一致。于是 theta 自然拆成 carry decay（日历）与 variance decay（时钟）；周末只增加很少的 variance time，模型中的 decay 集中在方差真正累积的日子。
- **v0.2 默认日频步长**，与多周 VRP 结构的管理频率一致（每日收盘检查离场、展期、行权与保证金）。
- **Intraday（Phase 4）**：U 形日内方差曲线 `u(minute)`（归一化为一个交易日的方差）驱动分钟级路径，spread 模型有自己的日内曲线。开盘 30 分钟持有之类的研究需要它们。

### 5.5 路径过程（P 测度）

| 过程 | 状态 | 用途 |
|---|---|---|
| GBM | S | 基准；解析检验 |
| Merton 跳扩散 | S | 跳空与崩盘尾部 |
| Heston | S, v | 波动率聚集、spot–vol 相关 |
| Bates（Heston + 跳跃） | S, v | 默认的现实指数模型 |
| Rough Bergomi | S、forward variance 曲线 | rough vol（H ≈ 0.1）、短期 skew 与 vol-of-vol；研究用 |
| Block bootstrap | S, VIX | 经验收益，无参数形式 |
| 历史回放 | S, VIX | 真实路径；VIX 作为 30 天 IV 的代理 |

- 所有过程返回相同的契约：`S[p,t]`、方差状态、跳跃标记。
- **参数不确定性**：`priors` 每批抽取一个参数向量（例如 200 批 × 100 路径）。报告给出合并分布，以及 `Var(P&L) = E[Var(P&L | θ)] + Var(E[P&L | θ])` 的分解。
- **校准（Phase 3）**：`services/optsim/scenario.py` 通过 OptionLab 的 `DataService` 读取 SPY、^GSPC、^VIX 的日线历史（provider seam 背后的 yfinance），估计已实现方差、跳跃统计、波动率聚集和 SSR 代理，输出先验。这一步只用真实的 OHLCV 历史，不需要期权数据。
- Regime 条件先验：读取 `regime_log` 的 `vol_regime` / `dir_regime`，按 regime 分组估计参数。
- Rough Bergomi 采用 hybrid scheme（Bennedsen, Lunde & Pakkanen 2017）。它的状态是 forward variance 曲线，可以直接给出 variance-swap 隐含方差，将来可以接入 VS 口径（§5.6）。
- 回放的注意事项：VIX 是 30 天 variance-swap 风格指数，高于 ATM IV。回放用拟合的调整把 VIX 映射为 ATM IV，并在所有地方标注为 proxy replay。
- 隔夜跳空单独抽样、按开盘跳空幅度与方向对路径做条件化：随 intraday 一起放到 Phase 4。

### 5.6 IV–RV 联动与 VRP 口径（决策 6）

t₀ 的曲面由场景给出。声明的溢价决定相对于它的 real-world 动态，以及 IV 沿每条路径如何移动。

**口径接口**

```python
class AtmIv:  # 已实现：默认锚点
    name = "atm_iv"

    def value(self, surface, tau): ...  # σ_ATM(τ)


class VarSwapLevel:  # 预留：调用即抛出 NotImplementedError
    name = "var_swap"

    def value(self, surface, tau): ...
```

`vrp.measure = "atm_iv"` 是默认值；配置成 `"var_swap"` 时，运行在启动阶段就以清晰的错误信息失败，不会静默回退。

**RV 的两个口径**

VRP 的数值取决于「已实现波动率」怎么算。验算显示，21 个交易日 close-to-close 估计量自身就有偏：GBM 下 σ = 16% 时 `E[RV̂] − σ = −0.19` vol points；Heston（ξ = 0.6，ρ = −0.7）下 `E[RV̂]` 比 `√E[∫v]` 低 0.78 vol points。这与 VRP 本身同一量级，所以口径必须写明：

| 口径 | 定义 | 用途 |
|---|---|---|
| `integrated` | `σ̄_t(τ) = √(E_t^P[∫_t^{t+τ} v ds] / τ)`：模型量，没有估计量噪声 | 内部动力学 |
| `estimator`（默认） | `E_t^P[RV̂_n]`，RV̂_n 为 n 个交易日 close-to-close、零均值、×252 | 声明与报告；与 Mack & Sinclair 及历史数据可比 |

两者的差写成比例 `E^P[RV̂_n] = (1 − j)·σ̄`：

- GBM 有解析式：`j = 1 − c(n)`，`c(n) = √(2/n)·Γ((n+1)/2) / Γ(n/2)`；n = 21 时 j ≈ 0.012。
- Heston、Bates 在 (v, τ) 网格上用预跑 MC 制成 `j(v, τ)` 表；rough Bergomi 放到 Phase 4。
- 预跑用独立子流（§4.4），路径数固定（默认 2 万），每个参数批次一张表；结果作为产出物 `jensen.npz` 保存并参与哈希。改变预跑路径数不会改变主路径；`j` 只依赖过程参数，不依赖 VRP，所以 ledger 的各组合共用同一张表。

**Structural 联动（默认）：显式不动点**

以 estimator 口径声明 `VRP = a + b·IV`，即 `IV − (1 − j)·σ̄ = a + b·IV`，解得：

```text
IV_ATM,t(τ) = ((1 − j)·σ̄_t(τ) + a) / (1 − b)
σ̄_0(τ)      = ((1 − b)·IV_ATM,0(τ) − a) / (1 − j)
```

- 每条路径的每一步，由方差状态算出 σ̄（Heston / Bates 有闭式），再按第一式得到 ATM IV，不需要迭代。
- t₀ 用第二式反解初始状态，据此设定方差过程的 `v₀`、`θ`（Heston 等）。今天的价格保持场景给定的值，声明的溢价由已实现动态承载。
- **参数域校验**（配置展开时执行，违反即报错）：
    - `b < 1`；默认允许范围 −0.5 ≤ b ≤ 0.5，超出时要求显式确认。
    - 每个期限上 `(1 − b)·IV_ATM,0 − a ≥ σ_floor`（默认 1 vol point），保证初始的预期已实现波动率为正。
    - 路径上 IV 低于 `σ_floor` 时截断并计数，报告给出截断比例。
- **VRP 可以为负**：`a` 可以取负值，例如模拟已实现波动高于隐含波动的危机阶段，只要满足上面的下限。
- 仿射形式同时覆盖纯加法（b = 0）与纯比例（a = 0）。Mack & Sinclair 发现 SPY 的溢价以 vol points 计在不同 IV 水平上相当稳定，但占 IV 的比例低波动时更高（约 19%）、高波动时更低（约 13%），介于两种纯形式之间。
- 以 ATM 为锚，OTM 行权价的 IV 来自曲面形状。翼部相对 P 分布是否偏贵，在 ledger 中由 skew 因子或残差体现（§5.11）。
- 事件日的 P 侧方差由 `p_var_ratio` 控制（§5.3），它属于 variance 因子。
- 深度左尾（书中 SPY 样本的最小值接近 −66.5 vol points）必须来自跳跃与方差过程，而不是 VRP 噪声，否则崩盘风险会被计算两次。

**校准现实：VRP_ATM 仍是声明的先验，不是校准值**

- OptionLab 没有期权历史（ADR 0004），futu 快照采集又已延后（决策 4），所以目前无法从历史数据估计 ATM 口径的 VRP。`a`、`b` 是用户声明的假设，每次都要做 sweep（§3.2 I 的溢价曲线）。
- 当前唯一可得的隐含波动率历史是 ^VIX，而它是 VS 口径。因此 VS 接口一旦落实，第一个用途就是：用 VIX 与其后 SPX 已实现波动率校准 VRP_VS，再用曲面算出的 gap 换算为 VRP_ATM。
- 文献数值是 VS 口径，不能直接当 ATM 默认值：

```text
VRP_ATM = VRP_VS − (VS level − ATM IV)
```

在假设曲面上用 replication 积分算出的 gap（r = q = 0，σ_ATM = 16%）：

| 曲面 | 30 天 VS | 30 天 gap | 45 天 gap |
|---|---|---|---|
| 平坦 smile（β = 0，γ = 0） | 16.00% | 0.00 vol points | 0.00 vol points |
| 只有 skew（β_ref = −0.9，γ = 0） | 18.42% | 2.42 | 2.71 |
| 默认（β_ref = −0.9，γ = 1.0） | 19.01% | 3.01 | 3.62 |
| 陡峭（β_ref = −1.3，γ = 1.5） | 21.95% | 5.95 | 6.70 |

这些是假设曲面上的模型结果，不是经验估计；但它们说明 gap 与文献中 3–4 vol points 的平均 VS 口径 VRP 属于同一量级。由此推论：ATM 口径的溢价可能远小于直接引用文献数值所暗示的水平，指数 VRP 中可能有相当一部分来自翼部（skew 溢价）。这一推论需要用数据验证（Phase 4 的 VS 接口与 VIX 校准）。另外，文献数值使用的估计量口径也要与 `vrp.rv_days` 对齐，否则还会混入上面的估计量偏差。

**VS 接口规格（后续按需落实）**

- `VarSwapLevel.value(surface, τ)`：在曲面上做对数合约 replication，`K_var = (2e^{rτ}/τ)·[∫_0^F P(K)/K² dK + ∫_F^∞ C(K)/K² dK]`；参数包括 wing 策略（截断上下限或 SVI 尾部）与积分网格。
- 保留的测试：平坦 smile 下 VS 等于 ATM；replication 结果与 d2 加权的隐含方差积分一致（Gatheral 2006）。
- 配置键已经预留：`vrp.measure`、`vrp.basis`、`vrp.rv_days`（默认 21）。

**联动模式**

| 模式 | 定义 | 适用 |
|---|---|---|
| `structural`（默认） | 上面的显式不动点 | 优势研究：VRP 显式 |
| `reduced_form` | ATM IV 自成一个因子：`dσ = κ(σ̄ − σ)dt + SSR·β·dlnS + η·σ·dW⊥`，`E[RV̂_n] = IV − VRP` | 压力与盯市风险；用 SPY/VIX 校准（VIX 为代理）；支持 `skew_dynamic` 因子 |
| `consistent_q` | 在 P ≠ Q 参数下用 Q 模型（Heston/Bates，COS 方法）重定价得到 IV | 研究；一致性检查；支持 `skew_static` 因子（Phase 4） |

在 `structural` 模式下，skew 与曲率默认保持归一化形状不变；可选 AR(1) 因子。

### 5.7 执行与成本（决策 4：参数化）

```text
P_exec  = P_mid ± α·h                (买入 +，卖出 −)
h       = max(tick, ½·spread_pct·P_mid) · m_k · m_τ · m_regime
cost_rt = 2·α·h + fees
cost_vp = cost_rt / vega_per_vol_point          (vol points)
```

- `spread_pct` 与 OptionLab Option Pricing Matrix 的约定一致（那里的 fill 偏移是 `max(mid × spreadPct/200, 0.01)`），也与学习期宪章「开仓时 spread 占 mid ≤ 10%」使用同一个比率，报告可以直接核对。
- `m_k`、`m_τ`、`m_regime` 是 moneyness、期限、波动率 regime 的乘数，默认为 1；全部是假设参数，标注为 `hypothetical`。
- `α ∈ [0, 1]`：0 表示按 mid 成交，1 表示付满整个 half-spread。默认：限价单 0.5；止损与强制离场 1.0，并使用触发时刻的（更宽的）spread 状态。
- 对冲交易与指派后处理股票的交易各自计成本。
- 用 vol points 表示，成本与优势在同一尺度上：往返成本 0.60、每 vol point vega 0.30（都以期权价格单位计）的 straddle，要有 2 vol points 的优势才开始赚钱。
- futu 快照恢复采集后（Phase 4），由真实买卖价构建的 spread 表通过同一接口替换参数化模型。

### 5.8 保证金（决策 3：Reg-T 与 PM 一键切换）

- `margin.model = "regt" | "pm"` 指定 **binding** 制度：它决定仓位、return on margin、资金约束检查（P(保证金 > 资本)）和 Program 模式的资金占用。CLI 用 `--margin regt|pm`。
- `margin.compare = true`（默认）同时计算另一种制度，所有报告并列给出。
- 两种制度对 American 腿都使用该腿自己的定价引擎，因此 style 切换与 margin 切换可以自由组合。

**Reg-T（strategy-based，Cboe 规则）**

| 头寸 | 要求 |
|---|---|
| 裸卖 broad-based index，或跟踪 broad-based index 的 ETF（如 SPY） | 100% 权利金 + 15% 标的价值 − OTM 金额；最低为权利金 + 10% 标的价值（call）或 10% 行权价（put） |
| 裸卖 equity、narrow-based index、跟踪 narrow-based index 的 ETF | 同上，比例为 20% |
| 杠杆 ETF | 上述比例乘以杠杆倍数 |
| Long 期权 | ≤ 9 个月全额支付；> 9 个月（listed）为成本的 75% |
| 价差（short 在 long 之前或同时到期） | min(short 的裸卖要求, 最大可能损失) + long 全额支付；卖出权利金可以冲抵 |
| Short straddle / strangle | 两侧裸卖要求中较大者 + 另一侧的权利金 |
| Iron condor / iron butterfly | 最大可能损失 + long 成本，卖出权利金冲抵；净占用 = 较宽一翼的宽度 − 净权利金 |
| Covered call | 股票 50%（初始）/ 25%（维持）；short call 无额外要求 |
| Protective put / collar | 股票 50%，put 全额；维持要求见 Cboe Margin Manual |
| Calendar / diagonal | 按价差规则；long 全额；European calendar 的 long 腿可能无法覆盖指派，报告中提示 |
| 指派后形成的股票 | 按股票 Reg-T：50% / 25% |

**PM（risk-based，TIMS 风格代理）**

- 在产品区间内取 10 个等距估值点（每侧 5 个），按理论模型重估组合，取最大理论损失。
- 区间：高市值 broad-based index −8% / +6%（Cboe 的示例说明 SPY 适用同一区间）；非高市值 broad-based index ±10%；个股与 narrow-based ±15%。
- 要求 = max(最大理论损失, 每张合约 0.375 × 乘数)；对 long 合约，最低要求不超过其市值。
- 规则要求情景同时变动标的与 IV，但没有规定 IV 冲击的幅度（由 OCC TIMS 决定）。代理用 `pm.iv_rule`：默认 sticky strike；可选 ±IV shift 作为券商附加。券商附加与账户最低权益要求都是配置项。
- 估值点上用该腿的定价引擎，在估值当天（不推进时间）重估。

**示例**（45 天，r 4.5%，q 1.3%，默认假设曲面；单位：美元，每组 1 张）

> 这些是设计期原型的数值（曲面为 §3.1 的幂律 skew），与现实现的曲面参数不同；现实现的回归数值见 [optsim.md](optsim.md) §4。

| 头寸 | 净权利金 | Reg-T 现金占用 | PM | Reg-T / PM |
|---|---|---|---|---|
| SPX-like 16Δ short strangle（5600P / 6300C，S = 6000） | 6,284 | 60,000 | 13,731 | 4.4× |
| SPX-like iron condor（同上，两翼各 100 点） | 2,371 | 7,629 | 4,154 | 1.8× |
| SPY-like 30Δ short put（583P，S = 600），European | 757 | 7,300 | 2,569 | 2.8× |
| 同上，American | 765 | 7,300 | 2,621 | 2.8× |
| 个股 30Δ short put（189P，S = 200，ATM IV 35%），American | 541 | 2,900 | 1,591 | 1.8× |

- Reg-T 一列是扣除卖出权利金后的现金占用；PM 一列使用 sticky strike，不含 IV 冲击与券商附加。American 两行用参考 `tree` 计算（v0.2 用 BS2002，差 4–5 美元）。
- 结论：对裸卖结构，制度选择会让 return on margin 与 Kelly 仓位相差 1.8–4.4 倍，是一阶输入而不是细节；有限风险结构的差距较小。
- 沿路径：Reg-T 在全部路径上计算；PM 默认在子样本上计算，PM 为约束制度且存在保证金触发规则时改为全部路径（§4.7）。
- 学习期宪章第 3.2 节目前禁止任何保证金放大，所以这些输出是研究结果，不是交易许可。

### 5.9 管理策略

纯函数 `policy(state_t) → actions`，在每一步作用于仍存活的路径。

- **对冲**：`none`、`time(Δt)` 或 `band(δ)`（Whalley–Wilmott 式无交易区间）。对冲 delta 可选：当前 IV 下的 model Δ、预测 RV 下的 Δ、effective Δ（SSR）或 minimum-variance Δ（Hull & White 2017）。按隐含还是已实现波动率对冲，会改变 P&L 的路径与分布形状，但基本不改变均值（Ahmad & Wilmott 2005；μ = r 时严格成立，见 §8 的验算）。
- **离场**：止盈、止损、DTE、最长持有时间、事件、Greek 上限（dollar delta、dollar gamma）。
- **展期**：被测试的一侧；到某个 DTE 时按日历展期。
- **提前行权（long American 腿）**：`rational` 在 spot 越过边界表给出的 B(τ; σ) 时行权；`never` 改为卖出平仓。已用 LSMC 验证路径上的 rational 行权（§8）。
- **被指派（short American 腿）**：
    - `rational`：spot 进入边界表给出的行权区域即被指派；call 在除息日前一日的指派由带离散股息的表给出（Phase 3）。
    - `conservative(ε)`：extrinsic < ε 即被指派。
    - `none`：不发生提前指派。
    - `on_assignment`：`close` 在下一个估值点按可成交价格处理股票；`hold` 保留股票头寸，并按股票保证金计算。
    - 到期 pin risk：实物交割时行权价 ±x% 区间内按概率 p 被指派。
    - 判定在全部路径上执行，不抽样。边界与估值用的 EEP 来自同一次 tree 计算，rational 指派时价值在边界上等于内在价值，没有跳变；`conservative(ε)` 下的跳变就是对手方放弃的时间价值。
- **Schedule（Program 模式）**：每 N 天、每周固定一天，或 regime 标签属于某个集合时入场。无条件与条件 schedule 分开配置，因为两者的验证方式不同。

### 5.10 P&L 归因

每一步用步初的 Greeks 和该步的因子变动：

```text
dV ≈ Δ·dS + ½Γ·dS² + Θ·dt + Σ_i Vega_i·dσ_i
     + Σ_i Vanna_i·dS·dσ_i + ½·Σ_i Volga_i·dσ_i² + ρ·dr
residual = dV_actual − Σ terms
```

| 桶 | 项 | 含义 |
|---|---|---|
| 已实现 | ½Γ·dS² + Θ_var·dt | 对冲后的组合约为 ½ΓS²·(x² − σ_I²·dτ_var)，x 为该步收益：赚到的方差减付出的方差 |
| 隐含 | vega、vanna、volga | IV 变化带来的 P&L，含 roll-down |
| 方向 | Δ·dS 加对冲 P&L | 对冲后剩余的 spot 敞口 |
| Carry | 利息、股息 | 融资 |
| 行权 / 指派 | `conservative(ε)` 下对手方放弃的时间价值、指派后股票头寸的 P&L；rational 判定下边界上价值等于内在价值，没有跳变 | American 腿特有 |
| 成本 | spread 与费用 | 执行 |
| 残差 | 剩余部分 | 必须很小；残差大说明步长太粗 |

它在分析层面把隐含敞口与已实现敞口分开。这不是一个对冲工具，但能看清每一美元来自哪个桶。顺序依赖的 full revaluation 瀑布分解（依次 S、σ、t、r）可用于精确对账；因为依赖顺序，默认仍用 Taylor 加残差。

### 5.11 溢价因子与 edge ledger 的精确定义

Edge ledger 的每个因子都有一个可复现的关闭态。对照组 = 当前模式下所有可开关的因子同时关闭，并使用与其他组合相同的随机数子流。

| 因子 | 开启态 | 关闭态 | 可单独开关的模式 |
|---|---|---|---|
| `drift` | `μ` 按配置 | `μ = r − q` | 所有模式 |
| `variance` | `VRP = a + b·IV`（estimator 口径）；事件 `p_var_ratio` 按配置 | `a = b = 0` 且 `p_var_ratio = 1`，即 `E^P[RV̂_n] = IV_ATM` | 所有模式 |
| `skew_dynamic` | `ssr_realized` 按配置 | `ssr_realized := ssr_priced` | 仅 `reduced_form`；structural 下 spot–vol 关系由过程参数决定，不能单独开关 |
| `skew_static` | 场景曲面的翼部（skew、曲率） | 翼部换成 P 过程在 drift 与 variance 关闭时自身隐含的曲面（P-fair wings） | 仅 `consistent_q`（Phase 4） |

- **Shapley 分解**：设当前模式下参与分解的因子集合为 F，k = |F|（structural 下 k = 2，reduced_form 下 3，consistent_q 下最多 4）。对 2^k 种组合各跑一次 MC，因子 i 的贡献为 `φ_i = Σ_{S ⊆ F∖{i}} |S|!(k−|S|−1)!/k! · [EV(S∪{i}) − EV(S)]`，满足 `Σ φ_i = EV(全开) − EV(全关)`。EV 均为成本后数值。
- **残差**：`residual = EV(全关，成本前)`。账目恒等式为 `EV(全开) = Σ φ_i + residual − costs(全关)`。在自洽设定下（例如 GBM 加平坦 smile，或曲面由同一个模型生成），残差应在 3 个标准误以内为零。
- **残差不是 bug，而是未声明的溢价**：structural 模式下翼部错价无法单独开关，它会出现在残差里。例如用 GBM 路径卖出带 skew 的 OTM put，即使 VRP = 0，残差也为正。这正是设计意图：未声明的溢价被单列出来，而不是被吸收进 variance 因子。残差显著不为零时，报告提示「场景曲面与 P 过程不一致」，用户要么解释它，要么改用能声明它的模式。
- **skew 差距的归属二选一**：`skew_gap_attribution = "premium"`（默认）时，`ssr_priced − ssr_realized` 的差距记为 `skew_dynamic` 溢价；`"jumps"` 时认为差距由跳跃补偿解释，`skew_dynamic` 恒为关闭（不计溢价），并要求过程含跳跃。配置校验强制执行。
- **共同随机数的含义**：开关因子会改变路径（例如 variance 关闭时方差水平不同），但每个组合使用相同的随机数序列，所以 EV 的差值是配对差值，标准误按逐路径差值计算（`optsim_compare`）。
- 运行次数随 k 指数增长：reduced_form 下 8 次，consistent_q 下 16 次。`ledger.factors` 可以只选其中几个；未选的因子保持开启，并在报告中注明。

---

## 6. 功能清单

- **F1 策略构建**：模板（vertical、straddle / strangle、iron condor / fly、butterfly 含 broken-wing、calendar、diagonal、ratio、risk reversal、collar、jade lizard）与自定义腿；按 delta、DTE 或 moneyness 选合约；按相同 vega、保证金、权利金或最大亏损归一化，以便公平比较（Mack & Sinclair 第 10 章正是在相同 vega 下比较 straddle、strangle 与 condor）。复用 OptionLab `core/strategies` 的工厂函数，由适配器把 `Leg` 转为 optsim 合约（补上 style、乘数、到期日期）。
- **F2 假设场景**：`MarketScenario` 参数化给定；内置预设（产品族、曲面、流动性）；Phase 3 起可从 OptionLab 历史数据校准先验；来源标签随结果保存。
- **F3 单点风险**：价值、P&L、model 与 effective Greeks、加权 vega、盈亏平衡已实现波动率、vol points 成本、EEP、两种保证金。
- **F4 风险随时间**：各时间切片的 P&L 与 Greeks 对 spot 曲线；Greeks 随日期；IV 冲击叠加；decay 投影（明天、下周一、下一个事件后）。
- **F5 情景与压力**：spot × 日期、spot × IV、IV × 日期网格；因子冲击；历史类比；PM 式网格。
- **F6 Monte Carlo**：过程 × IV 联动 × 策略 × 成本 × 保证金；参数不确定性批次；跨策略的共同随机数用于配对比较。
- **F7 归因**：逐步与累计：已实现、隐含、方向、carry、行权 / 指派、成本、残差。
- **F8 优势核算**：对照组、按因子的 Shapley ledger 与残差行（§5.11）、带盈亏平衡值的溢价曲线、tornado、模型分歧、引擎抽检。
- **F9 仓位**：模拟分布上的 Kelly、实用折减、破产风险、binding 保证金制度下的资金上限。
- **F10 Program 模式**：在长的模拟或回放路径上滚动入场：权益、回撤、资金（两种保证金制度）、重叠持仓的 Greeks。
- **F11 对比模式**：`compare` 支持 `style`、`margin`、`premia`、`engine`、`process` 五种开关，同一组随机数上并列输出两个版本与差值。
- **F12 历史回放**（Phase 4）：在真实 SPX/SPY 路径上运行策略，ATM IV 用 VIX 代理、skew 参数化，标注为 proxy。
- **F13 报告与集成**：SQLite 运行注册表与指标、产出物目录、`report.md`；后续接入 OptionLab UI 与 Notion Trade Log。
- **F14 宪章标注**：每份报告注明该结构在当前学习期宪章（v1.2 第 3 节：单腿 long、21–60 DTE、白名单标的）下是否可交易。研究报告可作为宪章第 3.3 节白名单扩展所需的「经济逻辑、风险维度、失效条件」书面材料，但不构成交易许可。

---

## 7. 工作流

### 7.1 交易前：多周 VRP 结构（主线）

示例：SPX-like 16Δ short strangle，45 DTE，权利金赚到 50% 或 21 DTE 时离场。

```text
python scripts/optsim.py grid    strangle.toml
python scripts/optsim.py mc      strangle.toml
python scripts/optsim.py compare strangle.toml --switch margin
python scripts/optsim.py sweep   strangle.toml --param vrp.b=0:0.15
python scripts/optsim.py program strangle_program.toml
```

- `grid`：随时间的风险、压力、两种保证金。
- `mc`：分布、对照组、ledger。
- `compare --switch margin`：Reg-T 与 PM 下的 return on margin、Kelly 仓位、资金约束触发概率。
- `sweep`：EV 对声明 VRP（ATM measure、estimator basis）的曲线与盈亏平衡值；默认 5,000 路径。
- `program`：滚动入场下的权益曲线、回撤与资金占用。

决策规则：把扣除成本后的盈亏平衡溢价与溢价的合理范围比较（注意口径，§5.6）。只有安全边际足够大、尾部与资本匹配、并且算出的仓位仍值得交易时才行动。

### 7.2 对比分析：style 与 margin

- **Style**（例如 SPY-like short put）：`compare --switch style` 输出 EEP、提前指派概率及其时间分布、指派后股票头寸带来的 P&L 与保证金变化。适合回答「把 SPX 换成 SPY，风险差在哪里」。
- **Margin**：同一策略在两种制度下的资本效率与约束。适合回答「在 PM 下这个仓位是否会在路径中途触发追加保证金」。
- 两种开关可以叠加（2 × 2），报告给出四格表与配对差值。

### 7.3 持仓监测（Phase 4）

- 输入：OptionLab 的 `tracked_strategies`（`legs_json`、入场快照）加一个场景：假设场景，或 yfinance 当前 spot / 当前链拟合的曲面。
- 输出：当前 Greeks、到明天 / 下周一 / 下一个事件的 decay 投影、压力网格、两种保证金、阈值告警；写入 `optsim_runs`，经 `optsim_links` 关联到该持仓。
- 买卖价快照账本（每天每个持仓的 mark、IV、曲面因子）在恢复 futu 采集后建立；它也是目前缺失的历史 IV 记录。

### 7.4 交易后复盘与模拟器校准（Phase 4）

- 用快照账本对每笔已平仓交易做归因：已实现、隐含、方向、行权 / 指派、成本。
- **PIT 检验**：把每笔实际 P&L 放进它自己的交易前模拟分布，`u_j = F_j(P&L_j)`。30 笔以上时 `u_j` 应接近 Uniform(0, 1)。两端都堆积说明尾部被低估；一端堆积说明溢价假设有偏。这是让 MC 能够替代回测、又不失诚实的那道检查。
- 每条 Notion Trade Log 记录保存其交易前 `run_id`。

### 7.5 研究

- **VRP 收割 Program**（v0.2 主线）：相同 vega 或相同保证金下比较结构；EV 对溢价的曲线；Bates 与 rough Bergomi 下的回撤与保证金路径；两种 style、两种保证金制度。
- **开盘卖期权假说**（延后到 Phase 4：需要 intraday 时钟与买卖价数据）：

| 维度 | 模拟器能提供什么 |
|---|---|
| 1. mid 价现象是否存在 | 无；这是数据问题 |
| 2. 往返成本下限 | 直接：用开盘 spread 表换算 vol points 成本 |
| 3. 可成交价格下的生存性 | 条件性：在假设的 IV 回复下给出可成交价格 P&L，以及扣除成本后的盈亏平衡回复幅度 |
| 4. 按跳空幅度与方向分层的逆向选择 | 部分：跳空条件化路径与各分层的空 gamma 风险；逆向选择本身必须测量 |

- **模型风险**：同一策略跨过程族；尾部分歧服务于 SPX/VIX 联合校准研究（rough vol 加跳跃）。

---

## 8. 验证

| 测试 | 已知答案 | 通过标准 |
|---|---|---|
| Put–call parity（European） | `C − P = D·(F − K)` | 误差 < 1e-10 |
| American 下界与界限 | `A ≥ max(E, 内在价值)`；`S·e^{−qτ} − K ≤ C − P ≤ S − K·e^{−rτ}` | 所有用例 |
| `table` 精度回归 | 相对 `tree`，随机状态（S/K 0.7–1.3，1–90 天，IV 8–80%） | 价格误差 ≤ 0.005（按行权价 100 计）；边界误差 ≤ 0.5% |
| `bs2002` 交叉检查回归 | 相对 `tree`，≤ 90 天 | call 相对误差 ≤ 0.01%；put 价格误差 ≤ 0.2（按行权价 100 计） |
| `tree` 外部参考（仅开发期，可选依赖） | QuantLib QD+ fixed-point 引擎 | 差值 ≤ 1e-3（按行权价 100 计） |
| LSMC 一致性 | 路径上的 rational 行权 ≈ `tree` 价格 | abs(z) < 3 |
| 指派判定一致性 | 按边界表的 rational 行权概率 ≈ LSMC 最优策略的行权概率 | 差值 < 3 个标准误 |
| Style 切换不变性 | 关闭提前行权的 American 路径 = European 引擎 | 完全一致 |
| OptionLab parity | q = 0、European、T ≥ 1/365 时等于 `greeks_vectorized`（价格、Δ、Γ、每 1% vega、每日 theta） | 误差 < 1e-10 |
| Greeks | 解析 = 中心差分 | 相对误差 < 1e-5 |
| 曲面无套利 | butterfly ≥ 0；总方差随 τ 递增 | 每个曲面 |
| 事件方差一致性 | 跨越事件的到期，`w(t, T)` 只在事件时刻下降 `v_e`，其余时刻连续；IV crush 等于解析值；`p_var_ratio = 1` 且 VRP = 0 时，跨事件的 delta 对冲 straddle 平均 P&L 为 0 | 精确；abs(z) < 3 |
| IV 联动不动点 | GBM 下每条路径 `IV_t = ((1 − j)σ + a)/(1 − b)`；a = b = 0 时 `E[IV − RV̂_n] = 0` | 精确；abs(z) < 3 |
| 配置校验 | `b ≥ 1`、`(1 − b)·IV_0 − a < σ_floor`、`skew_gap_attribution = "jumps"` 但过程无跳跃，均在启动时报错 | 每条规则一个失败用例 |
| 子流独立 | 改变 Jensen 预跑、子样本或引擎抽检的样本量，主路径逐位不变 | 完全一致 |
| 鞅性（Q） | μ = r − q 且 RV = IV 时 `E[D·V_t] = V_0` | abs(z) < 3 |
| 零优势，对冲 | RV = IV 时成本前平均 P&L = 0 | abs(z) < 3 |
| 离散对冲 | sd ≈ √(π/4)·Vega·σ/√N（Derman & Kamal 1999） | 偏差 10% 以内 |
| 按 RV 对冲 | P&L → V(σ_R) − V(σ_I)；sd 随 N 增大趋于 0 | 均值偏差 5% 以内 |
| Ledger 恒等式与残差 | `Σ φ_i + residual − costs = EV(全开)`；自洽设定下 residual = 0 | 精确；abs(z) < 3 |
| 配对差值标准误 | `optsim_compare` 的标准误 = 逐路径差值的样本标准差 / √n | 精确 |
| Reg-T 已知答案 | Cboe Margin Manual 的算例 | 完全一致 |
| PM 已知答案 | 10 点网格的最大损失；每张合约最低要求 | 完全一致 |
| Margin 切换不变性 | `regt` ↔ `pm` 只改变依赖保证金的输出；没有保证金触发规则时 P&L 路径不变 | 完全一致 |
| VS 接口 | `var_swap` 在实现前抛出 NotImplementedError；预留：平坦 smile 下 VS = ATM | 按状态 |
| 归因闭合 | 各项 + 残差 = dV；dt → 0 时残差 → 0 | 精确；趋势 |
| 可复现 | 相同配置与种子得到相同哈希 | 完全一致 |
| MC 收敛 | 标准误 ∝ n^(−1/2) | 斜率 −0.5 ± 0.05 |
| 对照 Program | 自洽设定下 P&L ≈ −成本 | abs(z) < 3 |
| 现实检验（PIT） | 已实现 PIT ~ Uniform(0, 1) | KS p > 0.05 |

测试遵循 OptionLab 约定：pytest、行为式命名（`test_<subject>_<expected_behaviour>`）、`tests/conftest.py` 自动隔离数据库。这些测试是数学恒等式与真实实现之间的已知答案比较，不是 mock 数据，与仓库「测试不用 mock 数据」的规则一致。需要联网的校准测试标记为 `network`。

**设计期验算**（numpy 原型，代码不进入仓库）：

| 检查 | 结果 |
|---|---|
| 盈亏平衡已实现波动率，单个期权 | IV = 0.22 时 σ_BE = 0.2200 |
| 盈亏平衡已实现波动率，带 skew 的 short strangle | 0.2359 = 各腿 IV 的 gamma 加权 RMS |
| Effective delta vs 重定价（SSR 1.5） | call 0.4571 vs 0.4571；put −0.2066 vs −0.2066 |
| 零优势，10 万路径 | N = 21 时均值 −0.0019（se 0.0013）；N = 84 时 +0.0005（se 0.0007） |
| Derman–Kamal | 模拟 sd / 公式 sd：N = 21 时 0.96，N = 84 时 0.98 |
| 按 RV 对冲 vs 按 IV 对冲（IV 20%，RV 25%，N = 500） | 均值 0.5725 与 0.5712，目标 0.5716；sd 0.112 vs 0.265 |
| 鞅性，100 万路径 | 2.2892（se 0.0023）vs 2.2872 |
| 二元正态（20 点 Gauss–Legendre）vs scipy | 最大误差 1e-16 |
| BS2002 vs `tree`（每类 270 个用例：S/K 0.8–1.2，7–365 天，IV 15–60%，q 0–3%） | call 最大相对误差 0.005%（≤ 90 天）；put 0.9%（≤ 45 天）、1.4%（≤ 90 天）、2.4%（≤ 365 天）；BS2002 系统性偏低 |
| BS2002 行权边界 vs 真实边界（put，IV 15–40%，30–90 天） | 偏高 0.45%–5.7% |
| `tree` vs QuantLib QD+ fixed-point | put ≤ 6.0e-4，call ≤ 4.4e-5 |
| `table` vs `tree`（400 个随机状态：S/K 0.7–1.3，1–90 天，IV 8–80%） | 最大误差 0.0028，平均 0.0002（按行权价 100 计）；同一组状态 BS2002 为 0.16 与 0.0074 |
| `table` 边界 vs 真实边界 | −0.22% 至 +0.08% |
| `table` 构建与查表 | 构建 1.9 秒（33 个 σ × 90 天）；查表约为 European 的 2.2 倍 |
| LSMC（20 万路径，逐日行权）vs `tree`，45 天 put | ATM：2.6225（se 0.0072）vs 2.6277；10% ITM：10.0899（se 0.0077）vs 10.0951 |
| BS2002 吞吐 | 每 100 万次 6–9 秒（European 的 60–80 倍） |
| RV̂（21 天，close-to-close）偏差 | GBM：−0.14 / −0.19 / −0.35 vol points（σ = 12% / 16% / 30%）；Heston（κ 3，ξ 0.6，ρ −0.7，σ 16%）：−0.78 |
| Reg-T vs PM | 见 §5.8 示例表 |
| VS level vs ATM IV | 见 §5.6 gap 表 |

---

## 9. 与 OptionLab 现有模块的关系

| 模块 | 关系 | 说明 |
|---|---|---|
| `core/strategies`（`Leg`、工厂函数） | 输入适配 | `Leg` → optsim 合约，补上 style、乘数、到期日期 |
| `core/options/greeks/black_scholes` | parity 基准 | optsim 的 European 引擎带 q、远期、到期处理，另行实现；用 parity 测试锁定一致，不修改现有模块 |
| Simulation tab（`core/options/simulation`，ADR 0008；`static/sim`） | 互补 | 现有功能是单期到期 payoff，带「entry IV vs forward vol」双 IV；optsim 把它推广到逐路径盯市。GBM 下设 VRP = σ_entry − σ_fwd，optsim 的到期结果退化为现有 tab 的结果，可以作为一条 parity 测试 |
| Option Pricing Matrix（`static/sim/option_pricing_matrix.js`） | 约定复用 | spread 偏移 `max(mid × spreadPct/200, 0.01)` |
| `core/options/simulation/expiry_calendar` | 复用 | NYSE 假日近似 → variance clock；提升为 `core/_shared` 公共函数 |
| `data_pipeline/read`（`DataService`） | 校准输入 | 经 provider seam 读取 SPY、^GSPC、^VIX 的 OHLCV（Phase 3） |
| `regime_log` | 条件先验 | `vol_regime` / `dir_regime` → 分 regime 的先验 |
| `tracked_strategies` | 后续 | 持仓监测输入（Phase 4） |
| Notion Trade Log | 后续 | 保存 `run_id` 与摘要；Formula / Rollup 字段永不进入推送载荷 |
| futu-api | 延后 | 快照与 spread 表适配器（Phase 4）；按 `docs/plans/futu_provider_integration.md` 的 provider seam 接入 |
| 学习期宪章 v1.2 | 标注 | 报告标注宪章状态（F14） |

**落地时需同步更新的仓库文档**（按 `AGENTS.md` 的约定，在同一次提交中完成）：

- `docs/decisions/0013-optsim-scenario-engine.md`（已存在）：引入 MC、SQLite 多表结构加 `.npz` 产出物、场景来源标签、American `table` 引擎等新边界时，在其中追加或新开 ADR；然后运行 `scripts/regen_adr_index.py`。
- `docs/glossary.md`：VRP（measure 与 basis）、SSR、variance clock、EEP、Reg-T、portfolio margin、ATM IV vs variance-swap level、edge ledger 与残差；同时更新 Greeks 条目中「假设 European exercise」的说明，指出 optsim 支持 American。（Reg-T、PM、BPR、sticky-strike 与 Greeks 条目已在 2026-10-19 更新。）
- `docs/constraints.md`：MC 只在 CLI 离线运行；假设场景必须带来源标签。
- `docs/architecture_review.md` §3 层表、`docs/l0_architecture.md`（`data/optsim/`）、`.gitignore`。
- `AGENTS.md`、`CLAUDE.md`、`CODEBUDDY.md` 的摘要镜像；最后运行 `doc_guard.py` 与 `arch_metrics.py --check`。

---

## 10. 路线图

> 现状（2026-10-20）：Phase 1 的最小子集（European + American grid、两种 margin、CLI）与 Phase 5 的 Grid 标签页
> 已完成；其余未开始。实际执行顺序以 [optsim.md](optsim.md) §5 为准。

| 阶段 | 范围 | 退出标准 |
|---|---|---|
| 0 规格 | 本文档；ADR 0013；TOML 配置 schema（含 §5.6 与 §5.11 的校验规则）；预设；测试夹具 | ADR 状态为 Accepted |
| 1a European 基线 | domain 与 product profile（`style` 键已在 schema 中，选 `american` 时明确提示「1b 交付」）；European 引擎与 Greeks；参数化曲面加 SSR 与时间规则；variance clock（日频、事件只计一次、NYSE 交易日历）；Reg-T 与 PM（并列输出）；Grid 引擎；SQLite 多表结构与产出物；CLI `grid` | 对 `greeks_vectorized` 的 parity、Greeks、无套利、事件方差一致性、Reg-T / PM 已知答案测试通过；European Grid < 1 秒；产出物可复现 |
| 1b American 增量 | `tree`（参考）、`table`（默认）、`bs2002`（交叉检查）；Grid 上的行权区域与边界输出；American 腿的 PM 重估；通用 `compare` 引擎与 `--switch style` | American 界限、`table` 与 `bs2002` 精度回归、style 切换不变性测试通过；American Grid（含表格构建）< 3 秒 |
| 2 MC 核心（日频） | GBM、Merton；structural IV 联动（显式不动点、estimator 口径、Jensen 预计算）；`SeedStreams`；策略含行权与指派（边界表判定，全部路径）；参数化成本；归因；指标；ledger（drift、variance 加残差）；两种制度的保证金路径；引擎抽检 | 鞅性、零优势、离散对冲、归因闭合、LSMC 与指派判定一致性、不动点、子流独立、ledger 恒等式测试通过；实测各档预算 |
| 3 VRP 研究 | Heston / Bates（含 `j(v, τ)` 表）；reduced-form 联动与 `skew_dynamic` 因子；先验与基于 yfinance 历史的校准（SPY、^VIX）；Program 模式；Kelly 仓位；离散股息 | 对照 Program 测试通过；产出校准报告 |
| 4 数据与扩展 | `consistent_q` 与 `skew_static` 因子；VS level（按需）加基于 VIX 的 VRP_VS 校准；rough Bergomi；SSVI 拟合（可用 yfinance 当前链）；futu 适配器（快照、spread 表）；intraday 时钟与开盘跳空研究；`tracked_strategies` 监测；PIT 复盘 | 第一份已平仓交易的 PIT 报告 |
| 5 UI | OptionLab 中的新 tab（HTMX fragment，只读已持久化的运行） | 延后 |

- **拆分 1a / 1b 不改变决策 1**（两种 style 同等重要）。European 是 `table` 引擎的 control variate，也是 parity 与已知答案测试的基础，所以先做 European 是依赖顺序，不是优先级。1b 只在 1a 的接口上增量接入，不改动 1a 的接口。
- 1a 的 Grid 已经并列输出两种保证金，所以通用 `compare` 引擎放在 1b，随 style 对比一起交付。
- 路径上的行权与指派策略（事件、股票头寸、`on_assignment`）属于 MC，放在 Phase 2；1b 在 Grid 上只输出行权区域与边界。边界表在 1b 就已建好，Phase 2 直接使用。
- 只做完 1a，就能对 European 产品确定性地回答核心问题；1b 把同样的回答扩展到 American；Phase 2 给出随机性的答案；Phase 3 让多周 VRP 研究完整可用。

---

## 11. 局限与决策记录

### 11.1 已知局限

- 模拟器只会复现假设的溢价；EV 的可信度取决于声明的溢价。溢价存在的证据来自数据（例如已实现 VRP 的历史），永远不来自模拟器。
- ATM 口径的 VRP 仍未经校准（§5.6）。在 VS 接口落实或期权数据恢复采集之前，所有 EV 结论都必须连同对 `vrp.a`、`vrp.b` 的 sweep 一起阅读。
- VRP 的 estimator 口径依赖 RV 的定义（天数、是否去均值、频率）；与外部数据比较时必须使用同一定义，否则会混入估计量偏差（21 天时约 0.2–0.8 vol points）。
- `skew_static` 在 Phase 4 之前不能单独开关，翼部错价只以残差出现。
- 尾部结果依赖模型；一个决策至少要在两个过程族下都成立。
- `table` 引擎的精度依赖 σ 网格与 x 网格；状态超出网格（σ > 150% 或极端 moneyness）时截断，并在引擎抽检中标记。BS2002 只作交叉检查，系统性低估 American put 的价值。
- PM 是 TIMS 风格的代理，与券商实际的 IV 冲击、集中度附加和 house 规则可能不同。
- 参数化 spread 是假设；微观结构（成交、逆向选择、开盘错位）只能以估计的参数进入。
- 实物交割的 pin risk 与 AM 结算跳空都是近似处理。
- 基于 VIX 的回放假设参数化 skew，是代理而不是基于真实期权价格的回测。
- 先验是主观的；批次设计暴露这种主观性，但不消除它。
- §4.7 的完整研究预算是按吞吐估算的，未含路径生成与策略逻辑开销，需在 Phase 2 实测。

### 11.2 决策记录（v0.2）

| # | 问题 | 决定 | 对设计的影响 |
|---|---|---|---|
| 1 | 主要产品 | European 与 American 同等重要，需一键切换 | `style` 与 `product.profile` 两级开关；`compare = "style"`；American 引擎 `table`（默认）、`tree`（参考）、`bs2002`（交叉检查）；行权与指派按边界表判定；Phase 1a / 1b 先后交付两种 style（v0.3） |
| 2 | 首要研究周期 | 多周 VRP 结构 | 默认日频；Program 模式提前到 Phase 3；intraday 与开盘研究延后到 Phase 4 |
| 3 | 保证金制度 | Reg-T 与 PM 同等重要，需一键切换 | `margin.model` 定 binding，`margin.compare` 默认并列；Phase 1 同时交付两种 |
| 4 | futu 买卖价快照 | 延后；模拟器针对假设期权分析 | `MarketScenario` 完全参数化并带来源标签；spread 参数化；futu 适配器移到 Phase 4 |
| 5 | 存储 | 作为 OptionLab 子功能 | `core/optsim` + `services/optsim` + `data_pipeline/store`；SQLite 注册表加 `.npz`；TOML 配置；CLI 离线；ADR 0013 |
| 6 | VRP 校准口径 | ATM IV 与 variance-swap level 都需要；ATM IV 优先，VS 留接口 | `ImpliedMeasure` 协议；`atm_iv` 实现，`var_swap` 预留并显式报错；文献数值标注 VS 口径 |

### 11.3 审查意见处理（v0.3）

| # | 审查意见 | 处理 | 理由与证据 | 落点 |
|---|---|---|---|---|
| 1 | Phase 1 过重，拆为 1a / 1b | 采纳，细化 | 拆分是依赖顺序而不是优先级（European 是 `table` 的 control variate 与 parity 基准）；路径上的行权与指派仍属 Phase 2；通用 `compare` 随 1b 交付，因为 1a 的 Grid 已并列输出两种保证金 | §10 |
| 2 | short American 指派判定用 `tree` 或 `eep_table` 复核；`eep_table` 提前到 Phase 2；默认报告引擎分歧 | 修正前提后采纳，并更进一步 | 实测 BS2002 边界偏高 0.45%–5.7%，会让 short put 过早被指派、P&L 偏乐观，与「低估尾部指派」方向相反。`table` 引擎的误差比 BS2002 小 40–60 倍、查表成本约为 European 的 2.2 倍，所以直接在 1b 作为默认引擎；决策只用边界表；引擎抽检默认开启 | §5.1、§5.9、§8 |
| 3 | 性能预算分档；ledger 与 sweep 默认 European；子样本分别生效 | 部分采纳 | 三档预算已给出。有了 `table` 引擎，American 完整研究约 1–2 分钟，ledger 与 sweep 不必默认降级为 European（保留为选项）。子样本只用于诊断量：行权与指派改变 P&L，必须在全部路径上执行，不能按建议抽样统计 | §4.7 |
| 4 | 零溢价与 Shapley 开关的精确定义 | 采纳 | 四个因子逐一给出关闭态与可单独开关的模式；增加残差行与账目恒等式；skew 差距的归属二选一，由配置校验强制 | §5.11 |
| 5 | IV 联动的不动点、参数域、Jensen 预跑、事件方差 | 采纳并扩展 | 显式解 `IV = ((1 − j)σ̄ + a)/(1 − b)`；参数域校验；VRP 允许为负；Jensen 预计算用独立子流并制表；实测估计量偏差 0.2–0.8 vol points，因此区分 integrated 与 estimator 两个口径。另发现 v0.2 在 variance clock 与总方差中重复计入了事件方差，已改为只计一次，并补上 P 侧事件方差与已知答案测试 | §5.3、§5.4、§5.6、§8 |
| 6 | 指标主键维度不够 | 采纳 | 规范化为 variants、metrics、series、compare、ledger 五张表；配对差值单独存储，因为它的标准误不能由各变体的标准误推出 | §4.6 |

### 11.4 仍待确认

1. 以哪家券商的规则为准：Reg-T 的 house 附加、PM 的 IV 冲击与最低权益。这决定 `margin.house` 的默认参数。
2. 是否把 American 引擎（`tree` 与 `table`）提升为 OptionLab 公共模块（例如 `core/options/pricing/`），供期权链分析等功能使用。这会影响现有 `greeks_vectorized` 的使用方，需要单独的 ADR，可以等 1b 之后决定。

---

## 附录 A. 示例配置（TOML）

> 这是**目标 schema**，与当前 CLI 不同；当前 CLI 的 schema 见 `docs/optsim/examples/*.toml` 与 [optsim.md](optsim.md) §1.3。

```toml
[run]
name = "spx-short-strangle-16d-45dte"
seed = 20261019             # 根种子；子流由 SeedSequence 派生

[product]
profile = "index_eu_cash"   # 产品族开关
# style = "american"        # 行权方式开关，覆盖 profile

[strategy]
normalize = { by = "vega", target = -500 }

[[strategy.legs]]
type = "put"
qty = -1
select = { delta = -0.16, dte = 45 }

[[strategy.legs]]
type = "call"
qty = -1
select = { delta = 0.16, dte = 45 }

[scenario]
source = "hypothetical"
spot = 6000.0
rate = 0.045
div_yield = 0.013

[scenario.surface]
atm = 0.16                  # 期限结构平坦
skew_ref = -0.9             # τ_ref = 30 天
skew_decay = 0.4
curvature = 1.0
wing_clip = [0.5, 3.0]      # 乘以 σ_ATM

[scenario.dynamics]
ssr_priced = 2.0
ssr_realized = 1.5
time_rule = "constant_maturity"
skew_gap_attribution = "premium"   # 或 "jumps"

[clock]
mode = "variance"
nontrading_weight = 0.1
events = [
  { date = "2026-12-09", kind = "FOMC", move_sd = 0.01, p_ratio = 1.0 },
]

[process]
model = "bates"
prior = "spx_bates_v1"

[ivlink]
mode = "structural"
iv_floor = 0.01

[ivlink.vrp]
measure = "atm_iv"          # "var_swap" 已预留，尚未实现
basis = "estimator"         # 或 "integrated"
rv_days = 21                # close-to-close，零均值，×252
a = 0.0
b = 0.05                    # 示例值：声明的先验，必须 sweep

[ivlink.jensen]
paths = 20000               # 独立子流；每个参数批次一张表

[management]
exit = { profit_target = 0.50, stop_loss = 2.0, dte = 21 }
hedge = { mode = "none" }
exercise = { long = "rational", short = "rational" }
on_assignment = "close"

[execution]
spread_pct = 0.03           # 假设值，待 futu 快照校准
tick = 0.05
fill_alpha = { entry = 0.5, exit = 0.5, stop = 1.0 }
fees_per_contract = 0.0     # 按券商填写

[margin]
model = "regt"              # 约束制度："regt" 或 "pm"
compare = true
pm = { points = 10, iv_rule = "sticky_strike", path_mode = "subsample" }

[pricing]
american_engine = "table"   # 或 "tree"、"bs2002"
table = { sigma_min = 0.05, sigma_max = 1.5, sigma_points = 33 }

[simulation]
batches = 200               # 参数抽样次数
paths_per_batch = 100
step = "1d"
antithetic = true

[subsample]
greeks = 2000
pm = 2000                   # PM 为约束且有保证金触发规则时改为全部路径
engine_check = 200          # 抽检的状态数

[ledger]
factors = ["drift", "variance"]   # structural 下可开关的因子
# style_override = "european"     # 提速选项；EEP 敏感时不要用

[sweep]
paths = 5000

[compare]
switch = "style"   # style | margin | premia | engine | process
```

- `pm.range` 不必配置：它由 product profile 决定（`index_eu_cash` 为 −8% / +6%）。
- 事件的 `move_sd` 是事件当天涨跌幅的标准差，`v_e = move_sd²`；`p_ratio` 即 §5.3 的 `p_var_ratio`。事件日期是示例占位。
- 配置展开时执行 §5.6 与 §5.11 的全部校验规则，违反即报错。

## 附录 B. 公式参考

```text
Generalized BSM（carry b = r − q），D = exp(−r·τ_cal)
  w  = σ²·τ_var + Σ v_e
  d1 = (ln(S/K) + b·τ_cal + w/2) / √w      d2 = d1 − √w
  C  = S·e^{(b−r)τ_cal}·N(d1) − K·D·N(d2)
  P  = K·D·N(−d2) − S·e^{(b−r)τ_cal}·N(−d1)

American put–call 对称（McDonald & Schroder 1998）
  C_A(S, K, τ, r, q, σ) = P_A(K, S, τ, q, r, σ)

American 界限
  A ≥ max(European, 内在价值)
  S·e^{−qτ} − K ≤ C_A − P_A ≤ S − K·e^{−rτ}

固定行权价 IV 在 SSR 下的变化
  dσ_ATM = SSR·β·dlnS          dσ(K) = (SSR − 1)·β·dlnS

Effective delta（vega 以单位波动率计）
  Δ_eff = Δ + Vega·(SSR − 1)·β / S

Minimum-variance delta（Hull & White 2017；a, b, c 回归得到）
  δ_MV = δ_BS + Vega/(S·√T)·(a + b·δ_BS + c·δ_BS²)

盈亏平衡已实现波动率（Θ_var 按年，不含 carry）
  σ_BE = √(−2·Θ_var / (Γ·S²))

加权 vega
  Vega_w = Σ_i Vega_i·(τ_ref/τ_i)^p      p = 0.5，τ_ref = 30d

按隐含波动率连续对冲的 P&L
  P&L_T = ∫ exp(r(T−t))·½·Γ_t·S_t²·(σ_R,t² − σ_I²) dt

离散对冲误差，N 次调仓（Derman & Kamal 1999）
  sd(P&L) ≈ √(π/4)·Vega·σ / √N

以 vol points 计的成本
  cost_vp = (2·α·h + fees) / vega_per_vol_point

Reg-T 裸卖（p = 15% 指数 / 20% 个股，× 杠杆倍数）
  call: prem + max(p·S − OTM, 0.10·S)
  put:  prem + max(p·S − OTM, 0.10·K)
  straddle / strangle: max(两侧要求) + 另一侧 prem

PM（10 个估值点 x_j，区间由产品决定）
  req = max( max_j [V(S) − V(S·(1+x_j))], 0.375·m·Σ|n_i| )

Variance-swap level（预留接口）
  K_var = (2e^{rτ}/τ)·[∫_0^F P(K)/K² dK + ∫_F^∞ C(K)/K² dK]
  VRP_ATM = VRP_VS − (√K_var − σ_ATM)

IV 联动不动点（estimator 口径，VRP = a + b·IV，b < 1）
  IV_t = ((1 − j)·σ̄_t + a) / (1 − b)
  σ̄_t  = √(E_t^P[∫_t^{t+τ} v ds] / τ)
  GBM：j = 1 − c(n)，c(n) = √(2/n)·Γ((n+1)/2) / Γ(n/2)

事件方差（只计一次；τ_var 不含事件日加权）
  w(t, T) = σ_base²·τ_var(t, T) + Σ_{t < t_e ≤ T} v_e
  v_e^P   = v_e · p_var_ratio

table 引擎（put；call 用对称关系）
  P_A = max(K − S, P_E(S, K, τ) + K·EEP(ln(S/K), τ; σ))
  行权区域：ln(S/K) ≤ b(τ; σ)

Edge ledger（因子集合 F，k = |F|，EV 为成本后）
  φ_i = Σ_{S⊆F∖{i}} |S|!(k−|S|−1)!/k!·[EV(S∪{i}) − EV(S)]
  EV(全开) = Σ_i φ_i + residual − costs(全关)
  residual = EV(全关，成本前)

Kelly（R = 交易 P&L / binding 制度下的资本占用）
  f* = argmax_f E[ln(1 + f·R)]  ≈  E[R] / Var[R]

已平仓交易 j 的 PIT（F_j 为其交易前模拟 CDF）
  u_j = F_j(P&L_j)；若 u ~ Uniform(0, 1) 则校准良好
```

## 附录 C. 变更记录

### v0.3 入库（2026-10-20）

- 文件移入仓库 `docs/plans/optsim_design.md`；正文不变，只加了状态说明（文首、§4、§5.8 示例、§10、附录 A）并把 ADR 文件名改为实际的 `0013-optsim-scenario-engine.md`。

### v0.2 → v0.3

- **审查意见**：处理一份计划审查报告的 6 条意见，逐条记录在 §11.3。
- **路线图**：Phase 1 拆为 1a（European 基线）与 1b（American 增量）。
- **American**：新增 `table` 引擎并设为默认；行权与指派只用边界表；BS2002 降为交叉检查；引擎抽检默认开启。
- **性能**：预算分 European、American、American + PM 三档；子样本只用于诊断量，行权与指派在全部路径上执行。
- **Ledger**：新增 §5.11，逐一定义溢价因子的关闭态，增加残差行与账目恒等式。
- **IV 联动**：显式不动点与参数域校验；RV 分 integrated 与 estimator 两个口径；Jensen 预计算用独立子流（`SeedStreams`）。
- **修正**：v0.2 在 variance clock 与总方差中重复计入事件方差，改为只计一次；补充 P 侧事件方差（`p_var_ratio`）。
- **存储**：指标改为 variants、metrics、series、compare、ledger 多表结构。

### v0.1 → v0.2

- **语言**：按项目约定改为中文正文、英文术语。
- **决策 1–6**：分别落在 §5.1、§5.4 与 §10、§5.8、§3.1 与 §5.7、§4、§5.6；汇总见 §11.2。
- **存储**：parquet / netCDF（xarray）改为 SQLite 注册表加 `.npz`；YAML 改为 TOML。原因：作为 OptionLab 子功能不新增依赖。
- **UI**：v0.1 中的 OptionView 即 OptionLab 的 Flask 前端；UI 改为 Phase 5 的一个 OptionLab tab，只读已持久化结果。
- **执行模型**：明确 MC 只在 CLI 离线运行（OptionLab constraints 第 6 节）。
- **路线图**：两种 style 与两种保证金制度都进入 Phase 1；Program 模式提前到 Phase 3；intraday、开盘跳空研究与 futu 适配器移到 Phase 4。
- **VRP**：口径显式化；文献数值标注为 VS 口径；新增 VS–ATM gap 的计算与换算关系。
- **新增**：American 引擎设计与精度证据、行权与指派策略、Reg-T / PM 规则表与示例、`compare` 模式、宪章标注、OptionLab 集成表与文档同步清单。

## 参考文献

- Mack, A. & Sinclair, E. (2024). *Retail Options Trading*（项目参考书；第 2、7、10、17、19 章）。
- Sinclair, E. (2020). *Positional Option Trading*. Wiley.
- Bergomi, L. (2016). *Stochastic Volatility Modeling*. CRC Press.
- Gatheral, J. (2006). *The Volatility Surface*. Wiley.
- Derman, E. (1999). Regimes of volatility. *Risk*.
- Derman, E. & Kamal, M. (1999). When you cannot hedge continuously: the corrections of Black–Scholes. *Risk*.
- Ahmad, R. & Wilmott, P. (2005). Which free lunch would you like today, Sir? Delta hedging, volatility arbitrage and optimal portfolios. *Wilmott Magazine*.
- Hull, J. & White, A. (2017). Optimal delta hedging for options. *Journal of Banking & Finance*.
- Bjerksund, P. & Stensland, G. (2002). Closed form valuation of American options. Working paper, NHH.
- Cox, J., Ross, S. & Rubinstein, M. (1979). Option pricing: a simplified approach. *Journal of Financial Economics*.
- Longstaff, F. & Schwartz, E. (2001). Valuing American options by simulation: a simple least-squares approach. *Review of Financial Studies*.
- McDonald, R. & Schroder, M. (1998). A parity result for American options. *Journal of Computational Finance*.
- Andersen, L., Lake, M. & Offengelden, D. (2016). High-performance American option pricing. *Journal of Computational Finance*.
- Gatheral, J. & Jacquier, A. (2014). Arbitrage-free SVI volatility surfaces. *Quantitative Finance*.
- Bayer, C., Friz, P. & Gatheral, J. (2016). Pricing under rough volatility. *Quantitative Finance*.
- Bennedsen, M., Lunde, A. & Pakkanen, M. (2017). Hybrid scheme for Brownian semistationary processes. *Finance and Stochastics*.
- Whalley, A. E. & Wilmott, P. (1997). An asymptotic analysis of an optimal hedging model for option pricing with transaction costs. *Mathematical Finance*.
- French, K. & Roll, R. (1986). Stock return variances: the arrival of information and the reaction of traders. *Journal of Financial Economics*.
- Cboe, Strategy-based Margin（裸卖比例、straddle / strangle、long 期权）：https://www.cboe.com/us/options/strategy_based_margin
- Cboe, Margin Manual（价差、iron condor / butterfly、ETF 与杠杆 ETF）：https://cdn.cboe.com/resources/membership/Margin_Manual.pdf
- Cboe, Margin Requirement Examples（strategy-based vs portfolio 示例；SPY 适用 −8% / +6%）：https://cdn.cboe.com/resources/membership/Margin_Requirement_Examples.pdf
- NASD Notice to Members 07-11（portfolio margin：10 个估值点、区间、每张合约 0.375 × 乘数）：https://www.finra.org/sites/default/files/NoticeDocument/p018677.pdf
- Cboe, Customer Portfolio Margin FAQ：https://res-certification.cboe.com/resources/regulation/circulars/general/IC-CBOE-2007-061.pdf
- OptionLab 仓库：`AGENTS.md`、`docs/constraints.md`、`docs/decisions/`（ADR 0001、0003、0004、0008、0011）、`docs/glossary.md`、`docs/options_learning_charter_v1_2.md`。
