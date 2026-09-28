# Генератор сопроводительных писем для IT-вакансий

Локальный веб-приложение на Flask, которое собирает сопроводительное письмо
для отклика на вакансию по тексту резюме и тексту вакансии.

Анализ текста — **только правиловый, на чистом Python**. Внешние AI-сервисы,
API, базы данных и CDN не используются вообще. Текст резюме никуда не
отправляется и не сохраняется: письмо собирается в памяти и отдаётся обратно
в браузер.

```
Резюме + Вакансия  ->  analyze_resume / analyze_vacancy  ->  match_skills
                   ->  сборка абзацев по шаблонам направления  ->  письмо
```

## Возможности

- 4 направления: **Backend Developer**, **Web/Frontend Developer**,
  **Manual QA**, **Automation QA** (расширяется добавлением файла).
- Локальный анализатор резюме: имя, должность, стаж, компании, технологии,
  soft skills, образование.
- Локальный анализатор вакансии: название, обязательные и желательные
  требования, опыт, обязанности, требования, компания (если она названа).
- Сопоставление навыков на три списка: `MATCHED` / `MISSING` / `OPTIONAL`.
- 3 стиля письма: **Профессиональный**, **Краткий** (до 1000 символов,
  цель — 700–1000), **Уверенный**.
- Панель «Что найдено в вакансии» с тегами совпадений, пробелов и
  желательных требований.
- Письмо сразу редактируется в textarea, оттуда его можно
  **скопировать** или **скачать .txt**.

### Главное обещание: письмо не врёт

Навык, которого нет в резюме, **никогда** не попадает в письмо — даже если он
есть в вакансии. Это обеспечено тремя независимыми механизмами:

1. **Шаблоны рендерят только подтверждённые факты.** Подстановка работает
   только по данным, найденным в резюме. Если подставлять нечего, блок целиком
   выбрасывается, а не «додумывается».
2. **Цитаты из вакансии фильтруются.** Задача из вакансии вставляется в письмо
   в кавычках только если все её упомянутые навыки есть в резюме.
3. **Финальная проверка `verify_cover_letter()`.** Готовый текст сверяется с
   исходными текстами резюме и вакансии; всё, чего там нет, удаляется.
   Кавычки `«…»` трактуются как цитата: внутри должен быть дословный
   фрагмент исходного текста.

Ключевой тест-пример (`tests/test_generator.py`):

```python
# В резюме: Python, Django, PostgreSQL
# В вакансии: Python, Django, PostgreSQL, Docker
result = generate_cover_letter(resume_text=..., vacancy_text=...)
assert result.matched_skills == ["Python", "Django", "PostgreSQL", "SQL"]
assert result.missing_skills == ["Docker", "Linux"]
assert "Docker" not in result.cover_letter
```

## Требования

- **Python 3.11 или новее** (проверено на 3.12)
- **Flask** — единственная зависимость

Фреймворков на клиенте нет: только HTML5, CSS3 и Vanilla JavaScript.

## Установка

```bash
# 1. Виртуальное окружение
python -m venv .venv

# 2. Активация
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# 3. Зависимости
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

Открыть <http://127.0.0.1:5000>.

Сервер поднимается только на `127.0.0.1`, в интернет не выходит. Порт можно
поменять переменными окружения:

```bash
# Windows (PowerShell)
$env:PORT=5050; python app.py
# macOS / Linux
PORT=5050 python app.py
```

Остановка — `Ctrl+C`.

## Тесты

Тесты используют стандартный `unittest`, ничего доустанавливать не нужно.

```bash
python -m unittest discover -s tests -t .
```

Ожидаемый результат: **178 тестов, OK**.

| Файл | Что проверяет |
|------|---------------|
| `tests/test_skills.py` | словарь навыков, алиасы, `IMPLIES`, защита от ложных срабатываний |
| `tests/test_analyzer.py` | разбор резюме и вакансии, определение направления |
| `tests/test_matcher.py` | деление навыков на `MATCHED` / `MISSING` / `OPTIONAL` |
| `tests/test_generator.py` | правдивость письма, стили, детерминизм, отсутствие самохвастовства |
| `tests/test_app.py` | Flask-эндпоинты, JSON-контракт, отсутствие CDN |
| `tests/test_text_utils.py` | работа со склонениями, числами, обрезкой текста |

## Структура проекта

```
.
├── app.py                     # Flask: маршруты /, /api/meta, POST /generate
├── requirements.txt           # Flask
├── README.md
├── generator/
│   ├── __init__.py            # публичный API пакета
│   ├── config.py              # пороги, запрещённые фразы, стоп-слова
│   ├── text_utils.py          # склонения, числа, обрезка, разделение текста
│   ├── types.py               # ResumeFacts, VacancyFacts, MatchResult, результат
│   ├── skills.py              # словарь навыков и правила их поиска
│   ├── analyzer.py            # analyze_resume / analyze_vacancy / detect_profession
│   ├── matcher.py             # сопоставление навыков резюме и вакансии
│   ├── phrases.py             # детерминированный выбор формулировок (SHA-256)
│   ├── styles.py              # описания стилей письма
│   ├── generator.py           # сборка письма, проверка правдивости
│   └── professions/
│       ├── base.py            # Profession, LetterContext и помощники блоков
│       ├── backend.py
│       ├── frontend.py
│       ├── manual_qa.py
│       └── automation_qa.py
├── templates/index.html       # единственный шаблон (Jinja)
├── static/
│   ├── css/style.css
│   ├── js/app.js
│   └── img/favicon.svg
└── tests/
    ├── fixtures.py            # эталонные резюме и вакансии
    └── test_*.py
