"""LLM-driven blog plan + outline + full article generation.

When `GROQ_API_KEY` is set we call Groq (free tier, fast). Otherwise we fall
back to deterministic stubs so the demo and tests run with no network.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from . import stubs


def _extract_json(text: str) -> Any:
    """Tolerant JSON extractor — strips markdown fences LLMs sometimes add."""
    t = re.sub(r"^```(?:json)?\s*", "", text.strip())
    t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def _groq_complete(prompt: str, system: str, *, temperature: float, max_tokens: int) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def _live() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


# ── Stage 1: blog plan ────────────────────────────────────────────────────────

def generate_plan(topic: str, language: str = "English") -> dict[str, Any]:
    if not _live():
        return stubs.stub_plan(topic, language)
    system = f"You are a {language} SEO content strategist. Return valid JSON only."
    prompt = f"""Generate a blog plan for the topic: "{topic}".

Return JSON with this exact shape:
{{
  "title": "SEO-optimized title (<60 chars)",
  "slug": "url-friendly-slug",
  "meta_description": "<155 chars compelling meta",
  "focus_keyword": "primary keyword",
  "secondary_keywords": ["keyword 2", "keyword 3", "keyword 4"],
  "target_audience": "who this is for",
  "content_angle": "unique angle/hook"
}}

Language: {language}. Return ONLY JSON."""
    raw = _groq_complete(prompt, system, temperature=0.4, max_tokens=600)
    return _extract_json(raw)


# ── Stage 2: outline ──────────────────────────────────────────────────────────

def generate_outline(plan: dict[str, Any], language: str = "English") -> list[dict[str, Any]]:
    if not _live():
        return stubs.stub_outline(plan)
    system = f"You are a {language} content outliner. Return valid JSON array only."
    prompt = f"""Generate an outline for:
Title: {plan['title']}
Focus keyword: {plan['focus_keyword']}
Angle: {plan['content_angle']}

Return JSON array of 5–7 H2 sections:
[
  {{"h2": "Section title", "points": ["point 1", "point 2", "point 3"]}}
]

Language: {language}. Return ONLY the JSON array."""
    raw = _groq_complete(prompt, system, temperature=0.5, max_tokens=1500)
    return _extract_json(raw)


# ── Stage 3: full article ─────────────────────────────────────────────────────

def generate_article(
    plan: dict[str, Any],
    outline: list[dict[str, Any]],
    *,
    language: str = "English",
    target_word_count: int = 1800,
) -> str:
    if not _live():
        return stubs.stub_article(plan, outline)
    system = (
        f"You are a {language} senior content writer. Direct, professional prose, "
        "no hype. Answer-first paragraphs. Use markdown."
    )
    outline_text = "\n".join(
        f"## {s['h2']}\n" + "\n".join(f"- {p}" for p in s["points"])
        for s in outline
    )
    prompt = f"""Write a complete {target_word_count}-word blog post in markdown.

Title: {plan['title']}
Meta: {plan['meta_description']}
Focus keyword: {plan['focus_keyword']}

Follow this outline strictly (H2 headings + subsections):
{outline_text}

Rules:
- Use H2 (##) for sections, H3 (###) for subsections
- 40-80 word paragraphs
- Include the focus keyword 4-6 times naturally
- End with a brief FAQ section (3 Q&As) as ## FAQ
- No preamble, start directly with the body

Language: {language}."""
    return _groq_complete(prompt, system, temperature=0.65, max_tokens=6000)


# ── Stage 4: image prompts ────────────────────────────────────────────────────

def generate_image_prompts(plan: dict[str, Any]) -> dict[str, str]:
    if not _live():
        return stubs.stub_image_prompts(plan)
    system = "You are a visual director. Return valid JSON only."
    prompt = f"""For this blog post, write 3 detailed English image-generation prompts.
Topic: {plan['title']}
Audience: {plan['target_audience']}

Return JSON:
{{
  "hero": "cinematic hero image prompt, photographic, 16:9",
  "info": "clean infographic prompt, flat vector style, data viz mood",
  "photo": "lifestyle photo prompt, natural lighting, human element"
}}

Return ONLY JSON."""
    raw = _groq_complete(prompt, system, temperature=0.5, max_tokens=500)
    return _extract_json(raw)
