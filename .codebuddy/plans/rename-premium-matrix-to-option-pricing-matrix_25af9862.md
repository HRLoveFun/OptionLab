---
name: rename-premium-matrix-to-option-pricing-matrix
overview: 将 "Premium Matrix" 模块整体重命名为 "Option Pricing Matrix"（期权定价矩阵），包括文件名、DOM id、CSS 类与变量前缀、JS API、面板状态键、测试用例名、文档描述，并重新构建 GitHub Pages 静态站点。
todos:
  - id: rename-files
    content: 用 git mv 重命名 6 个源码文件为 option_pricing_matrix 系列
    status: completed
  - id: update-js-engine
    content: 用 [skill:lsp-code-analysis] 校验引用后，改造引擎与 DOM 层 JS 及 black_scholes 注释
    status: completed
    dependencies:
      - rename-files
  - id: update-css-templates
    content: 批量更新 styles.css 的 pm- 前缀与两个模板文件的 id、文案、data 属性
    status: completed
    dependencies:
      - rename-files
  - id: update-backend-and-tests
    content: 更新后端 docstring、构建脚本 REDIRECTS 与四个测试文件的选择器
    status: completed
    dependencies:
      - rename-files
  - id: update-docs
    content: 改写 README.md 与 docs/glossary.md 中的模块名与文件路径
    status: completed
    dependencies:
      - rename-files
  - id: rebuild-and-verify
    content: 重建 site/ 并跑 ruff、pytest、vitest、doc_guard、arch_metrics 全量校验
    status: completed
    dependencies:
      - update-js-engine
      - update-css-templates
      - update-backend-and-tests
      - update-docs
---

## 产品概述

将「期权定价矩阵」模块的名称从 `Premium Matrix` 统一调整为 `Option Pricing Matrix`。该模块是仪表盘中的一个纯前端计算 Tab：用户输入 4 个假设参数（标的价格、隐含波动率、无风险利率、买卖价差），页面用 Black-Scholes 模型实时算出一整张期权价格网格。

## 模块功能内容

- **输入区**：价格、隐含波动率%、无风险利率%、买卖价差% 四个输入框，外加 Recalculate 按钮。
- **主指标区**：ATM 溢价率（hero 指标）+ 1σ 波动、ATM call、ATM put、网格规模四张 KPI 卡片。
- **矩阵主体**：行为行权价阶梯，列为到期期限（DTE）；每格左右拆分为 Call / Put 两半，各显示成交价与溢价率（达到盈亏平衡所需的标的涨跌幅）。
- **开关区**：Price / Prem. rate / Call / Put 四个数值与方向开关（纯样式切换，不重算）；Buy at ask / Sell at bid 二选一方向开关（改变计价基准，会重算）。
- **图例区**：说明溢价率算法、买卖价差如何影响成交价、X/Y 轴含义与键盘交互。

## 本次调整范围

- **用户可见文案**：Tab 按钮标签、面板标题、功能描述、加载/错误/空态提示、无障碍标签（aria-label）。
- **内部标识**：JS 文件名、模板文件名、测试文件名、DOM id、CSS 类名与变量前缀、全局对象与函数名、面板状态键。
- **项目文档**：README、术语表、后端 docstring 与注释、Pages 构建脚本中的展示名与路由别名。
- **视觉效果**：本次**不改变**任何视觉设计、布局、配色与交互逻辑，仅更换命名与文案措辞。

## 技术栈选型

沿用 OptionLab 现有技术栈，不引入任何新依赖：

- **后端**：Python 3.12 + Flask（本次仅改 docstring / 注释，无逻辑改动）
- **前端**：原生 ES Module + Alpine（`panelState` 四态机）+ Jinja2 模板 + HTMX，无构建步骤、无 React/Vue
- **静态站点**：`scripts/build_pages_site.py` 从模板生成 GitHub Pages 站点（CDN-only 依赖）
- **测试**：pytest（后端）、vitest + jsdom（前端单元）、Playwright（E2E，可选）
- **质量门禁**：ruff、`scripts/doc_guard.py`、`scripts/arch_metrics.py`、`scripts/audit_tags.py`

