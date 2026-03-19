# OptionView 标准会话提示词

## 使用方法
每次新建会话时，将以下提示词连同 `project_state.md` 内容一起发给 AI。

---

## 提示词正文

```
你正在协助开发 OptionView 项目（futu-api 接入改造）。

## 本次会话任务

1. 读取下方的项目状态文件内容，确认当前步骤
2. 加载对应步骤文件：`steps/step_{当前步骤}.md`（文件名格式：step_0A, step_1C, step_2B 等）
3. 仅加载步骤文件中「加载资源」一节列出的文件，不加载其他内容
4. 按步骤文件执行，完成产出物
5. 会话结束时，输出更新后的 `project_state.md` 完整内容（直接覆盖）

## 执行约束
- 只新增本步骤负责的产出物，不修改其他步骤的产出物
- 不提前进入下一步骤（即使本步骤已完成）
- Step 1-C 中，逐个处理 [has_example] 章节
- Phase 2（Step 2-A 开始）需先确认 `project_state.md` 中 `futu_tested_functions.py` 和 `docs/field_mapping.md` 均为 ✅

## 当前项目状态文件内容
- 读取 project_state.md
```

---

## 特殊场景提示词变体

### 场景：Step 1-C 单次迭代
```
你正在执行 OptionView Step 1-C 的一次迭代。

本次处理章节：[填入章节名，如「期权链查询」]
文档 URL：[填入 URL]

任务：
1. 从该章节/GitHub 对应文件提取示例代码
2. 封装为 `futu_tested_functions.py` 格式的独立函数
3. 实机运行，打印完整输出（dtypes + head(2)）
4. 将字段信息追加到 `docs/field_mapping.md`
5. 报告是否通过，以及实际输出的字段名列表

不要处理其他章节，不要更新 project_state.md（状态在所有 P0 函数完成后统一更新）。
```

### 场景：验证特定产出物
```
请验证以下产出物是否满足完成标准：
- 文件：[文件名]
- 对照步骤文件：steps/step_[X].md 中的「完成标准」一节

逐条检查，输出通过/失败清单。
```
