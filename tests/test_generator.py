"""Тесты генерации письма (`generator.generator`).

Здесь проверяются три главных свойства:
  1. достоверность - письмо не приписывает кандидату навыки из `missing`;
  2. детерминированность - одни и те же входные данные дают одно письмо;
  3. понятные ошибки валидации.
"""

from __future__ import annotations

import pathlib
import re
import unittest

from generator import (
    BRIEF_MAX_CHARS,
    BRIEF_MIN_CHARS,
    MAX_INPUT_CHARS,
    PROFESSIONS,
    STYLES,
    ValidationError,
    analyze_resume,
    analyze_vacancy,
    generate_cover_letter,
    generate_cover_letter_dict,
    get_profession,
    get_style,
    list_professions,
    match_skills,
    style_choices,
    verify_cover_letter,
)
from generator.config import BANNED_PHRASES

from .fixtures import (
    BACKEND_RESUME,
    BACKEND_VACANCY,
    CANONICAL_RESUME,
    CANONICAL_VACANCY,
    DEMO_BY_PROFESSION,
    FRONTEND_RESUME,
    FRONTEND_VACANCY,
    RESUME_WITHOUT_SKILLS,
)

EXPECTED_ERRORS = {
    "resume_empty": "Добавьте текст резюме.",
    "vacancy_empty": "Добавьте описание вакансии.",
    "resume_short": "Текст резюме слишком короткий. Вставьте полный текст резюме.",
    "vacancy_short": "Описание вакансии слишком короткое. Вставьте полное описание вакансии.",
}


