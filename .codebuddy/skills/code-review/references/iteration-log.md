# 迭代记录（iteration-log）

本文件由 SKILL.md「第七步：自迭代与经验沉淀」维护，是 skill 的经验记忆：

- 每轮评审结束后**追加**一条记录，倒序排列（最新在最上）；
- 每次评审开始（第一步）时读取最近 3 条记录与两个"高频"段，校准本轮评审；
- 记录只增不删；已消化的模式从"高频"段移除前，须确认对应清单已更新。

## 记录模板

```markdown
### <YYYY-MM-DD> <项目/评审对象简述>
- **输入**：模式=<全库/变更集/定点>；范围=<...>；语言=<...>；框架=<...>；变更类型=<...>
- **覆盖度**（全库模式）：<深审模块 / 抽样比例 / 扫描文件数>
- **发现统计**：P0 <n> / P1 <n> / P2 <n> / P3 <n>；疑点 <n>
- **问题类型分布**：<维度 × 模式及次数，如 安全/SQL拼接 ×2；效率/N+1 ×1>
- **误报**：<问题 → 原因：规则过宽 / 上下文不足 / 工具误报>
- **遗漏**：<问题 → 原因：清单缺模式 / 顺序不当 / 被工具告警淹没>
- **分级偏差**：<问题 → 原定级 → 合理定级 → 偏差原因>
- **改进建议**：
  - [规则] <调整哪条规则、怎么调>
  - [模式] <新增什么问题模式、写入哪个文件>
  - [分级] <修订第四步哪条判定标准>
  - [模板] <report-template.md 缺什么信息>
- **已落地改动**：<经确认写入的文件与摘要；未确认的标注"待确认">
```

### 2026-09-07 OptionLab 架构专项评审（第 2 轮，聚焦架构维度）
- **输入**：模式=<全库（架构聚焦，optionlab-arch-review skill 编排）>；范围=<8 维评分体系>；语言=<Python + JavaScript（推断）>；框架=<Flask + HTMX + matplotlib + SQLite + yfinance（推断）>；变更类型=<全库健康度>
- **覆盖度**（全库模式）：工具面=doc_guard（clean）+ arch_metrics --check（ok）+ 纯度测试 9 通过 + ruff/format 全绿；深审=routes/options.py、core/options/simulation/expiry.py、services/options/preload.py、scripts/build_pages_site.py、.github/workflows/pages.yml；跨切面 grep 扫描缓存豁免/ET 时区/site 漂移；pip-audit 未执行（工具未装）
- **发现统计**：P0 0 / P1 1 / P2 3 / P3 3；疑点 1
- **问题类型分布**：架构/构建不变量被提交物违反 ×1（site fork 将被 rmtree+copytree 覆盖）；一致性/文档漂移 ×2（CODEBUDDY.md 缺 services/market_review、str(e) 回显残留）；安全/devDeps 漏洞 ×1；可维护性/Py-JS 业务逻辑双实现 ×1；健壮性/参数转换裸抛 ×1；效率/过期缓存不回收 ×1；逻辑/时区不一致 ×1
- **误报**：无（site/static/option_pricing_matrix.js 差异先疑为构建产物过期，经 build_pages_site.py rmtree+copytree 证据确认为真问题）
- **遗漏**：上轮未发现 site fork 覆盖风险 → 原因：清单缺"构建脚本 rmtree 目标目录 vs 提交物包含独有文件"交叉检查模式
- **分级偏差**：无
- **改进建议**：
  - [模式] architecture-checklist 增补："CI 构建会整体重建的目录中，提交物含构建产物之外的独有文件"为不变量违反信号（本次由 git log 定位到仅改 site/static 的修复提交确证）
  - [分级] 维持"devDeps 漏洞降一档为 P2"口径（第 3 次验证一致，建议固化）
- **已落地改动**：仅追加本记录；清单修改待用户确认

