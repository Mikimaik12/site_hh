"""Клиент VK API: одна функция - одна публикация.

Модуль ничего не знает про Flask. Он получает готовые настройки, делает
HTTP-запрос к `wall.post` и возвращает результат или понятную ошибку.
Именно поэтому его можно проверить в тестах без сети: транспорт
подменяется аргументом `opener`.

Актуальные детали API (проверены по документации VK, 2026):

* версия - `5.199` (https://dev.vk.com/ru/reference/version/5.199);
* адрес - `https://api.vk.ru/method/wall.post`
  (https://dev.vk.com/ru/api/api-requests);
* ключ доступа передаётся в заголовке
  `Authorization: Bearer <КЛЮЧ_ДОСТУПА>`, а не параметром `access_token`:
  так токен не попадает в адресную строку и не может утечь через логи
  или историю браузера;
* для публикации от имени сообщества нужен **токен сообщества**;
* `owner_id` сообщества передаётся со знаком «минус», а `from_group=1`
  отвечает за публикацию от имени сообщества, а не администратора;
* успех выглядит как `{"response": {"post_id": 17}}`, ошибка - как
  `{"error": {"error_code": 214, "error_msg": "..."}}`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .config import VK_API_HOST, WALL_POST_URL, VkSettings

#: Метод, которым публикуется запись на стене сообщества.
METHOD_WALL_POST = "wall.post"

#: Значение `from_group`: публиковать от имени сообщества.
FROM_GROUP = "1"

#: Идентификатор приложения в User-Agent. Пригодится в логах VK при разборе
#: инцидентов; секретом не является.
USER_AGENT = "site_hh-cover-letter-generator/1.0 (local; +https://github.com/)"

_NETWORK_ERROR = "Связь с VK не установлена. Проверьте интернет и настройки прокси."
_GENERIC_ERROR = "Не удалось опубликовать запись в VK. Проверьте настройки VK API."
_NOT_CONFIGURED = "VK API не настроен."
_UNEXPECTED_HOST = "Ответ VK пришёл с неизвестного адреса, публикация отменена."

#: Понятные сообщения для кодов ошибок VK. Ключ - `error_code` из ответа.
#: Сырые `error_msg` VK пользователю не показываются: в них нет ничего,
#: что помогло бы, зато формат не гарантирован. Токен в сообщениях
#: не участвует никогда.
_ERROR_MESSAGES = {
    5: "Ключ доступа VK отклонён. Проверьте VK_ACCESS_TOKEN в файле .env.",
    6: "VK временно отклоняет запросы. Попробуйте через минуту.",
    7: "У ключа доступа нет прав на публикацию записей.",
    14: "VK запрашивает подтверждение публикации. Опубликуйте запись вручную.",
    15: "Недостаточно прав: ключ доступа не может публиковать записи в это сообщество.",
    17: "VK требует предварительного действия. Проверьте настройки публикации сообщества.",
    25: "Ключ доступа нельзя использовать для группы. Нужен токен сообщества.",
    27: "Не удалось авторизоваться от имени сообщества. Проверьте VK_ACCESS_TOKEN и VK_GROUP_ID.",
    28: "Не удалось авторизовать приложение VK. Проверьте настройки приложения.",
    29: "Превышен лимит частоты запросов к VK. Попробуйте позже.",
    100: "VK отклонил параметры публикации.",
    1051: "Метод недоступен для этого типа профиля.",
    210: "Нет доступа к публикации записей на стене сообщества.",
    214: "Публикация запрещена настройками сообщества.",
    219: "Недавно уже была опубликована рекламная запись.",
    220: "Слишком много получателей публикации.",
    222: "В настройках сообщества запрещены ссылки в записях.",
    224: "Слишком много рекламных записей за короткий срок.",
    225: "Публикация недоступна: в сообществе не настроен VK Donut.",
    13000: "Публикация заблокирована из-за активных ограничений в сообществе.",
}


class VkApiError(Exception):
    """Ошибка обращения к VK API.

    `user_message` - то, что безопасно показать человеку. Никаких
    технических деталей и тем более токена в нём быть не должно.
    `code` - код ошибки VK, если он был.
    """

    def __init__(self, user_message: str, *, code: Optional[int] = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.code = code

    def to_dict(self) -> dict:
        """Ответ приложения: только безопасное сообщение."""
        return {"success": False, "error": self.user_message, "code": self.code}


class VkNotConfiguredError(VkApiError):
    """Публикация запрошена, а VK не настроен."""

    def __init__(self, settings: Optional[VkSettings] = None) -> None:
        super().__init__(_NOT_CONFIGURED)
        self.missing = settings.missing_settings if settings is not None else []

    def to_dict(self) -> dict:
        payload = super().to_dict()
        if self.missing:
            payload["hint"] = "Заполните в файле .env: " + ", ".join(self.missing) + "."
        return payload


@dataclass(frozen=True)
class PublishResult:
    """Результат успешной публикации."""

    post_id: int
    url: str

    def to_dict(self) -> dict:
        return {"success": True, "post_id": self.post_id, "url": self.url}


def message_for_error(code: Optional[int]) -> str:
    """Понятное сообщение по коду ошибки VK."""
    if isinstance(code, int) and code in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[code]
    return _GENERIC_ERROR


def _ensure_expected_host(request_url: str, final_url: str) -> None:
    """Проверяет, что ответ пришёл с официального домена VK.

    Защита от редиректа на сторонний хост: туда ушёл бы заголовок
    `Authorization` с токеном.
    """
    expected = (urlsplit(request_url).hostname or "").lower()
    actual = (urlsplit(final_url).hostname or "").lower()
    if actual and expected and actual != expected:
        raise VkApiError(_UNEXPECTED_HOST)
    if actual and VK_API_HOST not in actual:
        raise VkApiError(_UNEXPECTED_HOST)


def _post_json(request: Request, timeout: float) -> dict:
    """Значение по умолчанию для `opener`: запрос и разбор JSON-ответа.

    Сетевые сбои здесь не перехватываются: их превращает в `VkApiError`
    сам клиент, чтобы любая ошибка транспорта выглядела одинаково.
    """
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - адрес из константы
        final_url = getattr(response, "url", "") or ""
        _ensure_expected_host(request.full_url, final_url)
        raw = response.read()

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VkApiError(_NETWORK_ERROR) from error
    if not isinstance(payload, dict):
        raise VkApiError(_NETWORK_ERROR)
    return payload


def build_publish_request(message: str, settings: VkSettings, url: str = WALL_POST_URL) -> Request:
    """Собирает HTTP-запрос `wall.post` для публикации от имени сообщества."""
    body = urlencode(
        {
            "owner_id": settings.owner_id,
            "message": message,
            "from_group": FROM_GROUP,
            "v": settings.api_version,
        }
    ).encode("utf-8")
    return Request(
        url,
        data=body,
        method="POST",
        headers={
            # Токен - только в заголовке. В URL он не попадает.
            "Authorization": f"Bearer {settings.access_token}",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )


def parse_publish_response(payload: dict, settings: VkSettings) -> PublishResult:
    """Разбирает ответ `wall.post` в `PublishResult` или в ошибку."""
    error = payload.get("error")
    if isinstance(error, dict):
        raw_code = error.get("error_code")
        code = raw_code if isinstance(raw_code, int) else None
        raise VkApiError(message_for_error(code), code=code)

    response = payload.get("response")
    if not isinstance(response, dict):
        raise VkApiError(_GENERIC_ERROR)
    try:
        post_id = int(response["post_id"])
    except (KeyError, TypeError, ValueError) as error:
        raise VkApiError(_GENERIC_ERROR) from error
    return PublishResult(post_id=post_id, url=f"https://vk.com/wall{settings.owner_id}_{post_id}")


class VkClient:
    """Тонкая обёртка над `wall.post`.

    Аргумент `opener` - точка подмены транспорта: функция
    `(Request, timeout) -> dict`. В продакшене это `_post_json`,
    в тестах - заглушка, которая возвращает заранее заданный JSON.
    """

    def __init__(
        self,
        settings: VkSettings,
        *,
        opener: Optional[Callable[[Request, float], dict]] = None,
        url: str = WALL_POST_URL,
    ) -> None:
        self._settings = settings
        self._opener = opener or _post_json
        self._url = url

    @property
    def settings(self) -> VkSettings:
        return self._settings

    def publish_post(self, message: str) -> PublishResult:
        """Публикует запись на стене сообщества.

        Аргументы:
            message: текст поста.

        Возвращает PublishResult с идентификатором записи и ссылкой.
        """
        if not self._settings.is_configured:
            raise VkNotConfiguredError(self._settings)
        if not message.strip():
            raise VkApiError("Пустой пост публиковать нельзя.")

        request = build_publish_request(message, self._settings, self._url)
        payload = self._call(request)
        return parse_publish_response(payload, self._settings)

    def _call(self, request: Request) -> dict:
        """Обращается к транспорту и превращает любой сбой в `VkApiError`.

        Перехват здесь, а не в `_post_json`, потому что подменённый
        транспорт тоже обязан вести себя так же: пользователю не нужна
        разница между «сеть недоступна» и «сервер недоволен», а
        traceback наружу отдавать нельзя.
        """
        try:
            return self._opener(request, self._settings.timeout)
        except VkApiError:
            raise
        except Exception as error:  # noqa: BLE001 - urllib бросает разное
            raise VkApiError(_NETWORK_ERROR) from error


def publish_vk_post(
    message: str,
    settings: Optional[VkSettings] = None,
    *,
    opener: Optional[Callable[[Request, float], dict]] = None,
) -> PublishResult:
    """Публикует пост в VK - короткая обёртка для вызова из кода.

    Полный путь вызова: Flask route -> `vk.service.publish_post` ->
    эта функция -> `VkClient`. Соблазн вызвать её прямо из маршрута есть,
    но тогда проверка настроек и текста останется в веб-слое.
    """
    client = VkClient(settings if settings is not None else _default_settings(), opener=opener)
    return client.publish_post(message)


def _default_settings() -> VkSettings:
    """Настройки из окружения. Импортируется лениво, чтобы пакет `vk`
    импортировался без чтения `.env`."""
    from .config import load_settings

    return load_settings()
