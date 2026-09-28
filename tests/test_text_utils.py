"""Тесты текстовых утилит (`generator.text_utils`)."""

from __future__ import annotations

import unittest

from generator.text_utils import (
    clean_fragment,
    dedupe,
    first_sentences,
    iter_lines,
    join_natural,
    normalize_inline,
    normalize_text,
    split_sentences,
    strip_bullet,
    to_lower,
    truncate,
    word_count,
)


class NormalizeTest(unittest.TestCase):
    def test_normalize_text_keeps_line_breaks(self):
        self.assertEqual(normalize_text("a\n\n\n\nb"), "a\n\nb")

    def test_iter_lines_strips_bullets(self):
        self.assertEqual(iter_lines("- первый\n• второй\n\nтретий"), ["первый", "второй", "третий"])

    def test_normalize_text_replaces_nbsp_and_dashes(self):
        self.assertEqual(normalize_inline("a\u00a0b \u2013 c"), "a b - c")

    def test_normalize_inline_joins_lines(self):
        self.assertEqual(normalize_inline("одна\nвторая"), "одна вторая")

    def test_to_lower_folds_yo(self):
        """«ё» и «е» считаются одним символом - так надёжнее поиск."""
        self.assertEqual(to_lower("Ёлка"), "елка")
        self.assertEqual(to_lower("ПРИВЕТ"), "привет")

    def test_iter_lines(self):
        self.assertEqual(iter_lines("a\n\n- b\nc"), ["a", "b", "c"])

    def test_strip_bullet(self):
        self.assertEqual(strip_bullet("  * пункт"), "пункт")
        self.assertEqual(strip_bullet("1. пункт"), "пункт")
        self.assertEqual(strip_bullet("пункт"), "пункт")


class SentencesTest(unittest.TestCase):
    def test_split_sentences(self):
        self.assertEqual(
            split_sentences("Одно предложение. Второе предложение! Третье?"),
            ["Одно предложение.", "Второе предложение!", "Третье?"],
        )

    def test_first_sentences(self):
        text = "Одно. Два. Три. Четыре."
        self.assertEqual(first_sentences(text, 2), "Одно. Два.")
        self.assertEqual(first_sentences(text, 99), text)

    def test_first_sentences_of_empty(self):
        self.assertEqual(first_sentences("", 3), "")


class CountersTest(unittest.TestCase):
    def test_word_count(self):
        self.assertEqual(word_count("Python, Django и PostgreSQL"), 4)
        self.assertEqual(word_count("   "), 0)

    def test_truncate_keeps_word_boundary(self):
        result = truncate("раз два три четыре пять", 10)
        self.assertTrue(result.endswith("…"))
        self.assertLessEqual(len(result), 11)
        self.assertIn("раз", result)

    def test_truncate_keeps_short_text(self):
        self.assertEqual(truncate("коротко", 100), "коротко")

    def test_clean_fragment_trims_punctuation(self):
        self.assertEqual(clean_fragment("  текст,  "), "текст")

    def test_clean_fragment_respects_limit(self):
        self.assertLessEqual(len(clean_fragment("а" * 500, limit=40)), 41)


class JoinTest(unittest.TestCase):
    def test_join_natural_one(self):
        self.assertEqual(join_natural(["Python"]), "Python")

    def test_join_natural_two(self):
        self.assertEqual(join_natural(["Python", "Django"]), "Python и Django")

    def test_join_natural_three(self):
        self.assertEqual(join_natural(["Python", "Django", "PostgreSQL"]), "Python, Django и PostgreSQL")

    def test_join_natural_five(self):
        self.assertEqual(
            join_natural(["a", "b", "c", "d", "e"]), "a, b, c, d и e"
        )

    def test_join_natural_empty(self):
        self.assertEqual(join_natural([]), "")

    def test_dedupe_keeps_order(self):
        self.assertEqual(dedupe(["b", "a", "b", "c", "a"]), ["b", "a", "c"])


if __name__ == "__main__":
    unittest.main()
