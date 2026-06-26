# FinCopilot V2.3 RAG Future Plan

## 1. 当前状态

V2.3 当前不实现完整 RAG，也不实现向量数据库。

当前系统采用结构化 memory 检索：

- 按 user_id 过滤；
- 按 workspace_id 过滤；
- 按 memory_type 检索；
- 按关键词检索 fact_text、entity_name 和 retrieval_tags。

## 2. 为什么 V2.3 暂不做完整 RAG

当前 FinCopilot 的核心数据主要是结构化财务数据和结构化业务记忆，而不是长文档问答。

V2.3 的重点是：

- 用户隔离；
- workspace 隔离；
- 业务事实沉淀；
- 行动项生命周期；
- Agent turn / trace / report 持久化；
- memory_context 注入 Agent workflow。

过早引入完整向量数据库会增加复杂度，但对当前 Demo 的解释力提升有限。

## 3. 已经预留的 RAG 字段

business_memory 表中已经预留：

- embedding_text
- retrieval_tags

其中：

- retrieval_tags 当前已经可用于关键词检索；
- embedding_text 后续可用于生成向量。

## 4. 未来 RAG 的正确检索顺序

未来加入 RAG 时，必须遵循：

```text
先过滤 user_id
-> 再过滤 workspace_id
-> 再进行向量相似度检索
-> 构建 memory_context_summary
-> 注入 Agent workflow
```

禁止：

```text
全库向量检索
跨用户检索
跨 workspace 检索
把所有用户 memory 混入 prompt
```

## 5. 未来可扩展内容

后续版本可以支持：

1. business_memory embedding；
2. reports embedding；
3. feedback embedding；
4. action history embedding；
5. workspace-level vector index；
6. hybrid retrieval：structured filter + keyword + vector similarity；
7. memory citation；
8. memory confidence scoring；
9. memory aging / expiration；
10. memory conflict detection。

## 6. 推荐后续版本

建议：

- V2.4：应收应付管理 + 7/30/90 天现金流预测；
- V2.5：结构化 memory + lightweight RAG；
- V2.6：OCR / 文件解析 / 发票文档检索；
- V2.7：更完整的多用户账户系统。
