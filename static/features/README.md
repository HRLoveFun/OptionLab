# static/features/

> L2 | 权威：该目录的迁移目标（尚未落地） | 不权威：当前进展（见 STATUS.md）

Reserved for feature-level orchestration scripts, refactored from the
top-level files (option-chain.js, market_review.js, etc.).

Migration plan: as state and DOM concerns are extracted, feature
scripts will move here and import state from `static/state/` and
shared UI atoms from `static/components/`.
