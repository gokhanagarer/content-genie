"""Offline pipeline tests — no API keys, no network."""

import json
from pathlib import Path

import pytest

from src import plan as plan_mod
from src.main import main as run_main


def test_stub_plan_has_required_keys():
    p = plan_mod.generate_plan("Server-Side Tagging")
    for key in ("title", "slug", "meta_description", "focus_keyword", "secondary_keywords"):
        assert key in p, f"missing key: {key}"
    assert p["_engine"] == "offline-stub"


def test_stub_outline_has_5_to_7_sections():
    p = plan_mod.generate_plan("Event Taxonomy")
    outline = plan_mod.generate_outline(p)
    assert 5 <= len(outline) <= 7
    for s in outline:
        assert s["h2"]
        assert isinstance(s["points"], list) and len(s["points"]) >= 2


def test_stub_article_includes_faq():
    p = plan_mod.generate_plan("Attribution Modelling")
    o = plan_mod.generate_outline(p)
    article = plan_mod.generate_article(p, o)
    assert "## FAQ" in article
    assert article.count("\n## ") >= 5  # all H2 sections present


def test_main_runs_offline_demo(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LIVE", raising=False)
    rc = run_main(["--topic", "Server-Side Tagging", "--no-wp"])
    assert rc == 0

    from src import main as m
    # at least one run directory should contain plan/outline/article
    runs = sorted([p for p in m.OUTPUT_DIR.iterdir() if p.is_dir()])
    assert runs, "no run directory created"
    latest = runs[-1]
    assert (latest / "plan.json").exists()
    assert (latest / "outline.json").exists()
    assert (latest / "article.md").exists()
    assert (latest / "hero.png").exists()