## 实施方案

### 总体策略

这是一次**纯命名重构**：先 `git mv` 改名保留文件历史，再按固定映射表做**词边界**批量替换，最后统一重建 Pages 站点并跑全量校验。不改变任何计算逻辑、DOM 结构、CSS 属性值与分层依赖关系。

### 标识符映射表（全量套用，不得遗漏）

| 旧标识 | 新标识 | 出现形态 |
| --- | --- | --- |
| `Premium Matrix` | `Option Pricing Matrix` | 显示名、文档标题 |
| `premium matrix` | `option pricing matrix` | 句中/句首小写文案 |
| `premium_matrix` | `option_pricing_matrix` | snake_case（面板键、文件名、include 路径） |
| `premium-matrix` | `option-pricing-matrix` | kebab-case（DOM id、URL slug） |
| `premiumMatrix` | `optionPricingMatrix` | camelCase |
| `PremiumMatrix` | `OptionPricingMatrix` | 全局对象 |
| `buildPremiumMatrix` | `buildOptionPricingMatrix` | 引擎导出函数 |
| `loadPremiumMatrix` | `loadOptionPricingMatrix` | 面板加载入口 |
| `pm-` | `opm-` | CSS 类、CSS 自定义属性、DOM id 前缀 |
| `data-pm-toggle` / `data-pm-side` / `data-action="pm-run"` | `data-opm-toggle` / `data-opm-side` / `data-action="opm-run"` | 自定义 data 属性 |


### 关键决策与取舍

1. **CSS 前缀选 `opm-` 而非 `pricing-`**：与项目已有的 `sim-` 短前缀风格一致，且 `opm-` 与既有 `pm-` 长度相近，不会撑大选择器与内联样式体积。已验证 `pm-` 仅存在于 `static/styles.css`、`static/premium_matrix.js`、`templates/partials/tab_premium_matrix.html` 三个文件，且**不存在** `xpm-` 形态（如 `ppm-`），但替换时仍强制使用词边界正则 `\bpm-` 以防误伤。

2. **「premium rate」（溢价率）指标名保持不动**：这是模块内部的领域术语（盈亏平衡所需涨跌幅，`(K+P−S)/S`），**不是**模块名。图例说明、`Prem. rate` 开关标签、`pm-*` 中的 `premium` 语义标识符均不参与本次重命名——这是本次改动最大的误伤风险点，必须逐处人工确认。

3. **后端只改注释不改接口**：`core/options/simulation/expiry.py`、`services/options/simulation.py`、`routes/options.py` 中的 `Premium Matrix` 仅出现在 docstring 里（描述 `/api/expiry_calendar` 的用途）。API 路径、请求参数、响应字段一律不动，保证向后兼容。

4. **`site/` 只重建不手改**：`site/index.html` 与 `site/premium-matrix/index.html` 均由 `scripts/build_pages_site.py` 生成且已纳入 git 跟踪。旧目录需 `git mv`，新产物由脚本生成，禁止手写编辑。

5. **保留 `.codebuddy/plans/premium-matrix-mvp_c3cf394f.md` 原名**：历史 plan 归档，保留以维持决策记录可追溯性。

### 性能与可靠性

- 本次无计算逻辑改动，网格计算性能（每列缓存 `√T`/`e^(−rT)`、每行缓存 `ln(S/K)`、put 由 call 经平价关系推导、按输入签名 memo）保持不变。
- 重命名后 `static/option_pricing_matrix.js` 与 `static/sim/option_pricing_matrix.js` 的加载顺序与模块依赖不变，`templates/index.html` 中两处 `<script>` 引用需同步更新，否则页面会 404 并导致 Tab 无法初始化。

### 避免技术债

- 复用项目既有的重命名安全边界：`.github/data/arch_baseline.json` 仅记录聚合计数（`layer_violations`/`cycles`/`god_files`/`dead_code_candidates`），**无文件级条目**；`tag_baseline.json` 亦无 premium 条目 → **本次重命名不需要更新任何 CI 基线**。
- 保留所有源文件头部的 `Domain / Context / Contracts / Dependencies` docstring 标签块格式，`scripts/doc_guard.py` 的 L1 不变量依赖该结构。