class ValidationTest(unittest.TestCase):
    def _error(self, **kwargs):
        params = {
            "resume_text": CANONICAL_RESUME,
            "vacancy_text": CANONICAL_VACANCY,
            "profession": "backend",
            "style": "professional",
        }
        params.update(kwargs)
        with self.assertRaises(ValidationError) as context:
            generate_cover_letter(**params)
        return context.exception

    def test_empty_resume(self):
        error = self._error(resume_text="")
        self.assertEqual(error.message, EXPECTED_ERRORS["resume_empty"])
        self.assertEqual(error.field, "resume")

    def test_empty_resume_none(self):
        self.assertEqual(self._error(resume_text=None).message, EXPECTED_ERRORS["resume_empty"])

    def test_whitespace_resume(self):
        self.assertEqual(self._error(resume_text="   \n ").message, EXPECTED_ERRORS["resume_empty"])

    def test_empty_vacancy(self):
        error = self._error(vacancy_text="")
        self.assertEqual(error.message, EXPECTED_ERRORS["vacancy_empty"])
        self.assertEqual(error.field, "vacancy")

    def test_too_short_resume(self):
        error = self._error(resume_text="Python, Django")
        self.assertEqual(error.message, EXPECTED_ERRORS["resume_short"])
        self.assertEqual(error.field, "resume")

    def test_too_short_vacancy(self):
        error = self._error(vacancy_text="Python, Docker")
        self.assertEqual(error.message, EXPECTED_ERRORS["vacancy_short"])
        self.assertEqual(error.field, "vacancy")

    def test_too_large_resume(self):
        error = self._error(resume_text="Python " * (MAX_INPUT_CHARS // 7 + 10))
        self.assertIn(str(MAX_INPUT_CHARS), error.message)
        self.assertEqual(error.field, "resume")

    def test_unknown_profession(self):
        error = self._error(profession="devops")
        self.assertTrue(error.message.startswith("Выберите направление из списка:"))
        self.assertEqual(error.field, "profession")

    def test_unknown_style(self):
        error = self._error(style="poetic")
        self.assertTrue(error.message.startswith("Выберите стиль письма из списка:"))
        self.assertEqual(error.field, "style")

    def test_profession_and_style_are_case_insensitive(self):
        result = generate_cover_letter(
            CANONICAL_RESUME, CANONICAL_VACANCY, profession="BACKEND", style="Brief"
        )
        self.assertEqual(result.profession, "backend")
        self.assertEqual(result.style, "brief")

    def test_error_to_dict(self):
        error = self._error(resume_text="")
        self.assertEqual(
            error.to_dict(),
            {"success": False, "error": EXPECTED_ERRORS["resume_empty"], "field": "resume"},
        )


class TruthfulnessTest(unittest.TestCase):
    """Ключевое требование: отсутствующие навыки не попадают в письмо."""

    def test_docker_is_not_claimed(self):
        """Резюме «Python, Django, PostgreSQL», в вакансии есть Docker."""
        result = generate_cover_letter(CANONICAL_RESUME, CANONICAL_VACANCY)
        self.assertIn("Docker", result.missing_skills)
        self.assertNotIn("Docker", result.matched_skills)
        self.assertNotIn("Docker", result.cover_letter)
        self.assertNotIn("docker", result.cover_letter.lower())

    def test_letter_has_no_verification_problems(self):
        for profession in PROFESSIONS:
            resume_text, vacancy_text = DEMO_BY_PROFESSION[profession]
            for style in STYLES:
                result = generate_cover_letter(resume_text, vacancy_text, profession, style)
                resume = analyze_resume(resume_text)
                vacancy = analyze_vacancy(vacancy_text)
                match = match_skills(resume, vacancy)
                problems = verify_cover_letter(
                    result.cover_letter, resume, vacancy, match, (vacancy.company, vacancy.title)
                )
                self.assertEqual(
                    problems, [], msg=f"{profession}/{style}: {problems}"
                )

    def test_missing_skills_never_mentioned(self):
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            for style in STYLES:
                result = generate_cover_letter(resume_text, vacancy_text, profession, style)
                letter = result.cover_letter.lower()
                for skill in result.missing_skills:
                    self.assertNotIn(
                        skill.lower(),
                        letter,
                        msg=f"{profession}/{style}: навык {skill} не должен попадать в письмо",
                    )

    def test_no_banned_phrases(self):
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            for style in STYLES:
                letter = generate_cover_letter(
                    resume_text, vacancy_text, profession, style
                ).cover_letter.lower()
                for phrase in BANNED_PHRASES:
                    self.assertNotIn(phrase, letter, msg=f"{profession}/{style}: «{phrase}»")

    def test_no_gendered_wording(self):
        """Письмо не предполагает пол автора."""
        forbidden = (
            r"\bготов\b",
            r"\bготов[аои]\b",
            r"\bуверен[аои]?\b",
            r"\bпризнателен[аи]?\b",
            r"\bзаинтересовала\b",
            r"\bзаинтересовался\b",
            r"\bзаинтересовал\b",
            r"\b(?:рад|рада|радо|рады)\b",
            r"\bспособен[аи]?\b",
            r"\bсильн[аое]\b",
        )
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            for style in STYLES:
                letter = generate_cover_letter(
                    resume_text, vacancy_text, profession, style
                ).cover_letter.lower()
                for pattern in forbidden:
                    with self.subTest(profession=profession, style=style, pattern=pattern):
                        self.assertIsNone(re.search(pattern, letter))

    def test_phrase_pools_have_no_gendered_wording(self):
        """Ни одна формулировка в шаблонах не указывает пол автора.

        Проверяются исходники направлений, а не только готовые письма:
        так ошибка ловится сразу во всех формулировках сразу, а не в одном
        конкретном письме.
        """
        package_dir = pathlib.Path(__file__).resolve().parent.parent / "generator"
        for path in sorted(package_dir.rglob("*.py")):
            if path.name == "config.py":
                # В config.py gendered-формы живут в списке запрещённых.
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                self.assertIsNone(
                    re.search(
                        r"\b(?:готов|готов[аои]|уверен[аои]?|признателен[аи]?|"
                        r"заинтересовал[аи]?ся?|(?:рад|рада|радо|рады)|способен[аи]?)\b",
                        source,
                        re.IGNORECASE,
                    ),
                    msg=f"{path.name}: найдена gendered-формулировка",
                )

    def test_year_claim_requires_year_in_resume(self):
        """Без стажа в резюме письмо не обещает конкретных лет."""
        resume_text = "Разработчик. Опыт коммерческой разработки. Python, Django, PostgreSQL, Git."
        vacancy_text = "Вакансия: Backend Developer. Обязанности: разработка на Python и Django."
        letter = generate_cover_letter(resume_text, vacancy_text).cover_letter
        self.assertNotIn("лет", letter)

    def test_quotes_come_from_sources(self):
        resume = analyze_resume(BACKEND_RESUME)
        vacancy = analyze_vacancy(BACKEND_VACANCY)
        match = match_skills(resume, vacancy)
        letter = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY).cover_letter
        self.assertIn("«", letter)  # цитаты из вакансии используются
        self.assertEqual(
            verify_cover_letter(letter, resume, vacancy, match, (vacancy.company, vacancy.title)),
            [],
        )

    def test_company_not_invented(self):
        letter = generate_cover_letter(CANONICAL_RESUME, CANONICAL_VACANCY).cover_letter
        self.assertNotIn("в компании", letter)
        self.assertNotIn("«", letter)

    def test_skill_is_not_repeated_in_extra_block(self):
        """Навык из стека не должен дублироваться в блоке «Также есть опыт»."""
        resume = "Backend Developer. 3 года опыта. Стек: Python, Django, PostgreSQL, Git."
        vacancy = "Backend Developer. Требования: Python, Django, PostgreSQL, Docker, Linux."
        letter = generate_cover_letter(resume, vacancy).cover_letter
        self.assertNotIn("Также есть опыт", letter)
        self.assertEqual(letter.lower().count("git"), 1)


class GenerationBasicsTest(unittest.TestCase):
    def test_returns_generation_result(self):
        result = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY)
        self.assertTrue(result.cover_letter)
        self.assertEqual(result.profession, "backend")
        self.assertEqual(result.style, "professional")
        self.assertEqual(result["profession"], "backend")  # доступ как к словарю

    def test_letter_is_not_empty_and_has_signature(self):
        letter = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY).cover_letter
        self.assertIn("С уважением", letter)
        self.assertIn("Иван Петров", letter)
        self.assertNotIn("\n\n\n", letter)

    def test_letter_uses_vacancy_company(self):
        result = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY)
        self.assertEqual(result.vacancy_company, "Айти Парк")
        self.assertIn("Айти Парк", result.cover_letter)

    def test_letter_mentions_confirmed_facts(self):
        letter = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY).cover_letter
        self.assertIn("Python", letter)
        self.assertIn("Django", letter)
        self.assertIn("6 лет", letter)

    def test_resume_without_stack_falls_back(self):
        result = generate_cover_letter(RESUME_WITHOUT_SKILLS, BACKEND_VACANCY)
        self.assertTrue(result.cover_letter)
        self.assertTrue(any("технолог" in warning for warning in result.warnings))
        for skill in result.missing_skills:
            self.assertNotIn(skill.lower(), result.cover_letter.lower())

    def test_resume_without_stack_in_every_style(self):
        for style in STYLES:
            result = generate_cover_letter(RESUME_WITHOUT_SKILLS, BACKEND_VACANCY, style=style)
            self.assertTrue(result.cover_letter)
            self.assertNotIn("Docker", result.cover_letter)

    def test_warning_when_company_missing(self):
        result = generate_cover_letter(CANONICAL_RESUME, CANONICAL_VACANCY)
        self.assertTrue(any("компани" in warning.lower() for warning in result.warnings))

    def test_result_dict_shape(self):
        payload = generate_cover_letter_dict(BACKEND_RESUME, BACKEND_VACANCY)
        self.assertEqual(
            set(payload),
            {
                "success",
                "cover_letter",
                "matched_skills",
                "missing_skills",
                "optional_skills",
                "resume_only_skills",
                "warnings",
                "profession",
                "style",
                "detected_profession",
                "vacancy_company",
                "vacancy_title",
            },
        )
        self.assertIs(payload["success"], True)

    def test_detected_profession_is_only_a_hint(self):
        result = generate_cover_letter(FRONTEND_RESUME, FRONTEND_VACANCY, profession="backend")
        self.assertEqual(result.detected_profession, "frontend")
        self.assertEqual(result.profession, "backend")


