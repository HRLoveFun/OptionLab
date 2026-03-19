# Step 0-A：futu-api 文档导航

## 目标
构建 futu-api 官方文档的期权相关章节导航，供后续步骤按需定位，无需全量加载文档。

## 加载资源
- Futu-API-Doc-en-Python.md

## 执行过程
1. 访问 Futu-API-Doc-en-Python.md，浏览目录结构
2. 识别期权相关章节，重点定位：
   - 期权到期日查询
   - 期权链查询
   - 行情快照/现货价格
   - 连接管理（OpenQuoteContext 等）
   - Ticker 格式说明
3. 对每个章节判断是否包含可运行示例代码（标记 `[has_example]`）

## 产出物
**文件**：`docs/nav/futu_api_doc_nav.md`

**格式模板**：
```markdown
# futu-api 文档导航

## 连接管理
- 章节：XXX | URL：... | [has_example] | 说明：OpenQuoteContext 生命周期管理

## Ticker 格式
- 章节：XXX | URL：... | [has_example] | 说明：美股 US.AAPL，港股 HK.00700

## 期权：到期日查询
- 章节：XXX | URL：... | [has_example] | 说明：get_option_expiration_date()

## 期权：期权链查询
- 章节：XXX | URL：... | [has_example] | 说明：get_option_chain()

## 期权：行情快照
- 章节：XXX | URL：... | [has_example] | 说明：get_market_snapshot()
```

## 完成标准
- [ ] 包含期权到期日、期权链、行情快照三个核心章节
- [ ] 包含连接管理章节
- [ ] 包含 Ticker 格式章节
- [ ] 每个章节有 `[has_example]` 或 `[no_example]` 标记
- [ ] 每个章节有 URL 可供后续步骤直接访问

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 0-B
- 已完成 → 追加 Step 0-A
- `docs/nav/futu_api_doc_nav.md` → ✅ 已创建
