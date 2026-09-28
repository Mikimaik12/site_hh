"""Общий словарь IT-навыков.

Ключевой модуль проекта: чтобы добавить новый навык, достаточно дописать
одну строку в соответствующую секцию ниже. Никаких правок в коде
анализатора, матчера или генератора делать не нужно.

Устройство записи:
    Skill("Python", ("python", "python3"), CATEGORY_LANGUAGE)
      * первое поле   — каноническое имя, которое видит пользователь;
      * второе поле   — синонимы (алиасы), по которым ищем текст;
      * третье поле   — категория (язык, фреймворк, БД, ...).

Особые случаи:
    * context_only=True — навык распознаётся только в «технологическом»
      контексте (рядом с запятой, списком навыков и т.п.). Так короткие
      слова вроде «Go» и «C» не дают ложных срабатываний.
    * IMPLIES — если в резюме найден навык из IMPLIES, автоматически
      добавляются перечисленные рядом с ним навыки (PostgreSQL -> SQL).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

# --- Категории навыков --------------------------------------------------------

CATEGORY_LANGUAGE = "language"
CATEGORY_FRAMEWORK = "framework"
CATEGORY_DATABASE = "database"
CATEGORY_INFRA = "infrastructure"
CATEGORY_CLOUD = "cloud"
CATEGORY_VCS = "vcs"
CATEGORY_CI = "ci"
CATEGORY_API = "api"
CATEGORY_PRACTICE = "practice"
CATEGORY_TESTING = "testing"
CATEGORY_QA_TOOL = "qa_tool"
CATEGORY_TOOL = "tool"
CATEGORY_OTHER = "other"

CATEGORY_LABELS: Dict[str, str] = {
    CATEGORY_LANGUAGE: "языки программирования",
    CATEGORY_FRAMEWORK: "фреймворки и библиотеки",
    CATEGORY_DATABASE: "базы данных",
    CATEGORY_INFRA: "инфраструктура и DevOps",
    CATEGORY_CLOUD: "облачные сервисы",
    CATEGORY_VCS: "системы контроля версий",
    CATEGORY_CI: "CI/CD",
    CATEGORY_API: "API и протоколы",
    CATEGORY_PRACTICE: "практики разработки",
    CATEGORY_TESTING: "виды тестирования",
    CATEGORY_QA_TOOL: "QA-инструменты",
    CATEGORY_TOOL: "инструменты",
    CATEGORY_OTHER: "прочее",
}


@dataclass(frozen=True)
class Skill:
    """Описание одного навыка из словаря."""

    name: str
    aliases: Tuple[str, ...]
    category: str = CATEGORY_OTHER
    context_only: bool = False


# --- Языки программирования ----------------------------------------------------

LANGUAGES: Tuple[Skill, ...] = (
    Skill("Python", ("python", "python3", "python 3"), CATEGORY_LANGUAGE),
    Skill("Java", ("java",), CATEGORY_LANGUAGE),
    Skill("JavaScript", ("javascript", "java script", "ecmascript", "js"), CATEGORY_LANGUAGE),
    Skill("TypeScript", ("typescript", "type script"), CATEGORY_LANGUAGE),
    Skill("C#", ("c#", "c sharp", "csharp"), CATEGORY_LANGUAGE),
    Skill("C++", ("c++", "cpp", "c plus plus"), CATEGORY_LANGUAGE),
    Skill("C", ("c",), CATEGORY_LANGUAGE, context_only=True),
    Skill("Go", ("golang", "go",), CATEGORY_LANGUAGE, context_only=True),
    Skill("PHP", ("php",), CATEGORY_LANGUAGE),
    Skill("Ruby", ("ruby", "rails ruby"), CATEGORY_LANGUAGE),
    Skill("Kotlin", ("kotlin",), CATEGORY_LANGUAGE),
    Skill("Swift", ("swift",), CATEGORY_LANGUAGE),
    Skill("Rust", ("rust",), CATEGORY_LANGUAGE),
    Skill("Scala", ("scala",), CATEGORY_LANGUAGE),
    Skill("Dart", ("dart",), CATEGORY_LANGUAGE),
    Skill("Elixir", ("elixir",), CATEGORY_LANGUAGE),
    Skill("Perl", ("perl",), CATEGORY_LANGUAGE),
    Skill("SQL", ("sql", "sql92", "ansi sql"), CATEGORY_DATABASE),
    Skill("Bash", ("bash", "shell scripting", "shell script"), CATEGORY_LANGUAGE),
    Skill("Assembly", ("assembly", "asm"), CATEGORY_LANGUAGE),
)

# --- Фреймворки и библиотеки (backend) ----------------------------------------

BACKEND_FRAMEWORKS: Tuple[Skill, ...] = (
    Skill("Django", ("django",), CATEGORY_FRAMEWORK),
    Skill("Flask", ("flask",), CATEGORY_FRAMEWORK),
    Skill("FastAPI", ("fastapi", "fast api"), CATEGORY_FRAMEWORK),
    Skill("Spring", ("spring", "spring boot", "springboot"), CATEGORY_FRAMEWORK),
    Skill(".NET", (".net", "dotnet", "dot net", "asp.net", "aspnet"), CATEGORY_FRAMEWORK),
    Skill("Node.js", ("node.js", "node js", "nodejs"), CATEGORY_FRAMEWORK),
    Skill("Express", ("express.js", "express js", "expressjs"), CATEGORY_FRAMEWORK),
    Skill("NestJS", ("nestjs", "nest js"), CATEGORY_FRAMEWORK),
    Skill("Laravel", ("laravel",), CATEGORY_FRAMEWORK),
    Skill("Symfony", ("symfony",), CATEGORY_FRAMEWORK),
    Skill("Rails", ("rails", "ruby on rails"), CATEGORY_FRAMEWORK),
    Skill("Gin", ("gin gonic", "gin framework"), CATEGORY_FRAMEWORK),
    Skill("gRPC", ("grpc",), CATEGORY_FRAMEWORK),
    Skill("GraphQL", ("graphql", "graph ql"), CATEGORY_API),
    Skill("REST API", ("rest api", "rest-api", "restful", "restful api", "rest apis"), CATEGORY_API),
    Skill("WebSocket", ("websocket", "web socket"), CATEGORY_API),
    Skill("SQLAlchemy", ("sqlalchemy",), CATEGORY_FRAMEWORK),
    Skill("Hibernate", ("hibernate",), CATEGORY_FRAMEWORK),
    Skill("Pydantic", ("pydantic",), CATEGORY_FRAMEWORK),
    Skill("Celery", ("celery",), CATEGORY_FRAMEWORK),
    Skill("Elasticsearch", ("elasticsearch", "elastic search"), CATEGORY_DATABASE),
    Skill("RabbitMQ", ("rabbitmq", "rabbit mq"), CATEGORY_INFRA),
    Skill("Kafka", ("kafka", "apache kafka"), CATEGORY_INFRA),
    Skill("OAuth 2.0", ("oauth2", "oauth 2.0", "oauth2.0"), CATEGORY_API),
    Skill("JWT", ("jwt", "json web token"), CATEGORY_API),
    Skill("Microservices", ("microservices", "микросервисы", "микросервисная архитектура"), CATEGORY_PRACTICE),
    Skill("API Design", ("api design", "проектирование api"), CATEGORY_PRACTICE),
)

# --- Фронтенд ------------------------------------------------------------------

FRONTEND_FRAMEWORKS: Tuple[Skill, ...] = (
    Skill("React", ("react", "react.js", "reactjs", "react js"), CATEGORY_FRAMEWORK),
    Skill("Vue", ("vue", "vue.js", "vuejs", "vue 3", "vue.js 3"), CATEGORY_FRAMEWORK),
    Skill("Angular", ("angular", "angularjs", "angular 2"), CATEGORY_FRAMEWORK),
    Skill("Next.js", ("next.js", "nextjs", "next js"), CATEGORY_FRAMEWORK),
    Skill("Nuxt", ("nuxt", "nuxt.js", "nuxtjs"), CATEGORY_FRAMEWORK),
    Skill("Svelte", ("svelte", "sveltekit"), CATEGORY_FRAMEWORK),
    Skill("Redux", ("redux", "redux toolkit"), CATEGORY_FRAMEWORK),
    Skill("MobX", ("mobx",), CATEGORY_FRAMEWORK),
    Skill("jQuery", ("jquery",), CATEGORY_FRAMEWORK),
    Skill("HTML", ("html", "html5", "html 5"), CATEGORY_LANGUAGE),
    Skill("CSS", ("css", "css3", "css 3"), CATEGORY_LANGUAGE),
    Skill("SCSS", ("scss", "sass"), CATEGORY_LANGUAGE),
    Skill("Tailwind CSS", ("tailwind", "tailwindcss", "tailwind css"), CATEGORY_FRAMEWORK),
    Skill("Bootstrap", ("bootstrap",), CATEGORY_FRAMEWORK),
    Skill("Webpack", ("webpack",), CATEGORY_TOOL),
    Skill("Vite", ("vite",), CATEGORY_TOOL),
    Skill("Figma", ("figma",), CATEGORY_TOOL),
    Skill("Storybook", ("storybook",), CATEGORY_TOOL),
    Skill("Responsive Design", ("responsive design", "адаптивная вёрстка", "адаптивная верстка", "отзывчивый дизайн"), CATEGORY_PRACTICE),
    Skill("Cross-browser Testing", ("cross-browser", "cross browser", "кроссбраузерн"), CATEGORY_PRACTICE),
)

# --- Базы данных и хранилища ---------------------------------------------------

DATABASES: Tuple[Skill, ...] = (
    Skill("PostgreSQL", ("postgresql", "postgres", "postgre sql", "pg"), CATEGORY_DATABASE),
    Skill("MySQL", ("mysql", "my sql"), CATEGORY_DATABASE),
    Skill("MariaDB", ("mariadb",), CATEGORY_DATABASE),
    Skill("MongoDB", ("mongodb", "mongo db", "mongo"), CATEGORY_DATABASE),
    Skill("Redis", ("redis",), CATEGORY_DATABASE),
    Skill("ClickHouse", ("clickhouse", "click house"), CATEGORY_DATABASE),
    Skill("MSSQL", ("mssql", "sql server", "microsoft sql server"), CATEGORY_DATABASE),
    Skill("Oracle", ("oracle db", "oracle database", "pl/sql", "plsql"), CATEGORY_DATABASE),
    Skill("SQLite", ("sqlite", "sqlite3"), CATEGORY_DATABASE),
    Skill("DynamoDB", ("dynamodb",), CATEGORY_DATABASE),
    Skill("Cassandra", ("cassandra",), CATEGORY_DATABASE),
    Skill("Neo4j", ("neo4j",), CATEGORY_DATABASE),
    Skill("Prisma", ("prisma",), CATEGORY_FRAMEWORK),
    Skill("Liquibase", ("liquibase",), CATEGORY_FRAMEWORK),
)

# --- Инфраструктура, DevOps, облако --------------------------------------------

INFRASTRUCTURE: Tuple[Skill, ...] = (
    Skill("Docker", ("docker", "dockerfile"), CATEGORY_INFRA),
    Skill("Kubernetes", ("kubernetes", "k8s", "кубернетес"), CATEGORY_INFRA),
    Skill("Linux", ("linux", "ubuntu", "debian", "centos", "rhel"), CATEGORY_INFRA),
    Skill("Nginx", ("nginx",), CATEGORY_INFRA),
    Skill("Terraform", ("terraform",), CATEGORY_INFRA),
    Skill("Ansible", ("ansible",), CATEGORY_INFRA),
    Skill("Jenkins", ("jenkins",), CATEGORY_CI),
    Skill("GitLab CI", ("gitlab ci", "gitlab-ci", "gitlabci"), CATEGORY_CI),
    Skill("GitHub Actions", ("github actions", "gh actions"), CATEGORY_CI),
    Skill("CI/CD", ("ci/cd", "ci-cd", "cicd", "ci cd", "continuous integration", "непрерывная интеграция"), CATEGORY_CI),
    Skill("Git", ("git", "vcs", "система контроля версий"), CATEGORY_VCS),
    Skill("GitHub", ("github", "github.com"), CATEGORY_VCS),
    Skill("GitLab", ("gitlab", "gitlab.com"), CATEGORY_VCS),
    Skill("Bitbucket", ("bitbucket",), CATEGORY_VCS),
    Skill("AWS", ("aws", "amazon web services", "ec2", "s3"), CATEGORY_CLOUD),
    Skill("GCP", ("gcp", "google cloud", "google cloud platform"), CATEGORY_CLOUD),
    Skill("Azure", ("azure", "microsoft azure"), CATEGORY_CLOUD),
    Skill("Prometheus", ("prometheus",), CATEGORY_INFRA),
    Skill("Grafana", ("grafana",), CATEGORY_INFRA),
    Skill("Datadog", ("datadog",), CATEGORY_INFRA),
    Skill("Kibana", ("kibana", "elk stack"), CATEGORY_INFRA),
    Skill("Kafka UI", ("kafka ui",), CATEGORY_TOOL),
    Skill("Observability", ("observability", "наблюдаемость", "мониторинг"), CATEGORY_PRACTICE),
    Skill("Logging", ("logging", "логирование"), CATEGORY_PRACTICE),
    Skill("Performance Optimization", ("performance optimization", "оптимизация производительности", "профилирование", "profiling"), CATEGORY_PRACTICE),
    Skill("Code Review", ("code review", "код-ревью", "код ревью", "ревью кода"), CATEGORY_PRACTICE),
    Skill("Git Flow", ("git flow", "gitflow"), CATEGORY_PRACTICE),
    Skill("Scrum", ("scrum", "agile", "agile methodologies", "гибридная методология", "kanban"), CATEGORY_PRACTICE),
    Skill("Jira", ("jira",), CATEGORY_QA_TOOL),
    Skill("Confluence", ("confluence",), CATEGORY_TOOL),
    Skill("Docker Compose", ("docker-compose", "docker compose", "docker-compose.yml"), CATEGORY_INFRA),
)

# --- Тестирование и QA ---------------------------------------------------------

TESTING: Tuple[Skill, ...] = (
    Skill("Manual Testing", ("manual testing", "ручное тестирование", "manual qa", "manualtest"), CATEGORY_TESTING),
    Skill("Functional Testing", ("functional testing", "функциональное тестирование"), CATEGORY_TESTING),
    Skill("Regression Testing", ("regression testing", "регрессионное тестирование", "регресси*"), CATEGORY_TESTING),
    Skill("Smoke Testing", ("smoke testing", "смоук-тестирование", "смоук тестирование", "smoke test", "смоук*"), CATEGORY_TESTING),
    Skill("API Testing", ("api testing", "тестирование api", "api-тестирование", "тестирование api*"), CATEGORY_TESTING),
    Skill("UI Testing", ("ui testing", "тестирование интерфейса", "тестирование ui"), CATEGORY_TESTING),
    Skill("Integration Testing", ("integration testing", "интеграционное тестирование"), CATEGORY_TESTING),
    Skill("Load Testing", ("load testing", "нагрузочное тестирование"), CATEGORY_TESTING),
    Skill("Performance Testing", ("performance testing", "тестирование производительности"), CATEGORY_TESTING),
    Skill("Cross-platform Testing", ("cross-platform testing", "кроссплатформенное тестирование"), CATEGORY_TESTING),
    Skill("End-to-End Testing", ("end-to-end", "e2e", "сквозное тестирование"), CATEGORY_TESTING),
    Skill("Unit Testing", ("unit testing", "юнит-тестирование", "модульное тестирование"), CATEGORY_TESTING),
    Skill("Test Cases", ("test cases", "test case", "тест-кейсы", "тесткейсы", "тестовые кейсы", "чеклисты"), CATEGORY_PRACTICE),
    Skill("Bug Reporting", ("bug report", "bug reports", "баг-репорты", "багрепорты", "дефекты", "заведение багов"), CATEGORY_PRACTICE),
    Skill("Test Documentation", ("test documentation", "тестовая документация", "тест-план", "test plan", "тест-кейсы"), CATEGORY_PRACTICE),
    Skill("Test Design", ("test design", "проектирование тестов", "тестовое покрытие", "test coverage"), CATEGORY_PRACTICE),
    Skill("Requirements Analysis", ("requirements analysis", "анализ требований", "работа с требованиями"), CATEGORY_PRACTICE),
    Skill("Postman", ("postman",), CATEGORY_QA_TOOL),
    Skill("Swagger", ("swagger", "openapi", "open api"), CATEGORY_QA_TOOL),
    Skill("Charles", ("charles proxy", "charles", "fiddler", "proxyman"), CATEGORY_QA_TOOL),
    Skill("DevTools", ("devtools", "dev tools", "chrome devtools", "инструменты разработчика"), CATEGORY_QA_TOOL),
    Skill("Selenium", ("selenium", "selenoid", "selenium grid"), CATEGORY_QA_TOOL),
    Skill("Playwright", ("playwright", "play wright"), CATEGORY_QA_TOOL),
    Skill("Cypress", ("cypress",), CATEGORY_QA_TOOL),
    Skill("Pytest", ("pytest", "py test"), CATEGORY_QA_TOOL),
    Skill("JUnit", ("junit", "junit5", "junit 5", "testng"), CATEGORY_QA_TOOL),
    Skill("Allure", ("allure", "allure report", "allure2"), CATEGORY_QA_TOOL),
    Skill("TestRail", ("testrail", "test rail"), CATEGORY_QA_TOOL),
    Skill("Mocha", ("mocha", "mocha.js"), CATEGORY_QA_TOOL),
    Skill("Jest", ("jest",), CATEGORY_QA_TOOL),
    Skill("Robot Framework", ("robot framework", "robotframework"), CATEGORY_QA_TOOL),
    Skill("Page Object Model", ("page object", "page object model", "pom pattern", "page factory"), CATEGORY_PRACTICE),
    Skill("API Contract Testing", ("contract testing", "контрактные тесты", "schema validation"), CATEGORY_PRACTICE),
)

# --- Soft skills (ищутся только в резюме) ---------------------------------------

SOFT_SKILLS: Tuple[str, ...] = (
    "коммуникабельность",
    "работа в команде",
    "ответственность",
    "самостоятельность",
    "внимание к деталям",
    "внимательность",
    "обучаемость",
    "самообучение",
    "инициативность",
    "аналитическое мышление",
    "критическое мышление",
    "решение задач",
    "решение проблем",
    "стрессоустойчивость",
    "работа с дедлайнами",
    "управление временем",
    "сильные коммуникативные навыки",
    "analytical thinking",
    "problem solving",
    "teamwork",
    "communication skills",
    "ownership",
    "time management",
    "self-learning",
    "attention to detail",
    "proactivity",
)

# --- Сводный реестр -----------------------------------------------------------

ALL_SKILLS: Tuple[Skill, ...] = (
    LANGUAGES
    + BACKEND_FRAMEWORKS
    + FRONTEND_FRAMEWORKS
    + DATABASES
    + INFRASTRUCTURE
    + TESTING
)

#: Навыки, которые подразумеваются другими навыками.
#: Ключ — найденный навык, значение — что добавить в список.
IMPLIES: Dict[str, Tuple[str, ...]] = {
    "PostgreSQL": ("SQL",),
    "MySQL": ("SQL",),
    "MariaDB": ("SQL",),
    "MSSQL": ("SQL",),
    "Oracle": ("SQL",),
    "SQLite": ("SQL",),
    "ClickHouse": ("SQL",),
    "MongoDB": ("NoSQL",),
    "Spring": ("Java",),
    "Spring Boot": ("Java",),
    "Hibernate": ("Java", "SQL"),
    "JUnit": ("Java",),
    "React": ("JavaScript",),
    "Redux": ("JavaScript",),
    "Vue": ("JavaScript",),
    "Vuex": ("JavaScript",),
    "jQuery": ("JavaScript", "CSS", "HTML"),
    "Next.js": ("React", "JavaScript"),
    "Nuxt": ("Vue", "JavaScript"),
    "NestJS": ("Node.js", "TypeScript"),
    "Angular": ("TypeScript", "JavaScript"),
    "Django": ("Python",),
    "Flask": ("Python",),
    "FastAPI": ("Python",),
    "SQLAlchemy": ("Python", "SQL"),
    "Pytest": ("Python",),
    "Selenium": ("UI Testing",),
    "Playwright": ("UI Testing",),
    "Cypress": ("UI Testing",),
    "Express": ("Node.js", "JavaScript"),
    "Laravel": ("PHP",),
    "Symfony": ("PHP",),
    "Gin": ("Go",),
    "Rails": ("Ruby",),
    "Docker": ("Linux",),
    "Docker Compose": ("Docker",),
    "Kubernetes": ("Docker", "Linux"),
    "Terraform": ("Infrastructure as Code",),
    "Swagger": ("REST API",),
    "TestRail": ("Test Cases",),
    "Manual Testing": ("Test Cases", "Bug Reporting"),
    "Regression Testing": ("Functional Testing",),
    "Smoke Testing": ("Functional Testing",),
    "Allure": ("CI/CD",),
    "Git": ("Version Control",),
}

#: Служебные навыки, которые появляются только из IMPLIES и не ищутся в тексте.
#: Для них не нужен первичный поиск по алиасам.
DERIVED_ONLY = frozenset(
    {
        "NoSQL",
        "Infrastructure as Code",
        "Version Control",
        "Spring Boot",
    }
)

# --- Внутренние структуры для быстрого поиска ----------------------------------

_ALIAS_TO_SKILL: Dict[str, Skill] = {}
for _skill in ALL_SKILLS:
    for _alias in _skill.aliases:
        _ALIAS_TO_SKILL.setdefault(_alias, _skill)

SKILLS_BY_NAME: Dict[str, Skill] = {skill.name: skill for skill in ALL_SKILLS}

#: Тот же словарь, но ключи в нижнем регистре - для регистронезависимых
#: проверок вроде «является ли эта строка списком технологий?».
SKILL_NAMES_LOWER: frozenset = frozenset(skill.name.lower() for skill in ALL_SKILLS)

#: Разделители, рядом с которыми короткое слово считается технологией.
_CONTEXT_SEPARATORS = ",;/|&+()[]{}\n\t-–—•·:="

#: Слова, рядом с которыми список навыков очевидно технологический.
_CONTEXT_MARKERS = (
    "skills",
    "skill",
    "stack",
    "tech",
    "technologies",
    "technology",
    "tools",
    "tool",
    "expertise",
    "languages",
    "language",
    "framework",
    "навык",
    "навыки",
    "стек",
    "технолог",
    "технологии",
    "технология",
    "инструмент",
    "инструменты",
    "язык",
    "языки",
    "знаю",
    "владею",
    "использ",
    "умею",
    "опыт",
    "stack:",
    "связка",
    "связки",
    "компетенции",
    "профиль",
    "специализация",
)


def _alias_pattern(alias: str) -> str:
    """Собирает regex для алиаса.

    Особенности:
      * пробелы допускают любое количество дефисов/пробелов
        («rest api», «rest-api», «rest  api»);
      * алиас, оканчивающийся на `*`, превращается в префикс
        («регресси*» найдёт «регрессионное» и «регрессионные»);
      * границы слова проверяются через lookaround, поэтому «C++»
        и «C#» тоже находятся корректно.
    """
    wildcard = alias.endswith("*")
    if wildcard:
        alias = alias[:-1]
    parts = [re.escape(part) for part in alias.split()]
    body = r"[\s\-]+".join(parts)
    suffix = r"\w*" if wildcard else ""
    return rf"(?<![\w]){body}{suffix}(?![\w])"


#: Алиасы в порядке убывания длины. Regex-движок проверяет альтернативы
#: слева направо и берёт первую подходящую, поэтому длинные алиасы должны
#: идти раньше коротких: иначе в «SQL Server» нашлось бы «SQL»,
#: а не «MSSQL», а в «docker-compose» - «Docker», а не «Docker Compose».
_ORDERED_ALIASES: Tuple[str, ...] = tuple(
    sorted(_ALIAS_TO_SKILL, key=lambda alias: (-len(alias), alias))
)

_COMBINED_PATTERN = re.compile(
    "|".join(
        f"(?P<a{index}>{_alias_pattern(alias)})"
        for index, alias in enumerate(_ORDERED_ALIASES)
    ),
    re.IGNORECASE,
)

_MATCH_BY_GROUP = {
    f"a{index}": alias for index, alias in enumerate(_ORDERED_ALIASES)
}

_CONTEXT_WINDOW = 45


@dataclass(frozen=True)
class SkillMatch:
    """Одно найденное упоминание навыка в тексте."""

    name: str
    category: str
    start: int
    end: int


def _has_tech_context(text_lower: str, start: int, end: int) -> bool:
    """Проверяет, что короткий навык упомянут в технологическом контексте."""
    # 1) Рядом есть список навыков / раздел со стеком.
    left = text_lower[max(0, start - _CONTEXT_WINDOW) : start]
    if any(marker in left for marker in _CONTEXT_MARKERS):
        return True
    # 2) С обеих или с одной стороны стоит разделитель списка.
    before = start - 1
    while before >= 0 and text_lower[before] in " \t":
        before -= 1
    after = end
    while after < len(text_lower) and text_lower[after] in " \t":
        after += 1
    left_char = text_lower[before] if before >= 0 else "\n"
    right_char = text_lower[after] if after < len(text_lower) else "\n"
    if left_char in _CONTEXT_SEPARATORS or right_char in _CONTEXT_SEPARATORS:
        return True
    return False


def _raw_matches(text: str) -> List[SkillMatch]:
    """Все совпадения алиасов без учёта пересечений."""
    text_lower = text.lower()
    found: List[SkillMatch] = []
    for match in _COMBINED_PATTERN.finditer(text):
        alias = _MATCH_BY_GROUP[match.lastgroup]
        skill = _ALIAS_TO_SKILL[alias]
        if skill.context_only and not _has_tech_context(text_lower, match.start(), match.end()):
            continue
        found.append(SkillMatch(skill.name, skill.category, match.start(), match.end()))
    return found


def _drop_overlaps(matches: List[SkillMatch]) -> List[SkillMatch]:
    """Оставляет самое длинное (самое специфичное) упоминание из пересечений."""
    ordered = sorted(
        matches,
        key=lambda item: (
            -(item.end - item.start),
            list(SKILLS_BY_NAME).index(item.name) if item.name in SKILLS_BY_NAME else 0,
        ),
    )
    kept: List[SkillMatch] = []
    for candidate in ordered:
        if any(candidate.start < other.end and other.start < candidate.end for other in kept):
            continue
        kept.append(candidate)
    return sorted(kept, key=lambda item: item.start)


def _expand_implied(matches: List[SkillMatch]) -> List[SkillMatch]:
    """Добавляет навыки, которые следуют из найденных (PostgreSQL -> SQL)."""
    queue = list(matches)
    result = list(matches)
    seen = {match.name for match in result}
    while queue:
        current = queue.pop(0)
        for implied_name in IMPLIES.get(current.name, ()):  # явная зависимость
            if implied_name in seen:
                continue
            implied_skill = SKILLS_BY_NAME.get(implied_name)
            if implied_skill is None and implied_name not in DERIVED_ONLY:
                continue
            seen.add(implied_name)
            derived = SkillMatch(
                name=implied_name,
                category=implied_skill.category if implied_skill else CATEGORY_OTHER,
                start=current.start,
                end=current.end,
            )
            result.append(derived)
            queue.append(derived)
    return sorted(result, key=lambda item: item.start)


def find_skill_matches(text: str) -> List[SkillMatch]:
    """Возвращает все навыки, найденные в тексте, в порядке появления.

    Учитываются только вхождения с границами слова, пересечения
    отбрасываются, а подразумеваемые навыки добавляются автоматически.
    """
    from .text_utils import normalize_inline

    normalized = normalize_inline(text or "")
    if not normalized:
        return []
    return _expand_implied(_drop_overlaps(_raw_matches(normalized)))


def find_skills(text: str) -> List[str]:
    """Возвращает список имён навыков, найденных в тексте."""
    names: List[str] = []
    seen = set()
    for match in find_skill_matches(text):
        if match.name not in seen:
            seen.add(match.name)
            names.append(match.name)
    return names


def find_skills_by_category(text: str) -> Dict[str, List[str]]:
    """Группирует найденные навыки по категориям."""
    grouped: Dict[str, List[str]] = {}
    for match in find_skill_matches(text):
        bucket = grouped.setdefault(match.category, [])
        if match.name not in bucket:
            bucket.append(match.name)
    return grouped


def skills_in_categories(text: str, categories: Iterable[str]) -> List[str]:
    """Навыки текста, попадающие в указанные категории (в порядке появления)."""
    wanted = set(categories)
    names: List[str] = []
    for match in find_skill_matches(text):
        if match.category in wanted and match.name not in names:
            names.append(match.name)
    return names


def is_known_skill(name: str) -> bool:
    """Проверяет, что навык есть в словаре."""
    if name in SKILLS_BY_NAME or name in DERIVED_ONLY:
        return True
    return any(name in implied for implied in IMPLIES.values())


def is_derived_only(name: str) -> bool:
    """Навык, который появляется только из IMPLIES (в словаре его нет).

    Такие названия («Version Control», «Spring Boot») полезны при
    сопоставлении, но показывать их пользователю незачем.
    """
    return name in DERIVED_ONLY and name not in SKILLS_BY_NAME


def display_skills(names: Iterable[str]) -> List[str]:
    """Убирает служебные (производные) названия из списка для показа."""
    return [name for name in names if not is_derived_only(name)]


def known_skill_names() -> List[str]:
    """Все известные навыки (для интерфейса и документации)."""
    return sorted({skill.name for skill in ALL_SKILLS})
