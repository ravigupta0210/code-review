"""Smoke tests — no network, no LLM calls."""

from commit_review import __version__
from commit_review.git_utils import flag_suspicious_files
from commit_review.reviewer import _parse_response
from commit_review.providers import build_provider, ProviderError


def test_version():
    assert __version__ == "0.1.0"


def test_flag_suspicious_files_finds_env():
    files = ["src/app.py", ".env", ".env.production", "README.md", "key.pem"]
    hits = flag_suspicious_files(files)
    assert ".env" in hits
    assert ".env.production" in hits
    assert "key.pem" in hits
    assert "src/app.py" not in hits


def test_parse_response_clean():
    summary, findings = _parse_response('{"summary": "all good", "findings": []}')
    assert summary == "all good"
    assert findings == []


def test_parse_response_with_findings():
    raw = """Some prose before.
    {"summary": "1 issue", "findings": [
      {"step": 6, "file": "a.py", "line": 12, "severity": "blocker", "message": "missing await"}
    ]}
    """
    summary, findings = _parse_response(raw)
    assert summary == "1 issue"
    assert len(findings) == 1
    assert findings[0].file == "a.py"
    assert findings[0].severity == "blocker"


def test_parse_response_invalid():
    summary, findings = _parse_response("not json at all")
    assert findings == []


def test_build_provider_unknown():
    try:
        build_provider("does-not-exist")
    except ProviderError as e:
        assert "unknown provider" in str(e)
    else:
        assert False, "expected ProviderError"


def test_build_provider_known():
    for name in ("anthropic", "openai", "gemini", "groq", "ollama"):
        p = build_provider(name)
        assert p.name == name
