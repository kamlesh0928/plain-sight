import pytest

from app.postprocess import (
    ModelOutputError,
    apply_safety_rules,
    extract_json,
    normalize,
)


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_fence_and_chatter():
    text = 'Sure! Here you go:\n```json\n{"summary": "hi"}\n```'
    assert extract_json(text) == {"summary": "hi"}


@pytest.mark.parametrize("bad", ["", "   ", "no json here", "{broken", "[1, 2]"])
def test_extract_json_rejects_bad_input(bad):
    with pytest.raises(ModelOutputError):
        extract_json(bad)


def test_normalize_happy_path():
    out = normalize(
        {
            "doc_type": "SMS",
            "headline": "Do not pay.",
            "summary": "A scam.",
            "risk_level": "Likely Scam",
            "red_flags": ["a", "b"],
            "what_to_do": ["x"],
            "confidence": "HIGH",
        }
    )
    assert out["risk_level"] == "likely_scam"
    assert out["confidence"] == "high"
    assert out["red_flags"] == ["a", "b"]


def test_normalize_unknown_risk_becomes_careful_low():
    out = normalize({"summary": "x", "risk_level": "banana", "confidence": "high"})
    assert (out["risk_level"], out["confidence"]) == ("careful", "low")


def test_normalize_requires_summary():
    with pytest.raises(ModelOutputError):
        normalize({"risk_level": "safe"})


def test_normalize_caps_list_lengths_and_accepts_strings():
    out = normalize({"summary": "x", "red_flags": [str(i) for i in range(20)], "what_to_do": "just one"})
    assert len(out["red_flags"]) == 5
    assert out["what_to_do"] == ["just one"]


def test_safe_with_red_flags_is_raised_to_careful():
    base = normalize({"summary": "x", "risk_level": "safe", "confidence": "high",
                      "headline": "All good", "red_flags": ["odd link"]})
    out = apply_safety_rules(base)
    assert out["risk_level"] == "careful"
    assert out["headline"] == ""
    assert out["adjusted"] is True


def test_safe_with_low_confidence_is_raised_to_careful():
    base = normalize({"summary": "x", "risk_level": "safe", "confidence": "low"})
    assert apply_safety_rules(base)["risk_level"] == "careful"


def test_clean_safe_stays_safe():
    base = normalize({"summary": "x", "risk_level": "safe", "confidence": "high", "headline": "ok"})
    out = apply_safety_rules(base)
    assert out["risk_level"] == "safe" and out["adjusted"] is False
