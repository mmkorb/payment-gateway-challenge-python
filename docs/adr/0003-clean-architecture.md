# 0003. Clean Architecture, pragmatic (three rings)
- Status: accepted (user decision 2026-10-22)

## Context
The Brief asks for simple, maintainable code without over-engineering (NFR-05). The gateway has two use cases, one bank and one store. Simple hexagonal (ports and adapters) and Clean Architecture were compared; both point dependencies inward and differ mostly in vocabulary and ring count.

## Decision
Clean Architecture with three rings in the starter's package `payment_gateway_api/`: `domain` (entities and rules), `application` (use cases and the interfaces they need, as `typing.Protocol`), `infrastructure` (`api`, `bank`, `persistence`). `main.py` wires everything. Business rules are domain functions; the Pydantic validators in `infrastructure/api` call them (ADR 0002). Layout and import rules: [architecture.md](../design/architecture.md).

Why: the vocabulary (entities, use cases, interfaces) is familiar to reviewers from C#/.NET; the core is testable without FastAPI, Pydantic or httpx; the bank and the store can be replaced without touching the core.

Alternatives rejected:
- Strict Clean Architecture with four rings (separate interface adapters, presenters, per-use-case input/output models): more classes and mapping for two endpoints.
- Hexagonal vocabulary: same structure; Clean names chosen for the reviewer.
- No layering (everything in the route): fastest to write, but business rules would depend on FastAPI and be harder to test.

## Consequences
- Each external dependency has one interface in `application/` and one adapter in `infrastructure/`.
- Some mapping by hand between the Pydantic models and the domain `Payment`.
