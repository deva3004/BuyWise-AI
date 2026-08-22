# BuyWise-AI

An AI-powered autonomous shopping and price-intelligence agent, built at
₹0 infrastructure cost.

> **Status:** Core product is functional end-to-end — search, RAG over
> seller policies, guardrailed agent decisions, authentication, and the
> Streamlit frontend all work. Scaling features (rate limiting, caching,
> a background worker, horizontal scaling behind a load balancer) are
> designed but not yet implemented.

## Overview

Given a product query, BuyWise-AI searches for offers across sellers,
retrieves relevant seller policy context via RAG, applies hard guardrail
rules in code, and has an LLM agent produce a BUY / WAIT / RE-EVALUATE
decision with reasoning — personalized per signed-in user, drawing on
their own watchlist rather than a manually typed ID. A Streamlit frontend
talks to a FastAPI backend over JWT-authenticated requests; PostgreSQL is
the system of record, with ChromaDB as a rebuildable vector index over
seller policies.

## Architecture

- **PostgreSQL** — `users`, `products` → `product_variants` → `offers`
  (current state, one row per variant+seller) → `price_history`
  (append-only), `sellers`, `seller_policies`, `watchlists`. Managed via
  SQLAlchemy models + Alembic migrations.
- **FastAPI** — routes split by domain under `app/routers/`: `auth`
  (signup/login, issues JWTs), `watchlist`, `catalog` (search + product/
  offer/variant lookups), `policies` (seller-policy ingest + RAG search),
  `agent` (the decision endpoint). A shared `get_db` session dependency
  lives in `app/dependencies.py`; a global exception handler in `main.py`
  turns any unhandled error into a consistent JSON 500 instead of a raw
  traceback.
- **Auth** — JWT (HS256), not server-side sessions, chosen so a future
  multi-instance deployment needs no shared session store: a signature
  check is self-contained, while a session lookup would require every
  instance to hit the same store. The accepted trade-off is that a token
  can't be revoked before it expires. Passwords hashed with bcrypt.
  `watchlists.user_id` and the agent's "my watchlist" tool both derive the
  user from the verified token, never from client input.
- **RAG** — seller policies live in Postgres as the source of truth;
  `app/rag.py` embeds them (local HuggingFace `SentenceTransformer`) into
  ChromaDB, filterable by `seller_id`, and the index is fully rebuildable
  from Postgres.
- **Agent** — manual tool-calling loop (`app/agent.py` + `app/tools.py`)
  against Groq's `chat.completions` API, with an explicit tool allowlist
  and per-tool Pydantic argument validation. Hard guardrail rules (e.g.
  minimum seller rating) run in code *before* the LLM sees the decision —
  deliberately not left to the prompt alone. Each run logs a structured
  JSON trace (tool calls, decision, reasoning) for observability.
- **Frontend** — Streamlit (`streamlit_app.py`), JWT held in
  `st.session_state` and sent as `Authorization: Bearer <token>` on
  protected calls.

## Tech Stack

- **Backend:** FastAPI
- **Database:** PostgreSQL (SQLAlchemy + Alembic)
- **Vector store:** ChromaDB
- **Embeddings:** HuggingFace (local)
- **Agent:** Manual tool-calling over Groq (free tier)
- **Auth:** JWT (PyJWT) + bcrypt
- **Frontend:** Streamlit
- **Infra:** Docker, GitHub Actions (planned)

## Setup

### Option A — Docker (recommended, closest to how this would actually deploy)

Prerequisites: Docker + Docker Compose.

```bash
cp .env.example .env   # fill in GROQ_API_KEY and JWT_SECRET_KEY at minimum
docker compose up --build
```

This starts three containers: Postgres (with a persistent volume),
the FastAPI backend (`uvicorn`, migrations applied automatically on
startup), and the Streamlit frontend. Once it's up:

- Frontend: http://localhost:8501
- API: http://localhost:8000 (docs at http://localhost:8000/docs)

The database starts empty. To populate it with a mock catalog (products,
sellers, offers, seller policies) so the frontend has something to
browse:

```bash
docker compose exec api python -m db.seed_mock_data
```

From the frontend, sign up for an account from the sidebar before using
the Watchlist or Ask the Agent pages — both require an authenticated
session.

### Option B — Local dev (no Docker)

Prerequisites: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), a
running Postgres instance.

```bash
cp .env.example .env       # set DATABASE_URL, GROQ_API_KEY, JWT_SECRET_KEY
uv sync
uv run alembic upgrade head
uv run python -m db.seed_mock_data   # optional: mock catalog data

uv run uvicorn main:app --reload          # terminal 1 — API on :8000
uv run streamlit run streamlit_app.py     # terminal 2 — frontend on :8501
```

### Tests / eval

```bash
uv run python -m eval.run_eval
```

Runs a small fixed set of agent decision scenarios (guardrail-eligible
and guardrail-blocked) against a live backend + Groq and reports
pass/fail — see `PROJECT_STATE.md` for what it currently covers.

## Challenges & Solutions

**Migration drift silently masquerading as an application bug.**
Debugging a mock-data seed script that appeared to insert nothing turned
into two stacked issues: a safety guard in the seed script was silently
no-op'ing against unrelated leftover dev data, and — once that was
cleared — the database turned out to be one Alembic migration behind the
repo, so a table the code assumed existed simply wasn't there yet. The
practical lesson: when a query "should" return data and doesn't, check
what's actually in the database directly before debugging the query
logic, and don't assume a migration file existing in the repo means it's
been applied to every environment — `alembic current` vs `alembic heads`
answers that in seconds.

**"Docker is running" isn't the same fact as "my container is running."**
An `alembic revision --autogenerate` command failed with a Postgres
connection refused error, which looked like a networking or config
problem. It turned out the specific Postgres container had exited and
just hadn't been restarted — Docker Desktop being open says nothing about
any individual container's state. `docker ps -a` before assuming a
code-level cause became the standing first move for any DB-connection
error.

## Future Work

**Next up:**

- Verify the Docker Compose setup end-to-end (written, not yet run)
- CI pipeline (GitHub Actions) for linting and tests on push
- Rate limiting on the API
- Redis caching layer

**Longer-term / deferred:**

- Background worker / job queue / scheduler for always-on price monitoring
- Load balancer + multiple API instances
- Graph RAG (Neo4j)
- Multimodal / image RAG
- Full LLM gateway abstraction
- Multi-agent supervisor architecture
- Full production eval suite

## License

<!-- TODO -->
