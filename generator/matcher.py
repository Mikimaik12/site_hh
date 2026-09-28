"""Сопоставление навыков резюме и вакансии.

Главное правило модуля: навык из вакансии, которого нет в резюме,
никогда не должен попасть в `matched`. Только `matched` и `optional_matched`
разрешено упоминать в письме как опыт кандидата.
"""

from __future__ import annotations

from typing import List, Optional

from .types import MatchResult, ResumeFacts, VacancyFacts


def match_skills(
    resume: ResumeFacts,
    vacancy: VacancyFacts,
    optional_limit: Optional[int] = None,
) -> MatchResult:
    """Сравнивает навыки резюме и вакансии.

    Аргументы:
        resume:      факты, извлечённые из резюме;
        vacancy:     факты, извлечённые из вакансии;
        optional_limit: максимум «желательных» навыков в результате.
    """
    resume_skills = list(dict.fromkeys(resume.skills))
    resume_set = set(resume_skills)
    vacancy_required = list(dict.fromkeys(vacancy.required_skills))
    vacancy_optional = list(dict.fromkeys(vacancy.optional_skills))

    matched = [skill for skill in vacancy_required if skill in resume_set]
    missing = [skill for skill in vacancy_required if skill not in resume_set]

    optional = vacancy_optional
    if optional_limit is not None:
        optional = optional[:optional_limit]
    optional_matched = [skill for skill in optional if skill in resume_set]
    optional_missing = [skill for skill in optional if skill not in resume_set]

    resume_only = [skill for skill in resume_skills if skill not in set(vacancy_required) | set(optional)]

    return MatchResult(
        matched=matched,
        missing=missing,
        optional=optional,
        optional_matched=optional_matched,
        optional_missing=optional_missing,
        resume_only=resume_only,
    )
