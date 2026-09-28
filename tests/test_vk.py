"""Тесты модуля VK: генерация постов и публикация.

Сеть не используется. Транспорт клиента подменяется заглушкой, поэтому
проверяется ровно то, что делает наш код: сборка текста, проверки перед
отправкой, разбор ответа VK и поведение при ошибках.
"""

from __future__ import annotations

import unittest
from urllib.request import Request

from app import app
from generator import analyze_pair
from vk import (
    PostLimits,
    VkApiError,
    VkClient,
    VkNotConfiguredError,
    VkPostError,
    VkSettings,
    VkValidationError,
    build_post,
    find_foreign_urls,
    find_personal_data,
    generate_vk_post,
    load_settings,
    publish_post,
    verify_vk_post,
    vk_status,
)
from vk.api import parse_publish_response
from vk.config import MAX_MATCHES, MAX_MISSING, MAX_REQUIREMENTS, normalize_group_id
from vk.post_generator import (
    POST_TYPE_ADVICE,
    POST_TYPE_BREAKDOWN,
    POST_TYPE_SKILL_CHECK,
    POST_TYPES,
    ROLE_MATCHED,
    VkBlock,
    post_types,
)
from vk.service import validate_publishable_text

from .fixtures import CANONICAL_RESUME, CANONICAL_VACANCY

app.config.update(TESTING=True)

SITE_URL = "https://generator.example"

#: Настройки без секретов: публикация невозможна и не должна падать.
NOT_CONFIGURED = VkSettings()
#: Настройки с правдоподобным, но выдуманным токеном.
CONFIGURED = VkSettings(group_id="-4242", access_token="test-token-do-not-use", site_url=SITE_URL)


def fake_opener(payload):
    """Заглушка транспорта: возвращает заранее заданный ответ VK."""
    calls = []

    def opener(request: Request, timeout: float) -> dict:
        calls.append(request)
        return payload

    opener.calls = calls
    return opener


class PostGeneratorTest(unittest.TestCase):
    """Сборка текста поста из уже готового разбора вакансии."""

    def setUp(self):
        self.analysis = analyze_pair(CANONICAL_RESUME, CANONICAL_VACANCY)

    def test_breakdown_post_is_built_from_vacancy(self):
        post = build_post(
            CANONICAL_RESUME, CANONICAL_VACANCY, POST_TYPE_BREAKDOWN, settings=CONFIGURED
        )
        self.assertEqual(post.post_type, POST_TYPE_BREAKDOWN)
        self.assertIn("Разбираем вакансию", post.text)
        self.assertIn("Что ищут:", post.text)
        self.assertIn("Совпадает с резюме:", post.text)
        self.assertIn(SITE_URL, post.text)

    def test_all_three_post_types_exist_and_differ(self):
        texts = {
            item.id: build_post(
                CANONICAL_RESUME, CANONICAL_VACANCY, item.id, settings=CONFIGURED
            ).text
            for item in post_types()
        }
        self.assertEqual(len(texts), 3)
        self.assertEqual(
            set(texts), {POST_TYPE_BREAKDOWN, POST_TYPE_SKILL_CHECK, POST_TYPE_ADVICE}
        )
        self.assertEqual(len(set(texts.values())), 3, "посты не должны совпадать")
        self.assertIn("В вакансии есть", texts[POST_TYPE_SKILL_CHECK])
        self.assertIn("Совет для IT-соискателю", texts[POST_TYPE_ADVICE])

    def test_advice_type_works_without_resume_and_vacancy(self):
        post = build_post("", "", POST_TYPE_ADVICE, settings=CONFIGURED)
        self.assertTrue(post.text.strip())
        self.assertIn(SITE_URL, post.text)

    def test_unknown_post_type_is_rejected(self):
        with self.assertRaises(VkPostError):
            build_post(CANONICAL_RESUME, CANONICAL_VACANCY, "telegram", settings=CONFIGURED)

    def test_post_length_matches_counter(self):
        post = build_post(
            CANONICAL_RESUME, CANONICAL_VACANCY, POST_TYPE_BREAKDOWN, settings=CONFIGURED
        )
        self.assertEqual(post.chars, len(post.text))
        self.assertEqual(post.to_dict()["chars"], len(post.text))

    def test_limits_are_configurable(self):
        tight = VkSettings(
            group_id="1",
            access_token="t",
            site_url=SITE_URL,
            limits=PostLimits(requirements=1, matches=1, missing=1),
        )
        post = build_post(
            CANONICAL_RESUME, CANONICAL_VACANCY, POST_TYPE_BREAKDOWN, settings=tight
        )
        self.assertEqual(post.text.count("•"), 1)
        self.assertEqual(post.text.count("✅"), 1)
        self.assertEqual(post.text.count("⚠"), 1)

    def test_default_limits_match_configuration(self):
        self.assertEqual((MAX_REQUIREMENTS, MAX_MATCHES, MAX_MISSING), (6, 5, 5))


