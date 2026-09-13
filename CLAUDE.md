# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🔴 动手前必读：执行循环协议

本仓库当前的施工由 [`docs/hardening/LOOP-PROTOCOL.md`](docs/hardening/LOOP-PROTOCOL.md) 驱动，**该文件优先级高于本文件**。

在开始任何 ticket 之前，**必须重读该文件**（不得凭记忆推断流程），然后按顺序读：

1. `docs/hardening/LOOP-PROTOCOL.md` —— 流程权威来源
2. `docs/hardening/prd.md` —— 需求与验收口径
3. `docs/hardening/TRACKER.md` —— 恢复当前进度
4. `docs/hardening/tickets/T<编号>-*.md` —— 当前 ticket 的完整定义

要点速览（细节以协议文件为准）：

- 单 ticket：`/implement` → **跳过自带 `/code-review`** → 测试全绿后自行 commit → 追加 TRACKER 记录
- 每 3 个 ticket：对累计 diff 跑一次批量 `/code-review`，fixed point = 上一批审查结束时的 commit
- 全部完成后：对整条分支跑最终全量 `/code-review`，fixed point = `main`
- 每张 ticket 一条分支 + PR，不用 squash，保留 commit 粒度
- **密钥红线**：严禁把真实密钥写入任何被 git 跟踪的文件

## Project Overview

行业信息助手 (Industry Information Assistant) — an AI-powered deep research assistant with multi-agent collaboration, supporting intelligent search, knowledge graphs, chart visualization, stock data, bidding info, and news collection. Targeted at industry research in smart transportation, fintech, healthcare, and energy sectors.

**Tech Stack:**
- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, LangGraph, LangChain
- **Frontend:** React 19, TypeScript, Vite, Ant Design 5, ECharts, Valtio (state)
- **Infrastructure:** PostgreSQL 15, Redis 7, Milvus 2.3 (vector DB), Elasticsearch 8 (optional), MinIO (object storage)
- **LLM:** Alibaba Cloud DashScope (aliyun bailian) — `deepseek-v3.2`, `qwen-plus`; also supports OpenRouter

## Project Structure

```
industry_information_assistant/
├── backend/
│   ├── app/
│   │   ├── app_main.py              # FastAPI entry point
│   │   ├── config/
│   │   │   ├── llm_config.py        # LLM & agent model config (central)
│   │   │   ├── industry_config.py   # Industry keyword definitions
│   │   │   └── stock_mapping.py     # Company-to-stock-code map
│   │   ├── core/
│   │   │   ├── database.py          # SQLAlchemy engine/session
│   │   │   ├── redis_client.py      # Redis connection
│   │   │   └── security.py          # JWT auth utilities
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py, chat.py, knowledge.py, news.py
│   │   │   ├── industry_data.py, research.py
│   │   ├── router/                  # FastAPI routers (REST endpoints)
│   │   │   ├── auth_router, chat_router, search_router
│   │   │   ├── research_router, news_router, knowledge_router
│   │   │   ├── database_router, session_router, memory_router
│   │   │   ├── document_router, attachment_router, bidding_router
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── service/                 # Business logic (core of the app)
│   │   │   ├── deep_research_v2/    # Multi-agent research system ⭐
│   │   │   │   ├── graph.py         # LangGraph workflow (Plan→Research→Analyze→Write→Review→Revise)
│   │   │   │   ├── state.py         # Shared state / TypedDict for agents
│   │   │   │   ├── service.py       # Service entry (SSE streaming)
│   │   │   │   └── agents/          # Individual agents (architect, scout, analyst, wizard, critic, writer)
│   │   │   ├── chat_service.py/v2   # Chat logic
│   │   │   ├── retrieval_service.py # RAG retrieval
│   │   │   ├── web_search_service.py
│   │   │   ├── news_collection_service.py
│   │   │   ├── docmind_service.py   # Document parsing (Alibaba DocMind)
│   │   │   ├── chart_generator.py   # Data visualization (matplotlib/seaborn)
│   │   │   ├── stock_service.py     # Stock data
│   │   │   ├── bidding_service.py   # Bidding/tender info
│   │   │   ├── text2sql_service.py  # NL-to-SQL
│   │   │   ├── embedding_service.py, milvus_service.py  # Vector search
│   │   │   ├── checkpoint_service.py, memory_service.py
│   │   │   └── scheduler_service.py # Cron-like news collection scheduler
│   │   └── scripts/                 # Data init/seeding scripts
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx, main.tsx
│   │   ├── api/                     # API client (axios-based, plugin system)
│   │   │   ├── request/             # Request plugins: auth, error-toast, loading, repeat
│   │   │   ├── session.ts, auth.ts, news.ts, knowledge.ts, etc.
│   │   ├── components/              # Shared UI components
│   │   │   ├── chart/               # ECharts wrapper
│   │   │   ├── sender/              # Chat input
│   │   │   ├── markdown/            # Markdown renderer
│   │   │   ├── chunks-drawer/       # RAG chunks drawer
│   │   │   ├── upload-modal/        # File upload
│   │   │   └── stock-card/          # Stock display card
│   │   ├── pages/
│   │   │   ├── chat/                # Main chat & research pages (streaming UI)
│   │   │   │   ├── index.tsx        # Chat session view
│   │   │   │   ├── newchat.tsx      # New chat landing
│   │   │   │   └── component/       # Chat sub-components (research-process, step-detail-panel, research-detail with knowledge-graph, search-results, visualization, process-report)
│   │   │   ├── knowledge/           # Knowledge base management
│   │   │   ├── database/            # Database explorer
│   │   │   ├── news/                # News collection
│   │   │   ├── bidding/             # Bidding info
│   │   │   ├── auth/                # Login page
│   │   │   └── index/               # Landing page
│   │   ├── store/                   # Valtio state stores
│   │   ├── router/                  # React Router config
│   │   └── layout/                  # Base layout (nav, footer)
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml               # All infra services
├── docker/init-db/                  # DB init scripts
└── start-services.sh                # One-click start script
```

