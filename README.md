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

## Smart Assistant Agent + RAG

The assistant uses a controlled LLM Agent architecture:

1. Agent Planner classifies intent and emits a structured tool plan.
2. Tool Registry executes catalog search, recommendation, cart, and address tools.
3. Hybrid RAG combines query rewrite, Pinecone dense recall, metadata/keyword recall, SQL hard filters, reranking, and citation evidence.
4. Confirmation Manager gates side-effect operations such as cart updates and address saves.
5. Evaluation cases report recall@5 and constraint pass rate.

Focused verification:

```bash
python -m pytest tests/service/test_assistant_orchestrator.py tests/service/test_rag_retriever.py -q
python tools/evaluate_assistant_rag.py
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```



uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log


 npm --prefix ui run dev
