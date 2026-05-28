#!/usr/bin/env python3
"""
Gemini API writer for hebrew-book-producer plugin.

Two modes:

  Draft mode — generate new prose from chapter context:
    python scripts/gemini_book_writer.py \\
      --mode draft \\
      --voice /path/to/AUTHOR_VOICE.md \\
      --context /tmp/chapter-context.json

  Edit mode — rewrite prose per precise instructions:
    python scripts/gemini_book_writer.py \\
      --mode edit \\
      --voice /path/to/AUTHOR_VOICE.md \\
      --context /tmp/edit-context.json

Draft context JSON:
  {
    "chapter_brief": "...",
    "sefaria_sources": [...],
    "section_index": 0,
    "word_ceiling": 400,
    "language": "he"
  }

Edit context JSON:
  {
    "original_text": "...",
    "edit_instructions": "...",
    "constraints": ["preserve all citations", ...],
    "language": "he"
  }

Reads $GEMINI_API_KEY from environment.
Uses only stdlib (urllib, json) — zero pip dependencies.
Python 3.9+ required.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from typing import Optional


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 60
MAX_RETRIES = 3
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 3000


# ---------------------------------------------------------------------------
# Voice profile loading
# ---------------------------------------------------------------------------

def load_voice_profile(path: str) -> dict:
    """Load AUTHOR_VOICE.md and return (raw_text, writer_config).

    Returns a dict:
      {
        "raw": <full markdown text>,
        "writer": {
          "provider": "gemini" | "claude",
          "model": "gemini-2.5-flash",
          "temperature": 0.7,
          "max_tokens": 3000
        }
      }

    The writer: block is parsed from the '## Writer Configuration' section
    ONLY if it appears as live YAML (not inside an HTML comment).
    Falls back to provider=claude for all fields when the section is absent,
    commented-out, or missing individual keys.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Voice profile not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    writer_cfg = _extract_writer_config(raw)
    return {"raw": raw, "writer": writer_cfg}


def _extract_writer_config(text: str) -> dict:
    """Extract writer: YAML block from ## Writer Configuration section.

    Ignores content inside HTML comments (<!-- ... -->).
    Returns defaults if the section is absent or commented out.
    """
    defaults = {
        "provider": "claude",
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": DEFAULT_MAX_TOKENS,
    }

    # Strip all HTML comments from the text before parsing
    text_no_comments = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # Find the ## Writer Configuration section
    section_match = re.search(
        r'^##\s+Writer Configuration\s*\n(.*?)(?=^##\s|\Z)',
        text_no_comments,
        re.MULTILINE | re.DOTALL
    )
    if not section_match:
        return defaults

    section_body = section_match.group(1)

    # Look for a writer: YAML block (may or may not be in a code fence)
    # Strip fences if present
    fenced = re.search(r'```(?:yaml|yml)?\s*\n(.*?)```', section_body, re.DOTALL)
    if fenced:
        yaml_text = fenced.group(1)
    else:
        yaml_text = section_body

    # Find the writer: key and parse its sub-keys
    writer_match = re.search(r'^writer:\s*$', yaml_text, re.MULTILINE)
    if not writer_match:
        # Maybe writer: value is inline — check for any writer: block at all
        return defaults

    # Parse the indented block following writer:
    start = writer_match.end()
    remaining = yaml_text[start:]
    parsed = _parse_writer_block(remaining)
    if not parsed:
        return defaults

    return {
        "provider": parsed.get("provider", defaults["provider"]),
        "model": parsed.get("model", defaults["model"]),
        "temperature": _coerce_float(parsed.get("temperature"), defaults["temperature"]),
        "max_tokens": _coerce_int(parsed.get("max_tokens"), defaults["max_tokens"]),
    }


def _parse_writer_block(text: str) -> dict:
    """Parse indented key: value pairs immediately following the writer: key."""
    result = {}
    for line in text.split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        # Stop at next top-level key (not indented)
        if line and line[0] != ' ' and line[0] != '\t':
            break
        stripped = line.strip()
        if ':' in stripped:
            key, _, val = stripped.partition(':')
            key = key.strip().strip('"').strip("'")
            val = val.strip().strip('"').strip("'")
            if val:
                result[key] = val
    return result


