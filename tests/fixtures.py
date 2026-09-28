"""Тексты-примеры для тестов.

Резюме и вакансии здесь намеренно «живые»: с ними должны работать и
анализатор, и генератор, и веб-интерфейс (кнопка «Пример»).
"""

from __future__ import annotations

#: Главный учебный случай из технического задания:
#: в вакансии есть Docker, в резюме - нет. Письмо не должно упоминать Docker.
CANONICAL_RESUME = "Python, Django, PostgreSQL"
CANONICAL_VACANCY = "Python, Django, PostgreSQL, Docker"

BACKEND_RESUME = """Иван Петров
Должность: Backend Developer
Опыт работы: 6 лет

Опыт работы
Acme Tech, 2021 - настоящее время
Senior Backend Developer
Разрабатываю REST API на Python и Django, использую PostgreSQL, Redis, Docker, Git, Jenkins.

ООО Ромашка, 2019 - 2021
Backend Developer
Писал интеграции через API, работал с MySQL, Docker, Linux.

Образование
Высшее образование, МГТУ, 2016

О себе
Ответственность, работа в команде, внимание к деталям."""

BACKEND_VACANCY = """Вакансия: Backend Developer
Компания: ООО Айти Парк

Обязанности:
- Разработка и поддержка REST API на Python/Django;
- Проектирование схемы базы данных PostgreSQL;
- Настройка CI/CD и Docker для сборки.

Обязательные требования:
Python, Django, PostgreSQL, Docker, Linux, Git, REST API, SQL

Желательно:
Kubernetes, Kafka, Redis
Опыт от 3 лет."""

FRONTEND_RESUME = """Алексей Иванов
Frontend Developer, 5 лет опыта

Опыт работы
ООО Веб-Мастер, 2021 - сейчас
Frontend Developer
React, TypeScript, JavaScript, HTML, CSS, SCSS, Webpack, REST API, Redux, Git, Figma.
Адаптивная вёрстка, интеграция с API.

ИП Соколов, 2019 - 2021
Web Developer
Вёрстка на HTML/CSS, jQuery, Bootstrap, Vue, Ajax.

Образование
Высшее образование, УрГУ, 2019"""

FRONTEND_VACANCY = """Вакансия: Frontend Developer
Компания: ООО Айти Парк

Обязанности:
- Разработка интерфейсов на React и TypeScript;
- Вёрстка по дизайну из Figma, адаптивность;
- Интеграция с REST API.

Требования:
JavaScript, TypeScript, React, HTML, CSS, Git, REST API

Желательно:
Next.js, Webpack, Docker
Опыт от 2 лет."""

MANUAL_QA_RESUME = """Мария Смирнова
Должность: QA Engineer
Опыт работы: 4 года

Опыт работы
ООО ТехноСфера, 2022 - настоящее время
QA Engineer
Ручное тестирование веб-приложений: пишу тест-кейсы и чек-листы, веду регрессионное
и смоук-тестирование, заводить баг-репорты в Jira, тестирую API через Postman,
пишу SQL-запросы к PostgreSQL.

АО Диджитал, 2020 - 2022
Junior QA
Функциональное тестирование, работа с Charles, DevTools, Swagger.

Образование
Высшее образование, СПбГУ, 2020

О себе
Внимание к деталям, ответственность, коммуникабельность."""

MANUAL_QA_VACANCY = """Вакансия: QA Engineer
Компания: ООО Банк Технологии

Обязанности:
- Написание и актуализация тест-кейсов;
- Проведение регрессионного и смоук-тестирования;
- Проверка API через Postman и Swagger;
- Заведение дефектов в Jira.

Обязательные требования:
Functional Testing, Regression Testing, Test Cases, Bug Reporting, Jira, API Testing, Postman, SQL

Желательно:
TestRail, Charles
Опыт от 2 лет."""

AUTOMATION_QA_RESUME = """Дмитрий Орлов
Должность: Automation QA Engineer
Опыт работы: 3 года

Опыт работы
ООО СофтЛаб, 2022 - настоящее время
QA Automation Engineer
Автоматизация тестирования на Python и Pytest, Selenium WebDriver, Playwright,
API-тесты, Allure, Jenkins, Git, Docker, REST API.

АО Текст, 2021 - 2022
QA Engineer
Ручное тестирование, тест-кейсы, Jira, Postman.

Образование
Высшее образование, МИФИ, 2021"""

AUTOMATION_QA_VACANCY = """Вакансия: Automation QA Engineer
Компания: ООО Финтех

Обязанности:
- Разработка автотестов UI на Selenium/Playwright;
- Автоматизация API-тестов;
- Настройка запуска тестов в CI (Jenkins);
- Анализ отчётов Allure.

Обязательные требования:
Selenium, Playwright, Pytest, Python, API Testing, CI/CD, Allure, Git

Желательно:
Docker, Kubernetes, TestRail
Опыт от 2 лет."""

#: Готовые пары «направление -> (резюме, вакансия)».
DEMO_BY_PROFESSION = {
    "backend": (BACKEND_RESUME, BACKEND_VACANCY),
    "frontend": (FRONTEND_RESUME, FRONTEND_VACANCY),
    "manual_qa": (MANUAL_QA_RESUME, MANUAL_QA_VACANCY),
    "automation_qa": (AUTOMATION_QA_RESUME, AUTOMATION_QA_VACANCY),
}

#: Резюме без единого технологического навыка - проверяем запасной сценарий.
RESUME_WITHOUT_SKILLS = """Ольга Кузнецова
Менеджер проектов

Опыт работы 5 лет
Веду проекты в банковской сфере, работаю в команде, умею договариваться."""
