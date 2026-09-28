"""Стили письма.

Стиль — это набор параметров сборки письма: сколько навыков упоминать,
какие блоки включать, какой тон и какие ограничения по длине.
Чтобы добавить новый стиль, достаточно дописать ещё одну запись
в `STYLES` - код менять не придётся.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .config import BRIEF_MAX_CHARS


@dataclass(frozen=True)
class StyleSpec:
    """Параметры стиля письма."""

    id: str
    label: str
    description: str
    max_skills: int = 6
    max_tasks: int = 2
    include_experience_block: bool = True
    include_stack_block: bool = True
    include_tasks_block: bool = True
    include_soft_skills_block: bool = True
    include_education_block: bool = True
    include_company_line: bool = True
    brief: bool = False
    enthusiasm: bool = False


STYLES: Dict[str, StyleSpec] = {
    "professional": StyleSpec(
        id="professional",
        label="Профессиональный",
        description="Спокойный деловой тон, полный набор блоков.",
        max_skills=6,
        max_tasks=2,
    ),
    "brief": StyleSpec(
        id="brief",
        label="Краткий",
        description=f"Только самое важное, {BRIEF_MAX_CHARS} символов или меньше.",
        max_skills=4,
        max_tasks=1,
        # Образование в коротком письме остаётся: это конкретный факт.
        # Soft skills - как раз та «вода», ради которой письмо раздувается.
        include_soft_skills_block=False,
        include_tasks_block=True,
        brief=True,
    ),
    "confident": StyleSpec(
        id="confident",
        label="Уверенный",
        description="Более энергичная подача без самовосхваления.",
        max_skills=7,
        max_tasks=2,
        include_company_line=True,
        enthusiasm=True,
    ),
}

DEFAULT_STYLE = "professional"


def get_style(style_id: str) -> StyleSpec:
    """Возвращает настройки стиля (для неизвестного - стиль по умолчанию)."""
    return STYLES.get((style_id or "").strip().lower(), STYLES[DEFAULT_STYLE])


def is_known_style(style_id: str) -> bool:
    """Проверяет, что стиль поддерживается."""
    return (style_id or "").strip().lower() in STYLES


def style_choices() -> Tuple[Tuple[str, str], ...]:
    """Список (id, label) для интерфейса."""
    return tuple((spec.id, spec.label) for spec in STYLES.values())
