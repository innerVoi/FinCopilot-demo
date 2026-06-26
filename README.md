# FinCopilot V2.3

FinCopilot V2.3 is a Memory-Augmented Agentic CFO Copilot for small business owners.

It provides one English demo experience for uploading business data, asking finance questions, reviewing cash-flow risk, checking suspicious expenses, generating action items, saving reports, and reusing user-confirmed business memory.

## What V2.3 Adds

- SQLite-based business memory.
- `user_id / workspace_id` isolation.
- User feedback persisted to `user_feedback`.
- High-value feedback converted into `business_memory`.
- Memory context retrieved before Agent analysis.
- Agent turns, traces, reports, and action items persisted.
- Action item lifecycle with duplicate-feedback protection.
- Memory management UI.
- RAG future-plan fields reserved through `embedding_text` and `retrieval_tags`.

## Action Lifecycle

V2.3 persists action items in `action_memory`. New actions start as `pending`, and user feedback can move them to `done`, `ignored`, `rejected`, or `needs_follow_up`. Duplicate feedback is blocked at the service layer.

## Main Pages

1. **Copilot Home**: upload data, ask questions, review cards and detailed previews.
2. **Analysis Details**: inspect budget, invoices, cash flow, suspicious expenses, goals, and traces.
3. **Actions & Reports**: review action items, reports, and traces.
4. **Data & Settings**: manage data, API status, safety boundaries, and Memory & Workspace.

## Demo Questions

- Is cash flow safe for the next 30 days?
- Which expenses look most suspicious this month?
- Which invoices or payments should be prioritized?
- Generate my finance action plan for this week.

## Start

```bash
conda activate fincopilot
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## Environment

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=your_base_url_here
OPENAI_MODEL=gpt-5.4-mini
ENABLE_AGENT_API=true
OPENAI_AGENT_MODEL=gpt-5.4-mini
FINCOPILOT_MEMORY_DB_PATH=data/fincopilot_memory.db
FINCOPILOT_DEFAULT_USER_ID=demo_user
FINCOPILOT_DEFAULT_WORKSPACE_ID=demo_workspace
```

If the API key is missing or the live Agent call fails, FinCopilot automatically uses fallback mode.

## Safety Boundary

FinCopilot is for financial organization, risk reminders, and educational support only. It does not provide investment, tax, legal, debt-resolution, or professional financial advice. It does not determine fraud and does not execute payments or transfers.

## Verification

```bash
python -m py_compile app.py ui/*.py agent_api/*.py memory/*.py src/*.py agent/*.py
pytest
```

## License
Permitted only for personal learning, research, teaching, and other non-commercial purposes. Without the author’s written permission, it may not be used for commercial products, commercial services, internal business operations, SaaS services, outsourced projects, profit-oriented deployments, or any other commercial purposes.