## Development Commands

### Infrastructure (Docker)
```bash
# Start all dependency services (PostgreSQL, Redis, Milvus, ES, MinIO)
./start-services.sh start

# Check status
./start-services.sh status

# Stop all
./start-services.sh stop
```

### Backend
```bash
cd backend

# Create/activate venv (conda recommended)
conda create -n deepresearch python=3.10
conda activate deepresearch

# Install dependencies
pip install -r requirements.txt

# Copy & edit .env (must fill DASHSCOPE_API_KEY and BOCHA_API_KEY)
cp .env.example .env

# Start backend
python app/app_main.py          # Runs on :8000

# Or with uvicorn directly
uvicorn app_main:app --reload   # Hot-reload for development
```

### Frontend
```bash
cd frontend

# Install (note: --legacy-peer-deps needed for React 19 + Ant Design)
npm install --legacy-peer-deps

# Dev server (runs on :5183, proxies API to backend)
npm run dev

# Build
npm run build

# Lint
npm run lint

# Preview production build
npm run preview
```

### API Endpoints (key ones)
- `GET /hello` — Health check
- `POST /api/research` — Deep research (SSE streaming)
- `POST /api/chat` — Chat with context
- `GET /api/industries` — List supported industries

## Architecture Highlights

> **Two research routes coexist by design (PRD NG-2 / NG-3 — do NOT delete either):**
> the default is **V2** (`backend/app/service/deep_research_v2/`, multi-agent workflow, selected by `version=v2`);
> the **V1 ReAct route** (`service/dr_g.py` + `react_controller.py` + `tool_executor.py`, selected by `version=v1`)
> is an intentionally retained alternative. V1 is unreachable on the daily default path — that does not make it
> dead code. The LangGraph runtime inside `deep_research_v2/graph.py` is likewise a retained parallel
> implementation (the hand-written async state machine `_run_simplified` is what actually runs today).

### Multi-Agent Deep Research System (`backend/app/service/deep_research_v2/`)
The core feature — a LangGraph-based multi-agent workflow:

1. **ChiefArchitect** — Analyzes query, generates research outline with sections
2. **DeepScout** — Parallel web search per section, collects facts
3. **DataAnalyst** — Extracts structured data points from facts
4. **CodeWizard** — Generates Python code for charts (matplotlib/seaborn → base64 images + ECharts options)
5. **LeadWriter** — Writes/synthesizes the final report
6. **CriticMaster** — Adversarial review, detects missing sources, logic errors, bias, hallucinations

The workflow uses a **hand-written async state machine** (not LangGraph at runtime) to support real-time SSE streaming — each agent's progress is pushed to an `asyncio.Queue` and yielded as SSE events. Supports **checkpoint/resume** through Postgres persistence.

### LLM Configuration
All LLM/agent model settings are centralized in `backend/app/config/llm_config.py`. Uses **DashScope** (Alibaba Cloud) by default. Each agent can use a different model — scout uses `qwen-plus` (faster/cheaper), while writer uses `deepseek-v3.2`.

### Industry Config
Pre-defined industry domains in `industry_config.py` — each has search keywords for news, bidding, and research. Currently: smart transportation, fintech, healthcare, energy.

### Infrastructure Dependencies
- **PostgreSQL** — Primary data store (chat history, users, kb, checkpoints)
- **Redis** — Caching (chat context, session state)
- **Milvus** — Vector DB for RAG on uploaded documents
- **Elasticsearch** — Full-text search (optional, for knowledge bases)
- **MinIO** — Object storage for document files

### Frontend State
Uses **Valtio** for React state management (stores: `auth.ts`, `session.ts`, `knowledge.ts`, `industry.ts`, `device.ts`). API client has a plugin system (auth injection, error toast, loading spinner, repeat-request prevention).

### Auth
JWT-based authentication with `python-jose`. Default tokens expire in 1440 minutes. Routes are protected by `<AuthGuard>` component.

### Key External API Dependencies
| API | Purpose | Required |
|-----|---------|----------|
| DashScope (Alibaba) | LLM & Embedding | **Yes** |
| Bocha Search | Web search | **Yes** |
| DocMind (Alibaba) | Document parsing | No |
| JuHe Stock | Stock market data | No |
| Bidding API | Tender info | No |
| OpenRouter | Multi-model gateway | No |
