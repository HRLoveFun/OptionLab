# Automation: Keeping AI-Context Artefacts Fresh

> **Goal**: Keep the comment tags, docstrings, project docs, ADRs, glossary,
> and commit conventions accurate as the codebase iterates — with the
> minimum possible human babysitting.

## Honest framing

True "zero human intervention" is impossible for **semantic** artefacts (an ADR
captures a *judgement*; a glossary entry expresses *intent*). What we can do:

1. **Deterministic guards (L1)** — block obviously-wrong states automatically. *Truly* zero-touch.
2. **Derived artefacts (L3)** — regenerate things that are mechanical functions of source. Truly zero-touch.
3. **AI-drafted updates (L2)** — when the *first draft* is what costs effort, automate the draft and ask a human to click "merge". Near-zero-touch.

The system below is a layered defense. Each layer fails open to the next.

---

## L1 — Deterministic guardians (zero human touch)

Implemented in [`scripts/doc_guard.py`](../scripts/doc_guard.py). Run by:
- pre-commit hook (fast subset)
- CI on every PR via `.github/workflows/doc-guard.yml` (full set)

What it checks (each rule produces a non-zero exit code on violation):

| Rule                     | What it catches                                                                                                                    | Why                                                                           |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `tag-syntax`             | `WHY:`/`CONSTRAINT:`/etc. used outside the canonical vocabulary, or with malformed forms (lowercase, missing colon).               | Keeps the tag set stable so AI grep is reliable.                              |
| `yfinance-throttle`      | Any new `yf.download` / `yf.Ticker(...)` call site not preceded by `yf_throttle()` or routed through `data_pipeline/yf_client.py`. | Hard architectural invariant from ADR 0005.                                   |
| `yfinance-session-kwarg` | Any call passing `session=` to a yfinance API.                                                                                     | Silent failure mode (curl_cffi). See `docs/constraints.md` §2.                |
| `sqlite-bypass`          | New `sqlite3.connect(` outside `data_pipeline/db.py`.                                                                              | Bypasses WAL pragmas (ADR 0003).                                              |
| `import-direction`       | Imports from `services/` inside `core/` or `data_pipeline/`; from `core/` inside `data_pipeline/`.                                 | ADR 0001 — already enforced by an existing hook; doc-guard is the safety net. |
| `adr-link-integrity`     | Markdown links from `docs/decisions/` / `docs/constraints.md` / `docs/glossary.md` that point at non-existent files or anchors.    | ADRs must stay reachable.                                                     |
| `adr-index-fresh`        | `docs/decisions/README.md` index does not match the actual ADR files in the folder.                                                | Auto-fixable; CI fails if not regenerated.                                    |
| `module-docstring`       | Modules in `core/` or `data_pipeline/` missing a top-level docstring.                                                              | Keeps the "Context:" docstring habit alive.                                   |
| `tagged-code-stale`      | A `# CONSTRAINT: see docs/...` reference points at a file/section that no longer exists.                                           | Prevents tag rot.                                                             |
| `commit-msg`             | Commit subjects without a `<type>:` prefix or with type outside the allowed set.                                                   | Run as a `commit-msg` git hook locally.                                       |

### Failure modes
- Pre-commit blocks the commit. Fix locally, retry.
- CI fails the PR check. Fix in branch, push.
- Both report the offending file and line — no manual searching.

---

## L3 — Derived artefacts (zero human touch)

These regenerate from the source of truth, so they cannot drift if the script runs.

| Artefact                                       | Source of truth                                  | Regenerator                                                           |
| ---------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------- |
| `docs/decisions/README.md` index table         | ADR file frontmatter (`Status:` line + first H1) | [`scripts/regen_adr_index.py`](../scripts/regen_adr_index.py)         |
| `.github/data/tag_baseline.json`               | grep over codebase for canonical tags            | [`scripts/audit_tags.py --update-baseline`](../scripts/audit_tags.py) |
| Glossary cross-link block in module docstrings | `docs/glossary.md` headings                      | (future) `scripts/regen_glossary_links.py`                            |

These are wired into `pre-commit` with `language: system` and the script
auto-stages its output. If the regenerated content differs from the committed
version, the commit fails and the user just commits again with the regenerated
files staged — *no thinking required*.

