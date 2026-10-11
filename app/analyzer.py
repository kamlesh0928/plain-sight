import base64
import io
import logging
import os
import time
from functools import lru_cache

import httpx
from PIL import Image, ImageOps

from .postprocess import ModelOutputError, apply_safety_rules, extract_json, normalize
from .prompts import build_prompt

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:
    pass

log = logging.getLogger("plainsight")
MAX_SIDE = 1600  # px; keeps requests fast and cheap


class InvalidImageError(ValueError):
    """The uploaded file is not an image we can read."""


def prepare_image(data: bytes) -> bytes:
    """Fix rotation, shrink and re-encode as JPEG. Nothing is written to disk."""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as exc:
        raise InvalidImageError("could not read image") from exc
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


@lru_cache(maxsize=1)
def _gemini_client():
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _generate_with_retry(client, model, contents, config, tries=4):
    """Retry temporary Google errors (429, 500, 503) with a growing wait."""
    delay = 2
    for attempt in range(1, tries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code not in (429, 500, 503) or attempt == tries:
                raise
            log.warning("Model %s returned %s (attempt %d/%d). Retrying in %ds.",
                        model, code, attempt, tries, delay)
            time.sleep(delay)
            delay *= 2


def _call_gemini(jpeg: bytes, prompt: str) -> str:
    from google.genai import types

    from .schema import Verdict

    client = _gemini_client()
    models = [os.environ["MODEL_ID"]]
    backup = os.environ.get("MODEL_FALLBACK", "").strip()
    if backup:
        models.append(backup)

    contents = [types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"), prompt]
    if os.environ.get("JSON_MODE", "false").lower() in {"1", "true", "yes"}:
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=Verdict,
        )
    else:  # default: the prompt asks for JSON and the parser handles it
        config = types.GenerateContentConfig(temperature=0.2)

    last_error = None
    for model in models:
        try:
            response = _generate_with_retry(client, model, contents, config)
            return response.text or ""
        except Exception as exc:
            last_error = exc
            log.warning("Model %s failed: %s", model, type(exc).__name__)
    raise last_error


def _call_ollama(jpeg: bytes, prompt: str) -> str:
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    payload = {
        "model": os.environ["MODEL_ID"],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(jpeg).decode("ascii")],
            }
        ],
    }
    response = httpx.post(f"{url}/api/chat", json=payload, timeout=180)
    response.raise_for_status()
    return response.json()["message"]["content"]


def provider() -> str:
    return os.environ.get("PROVIDER", "gemini").lower()


def _call_model(jpeg: bytes, prompt: str) -> str:
    if provider() == "ollama":
        return _call_ollama(jpeg, prompt)
    return _call_gemini(jpeg, prompt)


def analyze_image(data: bytes, lang: str = "en") -> dict:
    """Return a normalized verdict dict for the image bytes."""
    jpeg = prepare_image(data)
    prompt = build_prompt(lang)

    last_error = None
    for attempt in (1, 2):  # one retry if the model returns unusable output
        try:
            result = normalize(extract_json(_call_model(jpeg, prompt)))
            result = apply_safety_rules(result)
            result["demo"] = False
            return result
        except ModelOutputError as exc:
            last_error = exc
            log.warning("Unusable model output on attempt %d: %s", attempt, exc)
    raise last_error
