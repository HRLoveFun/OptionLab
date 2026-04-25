# static/features/

Reserved for feature-level orchestration scripts, refactored from the
top-level files (option-chain.js, game.js, market-review.js, etc.).

Migration plan: as state and DOM concerns are extracted, feature
scripts will move here and import state from `static/state/` and
shared UI atoms from `static/components/`.
