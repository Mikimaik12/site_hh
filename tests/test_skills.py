"""Тесты словаря навыков (`generator.skills`)."""

from __future__ import annotations

import unittest

from generator.skills import (
    CATEGORY_QA_TOOL,
    DERIVED_ONLY,
    IMPLIES,
    display_skills,
    find_skill_matches,
    find_skills,
    find_skills_by_category,
    is_derived_only,
    is_known_skill,
    known_skill_names,
    skills_in_categories,
)


class FindSkillsTest(unittest.TestCase):
    def test_finds_basic_backend_stack(self):
        self.assertEqual(
            find_skills("Разрабатываю на Python и Django, база PostgreSQL"),
            ["Python", "Django", "PostgreSQL", "SQL"],
        )

    def test_finds_russian_aliases(self):
        found = find_skills("Пишу тест-кейсы и чек-листы, веду регрессионное тестирование")
        self.assertIn("Test Cases", found)
        self.assertIn("Regression Testing", found)

    def test_implied_skills_are_added(self):
        found = find_skills("Django, PostgreSQL")
        self.assertIn("Python", found)  # Django -> Python
        self.assertIn("SQL", found)  # PostgreSQL -> SQL

    def test_implied_skills_are_transitive(self):
        # Kubernetes -> Docker -> Linux
        found = find_skills("Kubernetes")
        self.assertIn("Docker", found)
        self.assertIn("Linux", found)

    def test_implies_map_is_consistent(self):
        for source, implied in IMPLIES.items():
            for name in implied:
                self.assertTrue(
                    is_known_skill(name),
                    msg=f"{source} -> {name}: навык не известен словарю",
                )

    def test_no_substring_false_positives(self):
        # «JavaScript» не должно превращаться в «Java», а «Java» - в «JavaScript».
        self.assertEqual(find_skills("JavaScript"), ["JavaScript"])
        self.assertIn("Java", find_skills("Java, Spring"))
        self.assertNotIn("Java", find_skills("JavaScript, TypeScript"))

    def test_csharp_and_cpp_boundaries(self):
        self.assertEqual(find_skills("C#, C++"), ["C#", "C++"])

    def test_context_only_skill_needs_tech_context(self):
        # Обычное английское «go» - не навык.
        self.assertEqual(find_skills("I go to the office every day and lead the team"), [])
        # В списке навыков - навык.
        self.assertIn("Go", find_skills("Навыки: Go, PostgreSQL, Docker"))

    def test_wildcard_alias(self):
        self.assertIn("Regression Testing", find_skills("регрессионные проверки"))
        self.assertIn("Smoke Testing", find_skills("смоук-тестирование"))

    def test_dashes_and_spaces_variants(self):
        self.assertIn("REST API", find_skills("REST-API"))
        self.assertIn("REST API", find_skills("rest api"))
        self.assertIn("CI/CD", find_skills("ci-cd"))
        self.assertIn("Docker Compose", find_skills("docker-compose.yml"))

    def test_longest_alias_wins(self):
        # Короткий алиас не должен «съедать» длинный.
        self.assertIn("MSSQL", find_skills("опыт: SQL Server, T-SQL"))
        self.assertIn("GitHub Actions", find_skills("сборки в GitHub Actions"))
        self.assertIn("GitLab CI", find_skills("сборки в GitLab CI"))
        self.assertIn("Git Flow", find_skills("работаем по Git Flow"))
        self.assertIn("Git", find_skills("Git, GitHub, Bitbucket"))

    def test_soft_looking_words_are_not_skills(self):
        self.assertEqual(find_skills("Ответственность, работа в команде, внимание к деталям."), [])

    def test_empty_text(self):
        self.assertEqual(find_skills(""), [])
        self.assertEqual(find_skills("   \n  "), [])

    def test_matches_are_sorted_by_position(self):
        matches = find_skill_matches("Python, Django, PostgreSQL, Git")
        names = [match.name for match in matches]
        self.assertEqual(names[:2], ["Python", "Django"])
        self.assertLess(names.index("Python"), names.index("Git"))
        self.assertEqual([match.start for match in matches], sorted(match.start for match in matches))

    def test_no_duplicate_names(self):
        found = find_skills("Python, python, PYTHON, Django, Django")
        self.assertEqual(found, ["Python", "Django"])


class QaToolDictionaryTest(unittest.TestCase):
    def test_qa_tools_are_recognized(self):
        text = "Selenium, Playwright, Pytest, Postman, Swagger, Jira, Allure, Charles, TestRail"
        found = find_skills(text)
        for name in ("Selenium", "Playwright", "Pytest", "Postman", "Swagger", "Jira", "Allure", "Charles", "TestRail"):
            self.assertIn(name, found)

    def test_qa_tools_have_qa_category(self):
        grouped = find_skills_by_category("Selenium, Postman, TestRail")
        for name in ("Selenium", "Postman", "TestRail"):
            self.assertIn(name, grouped[CATEGORY_QA_TOOL])

    def test_skills_in_categories(self):
        text = "Python, Django, PostgreSQL, Selenium"
        self.assertEqual(
            skills_in_categories(text, ("qa_tool",)),
            ["Selenium"],
        )
        self.assertEqual(
            skills_in_categories(text, ("language",)),
            ["Python"],
        )


class DictionaryMetaTest(unittest.TestCase):
    def test_known_skill_names_sorted_and_unique(self):
        names = known_skill_names()
        self.assertEqual(names, sorted(set(names)))
        self.assertIn("Python", names)
        self.assertIn("Docker", names)
        self.assertIn("Jira", names)

    def test_is_known_skill(self):
        self.assertTrue(is_known_skill("Python"))
        self.assertTrue(is_known_skill("SQL"))  # производный от PostgreSQL
        self.assertFalse(is_known_skill("Квантовый компьютер"))

    def test_derived_only_skills_are_hidden_from_user(self):
        self.assertTrue(is_derived_only("Version Control"))
        self.assertFalse(is_derived_only("Git"))
        self.assertEqual(display_skills(["Git", "Version Control", "SQL"]), ["Git", "SQL"])
        for name in DERIVED_ONLY:
            self.assertNotIn(name, display_skills(known_skill_names()))


if __name__ == "__main__":
    unittest.main()
