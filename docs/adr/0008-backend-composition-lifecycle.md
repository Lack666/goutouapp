# ADR 0008: Phase 2 composition and resource ownership

Status: accepted for Phase 2D (2026-09-27).

## Decision

- Keep the three existing boundaries. FastAPI assembles transport and owns the
  lazy `Database` holder; repositories and services accept a SQLAlchemy
  `Session`; LLM consumers accept the typed `LLMProvider` created from Settings.
  No general dependency container is needed for the current foundation.
- FastAPI lifespan disposes its database pool on shutdown. Request sessions
  continue to commit, roll back and close through `get_db` in
  `app/api/dependencies.py`; the persistence module itself does not import
  FastAPI. Non-HTTP callers explicitly own their Session transaction. The
  compatible LLM adapter closes its default HTTPX client after each operation;
  an injected client belongs to the injecting caller.
- Keep `/health` as liveness and `/ready` as a PostgreSQL-only probe. Startup
  does not connect to PostgreSQL or an LLM. The LLM factory is called only by
  an explicit consumer.
- Run five infrastructure smoke scenarios in the backend gate: online and
  offline PostgreSQL, keyless Mock operations, compatible fake transport, and
  a transaction combining a Mock response with existing message persistence.
  Keep `TEST_DATABASE_URL` solely in the isolated test harness. Add
  `alembic check` after the reversible migration cycle.

## Consequences

Future Agent Runtime code can receive Settings, repositories/services or a
scoped Session, and an LLMProvider by ordinary Python injection. This decision
does not create an Agent, transport endpoint or new persistence model. The
integration tests require the existing disposable PostgreSQL test namespace;
all model calls remain offline.
