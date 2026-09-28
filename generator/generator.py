"""Сборка сопроводительного письма.

Модуль связывает воедино анализ, сопоставление и шаблоны профессий.
Он же отвечает за два важных свойства результата:

1. Достоверность. Перед возвратом письмо проверяется функцией
   `verify_cover_letter`. Если в тексте нашлось утверждение о навыке,
   которого нет в резюме, абзац удаляется.
2. Контролируемую длину (для стиля «Краткий»).
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable, List, Optional, Sequence, Tuple

from . import professions as professions_module
from .analyzer import analyze_resume, analyze_vacancy, detect_profession
from .config import (
    BANNED_PHRASES,
    BRIEF_MAX_CHARS,
    BRIEF_MIN_CHARS,
    MAX_INPUT_CHARS,
    MAX_SKILLS_MENTIONED,
    MIN_INPUT_CHARS,
    MIN_MEANINGFUL_WORDS,
)
from .matcher import match_skills
from .phrases import PhrasePicker
from .professions import build_paragraphs, get_profession, is_known_profession
from .professions.base import LetterContext, generic_stack_line
from .styles import get_style, is_known_style
from .text_utils import (
    clean_fragment,
    first_sentences,
    join_natural,
    normalize_inline,
    to_lower,
    truncate,
    word_count,
)
from .types import GenerationResult, MatchResult, ResumeFacts, VacancyFacts

_ERROR_RESUME_EMPTY = "Добавьте текст резюме."
_ERROR_VACANCY_EMPTY = "Добавьте описание вакансии."
_ERROR_RESUME_SHORT = "Текст резюме слишком короткий. Вставьте полный текст резюме."
_ERROR_VACANCY_SHORT = "Описание вакансии слишком короткое. Вставьте полное описание вакансии."
_ERROR_PROFESSION = "Выберите направление из списка: {options}."
_ERROR_STYLE = "Выберите стиль письма из списка: {options}."

_YEARS_CLAIM_RE = re.compile(
    r"\b\d{1,2}\s*(?:лет|года|год|years?|yrs?)\b", re.IGNORECASE
)
_QUOTED_RE = re.compile(r"«([^»]{2,200})»")

#: На сколько поднимается лимит навыков, если «Краткому» письму не хватает
#: длины. Шаг небольшой: одно за другим навыки выглядят естественнее, чем
#: длинный список в один абзац.
_SKILL_CAP_STEP = 3


class ValidationError(ValueError):
    """Ошибка входных данных с понятным сообщением для пользователя."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message

    def to_dict(self) -> dict:
        return {"success": False, "error": self.message, "field": self.field}


# --- Валидация -----------------------------------------------------------------


def validate_resume(text: Optional[str]) -> str:
    """Проверяет резюме и возвращает нормализованный текст."""
    value = (text or "").strip()
    if not value:
        raise ValidationError("resume", _ERROR_RESUME_EMPTY)
    if len(value) > MAX_INPUT_CHARS:
        raise ValidationError(
            "resume", f"Резюме слишком большое: максимум {MAX_INPUT_CHARS} символов."
        )
    if len(value) < MIN_INPUT_CHARS or word_count(value) < MIN_MEANINGFUL_WORDS:
        raise ValidationError("resume", _ERROR_RESUME_SHORT)
    return value


def validate_vacancy(text: Optional[str]) -> str:
    """Проверяет описание вакансии и возвращает нормализованный текст."""
    value = (text or "").strip()
    if not value:
        raise ValidationError("vacancy", _ERROR_VACANCY_EMPTY)
    if len(value) > MAX_INPUT_CHARS:
        raise ValidationError(
            "vacancy", f"Вакансия слишком большая: максимум {MAX_INPUT_CHARS} символов."
        )
    if len(value) < MIN_INPUT_CHARS or word_count(value) < MIN_MEANINGFUL_WORDS:
        raise ValidationError("vacancy", _ERROR_VACANCY_SHORT)
    return value


def validate_profession(profession_id: str) -> str:
    """Проверяет, что направление поддерживается."""
    value = (profession_id or "").strip().lower()
    if not is_known_profession(value):
        options = ", ".join(item.label for item in professions_module.list_professions())
        raise ValidationError("profession", _ERROR_PROFESSION.format(options=options))
    return value


