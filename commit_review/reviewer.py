"""Core review engine. Encodes the 8-step SKILL.md checklist as a system prompt
and parses the LLM's JSON response into structured findings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal

from .providers import Provider, ProviderError


Severity = Literal["blocker", "warning", "nit"]

STEP_NAMES = {
    1: "Manifest",
    2: "Build",
    3: "Null-safety",
    4: "Imports",
    5: "Name-collision",
    6: "Logic",
    7: "Naming",
    8: "Better-pattern",
}


@dataclass
class Finding:
    step: int
    file: str
    line: int | None
    severity: Severity
    message: str

    @property
    def step_name(self) -> str:
        return STEP_NAMES.get(self.step, f"Step {self.step}")


@dataclass
class ReviewResult:
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    raw: str = ""

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def has_blockers(self) -> bool:
        return bool(self.blockers)

    def by_step(self) -> dict[int, list[Finding]]:
        buckets: dict[int, list[Finding]] = {}
        for f in self.findings:
            buckets.setdefault(f.step, []).append(f)
        return buckets


SYSTEM_PROMPT = """You are commit-review, an AI pre-commit quality gate.

You review a staged git diff and report findings. You are **read-only** — you
never propose a rewrite or refactor unless asked. You find issues, name them
clearly, and let the developer decide.

Run this 8-step checklist on the diff. For each finding, emit a JSON object.

1. Manifest — flag unexpected files: secrets (.env*, *.pem, *.key, credentials),
   lockfiles the diff didn't justify, files outside the apparent scope.
2. Build — skipped (runner handles this locally); do not emit findings here.
3. Null-safety — values from API responses, props, route params, storage, or
   external input that aren't guarded against null/undefined/empty.
4. Imports — unused imports, wrong paths, symbols not exported from that path.
5. Name-collision — new top-level identifiers that shadow existing ones with
   different semantics (you can only flag what's visible in the diff).
6. Logic — off-by-one, inverted booleans, missing await, unreachable branches,
   races, infinite loops, swallowed catch blocks, console.log/print left in,
   hardcoded secrets/URLs, obvious O(n^2) where O(n) fits.
7. Naming — unclear identifiers, casing that breaks the file's convention.
8. Better-pattern — a clearly more idiomatic pattern (Promise.all for
   independent awaits, early return, named constants). Only when clearly better.

Severity guide:
- blocker: will break prod, leak data, or is wrong. Must fix before commit.
- warning: likely bug or real concern. Should fix.
- nit: style/polish. Take or leave.

## Output format (strict)

Respond with a single JSON object, no prose outside it:

{
  "summary": "one-sentence overall read",
  "findings": [
    {
      "step": 3,
      "file": "src/foo.ts",
      "line": 42,
      "severity": "blocker",
      "message": "user.profile accessed without null check; API can return user without profile"
    }
  ]
}

If the diff is clean, return {"summary": "...", "findings": []}.

Rules:
- Do not suggest rewrites in `message` — describe the concern only.
- Be concrete: file path + line + what you saw.
- No false alarms: if unsure, omit. Quality > quantity.
- If a step has nothing to report, emit no findings for that step.
"""


def _build_user_prompt(
    branch: str,
    staged_files: list[str],
    diffstat: str,
    diff: str,
    suspicious: list[str],
) -> str:
    parts = [
        f"Branch: {branch}",
        "",
        "Files staged:",
        *(f"  - {f}" for f in staged_files),
        "",
        "Diffstat:",
        diffstat.rstrip(),
    ]
    if suspicious:
        parts.extend(
            ["", "⚠ Potentially sensitive files detected:"]
            + [f"  - {f}" for f in suspicious]
        )
    parts.extend(["", "--- STAGED DIFF ---", diff])
    return "\n".join(parts)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_response(text: str) -> tuple[str, list[Finding]]:
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return "(could not parse model response)", []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "(model returned invalid JSON)", []
    summary = str(data.get("summary") or "").strip()
    findings: list[Finding] = []
    for item in data.get("findings", []) or []:
        try:
            findings.append(
                Finding(
                    step=int(item.get("step", 0)),
                    file=str(item.get("file") or "?"),
                    line=item.get("line") if isinstance(item.get("line"), int) else None,
                    severity=item.get("severity", "warning"),
                    message=str(item.get("message") or "").strip(),
                )
            )
        except (ValueError, TypeError):
            continue
    return summary, findings


def review_diff(
    provider: Provider,
    *,
    branch: str,
    staged_files: list[str],
    diffstat: str,
    diff: str,
    suspicious: list[str],
) -> ReviewResult:
    if not diff.strip():
        return ReviewResult(summary="no staged changes", findings=[])
    user = _build_user_prompt(branch, staged_files, diffstat, diff, suspicious)
    try:
        raw = provider.chat(SYSTEM_PROMPT, user)
    except ProviderError:
        raise
    summary, findings = _parse_response(raw)
    return ReviewResult(findings=findings, summary=summary, raw=raw)
