# Smart Order — 智能外卖助手

AI-Powered Food Delivery Assistant with Enterprise-Grade Agent & RAG Pipeline

---

## 📖 Overview · 项目简介

**Smart Order** is a full-stack food delivery system built around an **AI Agent** (LangGraph state machine) and an **enterprise-grade RAG** (Retrieval-Augmented Generation) pipeline. Users can browse merchants, manage carts, place orders, and have natural-language conversations with the AI assistant for dish recommendations, order management, and delivery inquiries.

The system features a **unified 8-tool Agent**, **multi-step plan execution**, **SSE streaming**, **multi-turn conversation memory**, **Cross-Encoder reranking**, **input/output guardrails**, **structured observability**, and **centralized configuration management**.

**智能外卖助手** 是一个全栈外卖点餐系统，核心是基于 **LangGraph 状态机 Agent** 和**企业级 RAG 管线**的 AI 助手。系统具备**统一 8 工具体系**、**多步计划执行**、**SSE 流式输出**、**多轮对话记忆**、**Cross-Encoder 精排**、**输入/输出安全护栏**、**结构化可观测性**和**集中配置管理**等企业级能力。

---

> **📚 Learning Project · 学习项目**  
> This project is built for **learning and educational purposes**. Parts of the codebase are developed with **Vibe Coding** — an AI-assisted development approach where some code is generated through iterative prompting rather than fully manual authoring. While the overall architecture and core logic are intentionally designed, certain modules may reflect experimental or AI-suggested patterns.  
> 本项目为**学习目的**而构建。部分代码采用了 **Vibe Coding**生成。整体架构和核心逻辑经过有意设计，但部分模块可能包含实验性或 AI 建议的模式。

---

## ✨ Features · 功能特性

### Core Business · 核心业务
- **Merchant & Dish Catalog** — Browse dishes by category, cuisine type, price range / 按分类、菜系、价格浏览菜品
- **Shopping Cart** — Add, update, remove cart items with persistent state / 购物车增删改查，状态持久化
- **Order Management** — Place orders, view order history and details / 下单、查看订单历史和详情
- **Address Management** — Save and manage delivery addresses / 管理收货地址
- **User Auth** — Register, login, JWT-based token refresh / 注册登录，JWT 令牌刷新

### AI Assistant · AI 智能助手
- **LangGraph Agent Runtime** — State-machine-based conversational agent with 8 unified tools / 基于状态机的对话智能体，统一 8 工具体系
- **Multi-step Plan Execution** — RAG → Action serialized workflows (e.g., search then add to cart) / 多步计划执行（搜索后加购物车）
- **LLM Query Rewriting** — Intelligent query expansion for better recall / LLM 查询改写，提升召回率
- **SSE Streaming** — Token-by-token streaming responses via Server-Sent Events / SSE 流式逐 token 输出
- **Multi-turn Conversation** — Thread-safe session history with LRU eviction / 多轮对话上下文管理，线程安全 LRU 淘汰
- **Async Endpoint** — Non-blocking chat via `asyncio.to_thread()` / 异步聊天端点

### RAG Pipeline · RAG 管线
- **4-Route Recall** — Dense vector (Pinecone), Sparse (BM25), SQL catalog, Business rules / 4 路召回：向量、稀疏、SQL、业务规则
- **RRF Fusion** — Reciprocal Rank Fusion to merge multi-route results / RRF 排序融合
- **Cross-Encoder Reranking** — DashScope gte-rerank semantic relevance scoring / Cross-Encoder 精排
- **Intent-based Weighted Reranking** — Dynamic weight profiles per query intent / 基于意图的动态加权重排序
- **Diversification** — Merchant-level result diversity / 商家级结果多样化
- **TieredCache** — Thread-safe LRU embedding cache replacing `@lru_cache` / 分层缓存替代 lru_cache

### Safety & Observability · 安全与可观测性
- **Input Guardrail** — Regex-based prompt injection detection / 输入护栏：正则注入检测
- **Output Guardrail** — Price hallucination detection against evidence / 输出护栏：价格幻觉检测
- **MetricsCollector** — Structured timers, counters, and metadata for agent & RAG nodes / 结构化指标采集
- **RAG Evaluation Framework** — Golden set testing with keyword recall and absence check / RAG 离线评估框架
- **Indexing Pipeline** — Catalog data → text → Pinecone upsert with namespace separation / 向量索引管线
- **Centralized Config** — `AppConfig` dataclass with nested RAG, Agent, Guardrail configs / 集中配置管理

### Grounding & Memory · 可信回答与记忆
- **Grounding & Citations** — Evidence-backed answers with source attribution / 带引用的可信回答
- **Undo Support** — Reversible actions (cart, address, preference changes) / 可撤销操作
- **Long-term Memory** — Persistent user preference learning / 用户偏好长期记忆

