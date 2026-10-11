import json, os
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from app.prompts import SYSTEM_PROMPT, RESPONSE_SCHEMA

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_ID = os.environ["MODEL_ID"]
LANGS = {"en": "English", "hi": "Hindi", "mr": "Marathi"}

app = FastAPI(title="PlainSight")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home():
    return FileResponse("app/static/index.html")

@app.post("/analyze")
async def analyze(image: UploadFile = File(...), lang: str = Form("en")):
    data = await image.read()
    prompt = f"Explain this image. Write all text values in {LANGS.get(lang, 'English')}."
    resp = client.models.generate_content(
        model=MODEL_ID,
        contents=[types.Part.from_bytes(data=data, mime_type=image.content_type), prompt],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )
    return json.loads(resp.text)