### 2026-09-08 OptionLab 整改期补充（第 1-4 批修复中的评审校准）
- **输入**：模式=<整改（四批）>；范围=<同 2026-09-07 全库回顾>；变更类型=<修复验证>
- **误报**：core/market 各文件头 "Dependencies DOWNWARD: services.market.charts" 被判为"系统性过时 docstring" → 实际仓库约定是 UPWARD=本文件依赖项 / DOWNWARD=消费方（与 utils/rate_limit.py 一致），大部分文件头是正确的；仅 data_context.py 存在混列。原因：**未先核对仓库自身约定就按通用分层直觉判 P3**
- **遗漏**：① e2e conftest 的 FAKE_REGIME_HISTORY 与真实服务契约形状不匹配 → smoke 测试时序竞态 flake（评审时只扫了测试文件的存在性，未核对 mock 形状与生产契约一致性）；② 已提交的 site/ 构建产物已经漂移（static/option_pricing_matrix.js），评审发现了"无门禁"风险但未抽查"当前是否已漂移"；③ config 选择器提供 QE 频率但管道从不生成，评审只判了"口径不一致"（P3），实际是用户可触发的功能性缺失
- **改进建议**：
  - [规则] security/maintainability-checklist 增补：评审 docstring 类"契约漂移"前，先在仓库内找同一约定的 ≥2 个正确样例校准语义，避免按直觉误判
  - [模式] "mock 形状与生产契约一致性"检查写入 architecture-checklist：e2e fixture 应镜像真实路由返回形状（含 status 键），否则产生时序竞态 flake
  - [分级] "用户可选选项在管道中缺失"应从 P3 上调至 P2（功能性缺失而非文档漂移）
- **已落地改动**：仅追加本记录

### 2026-09-07 OptionLab 全库回顾
- **输入**：模式=<全库>；范围=<app.py, routes, services, core, data_pipeline, utils, scripts, static, templates, tests, site>；语言=<Python + JavaScript（推断）>；框架=<Flask + HTMX/Alpine + matplotlib + SQLite + yfinance；vitest/Playwright（推断）>；变更类型=<全库健康度>
- **覆盖度**（全库模式）：深审=data_pipeline、services（32 文件全读）、期权模拟热路径（expiry.py/black_scholes/simulation/routes/options）、core/market（抽样）；跨切面 grep 扫描 100% 文件（static/templates/routes/utils/app.py 由跨切面代理覆盖）；scripts 仅 grep 扫描未深审；archive 未评审
- **发现统计**：P0 0 / P1 7 / P2 16 / P3 12；疑点 6
- **问题类型分布**：安全/限流键伪造 ×1；安全/入口参数直通 I/O 层 ×1；安全/条件性调试器暴露 ×1；架构/core 层运行时 I/O 依赖（有白名单妥协）×1；逻辑/失败状态被缓存 ×2（_range memo、job cache error memoisation）；逻辑/函数属性隐藏状态 ×1；逻辑/测试日期依赖 flaky ×1；一致性/前端契约改动未同步 e2e ×1；系统性/无界缓存 ×5 处；系统性/错误处理双轨制（str(e) 回显 + error-dict 键碎片化）；系统性/吞错静默降级 ×4 处
- **误报**：core/market data_context import data_pipeline 初判 P0 → 实有 `doc-guard: allow=core-purity` 白名单标记且 doc_guard 通过，属文档化妥协，降 P1
- **遗漏**：无（本轮无后续暴露）
- **分级偏差**：npm audit 2 critical（vitest/vite）→ 定 P2 而非 P1，沿用上一轮口径：devDependencies、需 --ui 模式才可利用、无运行时调用点；app.py debug=True 初判 P0 → 生产入口是 gunicorn（deploy/Dockerfile、Render start command），app.py 仅为 dev 入口，降 P1
- **改进建议**：
  - [规则] performance-checklist 增补："缓存写入前区分成功/失败结果"模式（失败、error-dict、None 不应进入正向 TTL memo）
  - [模式] "无界模块级 dict 缓存"模式（_query_cache/_rate_buckets/_option_chain_cache/_mr_cache/_all_conns 同构），写入 architecture-checklist 或 performance-checklist
  - [模式] "前端可见性契约改动必须同步对应 e2e 断言"（visibility:hidden → opacity 淡出使 to_be_hidden 失效）
  - [分级] devDependency 中的漏洞默认降一档（与上轮一致，已验证两次，考虑固化）
- **已落地改动**：仅追加本记录；清单修改待用户确认