## 执行细节（落地要点）

1. **替换顺序**：先 `premium-matrix` → 再 `premium_matrix` → 再 `PremiumMatrix` → 再 `premiumMatrix` → 再 `Premium Matrix`/`premium matrix` → 最后 `\bpm-`。各模式互不重叠，顺序本身非强制，但固定顺序便于复核。
2. **文案需人工润色**，不能纯机械替换。关键几处：

- 标题：`<h2>Premium Matrix</h2>` → `<h2>Option Pricing Matrix</h2>`
- 面板描述：开头的 `A hypothetical premium-rate grid` 保留（描述的是网格内容），但句中 `premium matrix` 措辞改为 `option pricing matrix`
- 加载态：`Computing the premium matrix...` → `Computing the option pricing matrix...`
- 空态中文：`即可生成溢价率矩阵` → `即可生成期权定价矩阵`
- 无障碍：`aria-label="Premium matrix key metrics"` → `aria-label="Option pricing matrix key metrics"`
- `aria-label="Recalculate the premium matrix"` → `aria-label="Recalculate the option pricing matrix"`

3. **测试断言同步**：`tests/e2e/test_option_pricing_matrix.py` 内的选择器、`tests/e2e/test_smoke.py` L22、`tests/test_pages_build.py` L24 的 tab id 列表必须一并更新，否则 E2E 与构建断言会失败。
4. **构建脚本两处**：`scripts/build_pages_site.py` 的 `REDIRECTS`（L49，slug 与展示名）与 tab id 断言列表（L350）。
5. **`window.OptionPricingMatrix` 是动态全局**：text grep 可能漏掉动态拼接的引用，需借助语义引用分析确认。

## 架构设计

本次为命名重构，**架构与分层保持不变**。仍遵循 OptionLab 的单向依赖流：

```
app.py → routes/ → services/ → core/ → data_pipeline/ → utils/
```

该模块的运行链路不受影响：

- **纯计算层**：`static/sim/option_pricing_matrix.js`（引擎，零 I/O）+ `static/sim/black_scholes.js`（BS 与 Greeks 原语）
- **DOM 层**：`static/option_pricing_matrix.js`，受 `panelState` 四态机（`idle → loading → loaded → empty|error`）约束
- **模板层**：`templates/partials/tab_option_pricing_matrix.html`，由 `templates/index.html` 在 Tab 切换时懒加载
- **后端旁支**：`/api/expiry_calendar` 提供到期日列（仅 docstring 提及本模块，接口不变）

无新增模块、无新增依赖、无跨层调用变更，因此 `doc_guard` 的 `import-direction` 不变量不受影响。

## 目录结构

本次改动共涉及 22 个源文件（不含 `site/` 生成产物）。整体为「6 个文件改名 + 16 个文件内容更新 + 重建 site/」。

