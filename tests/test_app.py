"""Тесты веб-слоя (`app.py`).

Приложение проверяется через встроенный тест-клиент Flask:
реальный сервер запускать не нужно, данные никуда не отправляются.
"""

from __future__ import annotations

import json
import unittest

from app import app

from .fixtures import BACKEND_RESUME, BACKEND_VACANCY, CANONICAL_RESUME, CANONICAL_VACANCY

app.config.update(TESTING=True)


class IndexPageTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_is_available(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])

    def test_page_contains_all_professions(self):
        html = self.client.get("/").get_data(as_text=True)
        for label in ("Backend Developer", "Frontend Developer", "QA Engineer", "Automation QA"):
            self.assertIn(label, html)

    def test_page_contains_all_styles(self):
        html = self.client.get("/").get_data(as_text=True)
        for label in ("Профессиональный", "Краткий", "Уверенный"):
            self.assertIn(label, html)

    def test_page_has_required_elements(self):
        html = self.client.get("/").get_data(as_text=True)
        for marker in ('id="resume"', 'id="vacancy"', 'id="generate"', 'id="coverLetter"'):
            self.assertIn(marker, html)
        for label in ("Копировать", "Скачать .txt", "Создать заново", "Что найдено в вакансии"):
            self.assertIn(label, html)

    def test_page_has_demo_texts_and_limits(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("window.DEMO_TEXTS", html)
        self.assertIn("window.APP_LIMITS", html)

    def test_no_external_resources(self):
        """Ни CDN, ни внешних ссылок: всё обслуживается локально."""
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("//cdn", html)
        self.assertNotIn("cdn.", html)
        for attribute in ('src="http', "src='http", 'href="http', "href='http", 'url(http'):
            self.assertNotIn(attribute, html)

    def test_local_static_files(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("/static/css/style.css", html)
        self.assertIn("/static/js/app.js", html)
        self.assertIn("/static/img/favicon.svg", html)

    def test_static_files_are_served(self):
        for path in ("/static/css/style.css", "/static/js/app.js", "/static/img/favicon.svg"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, msg=path)

    def test_responses_are_not_cached(self):
        response = self.client.get("/")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")

    def test_hidden_attribute_wins_over_class_display(self):
        """`hidden` должен прятать элемент, даже если класс задаёт `display`.

        Без этого `.alert { display: flex }` перебивает стандартное
        `[hidden] { display: none }`, и пустое окно ошибки висит на странице
        всё время.
        """
        css = self.client.get("/static/css/style.css").get_data(as_text=True)
        self.assertRegex(css, r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important")

    def test_alert_and_optional_groups_start_hidden(self):
        """Окно ошибки и пустые группы не должны быть открыты при загрузке."""
        html = self.client.get("/").get_data(as_text=True)
        for element_id in ("alert", "resultSection", "optionalGroup", "warningsGroup"):
            with self.subTest(element=element_id):
                self.assertRegex(
                    html,
                    rf'id="{element_id}"[^>]*\shidden',
                    msg=f'#{element_id} должен быть скрыт в разметке',
                )


class MetaApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_meta_lists_professions_and_styles(self):
        payload = self.client.get("/api/meta").get_json()
        self.assertIs(payload["success"], True)
        self.assertEqual(
            [item["id"] for item in payload["professions"]],
            ["backend", "frontend", "manual_qa", "automation_qa"],
        )
        self.assertEqual(
            [item["id"] for item in payload["styles"]],
            ["professional", "brief", "confident"],
        )


class GenerateApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def post(self, **payload):
        return self.client.post("/generate", json=payload)

    def test_successful_generation(self):
        response = self.post(resume=BACKEND_RESUME, vacancy=BACKEND_VACANCY)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIs(payload["success"], True)
        self.assertTrue(payload["cover_letter"])
        self.assertIn("Python", payload["cover_letter"])
        self.assertEqual(payload["profession"], "backend")
        self.assertEqual(payload["style"], "professional")
        self.assertEqual(payload["vacancy_company"], "Айти Парк")
        self.assertIn("matched_skills", payload)
        self.assertIsInstance(payload["warnings"], list)

    def test_response_is_utf8_without_escapes(self):
        response = self.post(resume=BACKEND_RESUME, vacancy=BACKEND_VACANCY)
        self.assertIn("Айти Парк", response.get_data(as_text=True))
        self.assertNotIn("\\u0410", response.get_data(as_text=True))

    def test_docker_is_not_claimed(self):
        payload = self.post(resume=CANONICAL_RESUME, vacancy=CANONICAL_VACANCY).get_json()
        self.assertIn("Docker", payload["missing_skills"])
        self.assertNotIn("Docker", payload["cover_letter"])

    def test_every_style_and_profession_works(self):
        for profession in ("backend", "frontend", "manual_qa", "automation_qa"):
            for style in ("professional", "brief", "confident"):
                response = self.post(
                    resume=BACKEND_RESUME,
                    vacancy=BACKEND_VACANCY,
                    profession=profession,
                    style=style,
                )
                self.assertEqual(response.status_code, 200, msg=f"{profession}/{style}")
                self.assertTrue(response.get_json()["cover_letter"])

    def test_missing_resume(self):
        response = self.post(resume="", vacancy=BACKEND_VACANCY)
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIs(payload["success"], False)
        self.assertEqual(payload["error"], "Добавьте текст резюме.")
        self.assertEqual(payload["field"], "resume")

    def test_missing_vacancy(self):
        response = self.post(resume=BACKEND_RESUME, vacancy="")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["field"], "vacancy")

    def test_short_resume(self):
        response = self.post(resume="Python", vacancy=BACKEND_VACANCY)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "Текст резюме слишком короткий. Вставьте полный текст резюме.",
        )

    def test_unknown_profession(self):
        response = self.post(
            resume=BACKEND_RESUME, vacancy=BACKEND_VACANCY, profession="devops"
        )
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["field"], "profession")
        self.assertIn("Backend Developer", payload["error"])

    def test_unknown_style(self):
        response = self.post(resume=BACKEND_RESUME, vacancy=BACKEND_VACANCY, style="haiku")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["field"], "style")

    def test_non_json_body(self):
        response = self.client.post("/generate", data="просто текст")
        self.assertEqual(response.status_code, 400)
        self.assertIs(response.get_json()["success"], False)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get("/generate").status_code, 405)

    def test_response_is_not_cached(self):
        response = self.post(resume=BACKEND_RESUME, vacancy=BACKEND_VACANCY)
        self.assertIn("no-store", response.headers["Cache-Control"])


class ErrorHandlingTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_404_returns_json(self):
        response = self.client.get("/nope")
        self.assertEqual(response.status_code, 404)
        payload = response.get_json()
        self.assertIs(payload["success"], False)
        self.assertTrue(payload["error"])

    def test_unknown_route_does_not_leak_stacktrace(self):
        response = self.client.get("/nope")
        self.assertNotIn("Traceback", response.get_data(as_text=True))


class PrivacyTest(unittest.TestCase):
    """Входные данные не должны сохраняться или попадать в ответ."""

    def setUp(self):
        self.client = app.test_client()
        self.secret = "ОченьСекретныйМаркерОпыта"

    def test_input_is_not_stored_in_cookies(self):
        response = self.client.post(
            "/generate",
            json={"resume": f"Python, Django, {self.secret}", "vacancy": CANONICAL_VACANCY},
        )
        self.assertEqual(response.headers.get("Set-Cookie"), None)

    def test_output_does_not_contain_other_input(self):
        response = self.client.post(
            "/generate",
            json={"resume": BACKEND_RESUME, "vacancy": f"{CANONICAL_VACANCY} {self.secret}"},
        )
        self.assertNotIn(self.secret, response.get_data(as_text=True))

    def test_static_assets_do_not_contain_input(self):
        """Ни один статический файл не содержит пользовательский текст."""
        for path in ("/static/css/style.css", "/static/js/app.js", "/"):
            body = self.client.get(path).get_data(as_text=True)
            self.assertNotIn(self.secret, body, msg=path)


if __name__ == "__main__":
    unittest.main()
