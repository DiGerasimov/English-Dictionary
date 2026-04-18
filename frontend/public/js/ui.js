import { api, auth, playWordAudio, stopAudio } from "./api.js";

export function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function")
      el.addEventListener(k.slice(2).toLowerCase(), v);
    else el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

let toastHost;

export function toast(msg, type = "info") {
  if (!toastHost) {
    toastHost = h("div", {
      class:
        "fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 pointer-events-none",
    });
    document.body.append(toastHost);
  }
  const palette =
    type === "error"
      ? "bg-rose-900/90 border border-rose-500/50 text-rose-200"
      : type === "success"
        ? "bg-emerald-900/90 border border-emerald-500/50 text-emerald-200"
        : "bg-slate-800/90 border border-slate-600/50 text-slate-200";
  const el = h("div", {
    class: `toast ${palette} px-4 py-2 rounded-xl text-sm shadow-lg pointer-events-auto`,
  });
  el.textContent = msg;
  toastHost.append(el);
  setTimeout(() => {
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 200);
  }, 2200);
}

export function sheet(content, { title = "", footer = null } = {}) {
  const back = h("div", {
    class: "fixed inset-0 z-50 sheet-backdrop flex items-end justify-center",
    onclick: (e) => {
      if (e.target === back) close();
    },
  });
  const panel = h("div", {
    class:
      "sheet bg-slate-900 border-t border-white/10 w-full max-w-2xl rounded-t-3xl px-5 pt-4 pb-6 max-h-[85vh] flex flex-col",
  });
  const handle = h("div", { class: "w-10 h-1.5 bg-slate-700 rounded-full mx-auto mb-3" });
  panel.append(handle);
  if (title) {
    panel.append(
      h("h3", { class: "text-lg font-semibold mb-3 px-1" }, title),
    );
  }
  const body = h("div", { class: "flex-1 overflow-y-auto px-1" });
  body.append(content);
  panel.append(body);
  if (footer) panel.append(h("div", { class: "pt-3 mt-2 border-t border-white/10" }, footer));
  back.append(panel);
  document.body.append(back);
  const close = () => back.remove();
  return { close, el: panel };
}

export function modal(content, { title = "", onClose } = {}) {
  const back = h("div", {
    class: "fixed inset-0 z-50 sheet-backdrop flex items-center justify-center p-4",
    onclick: (e) => {
      if (e.target === back) close();
    },
  });
  const panel = h("div", {
    class:
      "modal-center bg-slate-900 border border-white/10 w-full max-w-lg rounded-2xl p-5 max-h-[90vh] overflow-y-auto",
  });
  if (title) {
    panel.append(
      h("div", { class: "flex items-center justify-between mb-3" }, [
        h("h3", { class: "text-lg font-semibold" }, title),
        h(
          "button",
          { class: "btn-ghost text-sm px-2 py-1", onclick: () => close() },
          "✕",
        ),
      ]),
    );
  }
  panel.append(content);
  back.append(panel);
  document.body.append(back);
  const close = () => {
    back.remove();
    if (onClose) onClose();
  };
  return { close, el: panel };
}

export function spinner(size = "w-8 h-8") {
  return h("div", {
    class: `${size} border-4 border-slate-700 border-t-brand-500 rounded-full animate-spin`,
  });
}

export function skeletonCard() {
  return h("div", { class: "space-y-3" }, [
    h("div", { class: "skeleton h-6 w-2/3" }),
    h("div", { class: "skeleton h-4 w-1/2" }),
    h("div", { class: "skeleton h-20 w-full" }),
  ]);
}

export function progressBar(value, max) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  const bar = h("div", { class: "progress-bar" }, [h("span", { style: `width:${pct}%` })]);
  return bar;
}

export function statusBadge(progress) {
  if (!progress || (!progress.seen && !progress.is_learned))
    return h("span", { class: "badge badge-new" }, "Новое");
  if (progress.is_learned) return h("span", { class: "badge badge-learned" }, "Изучено");
  return h("span", { class: "badge badge-learning" }, "Изучаем");
}

