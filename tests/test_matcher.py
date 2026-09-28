"""Тесты сопоставления навыков (`generator.matcher`).

Главное правило: навык из вакансии, которого нет в резюме, не должен
попасть в `matched` и не должен использоваться в письме.
"""

from __future__ import annotations

import unittest

from generator.analyzer import analyze_resume, analyze_vacancy
from generator.matcher import match_skills
from generator.types import MatchResult

from .fixtures import (
    BACKEND_RESUME,
    BACKEND_VACANCY,
    CANONICAL_RESUME,
    CANONICAL_VACANCY,
    FRONTEND_RESUME,
    FRONTEND_VACANCY,
    MANUAL_QA_RESUME,
    MANUAL_QA_VACANCY,
)


def build(resume_text: str, vacancy_text: str) -> MatchResult:
    return match_skills(analyze_resume(resume_text), analyze_vacancy(vacancy_text))


class MatchSkillsTest(unittest.TestCase):
    def test_canonical_case(self):
        """Резюме «Python, Django, PostgreSQL» против вакансии с Docker."""
        result = build(CANONICAL_RESUME, CANONICAL_VACANCY)
        self.assertEqual(result.matched, ["Python", "Django", "PostgreSQL", "SQL"])
        self.assertIn("Docker", result.missing)
        self.assertNotIn("Docker", result.matched)

    def test_missing_never_leaks_into_matched(self):
        for resume_text, vacancy_text in (
            (CANONICAL_RESUME, CANONICAL_VACANCY),
            (BACKEND_RESUME, BACKEND_VACANCY),
            (FRONTEND_RESUME, FRONTEND_VACANCY),
            (MANUAL_QA_RESUME, MANUAL_QA_VACANCY),
        ):
            result = build(resume_text, vacancy_text)
            for skill in result.missing:
                self.assertNotIn(skill, result.matched, msg=f"{skill} попал и туда, и сюда")
                self.assertNotIn(skill, result.optional_matched)

    def test_sets_are_disjoint(self):
        result = build(BACKEND_RESUME, BACKEND_VACANCY)
        self.assertFalse(set(result.matched) & set(result.missing))
        self.assertFalse(set(result.matched) & set(result.optional))
        self.assertFalse(set(result.optional_matched) & set(result.optional_missing))

    def test_matched_is_subset_of_vacancy(self):
        result = build(BACKEND_RESUME, BACKEND_VACANCY)
        vacancy_skills = set(analyze_vacancy(BACKEND_VACANCY).all_skills)
        for skill in result.matched:
            self.assertIn(skill, vacancy_skills)

    def test_optional_split(self):
        result = build(BACKEND_RESUME, BACKEND_VACANCY)
        # Redis есть и в резюме, и в желательных требованиях.
        self.assertIn("Redis", result.optional)
        self.assertIn("Redis", result.optional_matched)
        # Kubernetes в резюме нет.
        self.assertIn("Kubernetes", result.optional_missing)

    def test_resume_only(self):
        result = build(BACKEND_RESUME, BACKEND_VACANCY)
        # Jenkins есть в резюме, но не в вакансии.
        self.assertIn("Jenkins", result.resume_only)
        self.assertNotIn("Python", result.resume_only)

    def test_forbidden_for_letter(self):
        result = build(CANONICAL_RESUME, CANONICAL_VACANCY)
        forbidden = result.forbidden_for_letter
        self.assertIn("Docker", forbidden)
        self.assertNotIn("Python", forbidden)
        self.assertNotIn("Django", forbidden)

    def test_coverage(self):
        result = build(CANONICAL_RESUME, CANONICAL_VACANCY)
        self.assertGreater(result.coverage, 0.0)
        self.assertLess(result.coverage, 1.0)
        self.assertEqual(build(BACKEND_RESUME, BACKEND_VACANCY).coverage, 1.0)

    def test_coverage_without_requirements(self):
        result = build("Python, Django, PostgreSQL, Docker, Linux, SQL, Git", "Вакансия: Backend Developer")
        self.assertEqual(result.coverage, 0.0)

    def test_optional_limit(self):
        vacancy = analyze_vacancy(BACKEND_VACANCY)
        resume = analyze_resume(BACKEND_RESUME)
        result = match_skills(resume, vacancy, optional_limit=1)
        self.assertEqual(len(result.optional), 1)

    def test_no_skills_anywhere(self):
        result = match_skills(analyze_resume("Иван Петров, опыт 5 лет"), analyze_vacancy("Вакансия: Менеджер"))
        self.assertEqual(result.matched, [])
        self.assertEqual(result.missing, [])
        self.assertEqual(result.coverage, 0.0)

    def test_no_duplicates(self):
        result = build("Python, Python, Django", "Python, Django, Python")
        self.assertEqual(result.matched, ["Python", "Django"])


if __name__ == "__main__":
    unittest.main()