---

## 🏗️ Architecture · 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                           │
│           Element Plus · Axios · Vite · SSE Client              │
└──────────────────┬──────────────────────────────────────────────┘
                   │  HTTP / REST / SSE
┌──────────────────▼──────────────────────────────────────────────┐
│            Backend (FastAPI + Python 3.11+)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │         Assistant Service (LangGraph Agent)                │  │
│  │  InputGuardrail → LoadMemory → Plan → RAG/Action/Undo     │  │
│  │  → Evaluate → Respond (OutputGuardrail) → WriteMemory     │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │  ConversationStore │ StreamService │ MetricsCollector      │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌──────────┐ ┌───────────┐ ┌──────────────┐ ┌─────────────┐  │
│  │  Auth    │ │  Cart/    │ │  Address/    │ │  AppConfig  │  │
│  │  Service │ │  Catalog  │ │  Order       │ │  (central)  │  │
│  └──────────┘ └───────────┘ └──────────────┘ └─────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│                       Data Layer                                │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │   MySQL      │  │  Pinecone       │  │  DashScope        │  │
│  │  (SQLAlchemy)│  │  (Vector DB)    │  │  (Embedding/      │  │
│  │             │  │                 │  │   Cross-Encoder)  │  │
│  └──────────────┘  └─────────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Runtime Flow · Agent 运行流程

```
User Message
  │
  ▼
InputGuardrail ──(blocked)──► "请换一种方式提问"
  │ (allowed)
  ▼
LoadMemory → Plan (8 tools) → ┌── RAG (4-route recall → RRF → Filter
                               │        → CrossEncoder → WeightedRerank
                               │        → Diversify)
                               ├── Action (add_to_cart / remove_from_cart
                               │          / save_address / upsert_preference
                               │          / cart_clear)
                               ├── Undo (revert last action)
                               └── Evaluate (multi-step loop)
                                      │
                                      ▼
                               Respond (OutputGuardrail)
                                      │
                                      ▼
                               WriteMemory → SSE Stream / JSON Response
```

---

## 🛠️ Tech Stack · 技术栈

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Vue 3, Element Plus, Axios, Vite, Vitest |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, sse-starlette |
| **AI Runtime** | LangGraph (state machine), LangChain, LangChain-OpenAI |
| **RAG** | Pinecone (Vector DB), DashScope Embeddings & Cross-Encoder (gte-rerank), BM25 Sparse Recall, RRF Fusion |
| **Streaming** | SSE (Server-Sent Events) via sse-starlette |
| **Database** | MySQL 8.0+, SQLAlchemy 2.0, Alembic |
| **Auth** | JWT (python-jose), Passlib (pbkdf2_sha256) |
| **Observability** | MetricsCollector (structured timers/counters), RAG Evaluation Framework |
| **External APIs** | 高德地图 (AMap) for delivery distance, Tavily for web search |
| **Testing** | Pytest, pytest-asyncio, HTTPX, Vitest, Vue Test Utils |

---

## 🚀 Quick Start · 快速开始

### Prerequisites · 前置条件

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Pinecone account (for vector search)

### Backend Setup · 后端

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials

# Run database migrations
alembic upgrade head

# Seed demo data
python tools/seed_demo_data.py

