#!/usr/bin/env python3
"""Stub for the LLM-driven drafter.

Reads the candidate list from argv[1] and (when an API key is configured)
asks an LLM to generate concrete patches. Writes patches to disk so the
parent workflow can commit them.

Why a stub? We deliberately keep the LLM glue thin so it can be swapped:
  - Anthropic Claude via /v1/messages
  - OpenAI GPT-4 via /v1/chat/completions
  - `gh copilot suggest`
  - Local model

For now, the stub:
  - validates input
  - if no API key is set, exits 0 with a friendly message (the workflow
    falls back to opening an issue so visibility is preserved)
  - if a key is set, prints what it WOULD send (one prompt per candidate)
    and returns 0 — replace the `_call_llm` body with your provider
    of choice when ready.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


PROMPT_TEMPLATES = {
    "untagged-constant": textwrap.dedent(
        """
        File: {file} (line {line})
        Constant: {name} = {value}

        Task: write a one-to-three-line comment using the project's tag vocabulary
        (WHY / CONSTRAINT / TRADEOFF / INVARIANT / DOMAIN) explaining why this
        constant has the value it has. Reference docs/constraints.md or an ADR
        when applicable. Output ONLY the comment lines, no preamble.
        """
    ),
    "missing-module-docstring": textwrap.dedent(
        """
        File: {file}

        Task: write a 4-8 line module docstring with a 'Context:' block describing
        what this module does, what depends on it, and any non-obvious constraint.
        Output ONLY the docstring (triple-quoted), no preamble.
        """
    ),
    "terse-test-name": textwrap.dedent(
        """
        File: {file} (line {line})
        Current test name: {name}

        Task: read the test body (you'll be given context separately) and propose
        a clearer name in the form ``test_<subject>_<behaviour>``. Output ONLY
        the new name, no preamble.
        """
    ),
}


def _call_llm(_prompt: str) -> str | None:
    """Replace this with your provider integration when wiring up real drafts."""
    return None  # not implemented; workflow falls back to issue


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: draft_doc_updates.py <candidates.json>", file=sys.stderr)
        return 2
    candidates = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not candidates:
        print("no candidates")
        return 0
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        print(f"no LLM key configured; {len(candidates)} candidates would be drafted.")
        return 0
    cap = int(os.environ.get("MAX_DRAFT_CHANGES", "5"))
    for c in candidates[:cap]:
        tmpl = PROMPT_TEMPLATES.get(c.get("kind"))
        if not tmpl:
            continue
        prompt = tmpl.format(**c)
        suggestion = _call_llm(prompt)
        if suggestion is None:
            continue
        # TODO: apply suggestion as a patch — left as an exercise for whoever
        # plugs in their preferred LLM. The shape is a unified diff written to
        # the working tree so peter-evans/create-pull-request picks it up.
    return 0


if __name__ == "__main__":
    sys.exit(main())
