"""
Shared Gemini client for all CaseGen agents.
Uses google.genai (not deprecated google.generativeai).
"""

import json
import re
import time
from typing import Any, Callable, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TEMPERATURE, MAX_OUTPUT_TOKENS

T = TypeVar("T", bound=BaseModel)

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def extract_json(raw: str) -> dict:
    """Robustly extract a JSON object from a Gemini response."""
    if not raw:
        return {}

    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def generate_text(
    prompt: str,
    temperature: float = LLM_TEMPERATURE,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    max_retries: int = 3,
) -> str:
    """Call Gemini with exponential backoff retry."""
    client = get_client()
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            text = response.text
            if text and text.strip():
                return text.strip()
            last_error = ValueError("Empty response from Gemini")
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"[LLM] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {last_error}")


def generate_json(
    prompt: str,
    temperature: float = LLM_TEMPERATURE,
    max_retries: int = 3,
) -> dict:
    """Generate and parse JSON from Gemini."""
    raw = generate_text(prompt, temperature=temperature, max_retries=max_retries)
    result = extract_json(raw)
    if not result:
        raise ValueError("Could not parse JSON from Gemini response")
    return result


def generate_validated_json(
    prompt: str,
    model_class: Type[T],
    max_retries: int = 3,
    on_retry: Optional[Callable[[int, str], None]] = None,
) -> T:
    """
    Generate JSON and validate against a Pydantic model.
    On ValidationError, re-prompt Gemini with error details (up to max_retries).
    """
    current_prompt = prompt
    last_error = ""

    for attempt in range(max_retries):
        try:
            data = generate_json(current_prompt, max_retries=3)
            return model_class(**data)
        except ValidationError as e:
            last_error = str(e)
            if on_retry:
                on_retry(attempt + 1, last_error)
            current_prompt = (
                f"{prompt}\n\n"
                f"You made a JSON syntax or schema error on attempt {attempt + 1}:\n"
                f"{last_error}\n\n"
                "Fix it and return ONLY a valid JSON object matching the schema exactly."
            )
        except Exception as e:
            last_error = str(e)
            if on_retry:
                on_retry(attempt + 1, last_error)
            current_prompt = (
                f"{prompt}\n\n"
                f"Previous attempt failed: {last_error}\n"
                "Return ONLY valid JSON."
            )

    raise ValueError(f"Failed to produce valid {model_class.__name__} after {max_retries} attempts: {last_error}")
