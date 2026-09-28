"""Шаблоны писем для Backend Developer.

Смысловые блоки: приветствие -> интерес к вакансии -> релевантный опыт ->
совпадающие технологии -> задачи из вакансии -> soft skills/образование ->
завершение.

Каждый блок - это пул готовых формулировок. Подстановки выполняются
только по фактам, найденным в резюме, поэтому письмо не может
приписать кандидату лишнего.
"""

from __future__ import annotations

from typing import List

from ..skills import (
    CATEGORY_API,
    CATEGORY_CI,
    CATEGORY_CLOUD,
    CATEGORY_DATABASE,
    CATEGORY_FRAMEWORK,
    CATEGORY_INFRA,
    CATEGORY_LANGUAGE,
    CATEGORY_OTHER,
    CATEGORY_PRACTICE,
    CATEGORY_QA_TOOL,
    CATEGORY_TESTING,
    CATEGORY_TOOL,
    CATEGORY_VCS,
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
    id="backend",
    label="Backend Developer",
    short_label="Backend",
    description="Серверная разработка: API, базы данных, интеграции, инфраструктура.",
    default_title="Backend Developer",
    focus_genitive="backend-разработки",
    focus_dative="backend-разработкой",
    focus_prepositional="backend-разработке",
    detection_keywords=(
        "backend",
        "back-end",
        "бэкенд",
        "бэкенд",
        "сервер",
        "server-side",
        "api",
        "разработчик",
        "developer",
        "инженер",
        "engineer",
    ),
    focus_categories=(
        CATEGORY_LANGUAGE,
        CATEGORY_FRAMEWORK,
        CATEGORY_API,
        CATEGORY_DATABASE,
        CATEGORY_INFRA,
        CATEGORY_CLOUD,
        CATEGORY_CI,
        CATEGORY_VCS,
        CATEGORY_TOOL,
        CATEGORY_PRACTICE,
        CATEGORY_QA_TOOL,
        CATEGORY_TESTING,
        CATEGORY_OTHER,
    ),
    is_testing=False,
    icon="server",
)

_INTEREST = (
    "Откликаюсь на вакансию {title}{at_company}.",
    "Вакансия {title}{at_company} привлекла моё внимание.",
    "Интересна вакансия {title}{at_company} - хочу перенести свой опыт в {focus_prep} в ваш продукт.",
    "Рассматриваю вакансию {title}{at_company} - хочу обсудить задачи и условия работы.",
)

#: Формулировки, которые можно использовать только при реальном стеке.
_INTEREST_OVERLAP = (
    "Ваша вакансия {title}{at_company} привлекла внимание: мне близки задачи {focus_gen}.",
    "Рассматриваю вакансию {title}{at_company}: задачи из описания совпадают с тем, чем занимаюсь.",
)

_INTEREST_CONFIDENT = (
    "Вакансия {title}{at_company} мне интересна - давайте обсудим детали и формат работы.",
    "Откликаюсь на вакансию {title}{at_company}. Мне интересны задачи {focus_gen} - хочется обсудить, где мой опыт будет полезен.",
)

_INTEREST_CONFIDENT_OVERLAP = (
    "Откликаюсь на вакансию {title}{at_company} и хочу обсудить, как мой опыт закрывает часть этих задач.",
    "Откликаюсь на вакансию {title}{at_company}. Задачи {focus_gen} - это основная часть моей работы.",
)

_EXPERIENCE = (
    "Мой опыт в {focus_prep} - {years}. Сейчас работаю в компании «{company}» на позиции {position}.",
    "В {focus_prep} работаю {years}; последнее место работы - «{company}», позиция {position}.",
    "Сейчас занимаю позицию {position} в компании «{company}», суммарный опыт в {focus_prep} - {years}.",
    "Работаю в компании «{company}» на позиции {position}, общий стаж в {focus_prep} - {years}.",
)

# Формулировки про стек живут только здесь: если они окажутся в _EXPERIENCE,
# письмо дважды перечислит один и тот же набор технологий.
_STACK = (
    "Ваша вакансия во многом совпадает с моим стеком: {stack}.",
    "Ключевое пересечение по технологиям - {stack}. С этим стеком работаю на постоянной основе.",
    "Совпадающие технологии: {stack} - на них я могу сразу включиться в работу.",
    "По технологиям пересечение явное: {stack}.",
    "Основное совпадение по стеку - {stack}; с этими инструментами работаю в последних проектах.",
    "В повседневной работе опираюсь на {stack}: задачи связаны с {focus_dat}.",
)

_TASKS = (
    "В вакансии есть задачи, знакомые по опыту: {tasks}.",
    "Близки по опыту задачи из вакансии: {tasks}.",
    "Отдельно отмечу задачи, где совпадает мой стек: {tasks}.",
    "Совпадение по стеку видно и в самих задачах: {tasks}.",
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
    """Собирает абзацы письма для backend-разработчика."""
    confident = ctx.style.enthusiasm
    interest_pool = _INTEREST_CONFIDENT if confident else _INTEREST
    overlap_pool = _INTEREST_CONFIDENT_OVERLAP if confident else _INTEREST_OVERLAP
    paragraphs = [
        greeting(ctx),
        interest_line(ctx, interest_pool, "backend-interest", overlap_variants=overlap_pool),
        experience_line(ctx, _EXPERIENCE, "backend-experience"),
        skill_line(ctx, _STACK, "backend-stack"),
        tasks_line(ctx, _TASKS, "backend-tasks"),
        soft_skills_line(ctx, _SOFT, "backend-soft"),
        education_line(ctx, _EDUCATION, "backend-education"),
    ]
    paragraphs.append(closing(ctx))
    return [paragraph for paragraph in paragraphs if paragraph]
