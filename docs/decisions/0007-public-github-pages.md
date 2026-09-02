# 0007. Publish on GitHub Pages (Public Repo)

- **Status**: Accepted
- **Date**: 2026-09-02
- **Deciders**: project author

## Context

The "Simulation" feature (see `docs/plans/simulation_tab.md`) is a 100% client-side
payoff simulator: no yfinance, no SQLite, no matplotlib. That makes it deployable
as a standalone static site on **GitHub Pages** so it can be opened from any device
to input parameters and read expiry-payoff results without running the Flask server.

The existing `README.md` states *"Internal / unpublished. All rights reserved by the
project owner."*, which conflicts with a free GitHub Pages deployment — **GitHub Pages
requires the publishing repository to be public** (private-repo Pages is a paid feature).

This ADR records the decision to open the repository and publish the simulator.

## Options Considered

1. **Keep the repo private; publish a separate public mirror repo** (`optionlab-sim`)
   that holds only the simulator files. Safest for the rest of the codebase, but adds
   a sync step and splits the project in two.
2. **Make the whole repository public and serve Pages from it** (default `docs/` or a
   `site/` branch/dir). Simplest, no mirror; exposes the full codebase (acceptable for
   a research tool, but exposes `market_data.sqlite`).
3. **Keep private + pay for GitHub Pro** to get private Pages. Avoids exposure but adds
   recurring cost for a personal research tool.

## Decision

Adopt **Option 2** — the repository becomes **public** and the simulator is published
via GitHub Pages. Concretely:

- License changed from *Internal / unpublished* to **MIT** (see `README.md`).
- GitHub Pages is published from a dedicated `site/` directory built by a CI workflow
  (`gh-pages` branch), not from the repo root, so Flask/`core`/`core` internals are not
  the served artifact.
- **Prerequisite (BLOCKING)**: `market_data.sqlite` is currently tracked in git
  (≈10 MB, committed in 5+ historical commits) and contains local price/regime data.
  It MUST be removed from the working tree and from git history before the repo is made
  public. Recommended non-destructive route: create the public presence from a fresh
  tree that excludes the DB (and any `.env`), rather than force-pushing a rewritten
  history of the private repo. If history rewrite is chosen instead, use
  `git-filter-repo`/BFG and force-push only after explicit sign-off.

## Consequences

- **Positive**: anyone can open the simulator URL; zero server needed for that feature.
- **Positive**: no paid plan, no mirror repo to keep in sync.
- **Trade-off**: the full source (including yfinance/strategy code) is public. Acceptable
  for a research tool, but contributors must not commit the local `market_data.sqlite`
  (it stays git-ignored after this change).
- **Risk**: a public simulator implies a public API if the in-app Flask tab is opened
  from the Pages origin pointing back at a host — mitigated by keeping the simulator
  self-contained (no `fetch`); see `docs/constraints.md` §7 and the plan doc.
- **Trade-off**: MIT license means the code can be reused, but the financial math carries
  no warranty (standard MIT disclaimer applies).
