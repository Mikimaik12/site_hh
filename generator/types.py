"""Структуры данных, которыми обмениваются модули генератора.

Модуль не импортирует ничего из `generator`, поэтому его можно
использовать из любой части пакета без циклических зависимостей.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .skills import SkillMatch


@dataclass
class ResumeFacts:
    """Всё, что удалось достоверно извлечь из резюме."""

    name: str = ""
    current_title: str = ""
    target_title: str = ""
    years_of_experience: Optional[int] = None
    companies: List[str] = field(default_factory=list)
    positions: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    skills_by_category: Dict[str, List[str]] = field(default_factory=dict)
    soft_skills: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    skill_matches: List[SkillMatch] = field(default_factory=list)

    @property
    def years_text(self) -> str:
        """Опыт словами, например «6 лет». Пустая строка, если опыт не найден."""
        years = self.years_of_experience
        if not years:
            return ""
        last_two = 11 <= years % 100 <= 14
        if years % 10 == 1 and not last_two:
            tail = "год"
        elif years % 10 in (2, 3, 4) and not last_two:
            tail = "года"
        else:
            tail = "лет"
        return f"{years} {tail}"

    @property
    def last_company(self) -> str:
        return self.companies[0] if self.companies else ""

    @property
    def last_position(self) -> str:
        return self.positions[0] if self.positions else ""


@dataclass
class VacancyFacts:
    """Всё, что удалось извлечь из описания вакансии."""

    title: str = ""
    company: str = ""
    required_skills: List[str] = field(default_factory=list)
    optional_skills: List[str] = field(default_factory=list)
    min_years: Optional[int] = None
    responsibilities: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)

    @property
    def all_skills(self) -> List[str]:
        return list(dict.fromkeys(self.required_skills + self.optional_skills))


@dataclass
class MatchResult:
    """Результат сопоставления резюме и вакансии.

    matched — навык есть и в резюме, и в вакансии;
    missing — навык есть только в вакансии;
    optional — «желательные» навыки вакансии (часть из них есть в резюме);
    resume_only — навыки резюме, которых в вакансии нет.
    """

    matched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    optional: List[str] = field(default_factory=list)
    optional_matched: List[str] = field(default_factory=list)
    optional_missing: List[str] = field(default_factory=list)
    resume_only: List[str] = field(default_factory=list)

    @property
    def forbidden_for_letter(self) -> List[str]:
        """Навыки, которые нельзя приписывать кандидату."""
        return list(dict.fromkeys(self.missing + self.optional_missing))

    @property
    def coverage(self) -> float:
        """Доля закрытых обязательных требований (0.0 - 1.0)."""
        total = len(self.matched) + len(self.missing)
        if not total:
            return 0.0
        return round(len(self.matched) / total, 2)


@dataclass
class GenerationResult:
    """Результат генерации письма."""

    cover_letter: str
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    optional_skills: List[str] = field(default_factory=list)
    resume_only_skills: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    profession: str = ""
    style: str = ""
    detected_profession: str = ""
    vacancy_company: str = ""
    vacancy_title: str = ""

    def to_dict(self) -> dict:
        return {
            "success": True,
            "cover_letter": self.cover_letter,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "optional_skills": self.optional_skills,
            "resume_only_skills": self.resume_only_skills,
            "warnings": self.warnings,
            "profession": self.profession,
            "style": self.style,
            "detected_profession": self.detected_profession,
            "vacancy_company": self.vacancy_company,
            "vacancy_title": self.vacancy_title,
        }

    def __getitem__(self, key: str):
        """Позволяет обращаться к результату как к словарю."""
        return self.to_dict()[key]
