"""
Simple JSON-file based translation system.

Usage:
    from app.utils.translations import t
    t("main_menu", lang="fa")
    t("locked_content", lang="en", price="200,000", currency="IRT")
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import config


@lru_cache(maxsize=None)
def _load_locale(lang: str) -> dict:
    path = Path(config.LOCALES_DIR) / f"{lang}.json"
    if not path.exists():
        raise FileNotFoundError(f"Locale file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate `key` into `lang` (falls back to default language, then to the key itself)."""
    lang = lang if lang in config.SUPPORTED_LANGUAGES else config.DEFAULT_LANGUAGE
    data = _load_locale(lang)
    text = data.get(key)
    if text is None:
        # fall back to default language, then to the raw key so missing
        # translations never crash a handler.
        fallback = _load_locale(config.DEFAULT_LANGUAGE)
        text = fallback.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def field_for_lang(obj, base_field: str, lang: str) -> str:
    """Read `<base_field>_fa` / `<base_field>_en` off a model instance based on lang."""
    value = getattr(obj, f"{base_field}_{lang}", None)
    if value:
        return value
    # fall back to the other language rather than showing nothing
    other = "en" if lang == "fa" else "fa"
    return getattr(obj, f"{base_field}_{other}", None) or ""
