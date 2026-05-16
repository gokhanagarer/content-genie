"""Orchestrator: plan → outline → article → images → (optional) WordPress."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from . import images, plan as plan_mod

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("content-genie")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
PIPELINE_LOG = OUTPUT_DIR / "pipeline.jsonl"


def _markdown_to_html(md: str) -> str:
    try:
        import markdown
        return markdown.markdown(md, extensions=["fenced_code", "tables"])
    except ImportError:
        parts = []
        for p in md.split("\n\n"):
            p = p.strip()
            if not p:
                continue
            if p.startswith("### "):
                parts.append(f"<h3>{p[4:]}</h3>")
            elif p.startswith("## "):
                parts.append(f"<h2>{p[3:]}</h2>")
            elif p.startswith("# "):
                parts.append(f"<h1>{p[2:]}</h1>")
            else:
                parts.append(f"<p>{p}</p>")
        return "\n".join(parts)


def _log_pipeline(record: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with PIPELINE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_one(topic: str, *, publish: bool, skip_wp: bool, language: str, word_count: int) -> Path:
    log.info("=== %s ===", topic)
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    workdir = OUTPUT_DIR / run_id
    workdir.mkdir(parents=True, exist_ok=True)

    log.info("Step 1/5: plan")
    plan = plan_mod.generate_plan(topic, language=language)
    (workdir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("Step 2/5: outline")
    outline = plan_mod.generate_outline(plan, language=language)
    (workdir / "outline.json").write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("Step 3/5: article")
    article_md = plan_mod.generate_article(plan, outline, language=language, target_word_count=word_count)
    (workdir / "article.md").write_text(article_md, encoding="utf-8")
    log.info("  %d words", len(article_md.split()))

    log.info("Step 4/5: images")
    image_prompts = plan_mod.generate_image_prompts(plan)
    images_made = {}
    for key, prompt in image_prompts.items():
        target = workdir / f"{key}.png"
        if images.generate(prompt, target):
            images_made[key] = str(target)
            log.info("  %s", key)

    if skip_wp or not all(os.environ.get(k) for k in ("WP_SITE_URL", "WP_USER", "WP_APP_PASSWORD")):
        log.info("Step 5/5: WordPress publish skipped (no credentials or --no-wp)")
        _log_pipeline({"run_id": run_id, "topic": topic, "status": "ready_local",
                       "workdir": str(workdir), "images": list(images_made)})
        return workdir

    log.info("Step 5/5: WordPress publish")
    from . import publish as pub  # lazy import; publish module reads env vars on demand
    featured_id = 0
    for key, path in images_made.items():
        media = pub.upload_image(path, f"{plan['focus_keyword']} - {key}")
        log.info("  uploaded %s (media_id=%d)", key, media["id"])
        if key == "hero":
            featured_id = media["id"]
    post = pub.create_post(plan, _markdown_to_html(article_md), featured_id, publish=publish)
    log.info("  WP post %d → %s (status=%s)", post["id"], post["link"], post["status"])
    _log_pipeline({"run_id": run_id, "topic": topic,
                   "status": "published" if publish else "draft",
                   "wp_id": post["id"], "wp_url": post["link"], "workdir": str(workdir)})
    return workdir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="content-genie blog pipeline")
    parser.add_argument("--topic", help="single topic")
    parser.add_argument("--from-keywords", help="file with one topic per line")
    parser.add_argument("--publish", action="store_true", help="publish (default: draft)")
    parser.add_argument("--no-wp", action="store_true", help="generate locally; skip WordPress")
    parser.add_argument("--language", default=os.environ.get("CONTENT_LANGUAGE", "English"))
    parser.add_argument("--word-count", type=int, default=int(os.environ.get("TARGET_WORD_COUNT", "1800")))
    args = parser.parse_args(argv)

    topics: list[str] = []
    if args.topic:
        topics.append(args.topic)
    elif args.from_keywords:
        topics = [
            ln.strip() for ln in Path(args.from_keywords).read_text(encoding="utf-8").splitlines() if ln.strip()
        ]
    else:
        parser.error("Provide --topic or --from-keywords")

    for topic in topics:
        try:
            run_one(topic, publish=args.publish, skip_wp=args.no_wp,
                    language=args.language, word_count=args.word_count)
        except Exception:  # noqa: BLE001
            log.exception("failed for %r", topic)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
