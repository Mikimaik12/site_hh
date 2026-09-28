"""Локальный генератор сопроводительных писем для IT-вакансий.

Пакет полностью автономен: работает на Python 3.11+, использует только
стандартную библиотеку и не обращается ни к одному внешнему сервису.

Быстрый старт:
    from generator import generate_cover_letter

    result = generate_cover_letter(
        resume_text="Python, Django, PostgreSQL",
        vacancy_text="Python, Django, PostgreSQL, Docker",
        profession="backend",
        style="professional",
    )
    print(result.cover_letter)
    print(result.matched_skills)   # ['Python', 'Django', 'PostgreSQL', 'SQL']
    print(result.missing_skills)   # ['Docker']
"""

from __future__ import annotations

from .analyzer import analyze_resume, analyze_vacancy, detect_profession
from .config import (
    BRIEF_MAX_CHARS,
    BRIEF_MIN_CHARS,
    MAX_INPUT_CHARS,
    MIN_INPUT_CHARS,
    RECOMMENDED_INPUT_CHARS,
)
from .generator import (
    ValidationError,
    generate_cover_letter,
    generate_cover_letter_dict,
    verify_cover_letter,
)
from .matcher import match_skills
from .professions import (
    DEFAULT_PROFESSION,
    PROFESSIONS,
    get_profession,
    is_known_profession,
    list_professions,
)
from .skills import known_skill_names
from .styles import STYLES, get_style, is_known_style, style_choices
from .types import GenerationResult, MatchResult, ResumeFacts, VacancyFacts

__version__ = "1.0.0"

__all__ = [
    "BRIEF_MAX_CHARS",
    "BRIEF_MIN_CHARS",
    "DEFAULT_PROFESSION",
    "GenerationResult",
    "MatchResult",
    "MAX_INPUT_CHARS",
    "MIN_INPUT_CHARS",
    "PROFESSIONS",
    "RECOMMENDED_INPUT_CHARS",
    "ResumeFacts",
    "STYLES",
    "VacancyFacts",
    "ValidationError",
    "__version__",
    "analyze_resume",
    "analyze_vacancy",
    "detect_profession",
    "generate_cover_letter",
    "generate_cover_letter_dict",
    "get_profession",
    "get_style",
    "is_known_profession",
    "is_known_style",
    "known_skill_names",
    "list_professions",
    "match_skills",
    "style_choices",
    "verify_cover_letter",
]
