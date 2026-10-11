import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import app.main as main  # noqa: E402
from app.analyzer import prepare_image  # noqa: E402

client = TestClient(main.app)

FAKE_RESULT = {
    "doc_type": "SMS",
    "headline": "Do not pay.",
    "summary": "A scam.",
    "risk_level": "likely_scam",
    "red_flags": ["threat"],
    "what_to_do": ["ignore"],
    "confidence": "high",
    "adjusted": False,
    "demo": False,
}


def png_bytes(size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, "PNG")
    return buf.getvalue()


def post(data=None, content_type="image/png", lang="en"):
    data = png_bytes() if data is None else data
    return client.post("/analyze", files={"image": ("a.png", data, content_type)}, data={"lang": lang})


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_home_serves_ui():
    res = client.get("/")
    assert res.status_code == 200 and "PlainSight" in res.text


def test_rejects_non_image_content_type():
    assert post(b"hello", content_type="text/plain").status_code == 415


def test_rejects_corrupt_image_without_calling_model():
    assert post(b"not really an image").status_code == 415


def test_returns_model_result(monkeypatch):
    calls = {}

    def fake(data, lang):
        calls["lang"] = lang
        return FAKE_RESULT

    monkeypatch.setattr(main, "analyze_image", fake)
    res = post(lang="hi")
    assert res.status_code == 200 and res.json()["risk_level"] == "likely_scam"
    assert calls["lang"] == "hi"


def test_unknown_language_falls_back_to_english(monkeypatch):
    seen = {}
    monkeypatch.setattr(main, "analyze_image", lambda data, lang: seen.setdefault("lang", lang) and FAKE_RESULT)
    post(lang="xx")
    assert seen["lang"] == "en"


def test_model_failure_returns_502(monkeypatch):
    def boom(data, lang):
        raise RuntimeError("model down")

    monkeypatch.setattr(main, "analyze_image", boom)
    monkeypatch.delenv("DEMO_FALLBACK", raising=False)
    assert post().status_code == 502


def test_demo_fallback(monkeypatch):
    def boom(data, lang):
        raise RuntimeError("model down")

    monkeypatch.setattr(main, "analyze_image", boom)
    monkeypatch.setenv("DEMO_FALLBACK", "true")
    res = post(lang="mr")
    assert res.status_code == 200 and res.json()["demo"] is True


def test_prepare_image_shrinks_large_images():
    out = Image.open(io.BytesIO(prepare_image(png_bytes((4000, 3000)))))
    assert max(out.size) <= 1600
