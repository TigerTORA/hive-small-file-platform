# Architecture Decision Records (ADR)

Why ADRs?
- Make important technical decisions explicit, searchable, and reviewable.
- Help future you (and teammates) understand the context and trade-offs.

When to write an ADR
- You make a non-trivial technical choice that affects behavior, safety, or cost.
- Examples: access method (WebHDFS vs native libs), default strict mode, job orchestration (Celery vs in-app), schema changes.

How to write
1) Copy `0000-template.md` to a new file `NNNN-title.md` (increment NNNN).
2) Fill in Context → Decision → Consequences; keep it short (1–2 pages).
3) Link the ADR in your PR description.

Conventions
- Folder: `docs/adr/`
- Filenames: `0001-some-decision.md`
- Status: `Proposed` → `Accepted` (or `Superseded by 00XX`)
- Keep code and docs in the same PR when possible.

Reading order
- Start from the latest ADRs (highest number) to understand current direction.

