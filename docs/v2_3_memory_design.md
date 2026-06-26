# FinCopilot V2.3 Memory Design

## 1. 目标

V2.3 引入基于数据库的、用户隔离的业务 memory。

## 2. 核心原则

- 所有 memory 都必须带 user_id；
- 所有 memory 都必须带 workspace_id；
- 所有查询必须在当前 user_id / workspace_id 下进行；
- 禁止跨用户检索；
- 后续 RAG 也必须先过滤 user_id / workspace_id。

## 3. 数据库

默认使用 SQLite：

```text
data/fincopilot_memory.db
```

## 4. 当前默认身份

- user_id: demo_user
- workspace_id: demo_workspace

## 5. 当前 Step 1 完成内容

- SQLite 初始化；
- users 表；
- workspaces 表；
- memory 相关表预创建；
- 数据与设置页展示当前 user/workspace；
- 报告摘要展示修复。

## 6. Step 2 完成内容

Step 2 增加 Business Memory 的存储、检索和展示能力。

- `memory/memory_service.py` 提供 Business Memory 新增、查询、列表、停用、计数和 last_used_at 更新；
- `memory/retrieval.py` 根据任务类型检索当前 user/workspace 范围内的业务记忆；
- 所有 Business Memory 查询都带 `user_id` 和 `workspace_id` 过滤；
- `ui/memory_panel.py` 提供 Business Memory 上下文展示和管理面板；
- Copilot 主界面在推荐任务之后展示当前可用 Business Memory 上下文；
- 数据与设置页的 Memory 与工作区 Tab 支持查看、新增和停用 Business Memory；
- 本步骤不接入 RAG，不修改 Agent prompt，不改变 `run_multi_agent_turn` 执行链路。

## 7. V2.3 Step 3：用户反馈 → Memory 写入

Step 3 打通用户反馈到业务记忆的写入链路。

用户可以反馈：

- 某笔支出是正常支出；
- 某个供应商是长期合作方；
- 某项支出是周期性支出；
- 当前现金余额是多少；
- 未来预计回款是多少；
- 某个风险需要持续关注；
- 某个行动项已经完成或暂时忽略；
- 某条建议不适合当前业务。

系统会将所有反馈写入 `user_feedback`，并将部分高价值反馈确定性转换为 `business_memory`。

所有反馈和 memory 都必须绑定当前 `user_id` 和 `workspace_id`。

本步骤不把 memory 注入 Agent prompt，不修改 `run_multi_agent_turn`，不实现 RAG 或向量数据库。

## 8. V2.3 Step 4：Memory-Augmented Agent Orchestrator 与行动项反馈闭环

Step 4 将 `memory_context_summary` 正式接入 Agent 编排流程。

每次 Agent 分析前，系统会：

- 在当前 `user_id / workspace_id` 下检索相关 Business Memory；
- 构建 `memory_context`；
- 将 `memory_context` 注入 Agent context summary；
- 让 Manager Agent 和 Specialist Agents 可以参考用户此前确认过的业务事实；
- 在 `turn_result` 中记录 `memory_context`、`memory_trace`、`used_memory_ids` 和 `memory_augmented`；
- 在 trace、结果卡片和详细预览中展示本轮实际参考的历史记忆；
- 更新本轮使用过的 memory 的 `last_used_at`。

本步骤仍不做 RAG、向量数据库或 embedding，也不会把完整 memory 表传给 LLM。

同时，Step 4 补齐行动项反馈闭环：

- 行动与报告页支持针对具体 action item 提交反馈；
- 行动项反馈必须填写原因；
- 原因写入 `user_feedback.feedback_text`；
- `target_type` 固定为 `action_item`；
- `target_id` 记录具体 `action_id`；
- 支持 `complete_action`、`ignore_action`、`reject_suggestion` 和 `needs_follow_up`；
- 行动项反馈只写入 `user_feedback`，不自动创建 `business_memory`。

## 9. V2.3 Step 5：Turn / Trace / Report / Action 持久化

Step 5 完成 Agent 运行结果和行动项生命周期的持久化闭环。

系统会在每次 Agent turn 完成后写入：

- `agent_turns`：用户问题、Manager Plan、工具结果、Specialist 输出、最终回答和模式；
- `agent_traces`：完整 trace JSON 和 trace markdown；
- `reports`：报告标题、报告摘要和完整 markdown；
- `action_memory`：本轮生成的行动项。

Action lifecycle：

- 新行动项初始状态为 `pending`；
- 用户提交行动项反馈后，状态变为 `done`、`ignored`、`rejected` 或 `needs_follow_up`；
- 已处理行动项不再显示反馈表单；
- 服务层会阻止重复反馈，重复提交不会新增 `user_feedback`；
- 反馈原因写入 `user_feedback.feedback_text`，并同步写入 `action_memory.metadata_json`。

所有 turn、trace、report、action 和 feedback 都必须绑定当前 `user_id / workspace_id`。

## 10. V2.3 Step 6：Memory 管理 UI 与用户 / 工作区隔离验证

Step 6 将 V2.3 已经沉淀到数据库中的内容集中展示到 Memory 管理界面中。

该界面位于：

```text
数据与设置 → Memory 与工作区
```

它支持：

- 查看当前 `user_id` 和 `workspace_id`；
- 切换当前 demo workspace；
- 创建当前用户下的 demo workspace；
- 查看 `business_memory`；
- 查看 `user_feedback`；
- 查看 `action_memory`，并区分待办与已处理行动项；
- 查看 `agent_turns`；
- 查看 `reports`，其中 `report_title` 放标题，`report_summary` 放正文，`report_markdown` 放展开区；
- 停用当前 workspace 下的 Business Memory；
- 清理当前 workspace 的 memory 数据；
- 验证不同 workspace 的 memory / feedback / actions / reports 不串用。

清理操作只作用于当前 `user_id` 和 `workspace_id`，不会删除 `users` 或 `workspaces`，也不会影响其他用户或其他 workspace。

V2.3 当前仍只使用结构化 memory 检索，不做向量检索。`business_memory.embedding_text` 和 `business_memory.retrieval_tags` 是为后续 RAG 预留的字段。

## 11. V2.3 Step 7：V2.3 收尾与 RAG 铺垫

Step 7 完成 V2.3 的版本收尾，包括：

- README 完整版；
- demo_script 完整版；
- v2_3_checklist；
- RAG future plan；
- 最终 readiness tests；
- 完整演示路径；
- 最终验收标准。

V2.3 的最终定位是：

```text
FinCopilot V2.3：Memory-Augmented Agentic CFO Copilot
```

它通过数据库驱动、用户隔离的业务 memory，让 FinCopilot 从一次性分析工具升级为能够记住用户业务背景、复用历史反馈、追踪行动项状态并持续改进分析上下文的 agentic system。

## 12. 后续步骤

- V2.4：应收应付管理 + 7/30/90 天现金流预测；
- V2.5：Workspace-Isolated Lightweight RAG。
