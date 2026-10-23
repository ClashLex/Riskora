"""Optional grounded extraction from user supplied company disclosures."""

from __future__ import annotations

import json
import os
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, HttpUrl


class Fact(BaseModel):
    statement: str = Field(min_length=3, max_length=500)
    evidence: str = Field(min_length=3, max_length=500)


class NumericFact(BaseModel):
    label: str = Field(min_length=2, max_length=100)
    value_text: str = Field(min_length=1, max_length=50)
    unit: str = Field(max_length=50)
    evidence: str = Field(min_length=3, max_length=500)


class Extraction(BaseModel):
    isin: str
    category: str = Field(min_length=2, max_length=80)
    published_at: str
    direction: Literal["positive", "neutral", "negative"]
    explanation: str = Field(min_length=3, max_length=500)
    facts: list[Fact] = Field(max_length=10)
    numbers: list[NumericFact] = Field(default_factory=list, max_length=10)
    source_url: HttpUrl
    confidence: float = Field(ge=0, le=1)


def extract(event: dict):
    key, model, base = (
        os.getenv(name, "").strip() for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL")
    )
    if not all((key, model, base)):
        raise ValueError("LLM is not configured; events remain available without extraction.")
    parsed = urlparse(base)
    if (
        (
            parsed.scheme != "https"
            and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"})
        )
        or not parsed.netloc
        or parsed.username
    ):
        raise ValueError("LLM_BASE_URL must use HTTPS or a local loopback endpoint.")
    prompt = (
        "Extract only facts supported by the supplied excerpt. Return a JSON object with "
        "isin, category, published_at, direction (positive/neutral/negative), explanation, "
        "facts (verbatim statement and evidence), numbers (label, verbatim value_text, unit, "
        "verbatim evidence), source_url, confidence. "
        "If no facts are supported, use an empty facts array and neutral direction. "
        f"Document: {json.dumps(event, ensure_ascii=False)}"
    )
    with httpx.Client(timeout=25, follow_redirects=False) as client:
        response = client.post(
            base.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "You extract grounded facts from disclosures. Never infer trading decisions.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
    result = Extraction.model_validate_json(payload["choices"][0]["message"]["content"])
    if (
        result.isin != event["isin"]
        or result.published_at != event["published_at"]
        or str(result.source_url).rstrip("/") != event["source_url"].rstrip("/")
    ):
        raise ValueError("Extraction identifiers or provenance do not match the supplied event.")
    original = event["excerpt"].casefold()
    if any(
        fact.evidence.casefold() not in original or fact.statement.casefold() not in original
        for fact in result.facts
    ):
        raise ValueError(
            "Extraction contains a factual statement or evidence absent from the supplied excerpt."
        )
    if any(
        figure.evidence.casefold() not in original
        or figure.value_text.casefold() not in figure.evidence.casefold()
        for figure in result.numbers
    ):
        raise ValueError("Extraction contains a numerical figure absent from the supplied excerpt.")
    return result.model_dump(mode="json"), model
