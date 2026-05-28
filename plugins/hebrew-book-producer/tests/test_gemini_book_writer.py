#!/usr/bin/env python3
"""
Unit tests for scripts/gemini_book_writer.py

Run:
  python3 -m unittest tests/test_gemini_book_writer.py
  # or from plugin root:
  python3 -m unittest plugins/hebrew-book-producer/tests/test_gemini_book_writer.py
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Allow import from scripts/ regardless of cwd
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), 'scripts')
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from gemini_book_writer import (
    load_voice_profile,
    build_draft_prompt,
    build_edit_prompt,
    call_gemini_api,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VOICE_WITH_ACTIVE_WRITER = """\
> Updated 2026-05-28 by hebrew-book-producer
> Status: complete

# Voice Profile — Test Author

## Core voice

Write with clarity and intellectual rigour.

## Non-fiction-book-specific

Open each chapter with a concrete question.

## Writer Configuration

writer:
  provider: "gemini"
  model: "gemini-2.5-flash"
  temperature: 0.8
  max_tokens: 2500
"""

VOICE_WITH_COMMENTED_WRITER = """\
> Updated 2026-05-28 by hebrew-book-producer
> Status: seed

# Voice Profile — Test Author

## Core voice

Write with clarity.

## Writer Configuration

_Empty. Set during voice setup._

<!--
writer:
  provider: "gemini"
  model: "gemini-2.5-flash"
  temperature: 0.7
  max_tokens: 3000
-->
"""

VOICE_NO_WRITER_SECTION = """\
> Updated 2026-05-28 by hebrew-book-producer
> Status: seed

# Voice Profile — Test Author

## Core voice

Write with clarity.

## Non-fiction-book-specific