class NoInventedSkillsTest(unittest.TestCase):
    """Главное правило проекта: отсутствующий навык не становится опытом."""

    def setUp(self):
        self.analysis = analyze_pair(CANONICAL_RESUME, CANONICAL_VACANCY)
        self.forbidden = self.analysis.match.forbidden_for_letter

    def test_forbidden_skill_is_actually_missing(self):
        self.assertIn("Docker", self.forbidden)

    def test_post_never_claims_missing_skill_as_experience(self):
        post = build_post(
            CANONICAL_RESUME, CANONICAL_VACANCY, POST_TYPE_BREAKDOWN, settings=CONFIGURED
        )
        matched_block = [block for block in post.blocks if block.role == ROLE_MATCHED]
        self.assertTrue(matched_block)
        for block in matched_block:
            for skill in self.forbidden:
                self.assertNotIn(
                    skill.lower(),
                    block.text.lower(),
                    "навык без опыта в резюме попал в блок «Совпадает с резюме»",
                )

    def test_missing_skill_is_named_only_as_absent(self):
        post = build_post(
            CANONICAL_RESUME, CANONICAL_VACANCY, POST_TYPE_BREAKDOWN, settings=CONFIGURED
        )
        self.assertIn("Есть в вакансии, но нет в резюме:", post.text)
        self.assertIn("нет в резюме", post.text)
        self.assertNotIn("владеете", post.text.lower())
        self.assertNotIn("опыт работы с docker", post.text.lower())

    def test_verification_catches_a_forged_claim(self):
        forged = [VkBlock("Совпадает с резюме:\n✅ Docker", ROLE_MATCHED)]
        problems = verify_vk_post(forged, self.analysis, site_url=SITE_URL)
        self.assertTrue(problems)
        self.assertIn("Docker", problems[0])

    def test_post_generation_refuses_to_emit_forged_post(self):
        from vk.post_generator import _BUILDERS

        original = _BUILDERS[POST_TYPE_BREAKDOWN]
        _BUILDERS[POST_TYPE_BREAKDOWN] = lambda *_: [VkBlock("Пишу на Docker каждый день", ROLE_MATCHED)]
        try:
            with self.assertRaises(VkPostError):
                generate_vk_post(self.analysis, POST_TYPE_BREAKDOWN, SITE_URL)
        finally:
            _BUILDERS[POST_TYPE_BREAKDOWN] = original


class PersonalDataTest(unittest.TestCase):
    """В посте не должно быть личных данных и посторонних ссылок."""

    def setUp(self):
        self.analysis = analyze_pair(CANONICAL_RESUME, CANONICAL_VACANCY)

    def test_email_is_detected(self):
        self.assertTrue(find_personal_data("Пишите на ivan@example.com"))

    def test_phone_is_detected(self):
        self.assertTrue(find_personal_data("Телефон +7 (999) 123-45-67"))

    def test_year_range_is_not_a_phone(self):
        self.assertEqual(find_personal_data("Опыт 2019 - 2021, обучение с 2016 года"), [])

    def test_candidate_name_is_detected(self):
        analysis = analyze_pair("Иван Петров\nPython, Django, три года опыта", CANONICAL_VACANCY)
        self.assertTrue(find_personal_data("С уважением, Иван Петров", analysis))

    def test_generated_posts_contain_no_personal_data(self):
        for item in post_types():
            post = build_post(CANONICAL_RESUME, CANONICAL_VACANCY, item.id, settings=CONFIGURED)
            self.assertEqual(find_personal_data(post.text, self.analysis), [], item.id)

    def test_only_site_url_is_allowed(self):
        self.assertEqual(find_foreign_urls("Ссылка: " + SITE_URL, SITE_URL), [])
        self.assertTrue(find_foreign_urls("Мой профиль: https://t.me/ivanpetrov", SITE_URL))

    def test_generated_posts_have_no_foreign_urls(self):
        for item in post_types():
            post = build_post(CANONICAL_RESUME, CANONICAL_VACANCY, item.id, settings=CONFIGURED)
            self.assertEqual(find_foreign_urls(post.text, SITE_URL), [], item.id)