def validate_style(style_id: str) -> str:
    """Проверяет, что стиль поддерживается."""
    value = (style_id or "").strip().lower()
    if not is_known_style(value):
        from .styles import style_choices

        options = ", ".join(label for _, label in style_choices())
        raise ValidationError("style", _ERROR_STYLE.format(options=options))
    return value


# --- Проверка достоверности ----------------------------------------------------


def _without_spans(text: str, spans: Iterable[str]) -> str:
    """Убирает из текста заранее разрешённые фрагменты (компания, должность)."""
    result = text
    for span in spans:
        if span and len(span) > 1:
            result = result.replace(span, " ")
    return result


def verify_cover_letter(
    cover_letter: str,
    resume: ResumeFacts,
    vacancy: Optional[VacancyFacts] = None,
    match: Optional[MatchResult] = None,
    allowed_spans: Sequence[str] = (),
) -> List[str]:
    """Проверяет письмо на недостоверные утверждения.

    Возвращает список проблем (пустой список - всё в порядке):
    * упоминание навыка, которого нет в резюме;
    * выдуманная цитата (текст в кавычках, которого нет в исходных текстах);
    * запрещённые самовосхвательные формулировки;
    * заявленный стаж работы, которого нет в резюме.
    """
    problems: List[str] = []
    if not cover_letter.strip():
        return ["Письмо пустое."]

    # 1. Навыки, которых нет в резюме.
    forbidden = set(match.forbidden_for_letter) if match else set()
    if forbidden:
        check_text = to_lower(_without_spans(cover_letter, allowed_spans))
        for skill in sorted(forbidden):
            if _mentions_skill(check_text, skill):
                problems.append(f"Упомянут навык, отсутствующий в резюме: {skill}")

    # 2. Цитаты: в письме допустимы только реальные фрагменты исходных текстов.
    source = normalize_inline(
        f"{resume.name} {resume.current_title} {' '.join(resume.companies)} "
        f"{' '.join(resume.positions)} {' '.join(resume.education)} "
        + (
            f"{vacancy.title} {vacancy.company} {' '.join(vacancy.responsibilities)} "
            f"{' '.join(vacancy.requirements)}"
            if vacancy
            else ""
        )
    )
    source_lower = to_lower(source)
    source_squeezed = source_lower.replace(" ", "")
    for quote in _QUOTED_RE.findall(cover_letter):
        candidate = to_lower(normalize_inline(quote))
        if candidate and (candidate in source_lower or candidate.replace(" ", "") in source_squeezed):
            continue
        problems.append(f"Цитата без источника: «{clean_fragment(quote, 60)}»")

    # 3. Запрещённые формулировки.
    lowered = to_lower(cover_letter)
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            problems.append(f"Запрещённая формулировка: {phrase}")

    # 4. Стаж работы, которого нет в резюме.
    if resume.years_of_experience is None and _YEARS_CLAIM_RE.search(_without_spans(cover_letter, allowed_spans)):
        problems.append("Заявлен стаж работы, которого нет в резюме.")

    return problems


def _mentions_skill(text_lower: str, skill: str) -> bool:
    """Проверяет, что навык упомянут в тексте (с границами слова)."""
    name = to_lower(skill)
    if not name:
        return False
    return f" {name} " in f" {text_lower} " or f"{name}." in text_lower or f"{name}," in text_lower


# --- Контроль длины для стиля «Краткий» ---------------------------------------


def _body_and_closing(paragraphs: Sequence[str]) -> Tuple[List[str], str]:
    """Отделяет последний абзац (завершение) от тела письма."""
    if not paragraphs:
        return [], ""
    return list(paragraphs[:-1]), paragraphs[-1]