```
OptionLab/
├── static/
│   ├── sim/
│   │   ├── option_pricing_matrix.js        # [RENAME+MODIFY] 由 premium_matrix.js 改名。纯计算引擎（零 I/O、Pages 安全）。
│   │   │                                  #   导出 buildPremiumMatrix → buildOptionPricingMatrix；
│   │   │                                  #   挂载 window.PremiumMatrix → window.OptionPricingMatrix。
│   │   │                                  #   保留每列 √T/e^(−rT) 缓存、每行 ln(S/K) 缓存、平价关系求 put、
│   │   │                                  #   按输入签名 memo 等性能实现；更新文件头注释。
│   │   └── black_scholes.js               # [MODIFY] 仅更新注释中对 premium matrix 的引用。
│   ├── option_pricing_matrix.js           # [RENAME+MODIFY] 由 premium_matrix.js 改名。DOM 渲染层。
│   │                                      #   更新：PANEL = 'option_pricing_matrix'、window.OptionPricingMatrix 消费点、
│   │                                      #   window.loadOptionPricingMatrix 导出、全部 el('opm-xxx') DOM id、
│   │                                      #   [data-opm-side] / [data-opm-toggle] 选择器、CSS 类名拼装、文件头注释。
│   │                                      #   不改：渲染契约（单次 HTML 字符串赋值、开关走 data-show-* 不重算、
│   │                                      #   --opm-sigma-left 宽度同步、列高亮与 σ 参考列交互）。
│   └── styles.css                         # [MODIFY] 约 250+ 处：.pm-* → .opm-* 类、--pm-* → --opm-* 自定义属性，
│                                          #   含注释中的 pm-matrix / pm-cell / pm-half 等描述。属性值一律不动。
├── templates/
│   ├── index.html                         # [MODIFY] sim/option_pricing_matrix.js 与 option_pricing_matrix.js 的 script src；
│   │                                      #   Tab 按钮 data-tab="tab-option-pricing-matrix" 与标签文字；
│   │                                      #   {% include 'partials/tab_option_pricing_matrix.html' %}；
│   │                                      #   内联懒加载逻辑（tab id、isLoaded 键、loadOptionPricingMatrix 调用）。
│   └── partials/
│       └── tab_option_pricing_matrix.html  # [RENAME+MODIFY] 由 tab_premium_matrix.html 改名。
│                                           #   id="tab-option-pricing-matrix"、panelState('option_pricing_matrix')、
│                                           #   opm-heading、<h2>Option Pricing Matrix</h2>、面板描述文案、
│                                           #   data-action="opm-run"、data-opm-toggle / data-opm-side、
│                                           #   aria-label 文案、加载/错误/空态提示（含中文空态）、
│                                           #   其余全部 pm-* id 与类 → opm-*。
├── core/options/simulation/
│   └── expiry.py                          # [MODIFY] 仅注释/docstring：L310「Expiration-calendar generation
│                                          #   (Premium Matrix columns)」、L447「Build upcoming option expirations
│                                          #   for a Premium Matrix.」。保留 Domain/Context/Contracts 标签块。
├── services/options/
│   └── simulation.py                      # [MODIFY] 仅 docstring：L267「build the expiry calendar for the
│                                          #   Premium Matrix」→ Option Pricing Matrix。
├── routes/
│   └── options.py                         # [MODIFY] 仅 docstring：L236 /api/expiry_calendar 用途描述。
├── scripts/
│   └── build_pages_site.py                # [MODIFY] L49 REDIRECTS：「option-pricing-matrix/index.html」:
│                                          #   ("tab-option-pricing-matrix", "Option Pricing Matrix")；
│                                          #   L350 tab id 断言列表中的 "tab-premium-matrix"。
├── tests/
│   ├── unit/
│   │   ├── option_pricing_matrix.test.js   # [RENAME+MODIFY] 由 premium_matrix.test.js 改名。更新 import 路径、
│   │   │                                   #   window.OptionPricingMatrix、window.loadOptionPricingMatrix 断言。
│   │   └── sim/
│   │       ├── option_pricing_matrix.test.js # [RENAME+MODIFY] 由 sim/premium_matrix.test.js 改名。更新 import 路径
│   │       │                                 #   与 buildOptionPricingMatrix 调用。
│   │       └── sim.guard.test.js             # [MODIFY] 更新对 sim/premium_matrix.js 的引用。
│   ├── e2e/
│   │   ├── test_option_pricing_matrix.py     # [RENAME+MODIFY] 由 test_premium_matrix.py 改名。更新 Tab 选择器与断言。
│   │   └── test_smoke.py                     # [MODIFY] L22 tab id 列表 "tab-premium-matrix" → "tab-option-pricing-matrix"。
│   ├── test_pages_build.py                   # [MODIFY] L24 tab id 列表。
│   └── test_expiry_calendar_api.py           # [MODIFY] L1 模块 docstring。
├── README.md                               # [MODIFY] L18「a client-side premium matrix」、
│                                            #   L20「(Simulation, Premium Matrix)」、L229 文件清单中的 premium_matrix.js、
│                                            #   L284-288 Pages 段落（标题与正文）。
├── docs/
│   └── glossary.md                          # [MODIFY] L96 小节标题「Premium Matrix Tab (Premium-Rate Grid)」→
│                                            #   「Option Pricing Matrix Tab」；L97-102 正文中的模块名与文件路径。
│                                            #   保留「premium rate」指标名与三条轴对齐契约的原文。
├── .codebuddy/plans/
│   └── premium-matrix-mvp_c3cf394f.md       # [KEEP] 历史 plan 归档，保留原名以维持决策记录可追溯。
└── site/                                    # [REGENERATE] 由 scripts/build_pages_site.py 重新生成，禁止手写：
    ├── index.html                           #   重新生成（Tab 标签、面板 DOM、script src 全部同步）。
    ├── static/{styles.css, option_pricing_matrix.js, sim/option_pricing_matrix.js}
    │                                        #   重新生成；旧 premium_matrix.js 需由脚本清理。
    └── option-pricing-matrix/index.html     #   由 premium-matrix/ git mv 后重新生成（slug 重定向页）。
```

