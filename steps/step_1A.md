# Step 1-A：Ticker 命名规则

## 目标
整理 futu-api Ticker 格式规则，输出转换伪代码，初始化 `docs/api_syntax_notes.md`。

## 加载资源
- `docs/nav/futu_api_doc_nav.md` → 定位 Ticker 格式章节 URL
- 访问该章节内容

## 执行过程
1. 从 `futu_api_doc_nav.md` 找到 Ticker 格式章节 URL
2. 阅读该章节，整理：
   - 各市场 Ticker 格式（美股、港股、A股等）
   - 格式规则（前缀.代码）
   - 特殊案例（指数、ETF 等）
3. 编写双向转换伪代码

## 产出物
**文件**：`docs/api_syntax_notes.md`（初始化）

**写入内容**：
```markdown
# futu-api 调用语法笔记
（本文件由 Step 1-A 初始化，Step 1-B 追加内容）

## 1. Ticker 格式规则
（来源：文档章节 XXX，URL：...）

### 格式
- 美股：`US.{SYMBOL}` → `US.AAPL`, `US.SPY`
- 港股：`HK.{5位数字}` → `HK.00700`
- ...

### 转换伪代码
def to_futu_ticker(symbol: str, market: str) -> str:
    # symbol: "AAPL", market: "US"/"HK"
    ...

def from_futu_ticker(futu_ticker: str) -> tuple[str, str]:
    # 返回 (symbol, market)
    ...
```

## 完成标准
- [ ] 覆盖美股、港股两类格式
- [ ] 双向转换伪代码逻辑完整
- [ ] 注明文档来源 URL
- [ ] 文件已初始化，包含文件头说明

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 1-B
- 已完成 → 追加 Step 1-A
- `docs/api_syntax_notes.md` → ✅ 已创建（Step 1-B 将追加内容）
