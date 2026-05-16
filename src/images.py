"""Image generation. Live: Pollinations.ai (free, no key). Offline: write a tiny placeholder PNG."""

from __future__ import annotations

import logging
import os
import time
import urllib.parse
from pathlib import Path

import requests

log = logging.getLogger(__name__)

# 1×1 transparent PNG (smallest valid PNG) — used by the offline placeholder.
_PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _live() -> bool:
    return os.environ.get("LIVE", "0") == "1"


def _placeholder(output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_PNG_1x1)
    return True


def generate(prompt: str, output_path: str | Path, *, width: int = 1920, height: int = 1080) -> bool:
    """Generate an image for `prompt` and write it to `output_path`. Returns True on success.

    Offline (LIVE != 1): writes a 1×1 placeholder PNG so the pipeline still produces a file.
    Live: calls Pollinations.ai with retries.
    """
    out = Path(output_path)
    if not _live():
        return _placeholder(out)

    encoded = urllib.parse.quote(prompt, safe="")
    url = f"https://image.pollinations.ai/prompt/{encoded}"
    params = {"width": width, "height": height, "model": "flux", "nologo": "true", "enhance": "true"}

    for attempt, delay in enumerate([0, 3, 8, 20]):
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            if len(r.content) < 1000:
                raise RuntimeError(f"tiny response ({len(r.content)} bytes)")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(r.content)
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("image generation failed (attempt %d): %s", attempt + 1, e)
    return False
