"""Утилиты для работы с текстом: нормализация, токенизация, склейка списков.

Модуль полностью локальный: используются только стандартная библиотека
и регулярные выражения. Никаких внешних сервисов.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Sequence

#: Символы, которые встречаются в тексте вместо обычных дефисов.
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

#: Кавычки разных сортов.
_QUOTES_LEFT = "\u00ab\u201c\u201e\u2018\u2019\u201b"
_QUOTES_RIGHT = "\u00bb\u201d\u201f\u201a\u201c\u201d"

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"[ \t\u00a0\u2007\u202f]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")
_WORD_RE = re.compile(r"[\w+#./-]+", re.UNICODE)
_BULLET_RE = re.compile(r"^\s*(?:[-*\u2022\u2013\u2014\u00b7\u25aa\u25cf]|\d{1,2}[.)])\s+")


def normalize_text(text: str) -> str:
    """Приводит текст к единому виду: чистит HTML, нормализует пробелы и кавычки.

    Переводы строк сохраняются — по ним мы определяем разделы резюме.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HTML_TAG_RE.sub(" ", text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    for dash in _DASHES:
        text = text.replace(dash, "-")
    for quote in _QUOTES_LEFT:
        text = text.replace(quote, "\"")
    for quote in _QUOTES_RIGHT:
        text = text.replace(quote, "\"")
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def normalize_inline(text: str) -> str:
    """Нормализует текст и схлопывает его в одну строку (для regex-поиска)."""
    return re.sub(r"\s+", " ", normalize_text(text)).strip()


def to_lower(text: str) -> str:
    """Регистронезависимое сравнение с учётом кириллицы и латиницы."""
    return (text or "").lower().replace("\u0451", "\u0435")


def strip_bullet(line: str) -> str:
    """Убирает маркер списка в начале строки."""
    return _BULLET_RE.sub("", line or "").strip()


def iter_lines(text: str) -> List[str]:
    """Возвращает непустые строки текста без маркеров списка."""
    result = []
    for raw in normalize_text(text).split("\n"):
        line = strip_bullet(raw)
        if line:
            result.append(line)
    return result


def split_sentences(text: str) -> List[str]:
    """Делит текст на предложения (простой rule-based сплиттер)."""
    text = normalize_inline(text)
    if not text:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def first_sentences(text: str, count: int) -> str:
    """Берёт первые N предложений из текста."""
    return " ".join(split_sentences(text)[:count])


def word_count(text: str) -> int:
    """Количество слов в тексте."""
    return len(_WORD_RE.findall(normalize_inline(text)))


def truncate(text: str, limit: int, ellipsis: str = "\u2026") -> str:
    """Обрезает текст по границе слова."""
    text = normalize_inline(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit * 0.6:
        cut = cut[:space]
    return cut.rstrip(" ,;:-") + ellipsis


def clean_fragment(text: str, limit: int = 110) -> str:
    """Готовит короткий фрагмент из чужого текста для цитирования в письме.

    Убирает висящие запятые/точки и обрезает по словам.
    """
    fragment = normalize_inline(text).strip()
    fragment = fragment.rstrip(" ,;:-.")
    if not fragment:
        return ""
    return truncate(fragment, limit, ellipsis="")


def join_natural(items: Sequence[str], conjunction: str = "и") -> str:
    """Склеивает список по-русски: «Python, Django и PostgreSQL»."""
    items = [item for item in (i.strip() for i in items) if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" {conjunction} " + items[-1]


def dedupe(items: Iterable[str]) -> List[str]:
    """Убирает повторы, сохраняя порядок."""
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result

