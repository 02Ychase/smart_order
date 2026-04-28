# smart_order

## Backend setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python tools/seed_demo_data.py
python run.py
```

Demo login:

- username: `demo_user`
- password: `demo123456`

## Frontend setup

```bash
cd ui
npm install
npm run dev
```

## LangGraph Agent + Advanced RAG

The assistant uses LangGraph as the runtime state machine. Each chat session maps to a LangGraph thread ID, so short-term messages and recent actions are checkpointed per session.

The main flow is:

1. Load short-term and long-term memory.
2. Use an LLM planner to create a structured plan.
3. Route to RAG, local write action, undo, or direct answer.
4. Record reversible cart/address/preference writes in the action journal.
5. Generate grounded answers from evidence.

RAG uses multi-route recall, RRF fusion, hard filters, weighted reranking, diversification, and citation-backed evidence packs.

Focused verification:

```bash
python -m pytest tests/service/test_assistant_orchestrator.py tests/service/test_rag_retriever.py -q
python tools/evaluate_assistant_rag.py
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```



uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log


 npm --prefix ui run dev
