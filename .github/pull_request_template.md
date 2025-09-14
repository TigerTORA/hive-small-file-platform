## Summary
- What problem does this PR solve? Why now?

## Changes
- Key changes (bullet points)
- Any schema or config changes? (Alembic migration? .env?)

## Risk / Impact
- User-facing changes? Backward compatibility?
- Performance or operational impacts?

## Testing & Verification
- Commands run locally (copy/paste):
  - `make ci-test`
  - Backend: `cd backend && python -m pytest -v`
  - Frontend: `cd frontend && npm run test:run`
- Screenshots / logs (if applicable)

## Rollout & Rollback
- Rollout steps (env vars, migrations, toggles)
- Rollback steps (how to revert safely)

Auto-merge
- If safe to auto-merge once CI is green, add label `automerge` to this PR.

## Documentation
- ADRs updated/added? Link:
- README/Runbooks updated?

## Checklist
- [ ] Small, focused PR (or linked follow-ups)
- [ ] Tests pass locally and in CI
- [ ] Docs updated (README/ADR/Runbook)
- [ ] Safe to roll back with clear steps