def _fit_length(paragraphs: List[str], ctx: LetterContext) -> List[str]:
    """Приводит письмо к ограничениям по длине выбранного стиля."""
    letter = "\n\n".join(paragraphs)
    if not ctx.style.brief or len(letter) <= BRIEF_MAX_CHARS:
        return paragraphs

    body, closing_text = _body_and_closing(paragraphs)
    # Отбрасываем необязательные блоки с конца тела.
    while body and len("\n\n".join(body + [closing_text])) > BRIEF_MAX_CHARS:
        body.pop()
    if not body:
        body = [first_sentences(paragraphs[0], 1)] if paragraphs else []

    letter = "\n\n".join(body + [closing_text])
    if len(letter) > BRIEF_MAX_CHARS:
        shortened = first_sentences("\n\n".join(body), max(2, len(body) * 2))
        letter = "\n\n".join([truncate(shortened, BRIEF_MAX_CHARS - len(closing_text) - 2), closing_text])
    return [paragraph for paragraph in letter.split("\n\n") if paragraph]


def _enrich_short_letter(paragraphs: List[str], ctx: LetterContext) -> List[str]:
    """Добавляет подтверждённые детали, если письмо получилось слишком коротким.

    Добавляются только факты из резюме. Порядок дополнений - от самого
    релевантного к наименее релевантному: сначала стек и задачи, потом
    стаж с компанией, и только затем то, чего стиль письма по умолчанию
    не включает (soft skills, образование).

    Нижняя граница `BRIEF_MIN_CHARS` - цель, а не гарантия: если в
    резюме не осталось неиспользованных фактов, письмо останется
    коротким, а пользователь увидит предупреждение. Добивать длину
    выдуманными формулировками нельзя.
    """
    letter = "\n\n".join(paragraphs)
    if len(letter) >= BRIEF_MIN_CHARS:
        return paragraphs

    body, closing_text = _body_and_closing(paragraphs)
    additions: List[str] = []

    extra_skills = _unmentioned_skills(ctx.resume.skills, letter, ctx.match.matched)[:5]
    if extra_skills:
        additions.append(f"Также есть опыт: {join_natural(extra_skills)}.")

    extra_tasks = ctx.safe_responsibilities(limit=4)
    if len(extra_tasks) > ctx.style.max_tasks:
        quoted = join_natural([f"«{task}»" for task in extra_tasks[ctx.style.max_tasks:]], conjunction="и")
        additions.append(f"Также знакомы задачи: {quoted}.")

    # Блок опыта уже может содержать стаж и компанию - тогда повторять
    # их в конце письма незачем.
    if (
        ctx.resume.years_text
        and ctx.resume.last_company
        and not (
            _skill_mentioned(ctx.resume.last_company, letter)
            and _skill_mentioned(ctx.resume.years_text, letter)
        )
    ):
        additions.append(
            f"Суммарно {ctx.resume.years_text} в {ctx.profession.focus_prepositional}, "
            f"последнее место работы - «{ctx.resume.last_company}»."
        )

    if ctx.resume.soft_skills and ctx.style.include_soft_skills_block:
        # Если soft skills уже есть в письме, второй раз их перечислять
        # не нужно - иначе один и тот же список дважды в одном письме.
        fresh_soft = _unmentioned_skills(ctx.resume.soft_skills, letter)[:3]
        if fresh_soft:
            additions.append(f"Отдельно про soft skills: {join_natural(fresh_soft)}.")

    if ctx.resume.education and ctx.style.include_education_block:
        # Образование тоже может быть уже в письме: «По образованию - ...»
        # из блока шаблона и «Образование: ...» из дополнения - одно и то же.
        if not _skill_mentioned(ctx.resume.education[0], letter):
            additions.append(f"Образование: {clean_fragment(ctx.resume.education[0], 90)}.")

    for addition in additions:
        # Не дублируем то, что уже есть в письме.
        if _sentence_present(addition, letter):
            continue
        candidate = "\n\n".join(body + [addition, closing_text])
        if len(candidate) > BRIEF_MAX_CHARS:
            break
        body.append(addition)
        letter = candidate
        if len(letter) >= BRIEF_MIN_CHARS:
            break
    return body + [closing_text] if body else paragraphs


