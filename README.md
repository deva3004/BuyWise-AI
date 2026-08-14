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

<!-- TODO: fill in once there's something runnable (Day 1+):
     - prerequisites
     - env vars / .env.example
     - install steps
     - how to run locally (docker compose up)
     - how to run tests -->

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