class SettingsTest(unittest.TestCase):
    """Настройки читаются из окружения, секрет наружу не отдаётся."""

    def test_missing_credentials_mean_not_configured(self):
        self.assertFalse(NOT_CONFIGURED.is_configured)
        self.assertFalse(vk_status_from({})["enabled"])

    def test_group_id_accepts_link_and_minus(self):
        for raw, expected in (
            ("123", "123"),
            ("-123", "123"),
            ("https://vk.com/club123", "123"),
            ("public123", "123"),
            ("  @123  ", "123"),
        ):
            self.assertEqual(normalize_group_id(raw), expected, raw)

    def test_repr_never_shows_the_token(self):
        text = repr(CONFIGURED)
        self.assertNotIn(CONFIGURED.access_token, text)
        self.assertIn("***", text)

    def test_public_dict_has_no_token(self):
        payload = CONFIGURED.public_dict()
        self.assertNotIn("access_token", str(payload))
        self.assertNotIn(CONFIGURED.access_token, str(payload))

    def test_settings_come_from_environment_mapping(self):
        settings = load_settings(
            {
                "VK_GROUP_ID": "999",
                "VK_ACCESS_TOKEN": "secret-value",
                "SITE_URL": "https://site.example/",
                "VK_API_VERSION": "5.199",
            }
        )
        self.assertTrue(settings.is_configured)
        self.assertEqual(settings.owner_id, -999)
        self.assertEqual(settings.site_url, "https://site.example")
        self.assertEqual(settings.api_version, "5.199")


