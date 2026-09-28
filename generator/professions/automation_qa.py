"""Шаблоны писем для Automation QA.

Акцент: автоматизация тестов, Selenium / Playwright / Cypress, Pytest,
JUnit, API automation, CI/CD, Allure. Упоминаются только те инструменты,
которые найдены в резюме.
"""

from __future__ import annotations

from typing import List

from ..skills import (
    CATEGORY_CI,
    CATEGORY_DATABASE,
    CATEGORY_FRAMEWORK,
    CATEGORY_INFRA,
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
    id="automation_qa",
    label="Automation QA",
    short_label="Automation QA",
    description="Автоматизация тестирования: фреймворки, API-тесты, запуск в CI/CD.",
    default_title="Automation QA Engineer",
    focus_genitive="автоматизации тестирования",
    focus_dative="автоматизацией тестирования",
    focus_prepositional="автоматизации тестирования",
    detection_keywords=(
        "automation qa",
        "qa automation",
        "автоматизатор",
        "автотесты",
        "автоматизация тестирования",
        "sdet",
        "test automation",
        "автоматизированное тестирование",
        "selenium",
    ),
    focus_categories=(
        CATEGORY_QA_TOOL,
        CATEGORY_TESTING,
        CATEGORY_LANGUAGE,
        CATEGORY_FRAMEWORK,
        CATEGORY_CI,
        CATEGORY_INFRA,
        CATEGORY_DATABASE,
        CATEGORY_PRACTICE,
        CATEGORY_TOOL,
        CATEGORY_OTHER,
    ),
    is_testing=True,
    icon="robot",
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
    "Откликаюсь на вакансию {title}{at_company} и хочу обсудить задачи по автоматизации.",
    "Вакансия {title}{at_company} мне интересна - давайте обсудим детали и формат работы.",
)

_INTEREST_CONFIDENT_OVERLAP = (
    "Откликаюсь на вакансию {title}{at_company}. Описанные задачи по тестам совпадают с моей работой.",
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
    "Ключевое пересечение: {stack}. С этим набором работаю на постоянной основе.",
    "Совпадающие навыки: {stack} - они закрывают задачи из описания.",
    "Из совпадающих инструментов - {stack}.",
    "Основной инструментарий для автотестов: {stack}.",
)

_TASKS = (
    "В вакансии есть задачи, знакомые по опыту: {tasks}.",
    "Близки по опыту задачи из вакансии: {tasks}.",
    "Отдельно отмечу задачи, где совпадает мой стек: {tasks}.",
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
    """Собирает абзацы письма для Automation QA."""
    confident = ctx.style.enthusiasm
    interest_pool = _INTEREST_CONFIDENT if confident else _INTEREST
    overlap_pool = _INTEREST_CONFIDENT_OVERLAP if confident else _INTEREST_OVERLAP
    paragraphs = [
        greeting(ctx),
        interest_line(ctx, interest_pool, "automation-interest", overlap_variants=overlap_pool),
        experience_line(ctx, _EXPERIENCE, "automation-experience"),
        skill_line(ctx, _STACK, "automation-stack"),
        tasks_line(ctx, _TASKS, "automation-tasks"),
        soft_skills_line(ctx, _SOFT, "automation-soft"),
        education_line(ctx, _EDUCATION, "automation-education"),
    ]
    paragraphs.append(closing(ctx))
    return [paragraph for paragraph in paragraphs if paragraph]
