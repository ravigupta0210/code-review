"""commit-review CLI.

Commands:
  commit-review review       Review staged changes and print findings. (read-only)
  commit-review commit -m    Review, then commit if no blockers.
  commit-review push         Show push plan and push after confirmation.
  commit-review install-hook Install a git pre-commit hook that runs review.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from . import __version__
from .build_check import detect_and_run
from .config import Config
from .git_utils import (
    GitError,
    current_branch,
    flag_suspicious_files,
    push_plan,
    repo_root,
    staged_diff,
    staged_diffstat,
    staged_files,
)
from .output import (
    console,
    print_build_results,
    print_findings,
    print_manifest,
    print_push_plan,
)
from .providers import ProviderError, build_provider
from .reviewer import review_diff


def _load_context() -> tuple[Path, Config]:
    try:
        root = repo_root()
    except GitError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(2)
    cfg = Config.load(root)
    return root, cfg


def _run_review(root: Path, cfg: Config, skip_build: bool) -> tuple[bool, int]:
    """Returns (passed, num_blockers). passed=True means safe to proceed."""
    branch = current_branch(root)
    files = staged_files(root)
    if not files:
        console.print("[yellow]No staged changes. Run `git add` first.[/yellow]")
        return False, 0

    diffstat = staged_diffstat(root)
    suspicious = flag_suspicious_files(files)
    print_manifest(branch, diffstat, suspicious)

    if suspicious:
        console.print(
            "[red]Sensitive files detected. Unstage them before continuing.[/red]"
        )
        return False, 99

    build_results = detect_and_run(root, skip=skip_build or cfg.skip_build)
    print_build_results(build_results)
    if any(not r.ok for r in build_results):
        console.print("[red]Build failed — aborting review.[/red]")
        return False, 99

    diff = staged_diff(root)
    if len(diff.encode("utf-8")) > cfg.max_diff_bytes:
        console.print(
            f"[yellow]Diff is large ({len(diff)} chars); truncating to "
            f"{cfg.max_diff_bytes} bytes for review.[/yellow]"
        )
        diff = diff.encode("utf-8")[: cfg.max_diff_bytes].decode("utf-8", "ignore")

    try:
        provider = build_provider(cfg.provider, cfg.model)
    except ProviderError as e:
        console.print(f"[red]{e}[/red]")
        return False, 99

    console.print(f"[dim]Reviewing with {cfg.provider}"
                  f"{' / ' + cfg.model if cfg.model else ''}…[/dim]")
    try:
        result = review_diff(
            provider,
            branch=branch,
            staged_files=files,
            diffstat=diffstat,
            diff=diff,
            suspicious=suspicious,
        )
    except ProviderError as e:
        console.print(f"[red]Review failed: {e}[/red]")
        return False, 99

    print_findings(result)
    return not result.has_blockers, len(result.blockers)


@click.group(help="AI pre-commit/pre-push code review gate.")
@click.version_option(__version__, prog_name="commit-review")
def main() -> None:  # pragma: no cover
    pass


@main.command(help="Review staged changes. Read-only.")
@click.option("--skip-build", is_flag=True, help="Skip build/lint/type-check.")
def review(skip_build: bool) -> None:
    root, cfg = _load_context()
    ok, blockers = _run_review(root, cfg, skip_build)
    if blockers:
        sys.exit(1)
    sys.exit(0 if ok else 1)


@main.command(help="Review, then commit if clean.")
@click.option("-m", "--message", required=True, help="Commit message.")
@click.option("--skip-build", is_flag=True)
@click.option("--allow-warnings", is_flag=True, help="Commit even if blockers found. Not recommended.")
def commit(message: str, skip_build: bool, allow_warnings: bool) -> None:
    root, cfg = _load_context()
    ok, blockers = _run_review(root, cfg, skip_build)
    if not ok and not allow_warnings:
        console.print(
            f"[red]Commit blocked: {blockers} blocker(s). "
            "Fix them, or re-run with --allow-warnings to override.[/red]"
        )
        sys.exit(1)
    console.print("[green]Creating commit…[/green]")
    try:
        subprocess.run(["git", "commit", "-m", message], cwd=root, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]git commit failed: {e}[/red]")
        sys.exit(e.returncode)


@main.command(help="Show push plan, confirm, then push.")
@click.option("--remote", default="origin", show_default=True)
@click.option("--yes", is_flag=True, help="Skip confirmation (useful in CI).")
def push(remote: str, yes: bool) -> None:
    root, _ = _load_context()
    try:
        plan = push_plan(root, remote=remote)
    except GitError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(2)
    print_push_plan(plan)
    if plan.local_branch in ("main", "master"):
        console.print(
            f"[red]Refusing to push {plan.local_branch} directly. "
            "Create a feature branch.[/red]"
        )
        sys.exit(2)
    if not yes:
        if not click.confirm("Push these commits?", default=False):
            console.print("[yellow]Aborted.[/yellow]")
            sys.exit(1)
    try:
        subprocess.run(
            ["git", "push", remote, plan.local_branch], cwd=root, check=True
        )
    except subprocess.CalledProcessError as e:
        console.print(
            "[red]Push failed. If it's a non-fast-forward rejection, "
            "pull/rebase first — do not force-push blindly.[/red]"
        )
        sys.exit(e.returncode)


@main.command("install-hook", help="Install a git pre-commit hook.")
def install_hook() -> None:
    root, _ = _load_context()
    hook = root / ".git" / "hooks" / "pre-commit"
    if not hook.parent.exists():
        console.print("[red]Not a git repo (no .git/hooks).[/red]")
        sys.exit(2)
    script = (
        "#!/usr/bin/env sh\n"
        "# commit-review pre-commit hook\n"
        "exec commit-review review\n"
    )
    if hook.exists():
        if not click.confirm(f"{hook} already exists. Overwrite?", default=False):
            sys.exit(1)
    hook.write_text(script)
    hook.chmod(0o755)
    console.print(f"[green]Installed hook → {hook}[/green]")


if __name__ == "__main__":  # pragma: no cover
    main()