### 2026-09-07 EMSXView 全库回顾
- **输入**：模式=<全库>；范围=<backend/api, frontend/src, CostView, platform_data, data_access, scripts, MarketView>；语言=<TypeScript + Python（推断）>；框架=<React 19 + Vite + shadcn/ui；FastAPI + Pydantic v2（推断）>；变更类型=<全库健康度>
- **覆盖度**（全库模式）：深审=backend/api（部分精读）、frontend costview、platform_data/data_access、CostView monitoring；抽样=execution store、MarketView router、scripts；跨切面 grep 扫描 100% 文件
- **发现统计**：P0 0 / P1 1 / P2 5 / P3 6；疑点 2
- **问题类型分布**：安全/硬编码凭证 ×1；安全/SQL拼接（防御深度）×1；安全/未鉴权内网调用 ×1；一致性/迁移残留死配置 ×1（跨 6 处）；可维护性/门禁口径漂移 ×1；可维护性/依赖停维 ×1；效率/SELECT * ×1；一致性/注释文档漂移 ×3
- **误报**：边界门禁报 broker.py 43 端点"未返回 ApiResponse" → 实为缺 `-> ApiResponse` 注解（端点均通过 response_model 返回 ApiResponse），门禁口径过窄
- **遗漏**：无（本轮无后续暴露）
- **分级偏差**：npm audit 1 critical（vitest UI RCE）→ 定 P2 而非 P1，理由：devDependencies、需 --ui 模式才可利用、无运行时调用点；regime_dim SQL 拼接 → 调用方有白名单，P0 降为 P2
- **改进建议**：
  - [规则] security-checklist 增补：门禁/审计工具自身口径需与代码实际风格对齐（检查注解型 vs 运行时型断言），避免大面积误报
  - [模式] "大迁移残留清零"模式：特性迁移收尾时 grep 旧标识符（模块名/路由前缀/构建脚本）应零命中，写入 architecture-checklist
  - [分级] devDependency 中的漏洞默认降一档（P1→P2），除非存在本地开发实际调用点
- **已落地改动**：本次仅追加本记录；清单修改待用户确认

### 2026-09-07 EMSXView 全库体检模块设计方案评审
- **输入**：范围=对话内设计稿（无 diff）；语言=Python（FastAPI + Pydantic v2 + 多 SQLite + 可选 PG，推断）；框架=FastAPI；变更类型=设计评审（新功能前置）
- **发现统计**：P0 0 / P1 2 / P2 4 / P3 2；疑点 2
- **问题类型分布**：架构/数据所有权 ×1（结果库写入 EMSXVIEW_DATA_DIR）；架构/重复建设 ×1（未整合既有 quality_gate、monitoring、DatabaseView 诊断）；架构/scope 模型与存储模型错配 ×1；设计不足/执行生命周期未定义 ×1；安全/报告敏感泄露面 ×1；需求缺口/周期触发 ×1；可维护性/弱类型 metrics ×1；可维护性/留存策略 ×1
- **误报**：无
- **遗漏**：初轮设计产出时未检索仓库既有同域资产（quality_gate、monitoring、DatabaseView），导致方案含重复建设——设计类评审应在第一步增加"既有资产盘点"动作
- **分级偏差**：无
- **改进建议**：
  - [规则] architecture-checklist.md §1.1 增补：设计/方案评审必须先盘点仓库内同域既有实现，评估复用/桥接后再规划新建
  - [模式] 设计评审常见模式：写路径落入他人所有的数据根（所有权错位）→ 记入 architecture-checklist.md §1.5 数据所有权条目的示例
- **已落地改动**：本次仅追加本记录；清单修改待用户确认

