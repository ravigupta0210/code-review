# Contributing

Thanks for considering a contribution. commit-review is small on purpose — the
goal is a tight, reliable quality gate, not a kitchen sink. Feature PRs that
expand scope significantly are likely to be declined; bug fixes, new providers,
and prompt-tuning are very welcome.

## Setup

```bash
git clone https://github.com/ravigupta0210/code-review.git
cd code-review
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running locally

```bash
export GROQ_API_KEY=gsk_...    # or any other provider key
cd /path/to/some/repo
git add <file>
commit-review review
```

## Tests

```bash
pytest -q
ruff check commit_review tests
```

## Pull requests

- Fork → branch → PR against `main`.
- Keep changes focused. One feature/fix per PR.
- Update `CHANGELOG.md` under `[Unreleased]`.
- New providers: add to `commit_review/providers.py` + `build_provider()`,
  document in README provider table, no new top-level dependency.
- New checks/rules: tune the system prompt in `commit_review/reviewer.py`. Avoid
  hardcoded heuristics — the LLM does the analysis.

## Reporting bugs

Use the bug report template. Always redact API keys before pasting logs.

## License

By contributing, you agree your changes are released under the MIT License.
