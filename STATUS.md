# 状态

> L1 | 权威：项目现状、批次进度、已知未完成与已知风险 | 不权威：模块结构、约定、决策理由

当前焦点：文档体系重构 — 入口、地图、进度三处归一，重复副本降为指针，未完成项见下表。

| 批次 | 目标 | 状态 | 证据 | 更新日期 |
| --- | --- | --- | --- | --- |
| 2026-09 架构整改 | 层反转、§2 债务清零、`doc_guard` 新规则 | 已完成 | `docs/architecture_review.md` §4/§5；`scripts/doc_guard.py` `ALL_RULES` | 2026-10-21 |
| L0 整改 P1-2 | 把 `static/sidebar.js` 纳入 git 并加引用守卫 | 已完成 | commit `7ef2a33`，守卫 `65c01f6`，`tests/test_pages_build.py` | 2026-09-08 |
| L0 整改 P1-1 | 不再跟踪生成的 Pages 镜像 | 已完成 | `docs/l0_architecture.md` §5；`.gitignore` 覆盖 42 个生成文件 | 2026-09-08 |
| 业务线重组 B1–B10（ADR 0011 / 0012） | provider seam、规范化 schema、readiness 预取、ticker-only 参数栏 | 已完成 | `data_pipeline/providers`、`store`、`ingest`、`transform`、`read`、`orchestrate`；`tests/test_architecture_purity.py`；ADR 0011/0012 Accepted | 2026-10-21 |
| optsim as-built（ADR 0013） | `core/optsim`、`POST /api/optsim`、Position Simulator tab | 已完成 | `tests/test_optsim.py`、`tests/test_optsim_api.py`、`docs/plans/optsim.md` §1 | 2026-10-23 |
| optsim v0.3 设计中未实现的部分 | 见 `docs/plans/optsim.md` 的路线图与已知限制 | 未开始 | `docs/plans/optsim.md` §1.7 与后续小节 | 2026-10-23 |
| 前端整合 P3 | 把 `static/` 根级脚本收进 `static/features/` | 未开始 | `static/features/` 目录内只有 README；`docs/architecture_review.md` §5 第 3 条 | 2026-11-09 |
| 全局无风险利率设置 | reorg 遗留项，等第二个 provider | 未开始 | `docs/plans/business_line_reorg.md` §10 | 2026-11-09 |
| ADR 0011 `ticker` → `symbol` 列改名 | reorg 遗留项，等第二个 provider | 未开始 | `docs/plans/business_line_reorg.md` §10 | 2026-11-09 |
| 文档体系重构 | `AGENTS.md` 瘦身、建 `DOC_MAP.md` 与 `STATUS.md`、副本降指针 | 进行中 | 本文件、`DOC_MAP.md`、`scripts/doc-check.sh` | 2026-11-09 |

> 状态只允许：`未开始` / `进行中` / `进行中（待验证）` / `已完成` / `受阻` / `已取消`。
> `已完成` 必须能指到证据（路径、可复跑命令、commit/PR 三者之一）；过程叙述进 `docs/plans/`，不进这张表。

## 已知风险与未验证

- **未裁决的冲突**：`docs/plans/optsim_design.md` 原有一句「已完成；其余未开始」，不区分 as-built 与设计目标；
  现改为指向本文件，具体口径以 `docs/plans/optsim.md` §1（as-built）为准。
- **未逐条核对**：`docs/frontend_architecture.md`（563 行）与 `docs/guides/USER_GUIDE.md`（678 行）只做了抽样核对，
  未逐条对照代码；标为「未验证」，不当作权威现状读。
- **旧文档中的过期表述按描述性冲突处理（代码优先）**：`.github/copilot-instructions.md` 原本写端口 `:5000`、
  常量在 `utils/utils.py`、Greeks 在 `core/options_greeks.py`，实际分别是 5001、`utils/constants.py`、
  `core/options/greeks/`；该文件已降为指针，这些句子随之删除，正文措辞未另做修订。
- **已删除的死文档**：`docs/guides/README.md`（旧版 README 副本，端口写 5000，0 引用）已删除，git 历史可追回。
- **能力边界**：`scripts/doc-check.sh` 只对账结构、路径、枚举值与标签是否在词表内；它不判断标签是否仍说真话，
  也不评价文档内容质量。
