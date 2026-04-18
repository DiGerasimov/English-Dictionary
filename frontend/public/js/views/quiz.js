import { api } from "../api.js";
import {
  difficultyLabel,
  h,
  partOfSpeechLabel,
  progressBar,
  sheet,
  skeletonCard,
  toast,
  wordWithAudio,
  transcriptionLabel,
  sortCategoriesWithPinned,
  pinButton,
} from "../ui.js";

const QUIZ_KEY = "english.quizSettings";
const QUIZ_STATS_KEY = "english.quizSessionStats";

const SETTINGS_FIELDS = ["scope", "only_unlearned", "category_id"];

function loadSettings() {
  try {
    const raw = JSON.parse(localStorage.getItem(QUIZ_KEY)) || {};
    const out = {};
    for (const k of SETTINGS_FIELDS) if (k in raw) out[k] = raw[k];
    return out;
  } catch {
    return {};
  }
}
function saveSettings(s) {
  const payload = {};
  for (const k of SETTINGS_FIELDS) payload[k] = s[k];
  localStorage.setItem(QUIZ_KEY, JSON.stringify(payload));
}

function loadStats() {
  try {
    const raw = JSON.parse(localStorage.getItem(QUIZ_STATS_KEY));
    if (raw && typeof raw === "object") {
      return {
        correct: Number(raw.correct) || 0,
        incorrect: Number(raw.incorrect) || 0,
        streak: Number(raw.streak) || 0,
      };
    }
  } catch {
    /* ignore */
  }
  return { correct: 0, incorrect: 0, streak: 0 };
}
function saveStats(s) {
  localStorage.setItem(
    QUIZ_STATS_KEY,
    JSON.stringify({ correct: s.correct, incorrect: s.incorrect, streak: s.streak }),
  );
}