def _widen_skill_cap(paragraphs: List[str], ctx: LetterContext) -> List[str]:
    """Расширяет список навыков, если «Краткое» письмо не дотянуло до цели.

    Стиль «Краткий» сознательно перечисляет мало навыков, но если даже
    после дополнений письмо короче `BRIEF_MIN_CHARS`, значит, часть
    подтверждённых совпадений с вакансией не попала в текст просто из-за
    этого ограничения. Это не выдумка, а неиспользованные факты резюме,
    поэтому лимит поднимается - и письмо пересобирается заново тем же
    детерминированным выбором формулировок.

    Шаг делается, пока есть что показать, пока письмо короче цели и пока
    текст не вылезет за `BRIEF_MAX_CHARS`. Останавливается и тогда, когда
    новый вариант не длиннее предыдущего: значит, показывать больше
    нечего и остаётся только предупредить пользователя.
    """
    if not ctx.style.brief:
        return paragraphs

    best = paragraphs
    best_length = len("\n\n".join(paragraphs))
    if best_length >= BRIEF_MIN_CHARS:
        return best

    original_cap = ctx.skill_cap
    try:
        while ctx.skills_limit < MAX_SKILLS_MENTIONED and best_length < BRIEF_MIN_CHARS:
            # `stack_skills()` обрезается по лимиту, поэтому число доступных
            # навыков узнаём, сравнивая список до и после его повышения.
            shown = len(ctx.stack_skills())
            ctx.skill_cap = min(MAX_SKILLS_MENTIONED, ctx.skills_limit + _SKILL_CAP_STEP)
            if len(ctx.stack_skills()) <= shown:
                ctx.skill_cap = original_cap
                break  # показать больше нечего: в резюме нет других навыков
            candidate = build_paragraphs(ctx)
            if not ctx.has_stack:
                generic = generic_stack_line(ctx)
                if generic:
                    candidate.insert(min(2, len(candidate) - 1), generic)
            # Пересборка возвращает исходный набор абзацев, поэтому
            # дополнения для короткого письма применяются к нему заново.
            candidate = _fit_length(candidate, ctx)
            candidate = _enrich_short_letter(candidate, ctx)
            length = len("\n\n".join(candidate))
            if length > BRIEF_MAX_CHARS or length <= best_length:
                break
            best, best_length = candidate, length
    finally:
        ctx.skill_cap = original_cap
    return best


def _skill_mentioned(skill: str, letter: str) -> bool:
    """Проверяет, упомянут ли навык в уже собранном тексте письма."""
    needle = to_lower(skill)
    return bool(needle) and needle in to_lower(letter)


def _unmentioned_skills(
    skills: Sequence[str], letter: str, matched: Sequence[str] = ()
) -> List[str]:
    """Навыки резюме, которых ещё нет в письме и которые не нужны вакансии."""
    skip = {to_lower(item) for item in matched}
    return [
        skill
        for skill in skills
        if to_lower(skill) not in skip and not _skill_mentioned(skill, letter)
    ]


def _sentence_present(sentence: str, letter: str) -> bool:
    """Проверяет, нет ли уже такого предложения в письме."""
    needle = to_lower(sentence).strip(" .!?").replace("ё", "е")
    haystack = to_lower(letter).replace("ё", "е")
    return bool(needle) and needle in haystack


# --- Основная функция ----------------------------------------------------------


def _build_seed(resume_text: str, vacancy_text: str, profession: str, style: str, seed: Optional[str]) -> str:
    """Собирает зерно детерминированного выбора фраз."""
    if seed is not None:
        return str(seed)
    payload = "|".join(
        [
            profession,
            style,
            hashlib.sha256(resume_text.strip().encode("utf-8")).hexdigest(),
            hashlib.sha256(vacancy_text.strip().encode("utf-8")).hexdigest(),
        ]
    )
    return payload


