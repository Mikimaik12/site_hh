"""Flask-приложение: тонкий веб-слой над пакетами `generator` и `vk`.

Приложение полностью локальное:
  * нет базы данных, нет внешних AI-API, нет CDN;
  * входные данные не сохраняются и не логируются;
  * ответы помечаются `no-store`, чтобы ничего не кэшировалось.

Публикация в VK - необязательная функция. Без ключа доступа приложение
работает как раньше, а по кнопке публикации объясняет, что VK не
настроен.

Запуск:
    python app.py
    затем открыть http://127.0.0.1:5000
"""

from __future__ import annotations

import logging
from typing import Tuple

from flask import Flask, jsonify, render_template, request

from generator import (
    MAX_INPUT_CHARS,
    MIN_INPUT_CHARS,
    RECOMMENDED_INPUT_CHARS,
    STYLES,
    ValidationError,
    generate_cover_letter,
    list_professions,
    style_choices,
)
from vk import (
    VkApiError,
    VkNotConfiguredError,
    VkPostError,
    VkValidationError,
    build_post,
    post_types,
    publish_post,
    vk_status,
)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.json.ensure_ascii = False

# Логи Werkzeug печатают только метод и путь запроса, но содержимое тела
# запроса туда не попадает. Дополнительно отключаем логирование ошибок,
# чтобы текст резюме гарантированно нигде не сохранялся.
logging.getLogger("werkzeug").setLevel(logging.ERROR)


def _no_store(response):
    """Запрещает кэширование и внешние ресурсы в ответе."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


app.after_request(_no_store)


@app.route("/")
def index() -> str:
    """Главная страница со всей логикой на клиенте."""
    return render_template(
        "index.html",
        professions=[profession.as_dict() for profession in list_professions()],
        styles=[
            {"id": spec.id, "label": spec.label, "description": spec.description}
            for spec in STYLES.values()
        ],
        limits={
            "min": MIN_INPUT_CHARS,
            "recommended": RECOMMENDED_INPUT_CHARS,
            "max": MAX_INPUT_CHARS,
        },
        vk_post_types=[item.as_dict() for item in post_types()],
        vk_enabled=vk_status()["enabled"],
        vk_max_chars=vk_status()["limits"]["max_chars"],
    )


@app.route("/api/meta")
def api_meta():
    """Справочник направлений, стилей и типов постов VK."""
    return jsonify(
        {
            "success": True,
            "professions": [profession.as_dict() for profession in list_professions()],
            "styles": [{"id": key, "label": label} for key, label in style_choices()],
            "vk_post_types": [item.as_dict() for item in post_types()],
            "vk": vk_status(),
        }
    )


@app.route("/generate", methods=["POST"])
def generate():
    """Генерирует письмо.

    Запрос:
        {"resume": "...", "vacancy": "...", "profession": "backend", "style": "professional"}
    Ответ:
        {"success": true, "cover_letter": "...", "matched_skills": [...], "missing_skills": [...]}
    """
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Ожидался JSON-объект.", "field": "body"}), 400

    resume_text = payload.get("resume", "")
    vacancy_text = payload.get("vacancy", "")
    profession = payload.get("profession", "backend")
    style = payload.get("style", "professional")

    try:
        result = generate_cover_letter(
            resume_text=resume_text,
            vacancy_text=vacancy_text,
            profession=profession,
            style=style,
        )
    except ValidationError as error:
        return jsonify(error.to_dict()), 400

    return jsonify(result.to_dict())


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"success": False, "error": "Страница не найдена."}), 404


# --- VK --------------------------------------------------------------------------
# Маршруты не содержат ничего, кроме разбора запроса и ответа. Вся логика
# в пакете `vk`: сборка текста, проверки и HTTP-запрос к ВКонтакте.


def _json_payload() -> dict:
    """Тело запроса как словарь. Неверный JSON - пустой словарь."""
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


@app.route("/vk/post", methods=["POST"])
def vk_post():
    """Собирает пост для VK и отдаёт его в предпросмотр.

    Запрос:
        {"resume": "...", "vacancy": "...", "post_type": "vacancy_breakdown"}
    Ответ:
        {"success": true, "post_type": "...", "text": "...", "chars": 379, ...}

    Ничего не публикуется: этот маршрут только готовит текст.
    """
    payload = _json_payload()
    try:
        post = build_post(
            resume_text=payload.get("resume", ""),
            vacancy_text=payload.get("vacancy", ""),
            post_type=payload.get("post_type"),
        )
    except ValidationError as error:
        return jsonify(error.to_dict()), 400
    except (VkValidationError, VkPostError) as error:
        message = getattr(error, "user_message", None) or str(error)
        return jsonify({"success": False, "error": message, "field": "post_type"}), 400
    return jsonify(post.to_dict())


@app.route("/vk/publish", methods=["POST"])
def vk_publish():
    """Публикует отредактированный текст поста на стене группы.

    Маршрут вызывается только после предпросмотра и подтверждения
    пользователем - автоматической публикации в проекте нет.

    Запрос:
        {"text": "..."}
    Ответ:
        {"success": true, "post_id": 17, "url": "https://vk.com/wall-1_17"}
    """
    payload = _json_payload()
    try:
        return jsonify(publish_post(payload.get("text", "")))
    except VkValidationError as error:
        return jsonify(error.to_dict()), 400
    except VkNotConfiguredError as error:
        return jsonify(error.to_dict()), 400
    except VkApiError as error:
        return jsonify(error.to_dict()), 502


@app.errorhandler(VkPostError)
def vk_post_bug(error: VkPostError):
    """Шаблон поста нарушил собственную проверку.

    Обычным вводом не вызывается: это ошибка разработки. Пользователь
    получает нейтральное сообщение без traceback.
    """
    app.logger.error("VK post rejected by its own verification: %s", error)
    return jsonify(
        {"success": False, "error": "Не удалось собрать пост для VK. Попробуйте другой тип публикации."}
    ), 500


@app.errorhandler(500)
def server_error(_error):  # pragma: no cover - защитный обработчик
    return jsonify({"success": False, "error": "Внутренняя ошибка сервера."}), 500


def main() -> None:
    """Запускает локальный сервер только на 127.0.0.1."""
    host, port = _parse_address()
    print(f"Генератор сопроводительных писем: http://{host}:{port}")
    print("Остановка: Ctrl+C")
    app.run(host=host, port=port, debug=False, use_reloader=False)


def _parse_address() -> Tuple[str, int]:
    """Читает хост и порт из переменных окружения (по умолчанию - локальные)."""
    import os

    host = os.environ.get("HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "5000"))
    except ValueError:
        port = 5000
    return host, port


if __name__ == "__main__":
    main()