Open with a question.
"""

DRAFT_CONTEXT = {
    "chapter_brief": "This chapter discusses the concept of תשובה in medieval Jewish philosophy.",
    "sefaria_sources": [
        {"ref": "Rambam, Mishneh Torah, Laws of Repentance 1:1",
         "text": "כל המצוות שבתורה, בין עשה בין לא תעשה"},
    ],
    "section_index": 0,
    "word_ceiling": 300,
    "language": "he",
}

EDIT_CONTEXT = {
    "original_text": "הרמב\"ם קובע כי התשובה היא יסוד היסודות.",
    "edit_instructions": "Strengthen the transition. Add a causal link to the next paragraph.",
    "constraints": ["preserve all citations", "keep paragraph count"],
    "language": "he",
}


# ---------------------------------------------------------------------------
# Tests: load_voice_profile
# ---------------------------------------------------------------------------

class TestLoadVoiceProfile(unittest.TestCase):

    def _write_temp(self, content: str) -> str:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         encoding='utf-8', delete=False) as f:
            f.write(content)
            return f.name

    def test_active_writer_block_parsed(self):
        path = self._write_temp(VOICE_WITH_ACTIVE_WRITER)
        try:
            profile = load_voice_profile(path)
            cfg = profile['writer']
            self.assertEqual(cfg['provider'], 'gemini')
            self.assertEqual(cfg['model'], 'gemini-2.5-flash')
            self.assertAlmostEqual(cfg['temperature'], 0.8)
            self.assertEqual(cfg['max_tokens'], 2500)
        finally:
            os.unlink(path)

    def test_commented_writer_block_defaults_to_claude(self):
        path = self._write_temp(VOICE_WITH_COMMENTED_WRITER)
        try:
            profile = load_voice_profile(path)
            cfg = profile['writer']
            self.assertEqual(cfg['provider'], 'claude',
                             "Commented-out writer block must resolve to provider=claude")
        finally:
            os.unlink(path)

    def test_no_writer_section_defaults_to_claude(self):
        path = self._write_temp(VOICE_NO_WRITER_SECTION)
        try:
            profile = load_voice_profile(path)
            cfg = profile['writer']
            self.assertEqual(cfg['provider'], 'claude')
            self.assertEqual(cfg['model'], DEFAULT_MODEL)
            self.assertAlmostEqual(cfg['temperature'], DEFAULT_TEMPERATURE)
            self.assertEqual(cfg['max_tokens'], DEFAULT_MAX_TOKENS)
        finally:
            os.unlink(path)

    def test_raw_text_preserved(self):
        path = self._write_temp(VOICE_WITH_ACTIVE_WRITER)
        try:
            profile = load_voice_profile(path)
            self.assertIn('## Core voice', profile['raw'])
            self.assertIn('## Non-fiction-book-specific', profile['raw'])
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_voice_profile('/nonexistent/path/AUTHOR_VOICE.md')


# ---------------------------------------------------------------------------
# Tests: build_draft_prompt
# ---------------------------------------------------------------------------

class TestBuildDraftPrompt(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                          encoding='utf-8', delete=False) as f:
            f.write(VOICE_WITH_ACTIVE_WRITER)
            self._voice_path = f.name
        self.profile = load_voice_profile(self._voice_path)

    def tearDown(self):
        os.unlink(self._voice_path)

    def test_system_prompt_includes_voice_rules(self):
        sys_p, _ = build_draft_prompt(self.profile, DRAFT_CONTEXT)
        self.assertIn('Write Hebrew non-fiction book prose', sys_p)
        self.assertIn('Core voice', sys_p)

    def test_system_prompt_includes_word_ceiling(self):
        sys_p, _ = build_draft_prompt(self.profile, DRAFT_CONTEXT)
        self.assertIn('300', sys_p)

    def test_system_prompt_forbids_invented_citations(self):
        sys_p, _ = build_draft_prompt(self.profile, DRAFT_CONTEXT)
        lower = sys_p.lower()
        self.assertTrue(
            'do not invent' in lower or 'sefaria-verified' in lower,
            "System prompt must instruct Gemini not to invent citations"
        )

    def test_user_prompt_includes_sefaria_sources(self):
        _, user_p = build_draft_prompt(self.profile, DRAFT_CONTEXT)
        self.assertIn('Rambam', user_p)
        self.assertIn('Laws of Repentance', user_p)

    def test_user_prompt_includes_chapter_brief(self):
        _, user_p = build_draft_prompt(self.profile, DRAFT_CONTEXT)
        self.assertIn('תשובה', user_p)

    def test_section_index_in_user_prompt(self):
        _, user_p = build_draft_prompt(self.profile, DRAFT_CONTEXT)
        self.assertIn('section 1', user_p)

    def test_no_sefaria_sources(self):
        ctx = {**DRAFT_CONTEXT, 'sefaria_sources': []}
        _, user_p = build_draft_prompt(self.profile, ctx)
        self.assertNotIn('Verified Sources', user_p)


# ---------------------------------------------------------------------------
# Tests: build_edit_prompt
# ---------------------------------------------------------------------------

class TestBuildEditPrompt(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                          encoding='utf-8', delete=False) as f:
            f.write(VOICE_WITH_ACTIVE_WRITER)
            self._voice_path = f.name
        self.profile = load_voice_profile(self._voice_path)

    def tearDown(self):
        os.unlink(self._voice_path)

    def test_system_prompt_execute_edit_precisely(self):
        sys_p, _ = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn('Execute this specific edit precisely', sys_p)

    def test_system_prompt_preserve_citations(self):
        sys_p, _ = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn('Preserve all citations', sys_p)

    def test_system_prompt_includes_voice_rules(self):
        sys_p, _ = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn('Core voice', sys_p)

    def test_system_prompt_return_only_rewritten_text(self):
        sys_p, _ = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn('Return ONLY the rewritten text', sys_p)

    def test_user_prompt_includes_original_text(self):
        _, user_p = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn(EDIT_CONTEXT['original_text'], user_p)

    def test_user_prompt_includes_edit_instructions(self):
        _, user_p = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn('Strengthen the transition', user_p)

    def test_constraints_in_system_prompt(self):
        sys_p, _ = build_edit_prompt(self.profile, EDIT_CONTEXT)
        self.assertIn('keep paragraph count', sys_p)

    def test_no_constraints(self):
        ctx = {**EDIT_CONTEXT, 'constraints': []}
        sys_p, _ = build_edit_prompt(self.profile, ctx)
        # Should still build without error
        self.assertIn('Execute this specific edit precisely', sys_p)


# ---------------------------------------------------------------------------
# Tests: call_gemini_api
# ---------------------------------------------------------------------------

class TestCallGeminiApi(unittest.TestCase):

    def _make_response_body(self, text: str) -> bytes:
        body = {
            "candidates": [
                {"content": {"parts": [{"text": text}]}}
            ]
        }
        return json.dumps(body).encode()

    def test_success_returns_text(self):
        mock_response = MagicMock()
        mock_response.read.return_value = self._make_response_body("שלום עולם")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = call_gemini_api(
                "sys", "user",
                model=DEFAULT_MODEL,
                api_key="test-key",
                temperature=0.7,
                max_tokens=1000,
            )
        self.assertEqual(result, "שלום עולם")

    def test_missing_api_key_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            call_gemini_api(
                "sys", "user",
                model=DEFAULT_MODEL,
                api_key=None,
                temperature=0.7,
                max_tokens=1000,
            )
        self.assertIn('GEMINI_API_KEY', str(ctx.exception))

    def test_retry_on_429(self):
        import urllib.error

        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise urllib.error.HTTPError(
                    url=None, code=429, msg='Too Many Requests',
                    hdrs=None, fp=None
                )
            mock_response = MagicMock()
            mock_response.read.return_value = self._make_response_body("retry worked")
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            with patch('time.sleep'):  # don't actually sleep
                result = call_gemini_api(
                    "sys", "user",
                    model=DEFAULT_MODEL,
                    api_key="test-key",
                    temperature=0.7,
                    max_tokens=1000,
                )
        self.assertEqual(result, "retry worked")
        self.assertEqual(call_count, 2)

    def test_non_429_http_error_raises(self):
        import urllib.error

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                url=None, code=500, msg='Internal Server Error',
                hdrs=None, fp=None
            )

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                call_gemini_api(
                    "sys", "user",
                    model=DEFAULT_MODEL,
                    api_key="test-key",
                    temperature=0.7,
                    max_tokens=1000,
                )
            self.assertEqual(ctx.exception.code, 500)

    def test_api_key_in_header_not_url(self):
        """API key should be sent as x-goog-api-key header, not in the URL."""
        captured_requests = []

        mock_response = MagicMock()
        mock_response.read.return_value = self._make_response_body("ok")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        def capturing_urlopen(req, timeout=None):
            captured_requests.append(req)
            return mock_response

        with patch('urllib.request.urlopen', side_effect=capturing_urlopen):
            call_gemini_api(
                "sys", "user",
                model=DEFAULT_MODEL,
                api_key="my-secret-key",
                temperature=0.7,
                max_tokens=1000,
            )

        self.assertEqual(len(captured_requests), 1)
        req = captured_requests[0]
        # Key must be in header
        self.assertEqual(req.get_header('X-goog-api-key'), 'my-secret-key')
        # Key must NOT be in URL query string
        self.assertNotIn('my-secret-key', req.full_url)


if __name__ == '__main__':
    unittest.main()
