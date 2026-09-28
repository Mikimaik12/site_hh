"""Настройки публикации в VK.

Все параметры читаются из переменных окружения, а при их отсутствии - из
файла `.env` в корне проекта. Файл `.env` в репозиторий не попадает
(см. `.gitignore`), а образец заполненных полей лежит в `.env.example`.

Секрет - один: `VK_ACCESS_TOKEN`. Он не выводится в HTML, не отдаётся в
JavaScript, не попадает в логи и не включается в ответы приложения.
Чтобы это не было только обещанием, у `VkSettings` переопределён
`__repr__`: даже случайный `print(settings)` в отладке покажет вместо
токна звёздочки.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

#: Актуальная версия VK API на 2026 год.
#: См. https://dev.vk.com/ru/reference/version/5.199
DEFAULT_API_VERSION = "5.199"

#: Адрес метода `wall.post`. Домен `api.vk.ru` указан в документации:
#: https://dev.vk.com/ru/api/api-requests
WALL_POST_URL = "https://api.vk.ru/method/wall.post"

#: Единственный домен, которому доверительно отдавать токен. Если ответ
#: пришёл с другого адреса (например, после редиректа), запрос считается
#: подозрительным и токен не должен туда попадать.
VK_API_HOST = "api.vk.ru"

#: Таймаут HTTP-запроса к VK, секунды.
DEFAULT_TIMEOUT = 10.0

#: Адрес сайта по умолчанию. В постах он ставится в конце текста, поэтому
#: заменяется одним значением в `.env`, а не правкой шаблонов.
DEFAULT_SITE_URL = "http://localhost:5000"

# --- Ограничения на пост --------------------------------------------------------

#: Сколько требований вакансии перечислять в посте.
MAX_REQUIREMENTS = 6

#: Сколько совпадений с резюме перечислять в посте.
MAX_MATCHES = 5

#: Сколько отсутствующих навыков перечислять в посте.
MAX_MISSING = 5

#: Максимальная длина поста. Ограничение своё, не ограничение VK:
#: в стену группы разумно публиковать текст, который читают целиком.
MAX_POST_CHARS = 4000

#: Минимальная длина поста, иначе публиковать нечего.
MIN_POST_CHARS = 1

#: Заголовок вакансии в посте обрезается до этого числа символов.
MAX_TITLE_CHARS = 70

#: Имя файла `.env` по умолчанию.
ENV_FILENAME = ".env"


# --- Чтение .env без сторонних зависимостей -----------------------------------


def load_dotenv(path: Optional[Path] = None, *, env: Optional[dict] = None, force: bool = False) -> bool:
    """Кладёт значения из `.env` в окружение, не затирая уже заданные.

    Своя реализация вместо `python-dotenv`: проект держится на одной
    зависимости (Flask), а разбирать `KEY=value` здесь тривиально.

    Аргументы:
        path:  путь к файлу; по умолчанию `.env` в корне проекта;
        env:   куда класть значения (по умолчанию `os.environ`);
        force: перечитать файл, даже если он уже читался.

    Возвращает True, если файл существовал и был разобран.
    """
    target = Path(path) if path is not None else default_env_path()
    if not target.is_file():
        return False
    target_env = os.environ if env is None else env
    for raw_line in target.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # Кавычки снимаем, содержимое внутри них сохраняем как есть.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        if key and key not in target_env:
            target_env[key] = value
    return True


def default_env_path() -> Path:
    """Путь к `.env` в корне проекта (на уровень выше пакета `vk`)."""
    return Path(__file__).resolve().parent.parent / ENV_FILENAME


# --- Настройки ------------------------------------------------------------------


@dataclass(frozen=True)
class PostLimits:
    """Сколько данных вакансии попадает в один пост."""

    requirements: int = MAX_REQUIREMENTS
    matches: int = MAX_MATCHES
    missing: int = MAX_MISSING
    max_chars: int = MAX_POST_CHARS

    def to_dict(self) -> dict:
        return {
            "requirements": self.requirements,
            "matches": self.matches,
            "missing": self.missing,
            "max_chars": self.max_chars,
        }


@dataclass(frozen=True, repr=False)
class VkSettings:
    """Настройки публикации в VK.

    Создаётся функцией `load_settings`. Публиковать можно только при
    заполненных `group_id` и `access_token`.
    """

    group_id: str = ""
    access_token: str = ""
    api_version: str = DEFAULT_API_VERSION
    site_url: str = DEFAULT_SITE_URL
    timeout: float = DEFAULT_TIMEOUT
    limits: PostLimits = field(default_factory=PostLimits)

    @property
    def is_configured(self) -> bool:
        """Готовы ли настройки к публикации."""
        return bool(self.group_id and self.access_token)

    @property
    def owner_id(self) -> int:
        """`owner_id` для `wall.post`: сообщество передаётся со знаком «минус»."""
        return -abs(int(self.group_id))

    @property
    def missing_settings(self) -> list:
        """Имена незаполненных переменных - для подсказки пользователю."""
        missing = []
        if not self.group_id:
            missing.append("VK_GROUP_ID")
        if not self.access_token:
            missing.append("VK_ACCESS_TOKEN")
        return missing

    def public_dict(self) -> dict:
        """Всё, что можно безопасно отдать браузеру.

        Токен здесь нет и не должен появиться: в интерфейсе достаточно
        знать, настроен ли VK, и знать лимит длины поста.
        """
        return {
            "enabled": self.is_configured,
            "api_version": self.api_version,
            "site_url": self.site_url,
            "limits": self.limits.to_dict(),
        }

    def __repr__(self) -> str:
        """Показывает токен как `***`, чтобы он не утёк в отладку."""
        token = "***" if self.access_token else "''"
        return (
            f"{type(self).__name__}(group_id={self.group_id!r}, access_token={token}, "
            f"api_version={self.api_version!r}, site_url={self.site_url!r}, "
            f"timeout={self.timeout!r}, limits={self.limits!r})"
        )


def normalize_group_id(raw: str) -> str:
    """Приводит значение `VK_GROUP_ID` к положительному числовому id.

    Пользователь часто вставляет не «123456», а ссылку
    `https://vk.com/club123456` или уже готовый `owner_id` со знаком
    минус. Все эти варианты должны работать.
    """
    value = (raw or "").strip().strip('"').strip("'")
    if not value:
        return ""
    for prefix in ("https://", "http://", "vk.com/", "www.vk.com/", "m.vk.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break
    value = value.rstrip("/")
    if value.startswith("@"):
        value = value[1:]
    value = value.lstrip("-")
    # Из «club123456» и «public123456» оставляем только цифры.
    digits = "".join(character for character in value if character.isdigit())
    return digits


def _int_from_env(source: Mapping[str, str], name: str, default: int, minimum: int = 1) -> int:
    """Читает положительное целое из окружения, молча откатываясь к default."""
    raw = (source.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def _float_from_env(source: Mapping[str, str], name: str, default: float) -> float:
    """Читает положительное число из окружения."""
    raw = (source.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _site_url_from_env(source: Mapping[str, str]) -> str:
    """Читает `SITE_URL` и убирает хвостовой слэш."""
    raw = (source.get("SITE_URL") or "").strip().strip('"').strip("'")
    if not raw:
        return DEFAULT_SITE_URL
    return raw.rstrip("/")


def load_settings(env: Optional[Mapping[str, str]] = None) -> VkSettings:
    """Собирает настройки публикации из окружения.

    Аргумент `env` нужен тестам: когда он передан, ни файл `.env`, ни
    реальное окружение процесса не читаются.

    Если `env` не передан, сначала один раз подгружается `.env` из корня
    проекта, затем читается `os.environ`. Значения из окружения имеют
    приоритет над файлом.
    """
    if env is not None:
        source: Mapping[str, str] = env
    else:
        load_dotenv()
        source = os.environ

    return VkSettings(
        group_id=normalize_group_id(source.get("VK_GROUP_ID", "")),
        access_token=(source.get("VK_ACCESS_TOKEN") or "").strip().strip('"').strip("'"),
        api_version=(source.get("VK_API_VERSION") or "").strip() or DEFAULT_API_VERSION,
        site_url=_site_url_from_env(source),
        timeout=_float_from_env(source, "VK_TIMEOUT", DEFAULT_TIMEOUT),
        limits=PostLimits(
            requirements=_int_from_env(source, "VK_MAX_REQUIREMENTS", MAX_REQUIREMENTS),
            matches=_int_from_env(source, "VK_MAX_MATCHES", MAX_MATCHES),
            missing=_int_from_env(source, "VK_MAX_MISSING", MAX_MISSING),
            max_chars=_int_from_env(source, "VK_MAX_POST_CHARS", MAX_POST_CHARS),
        ),
    )
