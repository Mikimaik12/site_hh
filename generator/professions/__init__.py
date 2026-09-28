"""Реестр профессий.

Профессии подгружаются автоматически из всех модулей этой папки, поэтому
для добавления нового направления достаточно создать рядом ещё один
`.py`-файл с объектом `PROFESSION` и функцией `build_paragraphs(ctx)`.
Никаких правок в других файлах не требуется.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Callable, Dict, List, Tuple

from .base import LetterContext, Profession

#: Порядок карточек в интерфейсе.
PROFESSION_ORDER: Tuple[str, ...] = ("backend", "frontend", "manual_qa", "automation_qa")

ParagraphBuilder = Callable[[LetterContext], List[str]]


def _load_all() -> Tuple[Dict[str, Profession], Dict[str, ParagraphBuilder]]:
    """Импортирует модули папки и собирает профессии и их сборщики абзацев."""
    professions: Dict[str, Profession] = {}
    builders: Dict[str, ParagraphBuilder] = {}
    for module_info in sorted(pkgutil.iter_modules(__path__), key=lambda item: item.name):
        if module_info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        profession = getattr(module, "PROFESSION", None)
        builder = getattr(module, "build_paragraphs", None)
        if profession is None or builder is None:
            continue
        professions[profession.id] = profession
        builders[profession.id] = builder
    return professions, builders


_ALL_PROFESSIONS, _BUILDERS = _load_all()

#: Все доступные профессии в порядке отображения в интерфейсе.
PROFESSIONS: Dict[str, Profession] = {
    **{key: _ALL_PROFESSIONS[key] for key in PROFESSION_ORDER if key in _ALL_PROFESSIONS},
    **{key: value for key, value in _ALL_PROFESSIONS.items() if key not in PROFESSION_ORDER},
}

DEFAULT_PROFESSION: str = PROFESSION_ORDER[0]


def get_profession(profession_id: str) -> Profession:
    """Возвращает профессию по id (для неизвестного - направление по умолчанию)."""
    return PROFESSIONS.get((profession_id or "").strip().lower(), PROFESSIONS[DEFAULT_PROFESSION])


def is_known_profession(profession_id: str) -> bool:
    """Проверяет, что направление поддерживается."""
    return (profession_id or "").strip().lower() in PROFESSIONS


def list_professions() -> Tuple[Profession, ...]:
    """Список профессий для интерфейса."""
    return tuple(PROFESSIONS.values())


def build_paragraphs(ctx: LetterContext) -> List[str]:
    """Собирает абзацы письма для профессии из контекста."""
    return _BUILDERS[ctx.profession.id](ctx)


__all__ = [
    "LetterContext",
    "PROFESSIONS",
    "PROFESSION_ORDER",
    "DEFAULT_PROFESSION",
    "Profession",
    "build_paragraphs",
    "get_profession",
    "is_known_profession",
    "list_professions",
]
