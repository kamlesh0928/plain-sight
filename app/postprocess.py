import json
import re

RISK_LEVELS = ("safe", "careful", "likely_scam")
CONFIDENCE_LEVELS = ("low", "medium", "high")


class ModelOutputError(ValueError):
    """The model reply could not be turned into a usable result."""


def extract_json(text: str) -> dict:
    """Pull a JSON object out of a model reply, tolerating code fences and chatter."""
    if not text or not text.strip():
        raise ModelOutputError("empty model response")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ModelOutputError("no JSON object found in model response")
    try:
        obj = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ModelOutputError("model response is not valid JSON") from exc
    if not isinstance(obj, dict):
        raise ModelOutputError("model response JSON is not an object")
    return obj


def _text(value, limit: int = 600) -> str:
    return str(value).strip()[:limit] if value is not None else ""


def _items(value, max_items: int = 5, limit: int = 300) -> list:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    cleaned = (_text(item, limit) for item in value)
    return [item for item in cleaned if item][:max_items]


def _choice(value, allowed):
    candidate = _text(value, 40).lower().replace(" ", "_").replace("-", "_")
    return candidate if candidate in allowed else None


def normalize(raw: dict) -> dict:
    """Coerce a raw model dict into the shape the UI expects."""
    summary = _text(raw.get("summary"))
    if not summary:
        raise ModelOutputError("model response has no summary")

    risk = _choice(raw.get("risk_level"), RISK_LEVELS)
    confidence = _choice(raw.get("confidence"), CONFIDENCE_LEVELS)
    if risk is None:
        risk, confidence = "careful", "low"
    if confidence is None:
        confidence = "low"

    return {
        "doc_type": _text(raw.get("doc_type"), 80) or "unclear",
        "headline": _text(raw.get("headline"), 200),
        "summary": summary,
        "risk_level": risk,
        "red_flags": _items(raw.get("red_flags")),
        "what_to_do": _items(raw.get("what_to_do"), max_items=4),
        "confidence": confidence,
    }


def apply_safety_rules(result: dict) -> dict:
    """Never let the model say 'safe' when its own output contradicts that.

    If the headline is dropped because the level was raised, the UI falls back to
    the localized risk label so the user never sees a mismatched sentence.
    """
    out = dict(result)
    out["adjusted"] = False
    if out["risk_level"] == "safe" and (out["red_flags"] or out["confidence"] == "low"):
        out["risk_level"] = "careful"
        out["headline"] = ""
        out["adjusted"] = True
    return out
