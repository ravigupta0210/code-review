"""Project-type detection and build/lint/type-check runners."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildResult:
    name: str
    command: str
    ok: bool
    output: str


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 600) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def _node_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _node_scripts(root: Path) -> dict:
    pkg = root / "package.json"
    if not pkg.exists():
        return {}
    try:
        data = json.loads(pkg.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("scripts", {}) or {}


def detect_and_run(root: Path, skip: bool = False) -> list[BuildResult]:
    """Detect project type and run build/type-check/lint. Returns results in order."""
    if skip:
        return []

    results: list[BuildResult] = []

    if (root / "package.json").exists():
        pm = _node_manager(root)
        scripts = _node_scripts(root)
        runner = shutil.which(pm) or pm
        for script in ("build", "type-check", "typecheck", "lint"):
            if script in scripts:
                cmd = [runner, "run", script] if pm == "npm" else [runner, script]
                ok, out = _run_cmd(cmd, root)
                results.append(
                    BuildResult(name=script, command=" ".join(cmd), ok=ok, output=out)
                )

    elif (root / "go.mod").exists():
        ok, out = _run_cmd(["go", "build", "./..."], root)
        results.append(BuildResult("go build", "go build ./...", ok, out))

    elif (root / "Cargo.toml").exists():
        ok, out = _run_cmd(["cargo", "build"], root)
        results.append(BuildResult("cargo build", "cargo build", ok, out))

    elif (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        ok, out = _run_cmd(["python", "-m", "compileall", "-q", "."], root)
        results.append(
            BuildResult("py compileall", "python -m compileall -q .", ok, out)
        )

    return results