---

## L2 — AI-drafted updates (human merges, no writing)

Triggered by `.github/workflows/doc-drift.yml` (scheduled weekly + manual dispatch).

For each rule below, the workflow uses the **GitHub CLI + Copilot Workspace
Action** (or `gh copilot suggest` / Claude API) to draft a PR. The PR is
labelled `doc-drift` so it can be filtered. A human just reviews and merges.

| Trigger                                                                                                                           | Drafted change                                                                 | Reviewer effort                    |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------- |
| Diff in `core/` introduces a new constant whose name matches `^[A-Z_]+$` and value isn't 0/1/None, with no `DOMAIN:` tag above it | A PR adds a `DOMAIN:` comment proposing rationale, plus a glossary entry stub. | Approve / tweak wording.           |
| Diff modifies code referenced by an ADR ("Related code:" line)                                                                    | A PR adds a "Status: needs review" banner to that ADR.                         | Decide: still accurate? supersede? |
| New file added to `core/` without module docstring                                                                                | A PR generates a `Context:` docstring from `git log` of the file's history.    | Sanity check.                      |
| Test file's tests have non-descriptive names (e.g. `test_foo`, `test_1`)                                                          | A PR proposes renamed tests using the body of each test.                       | Approve renames.                   |
| `docs/glossary.md` is missing a term that appears 5+ times in code                                                                | A PR appends a stub entry.                                                     | Fill in description.               |

The workflow is **idempotent**: if its previous PR is still open, it amends
that PR rather than spamming new ones.

### LLM call surface
The workflow shells out to a single script `scripts/draft_doc_updates.py`
which:
1. Computes the candidate change set deterministically (so the LLM gets
   small, focused inputs — not the whole repo).
2. Calls the configured LLM endpoint (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` /
   `gh copilot`) once per candidate.
3. Writes patches and lets the workflow commit + open the PR.

> **Cost guard**: the workflow caps the number of LLM calls per run via
> `MAX_DRAFT_CHANGES` (default 5). A separate weekly run handles backlog.

---

## Commit conventions (semi-automated)

A `commit-msg` git hook validates the subject prefix
(`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `revert:`).
The template at [`.gitmessage`](../.gitmessage) is set as
`commit.template` so `git commit` opens with the structure pre-filled —
authors fill in two fields rather than writing prose.

---

## Tag audits (regression-tracked)

`scripts/audit_tags.py` produces a JSON report of:
- count of each tag type across the repo,
- modules without docstrings,
- candidate magic numbers in `core/` / `data_pipeline/` not yet tagged.

CI compares the new report against `.github/data/tag_baseline.json` and
fails if the *uncovered* count grows. New code is therefore forced to
either tag its constants or update the baseline (a human gesture, but a
trivial one).

This converts an open-ended audit into a **monotone** check: tag coverage
can only stay flat or improve.

---

## Self-test

A small fixture in `tests/test_doc_guard_self.py` (added to the regular
pytest run) plants a violation in a temp dir and asserts that
`doc_guard.py` exits non-zero with the right rule ID. This guarantees the
guards themselves don't silently rot when refactored.

---

## What is *not* automated (and why)

- **Writing new ADRs.** A human must decide that a decision is significant
  enough to record. No heuristic captures this reliably.
- **Deciding whether a constraint has expired.** Removing items from
  `docs/constraints.md` requires judgement (e.g. "is yfinance still our
  only data source?"). The L2 workflow can flag candidates but won't act.
- **Translating Chinese-language UI strings.** Out of scope.

These items are listed to set expectations: anyone reading this doc should
not expect documentation to "write itself." They should expect the
mechanical parts to never go stale and the judgemental parts to be
queued up as approvable PRs.

---

## Local quick reference

```bash
# Run all L1 checks locally:
python scripts/doc_guard.py

# Re-generate derived artefacts (ADR index etc.) and stage them:
python scripts/regen_adr_index.py

# Update the tag baseline after intentionally accepting more uncovered code:
python scripts/audit_tags.py --update-baseline

# One-shot install of all hooks:
pre-commit install --hook-type pre-commit --hook-type commit-msg
```
