"""Load .commit-review.yml from repo root. All fields optional with sensible defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    provider: str = "anthropic"
    model: str | None = None
    skip_build: bool = False
    skip_steps: list[int] = field(default_factory=list)
    max_diff_bytes: int = 200_000
    extra_rules: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, repo_root: Path) -> "Config":
        for name in (".commit-review.yml", ".commit-review.yaml"):
            path = repo_root / name
            if path.exists():
                try:
                    data = yaml.safe_load(path.read_text()) or {}
                except yaml.YAMLError:
                    return cls()
                return cls(
                    provider=data.get("provider", "anthropic"),
                    model=data.get("model"),
                    skip_build=bool(data.get("skip_build", False)),
                    skip_steps=list(data.get("skip_steps", []) or []),
                    max_diff_bytes=int(data.get("max_diff_bytes", 200_000)),
                    extra_rules=list(data.get("extra_rules", []) or []),
                )
        return cls()
