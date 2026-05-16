"""WordPress REST API adapter. Only used when --publish is passed AND credentials are present."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import requests


def _auth_header() -> dict[str, str]:
    user = os.environ["WP_USER"]
    app_pw = os.environ["WP_APP_PASSWORD"]
    token = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _site() -> str:
    return os.environ["WP_SITE_URL"].rstrip("/")


def upload_image(image_path: str | Path, alt_text: str) -> dict[str, Any]:
    base = _site()
    url = f"{base}/wp-json/wp/v2/media"
    p = Path(image_path)
    with p.open("rb") as f:
        r = requests.post(
            url,
            headers={
                **_auth_header(),
                "Content-Disposition": f'attachment; filename="{p.name}"',
                "Content-Type": "image/png",
            },
            data=f.read(),
            timeout=60,
        )
    r.raise_for_status()
    media = r.json()
    requests.post(
        f"{url}/{media['id']}",
        headers={**_auth_header(), "Content-Type": "application/json"},
        json={"alt_text": alt_text},
        timeout=30,
    )
    return media


def create_post(plan: dict[str, Any], content_html: str, featured_media_id: int, *, publish: bool) -> dict[str, Any]:
    base = _site()
    r = requests.post(
        f"{base}/wp-json/wp/v2/posts",
        headers={**_auth_header(), "Content-Type": "application/json"},
        json={
            "title": plan["title"],
            "slug": plan["slug"],
            "content": content_html,
            "excerpt": plan["meta_description"],
            "status": "publish" if publish else "draft",
            "featured_media": featured_media_id,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()