```

## HTTP API

### `POST /generate`

Запрос:

```json
{
  "resume": "текст резюме",
  "vacancy": "текст вакансии",
  "profession": "backend",
  "style": "professional"
}
```

Успех — `200`:

```json
{
  "success": true,
  "cover_letter": "Здравствуйте! ...",
  "matched_skills": ["Python", "Django", "PostgreSQL", "SQL"],
  "missing_skills": ["Docker", "Linux"],
  "optional_skills": ["Kubernetes", "Redis"],
  "resume_only_skills": ["Celery"],
  "warnings": [],
  "profession": "backend",
  "style": "professional",
  "detected_profession": "backend",
  "vacancy_company": "Финтех",
  "vacancy_title": "Backend Developer"
}
```

Ошибка — `400` с понятным текстом:

```json
{ "success": false, "error": "Добавьте текст резюме.", "field": "resume" }
```

Поля ответа:

| Поле | Смысл |
|------|-------|
| `cover_letter` | готовый текст письма |
| `matched_skills` | навыки, которые есть и в резюме, и в требованиях вакансии |
| `missing_skills` | обязательные требования, которых в резюме нет |
| `optional_skills` | желательные требования, которых в резюме нет |
| `resume_only_skills` | навыки из резюме, которых нет в вакансии |
| `warnings` | предупреждения, например слишком короткий текст |
| `profession` | направление, по которому реально собрано письмо |
| `detected_profession` | направление, определённое по тексту |
| `vacancy_company` | компания из вакансии, если она названа |
| `vacancy_title` | должность из вакансии |

### `GET /api/meta`

Справочник направлений и стилей — удобно, если фронтенд делается отдельно.

### `GET /`

Страница приложения.

## Как это расширять

### Добавить навык

Всё в одном файле — `generator/skills.py`. Найдите нужную секцию и допишите
одну строку:

```python
Skill("Airflow", ("airflow", "apache airflow"), CATEGORY_INFRA),
```

Формат: `Skill(имя, (алиасы...), категория)`. Имя увидит пользователь, по
алиасам идёт поиск в тексте.

Специальные случаи:

- `context_only=True` — навык распознаётся только рядом со списком навыков.
  Так короткие слова вроде `Go` и `C` не дают ложных срабатываний.
- Алиас, оканчивающийся на `*`, работает как префикс: `("регресси*",)`.
- Если навык подразумевает другие, добавьте их в `IMPLIES`:
  ```python
  IMPLIES = {..., "PostgreSQL": ("SQL",)}
  ```

### Добавить профессию

Создайте файл рядом с существующими в `generator/professions/`, например
`data_analyst.py`. Он подгрузится автоматически — реестр сканирует папку,
правки в других файлах не нужны.

Нужен объект `PROFESSION` и функция `build_paragraphs`:

```python
from ..skills import CATEGORY_DATABASE, CATEGORY_LANGUAGE, CATEGORY_TOOL
from .base import (
    Profession, closing, experience_line, greeting, interest_line, skill_line,
)

PROFESSION = Profession(
    id="data_analyst",
    label="Data Analyst",
    short_label="Data",
    description="Аналитика данных, SQL-отчёты, визуализация.",
    default_title="Data Analyst",
    focus_genitive="аналитики данных",
    focus_dative="аналитике данных",
    focus_prepositional="аналитике данных",
    detection_keywords=("analyst", "аналитик", "data", "sql", "bi"),
    # Порядок важен: категории, которые стоят раньше, попадают в письмо
    # первыми, когда навыков много, а места хватает не на все.
    focus_categories=(CATEGORY_LANGUAGE, CATEGORY_DATABASE, CATEGORY_TOOL),
)

_INTEREST = ("Откликаюсь на вакансию {title}.",)
_EXPERIENCE = ("В аналитике данных работаю {years}.",)
_STACK = ("Основной стек: {skills}.",)


def build_paragraphs(ctx):
    return [
        greeting(ctx),
        interest_line(ctx, _INTEREST, "data-interest"),
        experience_line(ctx, _EXPERIENCE, "data-experience"),
        skill_line(ctx, _STACK, "data-stack"),
        closing(ctx),
    ]
