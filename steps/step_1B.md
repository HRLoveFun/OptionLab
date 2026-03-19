# Step 1-B：API 调用语法

## 目标
阅读三个核心 API 的文档章节，记录调用语法和文档声称的字段名，追加到 `docs/api_syntax_notes.md`。

**重要约束**：本步骤只记录文档内容，不保证字段名与实际运行输出一致。
所有字段列表必须标注「待实机确认（Step 1-C）」，这是有意为之的设计，不是遗漏。

## 加载资源
- `docs/nav/futu_api_doc_nav.md` → 定位三个 API 章节的 URL
- `docs/api_syntax_notes.md`（已存在，追加内容）
- 逐一访问三个章节 URL

## 执行过程
按顺序处理三个 API：
1. 期权到期日：`get_option_expiration_date()` 或等效函数
2. 期权链：`get_option_chain()` 或等效函数
3. 行情快照：`get_market_snapshot()` 或等效函数

每个 API 记录：
- 完整函数签名（含参数名、类型、默认值）
- 连接上下文类型（哪类 Context）
- 文档声称的返回字段名（DataFrame 列名 或 dict key）
- 连接管理模式（`with` 语句 或 手动 `open/close`）

## 产出物
**追加到**：`docs/api_syntax_notes.md`

**写入内容**：
```markdown
## 2. 连接管理模式
（来源：文档章节 XXX）
- 上下文类：OpenQuoteContext / OpenHKTradeContext / ...
- 推荐模式：with 语句（自动关闭）
  with futu.OpenQuoteContext(host=..., port=...) as ctx:
      ...
- 手动模式：ctx.open() / ctx.close()

## 3. get_option_expiration_date()
（来源：文档章节 XXX，URL：...）
- 签名：ret, data = ctx.get_option_expiration_date(code="US.AAPL")
- 参数：code (str, futu格式 Ticker)
- 返回：(RET_CODE, DataFrame)
- 文档声称字段：【待实机确认 Step 1-C】time (str), ...
- 注意事项：...

## 4. get_option_chain()
（来源：文档章节 XXX，URL：...）
- 签名：ret, data = ctx.get_option_chain(code=..., start=..., end=..., ...)
- 参数：...
- 返回：(RET_CODE, DataFrame)
- 文档声称字段：【待实机确认 Step 1-C】strike_price, call_bid_price, ...
- 注意事项：...

## 5. get_market_snapshot()
（来源：文档章节 XXX，URL：...）
- 签名：ret, data = ctx.get_market_snapshot(code_list=[...])
- 参数：...
- 返回：(RET_CODE, DataFrame)
- 文档声称字段：【待实机确认 Step 1-C】last_price, ...
- 注意事项：...
```

## 完成标准
- [ ] 三个 API 全部覆盖
- [ ] 每个 API 的函数签名完整
- [ ] 所有字段列表旁有「待实机确认 Step 1-C」标注
- [ ] 连接管理模式记录清楚

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 1-C
- 已完成 → 追加 Step 1-B
- `docs/api_syntax_notes.md` → ✅ 已完成（Step 1-B 追加完毕）
