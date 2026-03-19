# Step 1-C：实机编程验证

## 目标
逐节提取 futu-api 示例代码，封装为独立函数，实机运行验证，捕获真实字段名和数据结构。
产出两个并列产出物：可用函数库 + 权威字段映射表。

## 加载资源
- `docs/nav/futu_api_doc_nav.md`（定位 `[has_example]` 章节）
- `docs/nav/futu_github_nav.md`（定位示例文件路径）
- `docs/api_syntax_notes.md`（参考调用语法，不视为权威）
- 每次迭代：只加载当前处理章节的示例代码（单节）

## 执行策略：迭代式单节处理

**每次迭代只处理一个 `[has_example]` 章节**，完整流程：
1. 从 `futu_api_doc_nav.md` 取下一个未处理的 `[has_example]` 章节 URL
2. 访问该章节或 GitHub 对应示例文件，提取示例代码
3. 封装为独立函数（格式见下）
4. 实机运行，打印完整输出（`print(data.dtypes)` + `print(data.head(2))`）
5. 从打印输出中提取：实际字段名、Python 数据类型、示例值
6. 验证连接正常关闭（无泄漏）
7. 将函数追加到 `futu_tested_functions.py`
8. 将字段信息追加到 `docs/field_mapping.md`
9. 处理下一章节

## P0 优先级（必须完成）
按此顺序执行：
1. `get_option_expiration_dates()` → 返回期权到期日列表
2. `get_option_chain()` → 返回期权链 DataFrame
3. `get_spot_price()` → 返回现货价格（标量）

## P1 优先级（P0 完成后执行）
4. 连接管理：封装 `create_quote_ctx()` / `close_ctx()`（含异常处理）
5. 批量调用测试：连续调用 P0 函数10次，确认无连接泄漏

## 产出物 1：`futu_tested_functions.py`

**函数格式模板**：
```python
def get_option_expiration_dates(ticker: str, host: str = "127.0.0.1", port: int = 11111) -> list[str]:
    """
    获取指定标的的期权到期日列表。
    
    文档来源：futu-api 文档 > 期权到期日 > {URL}
    GitHub 示例：{文件路径} L{行号}
    实机验证日期：{YYYY-MM-DD}
    
    Args:
        ticker: futu 格式 Ticker，如 "US.AAPL"
        host: futu OpenD 地址
        port: futu OpenD 端口
    
    Returns:
        到期日字符串列表，格式 "YYYY-MM-DD"
    
    实机输出示例：
        ["2025-01-17", "2025-02-21", ...]
    """
    import futu
    with futu.OpenQuoteContext(host=host, port=port) as ctx:
        ret, data = ctx.get_option_expiration_date(code=ticker)
        if ret != futu.RET_OK:
            raise RuntimeError(f"futu API error: {data}")
        return data['time'].tolist()
```

## 产出物 2：`docs/field_mapping.md`

**格式**：
```markdown
# futu-api 字段映射表
（本文件由 Step 1-C 基于实机运行输出生成，以实际输出为准）
（更新日期：YYYY-MM-DD）

## get_option_chain() 返回字段
| futu 字段名 | Python 类型 | 示例值 | 对应 yfinance 字段 | 说明 |
|---|---|---|---|---|
| strike_price | float64 | 150.0 | strike | 行权价 |
| call_bid_price | float64 | 2.5 | bid | 认购期权买价 |
| ... | ... | ... | ... | ... |

## get_market_snapshot() 返回字段（现货价格）
| futu 字段名 | Python 类型 | 示例值 | 对应用途 | 说明 |
|---|---|---|---|---|
| last_price | float64 | 185.2 | spot price | 最新成交价 |
| ... | ... | ... | ... | ... |
```

**关键要求**：
- 所有字段名来自 `print(data.dtypes)` 的实际输出，不来自文档
- 无「待确认」标注（有则说明该字段未经实机验证，不允许进入此文件）
- `对应 yfinance 字段` 列参考 `docs/nav/system_nav.md` 中 `option_chain()` 返回字段

## 完成标准
- [ ] P0 三个函数实机验证通过（有实际运行输出记录）
- [ ] `docs/field_mapping.md` 中所有字段来自实机输出，无「待确认」标注
- [ ] 10次连续调用无连接泄漏（P1 完成后检查）
- [ ] 每个函数有文档来源注释和验证日期

## ⚠️ 进入下一步的门控检查
**只有满足以下条件，才能更新 `project_state.md` 进入 Step 2-A**：
1. `futu_tested_functions.py` 包含全部 P0 函数
2. `docs/field_mapping.md` 存在且无「待确认」字样
3. 连接管理函数存在（P1 第4项）

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 2-A
- 已完成 → 追加 Step 1-C
- `futu_tested_functions.py` → ✅ P0 已验证（注明验证日期）
- `docs/field_mapping.md` → ✅ 已创建（注明字段数量）
