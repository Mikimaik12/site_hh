"""Публикация постов в группу ВКонтакте.

Необязательный модуль: без настроек приложение работает как обычно, а
кнопка публикации объясняет, что VK не настроен.

Устройство:

    analyzer/generator  ->  post_generator  ->  api  ->  группа VK

`post_generator` собирает текст из уже готового разбора вакансии,
`api` ходит в VK HTTP-запросом, `service` связывает их и проверяет
текст перед отправкой, `config` читает настройки из `.env`.

Публичный интерфейс пакета:

    from vk import build_post, publish_post, vk_status

Ключ доступа в наружу не выдаётся: `vk_status()` сообщает только
«настроено / не настроено».
"""

from __future__ import annotations

from .api import (
    PublishResult,
    VkApiError,
    VkClient,
    VkNotConfiguredError,
    publish_vk_post,
)
from .config import (
    DEFAULT_API_VERSION,
    MAX_MATCHES,
    MAX_MISSING,
    MAX_POST_CHARS,
    MAX_REQUIREMENTS,
    PostLimits,
    VkSettings,
    load_settings,
    normalize_group_id,
)
from .post_generator import (
    DEFAULT_POST_TYPE,
    POST_TYPE_ADVICE,
    POST_TYPE_BREAKDOWN,
    POST_TYPE_SKILL_CHECK,
    POST_TYPES,
    PostType,
    VkBlock,
    VkPost,
    VkPostError,
    find_foreign_urls,
    find_personal_data,
    generate_vk_post,
    post_types,
    verify_vk_post,
)
from .service import (
    VkValidationError,
    build_post,
    publish_post,
    validate_publishable_text,
    vk_status,
)

__all__ = [
    "DEFAULT_API_VERSION",
    "DEFAULT_POST_TYPE",
    "MAX_MATCHES",
    "MAX_MISSING",
    "MAX_POST_CHARS",
    "MAX_REQUIREMENTS",
    "POST_TYPES",
    "POST_TYPE_ADVICE",
    "POST_TYPE_BREAKDOWN",
    "POST_TYPE_SKILL_CHECK",
    "PostLimits",
    "PostType",
    "PublishResult",
    "VkBlock",
    "VkApiError",
    "VkClient",
    "VkNotConfiguredError",
    "VkPost",
    "VkPostError",
    "VkSettings",
    "VkValidationError",
    "__version__",
    "build_post",
    "find_foreign_urls",
    "find_personal_data",
    "generate_vk_post",
    "load_settings",
    "normalize_group_id",
    "post_types",
    "publish_post",
    "publish_vk_post",
    "validate_publishable_text",
    "verify_vk_post",
    "vk_status",
]

__version__ = "1.0.0"