## 关键代码结构

改动前后需严格对应的三个接口契约（重命名后不得走样）：

```javascript
// static/sim/option_pricing_matrix.js —— 纯计算引擎导出与全局挂载
export function buildOptionPricingMatrix(opts) { /* 签名与返回结构不变 */ }
window.OptionPricingMatrix = { buildOptionPricingMatrix, /* 其余成员不变 */ };

// static/option_pricing_matrix.js —— 面板入口（供 templates/index.html 懒加载调用）
window.loadOptionPricingMatrix = function loadOptionPricingMatrix() { /* ... */ };
```

```html
<!-- templates/partials/tab_option_pricing_matrix.html —— 面板根节点 -->
<div class="tab-content" id="tab-option-pricing-matrix" x-data="panelState('option_pricing_matrix')"
     role="region" aria-labelledby="opm-heading">
```

```css
/* static/styles.css —— 需保持成对出现，避免只改类名漏改变量（反之亦然） */
.opm-matrix { --opm-half-min: 4.6rem; --opm-strike-w: 4.4rem; --opm-sigma-left: 4.4rem; }
```

## 验证清单

```
ruff check . && ruff format --check .     # 后端 lint/格式
pytest --ignore=tests/e2e                 # 后端单测
npx vitest run                            # 前端单测
python scripts/build_pages_site.py        # 重建 Pages 站点
python scripts/doc_guard.py               # 文档标签与分层不变量
python scripts/arch_metrics.py --check    # 架构漂移门禁
python scripts/audit_tags.py              # 标签覆盖回归
```

补充人工验证：启动 `python app.py`，切到该 Tab，确认标题为 `Option Pricing Matrix`、矩阵正常渲染、Price / Prem. rate / Call / Put 四个开关与 Buy/Sell 侧开关功能正常、无控制台报错。E2E（`pytest tests/e2e/`）需先 `pip install pytest-playwright && playwright install chromium`，若环境未安装则跳过并说明。

## Agent 扩展

### Skill

- **lsp-code-analysis**
- 用途：在批量替换前后，对 `buildPremiumMatrix`、`window.PremiumMatrix`、`loadPremiumMatrix`、`buildOptionPricingMatrix` 等符号做语义级引用分析（definitions / references / call hierarchy）。`window.PremiumMatrix` 是动态挂载的全局对象，纯文本 grep 可能漏掉动态拼接或跨模块引用，语义导航可确保零遗漏。
- 预期结果：得到一份完整的符号引用清单，确认重命名后不存在仍指向旧名的悬挂引用，且无旧名残留。

- **optionlab-arch-review**
- 用途：本次改动触及 `core/`、`services/`、`routes/` 三层的 docstring，且项目以 `doc_guard.py` 的 `import-direction` 为硬性不变量。在改动收尾时跑一次架构守护评审，确认重命名未引入跨层违规、循环依赖或死代码候选。
- 预期结果：8 维度评分无退化、跨层违规为 0、`arch_metrics.py --check` 通过，确认命名重构对分层边界零影响。