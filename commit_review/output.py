"""Rich-based terminal rendering for manifest, build, and findings."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .build_check import BuildResult
from .reviewer import ReviewResult

console = Console()


SEVERITY_STYLE = {
    "blocker": "bold red",
    "warning": "yellow",
    "nit": "dim cyan",
}


def print_manifest(branch: str, diffstat: str, suspicious: list[str]) -> None:
    body = Text()
    body.append("Branch: ", style="bold")
    body.append(f"{branch}\n\n")
    body.append(diffstat.rstrip() or "(no staged changes)")
    if suspicious:
        body.append("\n\n⚠ Potentially sensitive files:\n", style="bold red")
        for f in suspicious:
            body.append(f"  - {f}\n", style="red")
    console.print(Panel(body, title="[bold]What will be committed", border_style="cyan"))


def print_build_results(results: list[BuildResult]) -> None:
    if not results:
        console.print("[dim]build: skipped (no recognized project type)[/dim]")
        return
    table = Table(title="Build / lint / type-check", show_lines=False)
    table.add_column("Check", style="bold")
    table.add_column("Result")
    table.add_column("Command", style="dim")
    for r in results:
        status = "[green]pass[/green]" if r.ok else "[red]FAIL[/red]"
        table.add_row(r.name, status, r.command)
    console.print(table)
    for r in results:
        if not r.ok:
            console.print(
                Panel(
                    r.output[-2000:] or "(no output)",
                    title=f"[red]{r.name} output[/red]",
                    border_style="red",
                )
            )


def print_findings(result: ReviewResult) -> None:
    if result.summary:
        console.print(Panel(result.summary, title="[bold]Review summary", border_style="cyan"))
    if not result.findings:
        console.print("[green]✓ No findings — diff looks clean.[/green]")
        return
    by_step = result.by_step()
    for step in sorted(by_step):
        findings = by_step[step]
        step_name = findings[0].step_name
        table = Table(
            title=f"Step {step} — {step_name}",
            show_header=True,
            header_style="bold",
        )
        table.add_column("Severity", width=9)
        table.add_column("Location", style="cyan")
        table.add_column("Finding")
        for f in findings:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            sev = Text(f.severity, style=SEVERITY_STYLE.get(f.severity, "white"))
            table.add_row(sev, loc, f.message)
        console.print(table)


def print_push_plan(plan) -> None:
    body = Text()
    body.append("Local branch:  ", style="bold")
    body.append(f"{plan.local_branch}\n")
    body.append("Remote:        ", style="bold")
    body.append(f"{plan.remote}/{plan.remote_branch}\n\n")
    body.append("Commits going up:\n", style="bold")
    body.append(plan.commits.rstrip() or "(none)")
    body.append("\n\nFiles:\n", style="bold")
    body.append(plan.diffstat.rstrip() or "(none)")
    console.print(Panel(body, title="[bold]What will be pushed", border_style="cyan"))