export async function renderQuiz(root) {
  const state = {
    scope: "all",
    only_unlearned: true,
    category_id: null,
    categories: [],
    current: null,
    answered: false,
    loading: false,
    ...loadSettings(),
    session: loadStats(),
  };

  root.innerHTML = "";

  let lastWordId = null;

  const wrap = h("div", { class: "quiz-screen" });
  root.append(wrap);

  const header = h("header", { class: "px-4 pt-3 pb-1.5 space-y-1.5 shrink-0 min-w-0" });
  const topRow = h("div", { class: "flex items-center justify-between gap-2" }, [
    h("h1", { class: "text-lg font-bold" }, "Квиз"),
    h("div", { class: "text-xs flex items-center gap-2", "data-counter": true }),
  ]);
  const scopeRow = h("div", { class: "segmented w-full" });
  const optionsRow = h("div", { class: "flex items-center justify-between gap-2 text-xs flex-wrap" });
  header.append(topRow, scopeRow, optionsRow);

  const host = h("section", { class: "px-4 pb-3 flex flex-col min-w-0 gap-2" });
  wrap.append(header, host);

  try {
    state.categories = await api.categories();
  } catch (e) {
    toast(e.message, "error");
  }

  const counterHost = topRow.querySelector("[data-counter]");

  const renderCounters = () => {
    counterHost.innerHTML = "";
    counterHost.append(
      h("span", { class: "text-emerald-600 font-semibold" }, `✓ ${state.session.correct}`),
      h("span", { class: "text-rose-600 font-semibold" }, `✗ ${state.session.incorrect}`),
      h("span", { class: "text-slate-400" }, `🔥 ${state.session.streak}`),
      h(
        "button",
        {
          class: "text-slate-500 hover:text-slate-200 text-[13px] leading-none px-1",
          title: "Сбросить счётчик",
          "aria-label": "Сбросить счётчик",
          onclick: () => {
            state.session = { correct: 0, incorrect: 0, streak: 0 };
            saveStats(state.session);
            renderCounters();
          },
        },
        "↺",
      ),
    );
  };

  const renderHeader = () => {
    scopeRow.innerHTML = "";
    const btn = (id, label) =>
      h(
        "button",
        {
          class: `flex-1 ${state.scope === id ? "is-active" : ""}`,
          onclick: () => {
            state.scope = id;
            saveSettings(state);
            lastWordId = null;
            renderHeader();
            loadQuestion();
          },
        },
        label,
      );
    scopeRow.append(btn("all", "Все"), btn("category", "Категория"));

    optionsRow.innerHTML = "";
    const toggleUnl = h(
      "label",
      { class: "flex items-center gap-2 cursor-pointer select-none" },
      [
        h("input", {
          type: "checkbox",
          class: "accent-brand-500 w-4 h-4",
          checked: state.only_unlearned ? "checked" : undefined,
          onchange: (e) => {
            state.only_unlearned = e.target.checked;
            saveSettings(state);
            lastWordId = null;
            loadQuestion();
          },
        }),
        h("span", { class: "text-slate-300" }, "Только «Изучаем»"),
        h(
          "span",
          {
            class: "text-slate-500 text-[11px]",
            title:
              "Если выключено — иногда подмешиваются уже изученные слова для повторения",
          },
          "ⓘ",
        ),
      ],
    );
    optionsRow.append(toggleUnl);

    if (state.scope === "category") {
      const cat = state.categories.find((c) => c.id === state.category_id);
      optionsRow.append(
        h(
          "button",
          {
            class: "btn-outline text-xs py-1.5 px-2.5",
            onclick: () => openCategorySheet(state, loadQuestion, renderHeader),
          },
          cat ? `${cat.icon} ${cat.name_ru}` : "Выбрать категорию",
        ),
      );
    }

    renderCounters();
  };

  async function loadQuestion() {
    if (state.scope === "category" && !state.category_id) {
      renderEmpty("📁", "Выберите категорию", () =>
        openCategorySheet(state, loadQuestion, renderHeader),
      );
      return;
    }
    state.answered = false;
    state.loading = true;
    host.innerHTML = "";
    host.append(
      h("div", { class: "quiz-card" }, [skeletonCard()]),
    );
    try {
      state.current = await api.quizNext({
        scope: state.scope,
        category_id: state.scope === "category" ? state.category_id : undefined,
        only_unlearned: state.only_unlearned,
        exclude_word_id: lastWordId || undefined,
      });
      lastWordId = state.current?.word?.id || null;
      renderQuestion();
    } catch (e) {
      renderError(e.message);
    } finally {
      state.loading = false;
    }
  }

  function renderEmpty(icon, title, action) {
    host.innerHTML = "";
    host.append(
      h(
        "div",
        {
          class:
            "glass-panel rounded-2xl p-6 text-center text-slate-400 flex flex-col items-center justify-center",
        },
        [
          h("div", { class: "text-4xl mb-2" }, icon),
          h("div", { class: "font-medium mb-3" }, title),
          action
            ? h(
                "button",
                { class: "btn-primary", onclick: action },
                "Выбрать",
              )
            : null,
        ],
      ),
    );
  }

  function renderError(msg) {
    host.innerHTML = "";
    host.append(
      h(
        "div",
        {
          class:
            "glass-panel rounded-2xl p-6 text-center text-slate-400 flex flex-col items-center justify-center",
        },
        [
          h("div", { class: "text-4xl mb-2" }, "🙈"),
          h("div", { class: "font-medium mb-1" }, "Нет слов для квиза"),
          h("div", { class: "text-sm text-slate-400 mb-3" }, msg),
          h("a", { class: "btn-primary", href: "#/learn" }, "К изучению"),
        ],
      ),
    );
  }

  function renderQuestion() {
    const q = state.current;
    if (!q) return;
    const word = q.word;
    const progress = word.progress || {};
    host.innerHTML = "";

    const card = h(
      "article",
      {
        class: "quiz-card",
      },
      [
        h("div", { class: "flex items-center justify-between text-[11px] text-slate-400 mb-2 gap-2" }, [
          h("div", { class: "flex items-center gap-1 min-w-0 truncate" }, [
            h("span", {}, word.category.icon || "📁"),
            h("span", { class: "truncate" }, word.category.name_ru),
            h("span", { class: "text-slate-300" }, "·"),
            h("span", {}, partOfSpeechLabel(word.part_of_speech)),
            h("span", { class: "text-slate-300" }, "·"),
            h("span", {}, difficultyLabel(word.difficulty)),
          ]),
          q.is_review
            ? h(
                "span",
                {
                  class:
                    "whitespace-nowrap px-2 py-0.5 rounded-full bg-brand-900/30 text-brand-400 font-medium",
                },
                "🔄 Повторение",
              )
            : h(
                "span",
                { class: "whitespace-nowrap" },
                `✓ ${progress.correct_count || 0}/5`,
              ),
        ]),
        h(
          "div",
          { class: "py-6 sm:py-8 flex flex-col items-center justify-center gap-1" },
          [
            h(
              "div",
              { class: "text-center leading-tight" },
              [wordWithAudio(word, { size: "lg" })],
            ),
            word.transcription_ipa ? transcriptionLabel(word.transcription_ipa, { type: "ipa", extraClass: "text-xs sm:text-sm text-slate-400" }) : null,
          ],
        ),
        q.is_review ? null : progressBar(progress.correct_count || 0, 5),
      ],
    );

    const grid = h("div", { class: "quiz-grid" });
    q.options.forEach((opt) => {
      const btn = h(
        "button",
        {
          class: "quiz-option",
          onclick: () => submit(opt, btn, grid),
        },
        opt,
      );
      grid.append(btn);
    });

    host.append(card, grid);
  }

  async function submit(selected, btn, grid) {
    if (state.answered) return;
    state.answered = true;
    grid.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      const res = await api.quizAnswer({
        word_id: state.current.word.id,
        selected,
      });

      if (res.is_correct) {
        btn.classList.add("is-correct", "animate-pulse-glow");
        state.session.correct += 1;
        state.session.streak += 1;
      } else {
        btn.classList.add("is-wrong", "animate-shake");
        state.session.incorrect += 1;
        state.session.streak = 0;
      }
      saveStats(state.session);
      renderCounters();

      setTimeout(() => {
        renderAnswerDetail(res, selected);
      }, 600);
    } catch (e) {
      toast(e.message, "error");
      state.answered = false;
      grid.querySelectorAll("button").forEach((b) => (b.disabled = false));
    }
  }

  function renderAnswerDetail(res, selected) {
    const word = res.word;
    const p = word.progress || {};
    const isReview = !!res.is_review;
    const justLearned = !isReview && p.is_learned && p.correct_count === 5;
    host.innerHTML = "";

    const header = res.is_correct
      ? justLearned
        ? "Отлично! Слово изучено 🎉"
        : "Верно!"
      : `Правильный ответ: ${res.correct_answer}`;

    const detail = h(
      "div",
      {
        class: `quiz-card animate-slide-up-fade ${
          res.is_correct
            ? "bg-emerald-900/20 border-emerald-500/30"
            : "bg-rose-900/20 border-rose-500/30"
        }`,
      },
      [
        h("div", { class: "flex items-center justify-between gap-2 mb-2" }, [
          h(
            "div",
            {
              class: `text-sm font-semibold ${
                res.is_correct ? "text-emerald-400" : "text-rose-400"
              }`,
            },
            header,
          ),
          isReview
            ? h(
                "span",
                {
                  class:
                    "whitespace-nowrap px-2 py-0.5 rounded-full bg-brand-900/30 text-brand-400 text-[11px] font-medium",
                },
                "🔄 Повторение",
              )
            : null,
        ]),
        h("div", { class: "py-3 flex flex-col gap-2" }, [
          h("div", {}, [
            h("div", {}, [wordWithAudio(word, { size: "md", allowBlur: false })]),
            word.transcription_ipa ? transcriptionLabel(word.transcription_ipa, { type: "ipa", extraClass: "text-xs text-slate-400", allowBlur: false }) : null,
            word.transcription_ru ? transcriptionLabel(word.transcription_ru, { type: "ru", extraClass: "text-xs text-slate-400 italic", allowBlur: false }) : null,
            h("div", { class: "text-lg text-brand-400 font-medium mt-1" }, word.russian),
          ]),
          !res.is_correct
            ? h(
                "div",
                { class: "text-xs text-slate-400" },
                `Вы выбрали: ${selected}`,
              )
            : null,
          word.description
            ? h(
                "p",
                { class: "text-sm text-slate-400 leading-relaxed" },
                word.description,
              )
            : null,
        ]),
        isReview
          ? h(
              "div",
              { class: "text-[11px] text-slate-400 italic" },
              "Слово уже изучено — повторение, счётчик не увеличивается",
            )
          : h("div", { class: "text-xs text-slate-400" }, [
              h("span", { class: "text-emerald-600 font-medium" }, `✓ ${p.correct_count || 0}`),
              " · ",
              h("span", { class: "text-rose-600 font-medium" }, `✗ ${p.incorrect_count || 0}`),
              " · ",
              h("span", {}, `прогресс ${Math.min(5, p.correct_count || 0)}/5`),
            ]),
      ],
    );

    const nextBtn = h(
      "button",
      {
        class: "btn-primary w-full py-3 text-sm sm:text-base",
        onclick: loadQuestion,
      },
      "Следующее →",
    );

    host.append(detail, nextBtn);
  }

  renderHeader();
  loadQuestion();
}

