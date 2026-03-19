# Step 0-B：futu GitHub 仓库导航

## 目标
定位 futu-api GitHub 仓库中期权相关示例文件，供 Step 1-C 直接提取可运行代码。

## 加载资源
- `docs/nav/futu_api_doc_nav.md`（已存在）
- futu-api GitHub 仓库（在线访问）

## 执行过程
1. 访问 futu-api GitHub 仓库
2. 浏览 `/futu/` 主目录结构
3. 定位 `examples/` 或类似目录
4. 找到期权相关示例文件，记录完整路径
5. 浏览示例文件，确认包含哪些 API 的调用示例

## 产出物
**文件**：`docs/nav/futu_github_nav.md`

**格式模板**：
```markdown
# futu-api GitHub 导航

## 仓库根目录
- 仓库 URL：https://github.com/...
- 主要子目录：/futu/（核心库）, /examples/（示例）, /docs/（文档）

## 期权相关示例
- 文件：`examples/option_xxx.py` | 包含 API：get_option_chain, get_option_expiration_date
- 文件：`examples/quote_xxx.py` | 包含 API：get_market_snapshot

## 连接管理示例
- 文件：`examples/xxx.py` | 说明：OpenQuoteContext 使用示例

## 核心模块位置
- 期权相关：`futu/quote/xxx.py`
- 连接管理：`futu/common/xxx.py`
```

## 完成标准
- [ ] 至少一个期权相关示例文件的完整路径
- [ ] 示例文件包含 P0 优先级的至少一个 API（期权链 或 到期日）
- [ ] 仓库 URL 记录正确，可直接访问

## 完成后操作
更新 `project_state.md`：
- 当前步骤 → Step 0-C
- 已完成 → 追加 Step 0-B
- `docs/nav/futu_github_nav.md` → ✅ 已创建
