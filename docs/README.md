---
description: Index of the project documentation by SDLC phase, with status and when to read.
last_verified: 2026-10-22 (9ffcd48)
---

# Documentation

| Phase | Document | Status | Read before |
|---|---|---|---|
| Requirements | [functional.md](requirements/functional.md) | accepted | changing behaviour or validation |
| Requirements | [non-functional.md](requirements/non-functional.md) | accepted | changing security, tooling, error handling |
| Requirements | [assumptions.md](requirements/assumptions.md) | accepted | resolving an open question |
| Design | [architecture.md](design/architecture.md) | accepted | creating or moving packages |
| Design | [api.md](design/api.md) | accepted | changing the HTTP contract |
| Decisions | [adr/](adr/) | 6 accepted (0001 REST, 0002 FastAPI + Pydantic + httpx, 0003 Clean Architecture, 0004 idempotency, 0005 single bank call, 0006 in-memory repository) | revisiting a decision |
| Testing | [test-plan.md](testing/test-plan.md) | accepted | adding tests |
| Review | [review.md](review.md) | accepted | planning production work |
