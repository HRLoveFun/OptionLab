# Pull Request

## Summary

<!-- One paragraph: what changes user-visible behaviour or developer
ergonomics. Skip the diff narrative; reviewers will read the diff. -->

## Documentation impact

Tick all that apply, then update the corresponding artefact **in this PR**:

- [ ] No documentation impact.
- [ ] New/changed **constraint** → updated [`docs/constraints.md`](../docs/constraints.md)
- [ ] New/changed **architecture decision** → added an ADR under [`docs/decisions/`](../docs/decisions/)
- [ ] New domain term → added to [`docs/glossary.md`](../docs/glossary.md)
- [ ] New non-obvious code → added a `WHY:` / `CONSTRAINT:` / `TRADEOFF:` / `INVARIANT:` / `DOMAIN:` comment
- [ ] Changed code referenced by an existing ADR → updated that ADR's status / consequences

## Verification

- [ ] `pytest -x --tb=short` passes locally
- [ ] `python scripts/doc_guard.py` is clean (or new failures suppressed with documented `# doc-guard: allow=...`)
- [ ] `python scripts/audit_tags.py` reports no regression

## Notes for reviewers

<!-- Optional: tricky bits, alternatives considered, follow-up work. -->
