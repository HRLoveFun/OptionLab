---
name: optionlab-arch-review
description: |
  OptionLab 架构评审与守护 skill。当用户要求"评估项目架构 / 检查分层违规 /
  架构回归 / 架构评审 / architecture review / layering check"或修改涉及
  分层边界（core/services/routes/data_pipeline/utils）的代码时使用。
  输出 8 维度评分、跨层违规、循环依赖、上帝文件与死代码候选。
version: 1.0.0
---

# OptionLab Architecture Review

对本仓库执行可复现的架构评审。所有工具零第三方依赖，可在 CI 运行。

## 评分体系（8 维度，10 分制，加权）

| # | 维度 | 权重 | 度量方式 |
|---|---|---|---|
| D1 | 分层清晰度 | 20% | `scripts/doc_guard.py` 违规数（import-direction / core-purity / db-access / single-yf-exit） |
| D2 | 模块耦合度 | 15% | `scripts/arch_metrics.py`：fan-out Top5、环数（Tarjan SCC） |
| D3 | 内聚/SRP | 15% | >400 行文件数（arch_metrics `god_files`）；单文件职责数人工抽查 |
| D4 | 目录结构 | 10% | 游离模块、死代码候选（arch_metrics `dead_code_candidates`） |
| D5 | 命名规范 | 10% | 同名模块数（`models.py` 等）；`_` 前缀私有模块可读性 |
| D6 | 可扩展性 | 10% | 新增功能需改动文件数；注册表机制（`_RENDER_KIND_SLICES`） |
| D7 | 架构可治理性 | 10% | doc_guard 规则覆盖层数、盲区数、是否有度量/基线 |
| D8 | 文档一致性 | 10% | CODEBUDDY.md / constraints.md 声明 vs 实测 import 图偏差数 |

评级：≥8.5 优秀；7.0–8.4 良好；5.5–6.9 合格但脆弱；<5.5 需重构。

**分层允许集**（唯一权威：`scripts/doc_guard.py::_ALLOWED_DEPS`）：

```
app           → routes, services, core, data_pipeline, utils
routes        → services, data_pipeline, utils        # 不得直调 core
services      → core, data_pipeline, utils
core          → utils                                 # data_pipeline 仅限 §2 白名单
data_pipeline → utils
utils         → （叶子层，禁止任何向上依赖）
```

## 执行流程

1. **守护规则**：`python scripts/doc_guard.py` — 必须为 clean；每个违规对应
   一条跨层证据（文件:行号）。
2. **度量报告**：`python scripts/arch_metrics.py` — 记录 modules / edges /
   cycles / god_files / dead_code_candidates / fan-in/out Top5。
3. **漂移门禁**：`python scripts/arch_metrics.py --check` — 与
   `.github/data/arch_baseline.json` 对比，任何指标恶化 → 评审结论为"回归"。
4. **纯度契约**：`python -m pytest tests/test_architecture_purity.py -q` —
   core/ 8 个子包的 I/O 纯度断言（尊重 `doc-guard: allow` 标记）。
5. **评分**：按上表逐维打分，加权汇总；D1/D2/D3/D4/D7 可完全由工具输出
   推导，D5/D6/D8 抽查给出证据。
6. **债务登记**：新增豁免必须同时 (a) 在代码行加
   `# doc-guard: allow=<rule>`，(b) 登记 `docs/architecture_review.md` §2，
   (c) 说明退出条件。豁免数量只允许减少；增加时须更新 baseline 并说明原因。

## 技术债清单

权威位置：`docs/architecture_review.md` §2。快速核对：
`grep -rn "doc-guard: allow" --include='*.py' core services data_pipeline`

## 输出格式

结论包含：8 维评分表（含证据行号）、与基线的 diff、新发现的问题（按
P0–P3 优先级）、以及是否需要在同一次提交中更新
`docs/architecture_review.md` / `docs/constraints.md` / `CODEBUDDY.md`。
