# FinCopilot V2.1 Agent API 设计文档

## 1. 设计目标

V2.1 的目标是将 FinCopilot 从 Assistant-first UI 进一步升级为真实 API 驱动的多 Agent Copilot。

Step 2 先构建 Agent API 基础层，包括配置、schema、prompts、guardrails 和 fallback。

## 2. Agent 架构

采用 Manager Agent + Specialist Agents 架构。

### Manager Agent

负责理解用户问题、识别 intent、选择专业 Agent、生成工具计划和澄清问题。

### Cashflow Agent

负责解释现金流风险和资金安全问题。

### Anomaly Agent

负责解释异常支出和可疑交易。

### Planning Agent

负责围绕经营目标生成谨慎的行动建议。

### Report Agent

负责生成负责任的报告和摘要。

### Safety Agent

负责检查输出是否越界。

## 3. 工具使用原则

LLM 不直接计算财务指标。
LLM 不直接判断异常。
所有关键数字来自本地 Python 工具。
LLM 负责规划、解释、追问和组织行动。

## 4. API 启用规则

真实 Agent API 只有在以下条件同时满足时启用：

- ENABLE_AGENT_API=true
- OPENAI_API_KEY 存在

否则使用 fallback。

## 5. 安全边界

系统不会：

- 自动付款；
- 自动转账；
- 认定交易为欺诈；
- 提供投资建议；
- 提供税务建议；
- 提供法律建议；
- 提供债务处置建议；
- 承诺财务结果。

## 6. 当前 Step 2 范围

当前只实现：

- config；
- schemas；
- prompts；
- safety guardrails；
- fallback；
- client config check。

尚未实现：

- 真实 Manager Agent API 调用；
- Specialist Agent API 调用；
- function calling tool router；
- UI 中真实 Agent 调用。

## 7. V2.1 Step 3：工具摘要层与 Tool Router

当前新增：

1. context_builder：将 app 当前状态转换为 LLM-safe context summary；
2. tool_schemas：定义 Agent 可用工具；
3. tool_router：根据工具名返回对应摘要；
4. chat page debug：在对话页展示当前上下文摘要和 fallback 工具摘要结果。

设计原则：

- 不将完整 DataFrame 传给 LLM；
- 只传关键指标和 Top records；
- 所有关键数字来自本地 Python 工具；
- tool router 只读，不修改数据；
- 真实 API 调用仍在后续步骤实现。

## 8. V2.1 Step 4：真实 Manager Agent API

当前已实现：

1. Manager Agent API 调用；
2. Manager Agent messages 构建；
3. JSON 输出解析；
4. Manager Plan validation；
5. Manager Plan safety check；
6. API fallback；
7. 对话页展示 Manager Plan；
8. 对话页展示 Manager 选择的工具摘要。

当前 Manager Agent 的职责仅限于任务理解与规划。

尚未实现：

1. Specialist Agent API 调用；
2. 完整多 Agent orchestrator；
3. function calling loop；
4. Agent 自动生成最终经营回复。

## 9. V2.1 Step 5：Specialist Agents API

当前已实现：

1. Cashflow Agent API；
2. Anomaly Agent API；
3. Planning Agent API；
4. Report Agent API；
5. Specialist Agent messages 构建；
6. Specialist Agent JSON 解析；
7. Specialist Agent result validation；
8. Specialist Agent safety guardrails；
9. Specialist Agent fallback；
10. 多 Agent 输出合成；
11. 对话页展示 Specialist Agent 输出。

当前完整流程：

用户问题
-> Manager Agent
-> Tool Router
-> Specialist Agents
-> Response Composer
-> Assistant Reply。

默认 Agent 模型：

gpt-5.4-mini

可以通过 OPENAI_AGENT_MODEL 覆盖。

## 10. V2.1 Step 6：Multi-Agent Orchestrator

当前已实现：

1. Multi-Agent Orchestrator；
2. 统一入口 `run_multi_agent_turn`；
3. Manager Agent / Tool Router / Specialist Agents / Composer / Safety 的集中编排；
4. 统一 trace；
5. Agent Chat session state；
6. 对话页调用 orchestrator；
7. Action Center 展示最新对话建议；
8. Report Center 展示最近一次 multi-agent trace。

当前完整流程：

用户输入
-> run_multi_agent_turn
-> Manager Agent
-> Tool Router
-> Specialist Agents
-> Response Composer
-> Safety Guardrails
-> Trace Builder
-> UI 展示回复与 trace。

尚未实现：

1. 将 suggested_actions 正式转为 action_items；
2. 将多 Agent 对话结果写入 Agent Workspace；
3. 跨 session 持久化；
4. 正式报告导出；
5. Agents SDK 版本。

## 11. V2.1 Step 7：Action / Report 同步与 V2.1 收尾

当前已实现：

1. Multi-Agent suggested_actions 转正式 action_items；
2. Chat-derived action items 同步到 Action Center；
3. Chat-derived action items 支持 pending / in_progress / done / ignored 状态更新；
4. Multi-Agent Report 生成；
5. Multi-Agent Trace Markdown 生成；
6. Report Center 展示最近一次 Multi-Agent Report；
7. Report Center 支持下载 Multi-Agent Report；
8. Report Center 支持下载 Multi-Agent Trace；
9. V2.1 checklist；
10. README V2.1 完成版；
11. demo_script V2.1 完成版。

当前完整流程：

用户自然语言问题
-> Manager Agent 任务规划
-> Tool Router 获取工具摘要
-> Specialist Agents 输出专业分析
-> Response Composer 生成回复
-> Safety Guardrails 检查
-> Trace Builder 生成轨迹
-> suggested_actions 转为正式 action_items
-> Action Center 跟踪行动项
-> Report Center 展示和下载 Multi-Agent Report。

当前仍未实现：

1. 跨 session 持久化；
2. 数据库；
3. 日历提醒；
4. 邮件催款；
5. OCR；
6. 真实银行接口；
7. Agents SDK 版本；
8. 完整 function calling loop。

## 12. V2.2 Step 1：统一 Copilot 主界面

当前已实现：

1. Sidebar 精简为 Copilot 主界面、分析详情、行动与报告、数据与设置；
2. Copilot 主界面支持数据状态展示；
3. Copilot 主界面支持交易、发票和目标 CSV 快速上传；
4. Copilot 主界面支持推荐问题；
5. Copilot 主界面直接承载 Agent Chat；
6. Copilot 主界面展示 assistant reply、建议行动、补充问题和 trace 摘要；
7. Copilot 主界面提供 Manager Plan、Tool Results、Specialist Outputs 和 Multi-Agent Report 展开区；
8. Agent API 改为默认尝试真实调用；
9. 缺少 API Key、Key 无效、模型不可用或 API 失败时自动 fallback；
10. UI 不再提供用户可见的 Agent API 启用开关。

V2.2 页面结构：

用户进入 Copilot 主界面
-> 上传或使用样例数据
-> 输入自然语言问题
-> Multi-Agent Orchestrator
-> 主界面展示核心回答
-> 行动与报告页面沉淀行动项和报告
-> 分析详情页面展示完整证据层。
