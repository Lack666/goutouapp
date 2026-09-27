# ADR 0005 — FastAPI foundation without service dependencies

Status: accepted for Phase 2A (2026-09-26).

## Context

The user requested a runnable FastAPI base before PostgreSQL and Agent Runtime
work. The server must start and test without `DATABASE_URL`, `LLM_API_KEY`,
network access or a real model. Phase 0/1 verification must continue to run,
while the full Phase 2 database gate remains pending.

## Decision

- Keep one root uv project and `uv.lock`. FastAPI, Pydantic Settings and
  Uvicorn are runtime dependencies; HTTPX, pytest and Ruff are in the uv `dev`
  group. Use the latest stable releases available on 2026-09-26 within narrow
  compatible ranges. The lock resolves FastAPI 0.141.1, Pydantic Settings
  2.15.0, Uvicorn 0.54.0, HTTPX 0.28.1, pytest 9.1.1 and Ruff 0.16.9.
- Use a `create_app` factory to allow tests to inject settings. Import-time
  app creation remains available to Uvicorn. Put the version prefix in the
  v1 router, with an unversioned liveness endpoint.
- Keep DB and LLM settings optional. Mask both with `SecretStr`; do not create
  clients or check external connections at startup. `APP_DEBUG` enables local
  logging/reload but does not expose traceback responses.
- Define one minimal `error` envelope. Do not echo invalid input, custom
  exception detail or traceback. Preserve HTTP exception headers. Do not log
  request headers, body or query strings; disable Uvicorn access logging.
- Set `completed_subphase` to `2A` while `completed_phase` remains `1` until
  the full Phase 2 gate is built. `make.cmd verify` now runs backend tests and
  lint, and explicitly defers PostgreSQL, Agent and Mobile gates.

Later phase update: ADR 0007 moved HTTPX from the development group to runtime
dependencies when the LLM adapter began using it. ADR 0008 records Phase 2D's
database shutdown lifecycle and completed composition gate.

## Consequences

Health and status prove only that the HTTP process is running. Neither implies
database or model readiness. Future phases can add service and storage
implementations without coupling Agent code to FastAPI Request/Response.
Error codes and readiness checks can grow with those features, but must keep
the privacy-safe baseline.

## Sources checked

[FastAPI releases](https://fastapi.tiangolo.com/release-notes/),
[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/),
[Pydantic Settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/),
[uv dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/),
[uv lockfile](https://docs.astral.sh/uv/concepts/projects/layout/),
[Ruff configuration](https://docs.astral.sh/ruff/configuration/), and
maintainer-published release pages for
[Uvicorn](https://pypi.org/project/uvicorn/),
[pytest](https://pypi.org/project/pytest/) and
[Ruff](https://pypi.org/project/ruff/).
