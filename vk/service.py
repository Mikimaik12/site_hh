"""Сервисный слой публикации в VK.

Схема вызовов, заданная проектом:

    Flask route
        -> vk.service (здесь)
            -> vk.post_generator  (сборка текста)
            -> vk.api             (HTTP-запрос к VK)

Маршрут не знает ни про HTTP-запросы, ни про правила VK, а клиент не
знает ни про Flask, ни про резюме. Поэтому публикацию можно проверить
в тестах без сервера и без сети.

Здесь же - последняя проверка перед отправкой. Пользователь правит
текст поста вручную, поэтому сервер проверяет именно тот текст, который
уйдёт в группу: пустой он или нет, не содержит ли персональных данных
и посторонних ссылок.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from generator import ValidationError, analyze_pair
from generator.types import PairAnalysis

from .api import PublishResult, VkApiError, VkClient, VkNotConfiguredError
from .config import MIN_POST_CHARS, VkSettings, load_settings
from .post_generator import (
    POST_TYPES,
    VkPost,
    VkPostError,
    find_foreign_urls,
    find_personal_data,
    generate_vk_post,
    normalize_post_type,
)

#: Сообщения о негодном для публикации тексте.
_ERROR_EMPTY = "Пост пустой. Напишите текст в поле предпросмотра."
_ERROR_TOO_LONG = "Пост слишком длинный: максимум {limit} символов."
_ERROR_PERSONAL = "Уберите из поста персональные данные: {details}."
_ERROR_FOREIGN_URL = "Уберите из поста постороннюю ссылку: {details}."


class VkValidationError(ValueError):
    """Пользовательский ввод не годится для публикации.

    Отдельный тип от `VkApiError`: это не сбой VK, а просьба поправить
    текст, и ответ должен быть 400, а не 502.
    """

    def __init__(self, user_message: str, *, field: str = "text", code: Optional[int] = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.field = field
        self.code = code

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error": self.user_message,
            "field": self.field,
            "code": self.code,
        }


#: Клиент, которым пользуется сервис. Подменяется в тестах.
ClientFactory = Callable[[VkSettings], VkClient]

__all__ = [
    "ClientFactory",
    "VkPostError",
    "VkValidationError",
    "build_post",
    "publish_post",
    "validate_publishable_text",
    "vk_status",
]


def vk_status() -> dict:
    """Состояние интеграции для интерфейса.

    Возвращается только то, что безопасно отдавать браузеру: сам токен
    и идентификатор сообщества наружу не уходят.
    """
    return load_settings().public_dict()


def build_post(
    resume_text: str = "",
    vacancy_text: str = "",
    post_type: Optional[str] = None,
    *,
    settings: Optional[VkSettings] = None,
    analysis: Optional[PairAnalysis] = None,
) -> VkPost:
    """Собирает пост для предпросмотра.

    Резюме и вакансия разбираются существующим анализатором один раз
    (`generator.analyze_pair`) - генератор поста получает готовые факты
    и не анализирует тексты заново. Для типа «Совет соискателю» входные
    тексты не нужны вовсе.

    Аргумент `analysis` позволяет вызывающему коду передать уже
    готовый разбор и не платить за анализ второй раз.

    Возвращает VkPost. Ошибки входных данных поднимаются как
    `generator.ValidationError` - те же самые, что у `/generate`.
    """
    resolved_type = normalize_post_type(post_type)
    if analysis is None and POST_TYPES[resolved_type].needs_analysis:
        analysis = analyze_pair(resume_text, vacancy_text)

    active_settings = settings if settings is not None else load_settings()
    post = generate_vk_post(
        analysis=analysis,
        post_type=resolved_type,
        site_url=active_settings.site_url,
        limits=active_settings.limits,
    )
    if active_settings.site_url == _default_site_url():
        post.warnings.append(
            "В посте стоит локальный адрес из настроек по умолчанию - задайте SITE_URL в .env."
        )
    return post


def validate_publishable_text(text: str, settings: Optional[VkSettings] = None) -> str:
    """Проверяет текст, который пользователь собирается опубликовать.

    Публикуется именно отредактированный текст из предпросмотра,
    поэтому проверять надо его, а не результат генератора.

    Проверяются: пустота, длина, персональные данные и посторонние
    ссылки. Проверку «навык есть в резюме» повторить нельзя - резюме
    здесь уже недоступно, и текст к этому моменту мог переписать сам
    человек. Это осознанно: право отредактировать пост целиком важнее
    автоматической проверки.

    Возвращает текст для отправки или поднимает `VkValidationError`.
    """
    active_settings = settings if settings is not None else load_settings()
    message = (text or "").strip()
    if len(message) < MIN_POST_CHARS:
        raise VkValidationError(_ERROR_EMPTY)
    if len(message) > active_settings.limits.max_chars:
        raise VkValidationError(_ERROR_TOO_LONG.format(limit=active_settings.limits.max_chars))

    personal = find_personal_data(message)
    if personal:
        raise VkValidationError(_ERROR_PERSONAL.format(details=_join(personal)))
    foreign = find_foreign_urls(message, active_settings.site_url)
    if foreign:
        raise VkValidationError(_ERROR_FOREIGN_URL.format(details=_join(foreign)))
    return message


def publish_post(
    text: str,
    *,
    settings: Optional[VkSettings] = None,
    client_factory: Optional[ClientFactory] = None,
) -> dict:
    """Публикует пост в группу.

    Вызывается только после того, как пользователь увидел предпросмотр,
    отредактировал текст и подтвердил публикацию. Никаких действий «по
    умолчанию» здесь быть не может: единственная точка входа - явный
    POST-запрос от браузера.

    Аргументы:
        text:            готовый текст поста;
        settings:        настройки; по умолчанию из окружения;
        client_factory:  подмена клиента в тестах.

    Возвращает `{"success": True, "post_id": ..., "url": ...}`.
    Поднимает `VkValidationError` (400), `VkNotConfiguredError` (400)
    или `VkApiError` (502) - сообщения в них безопасны для показа.
    """
    active_settings = settings if settings is not None else load_settings()
    message = validate_publishable_text(text, active_settings)
    factory = client_factory or (lambda config: VkClient(config))
    result = _publish_with(factory, message, active_settings)
    return result.to_dict()


def _publish_with(
    factory: ClientFactory,
    message: str,
    settings: VkSettings,
) -> PublishResult:
    """Создаёт клиент и публикует. Отделён ради подмены в тестах."""
    if not settings.is_configured:
        raise VkNotConfiguredError(settings)
    client = factory(settings)
    publish = getattr(client, "publish_post", None)
    if not callable(publish):
        raise VkApiError("Не удалось опубликовать запись в VK. Проверьте настройки VK API.")
    return publish(message)


def _join(items: List[str]) -> str:
    """Склеивает список причин в одну строку."""
    unique = list(dict.fromkeys(items))
    if len(unique) == 1:
        return unique[0]
    return ", ".join(unique[:-1]) + " и " + unique[-1]


def _default_site_url() -> str:
    """Адрес сайта по умолчанию - чтобы отличить его от заданного в `.env`."""
    from .config import DEFAULT_SITE_URL

    return DEFAULT_SITE_URL
