# FinCopilot V2.1 Assistant-First 布局规划

## 1. 为什么要重构布局

v2 已经具备完整 Agentic Workflow，但整体体验仍偏 Dashboard。用户需要主动进入不同页面查看不同模块。

V2.1 将系统重构为 Assistant-first，让用户首先感知到这是一个财务行动助手。

## 2. 新页面结构

- 助理首页
- 和 FinCopilot 对话
- Agent 工作台
- 财务分析
- 行动中心
- 报告中心
- 数据管理

## 3. 页面职责

### 助理首页

展示欢迎语、当前经营状态、推荐问题和关键提醒。

### 和 FinCopilot 对话

提供自然语言入口。当前 Step 1 为占位，后续接真实多 Agent API。

### Agent 工作台

展示任务规划、工具调用、追问补全、行动清单、状态跟踪和工作流报告。

### 财务分析

集中展示预算、发票、现金流、异常和目标。

### 行动中心

集中展示行动项和进展。

### 报告中心

集中展示 Copilot 摘要和 Agent 工作流报告。

### 数据管理

集中处理上传、预览和字段说明。

## 4. 后续演进

V2.1 后续步骤将接入真实多 Agent API，使“和 FinCopilot 对话”页面真正支持：

用户问题 -> Manager Agent -> Specialist Agents -> 工具调用 -> 追问 -> 行动建议 -> 报告。

## 5. V2.1 Step 2：Agent API 基础层

当前已新增 `agent_api/` 目录，用于承载后续真实多 Agent API。

设计原则：

- Manager Agent 负责理解用户问题和规划；
- Specialist Agents 负责现金流、异常、规划和报告；
- 本地 deterministic tools 继续负责财务计算；
- Safety Guardrails 负责输出边界；
- Fallback 负责无 API Key 或 API 失败时的稳定演示。

当前 Step 2 只完成基础层，不在 UI 中真实调用 API。