export function partOfSpeechLabel(pos) {
  return (
    {
      noun: "сущ.",
      verb: "глагол",
      adjective: "прил.",
      adverb: "нареч.",
      pronoun: "местоим.",
      preposition: "предлог",
      conjunction: "союз",
      interjection: "междом.",
      phrase: "фраза",
    }[pos] || pos
  );
}

export function difficultyLabel(d) {
  return { easy: "лёгкая", medium: "средняя", hard: "сложная" }[d] || d;
}

let autoPlayTimeout = null;

/**
 * Блок «слово + иконка динамика».
 * При voice_mode=true у пользователя текст слова под блюром до первого клика или до клика по слову.
 * size: "lg" — крупный заголовок (карточка/квиз), "md" — средний (детали).
 */
export function wordWithAudio(
  word,
  { size = "lg", allowBlur = true, autoPlay = true, withAudio = true } = {},
) {
  const user = auth.getUser() || {};
  const blurOn = Boolean(allowBlur && user.voice_mode);

  const textClass =
    size === "lg"
      ? "text-2xl sm:text-3xl font-bold tracking-tight leading-tight"
      : size === "md"
        ? "text-xl sm:text-2xl font-bold tracking-tight leading-tight"
        : "text-base font-semibold";

  const textEl = h(
    "span",
    {
      class: `word-text ${textClass} ${blurOn ? "word-blur" : ""}`,
      onclick: (e) => {
        if (!blurOn) return;
        e.stopPropagation();
        textEl.classList.toggle("revealed");
        const container = textEl.closest(".swipe-card, .quiz-card, .modal-center");
        if (container) {
          container.querySelectorAll(".word-blur").forEach((el) => el.classList.add("revealed"));
        }
      },
    },
    word.english,
  );

  if (!withAudio) {
    return h("span", { class: "word-with-audio" }, [textEl]);
  }

  const btn = h(
    "button",
    {
      type: "button",
      class: "audio-btn",
      "aria-label": "Прослушать",
      onclick: async (e) => {
        e.stopPropagation();
        clearTimeout(autoPlayTimeout);
        if (btn.classList.contains("is-loading")) return;
        btn.classList.add("is-loading");
        try {
          await playWordAudio(word.id);
        } catch (err) {
          toast(err.message || "Не удалось воспроизвести аудио", "error");
        } finally {
          btn.classList.remove("is-loading");
        }
      },
    },
    "🔊",
  );

  if (autoPlay && user.voice_mode) {
    clearTimeout(autoPlayTimeout);
    stopAudio();
    autoPlayTimeout = setTimeout(() => {
      if (document.body.contains(btn)) {
        btn.click();
      }
    }, 1000);
  }

  return h("span", { class: "word-with-audio" }, [textEl, btn]);
}

export function transcriptionLabel(text, { type = "ipa", allowBlur = true, extraClass = "" } = {}) {
  if (!text) return null;
  const user = auth.getUser() || {};
  const blurOn = Boolean(allowBlur && user.voice_mode);
  
  const baseClass = extraClass || (type === "ipa" 
    ? "text-sm text-slate-400" 
    : "text-xs text-slate-400 italic");
    
  const content = type === "ipa" ? `/${text}/` : `[${text}]`;
  
  const el = h("div", {
    class: `word-text ${baseClass} ${blurOn ? "word-blur" : ""}`,
    onclick: (e) => {
      if (!blurOn) return;
      e.stopPropagation();
      el.classList.toggle("revealed");
    }
  }, content);
  
  return el;
}

export function sortCategoriesWithPinned(categories) {
  return [...categories].sort((a, b) => {
    const ap = a.is_pinned ? 1 : 0;
    const bp = b.is_pinned ? 1 : 0;
    if (ap !== bp) return bp - ap;
    return (a.order_index || 0) - (b.order_index || 0);
  });
}