# Start the server
python run.py
```

### Frontend Setup · 前端

```bash
cd ui
npm install
npm run dev
```

### Demo Login · 演示账号

| Field | Value |
|-------|-------|
| Username | `demo_user` |
| Password | `demo123456` |

---

## 📁 Project Structure · 项目结构

```
smart_order/
├── api/                            # FastAPI routes & schemas
│   ├── routes/                     # Route handlers (auth, cart, orders, assistant)
│   │   └── assistant.py            # Chat + SSE streaming endpoints
│   ├── models/                     # SQLAlchemy ORM models
│   ├── schemas.py                  # Pydantic request/response models
│   ├── main.py                     # FastAPI app entry
│   ├── db.py                       # Database connection
│   └── security.py                 # JWT auth utilities
├── service/                        # Business logic
│   ├── agent_runtime/              # LangGraph agent
│   │   ├── graph.py                # Agent graph definition (10 nodes)
│   │   ├── nodes.py                # Node implementations + guardrails
│   │   ├── planner.py              # Intent classification + tool dispatch
│   │   └── state.py                # Agent state TypedDict + data models
│   ├── rag/                        # RAG pipeline
│   │   ├── recall.py               # 4-route recall (Dense, Sparse, SQL, Business)
│   │   ├── fusion.py               # Reciprocal Rank Fusion
│   │   ├── filters.py              # Hard filters
│   │   ├── cross_encoder.py        # DashScope Cross-Encoder reranking
│   │   ├── reranker.py             # Intent-based weighted reranking + embedding cache
│   │   ├── diversifier.py          # Merchant-level diversity
│   │   ├── query_planner.py        # Query planning + constraint extraction
│   │   ├── query_rewriter.py       # LLM query rewriting
│   │   └── models.py               # RAG data models (FusedCandidate, RagEvidence)
│   ├── tools/                      # Tool implementations (cart, address, preference)
│   ├── assistant_service.py        # Main assistant orchestrator (sync + async)
│   ├── assistant_stream_service.py # SSE streaming service
│   ├── conversation_store.py       # Thread-safe multi-turn session store (LRU)
│   ├── cache.py                    # TieredCache (thread-safe LRU)
│   ├── config.py                   # AppConfig (RAG, Agent, Guardrail configs)
│   ├── guardrails.py               # Input/Output guardrails
│   ├── observability.py            # MetricsCollector (timers, counters, metadata)
│   └── ...                         # Cart, catalog, order, auth services
├── tools/                          # CLI tools & evaluation
│   ├── eval_golden_set.json        # RAG evaluation golden set (5 cases)
│   ├── rag_evaluation.py           # RAG offline evaluation framework
│   ├── indexing_pipeline.py        # Catalog → Pinecone indexing pipeline
│   └── ...                         # Seed data, vector store ops
├── prompt/                         # System prompts for agent
│   └── agent/                      # Planner, answer, memory, query rewrite prompts
├── repository/                     # Data access layer
├── database/                       # Migrations & seed data
├── tests/                          # Test suite (350+ tests)
│   ├── api/                        # API integration tests + stream tests
│   ├── service/                    # Service unit & integration tests
│   │   └── rag/                    # RAG-specific tests (reranker, cross-encoder, etc.)
│   └── ...                         # E2E agent flow tests
├── ui/                             # Vue 3 frontend
│   ├── src/                        # Components, views, composables, API clients
│   └── package.json
├── docs/                           # Design docs & plans
├── CLAUDE.md                       # AI assistant instructions
├── requirements.txt
└── pyproject.toml
```

---

## 🧪 Testing · 测试

```bash
# Run all backend tests (350+ tests)
pytest tests/ -v

# Run agent & RAG tests only
pytest tests/service/ -v

# Run specific test suites
pytest tests/service/test_langgraph_agent_graph.py -v   # Agent graph integration
pytest tests/service/test_multistep_plan.py -v          # Multi-step plan execution
pytest tests/service/test_guardrails.py -v              # Input/Output guardrails
pytest tests/service/rag/ -v                            # RAG pipeline tests

# Run RAG offline evaluation (golden set)
python tools/rag_evaluation.py

# Run legacy RAG evaluator
python tools/evaluate_assistant_rag.py

# Frontend tests
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```

---

## 🔑 Environment Variables · 环境变量

Key environment variables (configured in `.env`):

| Variable | Description |
|----------|-------------|
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` | LLM provider endpoint & key |
| `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` | Anthropic-compatible endpoint |
| `MODEL_NAME` | LLM model name |
| `DATABASE_URL` | MySQL connection string |
| `PINECONE_API_KEY` | Pinecone vector database key |
| `DASHSCOPE_API_KEY` | DashScope embedding key |
| `TAVILY_API_KEY` | Web search API key |
| `AMAP_API_KEY` | 高德地图 API key |
| `JWT_SECRET_KEY` | JWT signing secret |
| `LANGSMITH_API_KEY` | LangSmith tracing key |
| `QWEATHER_API_KEY` | Weather API key |

---

## 📚 Key Dependencies · 核心依赖

- **LangGraph** — Agent state machine with multi-step execution / 智能体状态机，支持多步执行
- **LangChain** — LLM orchestration & structured output / LLM 编排与结构化输出
- **Pinecone** — Vector semantic search / 向量语义搜索
- **DashScope** — Text embeddings (text-embedding-v4) & Cross-Encoder reranking (gte-rerank) / 文本嵌入与精排
- **sse-starlette** — Server-Sent Events for streaming / SSE 流式输出
- **FastAPI** — Web framework with async support / 异步 Web 框架
- **SQLAlchemy** — ORM / 数据库 ORM
- **Vue 3** — Frontend framework / 前端框架
- **Element Plus** — UI component library / UI 组件库

---

## 🔧 Configuration · 配置管理

The system uses a centralized `AppConfig` dataclass (`service/config.py`) with nested configs:

```python
AppConfig
├── RagConfig          # cache_max_size, cache_ttl, recall_limit,
│                      # cross_encoder_top_k, intent_weights, bm25 params
├── AgentConfig        # max_iterations, conversation limits
└── GuardrailConfig    # max_input_length, enable_input/output_guardrail
```

Override defaults via `set_config()` for testing, or extend to load from environment variables for production.

---

## 📄 License · 许可证

MIT
