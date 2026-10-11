import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from .analyzer import InvalidImageError, analyze_image, provider  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("plainsight")

BASE_DIR = Path(__file__).parent
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LANGS = {"en", "hi", "mr"}

app = FastAPI(title="PlainSight", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def _demo_result(lang: str) -> dict:
    with open(BASE_DIR / "demo_data.json", encoding="utf-8") as fh:
        data = json.load(fh)
    result = dict(data.get(lang) or data["en"])
    result["demo"] = True
    return result


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "provider": provider(), "model": os.environ.get("MODEL_ID", "")}


@app.post("/analyze")
def analyze(image: UploadFile = File(...), lang: str = Form("en")):
    lang = lang if lang in LANGS else "en"

    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image.")

    data = image.file.read(MAX_BYTES + 1)  # the image is kept in memory only
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (10 MB max).")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        return analyze_image(data, lang)
    except InvalidImageError:
        raise HTTPException(status_code=415, detail="Could not read this image.")
    except Exception:
        log.exception("Analysis failed")  # never log image content
        if os.environ.get("DEMO_FALLBACK", "").lower() in {"1", "true", "yes"}:
            return _demo_result(lang)
        raise HTTPException(status_code=502, detail="The model could not analyze this image.")