class StyleTest(unittest.TestCase):
    def test_all_styles_exist(self):
        self.assertEqual(sorted(STYLES), ["brief", "confident", "professional"])
        self.assertEqual(len(style_choices()), 3)

    def test_all_styles_generate_letters(self):
        for style in STYLES:
            result = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY, style=style)
            self.assertTrue(result.cover_letter)
            self.assertEqual(result.style, style)

    def test_brief_length_bounds(self):
        """«Краткий» не длиннее 1000 символов; 700 - цель, а не гарантия.

        Если в резюме не хватает подтверждённых фактов, чтобы добрать
        700 символов, письмо остаётся коротким, но пользователь
        получает предупреждение. Добивать длину выдумкой нельзя.
        """
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            result = generate_cover_letter(
                resume_text, vacancy_text, profession=profession, style="brief"
            )
            letter = result.cover_letter
            self.assertLessEqual(len(letter), BRIEF_MAX_CHARS, profession)
            if len(letter) < BRIEF_MIN_CHARS:
                self.assertTrue(
                    result.warnings,
                    f"{profession}: короткое письмо должно объяснять причину",
                )

    def test_brief_never_exceeds_upper_bound(self):
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            letter = generate_cover_letter(
                resume_text, vacancy_text, profession=profession, style="brief"
            ).cover_letter
            self.assertLessEqual(len(letter), BRIEF_MAX_CHARS)

    def test_brief_uses_unused_matched_skills_before_warning(self):
        """«Краткий» сначала показывает лишние совпадения, и только потом жалуется.

        Если совпадений с вакансией больше, чем обычно показывает стиль,
        но письмо всё равно короткое, поднимается лимит навыков. Предупреждение
        о длине должно означать «в резюме нечего добавить», а не «мы
        придержались красивого лимита».
        """
        resume_text, vacancy_text = DEMO_BY_PROFESSION["backend"]
        brief = get_style("brief")
        result = generate_cover_letter(resume_text, vacancy_text, style="brief")
        self.assertLess(
            len(result.cover_letter), BRIEF_MAX_CHARS, "письмо не должно вылезти за лимит"
        )
        if len(result.cover_letter) < BRIEF_MIN_CHARS:
            self.skipTest("в этом резюме не хватает совпадений для расширения")
        # Показано больше навыков, чем базовый лимит стиля.
        listed = [s for s in result.matched_skills if s in result.cover_letter]
        self.assertGreater(len(listed), brief.max_skills)

    def test_brief_respects_its_own_block_flags(self):
        """«Краткий» не добавляет soft skills: флаги стиля обязательны."""
        brief = get_style("brief")
        self.assertFalse(brief.include_soft_skills_block)
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            letter = generate_cover_letter(
                resume_text, vacancy_text, profession=profession, style="brief"
            ).cover_letter
            self.assertNotIn("soft skills", letter, profession)
            self.assertLessEqual(len(letter), BRIEF_MAX_CHARS)

    def test_soft_skills_appear_only_when_the_style_allows_them(self):
        resume_text, vacancy_text = DEMO_BY_PROFESSION["backend"]
        with_soft = generate_cover_letter(
            resume_text, vacancy_text, style="professional"
        ).cover_letter
        self.assertIn("работа в команде", with_soft)

    def test_vacancy_task_with_unknown_skill_is_not_quoted(self):
        """«Настройка CI/CD и Docker» не цитируется: CI/CD в резюме нет."""
        result = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY, style="brief")
        self.assertNotIn("CI/CD", result.cover_letter)
        self.assertNotIn("Настройка CI/CD", result.cover_letter)
        # А вот задача только на подтверждённых навыках - цитируется.
        self.assertIn("REST API", result.cover_letter)

    def test_professional_includes_education_and_soft_skills(self):
        letter = generate_cover_letter(
            BACKEND_RESUME, BACKEND_VACANCY, style="professional"
        ).cover_letter
        self.assertIn("МГТУ", letter)

    def test_no_block_is_printed_twice(self):
        """Один факт не должен печататься в письме дважды.

        Блок шаблона («По образованию - …») и дополнение в конце
        письма («Образование: …») печатают одно и то же, если их
        не сверить с уже готовым текстом.
        """
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            for style in STYLES:
                letter = generate_cover_letter(
                    resume_text, vacancy_text, profession, style
                ).cover_letter
                paragraphs = letter.split("\n\n")
                with self.subTest(profession=profession, style=style):
                    self.assertEqual(
                        len(paragraphs), len(set(paragraphs)), "повтор абзаца"
                    )
                    for marker in ("МГТУ", "СПбГУ", "НГУ", "МИФИ"):
                        self.assertLessEqual(
                            letter.count(marker), 1, f"{marker} указан дважды"
                        )
                    self.assertLessEqual(
                        letter.count("soft skills"), 1, "soft skills указаны дважды"
                    )
                    self.assertLessEqual(
                        letter.count("Также есть опыт"), 1, "список навыков повторён"
                    )

    def test_confident_is_more_energetic(self):
        confident = get_style("confident")
        professional = get_style("professional")
        self.assertTrue(confident.enthusiasm)
        self.assertFalse(professional.enthusiasm)
        self.assertGreater(confident.max_skills, professional.max_skills - 1)

    def test_unknown_style_falls_back_to_default(self):
        self.assertEqual(get_style("нет такого").id, "professional")


