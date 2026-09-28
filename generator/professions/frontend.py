"""Шаблоны писем для Web / Frontend Developer.

Акцент: интерфейсы, JavaScript/TypeScript, HTML/CSS, фреймворки,
адаптивность, работа с API. Все технологии берутся только из резюме.
"""

from __future__ import annotations

from typing import List

from ..skills import (
    CATEGORY_API,
    CATEGORY_FRAMEWORK,
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
    id="frontend",
    label="Web / Frontend Developer",
    short_label="Frontend",
    description="Клиентская часть веб-приложений: интерфейсы, фреймворки, адаптивность.",
    default_title="Frontend Developer",
    focus_genitive="frontend-разработки",
    focus_dative="frontend-разработкой",
    focus_prepositional="frontend-разработке",
    detection_keywords=(
        "frontend",
        "front-end",
        "фронтенд",
        "фронтэнд",
        "верстка",
        "вёрстка",
        "web",
        "ui",
        "ux",
        "javascript",
        "react",
        "vue",
        "angular",
    ),
    # Фреймворк здесь важнее языка: вакансия «React Developer» закрывается
    # именно им, а HTML и CSS без него всё равно остаются в резюме. Если
    # фреймворка в вакансии нет, первым встанет JavaScript.
    focus_categories=(
        CATEGORY_FRAMEWORK,
        CATEGORY_LANGUAGE,
        CATEGORY_PRACTICE,
        CATEGORY_API,
        CATEGORY_TOOL,
        CATEGORY_QA_TOOL,
        CATEGORY_TESTING,
        CATEGORY_OTHER,
    ),
    is_testing=False,
    icon="layout",
)

_INTEREST = (
    "Откликаюсь на вакансию {title}{at_company}.",
    "Вакансия {title}{at_company} привлекла моё внимание.",
    "Интересна позиция {title}{at_company} - хочу развиваться в {focus_prep}.",
)

#: Формулировки, которые можно использовать только при реальном стеке.
_INTEREST_OVERLAP = (
    "Ваша вакансия {title}{at_company} привлекла внимание: мне близки задачи {focus_gen}.",
)

_INTEREST_CONFIDENT = (
    "Откликаюсь на вакансию {title}{at_company} и хочу обсудить задачи по интерфейсам.",
    "Вакансия {title}{at_company} мне интересна - давайте обсудим детали и формат работы.",
)

_INTEREST_CONFIDENT_OVERLAP = (
    "Откликаюсь на вакансию {title}{at_company}. То, что описано в задачах, совпадает с тем, над чем я работаю.",
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
    "По стеку вакансия мне подходит: {stack}.",
    "Ключевое пересечение по технологиям - {stack}. С ними работаю постоянно.",
    "Совпадающие технологии: {stack} - именно на них сделана большая часть моих интерфейсов.",
    "Технологии, которые у нас совпадают: {stack}.",
    "Большая часть моих задач - интерфейсы и логика на клиенте: {stack}.",
)

_TASKS = (
    "В вакансии есть задачи, знакомые по опыту: {tasks}.",
    "Близки по опыту задачи из вакансии: {tasks}.",
    "Совпадение по стеку видно и в самих задачах: {tasks}.",
    "Часть описанных задач совпадает с тем, что было в моей работе: {tasks}.",
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
    """Собирает абзацы письма для frontend-разработчика."""
    confident = ctx.style.enthusiasm
    interest_pool = _INTEREST_CONFIDENT if confident else _INTEREST
    overlap_pool = _INTEREST_CONFIDENT_OVERLAP if confident else _INTEREST_OVERLAP
    paragraphs = [
        greeting(ctx),
        interest_line(ctx, interest_pool, "frontend-interest", overlap_variants=overlap_pool),
        experience_line(ctx, _EXPERIENCE, "frontend-experience"),
        skill_line(ctx, _STACK, "frontend-stack"),
        tasks_line(ctx, _TASKS, "frontend-tasks"),
        soft_skills_line(ctx, _SOFT, "frontend-soft"),
        education_line(ctx, _EDUCATION, "frontend-education"),
    ]
    paragraphs.append(closing(ctx))
    return [paragraph for paragraph in paragraphs if paragraph]