```

Чтобы карточка шла в нужном месте, впишите `id` в `PROFESSION_ORDER`
в `generator/professions/__init__.py`; новые направления и так добавляются в
конец автоматически.

### Изменить формулировки

Формулировки лежат в каждом модуле направления как кортежи строк — это пулы
вариантов. Хотите изменить тон или добавить вариант: правьте нужный пул,
например `_STACK` в `generator/professions/backend.py`.

Каждая строка-вариант может содержать подстановки вида `{skills}`, `{years}`,
`{company}`. Если подставлять нечего, строка просто не используется.

Если вариантов несколько, выбор **детерминированный**: он считается через
SHA-256 от «зерна» (направление + стиль + хеши обоих текстов) и номера слота.
Один и тот же вход всегда даёт один и тот же результат, а разный вход —
разные формулировки. Зерно можно задать вручную:

```python
from generator import generate_cover_letter

generate_cover_letter(resume_text=..., vacancy_text=..., seed="42")
```

### Добавить стиль письма

Всё в `generator/styles.py`, добавить запись в `STYLES`:

```python
"formal": StyleSpec(
    id="formal",
    label="Официальный",
    description="Максимально сдержанный тон.",
    max_skills=5,
    include_soft_skills_block=False,
),
```

Задают длину и состав письма: сколько навыков упоминать (`max_skills`),
какие блоки включать (`include_*_block`), тон (`enthusiasm`) и ограничение
длины (`brief`). Карточка стиля в интерфейсе появится сама.

## Ограничения и настройка

Все пороги собраны в `generator/config.py`:

| Параметр | Значение | Зачем |
|----------|----------|-------|
| `MIN_INPUT_CHARS` | 10 | короче — считается пустым вводом |
| `MIN_MEANINGFUL_WORDS` | 3 | отсекает случайные слова вместо резюме |
| `RECOMMENDED_INPUT_CHARS` | 200 | ниже порога показывается подсказка |
| `MAX_INPUT_CHARS` | 20000 | защита от слишком больших текстов |
| `BRIEF_MIN_CHARS` / `BRIEF_MAX_CHARS` | 700 / 1000 | границы стиля «Краткий» |
| `MAX_SKILLS_MENTIONED` | 7 | максимум навыков в одном письме |
| `MAX_TASKS_QUOTED` | 2 | максимум цитируемых задач из вакансии |
| `BANNED_PHRASES` | — | формулировки, которые запрещено использовать |

### Про нижнюю границу «Короткого» письма

`BRIEF_MIN_CHARS` — это **цель, а не гарантия**. Если письмо получилось короче
700 символов, генератор сначала попробует достать из резюме то, что ещё не
использовал:

1. поднять лимит навыков, чтобы показать больше совпадений с вакансией
   (это подтверждённые факты, а не выдумка);
2. добавить неиспользованные навыки резюме;
3. процитировать ещё одну задачу из вакансии;
4. добавить стаж с компанией;
5. добавить soft skills и образование — то, чего стиль по умолчанию не
   показывает.

Если в резюме больше нечего добавить, письмо останется коротким, а в поле
`warnings` появится сообщение:

> Данных в резюме немного, поэтому письмо получилось короче 700 символов.

Добивать длину выдуманными формулировками нельзя — это сломало бы главное
обещание генератора, поэтому короткое письмо лучше, чем правдивое, но длинное.
Предупреждение о длине честное: оно означает «в резюме нечего добавить», а не
«мы придержались красивого лимита».

Что стиль «Краткий» по умолчанию **не** включает: блок `soft skills` — это
общие слова, в коротком письме они только занимают место. Образование —
факт, поэтому оно включается. Управляется флагами `include_*_block` в
`generator/styles.py`.

Про письма сказано: никаких «я лучший кандидат» и «идеально подхожу» —
такие фразы отсекаются, а формулировки пишутся нейтрально, без указания
рода (`готов` не используется вообще). Это проверяется тестом по исходникам
шаблонов, а не только по готовым письмам.

## Гарантии приватности

- Текст резюме и вакансии **не сохраняется**: ни в базе, ни в файлы, ни в
  `localStorage`/`sessionStorage`/куках.
- Логирование Werkzeug отключено, чтобы содержимое запроса нигде не
  всплыло.
- Все ответы помечены `Cache-Control: no-store`.
- Ни одного обращения во внешнюю сеть: ни CDN, ни шрифтов, ни аналитики.
  CSS, JS, иконка и favicon лежат в `static/`.
- Сервер слушает только `127.0.0.1`.

## Использование как библиотека

Пакет `generator` работает и без веба:

```python
from generator import generate_cover_letter

result = generate_cover_letter(
    resume_text="Резюме: Python, Django, PostgreSQL, 3 года опыта.",
    vacancy_text="Вакансия: Python, Django, PostgreSQL, Docker.",
    profession="backend",
    style="professional",
)

print(result.cover_letter)
print(result.matched_skills)   # ['Python', 'Django', 'PostgreSQL', 'SQL']
print(result.missing_skills)   # ['Docker', 'Linux']
```
