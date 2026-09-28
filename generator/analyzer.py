"""Локальный rule-based анализатор текста резюме и вакансии.

Никаких моделей машинного обучения и внешних API: только словари,
регулярные выражения и правила. Цель — не «идеальный NLP», а быстрый
и предсказуемый разбор типового текста вакансии и резюме.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from .config import COMPANY_NAME_STOP_WORDS
from .skills import (
    CATEGORY_QA_TOOL,
    CATEGORY_TESTING,
    SKILLS_BY_NAME,
    SKILL_NAMES_LOWER,
    SOFT_SKILLS,
    display_skills,
    find_skill_matches,
    find_skills,
    is_derived_only,
)
from .text_utils import (
    clean_fragment,
    dedupe,
    iter_lines,
    normalize_inline as _inline,
    to_lower,
)
from .types import ResumeFacts, VacancyFacts

#: Категория каждого известного навыка - используется при скоринге профессий.
_CATEGORY_OF = {name: skill.category for name, skill in SKILLS_BY_NAME.items()}

# --- Заголовки разделов --------------------------------------------------------

_SECTION_HEADINGS = (
    "опыт",
    "experience",
    "работа",
    "employment",
    "образование",
    "education",
    "о себе",
    "about",
    "профиль",
    "summary",
    "skills",
    "навыки",
    "умения",
    "технологии",
    "технический стек",
    "стек",
    "контакты",
    "projects",
    "проекты",
    "дополнительная информация",
    "прочее",
    "языки",
    "хобби",
    "about me",
)

_OPTIONAL_MARKERS = (
    "желательно",
    "желательный",
    "будет плюсом",
    "будет преимуществом",
    "преимуществом",
    "плюсом",
    "nice to have",
    "nice-to-have",
    "plus",
    "optional",
    "дополнительным бонусом",
    "дополнительный плюс",
    "хотелось бы",
    "будет бонусом",
)

_REQUIRED_MARKERS = (
    "обязательные требования",
    "обязательные навыки",
    "требования",
    "необходимо",
    "обязанности",
    "мы ожидаем",
    "что предстоит",
    "задачи",
    "responsibilities",
    "requirements",
    "must have",
    "what you will do",
    "what you'll do",
    "about the job",
)

_RESPONSIBILITY_MARKERS = (
    "обязанности",
    "задачи",
    "что предстоит",
    "чем предстоит",
    "что нужно будет",
    "работа состоит",
    "в задачи входит",
    "your responsibilities",
    "what you'll do",
    "what you will do",
    "responsibilities",
    "what we expect you to do",
    "duties",
)

_TITLE_MARKERS = (
    "должность",
    "позиция",
    "вакансия",
    "название вакансии",
    "specialization",
    "position",
    "title",
    "role",
    "job",
)

_EXPERIENCE_MARKERS = (
    "опыт работы",
    "years of experience",
    "total experience",
    "общий стаж",
    "стаж",
    "years of",
    "лет опыта",
)

# --- Регулярные выражения ------------------------------------------------------

_YEARS_PATTERNS = (
    re.compile(r"(?P<value>\d{1,2})\s*\+?\s*(?:лет|года|год|years?|yrs?|year)\b", re.IGNORECASE),
    re.compile(r"(?:от|over|min(?:imum)?|более|more than|от)\s*(?:минимум\s*)?(?P<value>\d{1,2})\s*(?:\+)?\s*(?:лет|года|год|years?|yrs?|year)\b", re.IGNORECASE),
    re.compile(r"(?:experience|опыт|стаж)\D{0,12}?(?P<value>\d{1,2})\s*\+?\s*(?:лет|года|год|years?|yrs?)\b", re.IGNORECASE),
    re.compile(r"(?P<value>\d{1,2})\s*\+\s*(?:years?|yrs?)\b", re.IGNORECASE),
)

_NAME_LABELS = (
    "имя",
    "name",
    "фио",
    "фио кандидата",
    "candidate",
    "отклик от",
    "откликнулся",
)

_NAME_RE = re.compile(
    r"(?:имя|фио|name)\s*[:\-–]\s*(?P<value>[А-ЯЁA-Z][\w\-\s]{2,40})",
    re.IGNORECASE,
)

_TITLE_LABELS_RE = re.compile(
    r"(?:должность|позиция|target title|target position|ищу позицию|желаемая должность|"
    r"current title|текущая должность|position|title)\s*[:\-–]\s*(?P<value>[^\n]{2,60})",
    re.IGNORECASE,
)

_DATE_RANGE_RE = re.compile(
    r"(?P<from>(?:19|20)\d{2})\s*(?:[-–—/]|по|с)\s*"
    r"(?P<to>(?:19|20)\d{2}|наст\.\s*время|настоящее\s+время|текущее\s+время|сейчас|now|present|н\.?\s*в\.?)",
    re.IGNORECASE,
)

#: Признаки того, что строка - название компании.
_COMPANY_SUFFIXES = (
    "llc",
    "ltd",
    "inc",
    "gmbh",
    "s.a.",
    "sa",
    "corp",
    "corporation",
    "group",
    "holding",
    "technologies",
    "technology",
    "lab",
    "labs",
    "software",
    "systems",
    "solutions",
    "digital",
    "bank",
    "shop",
    "market",
    "s.r.o.",
    "ooo",
    "oao",
    "zao",
)

_TITLE_STOP_WORDS = {
    "резюме",
    "cv",
    "resume",
    "портфолио",
    "портфолио.",
    "профиль",
    "связаться",
    "контакты",
    "телефон",
    "email",
    "e-mail",
    "опыт",
    "образование",
    "навыки",
    "проекты",
    "summary",
}

_ACTION_VERBS = (
    "разработ",
    "разрабатыва",
    "разработка",
    "проектир",
    "тестир",
    "проверя",
    "автоматиз",
    "поддерж",
    "сопровожд",
    "оптимиз",
    "внедр",
    "созда",
    "пиш",
    "работа",
    "участв",
    "веду",
    "веде",
    "реализ",
    "анализ",
    "монитор",
    "сопровожден",
    "документ",
    "communicat",
    "develop",
    "design",
    "test",
    "automate",
    "support",
    "work",
    "build",
    "maintain",
    "monitor",
)

_EDUCATION_MARKERS = (
    "высшее образование",
    "высшее профессиональное образование",
    "незаконченное высшее",
    "бакалавр",
    "бакалавриат",
    "магистр",
    "магистратура",
    "среднее профессиональное",
    "среднее техническое",
    "техническое образование",
    "образование",
    "выпускник",
    "окончил",
    "диплом",
    "bachelor",
    "master",
    "university",
    "university degree",
    "college",
    "институт",
    "университет",
    "факультет",
    "кафедра",
    "аспирантура",
)

_EDUCATION_INSTITUTION_RE = re.compile(
    r"(?P<value>(?:[А-ЯЁA-Z][\w\-\.]+\s+){1,3}"
    r"(?:университет|институт|техникум|колледж|академия|факультет|school|university|institute|college|polytechnic))",
)

_EDUCATION_DEGREE_RE = re.compile(
    r"(высшее(?: профессиональное)? образование|незаконченное высшее|бакалавр\w*|магистр\w*|"
    r"аспирант\w*|среднее(?: профессиональное| техническое)? образование|"
    r"bachelor\w*|master\w*|ph\.?d|doctorate)",
    re.IGNORECASE,
)

_COMPANY_PATTERNS = (    re.compile(r"(?:компания|фирма|работадатель|employer)\s*[:\-–]?\s*(?P<value>[^\n]{2,50})", re.IGNORECASE),
    re.compile(r"(?:в\s+компанию|в\s+команду|компания)\s+(?P<value>[«\"']?[\w\.\-«»\"']{2,40})", re.IGNORECASE),
    re.compile(r"(?:о\s+компании|о\s+работодателе|about\s+(?:the\s+)?company|company)\s*[:\-–]?\s*(?P<value>[^\n]{2,50})", re.IGNORECASE),
    # Предложный падеж: «Вакансия Backend Developer в компании Acme».
    re.compile(r"(?:в\s+компании|в\s+организации|у\s+работодателя|в\s+фирме|в\s+студии)\s+(?P<value>[«\"']?[\w\.\-«»\"']{2,40})", re.IGNORECASE),
    re.compile(r"(?:работа\s+в|в\s+работе\s+в)\s+(?P<value>[^\n,.]{2,40})", re.IGNORECASE),
    re.compile(r"[\«\"]?(?P<value>[A-ZА-ЯЁ][\w\.\-]{1,20}(?:\s+[A-ZА-ЯЁ][\w\.\-]{1,20}){0,2})[\»\"]?\s*[—–-]{1,2}\s*(?:вакансия| VACANCY| вакансия)", re.IGNORECASE),
    re.compile(r"(?:Employer|Company|Вакансия\s+в|Компания)\s*[:\-–]?\s*(?P<value>[A-ZА-ЯЁ][\w\.\-&\s]{1,30})"),
)


#: Организационно-правовые формы, которые не являются частью названия.
_LEGAL_FORMS = (
    "ооо",
    "оао",
    "зао",
    "пао",
    "ао",
    "гк",
    "ип",
    "нпо",
    "нпп",
    "учредительное",
    "общество",
    "s.r.o",
    "llc",
    "ltd",
    "inc",
    "gmbh",
)


def _strip_legal_forms(text: str) -> str:
    """Убирает организационно-правовую форму: «ООО Ромашка» -> «Ромашка»."""
    words = (text or "").split()
    while words and to_lower(words[0].strip(".,\"")) in _LEGAL_FORMS:
        words.pop(0)
    return " ".join(words).strip()


def _clean_company_candidate(value: str) -> str:
    """Приводит кандидата в компанию к безопасному виду."""
    candidate = clean_fragment(value, limit=42)
    candidate = candidate.split("(")[0].strip()
    candidate = candidate.strip(" \t-–—:;,.\"«»'")
    if not candidate:
        return ""

    # Убираем организационно-правовую форму: ООО «Ромашка» -> Ромашка.
    candidate = _strip_legal_forms(candidate)
    words = candidate.split()
    if not words or len(words) > 4:
        return ""
    candidate = " ".join(words)

    lowered = to_lower(candidate)
    if lowered in COMPANY_NAME_STOP_WORDS:
        return ""
    for word in candidate.split():
        if to_lower(word.strip(".,")) in COMPANY_NAME_STOP_WORDS:
            return ""
    # Отсекаем описательные обороты и «слова-паразиты».
    stop_tokens = (
        "вакансия",
        "требуется",
        "ищет",
        "ищем",
        "работа",
        "команда",
        "компания",
        "проект",
        "hr",
        "рекрутер",
        "talent",
        "opportunity",
    )
    for token in stop_tokens:
        if token in lowered:
            return ""
    return candidate


def _extract_company(text: str) -> str:
    """Пытается найти название компании в вакансии."""
    for pattern in _COMPANY_PATTERNS:
        for match in pattern.finditer(text):
            candidate = _clean_company_candidate(match.group("value"))
            if candidate:
                return candidate
    return ""


#: Служебные слова перед названием должности: «Требуется Backend Developer».
_TITLE_PREFIX_RE = re.compile(
    r"^(?:вакансия|требуется|требуем|ищем|ищу|нужен|нужна|нужны|требуемый|роль|должность|"
    r"позиция|открытая\s+позиция|job|vacancy|position|title|role)\s*[:\-–—]?\s*",
    re.IGNORECASE,
)


#: Хвост вида «в компании Acme» - это уже не должность.
_TITLE_COMPANY_TAIL_RE = re.compile(
    r"\s+(?:в|на|у)\s+(?:компании|организации|команде|фирме|работодателе|студии)\s+\S.*$",
    re.IGNORECASE,
)


def _clean_title(value: str) -> str:
    """Приводит кандидата в должность к короткому названию.

    «Требуется Backend Developer. Нужен опыт от 3 лет» ->
    «Backend Developer»: иначе в письме появилась бы целая строка вакансии.
    """
    candidate = _TITLE_PREFIX_RE.sub("", (value or "").strip())
    for separator in (". ", "; ", ", ", " — ", " – ", " - "):
        position = candidate.find(separator)
        if position > 0:
            candidate = candidate[:position]
    candidate = _TITLE_COMPANY_TAIL_RE.sub("", candidate)
    return clean_fragment(candidate, limit=58).strip(" .,;:-–—")


def _extract_title(text: str) -> str:
    """Пытается найти название должности в вакансии."""
    for line in iter_lines(text):
        for marker in _TITLE_MARKERS:
            if to_lower(line).startswith(to_lower(marker)):
                value = line.split(":", 1)[-1].strip() if ":" in line else line[len(marker):].strip()
                value = _clean_title(value)
                if value and len(value.split()) <= 6:
                    return value
    # Первая строка, похожая на должность.
    for line in iter_lines(text)[:4]:
        if _looks_like_title(line):
            return _clean_title(line)
    return ""


_TITLE_KEYWORDS = (
    "developer",
    "engineer",
    "tester",
    "qa",
    "программист",
    "разработчик",
    "инженер",
    "тестировщик",
    "аналитик",
    "fullstack",
    "full-stack",
    "backend",
    "front",
    "devops",
    "sdet",
    "автоматизатор",
)


def _looks_like_title(line: str) -> bool:
    """Проверяет, что строка похожа на название должности."""
    lowered = to_lower(line)
    if lowered in _TITLE_STOP_WORDS:
        return False
    if any(char.isdigit() for char in line):
        return False
    if len(line) > 70:
        return False
    if not any(keyword in lowered for keyword in _TITLE_KEYWORDS):
        return False
    return len(line.split()) <= 6


def _looks_like_name(line: str) -> bool:
    """Проверяет, что строка может быть именем, а не должностью.

    В резюме первой строкой часто идёт должность («Backend Developer»),
    а имя идёт следом, поэтому такую строку пропускаем.
    """
    candidate = _normalize_name(line)
    if not candidate:
        return False
    lowered = to_lower(candidate)
    if any(keyword in lowered for keyword in _TITLE_KEYWORDS):
        return False
    if any(char.isdigit() for char in candidate):
        return False
    return True


def _extract_name(text: str) -> str:
    """Извлекает имя кандидата (только из резюме)."""
    for line in iter_lines(text)[:12]:
        match = _NAME_RE.search(line)
        if match:
            value = _normalize_name(match.group("value"))
            if value:
                return value

    for line in iter_lines(text)[:6]:
        if _looks_like_name(line):
            return _normalize_name(line)
    return ""


def _normalize_name(value: str) -> str:
    """Проверяет и нормализует строку как имя человека."""
    candidate = clean_fragment(value, limit=40)
    candidate = candidate.strip(" .,;:")
    if not candidate or len(candidate) < 4:
        return ""
    words = candidate.split()
    if len(words) > 3 or not 1 <= len(words) <= 3:
        return ""
    if any(char.isdigit() for char in candidate):
        return ""
    lowered = to_lower(candidate)
    if any(stop in lowered for stop in ("резюме", "resume", "cv", "http", "@", "телефон", "email")):
        return ""
    for word in words:
        # Имя: 2-20 букв, первая заглавная.
        if not 1 <= len(word) <= 20:
            return ""
        if not word[0].isupper():
            return ""
        if not word.isalpha():
            return ""
    return " ".join(word.capitalize() for word in words)


def _extract_years(text: str) -> Optional[int]:
    """Находит явно указанный стаж работы в тексте."""
    normalized = _inline(text)
    best: Optional[int] = None
    for pattern in _YEARS_PATTERNS:
        for match in pattern.finditer(normalized):
            try:
                value = int(match.group("value"))
            except (TypeError, ValueError):
                continue
            if 0 <= value <= 45:
                # При нескольких совпадениях берём максимальное (полный стаж).
                best = value if best is None else max(best, value)
    return best


def _is_skill_list(value: str) -> bool:
    """Проверяет, что фрагмент - список технологий, а не название компании.

    «Python, Django, PostgreSQL» состоит только из известных навыков,
    поэтому компанией быть не может.
    """
    parts = [part.strip(" .,;") for part in value.split(",")]
    if len(parts) < 2 or not all(parts):
        return False
    return all(to_lower(part) in SKILL_NAMES_LOWER for part in parts)


#: Служебные слова, которые не считаются частью названия компании.
_COMPANY_NOISE_WORDS = frozenset(
    {
        "в", "во", "на", "у", "с", "со", "и", "а", "по", "для", "от", "до",
        "года", "год", "лет", "месяцев", "месяца", "занимал", "занимала",
        "работал", "работала", "работалa",
    }
)


#: Слова, по которым фрагмент точно не является названием компании:
#: заголовки разделов резюме и служебные подписи.
_COMPANY_REJECT_WORDS = frozenset(
    {
        "опыт", "работа", "работы", "образование", "навыки", "умения",
        "проекты", "проект", "контакты", "телефон", "email", "резюме",
        "цель", "цели", "обо", "мне", "себе", "дополнительно", "информация",
        "обязанности", "требования", "условия", "ответственность",
        "skills", "experience", "education", "projects", "contacts",
        "about", "goal", "goals", "summary", "profile",
    }
)


def _strip_company_noise_words(value: str) -> str:
    """Убирает служебные слова по краям: «Работал в СофтЛаб» -> «СофтЛаб»."""
    words = value.split()
    while words and to_lower(words[0].strip(".,")) in _COMPANY_NOISE_WORDS:
        words.pop(0)
    while words and to_lower(words[-1].strip(".,")) in _COMPANY_NOISE_WORDS:
        words.pop()
    return " ".join(words).strip()


def _looks_like_company(value: str) -> bool:
    """Проверяет, что фрагмент строки похож на компанию."""
    lowered = to_lower(value)
    if _is_skill_list(value):
        return False
    # Цифры почти всегда означают даты или стаж, а не название компании.
    # Проверка идёт до суффиксов, иначе «SoftLab 3 года» сочтётся компанией.
    if any(char.isdigit() for char in value):
        return False
    words = [word for word in value.split() if to_lower(word.strip(".,")) not in _COMPANY_NOISE_WORDS]
    if not 1 <= len(words) <= 4:
        return False
    if all(to_lower(word.strip(".,")) in _COMPANY_REJECT_WORDS for word in words):
        return False
    if any(suffix in lowered for suffix in _COMPANY_SUFFIXES):
        return True
    capital = sum(1 for word in words if word[:1].isupper())
    return capital == len(words)


def _looks_like_position(value: str) -> bool:
    """Проверяет, что фрагмент строки похож на должность."""
    lowered = to_lower(value)
    if any(char.isdigit() for char in value):
        return False
    if not 2 <= len(value) <= 70:
        return False
    # Должность - это короткое название, а не целая фраза опыта работы.
    if len(value.split()) > 5:
        return False
    if lowered in _TITLE_STOP_WORDS:
        return False
    title_words = (
        "developer",
        "engineer",
        "программист",
        "разработчик",
        "инженер",
        "тестировщик",
        "аналитик",
        "qa",
        "lead",
        "senior",
        "junior",
        "middle",
        "middle+",
        "intern",
        "стажер",
        "стажёр",
        "руководитель",
        "менеджер",
        "devops",
        "sdet",
        "fullstack",
        "full-stack",
        "backend",
        "frontend",
        "automation",
        "автоматизатор",
    )
    return any(word in lowered for word in title_words)


#: Заголовки, на которых заканчивается блок «Опыт работы».
_EMPLOYMENT_STOP_HEADINGS = (
    "образование",
    "education",
    "о себе",
    "about me",
    "навыки",
    "skills",
    "проекты",
    "projects",
    "дополнительная информация",
)


def _is_section_heading(line: str) -> bool:
    """Проверяет, что строка - заголовок раздела, а не обычный текст.

    Короткая строка нужна, чтобы обычную фразу вида «веду проекты в
    банковской сфере» не принять за конец раздела «Опыт работы».
    """
    normalized = to_lower(line).strip(" .:-–—")
    if not normalized or len(line) > 40:
        return False
    return any(
        normalized == marker or normalized.startswith(marker)
        for marker in _EMPLOYMENT_STOP_HEADINGS
    )


def _split_employment_lines(text: str) -> List[str]:
    """Отбирает строки блока «Опыт работы»."""
    lines = iter_lines(text)
    result: List[str] = []
    started = False
    for line in lines:
        lowered = to_lower(line)
        if not started and any(marker in lowered for marker in _EXPERIENCE_MARKERS):
            started = True
            continue
        if started and _is_section_heading(line):
            break
        if started:
            result.append(line)
    return result


#: Ведущий предлог не входит в название: «В SoftLab» -> «SoftLab».
_LEADING_PREPOSITION_RE = re.compile(r"^(?:в|во|на|у|с|со)\s+", re.IGNORECASE)


def _strip_leading_preposition(value: str) -> str:
    """Убирает предлог в начале названия компании."""
    return _LEADING_PREPOSITION_RE.sub("", (value or "").strip()).strip()


#: Хвост со стажем: «3 года», «1,5 лет» - это не часть названия компании.
_DURATION_TAIL_RE = re.compile(
    r"[\s,;]*\d+(?:[.,]\d+)?\s*(?:лет|года|год|месяцев|месяца|месяцев)\b\.?\s*$",
    re.IGNORECASE,
)


def _extract_employments(text: str, exclude: Sequence[str] = ()) -> Tuple[List[str], List[str]]:
    """Извлекает компании и должности из блока опыта работы.

    `exclude` - значения, которые не могут быть названием компании
    (например, имя кандидата: иначе «Иван Петров» в шапке резюме
    превратился бы в работодателя).
    """
    lines = _split_employment_lines(text) or iter_lines(text)
    excluded = {to_lower(value) for value in exclude if value}
    companies: List[str] = []
    positions: List[str] = []

    for line in lines:
        # Разбиваем строку на части по разделителям (даты, вертикальная черта).
        parts = [part.strip() for part in re.split(r"\s*[|;•·]\s*|\s{2,}", line) if part.strip()]
        for part in parts:
            without_dates = _DATE_RANGE_RE.sub(" ", part)
            without_dates = re.sub(r"\b\d{4}\b", " ", without_dates)
            # Хвост вида «3 года» - это стаж, а не часть названия.
            without_dates = _DURATION_TAIL_RE.sub(" ", without_dates)
            cleaned = clean_fragment(without_dates, limit=70)
            if not cleaned or to_lower(cleaned) in excluded:
                continue
            # Компания может быть названа внутри длинной фразы:
            # «Работал в компании Acme на позиции Backend Developer».
            # Это проверяется первым, иначе вся фраза уедет в должности.
            inner = _company_inside_phrase(cleaned, excluded)
            if inner:
                if inner not in companies:
                    companies.append(inner)
                phrase_position = _position_inside_phrase(cleaned)
                if phrase_position and phrase_position not in positions:
                    positions.append(phrase_position)
                continue
            # Затем должность: «Senior Backend Developer» -
            # это не компания, хотя и состоит из заглавных слов.
            if _looks_like_position(cleaned):
                if cleaned not in positions:
                    positions.append(cleaned)
                continue
            company = clean_fragment(
                _strip_legal_forms(_strip_company_noise_words(_strip_leading_preposition(cleaned))),
                limit=70,
            )
            if not company:
                continue
            # «Работал в Python» - это про стек, а не про работодателя.
            if to_lower(company) in SKILL_NAMES_LOWER:
                continue
            if _looks_like_company(company) and company not in companies:
                companies.append(company)
    return companies, positions


#: Должность внутри фразы: «на позиции Backend Developer».
_POSITION_PHRASE_RE = re.compile(
    r"(?:на\s+позиции|в\s+должности|должность|позиция)\s+(?P<value>[A-ZА-ЯЁ][\w\.\-]{1,30}(?:\s+[A-ZА-ЯЁ][\w\.\-]{1,30}){0,3})",
    re.IGNORECASE,
)


def _position_inside_phrase(value: str) -> str:
    """Ищет должность внутри фразы опыта работы."""
    match = _POSITION_PHRASE_RE.search(value or "")
    if not match:
        return ""
    candidate = clean_fragment(match.group("value"), limit=50)
    return candidate if candidate and _looks_like_position(candidate) else ""


#: Фразы, после которых название компании стоит прямо в строке.
_EMPLOYER_PHRASE_RE = re.compile(
    r"(?:работал|работала|работалa|работаю|работали|был|была|трудился|трудилась)\s+"
    r"(?:в|на|в\s+течение)\s+(?:компании|фирме|организации|студии|команде)\s+"
    r"(?P<value>[«\"']?[\w\.\-«»\"']{2,40})",
    re.IGNORECASE,
)


#: Формы «В SoftLab», «В компании Acme» - короткая строка опыта работы.
_SHORT_EMPLOYER_RE = re.compile(
    r"^(?:в|на)\s+(?P<value>[«\"']?[A-ZА-ЯЁ][\w\.\-]{1,24}[»\"']?)$"
)

#: «Работал в СофтЛаб» - предлог «в» без слова «компании».
#: Флаг `(?i:...)` применён только к глаголу и предлогу: имя компании
#: должно начинаться с заглавной буквы, иначе в захват попадёт «на».
_EMPLOYER_ACCUSATIVE_RE = re.compile(
    r"(?i:работал|работала|работаю|работали|был|была|трудился|трудилась)\s+"
    r"(?i:в|на)\s+(?P<value>[A-ZА-ЯЁ][\w\.\-]{1,24}(?:\s+[A-ZА-ЯЁ][\w\.\-]{1,24}){0,1})"
    r"(?=\s|$|[.,;])"
)


def _company_inside_phrase(value: str, excluded: Sequence[str] = ()) -> str:
    """Ищет компанию внутри длинной фразы опыта работы."""
    candidate = ""
    match = _EMPLOYER_PHRASE_RE.search(value)
    if match:
        candidate = match.group("value")
    else:
        # Короткая строка вида «В SoftLab» или «В Acme Labs».
        short = _SHORT_EMPLOYER_RE.match(value)
        if short:
            candidate = short.group("value")
        else:
            accusative = _EMPLOYER_ACCUSATIVE_RE.search(value)
            if accusative:
                candidate = accusative.group("value")
    if not candidate:
        return ""
    candidate = _strip_legal_forms(clean_fragment(candidate, limit=40))
    if not candidate or to_lower(candidate) in excluded:
        return ""
    if any(char.isdigit() for char in candidate):
        return ""
    # «Работал в Python» - это про стек, а не про работодателя.
    if to_lower(candidate.strip("«»\"' ")) in SKILL_NAMES_LOWER:
        return ""
    if not (_looks_like_company(candidate) or _looks_like_position(candidate)):
        return ""
    return candidate


def _extract_titles(text: str, exclude: Sequence[str] = ()) -> Tuple[str, str]:
    """Извлекает текущую и желаемую должность из резюме."""
    current = ""
    target = ""
    for line in iter_lines(text):
        lowered = to_lower(line)
        if any(marker in lowered for marker in ("желаемая должность", "ищу позицию", "target", "желаемая позиция")):
            match = _TITLE_LABELS_RE.search(line)
            if match:
                target = clean_fragment(match.group("value"), limit=58)
        elif any(marker in lowered for marker in ("должность", "position", "current title", "текущая должность")):
            match = _TITLE_LABELS_RE.search(line)
            if match:
                current = clean_fragment(match.group("value"), limit=58)

    _, positions = _extract_employments(text, exclude)
    if not current and positions:
        current = positions[0]
    return current, target


#: Метка раздела, которую не нужно повторять в письме:
#: «Образование: высшее, МГТУ» -> «высшее, МГТУ».
_EDUCATION_LABEL_RE = re.compile(
    r"^(?:образование|education|обучение|учеба)\s*[:\-–—]\s*",
    re.IGNORECASE,
)

#: Степень перед словом «образование» тоже лишняя: в письве уже есть
#: блок «Образование: …», поэтому «Высшее образование, МГТУ» превращается
#: в «Образование: Высшее образование, МГТУ». Оставляем только «высшее».
_EDUCATION_DEGREE_PREFIX_RE = re.compile(
    r"^(?:(?P<incomplete>незаконченное\s+)?(?P<degree>высшее|среднее|техническое)\s+"
    r"(?:профессиональное\s+|техническое\s+)?образование"
    r"|(?P<bare>высшее|среднее|техническое))\s*,?\s+",
    re.IGNORECASE,
)


def _clean_education(value: str) -> str:
    """Убирает дублирование слова «образование» внутри факта.

    «Образование: Высшее образование, МГТУ» -> «высшее, МГТУ».
    """
    text = _EDUCATION_LABEL_RE.sub("", (value or "").strip())
    match = _EDUCATION_DEGREE_PREFIX_RE.match(text)
    if match:
        degree = match.group("degree") or match.group("bare")
        if match.group("incomplete"):
            degree = f"{match.group('incomplete').strip()} {degree}"
        text = f"{degree}, {text[match.end():]}"
    return text.strip(" .,:;-–—")


def _extract_education(text: str) -> List[str]:
    """Извлекает строки, похожие на образование.

    Пустые заголовки раздела («Образование») пропускаются: в письме нужны
    реальные факты, а не названия разделов. Сама метка раздела и слово
    «образование» внутри факта тоже убираются, иначе в письме получилось
    бы «Образование: Высшее образование, МГТУ».
    """
    found: List[str] = []
    for line in iter_lines(text):
        lowered = to_lower(line)
        if lowered in _EDUCATION_MARKERS or len(line) < 4:
            continue
        if any(marker in lowered for marker in _EDUCATION_MARKERS):
            value = _clean_education(line)
            if value:
                found.append(clean_fragment(value, limit=90))
    return dedupe(found)[:3]


def _extract_soft_skills(text: str) -> List[str]:
    """Ищет soft skills по словарю."""
    normalized = to_lower(_inline(text))
    found = []
    for skill in SOFT_SKILLS:
        if skill in normalized:
            found.append(skill)
    return found


def _split_vacancy_sections(text: str) -> Dict[str, List[str]]:
    """Делит текст вакансии на смысловые разделы.

    Возвращает словарь: `requirements` (обязательные требования),
    `optional` (желательное), `responsibilities` (обязанности),
    `other` (всё остальное, например «О вакансии», «Условия»).

    Разделы определяются по строкам-заголовкам. Если заголовков нет,
    весь текст попадает в `other`, и тогда требования определяются по
    всему тексту (см. analyze_vacancy).
    """
    sections: Dict[str, List[str]] = {
        "requirements": [],
        "optional": [],
        "responsibilities": [],
        "other": [],
    }
    current = "other"

    for line in iter_lines(text):
        lowered = to_lower(line)
        is_heading = len(line) <= 70

        if is_heading and any(marker in lowered for marker in _OPTIONAL_MARKERS):
            current = "optional"
            continue
        if is_heading and any(marker in lowered for marker in _RESPONSIBILITY_MARKERS):
            current = "responsibilities"
            continue
        if is_heading and any(marker in lowered for marker in _REQUIRED_MARKERS):
            current = "requirements"
            continue
        if is_heading and line.split(":", 1)[0].strip() and any(
            to_lower(line.split(":", 1)[0]) == marker for marker in _TITLE_MARKERS
        ):
            current = "other"
            continue
        sections[current].append(line)
    return sections


def _requirement_text(sections: Dict[str, List[str]], original: str) -> str:
    """Определяет текст, из которого берутся обязательные навыки."""
    required_lines = list(sections["requirements"])
    if required_lines and find_skills("\n".join(required_lines)):
        return "\n".join(required_lines)

    # Заголовков требований нет - берём всё, кроме желательного и обязанностей,
    # чтобы не потерять навыки из коротких вакансий.
    fallback = [line for line in sections["other"]]
    if fallback and find_skills("\n".join(fallback)):
        return "\n".join(fallback)
    return original or ""


def _extract_responsibilities(sections: Dict[str, List[str]]) -> List[str]:
    """Извлекает обязанности из раздела обязанностей (или по глаголам)."""
    collected: List[str] = []
    for line in sections["responsibilities"]:
        if 6 <= len(line) <= 220:
            collected.append(clean_fragment(line, limit=160))
    if not collected:
        for line in sections["other"]:
            lowered = to_lower(line)
            if 10 <= len(line) <= 220 and any(verb in lowered for verb in _ACTION_VERBS):
                collected.append(clean_fragment(line, limit=160))
    return dedupe(collected)[:10]


def _extract_requirements(sections: Dict[str, List[str]]) -> List[str]:
    """Возвращает строки требований (для отчёта «что нашли в вакансии»)."""
    return dedupe([clean_fragment(line, limit=160) for line in sections["requirements"]])[:12]


def _extract_min_years(text: str) -> Optional[int]:
    """Ищет требования к опыту («от 3 лет опыта»)."""
    normalized = _inline(text)
    for pattern in (
        re.compile(
            r"(?:от|не\s+менее|минимум|более|over|at\s+least|from)\s*(?:минимум\s*)?(\d{1,2})\s*(?:\+)?\s*"
            r"(?:лет|года|год|years?|yrs?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"(\d{1,2})\s*\+\s*(?:лет|years?)\b", re.IGNORECASE),
    ):
        match = pattern.search(normalized)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 40:
                return value
    return None


def analyze_resume(text: str) -> ResumeFacts:
    """Разбирает резюме и возвращает только подтверждённые факты."""
    matches = find_skill_matches(text or "")
    skills: List[str] = []
    skills_by_category: Dict[str, List[str]] = {}
    for match in matches:
        if is_derived_only(match.name):
            continue
        if match.name not in skills:
            skills.append(match.name)
        skills_by_category.setdefault(match.category, [])
        if match.name not in skills_by_category[match.category]:
            skills_by_category[match.category].append(match.name)

    name = _extract_name(text or "")
    current_title, target_title = _extract_titles(text or "", exclude=(name,))
    companies, positions = _extract_employments(text or "", exclude=(name,))

    return ResumeFacts(
        name=name,
        current_title=current_title,
        target_title=target_title,
        years_of_experience=_extract_years(text or ""),
        companies=companies,
        positions=positions,
        skills=skills,
        skills_by_category=skills_by_category,
        soft_skills=_extract_soft_skills(text or ""),
        education=_extract_education(text or ""),
        skill_matches=matches,
    )


def analyze_vacancy(text: str) -> VacancyFacts:
    """Разбирает вакансию: должность, компания, навыки, обязанности, опыт."""
    source = text or ""
    sections = _split_vacancy_sections(source)
    required_skills = display_skills(find_skills(_requirement_text(sections, source)))
    optional_skills = [
        skill
        for skill in display_skills(find_skills("\n".join(sections["optional"])))
        if skill not in required_skills
    ]

    return VacancyFacts(
        title=_extract_title(source),
        company=_extract_company(source),
        required_skills=required_skills,
        optional_skills=optional_skills,
        min_years=_extract_min_years(source),
        responsibilities=_extract_responsibilities(sections),
        requirements=_extract_requirements(sections),
    )


def _score_profession(professions: Sequence[object], text: str) -> Optional[str]:
    """Оценивает, какая профессия лучше всего подходит тексту."""
    normalized = to_lower(_inline(text or ""))
    if not normalized:
        return None

    skills = {to_lower(skill) for skill in find_skills(text or "")}
    test_keywords = (
        "qa",
        "test",
        "тест",
        "тестир",
        "автоматиз",
        "automation",
        "quality assurance",
    )
    is_testing = any(keyword in normalized for keyword in test_keywords)

    best_id = None
    best_score = 0.0
    for profession in professions:
        score = 0.0
        focus = set(getattr(profession, "focus_categories", ()))
        for keyword in getattr(profession, "detection_keywords", ()):  # словари профессий
            if to_lower(keyword) in normalized:
                score += 2.0
        for skill in skills:
            if _CATEGORY_OF.get(skill) in focus:
                score += 1.0
        if getattr(profession, "is_testing", False) == is_testing:
            score += 1.0
        if score > best_score:
            best_id, best_score = getattr(profession, "id", None), score
    return best_id if best_score >= 2.0 else None


def detect_profession(text: str, professions: Sequence[object]) -> Optional[str]:
    """Определяет профессию по тексту (используется только как подсказка UI)."""
    return _score_profession(professions, text)
