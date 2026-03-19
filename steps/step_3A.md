# Step 3-A：三层验证

## 目标
系统性验证改造结果：单元验证 → 集成验证 → 回归验证。

## 加载资源
- `docs/field_mapping.md`
- `docs/nav/system_nav.md`（含改造接入点）

## 验证清单

### 层1：单元验证
- [ ] Ticker 转换：5个案例（`AAPL`/`US`, `0700`/`HK`, `SPY`/`US`, 无效输入×2）
- [ ] 字段映射完整性：`futu_provider.py` 输出字段 ⊇ `OptionsChainAnalyzer` 期望字段
  - 对照 `field_mapping.md` 和 `system_nav.md` 中的「option_chain() 返回字段」
- [ ] 连接管理：连续调用 P0 函数10次，进程结束后无僵尸连接

### 层2：集成验证
- [ ] `GET /api/option_chain?ticker=US.AAPL&source=futu`
  - 返回 HTTP 200
  - 包含 `expirations`（非空列表）
  - 包含 `chain`（至少一个到期日）
  - `chain.{date}.calls` 包含 `strike`, `bid`, `ask`, `iv` 字段
  - `spot` 为正数 float
  - 响应时间 < 10秒
- [ ] `GET /api/option_chain?ticker=HK.00700&source=futu`（港股路径）

### 层3：回归验证
- [ ] `GET /api/option_chain?ticker=AAPL&source=yfinance`
  - 返回结构与改造前完全一致（字段名、层级、类型）
- [ ] `GET /api/option_chain?ticker=AAPL`（无 source 参数，默认 yfinance）
  - 行为与改造前完全一致

## 失败处理
- 任何验证失败 → 记录失败描述 + 定位到具体文件/函数 → 修复后重跑该层验证
- 不跳过验证项，这是方案最后一步，确保质量达标
## 完成标准
- [ ] 三层验证全部通过，无跳过项

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → 方案完成
- 已完成 → 追加 Step 3-A
