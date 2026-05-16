# Project Overview

This project is an AI-powered outbound outreach system.

Priorities:

- Reliability and crash recovery over flashy architecture
- Local-first execution and minimal vendor dependencies
- Maintain upgrade paths (SQLite to Postgres, Tavily to SearXNG)
- Keep the backend containerized; update Docker configs alongside code changes

Tech stack:

- Python 3.12+
- FastAPI
- LangGraph
- Pydantic v2
- SQLAlchemy
- SQLite (PostgreSQL compatible)
- OpenAI API
- Crawl4AI
- ScrapeGraphAI

# Architecture Rules

This project follows node-based workflow architecture.

Each node:

- must be async
- must be pure
- receives LeadState
- returns LeadState
- must not mutate global state

Nodes live in:

nodes/

Examples:

- search.py
- crawl.py
- extract.py
- enrich.py
- validate.py
- personalize.py
- draft.py
- outreach.py

# Coding Rules

Always:

- use type hints
- use Pydantic models
- use structured JSON logs
- raise explicit exceptions
- prefer composition over inheritance
- keep functions under 50 lines where practical
- keep dependencies lean and documented
- keep nodes pure and async

Never:

- write business logic in main.py
- hardcode API keys
- use print for production logging
- create duplicate state fields
- introduce vector databases
- add new cloud services without clear justification

# Database Rules

State is relational.

Use:

- SQLAlchemy ORM

Never:

- add NoSQL databases
- add Redis unless explicitly requested

# Testing Rules

Every node should be independently testable.

When generating code:

- include docstrings
- include edge-case handling
- include retry handling for external APIs
- avoid sending real emails in tests

# Output Rules

When generating code:

- generate complete files
- do not generate pseudocode
- do not omit imports
- never include secrets or API keys in outputs