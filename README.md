# Smart Order — AI-Powered Food Delivery Assistant

智能外卖点菜系统 · AI 驱动

---

## 📖 Overview · 项目简介

**Smart Order** is a full-stack food delivery ordering system built around an **AI Agent** (LangGraph) and **RAG** (Retrieval-Augmented Generation) pipeline. Users can browse merchants, manage carts, place orders, and have natural-language conversations with the AI assistant for dish recommendations, order management, and delivery inquiries.

**Smart Order** 是一个全栈智能外卖点菜系统，核心是基于 **AI Agent**（LangGraph）和 **RAG**（检索增强生成）管线的 AI 助手。用户可浏览商家、管理购物车、下单，并通过自然语言与 AI 助手交互，获取菜品推荐、订单管理和配送咨询等服务。

---

> **📚 Learning Project · 学习项目**  
> This project is built for **learning and educational purposes**. Parts of the codebase are developed with **Vibe Coding** — an AI-assisted development approach where some code is generated through iterative prompting rather than fully manual authoring. While the overall architecture and core logic are intentionally designed, certain modules may reflect experimental or AI-suggested patterns.  
> 本项目为**学习和教育目的**而构建。部分代码采用了 **Vibe Coding**（一种 AI 辅助开发的方式）生成。整体架构和核心逻辑经过有意设计，但部分模块可能包含实验性或 AI 建议的模式。

---

## ✨ Features · 功能特性

### Core Business · 核心业务
- **Merchant & Dish Catalog** — Browse dishes by category, cuisine type, price range / 按分类、菜系、价格浏览菜品
- **Shopping Cart** — Add, update, remove cart items with persistent state / 购物车增删改查，状态持久化
- **Order Management** — Place orders, view order history and details / 下单、查看订单历史和详情
- **Address Management** — Save and manage delivery addresses / 管理收货地址
- **User Auth** — Register, login, JWT-based token refresh / 注册登录，JWT 令牌刷新

### AI Assistant · AI 智能助手
- **LangGraph Agent Runtime** — State-machine-based conversational agent / 基于状态机的对话智能体
- **RAG Pipeline** — Multi-route recall, RRF fusion, weighted reranking, diversification / 多路召回、RRF 融合、加权重排序、结果多样化
- **Grounding & Citations** — Evidence-backed answers with source attribution / 带引用的可信回答
- **Undo Support** — Reversible actions (cart, address, preference changes) / 可撤销操作（购物车、地址、偏好变更）
- **Long-term Memory** — Persistent user preference learning / 用户偏好长期记忆

---

## 🏗️ Architecture · 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                  │
│         Element Plus · Axios · Vite                  │
└──────────────────┬──────────────────────────────────┘
                   │  HTTP / REST API
┌──────────────────▼──────────────────────────────────┐
│          Backend (FastAPI + Python 3.11+)            │
│  ┌──────────────────────────────────────────────┐   │
│  │         Assistant Service (LangGraph)         │   │
│  │  LoadMemory → Plan → RAG/Action/Undo → Write │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │  Auth    │ │  Cart/    │ │  Address/Order   │   │
│  │  Service │ │  Catalog  │ │  Service         │   │
│  └──────────┘ └───────────┘ └──────────────────┘   │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│                  Data Layer                          │
│  ┌──────────────┐  ┌────────────────────────────┐   │
│  │   MySQL      │  │  Pinecone Vector Database  │   │
│  │  (SQLAlchemy)│  │  (Semantic Search)         │   │
│  └──────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Agent Runtime Flow

```
User Message → LoadMemory → Plan → ┌── RAG (semantic + SQL + business recall)
                                    ├── Action (cart/address/preference)
                                    ├── Undo (revert last action)
                                    └── Respond (grounded answer with citations)
                                         → WriteMemory → Response
```

---

## 🛠️ Tech Stack · 技术栈

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Vue 3, Element Plus, Axios, Vite, Vitest |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **AI Runtime** | LangGraph, LangChain, LangChain-OpenAI |
| **RAG** | Pinecone (Vector DB), DashScope Embeddings, Multi-Route Recall, RRF Fusion |
| **Database** | MySQL 8.0+, SQLAlchemy 2.0, Alembic |
| **Auth** | JWT (python-jose), Passlib (pbkdf2_sha256) |
| **External APIs** | 高德地图 (AMap) for delivery distance, Tavily for web search |
| **Testing** | Pytest, HTTPX, Vitest, Vue Test Utils |

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
├── api/                        # FastAPI routes & schemas
│   ├── routes/                 # Route handlers (auth, cart, orders, etc.)
│   ├── models/                 # SQLAlchemy ORM models
│   ├── main.py                 # FastAPI app entry
│   ├── db.py                   # Database connection
│   └── security.py             # JWT auth utilities
├── service/                    # Business logic
│   ├── agent_runtime/          # LangGraph agent (graph, nodes, planner, state)
│   ├── rag/                    # RAG pipeline (recall, fusion, reranker, filters)
│   ├── tools/                  # Tool implementations (cart, address, preference)
│   ├── assistant_service.py    # Main assistant orchestrator
│   └── ...                     # Cart, catalog, order, auth services
├── agent/                      # Agent configuration
├── tools/                      # CLI tools (seed data, eval, vector store ops)
├── prompt/                     # System prompts for agent
├── repository/                 # Data access layer
├── database/                   # Migrations & seed data
│   ├── migrations/             # Alembic migrations
│   └── seeds/                  # Demo data
├── tests/                      # Test suite
│   ├── api/                    # API integration tests
│   ├── service/                # Service unit & integration tests
│   └── e2e/                    # End-to-end agent flow tests
├── ui/                         # Vue 3 frontend
│   ├── src/                    # Components, views, composables, API clients
│   └── package.json
├── docs/                       # Design docs & plans
├── CLAUDE.md                   # AI assistant instructions
├── requirements.txt
└── pyproject.toml
```

---

## 🧪 Testing · 测试

```bash
# Run all backend tests
pytest

# Run specific test file
pytest tests/service/test_agent_planner.py -v

# Run RAG evaluation
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

- **LangGraph** — Agent state machine / 智能体状态机
- **LangChain** — LLM orchestration / LLM 编排框架
- **Pinecone** — Vector semantic search / 向量语义搜索
- **FastAPI** — Web framework / Web 框架
- **SQLAlchemy** — ORM / 数据库 ORM
- **Vue 3** — Frontend framework / 前端框架
- **Element Plus** — UI component library / UI 组件库

---

## 📄 License · 许可证

MIT
