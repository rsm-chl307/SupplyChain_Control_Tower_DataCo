"""Central display translation. Never changes canonical business data."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from string import Formatter

SUPPORTED = ('en', 'zh-TW')


@lru_cache(maxsize=4)
def _catalog(path: str, version: int) -> dict[str, str]:
    return json.loads(Path(path).read_text())


def dictionary(locale: str) -> dict[str, str]:
    name = locale if locale in SUPPORTED else 'en'
    path = Path(__file__).parent / 'locales' / f'{name}.json'
    return _catalog(str(path), path.stat().st_mtime_ns)


def current_locale() -> str:
    # Keep pure helpers usable without a running Streamlit session.
    import streamlit as st
    value = st.session_state.get('ui_locale', 'en')
    return value if value in SUPPORTED else 'en'


def t(key: str, *, locale: str | None = None, **params) -> str:
    selected = locale or current_locale()
    template = dictionary(selected).get(key, dictionary('en').get(key, f'[missing:{key}]'))
    try:
        return template.format(**params)
    except (KeyError, ValueError, TypeError):
        return f'[missing:parameters:{key}]'


def _source_keys() -> dict[str, str]:
    return {source: key for key, source in dictionary('en').items()}


def localize(source, *, locale: str | None = None) -> str:
    """Adapt owned labels stored as data; unknown/raw text remains untouched."""
    value = str(source)
    key = _source_keys().get(value)
    return t(key, locale=locale) if key else value


def diagnostic(message, *, locale: str | None = None) -> str:
    """Localized summary plus unchanged technical detail; no export adaptation."""
    value = str(message)
    keys = {'Empty cohort / unavailable rows': 'diagnostic.empty',
            'Zero denominator; rate is N/A': 'diagnostic.zero'}
    key = keys.get(value, 'diagnostic.policy' if value.startswith('POLICY_CONTRAST') else 'diagnostic.summary')
    return f'{t(key, locale=locale)}\n\n{value}'


def placeholders(template: str) -> set[str]:
    return {field for _, field, _, _ in Formatter().parse(template) if field is not None}
