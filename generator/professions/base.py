"""Общая механика профессий: контекст письма и сборка абзацев.

Каждая профессия (см. соседние модули) описывает только свои фразы и
акценты. Всё остальное - рендеринг шаблонов, фильтрация недостоверных
фраз и склейка абзацев - сделано здесь.

Как добавить новую профессию:
    1. Создать файл в папке `professions/`, например `devops.py`.
    2. Описать объект `PROFESSION` (см. любой существующий модуль).
    3. Всё. Реестр подхватит файл автоматически.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ..phrases import PhrasePicker
from ..skills import find_skill_matches, is_derived_only
from ..styles import StyleSpec
from ..text_utils import clean_fragment, join_natural, to_lower
from ..types import MatchResult, ResumeFacts, VacancyFacts


@dataclass(frozen=True)
class Profession:
    """Описание IT-направления, для которого умеет писать генератор."""

    id: str
    label: str
    short_label: str
    description: str
    default_title: str
    #: Родительный падеж: «задачи backend-разработки».
    focus_genitive: str
    #: Дательный падеж: «с backend-разработкой».
    focus_dative: str
    #: Предложный падеж: «опыт в backend-разработке».
    focus_prepositional: str
    detection_keywords: Tuple[str, ...] = ()
    focus_categories: Tuple[str, ...] = ()
    is_testing: bool = False
    icon: str = "code"
    blocks: Tuple[Tuple[str, str], ...] = ()

    def as_dict(self) -> dict:
        """Данные для интерфейса (JSON)."""
        return {
            "id": self.id,
            "label": self.label,
            "short_label": self.short_label,
            "description": self.description,
            "default_title": self.default_title,
            "icon": self.icon,
        }


@dataclass
class LetterContext:
    """Всё, что блоки письма могут использовать.

    Содержит только проверенные факты, поэтому шаблоны остаются честными:
    подставить в письмо можно лишь то, что реально найдено в резюме.
    """

    resume: ResumeFacts
    vacancy: VacancyFacts
    match: MatchResult
    style: StyleSpec
    picker: PhrasePicker
    profession: Profession
    extra_stack: List[str] = field(default_factory=list)
    #: Сколько навыков можно упомянуть. Обычно берётся из стиля, но при
    #: нехватке длины в «Кратком» письме его можно временно поднять -
    #: это добавляет подтверждённые факты, а не выдумку.
    skill_cap: Optional[int] = None

    # --- справочные значения -------------------------------------------------

    @property
    def skills_limit(self) -> int:
        """Действующий лимит навыков: переопределение стиля или сам стиль."""
        if self.skill_cap is not None:
            return self.skill_cap
        return self.style.max_skills

    @property
    def job_title(self) -> str:
        """Название вакансии для письма (из вакансии или профессии)."""
        return self.vacancy.title or self.profession.default_title

    @property
    def company(self) -> str:
        """Название компании, если удалось извлечь."""
        return self.vacancy.company

    @property
    def at_company(self) -> str:
        """Хвост вида «в компании «X»» (пустая строка, если компании нет)."""
        return f" в компании «{self.company}»" if self.company else ""

    @property
    def name(self) -> str:
        return self.resume.name

    @property
    def has_stack(self) -> bool:
        """Есть ли в резюме хотя бы один технологический навык."""
        return bool(self.stack_skills())

    # --- подбор навыков ------------------------------------------------------

    def stack_skills(self) -> List[str]:
        """Навыки для упоминания в письме.

        Приоритет: совпадения с вакансией, отсортированные по акценту
        профессии; затем остальные навыки резюме (тоже подтвержденные).
        Ничего из `match.missing` сюда не попадает. Порядок стабилен,
        поэтому письмо воспроизводимо.
        """
        from ..config import MAX_SKILLS_MENTIONED

        limit = min(self.skills_limit, MAX_SKILLS_MENTIONED)
        allowed = set(self.match.matched) | set(self.match.optional_matched)
        ordered_source = list(self.match.matched) + list(self.match.optional_matched)

        def focus_rank(skill: str) -> int:
            category = _category_of(skill)
            try:
                return self.profession.focus_categories.index(category)
            except ValueError:
                return len(self.profession.focus_categories) + 1

        matched = sorted(
            [skill for skill in ordered_source if skill in allowed], key=focus_rank
        )
        resume_extra = [skill for skill in self.resume.skills if skill not in allowed]
        ordered = matched + resume_extra + list(self.extra_stack)
        seen = set()
        result = []
        for skill in ordered:
            if skill in seen:
                continue
            seen.add(skill)
            result.append(skill)
            if len(result) >= limit:
                break
        return result

    def stack_text(self, limit: Optional[int] = None) -> str:
        """Список навыков через запятую."""
        skills = self.stack_skills()
        if limit:
            skills = skills[:limit]
        return join_natural(skills)

    def focus_skills_text(self) -> str:
        """Навыки, релевантные именно этой профессии."""
        return join_natural([skill for skill in self.stack_skills() if _category_of(skill) in self.profession.focus_categories])

    def mentionable_skills(self) -> set:
        """Множество навыков, о которых письму разрешено говорить."""
        return set(self.resume.skills) | set(self.match.matched) | set(self.match.optional_matched)

    # --- безопасные цитаты из вакансии ---------------------------------------

    def safe_responsibilities(self, limit: int = 2) -> List[str]:
        """Обязанности из вакансии, безопасные для цитирования.

        Цитата отбрасывается, если в ней есть хотя бы один навык,
        которого нет в резюме: иначе письмо выглядело бы как утверждение
        о несуществующем опыте («знакомы задачи: настройка CI/CD»).
        """
        allowed = self.mentionable_skills()
        result: List[str] = []
        for responsibility in self.vacancy.responsibilities:
            fragment = clean_fragment(responsibility, limit=130)
            if not fragment:
                continue
            names = {
                match.name
                for match in find_skill_matches(fragment)
                if not is_derived_only(match.name)
            }
            if not names:
                # Цитата без навыков ничего не утверждает, но и пользы не несёт.
                continue
            if not names.issubset(allowed):
                continue
            result.append(fragment)
            if len(result) >= limit:
                break
        return result

    def task_skill_pairs(self) -> List[Tuple[str, str]]:
        """Пары (навык, обязанность) для блока про задачи."""
        allowed = self.mentionable_skills()
        pairs: List[Tuple[str, str]] = []
        for responsibility in self.safe_responsibilities(limit=4):
            for match in find_skill_matches(responsibility):
                if match.name in allowed:
                    pairs.append((match.name, responsibility))
                    break
        return pairs

    def focus_tasks_text(self) -> str:
        """Обязанности, релевантные стеку кандидата."""
        pairs = [responsibility for _, responsibility in self.task_skill_pairs()]
        return join_natural(pairs[:2])


def _category_of(skill: str) -> str:
    """Категория навыка (пустая строка для неизвестных навыков)."""
    from ..skills import SKILLS_BY_NAME

    skill_def = SKILLS_BY_NAME.get(skill)
    return skill_def.category if skill_def else ""


# --- Рендеринг шаблонов -------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def placeholders(template: str) -> List[str]:
    """Список подстановок, которые использует шаблон."""
    return _PLACEHOLDER_RE.findall(template)


def render(template: str, fields: Dict[str, str], optional: Sequence[str] = ()) -> Optional[str]:
    """Подставляет значения в шаблон.

    Возвращает None, если какое-то из обязательных значений пустое -
    именно так шаблон «требует» наличия факта (например, опыта работы
    в компании). Значения из `optional` подставляются как есть, даже
    если они пустые.
    """
    names = placeholders(template)
    for name in names:
        if name in optional:
            continue
        if not (fields.get(name) or "").strip():
            return None
    # Значения не обрезаем пробелами: для опциональных подстановок
    # пробел может быть частью фразы (например, « в компании «X»»).
    return template.format(**{name: (fields.get(name) or "") for name in names}).strip()


def render_first(
    pool: Sequence[str],
    slot: str,
    fields: Dict[str, str],
    picker: PhrasePicker,
    optional: Sequence[str] = (),
) -> Optional[str]:
    """Рендерит первый подходящий шаблон из пула.

    Варианты перебираются начиная с детерминированно выбранного, поэтому
    письмо не начинает каждый раз звучать одинаково, но остаётся
    воспроизводимым.
    """
    if not pool:
        return None
    start = picker._digest(slot, len(pool)) % len(pool)
    for offset in range(len(pool)):
        rendered = render(pool[(start + offset) % len(pool)], fields, optional)
        if rendered:
            return rendered
    return None


def interest_line(
    ctx: LetterContext,
    variants: Sequence[str],
    slot: str = "interest",
    overlap_variants: Sequence[str] = (),
) -> Optional[str]:
    """Абзац про интерес к вакансии.

    Название компании добавляется только тогда, когда оно реально
    найдено в тексте вакансии.

    `overlap_variants` - формулировки, которые утверждают, что задачи
    вакансии совпадают с опытом кандидата. Они подставляются, только
    если в резюме действительно есть стек: иначе письмо не должно
    ничего додумывать за кандидата.
    """
    fields = {"title": ctx.job_title, "at_company": ctx.at_company}
    pool: Tuple[str, ...] = tuple(variants)
    if ctx.has_stack:
        pool += tuple(overlap_variants)
    return render_first(pool, slot, fields, ctx.picker, optional=("at_company",))


# --- Готовые блоки -------------------------------------------------------------


def greeting(ctx: LetterContext) -> str:
    """Приветствие. Имя кандидата добавляется, только если оно найдено."""
    base = ctx.picker.pick(("Здравствуйте!", "Добрый день!", "Здравствуйте!"), "greeting")
    if ctx.name:
        return f"{base} Меня зовут {ctx.name}."
    return base


def closing(ctx: LetterContext) -> str:
    """Завершающая часть письма вместе с подписью.

    Формулировки намеренно нейтральные: письмо не предполагает пол
    автора резюме.
    """
    if ctx.style.enthusiasm:
        variants = (
            "Интересна возможность поработать над задачами, описанными в вакансии. Давайте обсудим детали.",
            "Рассчитываю, что мой опыт будет полезен команде. Обсудим, где это получится лучше.",
            "Отвечаю на отклик в течение рабочего дня. Свяжитесь, если нужна дополнительная информация.",
            "Интересна возможность поработать над задачами из вакансии. Давайте обсудим детали "
            "и формат работы, а также то, как мой опыт может быть полезен команде.",
        )
    else:
        variants = (
            "Спасибо за внимание к моему отклику. Свяжусь с вами, чтобы обсудить детали.",
            "Спасибо, что уделили время. Свяжитесь со мной, если понадобится дополнительная информация.",
            "Давайте обсудим детали вакансии: обычно отвечаю в течение рабочего дня.",
            "Обсудим задачи подробнее. Отвечаю на отклик в течение рабочего дня "
            "и передам дополнительные детали по запросу.",
        )
    first = ctx.picker.pick(variants, "closing")
    signature = "С уважением,\n" + ctx.name if ctx.name else "С уважением"
    if not first.endswith("."):
        first += "."
    return f"{first}\n\n{signature}"


def skill_line(ctx: LetterContext, variants: Sequence[str], slot: str) -> Optional[str]:
    """Абзац про совпадающие технологии."""
    stack = ctx.stack_text()
    if not stack:
        return None
    fields = {
        "stack": stack,
        "focus_gen": ctx.profession.focus_genitive,
        "focus_prep": ctx.profession.focus_prepositional,
        "title": ctx.job_title,
    }
    return render_first(variants, slot, fields, ctx.picker)


def experience_line(ctx: LetterContext, variants: Sequence[str], slot: str) -> Optional[str]:
    """Абзац про опыт кандидата (только подтверждённые факты)."""
    fields = {
        "years": ctx.resume.years_text,
        "company": ctx.resume.last_company,
        "position": ctx.resume.last_position,
        "stack": ctx.stack_text(limit=3),
        "focus_gen": ctx.profession.focus_genitive,
        "focus_dat": ctx.profession.focus_dative,
        "focus_prep": ctx.profession.focus_prepositional,
    }
    if ctx.resume.years_of_experience is None:
        fields["years"] = ""
    return render_first(variants, slot, fields, ctx.picker)


def tasks_line(ctx: LetterContext, variants: Sequence[str], slot: str) -> Optional[str]:
    """Абзац про задачи из вакансии, пересекающиеся с опытом кандидата."""
    if not ctx.style.include_tasks_block:
        return None
    tasks = ctx.safe_responsibilities(limit=ctx.style.max_tasks)
    if not tasks:
        return None
    quoted = join_natural([f"«{task}»" for task in tasks], conjunction="и")
    skills = join_natural(
        [skill for skill, _ in ctx.task_skill_pairs()][:3]
    )
    fields = {
        "tasks": quoted,
        "skills": skills,
        "focus_gen": ctx.profession.focus_genitive,
    }
    return render_first(variants, slot, fields, ctx.picker)


def soft_skills_line(ctx: LetterContext, variants: Sequence[str], slot: str) -> Optional[str]:
    """Абзац про soft skills (только найденные в резюме)."""
    if not ctx.style.include_soft_skills_block:
        return None
    skills = ctx.resume.soft_skills[:3]
    if not skills:
        return None
    fields = {
        "soft": join_natural(skills),
        "focus_gen": ctx.profession.focus_genitive,
    }
    return render_first(variants, slot, fields, ctx.picker)


def education_line(ctx: LetterContext, variants: Sequence[str], slot: str) -> Optional[str]:
    """Абзац про образование (только если оно указано в резюме)."""
    if not ctx.style.include_education_block:
        return None
    item = ctx.resume.education[0] if ctx.resume.education else ""
    if not item:
        return None
    fields = {"education": clean_fragment(item, limit=90)}
    return render_first(variants, slot, fields, ctx.picker)


def generic_stack_line(ctx: LetterContext) -> Optional[str]:
    """Запасной абзац, когда в резюме нет ни одного стека.

    Никаких утверждений о навыках - только мотивация и намерение
    разобраться в требованиях. Кавычки-ёлочки здесь не используются:
    проверка достоверности считает их цитатой из исходного текста.
    """
    focus_gen = ctx.profession.focus_genitive
    focus_dat = ctx.profession.focus_dative
    if ctx.picker.pick((True, False), "generic-style"):
        return (
            f"Мне интересны задачи, связанные с {focus_dat}, и я хочу глубоко разобраться "
            "в предметной области нового проекта."
        )
    return (
        f"Ключевой мотив - задачи в области {focus_gen}. Уточню детали по вашим требованиям "
        "на этапе технического общения."
    )


def matched_overlap(ctx: LetterContext) -> str:
    """Навыки, которые есть и в резюме, и в вакансии (для отчёта в UI)."""
    return join_natural(ctx.match.matched)