function openCategorySheet(state, onPick, rerenderHeader) {
  // При режиме повторения (only_unlearned=false) изначально показываем все,
  // включая полностью изученные категории — чтобы можно было повторять.
  let showAll = !state.only_unlearned;

  const container = h("div", { class: "space-y-3" });
  const grid = h("div", { class: "grid grid-cols-2 gap-2" });

  // Доступна ли категория для выбора: если only_unlearned — нужен хотя бы один «изучаемый» пул,
  // иначе (режим повторения) достаточно изученных слов.
  const isPickable = (c) => {
    const ready = c.quiz_ready_count || 0;
    const learned = c.learned_count || 0;
    return state.only_unlearned ? ready > 0 : ready > 0 || learned > 0;
  };

  const rebuild = () => {
    grid.innerHTML = "";
    const filtered = showAll
      ? state.categories
      : state.categories.filter(isPickable);
    const items = sortCategoriesWithPinned(filtered);
    if (!items.length) {
      grid.append(
        h(
          "div",
          { class: "col-span-2 text-sm text-slate-400 text-center py-6" },
          "Нет категорий с доступными словами. Откройте карточки в «Изучать», чтобы пополнить банк.",
        ),
      );
      return;
    }
    for (const c of items) {
      const active = state.category_id === c.id;
      const ready = c.quiz_ready_count || 0;
      const learned = c.learned_count || 0;
      const pickable = isPickable(c);
      const subtitle = state.only_unlearned
        ? `Изучаем: ${ready} · Изучено: ${learned}/${c.words_count}`
        : ready > 0
          ? `Изучаем: ${ready} · Повторять: ${learned}`
          : `Повторять: ${learned}/${c.words_count}`;
      const card = h(
        "button",
        {
          class: `category-card p-4 rounded-2xl border text-left transition ${
            active
              ? "bg-brand-600 text-white border-brand-500"
              : "bg-slate-800/50 border-slate-700/50 hover:border-brand-500"
          } ${pickable ? "" : "opacity-60"} ${c.is_pinned ? "is-pinned-card" : ""}`,
          onclick: () => {
            if (!pickable) {
              toast("В этой категории нет доступных слов для квиза", "info");
              return;
            }
            state.category_id = c.id;
            state.scope = "category";
            saveSettings(state);
            close();
            rerenderHeader();
            onPick();
          },
        },
        [
          h("div", { class: "text-xl mb-1" }, c.icon || "📁"),
          h("div", { class: "font-medium text-sm pr-6" }, c.name_ru),
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
  rebuild();

  container.append(grid);

  const showAllCheckbox = h("input", {
    type: "checkbox",
    class: "accent-brand-500 w-4 h-4",
    checked: showAll ? "checked" : undefined,
    onchange: (e) => {
      showAll = e.target.checked;
      rebuild();
    },
  });

  const footer = h("div", { class: "flex items-center gap-3" }, [
    h(
      "label",
      {
        class:
          "flex items-center gap-2 text-sm text-slate-400 cursor-pointer select-none flex-1",
      },
      [showAllCheckbox, h("span", {}, "Показывать все категории")],
    ),
    h(
      "button",
      {
        class: "btn-primary px-4",
        onclick: () => close(),
      },
      "Готово",
    ),
  ]);

  const { close } = sheet(container, { title: "Выберите категорию", footer });
}
