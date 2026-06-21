# FinCopilot

FinCopilot 是一个面向无专职财务小微企业主的财务分析 Copilot，目前demo已迭代到V2.2版本。

用户可以在一个主界面中完成数据上传、自然语言提问、核心结果查看、行动项生成和报告预览。系统默认尝试调用真实 Agent API，并在 API Key 缺失、模型不可用、调用失败或输出解析失败时自动 fallback。

FinCopilot 的目标不是替代专业财务顾问，而是帮助小微企业主快速回答三个问题：

1. 我现在的钱够不够？
2. 哪些支出有问题？
3. 接下来该优先收钱、付款还是控费？

本项目仅用于财务整理、风险提醒和教育性支持，不构成投资、税务、法律、债务处置或专业财务建议。

## 目标用户

- 小微企业主；
- 小型工作室负责人；
- 自由职业团队负责人；
- 早期创业团队运营者。

这些用户通常没有专职财务团队，需要自己处理交易流水、发票、供应商付款、客户回款和现金流压力。FinCopilot 的目标是把“看数据”推进到“形成行动”。

## 页面结构

V2.2 将原有多个页面收敛为四个入口：

1. **Copilot 主界面**：上传数据、提问、查看结果卡片和详细预览；
2. **分析详情**：查看预算、发票、现金流、异常、目标和 Agent 执行轨迹；
3. **行动与报告**：查看行动项、Multi-Agent 报告和 Trace；
4. **数据与设置**：查看数据预览、字段说明、Agent 与模型状态、安全边界。

## Copilot 主界面

Copilot 主界面是 V2.2 的默认入口。

用户可以在这里完成：

- 查看交易、发票、目标数据状态；
- 快速上传 CSV 或使用默认样例数据；
- 查看新手引导和数据缺失提示；
- 点击推荐任务自动执行问题；
- 直接输入自然语言问题；
- 查看结果卡片；
- 展开详细结果预览；
- 查看报告入口和后续推荐问题。

## Multi-Agent 架构

FinCopilot V2.2 采用 Manager Agent + Specialist Agents + Deterministic Tools 的架构。

完整流程：

```text
用户自然语言提问
-> Manager Agent 理解任务
-> Tool Router 获取本地工具摘要
-> Specialist Agents 分析
-> Response Composer 生成回复
-> Safety Guardrails 检查
-> Trace Builder 生成轨迹
-> Suggested Actions 转为正式行动项
-> Report Builder 生成报告
```

其中：

- Manager Agent 负责识别 intent、选择 Specialist Agents、规划 tool_plan 和提出 clarifying_questions；
- Cashflow Agent 负责现金流风险解释；
- Anomaly Agent 负责异常支出解释；
- Planning Agent 负责经营计划和目标建议；
- Report Agent 负责整理总结；
- 本地 Python 工具负责预算、发票、现金流、异常检测、行动项和报告等确定性计算。

所有关键数值来自本地工具。LLM 不直接计算财务指标，不读取完整 DataFrame，不修改原始数据。

## Agent API 策略

V2.2 默认尝试使用真实 Agent API。

用户不需要手动选择是否启用 Agent API。

系统行为如下：

- 如果 `OPENAI_API_KEY` 存在，则优先调用真实 Manager Agent 和 Specialist Agents；
- 如果 API Key 缺失、模型不可用、调用失败或输出解析失败，系统会自动 fallback；
- fallback 模式仍然可以使用本地规则、工具摘要和模板化 Agent 输出完成基础分析；
- UI 中不提供“启用 / 关闭 Agent API”的用户开关；
- `ENABLE_AGENT_API=false` 仅用于开发调试时强制 fallback。

默认模型为：

```env
OPENAI_AGENT_MODEL=gpt-5.4-mini
OPENAI_MODEL=gpt-5.4-mini
```

默认兼容接口地址为：

```env
OPENAI_BASE_URL=https://api.openai.com
```

如果当前环境不支持该模型，可以在 `.env` 中改为账号可用模型。

## 环境配置

```bash
conda create -n fincopilot python=3.10 -y
conda activate fincopilot
pip install -r requirements.txt
cp .env.example .env
```

