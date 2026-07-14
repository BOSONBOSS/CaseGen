"""
Shared Gemini client for all CaseGen agents.
Uses google.genai (not deprecated google.generativeai).
"""

import json
import re
import time
from typing import Any, Callable, Optional, Type, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    LLM_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)

T = TypeVar("T", bound=BaseModel)

_client = None

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_client():
    """Lazily build the Gemini client (only used when LLM_PROVIDER == 'gemini')."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _openrouter_generate(prompt: str, temperature: float, max_output_tokens: int) -> str:
    resp = requests.post(
        _OPENROUTER_URL,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


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
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            if LLM_PROVIDER == "openrouter":
                text = _openrouter_generate(prompt, temperature, max_output_tokens)
            else:
                from google.genai import types
                client = get_client()
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
            last_error = ValueError("Empty response from LLM")
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"[LLM] Primary provider ({LLM_PROVIDER}) attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    # -- AUTOMATIC FALLBACK --
    fallback_provider = "gemini" if LLM_PROVIDER == "openrouter" else "openrouter"
    exhausted_key = "OPENROUTER_API_KEY" if LLM_PROVIDER == "openrouter" else "GEMINI_API_KEY"
    
    print("\n" + "="*80)
    print(f"[WARNING] API KEY EXHAUSTED: Your {exhausted_key} has failed or run out of credits!")
    print(f"[ACTION REQUIRED] Please replace {exhausted_key} in your .env file.")
    print(f"[SYSTEM] Attempting automatic fallback to {fallback_provider} backup key to save this run...")
    print("="*80 + "\n")
    
    try:
        if fallback_provider == "openrouter" and OPENROUTER_API_KEY:
            text = _openrouter_generate(prompt, temperature, max_output_tokens)
        elif fallback_provider == "gemini" and GEMINI_API_KEY:
            from google.genai import types
            # get_client handles building the gemini client safely
            client = get_client()
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            text = response.text
        else:
             raise ValueError(f"Missing API key for fallback provider: {fallback_provider}")
             
        if text and text.strip():
            print(f"[LLM] [SUCCESS] Fallback to {fallback_provider} successful!")
            return text.strip()
    except Exception as fallback_e:
         print("\n" + "="*80)
         print(f"[FATAL ERROR] Both your primary and backup API keys are exhausted!")
         print(f"[ACTION REQUIRED] Please check BOTH OPENROUTER_API_KEY and GEMINI_API_KEY in your .env file.")
         print("="*80 + "\n")
         raise RuntimeError(f"Both primary ({LLM_PROVIDER}) and fallback ({fallback_provider}) failed. Last error: {fallback_e}")

    raise RuntimeError(f"API failed after {max_retries} attempts: {last_error}")


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
