"""
orchestrator/groq_pool.py

Groq API key rotation pool.
Loads up to 3 keys from the environment and cycles to the next key
automatically whenever the active key hits a rate-limit (429) or
authentication error (401/403).

Usage:
    from orchestrator.groq_pool import get_groq_client, groq_chat, groq_transcribe

    # Get a pre-built groq.Groq client (always uses the current active key)
    client = get_groq_client()

    # Or use the thin wrappers that handle rotation transparently:
    response = groq_chat(model="...", messages=[...], **kwargs)
    transcript = groq_transcribe(file=audio_bytes, model="whisper-large-v3-turbo")
"""

import os
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv
import groq

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
logger = logging.getLogger("LIBA.GroqPool")

# ── Key pool ─────────────────────────────────────────────────────────────────
_POOL = [
    k for k in [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
    ] if k
]

if not _POOL:
    raise EnvironmentError(
        "No Groq API keys found. Set GROQ_API_KEY (and optionally "
        "GROQ_API_KEY_2, GROQ_API_KEY_3) in your .env file."
    )

logger.info("[GroqPool] Loaded %d key(s).", len(_POOL))

_lock = threading.Lock()
_current_idx = 0      # index of the active key
_exhausted: set = set()   # indices of keys confirmed dead


def _active_key() -> str:
    return _POOL[_current_idx]


def _rotate(failed_idx: int) -> bool:
    """
    Mark `failed_idx` as exhausted and advance to the next available key.
    Returns True if a new key is available, False if all keys are exhausted.
    """
    global _current_idx
    with _lock:
        _exhausted.add(failed_idx)
        for offset in range(1, len(_POOL)):
            candidate = (failed_idx + offset) % len(_POOL)
            if candidate not in _exhausted:
                _current_idx = candidate
                logger.warning(
                    "[GroqPool] Key #%d failed — rotated to key #%d.",
                    failed_idx + 1, _current_idx + 1
                )
                return True
        logger.error("[GroqPool] All %d key(s) exhausted.", len(_POOL))
        return False


# ── Public helpers ────────────────────────────────────────────────────────────

def get_groq_client() -> groq.Groq:
    """Return a groq.Groq client built with the currently active key."""
    return groq.Groq(api_key=_active_key())


# Error codes that signal a key is exhausted / invalid (rotate immediately)
_ROTATE_ON = {401, 403, 429}


def groq_chat(*, model: str, messages: list, **kwargs):
    """
    Drop-in replacement for groq_client.chat.completions.create() with
    automatic key rotation on rate-limit or auth errors.

    Returns the raw Groq chat completion response object.
    Raises RuntimeError if all keys are exhausted.
    """
    for attempt in range(len(_POOL)):
        idx = _current_idx
        client = groq.Groq(api_key=_POOL[idx])
        try:
            return client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
        except groq.RateLimitError as exc:
            logger.warning("[GroqPool] Key #%d rate-limited: %s", idx + 1, exc)
            if not _rotate(idx):
                raise RuntimeError("All Groq API keys are rate-limited or exhausted.") from exc
        except groq.AuthenticationError as exc:
            logger.warning("[GroqPool] Key #%d auth error: %s", idx + 1, exc)
            if not _rotate(idx):
                raise RuntimeError("All Groq API keys are invalid.") from exc
        except groq.APIStatusError as exc:
            if exc.status_code in _ROTATE_ON:
                logger.warning("[GroqPool] Key #%d HTTP %d: %s", idx + 1, exc.status_code, exc)
                if not _rotate(idx):
                    raise RuntimeError(f"All Groq API keys returned HTTP {exc.status_code}.") from exc
            else:
                raise   # Non-key-related error — propagate immediately
    raise RuntimeError("groq_chat: exhausted all retry attempts across all keys.")


def groq_transcribe(*, file, model: str = "whisper-large-v3-turbo", **kwargs):
    """
    Drop-in replacement for groq_client.audio.transcriptions.create() with
    automatic key rotation on rate-limit or auth errors.

    `file` should be a tuple (filename, bytes, mime_type) or open file object,
    exactly as accepted by the groq SDK.

    Returns the raw Groq transcription response object.
    """
    for attempt in range(len(_POOL)):
        idx = _current_idx
        client = groq.Groq(api_key=_POOL[idx])
        try:
            return client.audio.transcriptions.create(
                file=file, model=model, **kwargs
            )
        except groq.RateLimitError as exc:
            logger.warning("[GroqPool] STT key #%d rate-limited: %s", idx + 1, exc)
            if not _rotate(idx):
                raise RuntimeError("All Groq keys are rate-limited for STT.") from exc
        except groq.AuthenticationError as exc:
            logger.warning("[GroqPool] STT key #%d auth error: %s", idx + 1, exc)
            if not _rotate(idx):
                raise RuntimeError("All Groq keys are invalid for STT.") from exc
        except groq.APIStatusError as exc:
            if exc.status_code in _ROTATE_ON:
                logger.warning("[GroqPool] STT key #%d HTTP %d: %s", idx + 1, exc.status_code, exc)
                if not _rotate(idx):
                    raise RuntimeError(f"All Groq STT keys returned HTTP {exc.status_code}.") from exc
            else:
                raise
    raise RuntimeError("groq_transcribe: exhausted all retry attempts across all keys.")


def pool_status() -> dict:
    """Return a snapshot of the pool state (useful for logging/debugging)."""
    return {
        "total_keys": len(_POOL),
        "active_key_index": _current_idx + 1,
        "exhausted_keys": [i + 1 for i in _exhausted],
        "active_key_prefix": _POOL[_current_idx][:12] + "...",
    }
