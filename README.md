# commit-review

**A tiny, local-first alternative to CodeRabbit.** AI reviews your staged diff
before it becomes a commit — catches null-pointer traps, leftover `console.log`,
missing `await`, name collisions, unsafe imports, and pattern smells. BYO API
key (Anthropic / OpenAI / Gemini). Open source. ~500 lines of Python.

> Think CodeRabbit, but: runs locally, no SaaS, no GitHub-only, no per-seat
> pricing. You pay your LLM provider directly (pennies per review).

## Why another reviewer?

- **CodeRabbit / Sweep / Bito** are great but cloud-hosted, subscription, and
  bound to GitHub PRs. Feedback arrives *after* the code is pushed.
- **Pre-commit hooks** (ruff, eslint, mypy) catch style/syntax — not *logic*.
- **commit-review** sits in the gap: catches real bugs *before* you commit,
  using the same LLMs everyone already has an API key for.

## What it checks (the 8 steps)

| # | Step              | Catches                                                     |
|---|-------------------|-------------------------------------------------------------|
| 1 | Manifest          | Secrets (`.env`, `*.pem`), out-of-scope files               |
| 2 | Build             | Runs `npm run build` / `go build` / `cargo build` locally   |
| 3 | Null-safety       | Unguarded access to API data, props, storage, route params  |
| 4 | Imports           | Unused, wrong path, not actually exported                   |
| 5 | Name-collision    | New identifiers that shadow existing ones                   |
| 6 | Logic             | Missing `await`, off-by-one, swallowed catches, stray logs  |
| 7 | Naming            | Unclear names, casing mismatches                            |
| 8 | Better-pattern    | `Promise.all` for independent awaits, early returns, etc.   |

**Core principle:** read-only. The tool **reports** findings — it does not
rewrite your code. You decide what to fix.

## Install

```bash
pip install commit-review
```

Then pick a provider. **Three of the five are free:**

| Provider  | Free? | How to get a key                                              |
|-----------|:-----:|---------------------------------------------------------------|
| Gemini    | ✅    | https://aistudio.google.com/app/apikey (no card needed)       |
| Groq      | ✅    | https://console.groq.com/keys (fast Llama 3.3 70B)            |
| Ollama    | ✅    | fully local — `brew install ollama && ollama serve`           |
| Anthropic | 💳    | https://console.anthropic.com/settings/keys                   |
| OpenAI    | 💳    | https://platform.openai.com/api-keys                          |

```bash
# Default provider is Gemini (free).
export GEMINI_API_KEY=AIza...

# Or any of:
export GROQ_API_KEY=gsk_...
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
# Ollama needs no env var, just `ollama serve` running on localhost:11434.
```

## Usage

```bash
# Stage some changes
git add src/foo.ts

# Review them (read-only, prints findings)
commit-review review

# Or: review + commit in one step (blocked if blockers found)
commit-review commit -m "add user profile endpoint"

# Push with a transparent plan + confirmation
commit-review push

# Wire it in as a git pre-commit hook
commit-review install-hook
```

### Exit codes

- `0` — clean, safe to commit
- `1` — blockers found (or user aborted)
- `2` — setup error (not a git repo, no API key, etc.)

## Config (optional)

Drop `.commit-review.yml` at repo root:

```yaml
provider: gemini            # gemini | groq | ollama | anthropic | openai
model: gemini-2.0-flash     # optional override
skip_build: false
skip_steps: []              # e.g. [7, 8] to drop naming + pattern nits
max_diff_bytes: 200000
extra_rules:
  - "Flag any use of `any` in TypeScript."
```

See `.commit-review.example.yml`.

## Compared to...

| Feature                         | commit-review | CodeRabbit | pre-commit (ruff/eslint) |
|---------------------------------|:-------------:|:----------:|:------------------------:|
| Runs before commit (local)      | ✅            | ❌         | ✅                       |
| Catches logic bugs (not just style) | ✅        | ✅         | ❌                       |
| Works without GitHub            | ✅            | ❌         | ✅                       |
| Open source                     | ✅            | ❌         | ✅                       |
| BYO API key (no subscription)   | ✅            | ❌         | N/A                      |
| Per-line PR comments            | ❌*           | ✅         | ❌                       |

*GitHub Action mode with PR comments is on the roadmap.*

## Roadmap

- [ ] GitHub Action that posts per-line PR comments
- [ ] `pre-commit` framework integration (`.pre-commit-hooks.yaml`)
- [ ] Local provider support (Ollama) for fully offline review
- [ ] `--json` output for editor integrations
- [ ] Incremental review (only the hunks changed since last review)

## License

MIT. See [LICENSE](LICENSE).
