/* ==========================================================================
   Клиентская логика страницы генератора писем.
   Только Vanilla JavaScript: без фреймворков, без внешних библиотек и CDN.
   Все данные уходят в локальный Flask через POST /generate и нигде не
   сохраняются (ни в localStorage, ни в sessionStorage, ни в куках).
   ========================================================================== */

(function () {
  "use strict";

  var state = {
    profession: "backend",
    style: "professional",
    vkType: "vacancy_breakdown"
  };

  var vkLimits = window.VK_LIMITS || { max: 4000 };

  var el = {
    cards: Array.prototype.slice.call(document.querySelectorAll("[data-profession]")),
    styles: Array.prototype.slice.call(document.querySelectorAll("[data-style]")),
    activeName: document.getElementById("activeProfessionName"),
    resume: document.getElementById("resume"),
    vacancy: document.getElementById("vacancy"),
    resumeCounter: document.getElementById("resumeCounter"),
    vacancyCounter: document.getElementById("vacancyCounter"),
    resumeHint: document.getElementById("resumeHint"),
    vacancyHint: document.getElementById("vacancyHint"),
    generate: document.getElementById("generate"),
    alert: document.getElementById("alert"),
    alertText: document.getElementById("alertText"),
    resultSection: document.getElementById("resultSection"),
    coverLetter: document.getElementById("coverLetter"),
    letterCounter: document.getElementById("letterCounter"),
    copyBtn: document.getElementById("copyBtn"),
    downloadBtn: document.getElementById("downloadBtn"),
    resetBtn: document.getElementById("resetBtn"),
    matchedList: document.getElementById("matchedList"),
    missingList: document.getElementById("missingList"),
    optionalList: document.getElementById("optionalList"),
    optionalGroup: document.getElementById("optionalGroup"),
    warningsList: document.getElementById("warningsList"),
    warningsGroup: document.getElementById("warningsGroup"),
    factCompany: document.getElementById("factCompany"),
    factTitle: document.getElementById("factTitle"),
    fillResume: document.getElementById("fillResume"),
    fillVacancy: document.getElementById("fillVacancy"),
    clearResume: document.getElementById("clearResume"),
    clearVacancy: document.getElementById("clearVacancy"),
    vkSection: document.getElementById("vkSection"),
    vkTypes: Array.prototype.slice.call(document.querySelectorAll("[data-vk-type]")),
    vkGenerate: document.getElementById("vkGenerate"),
    vkAlert: document.getElementById("vkAlert"),
    vkAlertText: document.getElementById("vkAlertText"),
    vkStatus: document.getElementById("vkStatus"),
    vkPreview: document.getElementById("vkPreview"),
    vkPostText: document.getElementById("vkPostText"),
    vkCounter: document.getElementById("vkCounter"),
    vkCopyBtn: document.getElementById("vkCopyBtn"),
    vkPublishBtn: document.getElementById("vkPublishBtn"),
    vkPublishResult: document.getElementById("vkPublishResult"),
    vkWarningsGroup: document.getElementById("vkWarningsGroup"),
    vkWarningsList: document.getElementById("vkWarningsList"),
    publishModal: document.getElementById("publishModal"),
    publishModalText: document.getElementById("publishModalText"),
    publishCancel: document.getElementById("vkPublishCancel"),
    publishConfirm: document.getElementById("vkPublishConfirm")
  };

  var limits = window.APP_LIMITS || { min: 10, recommended: 200, max: 20000 };

  /* --- Вспомогательные функции -------------------------------------------- */

  function plural(value, one, few, many) {
    var mod10 = value % 10;
    var mod100 = value % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
    return many;
  }

  function updateCounter(field, counter, hint) {
    var length = field.value.length;
    counter.textContent = length + " " + plural(length, "символ", "символа", "символов");
    if (length > limits.max) {
      counter.textContent += " — превышен лимит " + limits.max;
    }
    if (hint) {
      hint.hidden = !(length > 0 && length < limits.recommended);
    }
  }

  function refreshCounters() {
    updateCounter(el.resume, el.resumeCounter, el.resumeHint);
    updateCounter(el.vacancy, el.vacancyCounter, el.vacancyHint);
    updateCounter(el.coverLetter, el.letterCounter, null);
    updateVkCounter();
  }

  // У поста свой лимит длины (он приходит с ответом сервера), поэтому
  // общий updateCounter с лимитом полей ввода для него не подходит.
  function updateVkCounter() {
    if (!el.vkPostText || !el.vkCounter) return;
    var length = el.vkPostText.value.length;
    el.vkCounter.textContent = length + " " + plural(length, "символ", "символа", "символов");
    if (length > vkLimits.max) {
      el.vkCounter.textContent += " — превышен лимит " + vkLimits.max;
    }
  }

  function showError(message) {
    el.alertText.textContent = message;
    el.alert.hidden = false;
  }

  function hideError() {
    el.alert.hidden = true;
    el.alertText.textContent = "";
  }

  function setLoading(isLoading) {
    el.generate.classList.toggle("is-loading", isLoading);
    el.generate.disabled = isLoading;
    el.generate.querySelector(".button__label").textContent = isLoading
      ? "Создаём письмо…"
      : "Создать сопроводительное письмо";
  }

  function selectGroup(buttons, value, dataKey) {
    buttons.forEach(function (button) {
      var isActive = button.dataset[dataKey] === value;
      button.setAttribute("aria-checked", isActive ? "true" : "false");
      button.tabIndex = isActive ? 0 : -1;
    });
  }

  function renderTags(container, items, variant, emptyText) {
    container.innerHTML = "";
    if (!items || items.length === 0) {
      var empty = document.createElement("span");
      empty.className = "tag tag--empty";
      empty.textContent = emptyText || "Ничего не найдено";
      container.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var tag = document.createElement("span");
      tag.className = "tag" + (variant ? " tag--" + variant : "");
      tag.textContent = item;
      container.appendChild(tag);
    });
  }

  /* --- Выбор направления и стиля ------------------------------------------ */

  function initGroups() {
    el.cards.forEach(function (card) {
      card.addEventListener("click", function () {
        state.profession = card.dataset.profession;
        selectGroup(el.cards, state.profession, "profession");
        el.activeName.textContent = card.querySelector(".card__title").textContent;
      });
      card.addEventListener("keydown", function (event) {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" &&
            event.key !== "ArrowDown" && event.key !== "ArrowUp") {
          return;
        }
        event.preventDefault();
        var index = el.cards.indexOf(card);
        var step = (event.key === "ArrowRight" || event.key === "ArrowDown") ? 1 : -1;
        var next = el.cards[(index + step + el.cards.length) % el.cards.length];
        next.focus();
        next.click();
      });
    });

    el.styles.forEach(function (style) {
      style.addEventListener("click", function () {
        state.style = style.dataset.style;
        selectGroup(el.styles, state.style, "style");
      });
    });

    // Инициализация подписей и состояния.
    var active = document.querySelector("[data-profession][aria-checked='true']");
    if (active) {
      state.profession = active.dataset.profession;
      el.activeName.textContent = active.querySelector(".card__title").textContent;
    }
  }

  /* --- Кнопки работы с текстом -------------------------------------------- */

  function initFieldTools() {
    /* window.DEMO_TEXTS[profession] = {resume: "...", vacancy: "..."} */
    function fill(field, key) {
      var demo = (window.DEMO_TEXTS || {})[state.profession];
      var text = demo && demo[key];
      if (!text) return;
      field.value = text;
      refreshCounters();
      hideError();
    }

    el.fillResume.addEventListener("click", function () {
      fill(el.resume, "resume");
      el.resume.focus();
    });
    el.fillVacancy.addEventListener("click", function () {
      fill(el.vacancy, "vacancy");
      el.vacancy.focus();
    });
    el.clearResume.addEventListener("click", function () {
      el.resume.value = "";
      refreshCounters();
      el.resume.focus();
    });
    el.clearVacancy.addEventListener("click", function () {
      el.vacancy.value = "";
      refreshCounters();
      el.vacancy.focus();
    });

    [el.resume, el.vacancy, el.coverLetter].forEach(function (field) {
      field.addEventListener("input", refreshCounters);
    });
  }

  /* --- Запрос к локальному серверу ---------------------------------------- */

  function generate() {
    hideError();

    var payload = {
      resume: el.resume.value,
      vacancy: el.vacancy.value,
      profession: state.profession,
      style: state.style
    };

    if (!payload.resume.trim()) { showError("Добавьте текст резюме."); el.resume.focus(); return; }
    if (!payload.vacancy.trim()) { showError("Добавьте описание вакансии."); el.vacancy.focus(); return; }

    setLoading(true);

    fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store"
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data || result.data.success !== true) {
          var message = (result.data && result.data.error) || "Не удалось создать письмо.";
          showError(message);
          return;
        }
        renderResult(result.data);
      })
      .catch(function () {
        showError("Сервер недоступен. Убедитесь, что приложение запущено (python app.py).");
      })
      .then(function () {
        setLoading(false);
      });
  }

  function renderResult(data) {
    el.coverLetter.value = data.cover_letter || "";
    refreshCounters();

    renderTags(el.matchedList, data.matched_skills, "good", "Совпадений не найдено");
    renderTags(el.missingList, data.missing_skills, "muted", "Всё из требований найдено в резюме");

    el.optionalGroup.hidden = !(data.optional_skills && data.optional_skills.length);
    if (!el.optionalGroup.hidden) {
      renderTags(el.optionalList, data.optional_skills, "bonus", "Желательных требований не найдено");
    }

    el.factCompany.textContent = data.vacancy_company || "не указана";
    el.factTitle.textContent = data.vacancy_title || "не указана";

    var warnings = data.warnings || [];
    el.warningsGroup.hidden = warnings.length === 0;
    el.warningsList.innerHTML = "";
    warnings.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      el.warningsList.appendChild(li);
    });

    el.resultSection.hidden = false;
    el.vkSection.hidden = false;
    el.resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* --- Копирование, скачивание, сброс ------------------------------------- */

  // Копирование через execCommand — работает даже там, где Clipboard API
  // недоступен или отклоняет запрос (нет разрешения, нет жеста пользователя).
  function copyTextFallback(text) {
    return new Promise(function (resolve, reject) {
      var helper = document.createElement("textarea");
      helper.value = text;
      helper.setAttribute("readonly", "");
      helper.style.position = "fixed";
      helper.style.top = "0";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      helper.setSelectionRange(0, text.length);
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (error) { ok = false; }
      document.body.removeChild(helper);
      ok ? resolve() : reject(new Error("copy failed"));
    });
  }

  function copyText(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).catch(function () {
        return copyTextFallback(text);
      });
    }
    return copyTextFallback(text);
  }

  function flashButton(button, text) {
    var label = button.querySelector("span");
    var original = label.textContent;
    label.textContent = text;
    button.classList.add("is-done");
    window.setTimeout(function () {
      label.textContent = original;
      button.classList.remove("is-done");
    }, 1600);
  }

  function initResultActions() {
    el.generate.addEventListener("click", generate);

    document.addEventListener("keydown", function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        if (!el.generate.disabled) generate();
      }
    });

    el.copyBtn.addEventListener("click", function () {
      var text = el.coverLetter.value.trim();
      if (!text) { showError("Письмо пустое — нечего копировать."); return; }
      copyText(text)
        .then(function () { flashButton(el.copyBtn, "Скопировано"); })
        .catch(function () { showError("Браузер не дал доступ к буферу обмена. Выделите текст и скопируйте вручную."); });
    });

    el.downloadBtn.addEventListener("click", function () {
      var text = el.coverLetter.value;
      if (!text.trim()) { showError("Письмо пустое — нечего скачивать."); return; }
      var blob = new Blob(["\uFEFF" + text], { type: "text/plain;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = url;
      link.download = "cover-letter-" + state.profession + ".txt";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      flashButton(el.downloadBtn, "Файл готов");
    });

    el.resetBtn.addEventListener("click", function () {
      el.coverLetter.value = "";
      el.resultSection.hidden = true;
      hideVkPreview();
      hideError();
      refreshCounters();
      el.resume.focus();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* --- Контент для VK ---------------------------------------------------------
     Пост готовится на сервере, публикуется только по явному подтверждению.
     Ключ доступа в браузер не попадает: его использует только Flask.
     ------------------------------------------------------------------------- */

  function showVkError(message, hint) {
    el.vkAlertText.textContent = hint ? message + " " + hint : message;
    el.vkAlert.hidden = false;
  }

  function hideVkError() {
    el.vkAlert.hidden = true;
    el.vkAlertText.textContent = "";
  }

  function hideVkPreview() {
    el.vkSection.hidden = true;
    el.vkPreview.hidden = true;
    el.vkPostText.value = "";
    el.vkPublishResult.hidden = true;
    hideVkError();
    updateVkCounter();
  }

  function setVkLoading(isLoading) {
    el.vkGenerate.classList.toggle("is-loading", isLoading);
    el.vkGenerate.disabled = isLoading;
    el.vkGenerate.querySelector(".button__label").textContent = isLoading
      ? "Создаём пост…"
      : "Создать пост для VK";
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store"
    }).then(function (response) {
      return response.json().then(function (data) {
        return { ok: response.ok, data: data };
      });
    });
  }

  function renderVkPost(data) {
    el.vkPostText.value = data.text || "";
    if (data.max_chars) {
      vkLimits.max = data.max_chars;
    }
    updateVkCounter();

    var warnings = data.warnings || [];
    el.vkWarningsGroup.hidden = warnings.length === 0;
    el.vkWarningsList.innerHTML = "";
    warnings.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      el.vkWarningsList.appendChild(li);
    });

    el.vkPublishResult.hidden = true;
    el.vkPreview.hidden = false;
    hideVkError();
  }

  function generateVkPost() {
    hideVkError();
    el.vkPublishResult.hidden = true;

    setVkLoading(true);
    postJson("/vk/post", {
      resume: el.resume.value,
      vacancy: el.vacancy.value,
      post_type: state.vkType
    })
      .then(function (result) {
        if (!result.ok || !result.data || result.data.success !== true) {
          showVkError((result.data && result.data.error) || "Не удалось создать пост для VK.");
          return;
        }
        renderVkPost(result.data);
      })
      .catch(function () {
        showVkError("Сервер недоступен. Убедитесь, что приложение запущено (python app.py).");
      })
      .then(function () {
        setVkLoading(false);
      });
  }

  /* Подтверждение публикации. Модалка вместо window.confirm: у браузерного
     диалога надписи кнопок зависят от языка интерфейса, а здесь важно,
     чтобы человек точно прочитал «Опубликовать этот пост в группу VK?»
     и мог отменить одним нажатием Esc. */
  function openPublishModal() {
    el.publishModal.hidden = false;
    el.publishConfirm.focus();
    document.addEventListener("keydown", onModalKeydown);
  }

  function closePublishModal() {
    el.publishModal.hidden = true;
    document.removeEventListener("keydown", onModalKeydown);
  }

  function onModalKeydown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closePublishModal();
      return;
    }
    if (event.key === "Tab") {
      // Фокус не должен уйти из модалки на страницу под ней.
      event.preventDefault();
      var target = event.shiftKey ? el.publishCancel : el.publishConfirm;
      target.focus();
    }
  }

  function publishVkPost() {
    var text = el.vkPostText.value.trim();
    if (!text) {
      closePublishModal();
      showVkError("Пост пустой. Напишите текст в поле предпросмотра.");
      return;
    }

    closePublishModal();
    el.vkPublishBtn.disabled = true;

    postJson("/vk/publish", { text: text })
      .then(function (result) {
        var data = result.data || {};
        if (!result.ok || data.success !== true) {
          showVkError(data.error || "Не удалось опубликовать запись в VK.", data.hint);
          return;
        }
        el.vkPublishResult.hidden = false;
        el.vkPublishResult.textContent = "Опубликовано. Запись №" + data.post_id + ": " + data.url;
      })
      .catch(function () {
        showVkError("Сервер недоступен. Убедитесь, что приложение запущено (python app.py).");
      })
      .then(function () {
        el.vkPublishBtn.disabled = false;
      });
  }

  function initVk() {
    el.vkTypes.forEach(function (button) {
      button.addEventListener("click", function () {
        state.vkType = button.dataset.vkType;
        selectGroup(el.vkTypes, state.vkType, "vkType");
      });
    });

    el.vkPostText.addEventListener("input", updateVkCounter);
    el.vkGenerate.addEventListener("click", generateVkPost);

    el.vkCopyBtn.addEventListener("click", function () {
      var text = el.vkPostText.value.trim();
      if (!text) { showVkError("Пост пустой — нечего копировать."); return; }
      copyText(text)
        .then(function () { flashButton(el.vkCopyBtn, "Скопировано"); })
        .catch(function () { showVkError("Браузер не дал доступ к буферу обмена. Выделите текст и скопируйте вручную."); });
    });

    el.vkPublishBtn.addEventListener("click", openPublishModal);
    el.publishCancel.addEventListener("click", closePublishModal);
    el.publishConfirm.addEventListener("click", publishVkPost);
    Array.prototype.forEach.call(
      el.publishModal.querySelectorAll("[data-vk-close]"),
      function (backdrop) { backdrop.addEventListener("click", closePublishModal); }
    );

    // Подсказка под кнопкой: без настроек VK генерация постов работает,
    // а публикация объяснит, чего не хватает.
    el.vkStatus.textContent = window.VK_ENABLED === true
      ? "Публикация идёт от имени сообщества. Перед отправкой будет запрос подтверждения."
      : "Посты можно создавать и копировать. Для публикации укажите VK_ACCESS_TOKEN и VK_GROUP_ID в файле .env.";
  }

  /* --- Старт ---------------------------------------------------------------- */

  document.addEventListener("DOMContentLoaded", function () {
    initGroups();
    initFieldTools();
    initResultActions();
    initVk();
    refreshCounters();
  });
})();