def vk_status_from(env):
    """Состояние интеграции для произвольного окружения."""
    import os

    saved = {}
    try:
        for key in ("VK_GROUP_ID", "VK_ACCESS_TOKEN", "SITE_URL"):
            saved[key] = os.environ.pop(key, None)
        os.environ.update({key: value for key, value in env.items() if value is not None})
        return vk_status()
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class PublishTest(unittest.TestCase):
    """Публикация: настройки, запрос, ответы и ошибки."""

    def test_not_configured_gives_clear_message(self):
        with self.assertRaises(VkNotConfiguredError) as caught:
            publish_post("Текст поста", settings=NOT_CONFIGURED)
        self.assertEqual(caught.exception.user_message, "VK API не настроен.")
        self.assertIn("hint", caught.exception.to_dict())

    def test_empty_text_is_rejected_before_any_request(self):
        with self.assertRaises(VkValidationError):
            validate_publishable_text("   ", CONFIGURED)

    def test_personal_data_in_edited_text_is_rejected(self):
        with self.assertRaises(VkValidationError):
            validate_publishable_text("Пишите на ivan@example.com", CONFIGURED)

    def test_successful_mock_response(self):
        opener = fake_opener({"response": {"post_id": 17}})
        result = VkClient(CONFIGURED, opener=opener).publish_post("Текст поста")
        self.assertEqual(result.post_id, 17)
        self.assertEqual(result.url, "https://vk.com/wall-4242_17")
        self.assertEqual(result.to_dict()["success"], True)

    def test_request_shape_is_correct(self):
        opener = fake_opener({"response": {"post_id": 1}})
        VkClient(CONFIGURED, opener=opener).publish_post("Текст поста")
        request = opener.calls[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn("api.vk.ru", request.full_url)
        body = request.data.decode("utf-8")
        self.assertIn("owner_id=-4242", body)
        self.assertIn("from_group=1", body)
        self.assertIn("v=5.199", body)
        # Ключ доступа - в заголовке, а не в адресе и не в теле запроса.
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token-do-not-use")
        self.assertNotIn("test-token-do-not-use", request.full_url)
        self.assertNotIn("test-token-do-not-use", body)

    def test_vk_error_code_becomes_readable_message(self):
        opener = fake_opener({"error": {"error_code": 214, "error_msg": "Access denied"}})
        with self.assertRaises(VkApiError) as caught:
            VkClient(CONFIGURED, opener=opener).publish_post("Текст поста")
        self.assertEqual(caught.exception.code, 214)
        self.assertIn("сообщества", caught.exception.user_message)
        # Сырой текст VK наружу не отдаётся.
        self.assertNotIn("Access denied", caught.exception.user_message)

    def test_unknown_error_code_stays_generic(self):
        opener = fake_opener({"error": {"error_code": 99999}})
        with self.assertRaises(VkApiError) as caught:
            VkClient(CONFIGURED, opener=opener).publish_post("Текст поста")
        self.assertNotIn("99999", caught.exception.user_message)

    def test_malformed_response_is_an_error_not_a_crash(self):
        for payload in ({}, {"response": {}}, {"response": "ok"}, {"response": {"post_id": "x"}}):
            with self.assertRaises(VkApiError):
                parse_publish_response(payload, CONFIGURED)

    def test_network_failure_is_reported_without_traceback(self):
        def broken_opener(request, timeout):
            raise OSError("connection reset")

        with self.assertRaises(VkApiError) as caught:
            VkClient(CONFIGURED, opener=broken_opener).publish_post("Текст поста")
        self.assertIn("Связь с VK", caught.exception.user_message)
        self.assertNotIn("connection reset", caught.exception.user_message)

    def test_publish_post_uses_injected_client(self):
        sent = {}

        class FakeClient:
            def __init__(self, settings):
                sent["settings"] = settings

            def publish_post(self, message):
                sent["message"] = message
                from vk.api import PublishResult

                return PublishResult(post_id=5, url="https://vk.com/wall-999_5")

        result = publish_post(
            "Текст поста", settings=CONFIGURED, client_factory=FakeClient
        )
        self.assertEqual(sent["message"], "Текст поста")
        self.assertEqual(result["post_id"], 5)


class VkRoutesTest(unittest.TestCase):
    """Веб-слой: маршруты тонкие, секреты не утекают в ответы."""

    def setUp(self):
        self.client = app.test_client()

    def test_index_contains_vk_block(self):
        html = self.client.get("/").get_data(as_text=True)
        for marker in (
            "Контент для VK",
            'id="vkSection"',
            'id="vkGenerate"',
            'id="vkPostText"',
            'id="vkCounter"',
            'id="vkCopyBtn"',
            'id="vkPublishBtn"',
            "Опубликовать этот пост в группу VK?",
            "Опубликовать",
            "Отмена",
        ):
            self.assertIn(marker, html, marker)
        for label in ("Разбор вакансии", "Проверка навыков", "Совет соискателю"):
            self.assertIn(label, html, label)

    def test_index_has_no_vk_token(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("VK_ACCESS_TOKEN", html)
        self.assertNotIn("access_token", html)

    def test_meta_reports_vk_state(self):
        payload = self.client.get("/api/meta").get_json()
        self.assertIn("vk", payload)
        self.assertIn("enabled", payload["vk"])
        self.assertNotIn("access_token", str(payload["vk"]))
        self.assertEqual(len(payload["vk_post_types"]), len(POST_TYPES))

    def test_post_route_returns_preview_only(self):
        response = self.client.post(
            "/vk/post",
            json={
                "resume": CANONICAL_RESUME,
                "vacancy": CANONICAL_VACANCY,
                "post_type": POST_TYPE_BREAKDOWN,
            },
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertIn("text", payload)
        # Предпросмотр ничего не публикует: идентификатора записи нет.
        self.assertNotIn("post_id", payload)

    def test_post_route_validates_input(self):
        response = self.client.post("/vk/post", json={"resume": "", "vacancy": ""})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_post_route_rejects_unknown_type(self):
        response = self.client.post(
            "/vk/post",
            json={
                "resume": CANONICAL_RESUME,
                "vacancy": CANONICAL_VACANCY,
                "post_type": "unknown",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("тип публикации", response.get_json()["error"])

    def test_publish_route_without_settings_explains_and_does_not_crash(self):
        response = self.client.post("/vk/publish", json={"text": "Текст поста"})
        payload = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"], "VK API не настроен.")
        self.assertNotIn("Traceback", str(payload))

    def test_publish_route_rejects_empty_text(self):
        response = self.client.post("/vk/publish", json={"text": ""})
        self.assertEqual(response.status_code, 400)

    def test_app_works_without_vk_settings(self):
        for path in ("/", "/api/meta"):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        response = self.client.post(
            "/generate",
            json={
                "resume": CANONICAL_RESUME,
                "vacancy": CANONICAL_VACANCY,
                "profession": "backend",
                "style": "professional",
            },
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
