from typing import List, Literal

from pydantic import BaseModel


class Verdict(BaseModel):
    doc_type: str          # e.g. "SMS message", "UPI payment request", "Electricity bill"
    headline: str          # one short sentence with the verdict
    summary: str           # what this is, in simple words
    risk_level: Literal["safe", "careful", "likely_scam"]
    red_flags: List[str]   # concrete warning signs seen in the image
    what_to_do: List[str]  # 2-4 simple next steps
    confidence: Literal["low", "medium", "high"]
