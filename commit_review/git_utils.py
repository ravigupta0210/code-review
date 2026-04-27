"""Thin wrappers around git commands used by the reviewer."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(args: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise GitError("git is not installed or not on PATH") from e
    except subprocess.CalledProcessError as e:
        raise GitError(f"git {' '.join(args)} failed: {e.stderr.strip()}") from e
    return result.stdout


def current_branch(cwd: Path | None = None) -> str:
    return _run(["branch", "--show-current"], cwd).strip()


def repo_root(cwd: Path | None = None) -> Path:
    return Path(_run(["rev-parse", "--show-toplevel"], cwd).strip())


def staged_files(cwd: Path | None = None) -> list[str]:
    out = _run(["diff", "--cached", "--name-only"], cwd).strip()
    return [line for line in out.splitlines() if line]


def staged_diffstat(cwd: Path | None = None) -> str:
    return _run(["diff", "--cached", "--stat"], cwd)


def staged_diff(cwd: Path | None = None, context_lines: int = 3) -> str:
    return _run(["diff", "--cached", f"-U{context_lines}"], cwd)


def recent_log(n: int = 10, cwd: Path | None = None) -> str:
    return _run(["log", f"-n{n}", "--oneline"], cwd)


@dataclass
class PushPlan:
    local_branch: str
    remote: str
    remote_branch: str
    commits: str
    diffstat: str


def push_plan(cwd: Path | None = None, remote: str = "origin") -> PushPlan:
    branch = current_branch(cwd)
    try:
        commits = _run(["log", f"{remote}/{branch}..HEAD", "--oneline"], cwd)
        diffstat = _run(["diff", "--stat", f"{remote}/{branch}..HEAD"], cwd)
    except GitError:
        commits = _run(["log", "-n10", "--oneline"], cwd)
        diffstat = "(no upstream set — showing local-only context)"
    return PushPlan(
        local_branch=branch,
        remote=remote,
        remote_branch=branch,
        commits=commits,
        diffstat=diffstat,
    )


SUSPICIOUS_PATTERNS = (
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_dsa",
    "credentials.json",
    "service-account.json",
    ".pem",
    ".key",
)


def flag_suspicious_files(files: list[str]) -> list[str]:
    hits: list[str] = []
    for f in files:
        lower = f.lower()
        if any(p in lower for p in SUSPICIOUS_PATTERNS):
            hits.append(f)
    return hits