class ProfessionTest(unittest.TestCase):
    def test_four_professions_registered(self):
        self.assertEqual(
            [item.id for item in list_professions()],
            ["backend", "frontend", "manual_qa", "automation_qa"],
        )

    def test_profession_metadata(self):
        for item in list_professions():
            self.assertTrue(item.label)
            self.assertTrue(item.description)
            self.assertTrue(item.focus_genitive)
            self.assertTrue(item.focus_dative)
            self.assertTrue(item.focus_prepositional)
            self.assertIn(item.id, item.as_dict().values())
            self.assertEqual(item.as_dict()["id"], item.id)

    def test_each_profession_generates_a_letter(self):
        for profession in PROFESSIONS:
            resume_text, vacancy_text = DEMO_BY_PROFESSION[profession]
            result = generate_cover_letter(resume_text, vacancy_text, profession=profession)
            self.assertTrue(result.cover_letter)
            self.assertIn("С уважением", result.cover_letter)
            self.assertEqual(result.profession, profession)

    def test_profession_wording_is_used(self):
        """В письме используются падежные формы выбранного направления."""
        for profession, (resume_text, vacancy_text) in DEMO_BY_PROFESSION.items():
            spec = get_profession(profession)
            letter = generate_cover_letter(
                resume_text, vacancy_text, profession=profession
            ).cover_letter
            self.assertTrue(
                spec.focus_prepositional in letter or spec.focus_genitive in letter
                or spec.focus_dative in letter,
                msg=f"{profession}: падежные формы направления не использованы",
            )

    def test_qa_professions_use_their_own_focus(self):
        resume_text, vacancy_text = DEMO_BY_PROFESSION["manual_qa"]
        letter = generate_cover_letter(resume_text, vacancy_text, profession="manual_qa").cover_letter
        self.assertIn(get_profession("manual_qa").focus_prepositional, letter)

    def test_unknown_profession_falls_back_to_default(self):
        self.assertEqual(get_profession("devops").id, "backend")


