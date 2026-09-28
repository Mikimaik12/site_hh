"""Генератор постов для группы ВКонтакте.

Модуль превращает уже готовый результат анализа вакансии в текст поста.
Анализ здесь не повторяется: на вход приходит `PairAnalysis` из
`generator.analyze_pair`, поэтому пост и сопроводительное письмо
опираются на одни и те же факты и одно и то же сопоставление навыков.

Два правила, которые модуль держит жёстко:

1. **Навык, которого нет в резюме, не выдаётся за опыт кандидата.**
   Такой навык можно назвать только там, где пост прямо говорит, что
   его в резюме нет. Для этого каждый блок текста помечен флагом
   `allows_missing_skills`, а готовый пост проверяется функцией
   `verify_vk_post`. Проверка недоверчива к самой себе: если чей-то
   будущий шаблон нарушит правило, пост не соберётся вовсе, а не
   молча уедет в группу.

2. **В посте нет персональных данных.** Имя кандидата, телефон, почта и
   любые ссылки, кроме адреса самого сайта, в текст не попадают.
   Обезличивание сделано на входе (в пост идут только навыки и название
   должности), а проверка `find_personal_data` страхует результат.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from generator.config import BANNED_PHRASES
from generator.skills import mentions_skill
from generator.text_utils import clean_fragment, join_natural, to_lower
from generator.types import PairAnalysis

from .config import MAX_POST_CHARS, MAX_TITLE_CHARS, PostLimits

# --- Типы публикаций -----------------------------------------------------------

POST_TYPE_BREAKDOWN = "vacancy_breakdown"
POST_TYPE_SKILL_CHECK = "skill_check"
POST_TYPE_ADVICE = "career_advice"

DEFAULT_POST_TYPE = POST_TYPE_BREAKDOWN

_ERROR_POST_TYPE = "Выберите тип публикации из списка: {options}."


@dataclass(frozen=True)
class PostType:
    """Один тип публикации для VK."""

    id: str
    label: str
    description: str
    #: Нужны ли резюме и вакансия. Совет соискателю работает без них.
    needs_analysis: bool

    def as_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "description": self.description}


#: Порядок важен: он же порядок карточек в интерфейсе.
POST_TYPES: Dict[str, PostType] = {
    POST_TYPE_BREAKDOWN: PostType(
        id=POST_TYPE_BREAKDOWN,
        label="Разбор вакансии",
        description="Что ищут, что совпадает с резюме, чего не хватает",
        needs_analysis=True,
    ),
    POST_TYPE_SKILL_CHECK: PostType(
        id=POST_TYPE_SKILL_CHECK,
        label="Проверка навыков",
        description="Проверка, что генератор не приписывает лишнего",
        needs_analysis=True,
    ),
    POST_TYPE_ADVICE: PostType(
        id=POST_TYPE_ADVICE,
        label="Совет соискателю",
        description="Короткий пост о том, как честно писать письмо",
        needs_analysis=False,
    ),
}


#: Маркеры списков в постах.
_BULLET = "\u2022"
_CHECK = "\u2705"
_WARNING = "\u26a0\ufe0f"

#: Заголовки разделов, которые нужно вырезать, если под ними не осталось
#: ни одного пункта. Сравнение идёт без двоеточия.
_NOISY_HEADERS = (
    "Что ищут",
    "Совпадает с резюме",
    "Есть в вакансии, но нет в резюме",
)

#: Что сказать, когда в вакансии вообще не нашлось технологий.
_NOTHING_FOUND = "Технологии в тексте вакансии не распознались, разбирать нечего."

#: Строки, которые нельзя публиковать: адреса, почта, телефоны.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?<![\d\-])"
    r"(?:\+7|8)?"
    r"[\s\-().]{0,3}"
    r"\d{3}[\s\-().]{1,3}\d{3}[\s\-().]{1,3}\d{2}[\s\-().]{1,3}\d{2}"
    r"(?!\d)"
)
#: Строка резюме такой длины уже явно не навык, а кусок текста.
_BULK_COPY_MIN_CHARS = 40


class VkPostError(ValueError):
    """Пост не прошёл проверку и не должен попасть в группу.

    Это ошибка разработки шаблона, а не пользовательский ввод: обычным
    вводом она не вызывается, поэтому поднимается наружу, а не
    превращается в тихую подмену текста.
    """


# --- Роли блоков ---------------------------------------------------------------

ROLE_TITLE = "title"
ROLE_REQUIREMENTS = "requirements"
ROLE_MATCHED = "matched"
ROLE_MISSING = "missing"
ROLE_NOTE = "note"
ROLE_LINK = "link"

#: Единственные роли, в которых можно назвать навык, отсутствующий в
#: резюме. Так называют требования вакансии - но не опыт кандидата.
ROLES_ALLOWING_MISSING = frozenset({ROLE_REQUIREMENTS, ROLE_MISSING})


# --- Блоки поста ----------------------------------------------------------------


@dataclass(frozen=True)
class VkBlock:
    """Абзац поста и его роль в проверке.

    Роль важнее флага: по ней видно, зачем блок в тексте, и правило
    «навык без опыта в резюме можно называть только в требованиях и в
    списке пробелов» не нужно держать в голове. Блок с ролью `matched`
    проверяется так же строго, как письмо.
    """

    text: str
    role: str = ROLE_NOTE

    @property
    def allows_missing_skills(self) -> bool:
        return self.role in ROLES_ALLOWING_MISSING


@dataclass
class VkPost:
    """Готовый пост для предпросмотра."""

    text: str
    post_type: str
    site_url: str
    warnings: List[str] = field(default_factory=list)
    blocks: List[VkBlock] = field(default_factory=list)
    #: Лимит длины из настроек. Отдаётся в браузер, чтобы счётчик
    #: символов предупреждал заранее, а не по факту отказа VK.
    max_chars: int = MAX_POST_CHARS

    @property
    def chars(self) -> int:
        """Длина текста, как её считает счётчик символов в интерфейсе."""
        return len(self.text)

    def to_dict(self) -> dict:
        return {
            "success": True,
            "post_type": self.post_type,
            "text": self.text,
            "chars": self.chars,
            "max_chars": self.max_chars,
            "warnings": list(self.warnings),
            "site_url": self.site_url,
            "post_type_label": POST_TYPES[self.post_type].label if self.post_type in POST_TYPES else "",
        }


# --- Проверки -------------------------------------------------------------------


def looks_like_phone(candidate: str) -> bool:
    """Отличает телефон от даты и набора цифр в номере записи."""
    return sum(character.isdigit() for character in candidate) >= 10


def find_personal_data(text: str, analysis: Optional[PairAnalysis] = None) -> List[str]:
    """Ищет в тексте то, что публиковать нельзя.

    Проверяются почта, телефон, имя кандидата и крупные куски резюме.
    Возвращает список понятных описаний; пустой список - всё чисто.
    """
    problems: List[str] = []
    if not text:
        return problems

    if _EMAIL_RE.search(text):
        problems.append("В посте есть адрес электронной почты.")

    for candidate in _PHONE_RE.findall(text):
        if looks_like_phone(candidate):
            problems.append("В посте есть номер телефона.")
            break

    if analysis is not None:
        name = _safe_name(analysis.resume.name)
        if name and name in to_lower(text):
            problems.append("В посте есть имя кандидата.")
        for chunk in _resume_chunks(analysis.resume_text):
            if chunk in text:
                problems.append("В посте есть фрагмент текста резюме.")
                break

    return problems


def find_foreign_urls(text: str, site_url: str) -> List[str]:
    """Ищет ссылки, кроме адреса самого сайта.

    В посте допустима ровно одна ссылка - та, что задана в `SITE_URL`.
    Всё остальное может оказаться личным аккаунтом.
    """
    allowed = (site_url or "").rstrip("/")
    problems: List[str] = []
    for raw in _URL_RE.findall(text or ""):
        url = raw.rstrip(".,;:!?)")
        if allowed and url.startswith(allowed):
            continue
        problems.append(f"В посте есть посторонняя ссылка: {url}")
    return problems


def find_banned_phrases(text: str) -> List[str]:
    """Ищет самовосхвательные формулировки, запрещённые в письмах."""
    lowered = to_lower(text)
    return [phrase for phrase in BANNED_PHRASES if to_lower(phrase) in lowered]


def verify_vk_post(
    blocks: Sequence[VkBlock],
    analysis: Optional[PairAnalysis],
    *,
    site_url: str,
    text: Optional[str] = None,
) -> List[str]:
    """Проверяет пост перед тем, как отдать его пользователю.

    Возвращает список проблем. Пустой список означает, что пост можно
    показывать в предпросмотре. Вызывающий код решает, что делать с
    непустым списком: `generate_vk_post` отказывается собирать пост,
    а `vk.service` сообщает пользователю про его собственные правки.
    """
    problems: List[str] = []
    body = "\n\n".join(block.text for block in blocks if block.text)
    rendered = text if text is not None else body

    if not rendered.strip():
        problems.append("Пост пустой.")
        return problems

    # 1. Навык, которого нет в резюме, нельзя выдавать за опыт кандидата.
    if analysis is not None:
        forbidden = analysis.match.forbidden_for_letter
        for block in blocks:
            if block.allows_missing_skills:
                continue
            for skill in forbidden:
                if mentions_skill(block.text, skill):
                    problems.append(f"Навык, которого нет в резюме, подан как опыт: {skill}")

    # 2. Персональные данные и посторонние ссылки.
    problems.extend(find_personal_data(rendered, analysis))
    problems.extend(find_foreign_urls(rendered, site_url))

    # 3. Запрещённые формулировки - правило проекта общее для всех текстов.
    problems.extend(find_banned_phrases(rendered))

    return problems


# --- Сборка постов -------------------------------------------------------------


def generate_vk_post(
    analysis: Optional[PairAnalysis],
    post_type: str = DEFAULT_POST_TYPE,
    site_url: str = "",
    limits: Optional[PostLimits] = None,
) -> VkPost:
    """Собирает текст поста для VK.

    Аргументы:
        analysis:   результат `generator.analyze_pair`. Для типа
                    «Совет соискателю» не нужен и может быть `None`;
        post_type:  id типа публикации;
        site_url:   адрес сайта из настройки `SITE_URL`;
        limits:     сколько данных вакансии попадает в пост.

    Возвращает VkPost. Если пост не проходит проверку, поднимается
    VkPostError: публиковать такое нельзя.
    """
    resolved_type = normalize_post_type(post_type)
    if POST_TYPES[resolved_type].needs_analysis and analysis is None:
        raise VkPostError("Для этого типа публикации нужны резюме и вакансия.")

    settings = limits or PostLimits()
    builder = _BUILDERS[resolved_type]
    warnings: List[str] = []
    blocks = builder(analysis, site_url, settings, warnings)

    text = _render(blocks, settings.max_chars)
    problems = verify_vk_post(blocks, analysis, site_url=site_url, text=text)
    if problems:
        raise VkPostError("; ".join(problems))

    return VkPost(
        text=text,
        post_type=resolved_type,
        site_url=site_url,
        warnings=warnings,
        blocks=list(blocks),
        max_chars=settings.max_chars,
    )


def normalize_post_type(post_type: Optional[str]) -> str:
    """Приводит id типа публикации к известному значению."""
    value = (post_type or "").strip().lower()
    if not value:
        return DEFAULT_POST_TYPE
    if value in POST_TYPES:
        return value
    options = ", ".join(item.label for item in POST_TYPES.values())
    raise VkPostError(_ERROR_POST_TYPE.format(options=options))


def post_types() -> List[PostType]:
    """Все типы публикаций - используется в шаблоне."""
    return list(POST_TYPES.values())


def _render(blocks: Sequence[VkBlock], max_chars: int) -> str:
    """Склеивает блоки и убирает лишние пустые строки."""
    parts = [block.text.strip("\n") for block in blocks if block.text and block.text.strip()]
    text = "\n\n".join(parts).strip()
    if len(text) > max_chars:
        # Обрезаем по границе блока, а не по символу: пост не должен
        # заканчиваться половиной предложения.
        trimmed: List[str] = []
        for part in parts:
            candidate = "\n\n".join(trimmed + [part])
            if trimmed and len(candidate) > max_chars:
                break
            trimmed.append(part)
        text = "\n\n".join(trimmed).rstrip()
    # Удаление пустого заголовка оставляет после него лишнюю пустую строку.
    return re.sub(r"\n{3,}", "\n\n", _drop_noisy_headers(text)).strip()


def _drop_noisy_headers(text: str) -> str:
    """Убирает заголовок, под которым не осталось ни одного пункта.

    Так случается, когда вакансия почти пустая: «Что ищут:» без списка
    выглядит как ошибка вёрстки.
    """
    lines = text.split("\n")
    result: List[str] = []
    for index, line in enumerate(lines):
        # Заголовок заканчивается двоеточием, а в списке он без него.
        if line.strip().rstrip(":") in _NOISY_HEADERS:
            following = lines[index + 1].strip() if index + 1 < len(lines) else ""
            if not following or following.rstrip(":") in _NOISY_HEADERS:
                continue
        result.append(line)
    return "\n".join(result).strip()


def _gaps_summary(vacancy_skills: Sequence[str]) -> str:
    """Фраза для случая, когда пробелов нет.

    Важно не перепутать «всё совпало» с «нечего сравнивать»: если
    технологии в вакансии вообще не нашлись, говорить про полное
    совпадение нельзя.
    """
    if not vacancy_skills:
        return _NOTHING_FOUND
    return "Все обязательные требования из вакансии есть в резюме."


def _tail(site_url: str, label: str) -> str:
    """Завершающая ссылка на сайт. Единственная ссылка в посте."""
    return f"{label}\n{site_url}" if site_url else label


def _header(icon: str, prefix: str, analysis: Optional[PairAnalysis]) -> str:
    """Заголовок поста: эмодзи, суть и должность из вакансии.

    Если должность не нашлась, она просто не добавляется - фраза
    «Разбираем вакансию IT-вакансию» читается как ошибка, а не как пост.
    """
    title = safe_fragment(analysis.vacancy.title) if analysis is not None else ""
    return f"{icon} {prefix} {title}" if title else f"{icon} {prefix}"


def _build_breakdown(
    analysis: Optional[PairAnalysis],
    site_url: str,
    limits: PostLimits,
    warnings: List[str],
) -> List[VkBlock]:
    """Тип 1. Разбор вакансии: требования, совпадения, пробелы."""
    if analysis is None:
        raise VkPostError("Для разбора вакансии нужны резюме и вакансия.")

    vacancy = analysis.vacancy
    match = analysis.match
    if not vacancy.title:
        warnings.append("Должность в вакансии не найдена - в посте она общая.")

    required = vacancy.all_skills[: limits.requirements]
    matched = match.matched[: limits.matches]
    missing = match.missing[: limits.missing]

    if not required:
        warnings.append("В вакансии не нашлось технологий - пост получится без разбора требований.")
    if not matched:
        warnings.append("Совпадений с резюме не нашлось - письмо выйдет более общим.")

    blocks = [VkBlock(_header("\U0001f50e", "Разбираем вакансию", analysis), ROLE_TITLE)]

    blocks.append(
        VkBlock(
            "Что ищут:\n" + _bullets(required) if required else "Что ищут:",
            ROLE_REQUIREMENTS,
        )
    )

    if matched:
        blocks.append(VkBlock("Совпадает с резюме:\n" + _bullets(matched, _CHECK), ROLE_MATCHED))
    else:
        blocks.append(VkBlock("Совпадений не нашлось.", ROLE_MATCHED))

    if missing:
        # Навыки без опыта в резюме названы прямо как отсутствующие -
        # именно поэтому блок помечен ролью `missing`.
        blocks.append(
            VkBlock(
                "Есть в вакансии, но нет в резюме:\n" + _bullets(missing, _WARNING),
                ROLE_MISSING,
            )
        )
        blocks.append(
            VkBlock(
                "Генератор не стал приписывать кандидату отсутствующие навыки: "
                "письмо собирается только из того, что подтверждено резюме.",
                ROLE_NOTE,
            )
        )
    else:
        blocks.append(VkBlock(_gaps_summary(vacancy.all_skills), ROLE_MISSING))

    blocks.append(VkBlock(_tail(site_url, "\U0001f517 Попробовать генератор:"), ROLE_LINK))
    return blocks


def _build_skill_check(
    analysis: Optional[PairAnalysis],
    site_url: str,
    limits: PostLimits,
    warnings: List[str],
) -> List[VkBlock]:
    """Тип 2. Проверка навыков: что генератор не добавляет лишнего."""
    if analysis is None:
        raise VkPostError("Для проверки навыков нужны резюме и вакансия.")

    match = analysis.match
    absent = (match.missing + match.optional_missing)[: limits.missing]

    blocks = [VkBlock(_header("\U0001f9ea", "Проверяем генератор на вакансии", analysis), ROLE_TITLE)]

    if absent:
        blocks.append(VkBlock("В вакансии есть " + join_natural(absent) + ".", ROLE_MISSING))
        blocks.append(VkBlock("В резюме этих навыков нет.", ROLE_NOTE))
        blocks.append(VkBlock("Генератор не добавляет их в сопроводительное письмо.", ROLE_NOTE))
        blocks.append(
            VkBlock("Письмо строится только на подтверждённом опыте кандидата.", ROLE_NOTE)
        )
    elif not (analysis.vacancy.all_skills):
        blocks.append(VkBlock(_NOTHING_FOUND, ROLE_NOTE))
        blocks.append(
            VkBlock(
                "Проверка всё равно идёт по каждому навыку отдельно: "
                "в письмо попадает только то, что подтверждено резюме.",
                ROLE_NOTE,
            )
        )
    else:
        blocks.append(VkBlock("Все обязательные требования вакансии нашлись в резюме.", ROLE_MISSING))
        blocks.append(
            VkBlock(
                "Но проверка всё равно идёт по каждому навыку отдельно: "
                "в письмо попадает только то, что подтверждено резюме.",
                ROLE_NOTE,
            )
        )

    blocks.append(VkBlock(_tail(site_url, "\U0001f517 Попробовать:"), ROLE_LINK))
    return blocks


def _build_advice(
    analysis: Optional[PairAnalysis],
    site_url: str,
    limits: PostLimits,
    warnings: List[str],
) -> List[VkBlock]:
    """Тип 3. Совет соискателю. Работает без резюме и вакансии."""
    del analysis, limits
    return [
        VkBlock("\U0001f4a1 Совет для IT-соискателю", ROLE_TITLE),
        VkBlock(
            "Если в вакансии есть технология, которой нет в вашем резюме, "
            "не стоит автоматически писать в сопроводительном письме, что вы ей владеете.",
            ROLE_NOTE,
        ),
        VkBlock(
            "Лучше показать реальные совпадения между вашим опытом и требованиями вакансии.",
            ROLE_NOTE,
        ),
        VkBlock(_tail(site_url, "\U0001f517 Создать сопроводительное письмо:"), ROLE_LINK),
    ]

_BUILDERS = {
    POST_TYPE_BREAKDOWN: _build_breakdown,
    POST_TYPE_SKILL_CHECK: _build_skill_check,
    POST_TYPE_ADVICE: _build_advice,
}


# --- Вспомогательное ------------------------------------------------------------


def _bullets(items: Sequence[str], marker: str = _BULLET) -> str:
    """Список с маркерами."""
    return "\n".join(f"{marker} {item}" for item in items)


def safe_fragment(text: str, limit: int = MAX_TITLE_CHARS) -> str:
    """Готовит короткий фрагмент чужого текста для публичной публикации.

    Вырезает всё, что нельзя показывать группе: почту, телефон и
    ссылки. Заголовок вакансии приходит из пользовательского ввода,
    поэтому предполагать, что он чистый, нельзя.
    """
    fragment = clean_fragment(text or "", max(limit * 2, limit))
    fragment = _EMAIL_RE.sub(" ", fragment)
    fragment = _URL_RE.sub(" ", fragment)
    fragment = " ".join(_strip_phones(fragment))
    return clean_fragment(fragment, limit).strip(" ,;:-\u2013\u2014")


def _strip_phones(text: str) -> List[str]:
    """Заменяет номера телефонов на пустые строки."""
    return [
        " " if looks_like_phone(match) else match
        for match in _PHONE_RE.split(text)
    ]


def _safe_name(name: str) -> str:
    """Имя кандидата, пригодное для поиска в тексте.

    Проверяется только полное имя из двух и более частей: короткое или
    однословное «имя» слишком часто совпадает с обычным словом в посте
    («QA», «Dev»), и искать его бессмысленно.
    """
    value = clean_fragment(to_lower(name or ""), 60)
    parts = [part for part in re.split(r"[\s-]+", value) if part]
    if len(parts) < 2 or any(len(part) < 3 for part in parts):
        return ""
    return " ".join(parts)


def _resume_chunks(resume_text: str) -> List[str]:
    """Длинные строки резюме - их появление в посте означает утечку."""
    chunks = []
    for line in (resume_text or "").split("\n"):
        candidate = clean_fragment(line, 200)
        if len(candidate) >= _BULK_COPY_MIN_CHARS:
            chunks.append(candidate)
    return chunks