def generate_cover_letter(
    resume_text: str,
    vacancy_text: str,
    profession: str = "backend",
    style: str = "professional",
    seed: Optional[str] = None,
) -> GenerationResult:
    """Создаёт сопроводительное письмо.

    Аргументы:
        resume_text:  текст резюме;
        vacancy_text: текст описания вакансии;
        profession:   id направления (backend, frontend, manual_qa, automation_qa);
        style:        id стиля (professional, brief, confident);
        seed:         необязательное зерно выбора фраз (для тестов и отладки).

    Возвращает GenerationResult с полями cover_letter, matched_skills,
    missing_skills и информационными предупреждениями.
    """
    resume_input = validate_resume(resume_text)
    vacancy_input = validate_vacancy(vacancy_text)
    profession_id = validate_profession(profession)
    style_id = validate_style(style)

    resume_facts = analyze_resume(resume_input)
    vacancy_facts = analyze_vacancy(vacancy_input)
    match = match_skills(resume_facts, vacancy_facts)

    style_spec = get_style(style_id)
    ctx = LetterContext(
        resume=resume_facts,
        vacancy=vacancy_facts,
        match=match,
        style=style_spec,
        picker=PhrasePicker(_build_seed(resume_input, vacancy_input, profession_id, style_id, seed)),
        profession=get_profession(profession_id),
    )

    paragraphs = build_paragraphs(ctx)

    # Если в резюме нет ни одного стека - добавляем мотивационный абзац
    # вместо блока про технологии, чтобы письмо не выглядело пустым.
    if not ctx.has_stack:
        generic = generic_stack_line(ctx)
        if generic:
            insert_at = min(2, len(paragraphs) - 1)
            paragraphs.insert(insert_at, generic)

    paragraphs = _fit_length(paragraphs, ctx)
    paragraphs = _enrich_short_letter(paragraphs, ctx)
    # Предупреждение о длине показывается пользователю, поэтому перед ним
    # стоит убедиться, что лимит навыков действительно мешает, а не сама
    # резюме бедно фактами.
    paragraphs = _widen_skill_cap(paragraphs, ctx)
    paragraphs = _enforce_truthfulness(paragraphs, ctx)

    cover_letter = "\n\n".join(paragraphs).strip()

    return GenerationResult(
        cover_letter=cover_letter,
        matched_skills=list(match.matched),
        missing_skills=list(match.missing),
        optional_skills=list(match.optional),
        resume_only_skills=list(match.resume_only),
        warnings=_collect_warnings(ctx, cover_letter),
        profession=profession_id,
        style=style_id,
        detected_profession=detect_profession(vacancy_input, professions_module.list_professions()) or "",
        vacancy_company=vacancy_facts.company,
        vacancy_title=vacancy_facts.title,
    )


def _enforce_truthfulness(paragraphs: List[str], ctx: LetterContext) -> List[str]:
    """Удаляет абзацы, которые прошли бы как недостоверные.

    Это страховка: шаблоны уже строятся только из проверенных фактов,
    но проверка делает гарантию независимой от будущих правок.
    """
    allowed_spans = (ctx.vacancy.company, ctx.vacancy.title)
    if not allowed_spans[0]:
        allowed_spans = (ctx.vacancy.title,)
    result: List[str] = []
    for paragraph in paragraphs:
        if not verify_cover_letter(paragraph, ctx.resume, ctx.vacancy, ctx.match, allowed_spans):
            result.append(paragraph)
    return result or paragraphs


def _collect_warnings(ctx: LetterContext, cover_letter: str) -> List[str]:
    """Информационные сообщения для интерфейса (не блокируют генерацию)."""
    warnings: List[str] = []
    if not ctx.resume.skills:
        warnings.append(
            "В резюме не найдено технологий и инструментов - письмо получилось более общим."
        )
    elif not ctx.match.matched and not ctx.match.optional_matched:
        warnings.append(
            "Общих технологий с вакансией не найдено, поэтому письмо опирается на ваш стек в целом."
        )
    if not ctx.vacancy.company:
        warnings.append("Название компании в вакансии не найдено - письмо написано без него.")
    if ctx.style.brief and len(cover_letter) < BRIEF_MIN_CHARS:
        warnings.append(
            "Данных в резюме немного, поэтому письмо получилось короче "
            f"{BRIEF_MIN_CHARS} символов."
        )
    return warnings


def generate_cover_letter_dict(
    resume_text: str,
    vacancy_text: str,
    profession: str = "backend",
    style: str = "professional",
) -> dict:
    """Обёртка для JSON-API: возвращает словарь с ответом."""
    return generate_cover_letter(resume_text, vacancy_text, profession, style).to_dict()