### 2026-09-08 OptionLab 架构专项评审（第 3 轮，全库 + 架构聚焦）
- **输入**：模式=<全库（架构聚焦，code-review + optionlab-arch-review 编排）>；范围=<8 维评分 + 前两轮整改复核>；语言=<Python + JavaScript（推断）>；框架=<Flask + HTMX + matplotlib + SQLite + yfinance（推断）>；变更类型=<全库健康度>
- **覆盖度**（全库模式）：工具面=doc_guard（clean）+ arch_metrics --check（REGRESSION: dead_code 0→1）+ 纯度测试 9 通过 + ruff/format 全绿 + pytest 非 network 全过（仅 2 个 network 用例环境性失败）+ vitest 150/150；深审=data_pipeline/data_ops（_query/_range/_globals）、data_pipeline/db.py、services/market/dispatch.py、services/options/preload.py、services/market_review/fetch.py；抽样=static/{position,main,regime}.js innerHTML 插值点、ci.yml、build_pages_site.py
- **发现统计**：P0 0 / P1 1 / P2 4 / P3 3；疑点 2
- **问题类型分布**：一致性/构建产物漂移复发 ×1（c6f7927 只改 static 未同步 site，HEAD 上 CI diff 门禁必红）；可维护性/死代码 + 文档漂移 ×1（summary.py，即基线回归项）；可维护性/近重复函数 + 空结果 memo 残余 ×1（get_processed(_data)）；安全/缓存键无上限残余 ×1（_option_chain_cache）；安全/devDeps 漏洞 ×1（npm 11 项）；可维护性/str(e) 回显残留 ×1；安全/f-string SQL 防御深度 ×1；可维护性/私有符号跨包导入 ×1
- **误报**：`_option_chain_cache` 初判为"无界缓存复发" → 实有 TTL 过期即删（get 时 pop），仅键集合无上限，降为键枚举残余问题；QE 频率缺口（第 2 轮遗漏③）经 grep 证实管道已全面支持 → 非问题
- **遗漏**：无（本轮无后续暴露）
- **分级偏差**：site 漂移第 2 轮定 P1（无门禁）→ 本轮仍 P1 但理由变为"HEAD 上已存在门禁必红"，修复成本更低；环境踩坑：.venv 不存在 + requirements pin numpy==1.26.2 无 3.13 wheel → 记为 P3 打包问题而非测试失败
- **改进建议**：
  - [模式] architecture-checklist 增补："pin 精确版本的上游库需核对其 wheel 覆盖的 Python 版本区间与 requires-python 声明的一致性"（本次由环境安装失败确证）
  - [规则] 维持 devDeps 漏洞 P2 口径（第 4 次验证一致）
  - [分级] "有 CI 门禁但 HEAD 已违反的不变量"与"无门禁"同级定 P1，理由字段区分
- **已落地改动**：仅追加本记录

### 2026-09-08 OptionLab 整改收尾（第 3-4 批：P2 剩余 + P3 全清）
- **输入**：模式=<整改（vitest 3 升级 + str(e) 服务层 + upsert_many 白名单 + _dte 去重）>；范围=<同第 3 轮全库回顾>；变更类型=<修复验证>
- **发现统计**：修复 4 项；修复过程新增发现 2 处（已当场修复）
- **问题类型分布**：可维护性/`_dte` 四处逐字重复定义（比原判"私有符号跨包导入"更重，升级为重复实现）；可维护性/测试固化旧行为（test_render_streaming 断言 "synthetic failure" 泄露到响应）
- **误报**：无
- **遗漏**：rename 时引入函数内变量遮蔽（`dte = max(dte(...))` F823）→ ruff 当场抓出，未流入提交；`core/options/chain/__init__.py` 对 `_dte` 的再导出在首轮 grep（限 glob *.py 匹配 `import.*_dte`）中漏检，收集测试才暴露
- **分级偏差**：无
- **改进建议**：
  - [模式] security-checklist 增补："异常回显清理时同步 grep 断言该回显文本的测试用例，反转断言而非删除"；rename/收拢符号时必须全库 grep `__init__.py` 的再导出与 `__all__`
  - [规则] 维持"重命名引入遮蔽由 ruff F823 兜底"口径——lint 必须在 rename 类变更后全量跑而非抽查
- **已落地改动**：仅追加本记录

## 高频误报（滚动维护）

> 累计出现 >=2 次的误报模式与规则收窄方向；已在清单中修复的移除。

<暂无记录>

## 高频遗漏（滚动维护）

> 累计出现 >=2 次的遗漏模式与补充方向；已在清单中修复的移除。

<暂无记录>

## 模板与分级变更史

> report-template.md 或第四步判定标准每次变更在此留痕（日期 + 变更摘要），便于回溯口径漂移。

<暂无记录>