def _coerce_float(val, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _coerce_int(val, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_draft_prompt(profile: dict, context: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for draft mode.

    Args:
        profile: output of load_voice_profile()
        context: parsed draft context JSON with keys:
            chapter_brief, sefaria_sources, section_index, word_ceiling, language
    """
    voice_raw = profile.get("raw", "")
    word_ceiling = context.get("word_ceiling", DEFAULT_MAX_TOKENS)
    section_index = context.get("section_index", 0)
    language = context.get("language", "he")

    system_parts = [
        "Write Hebrew non-fiction book prose.",
        "",
        "## Voice and Style Rules",
        "",
        voice_raw,
        "",
        "## Non-fiction-book-specific rules take priority over Core voice rules when they conflict.",
        "",
        f"## Constraints",
        f"- Language: {language}",
        f"- Word ceiling for this section: {word_ceiling} words. Do not exceed it.",
        f"- Use ONLY the Sefaria-verified sources provided. Do not invent or hallucinate citations.",
        f"- Do not add headers or meta-commentary — write prose only.",
    ]
    system_prompt = '\n'.join(system_parts)

    chapter_brief = context.get("chapter_brief", "")
    sefaria_sources = context.get("sefaria_sources", [])

    user_parts = [
        f"## Chapter Brief",
        chapter_brief,
        "",
    ]
    if sefaria_sources:
        user_parts.append("## Verified Sources (use these verbatim; do not modify)")
        for src in sefaria_sources:
            if isinstance(src, dict):
                ref = src.get("ref", "")
                text = src.get("text", "")
                user_parts.append(f"- {ref}: {text}")
            else:
                user_parts.append(f"- {src}")
        user_parts.append("")
    user_parts.append(
        f"Write section {section_index + 1} of the chapter. "
        f"Maximum {word_ceiling} words. Hebrew prose only."
    )
    user_prompt = '\n'.join(user_parts)

    return system_prompt, user_prompt


def build_edit_prompt(profile: dict, context: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for edit mode.

    Args:
        profile: output of load_voice_profile()
        context: parsed edit context JSON with keys:
            original_text, edit_instructions, constraints, language
    """
    voice_raw = profile.get("raw", "")
    language = context.get("language", "he")
    constraints = context.get("constraints", [])

    system_parts = [
        "Execute this specific edit precisely. Do not change anything else.",
        "",
        "## Voice and Style Rules",
        "",
        voice_raw,
        "",
        "## Non-fiction-book-specific rules take priority over Core voice rules when they conflict.",
        "",
        f"## Constraints",
        f"- Language: {language}",
        "- Preserve all citations exactly as they appear in the original.",
        "- Return ONLY the rewritten text — no preamble, no explanation, no commentary.",
    ]
    for c in constraints:
        system_parts.append(f"- {c}")
    system_prompt = '\n'.join(system_parts)

    original_text = context.get("original_text", "")
    edit_instructions = context.get("edit_instructions", "")

    user_parts = [
        "## Original Text",
        original_text,
        "",
        "## Edit Instructions",
        edit_instructions,
        "",
        "Rewrite the original text according to the instructions above. "
        "Return ONLY the rewritten text.",
    ]
    user_prompt = '\n'.join(user_parts)

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------

def call_gemini_api(system_prompt: str, user_prompt: str, *,
                    model: str = DEFAULT_MODEL,
                    api_key: Optional[str],
                    temperature: float = DEFAULT_TEMPERATURE,
                    max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Call Gemini REST API and return generated text.

    Retries with exponential backoff on HTTP 429 (up to MAX_RETRIES attempts).
    Raises on all other HTTP errors or after exhausting retries.
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Export it in your shell profile.")

    url = f"{GEMINI_API_BASE}/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
    )

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = json.loads(r.read().decode())
                return body['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"[gemini] rate limited, retrying in {wait}s... (attempt {attempt + 1})",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            raise

    # Should not reach here, but satisfy type checker
    raise RuntimeError("Gemini API call failed after all retries")  # pragma: no cover


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Gemini writer for hebrew-book-producer (draft + edit modes)"
    )
    parser.add_argument('--mode', required=True, choices=['draft', 'edit'],
                        help='draft: generate new prose; edit: rewrite existing prose')
    parser.add_argument('--voice', required=True,
                        help='Path to AUTHOR_VOICE.md')
    parser.add_argument('--context', required=True,
                        help='Path to context JSON file')
    args = parser.parse_args()

    profile = load_voice_profile(args.voice)
    with open(args.context, 'r', encoding='utf-8') as f:
        context = json.load(f)

    writer_cfg = profile.get("writer", {})
    model = writer_cfg.get("model", DEFAULT_MODEL)
    temperature = _coerce_float(writer_cfg.get("temperature"), DEFAULT_TEMPERATURE)
    max_tokens = _coerce_int(writer_cfg.get("max_tokens"), DEFAULT_MAX_TOKENS)
    api_key = os.environ.get('GEMINI_API_KEY')

    if args.mode == 'draft':
        system_prompt, user_prompt = build_draft_prompt(profile, context)
    else:
        system_prompt, user_prompt = build_edit_prompt(profile, context)

    result = call_gemini_api(
        system_prompt, user_prompt,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    print(result)


if __name__ == '__main__':
    main()
