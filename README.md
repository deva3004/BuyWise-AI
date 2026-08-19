# BuyWise-AI

An AI-powered autonomous shopping and price-intelligence agent — built to
learn RAG and agentic AI concepts hands-on, on a 15-day timeline, at ₹0
infrastructure cost.

> 🚧 **Status: Day 0 / Milestone 1 — Foundation.** Nothing is built yet.
> This README will fill in as the project progresses; see `ROADMAP.md` for
> the day-by-day plan.

## Overview

<!-- TODO: 2-3 sentence pitch once the agent actually does something.
     What does it do end-to-end? e.g. "Given a product query, BuyWise-AI
     searches multiple sources, retrieves seller/policy context via RAG,
     applies hard guardrails, and returns a BUY/WAIT/RE-EVALUATE decision
     with reasoning." -->

## Architecture

<!-- TODO: architecture diagram + one paragraph once components exist.
     Planned shape: FastAPI backend, PostgreSQL (products, offers,
     price_history, watchlists), on-demand price-fetch adapter layer,
     ChromaDB for RAG, LangGraph agent with a guardrail layer enforced
     before the LLM decision step, Streamlit frontend. -->

## Tech Stack

- **Backend:** FastAPI
- **Database:** PostgreSQL
- **Vector store:** ChromaDB
- **Embeddings:** HuggingFace (local)
- **Agent framework:** Manual tool-calling → LangGraph
- **LLM:** Groq (free tier)
- **Frontend:** Streamlit
- **Infra:** Docker, GitHub Actions

## Setup

### Option A — Docker (recommended, closest to how this would actually deploy)

Prerequisites: Docker + Docker Compose.

```bash
cp .env.example .env   # fill in GROQ_API_KEY at minimum
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

### Option B — Local dev (no Docker)

Prerequisites: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), a
running Postgres instance.

```bash
cp .env.example .env       # set DATABASE_URL to your local Postgres, add GROQ_API_KEY
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

## Roadmap

See [`ROADMAP.md`](./ROADMAP.md) for the full 15-day phase breakdown
(Foundation → RAG → Agent → Evaluation & Observability → Frontend/Ship).

## Challenges & Solutions

<!-- TODO: pull the best entries from PROBLEMS_FACED.md here at the end,
     rewritten for a reader (not raw scrollback) — real bugs, wrong
     assumptions walked back, free-tier limitations worked around. -->

## Future Work

Deliberately cut from the 15-day resume scope (see `ROADMAP.md` for why):

- Graph RAG (Neo4j)
- Multimodal / image RAG
- Redis caching
- Full LLM gateway abstraction
- Background worker / job queue / scheduler (always-on price monitoring)
- Multi-agent supervisor architecture
- Full production eval suite

## License

<!-- TODO -->
