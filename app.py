"""Flask-приложение: тонкий веб-слой над пакетом `generator`.

Приложение полностью локальное:
  * нет базы данных, нет внешних API, нет CDN;
  * входные данные не сохраняются и не логируются;
  * ответы помечаются `no-store`, чтобы ничего не кэшировалось.

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
    )


@app.route("/api/meta")
def api_meta():
    """Справочник направлений и стилей для интерфейса."""
    return jsonify(
        {
            "success": True,
            "professions": [profession.as_dict() for profession in list_professions()],
            "styles": [{"id": key, "label": label} for key, label in style_choices()],
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