`.env.example` 默认包含：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com
OPENAI_MODEL=gpt-5.4-mini
ENABLE_AGENT_API=true
OPENAI_AGENT_MODEL=gpt-5.4-mini
```

保持占位符或未配置 Key 时，系统会自动 fallback，不会发起真实 API 调用。

## 启动方式

```bash
conda activate fincopilot
python -m streamlit run app.py
```

或：

```bash
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## 数据格式

### transactions.csv

```text
date,description,merchant,amount,type,account
```

`amount` 为正数表示收入，为负数表示支出。

### invoices.csv

```text
invoice_id,vendor,due_date,amount,status,category
```

`status` 支持 `paid`、`unpaid`、`overdue`。

### goals.csv

```text
goal_id,goal_name,target_amount,current_amount,due_date,priority
```

`priority` 支持 `high`、`medium`、`low`。

## 演示流程

1. 打开系统，默认进入 Copilot 主界面；
2. 查看新手引导、数据状态和 Agent 状态；
3. 使用默认样例数据，或上传交易、发票和目标 CSV；
4. 点击推荐任务“检查未来 30 天现金流”；
5. 系统自动执行“未来 30 天现金流安全吗？”；
6. 查看结果卡片、风险提醒、建议行动和补充问题；
7. 展开详细结果预览，查看现金流、发票、异常、目标、行动项、报告和 Agent 执行摘要；
8. 进入“分析详情”，查看完整表格和 Agent 执行轨迹；
9. 进入“行动与报告”，查看行动项、Multi-Agent 报告和 Trace；
10. 进入“数据与设置”，查看数据预览、字段说明、模型状态和安全边界。

推荐演示问题：

- 未来 30 天现金流安全吗？
- 这个月哪些支出最可疑？
- 有哪些发票或付款要优先处理？
- 帮我生成本周财务行动清单。

## V2.2 相比 V2.1 的变化

V2.1 已经具备真实多 Agent 能力，但界面仍然较分散。

V2.2 的重点是产品体验收敛：

| 维度 | V2.1 | V2.2 |
|---|---|---|
| 主入口 | 多个页面并列 | 一个 Copilot 主界面 |
| 数据上传 | 数据管理页为主 | 主界面可上传 |
| 问题输入 | 独立对话页 | Copilot 主界面 |
| 结果展示 | 文本 + 多个详情页 | 结果卡片 + 内嵌详情 |
| 详情查看 | 需频繁跳转 | 主界面预览 + 详情页归档 |
| 新手引导 | 较弱 | 空状态、推荐任务、下一步提示 |
| Agent API | 可配置启用 | 默认尝试启用，失败自动 fallback |

## 安全边界

FinCopilot V2.2 仅用于财务整理、风险提醒和教育性支持，不构成投资、税务、法律、债务处置或专业财务建议。

系统不会：

- 自动付款；
- 自动转账；
- 认定任何交易为欺诈；
- 提供投资建议；
- 提供税务建议；
- 提供法律建议；
- 提供债务处置建议；
- 承诺任何财务结果。

重要交易和财务决策请核查原始凭证，并在必要时咨询合格专业人士。

## 测试命令

```bash
python -m py_compile app.py
python -m py_compile ui/navigation.py
python -m py_compile ui/copilot_main.py
python -m py_compile ui/onboarding_panel.py
python -m py_compile ui/task_recommendations.py
python -m py_compile ui/result_cards.py
python -m py_compile ui/inline_detail_preview.py
python -m py_compile ui/analysis_detail_page.py
python -m py_compile ui/action_report_page.py
python -m py_compile ui/data_settings_page.py
python -m py_compile agent_api/config.py
python -m py_compile agent_api/answer_presenter.py
python -m py_compile agent_api/detail_preview_builder.py
pytest
```

测试不真实调用 OpenAI API。无 API Key 时系统仍可 fallback。

## License
仅允许个人学习、研究、教学等非商业用途；未经作者书面许可，不得用于商业产品、商业服务、公司内部业务、SaaS 服务、外包项目、盈利性部署或其他商业目的。