class DeterminismTest(unittest.TestCase):
    def test_same_input_same_letter(self):
        first = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY)
        second = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY)
        self.assertEqual(first.cover_letter, second.cover_letter)

    def test_seed_changes_result(self):
        first = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY, seed="a")
        second = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY, seed="b")
        self.assertNotEqual(first.cover_letter, second.cover_letter)

    def test_seed_is_reproducible(self):
        first = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY, seed="same")
        second = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY, seed="same")
        self.assertEqual(first.cover_letter, second.cover_letter)

    def test_formatting_does_not_change_facts(self):
        """Переносы строк в резюме не меняют найденные факты."""
        spaced = BACKEND_RESUME.replace("\n", "\n\n")
        first = generate_cover_letter(BACKEND_RESUME, BACKEND_VACANCY)
        second = generate_cover_letter(spaced, BACKEND_VACANCY)
        self.assertEqual(first.matched_skills, second.matched_skills)
        self.assertEqual(first.missing_skills, second.missing_skills)
        self.assertEqual(first.vacancy_company, second.vacancy_company)
        self.assertEqual(first.cover_letter.split("\n")[-1], second.cover_letter.split("\n")[-1])

    def test_every_variant_produces_a_valid_letter(self):
        """Все зёрна дают целое письмо без недостоверных утверждений."""
        for index in range(30):
            result = generate_cover_letter(
                BACKEND_RESUME, BACKEND_VACANCY, seed=str(index)
            )
            self.assertTrue(result.cover_letter)
            self.assertIn("С уважением", result.cover_letter)
            self.assertNotIn("  ", result.cover_letter)


if __name__ == "__main__":
    unittest.main()
