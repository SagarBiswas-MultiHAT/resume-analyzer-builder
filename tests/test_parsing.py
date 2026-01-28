import os
import importlib
import sys


def _load_app_module():
    """Import backend.app with a dummy key to avoid startup exit."""
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    if "backend.app" in sys.modules:
        del sys.modules["backend.app"]
    return importlib.import_module("backend.app")


def test_parse_ai_analysis_extracts_sections():
    app_module = _load_app_module()
    sample = """
Rating: 8
Suggestions:
- Add metrics to bullets.
- Clarify scope and impact.
Keyword Gaps (comma-separated): Python, Flask, CI/CD
Improved Summary (10/10):
Experienced engineer with measurable impact.
Improved Bullet Examples:
- Increased throughput by 25%.
Priority Fix Order:
1. Add metrics
2. Tighten summary
"""
    parsed = app_module.parse_ai_analysis(sample)
    assert parsed["rating"] == "8"
    assert "Add metrics" in (parsed["suggestions"] or "")
    assert parsed["keyword_gaps"] == "Python, Flask, CI/CD"
    assert "Experienced engineer" in (parsed["improved_summary"] or "")
    assert "Increased throughput" in (parsed["improved_bullets"] or "")
    assert "Add metrics" in (parsed["priority_fixes"] or "")


def test_health_endpoint():
    app_module = _load_app_module()
    client = app_module.app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "ok"
    assert "max_upload_mb" in payload
