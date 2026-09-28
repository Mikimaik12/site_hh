"""Тесты анализатора резюме и вакансии (`generator.analyzer`)."""

from __future__ import annotations

import unittest

from generator import list_professions
from generator.analyzer import analyze_resume, analyze_vacancy, detect_profession
from generator.types import ResumeFacts, VacancyFacts

from .fixtures import (
    AUTOMATION_QA_RESUME,
    AUTOMATION_QA_VACANCY,
    BACKEND_RESUME,
    BACKEND_VACANCY,
    CANONICAL_RESUME,
    CANONICAL_VACANCY,
    FRONTEND_RESUME,
    FRONTEND_VACANCY,
    MANUAL_QA_RESUME,
    MANUAL_QA_VACANCY,
    RESUME_WITHOUT_SKILLS,
)


class AnalyzeResumeTest(unittest.TestCase):
    def setUp(self):
        self.facts = analyze_resume(BACKEND_RESUME)

    def test_returns_resume_facts(self):
        self.assertIsInstance(self.facts, ResumeFacts)

    def test_name(self):
        self.assertEqual(self.facts.name, "Иван Петров")

    def test_current_title(self):
        self.assertEqual(self.facts.current_title, "Backend Developer")

    def test_years_and_years_text(self):
        self.assertEqual(self.facts.years_of_experience, 6)
        self.assertEqual(self.facts.years_text, "6 лет")

    def test_companies_and_positions(self):
        self.assertIn("Acme Tech", self.facts.companies)
        self.assertIn("Ромашка", self.facts.companies)
        self.assertIn("Senior Backend Developer", self.facts.positions)
        self.assertEqual(self.facts.last_company, "Acme Tech")
        self.assertEqual(self.facts.last_position, "Senior Backend Developer")

    def test_skills(self):
        for name in ("Python", "Django", "PostgreSQL", "Docker", "Git", "Jenkins", "REST API"):
            self.assertIn(name, self.facts.skills)

    def test_skills_by_category(self):
        self.assertIn("Python", self.facts.skills_by_category.get("language", []))
        self.assertIn("Django", self.facts.skills_by_category.get("framework", []))

    def test_soft_skills(self):
        self.assertIn("работа в команде", self.facts.soft_skills)
        self.assertIn("ответственность", self.facts.soft_skills)

    def test_education(self):
        self.assertTrue(self.facts.education)
        self.assertIn("МГТУ", self.facts.education[0])

    def test_education_heading_alone_is_not_fact(self):
        facts = analyze_resume("Иван Петров\nОбразование\n")
        self.assertEqual(facts.education, [])

    def test_years_plural_forms(self):
        self.assertEqual(analyze_resume("Опыт работы: 1 год").years_text, "1 год")
        self.assertEqual(analyze_resume("Опыт работы: 3 года").years_text, "3 года")
        self.assertEqual(analyze_resume("Опыт работы: 11 лет").years_text, "11 лет")

    def test_body_line_does_not_break_experience_section(self):
        # «веду проекты ...» - обычный текст, а не конец раздела.
        facts = analyze_resume(RESUME_WITHOUT_SKILLS)
        self.assertEqual(facts.companies, [])
        self.assertEqual(facts.positions, [])

    def test_company_not_taken_from_name_line(self):
        facts = analyze_resume("Пётр Сидоров\nДолжность: QA Engineer\n")
        self.assertEqual(facts.name, "Пётр Сидоров")
        self.assertEqual(facts.companies, [])

    def test_title_line_is_not_mistaken_for_name(self):
        """В резюме первой строкой идёт должность, имя - следом."""
        facts = analyze_resume("Backend Developer\nИван Петров\nОпыт 6 лет\n\nPython, Django.")
        self.assertEqual(facts.name, "Иван Петров")

    def test_job_title_is_not_used_as_company(self):
        """Без раздела опыта должность не должна превращаться в компанию."""
        facts = analyze_resume("Backend Developer\nИван Петров\nОпыт 6 лет\n\nPython, Django.")
        self.assertEqual(facts.companies, [])
        self.assertEqual(facts.last_company, "")

    def test_company_named_inside_a_sentence(self):
        """«Работал в компании Acme на позиции X» - типичная строка опыта."""
        facts = analyze_resume(
            "Иван Петров\n"
            "Работал в компании Acme на позиции Backend Developer 3 года.\n"
            "В SoftLab 3 года.\n"
        )
        self.assertEqual(facts.companies, ["Acme", "SoftLab"])
        self.assertEqual(facts.positions, ["Backend Developer"])

    def test_duration_is_not_part_of_company_name(self):
        facts = analyze_resume("Пётр Сидоров\nВ Acme Labs 2 года.\n")
        self.assertEqual(facts.companies, ["Acme Labs"])

    def test_company_after_verb_without_word_company(self):
        """«Работал в СофтЛаб на позиции X» - без слова «компании»."""
        facts = analyze_resume(
            "Дмитрий Орлов\n"
            "Работал в СофтЛаб на позиции QA Automation Engineer.\n"
        )
        self.assertEqual(facts.companies, ["СофтЛаб"])
        self.assertEqual(facts.positions, ["QA Automation Engineer"])

    def test_skill_is_not_mistaken_for_employer(self):
        facts = analyze_resume("Иван Петров\nРаботал в Python 2 года.\n")
        self.assertEqual(facts.companies, [])

    def test_education_label_is_not_duplicated(self):
        facts = analyze_resume("Иван Петров\nОбразование: высшее, МГТУ, 2018\n")
        self.assertEqual(facts.education, ["высшее, МГТУ, 2018"])

    def test_education_does_not_repeat_the_word_education(self):
        """«Высшее образование, МГТУ» -> «высшее, МГТУ».

        Иначе письмо читается как «Образование: Высшее образование, МГТУ».
        """
        cases = {
            "Высшее образование, МГТУ, 2016": "Высшее, МГТУ, 2016",
            "Образование: высшее, МГТУ, 2018": "высшее, МГТУ, 2018",
            "Высшее профессиональное образование, СПбГУ, 2020": "Высшее, СПбГУ, 2020",
            "Бакалавр, МГТУ, 2018": "Бакалавр, МГТУ, 2018",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                facts = analyze_resume(f"Иван Петров\n{source}\n")
                self.assertEqual(facts.education, [expected])

    def test_empty_text(self):
        facts = analyze_resume("")
        self.assertEqual(facts.name, "")
        self.assertEqual(facts.skills, [])
        self.assertIsNone(facts.years_of_experience)


class AnalyzeVacancyTest(unittest.TestCase):
    def setUp(self):
        self.facts = analyze_vacancy(BACKEND_VACANCY)

    def test_returns_vacancy_facts(self):
        self.assertIsInstance(self.facts, VacancyFacts)

    def test_title(self):
        self.assertEqual(self.facts.title, "Backend Developer")

    def test_company(self):
        self.assertEqual(self.facts.company, "Айти Парк")

    def test_required_skills(self):
        for name in ("Python", "Django", "PostgreSQL", "Docker", "Linux", "Git", "REST API", "SQL"):
            self.assertIn(name, self.facts.required_skills)

    def test_optional_skills(self):
        for name in ("Kubernetes", "Kafka", "Redis"):
            self.assertIn(name, self.facts.optional_skills)
        # Обязательные не должны дублироваться в желательных.
        self.assertFalse(set(self.facts.required_skills) & set(self.facts.optional_skills))

    def test_min_years(self):
        self.assertEqual(self.facts.min_years, 3)

    def test_responsibilities(self):
        self.assertTrue(self.facts.responsibilities)
        self.assertTrue(any("REST API" in item for item in self.facts.responsibilities))

    def test_requirements(self):
        self.assertTrue(self.facts.requirements)

    def test_all_skills(self):
        combined = self.facts.all_skills
        self.assertIn("Docker", combined)
        self.assertIn("Kubernetes", combined)
        self.assertEqual(len(combined), len(set(combined)))

    def test_company_is_not_invented(self):
        facts = analyze_vacancy("Требуется Backend Developer. Python, Django, PostgreSQL.")
        self.assertEqual(facts.company, "")
        self.assertEqual(facts.title, "Backend Developer")

    def test_company_in_prepositional_case(self):
        """«Вакансия X в компании Y» - самый частый формат заголовка."""
        facts = analyze_vacancy("Вакансия Backend Developer в компании Acme.\nТребования: Python.")
        self.assertEqual(facts.company, "Acme")
        self.assertEqual(facts.title, "Backend Developer")

    def test_title_does_not_swallow_company_clause(self):
        facts = analyze_vacancy("Backend Developer, компания Acme.\nТребования: Python.")
        self.assertEqual(facts.company, "Acme")
        self.assertEqual(facts.title, "Backend Developer")

    def test_no_headings_falls_back_to_whole_text(self):
        facts = analyze_vacancy("Python, Django, PostgreSQL, Docker")
        self.assertIn("Python", facts.required_skills)
        self.assertIn("Docker", facts.required_skills)
        self.assertEqual(facts.optional_skills, [])

    def test_derived_skill_names_are_hidden(self):
        facts = analyze_vacancy("Docker")
        self.assertIn("Docker", facts.required_skills)
        self.assertNotIn("Version Control", facts.required_skills)


class DetectProfessionTest(unittest.TestCase):
    def test_detects_each_profession(self):
        professions = list_professions()
        self.assertEqual(detect_profession(BACKEND_VACANCY, professions), "backend")
        self.assertEqual(detect_profession(FRONTEND_VACANCY, professions), "frontend")
        self.assertEqual(detect_profession(MANUAL_QA_VACANCY, professions), "manual_qa")
        self.assertEqual(detect_profession(AUTOMATION_QA_VACANCY, professions), "automation_qa")

    def test_returns_none_when_uncertain(self):
        self.assertIsNone(detect_profession("Продажи в отделе маркетинга", list_professions()))
        self.assertIsNone(detect_profession("", list_professions()))

    def test_resume_has_qa_focus(self):
        # Словарь QA-инструментов должен покрывать ручное и автотестирование.
        for text in (MANUAL_QA_RESUME, AUTOMATION_QA_RESUME):
            self.assertIn("Jira", analyze_resume(text).skills)
        self.assertNotIn("Jira", analyze_resume(BACKEND_RESUME).skills)

    def test_detect_profession_accepts_resume_text_too(self):
        self.assertEqual(
            detect_profession(AUTOMATION_QA_RESUME, list_professions()),
            "automation_qa",
        )


class CanonicalCaseTest(unittest.TestCase):
    """Ключевой случай ТЗ: Docker есть в вакансии, но нет в резюме."""

    def test_resume_skills(self):
        self.assertEqual(analyze_resume(CANONICAL_RESUME).skills, ["Python", "Django", "PostgreSQL", "SQL"])

    def test_vacancy_skills(self):
        facts = analyze_vacancy(CANONICAL_VACANCY)
        self.assertIn("Docker", facts.required_skills)
        self.assertNotIn("Docker", analyze_resume(CANONICAL_RESUME).skills)


if __name__ == "__main__":
    unittest.main()
