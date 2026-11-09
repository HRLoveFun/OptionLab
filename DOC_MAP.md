# 文档地图

> L0 | 权威：仓库里有哪些文档、各讲什么、何时读、何时改 | 不权威：文档内容本身（以各文档与代码为准）

先看词表，再按标签查，查完还要全文搜索。标签能找到还没写到某个词的文档，搜索能找到标签没覆盖的文档：

```bash
grep '【arch' DOC_MAP.md                        # 主题换成下面的父级
grep '【arch' DOC_MAP.md | grep '【cross-module】'   # 再叠一个时机标签
```

> 本仓 `docs/l0_architecture.md` 里的 "L0" 指**顶层目录层级**（`app.py`、`routes/`、`core/` …），
> 与本文件的 L0–L3 **文档层级**无关，两者不要互相套用。

<!-- doctags:begin -->

### 主题标签（关于）

- 【arch】Architecture: layers, module boundaries, dependency direction：【arch-layers】【arch-streaming】【arch-guards】
- 【data】Data acquisition, storage, transform and the provider seam：【data-pipeline】【data-provider】
- 【ui】Templates, static JS and the UI contract：【ui-contract】【ui-state】
- 【options】Options chain, Greeks, strategies and optsim：【options-sim】【options-terms】
- 【collab】Progress, handover, plans and this doc system itself：【collab-progress】【collab-plans】【collab-docmap】
- 【process】Conventions, gates, automation and the worktree flow：【process-conventions】【process-gates】【process-worktree】

### 时机标签（何时读）

- 【onboarding】第一次了解这个仓库
- 【start-task】开始一个新开发任务
- 【run】把项目跑起来
- 【add-feature】新增或扩展功能
- 【cross-module】改动跨层或改变模块边界
- 【challenge-design】想改掉、质疑某项既定设计，或想把它当技术债清理
- 【resume-batch】继续一个未完成的计划
- 【troubleshoot】排查运行或门禁故障
- 【write-tests】新增或修改测试
- 【term-lookup】遇到不确定的术语或领域常数

### 修改事件（何时改）

- 【batch-close】一批任务结束（更新 STATUS 那一行的状态、证据、日期）
- 【module-change】新增、删除模块或依赖方向变化
- 【decide】做了取舍、否掉方案或接受新 ADR
- 【usage-change】对外用法变化
- 【convention-change】约定变化
- 【doc-structure】文档结构变化（先改本文件，再动文件）
- 【doc-superseded】文档被新文档取代

<!-- doctags:end -->

<!-- docmap:begin -->

## 根目录

- `AGENTS.md` L0 — 关于【collab-docmap】和【process-conventions】；在【onboarding】和【start-task】时读；在【doc-structure】时改
- `DOC_MAP.md` L0 — 关于【collab-docmap】；在【onboarding】和【start-task】时读；在【doc-structure】时改
- `STATUS.md` L1 — 关于【collab-progress】；在【start-task】和【resume-batch】时读；在【batch-close】时改
- `README.md` L1 — 关于【arch-layers】和【collab-docmap】；在【onboarding】和【run】时读；在【usage-change】时改
- `.github/copilot-instructions.md` L0 — 关于【collab-docmap】和【process-conventions】；在【onboarding】时读；在【doc-structure】时改

## docs/

- `docs/architecture.md` L1 — 关于【arch-layers】【arch-streaming】和【data-pipeline】；在【cross-module】和【onboarding】时读；在【module-change】时改
- `docs/module_reference.md` L2 — 关于【arch-layers】和【data-pipeline】；在【cross-module】和【add-feature】时读；在【module-change】时改
- `docs/CONVENTIONS.md` L1 — 关于【process-conventions】；在【start-task】和【write-tests】时读；在【convention-change】时改
- `docs/constraints.md` L1 — 关于【arch-guards】【data-provider】和【options-terms】；在【challenge-design】和【start-task】时读；在【decide】时改
- `docs/glossary.md` L1 — 关于【options-terms】；在【term-lookup】时读；在【convention-change】时改
- `docs/architecture_review.md` L2 — 关于【arch-guards】和【arch-layers】；在【challenge-design】时读；在【batch-close】时改
- `docs/l0_architecture.md` L2 — 关于【arch-layers】和【arch-guards】；在【troubleshoot】和【challenge-design】时读；在【module-change】时改
- `docs/frontend_architecture.md` L2 — 关于【ui-contract】和【ui-state】；在【cross-module】和【add-feature】时读；在【module-change】时改
- `docs/automation.md` L2 — 关于【process-gates】；在【troubleshoot】时读；在【convention-change】时改
- `docs/options_learning_charter_v1_2.md` L3 — 关于【options-terms】；在【challenge-design】时读；在【doc-superseded】时改

## docs/guides/

- `docs/guides/USER_GUIDE.md` L2 — 关于【ui-contract】和【options-terms】；在【onboarding】和【term-lookup】时读；在【usage-change】时改
- `docs/guides/GIT_WORKTREE_WORKFLOW.md` L2 — 关于【process-worktree】；在【start-task】时读；在【convention-change】时改

## docs/plans/

- `docs/plans/business_line_reorg.md` L3 — 关于【data-pipeline】【data-provider】和【arch-layers】；在【resume-batch】和【challenge-design】时读；在【batch-close】时改
- `docs/plans/futu_provider_integration.md` L3 — 关于【data-provider】；在【resume-batch】时读；在【doc-superseded】时改
- `docs/plans/optsim.md` L3 — 关于【options-sim】和【ui-contract】；在【resume-batch】时读；在【batch-close】时改
- `docs/plans/optsim_design.md` L3 — 关于【options-sim】；在【resume-batch】时读；在【doc-superseded】时改
- `docs/plans/simulation_tab.md` L3 — 关于【options-sim】和【ui-contract】；在【resume-batch】时读；在【doc-superseded】时改
- `docs/plans/frontend_convergence.md` L3 — 关于【ui-contract】和【ui-state】；在【challenge-design】时读；在【batch-close】时改

## docs/decisions/

- `docs/decisions/` L3 — 关于【arch-layers】【data-provider】【options-sim】和【ui-contract】；在【challenge-design】和【start-task】时读；在【decide】时改

## static/

- `static/state/README.md` L2 — 关于【ui-state】；在【cross-module】时读；在【convention-change】时改
- `static/components/README.md` L2 — 关于【ui-state】；在【add-feature】时读；在【module-change】时改
- `static/features/README.md` L2 — 关于【ui-state】；在【add-feature】时读；在【module-change】时改

## tests/

- `tests/e2e/README.md` L2 — 关于【process-gates】；在【write-tests】和【troubleshoot】时读；在【convention-change】时改

## archive/

- `archive/` L3 — 关于【collab-plans】；在【troubleshoot】时读；在【doc-superseded】时改

<!-- docmap:end -->

<!-- docmap:exclude:begin -->
# 一行一个 glob，相对仓库根；放模板、第三方文档、没人读的生成物。隐藏目录已跳过，不用写
CLAUDE.md
CODEBUDDY.md
site/**
<!-- docmap:exclude:end -->