export function pinButton(category, onToggle) {
  const isPinned = Boolean(category.is_pinned);
  const btn = h(
    "button",
    {
      type: "button",
      class: `pin-btn ${isPinned ? "is-pinned" : ""}`,
      title: isPinned ? "Открепить" : "Закрепить сверху",
      "aria-label": isPinned ? "Открепить категорию" : "Закрепить категорию",
      onclick: async (e) => {
        e.stopPropagation();
        if (btn.disabled) return;
        btn.disabled = true;
        const newState = !isPinned;
        try {
          if (newState) await api.pinCategory(category.id);
          else await api.unpinCategory(category.id);
          category.is_pinned = newState;
          if (onToggle) onToggle();
        } catch (err) {
          toast(err.message || "Не удалось обновить закрепление", "error");
        } finally {
          btn.disabled = false;
        }
      },
    },
    isPinned ? "📌" : "📍",
  );
  return btn;
}

export function formTypeLabel(t) {
  return (
    {
      base: "base",
      past_simple: "past simple",
      past_participle: "past participle",
      present_participle: "-ing",
      third_person: "3rd person",
      plural: "множ. ч.",
      comparative: "compar.",
      superlative: "superl.",
    }[t] || t
  );
}

/**
 * Модалка выбора категорий с поиском. multi=true — мульти-выбор.
 * onConfirm вызывается с массивом выбранных id.
 */
export function categoryPickerSheet(categories, { selectedIds = [], multi = true, onConfirm, subtitleFor } = {}) {
  const selected = new Set(selectedIds);
  const container = h("div", { class: "space-y-3" });

  const searchInput = h("input", {
    class: "input",
    type: "search",
    placeholder: "Поиск по категории",
  });

  const grid = h("div", { class: "grid grid-cols-2 gap-2" });

  const rebuild = () => {
    grid.innerHTML = "";
    const q = searchInput.value.trim().toLowerCase();
    const filtered = categories.filter(
      (c) => !q || c.name_ru.toLowerCase().includes(q) || (c.name_en || "").toLowerCase().includes(q),
    );
    const visible = sortCategoriesWithPinned(filtered);
    if (!visible.length) {
      grid.append(
        h("div", { class: "col-span-2 text-sm text-slate-400 text-center py-6" }, "Ничего не найдено"),
      );
      return;
    }
    for (const c of visible) {
      const active = selected.has(c.id);
      const subtitle = subtitleFor ? subtitleFor(c) : `${c.learned_count}/${c.words_count} изучено`;
      const card = h(
        "button",
        {
          class: `category-card p-3 rounded-2xl border text-left transition ${
            active
              ? "bg-brand-600 text-white border-brand-500"
              : "bg-slate-800/50 border-slate-700/50 hover:border-brand-500"
          } ${c.is_pinned ? "is-pinned-card" : ""}`,
          onclick: () => {
            if (multi) {
              if (selected.has(c.id)) selected.delete(c.id);
              else selected.add(c.id);
            } else {
              selected.clear();
              selected.add(c.id);
            }
            rebuild();
            if (!multi) {
              result.close();
              if (onConfirm) onConfirm([...selected]);
            }
          },
        },
        [
          h("div", { class: "text-xl mb-1" }, c.icon || "📁"),
          h("div", { class: "font-medium text-sm leading-tight pr-6" }, c.name_ru),
          h(
            "div",
            {
              class: `text-[11px] mt-0.5 ${active ? "text-white/80" : "text-slate-400"}`,
            },
            subtitle,
          ),
        ],
      );
      grid.append(
        h("div", { class: "category-card-wrap" }, [card, pinButton(c, rebuild)]),
      );
    }
  };

  searchInput.addEventListener("input", rebuild);

  container.append(searchInput, grid);
  rebuild();

  const footer = h("div", { class: "flex gap-2" }, [
    h(
      "button",
      {
        class: "btn-ghost flex-1",
        onclick: () => {
          selected.clear();
          rebuild();
        },
      },
      "Очистить",
    ),
    h(
      "button",
      {
        class: "btn-primary flex-1",
        onclick: () => {
          result.close();
          if (onConfirm) onConfirm([...selected]);
        },
      },
      "Применить",
    ),
  ]);

  const result = sheet(container, {
    title: multi ? "Выберите категории" : "Выберите категорию",
    footer: multi ? footer : null,
  });
  return result;
}
