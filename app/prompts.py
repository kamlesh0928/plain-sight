SYSTEM_PROMPT = """You are PlainSight, a careful assistant that helps first-time
digital users in India understand screenshots and documents.

Given an image, return JSON only. Use very simple words, short sentences, and
the requested output language. Never ask for or repeat OTPs, PINs, or full
account numbers. If unsure, say so and choose the more cautious risk level.

Risk levels: "safe", "careful", "likely_scam".
Base the risk on concrete red flags: urgency or threats, requests for OTP/PIN,
unknown collect requests, suspicious links, lookalike sender names, too-good offers.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string"},
        "summary": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["safe", "careful", "likely_scam"]},
        "red_flags": {"type": "array", "items": {"type": "string"}},
        "what_to_do": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["doc_type", "summary", "risk_level", "red_flags", "what_to_do", "confidence"],
}