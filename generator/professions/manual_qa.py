"""Шаблоны писем для Manual QA.

Акцент: функциональное тестирование, регрессия, смоук, тест-кейсы,
баг-репорты, работа с API и SQL, Jira, взаимодействие с разработчиками.
Используются только те навыки, которые реально найдены в резюме.
"""

from __future__ import annotations

from typing import List

from ..skills import (
    CATEGORY_DATABASE,
    CATEGORY_LANGUAGE,
    CATEGORY_OTHER,
    CATEGORY_PRACTICE,
    CATEGORY_QA_TOOL,
    CATEGORY_TESTING,
    CATEGORY_TOOL,
)
from .base import (
    LetterContext,
    Profession,
    closing,
    education_line,
    experience_line,
    greeting,
    interest_line,
    skill_line,
    soft_skills_line,
    tasks_line,
)

PROFESSION = Profession(
    id="manual_qa",
    label="Manual QA",
    short_label="Manual QA",
    description="Ручное тестирование: тест-кейсы, чек-листы, баг-репорты, регрессия.",
    default_title="QA Engineer",
    focus_genitive="ручного тестирования",
    focus_dative="ручным тестированием",
    focus_prepositional="ручном тестировании",
    detection_keywords=(
        "manual qa",
        "qa",
        "quality assurance",
        "тестировщик",
        "тестирование",
        "tester",
        "test engineer",
        "ручное тестирование",
        "test cases",
    ),
    focus_categories=(
        CATEGORY_TESTING,
        CATEGORY_QA_TOOL,
        CATEGORY_DATABASE,
        CATEGORY_LANGUAGE,
        CATEGORY_TOOL,
        CATEGORY_PRACTICE,
        CATEGORY_OTHER,
    ),
    is_testing=True,
    icon="checklist",
)

_INTEREST = (
    "Откликаюсь на вакансию {title}{at_company}.",
    "Вакансия {title}{at_company} привлекла моё внимание.",
    "Интересна вакансия {title}{at_company} - хочу развиваться в {focus_prep}.",
)

#: Формулировки, которые можно использовать только при реальном стеке.
_INTEREST_OVERLAP = (
    "Ваша вакансия {title}{at_company} привлекла внимание: мне близки задачи {focus_gen}.",
)

_INTEREST_CONFIDENT = (
    "Откликаюсь на вакансию {title}{at_company} и хочу обсудить задачи по качеству продукта.",
    "Вакансия {title}{at_company} мне интересна - давайте обсудим детали и формат работы.",
)

_INTEREST_CONFIDENT_OVERLAP = (
    "Откликаюсь на вакансию {title}{at_company}. Описанные проверки совпадают с тем, чем я занимаюсь.",
)

_EXPERIENCE = (
    "Мой опыт в {focus_prep} - {years}. Сейчас работаю в компании «{company}» на позиции {position}.",
    "В {focus_prep} работаю {years}; последнее место работы - «{company}», позиция {position}.",
    "Сейчас занимаю позицию {position} в компании «{company}», суммарный опыт в {focus_prep} - {years}.",
    "Работаю в компании «{company}» на позиции {position}, общий стаж в {focus_prep} - {years}.",
)

# Формулировки про стек живут только здесь: если они окажутся в _EXPERIENCE,
# письмо дважды перечислит один и тот же набор инструментов.
_STACK = (
    "По инструментам вакансия мне подходит: {stack}.",
    "Ключевое пересечение: {stack}. С этим набором работаю постоянно.",
    "Совпадающие навыки: {stack} - они закрывают основную часть описанных проверок.",
    "Из совпадающих навыков - {stack}.",
    "Основной набор инструментов в тестировании: {stack}.",
)

_TASKS = (
    "В вакансии есть задачи, знакомые по опыту: {tasks}.",
    "Близки по опыту задачи из вакансии: {tasks}.",
    "Отдельно отмечу проверки, которые мне знакомы: {tasks}.",
    "Совпадение видно и в самих задачах: {tasks}.",
)

_SOFT = (
    "Отдельно про soft skills: {soft}.",
    "В работе для меня важны качества: {soft}.",
    "Кроме технических навыков, в резюме указано: {soft}.",
)

_EDUCATION = (
    "Образование: {education}.",
    "По образованию - {education}.",
)


def build_paragraphs(ctx: LetterContext) -> List[str]:
    """Собирает абзацы письма для ручного QA."""
    confident = ctx.style.enthusiasm
    interest_pool = _INTEREST_CONFIDENT if confident else _INTEREST
    overlap_pool = _INTEREST_CONFIDENT_OVERLAP if confident else _INTEREST_OVERLAP
    paragraphs = [
        greeting(ctx),
        interest_line(ctx, interest_pool, "manual-interest", overlap_variants=overlap_pool),
        experience_line(ctx, _EXPERIENCE, "manual-experience"),
        skill_line(ctx, _STACK, "manual-stack"),
        tasks_line(ctx, _TASKS, "manual-tasks"),
        soft_skills_line(ctx, _SOFT, "manual-soft"),
        education_line(ctx, _EDUCATION, "manual-education"),
    ]
    paragraphs.append(closing(ctx))
    return [paragraph for paragraph in paragraphs if paragraph]
