# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-27

### Added
- Initial release.
- Eight-step review checklist (manifest, build, null-safety, imports,
  name-collision, logic, naming, better-pattern) encoded as an LLM system prompt.
- Five LLM providers: Gemini, Groq, Ollama (free) + Anthropic, OpenAI (paid).
- `review`, `commit`, `push`, `install-hook` subcommands.
- Auto-detection of project type for build/lint/typecheck (npm, go, cargo, pip).
- Sensitive-file flagging (`.env`, `*.pem`, credentials) before commit/push.
- Push safety: refuses to push `main`/`master` directly, requires confirmation.
- Optional `.commit-review.yml` for per-repo configuration.

### Security
- Gemini provider now passes the API key via `x-goog-api-key` header instead of
  as a URL query parameter, so the key cannot leak into HTTP error messages.

[Unreleased]: https://github.com/ravigupta0210/code-review/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ravigupta0210/code-review/releases/tag/v0.1.0
