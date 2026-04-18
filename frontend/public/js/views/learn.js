import { api } from "../api.js";
import {
  categoryPickerSheet,
  difficultyLabel,
  formTypeLabel,
  h,
  modal,
  partOfSpeechLabel,
  progressBar,
  sheet,
  skeletonCard,
  statusBadge,
  toast,
  wordWithAudio,
  transcriptionLabel,
  sortCategoriesWithPinned,
  pinButton,
} from "../ui.js";

const FILTER_KEY = "english.learnFilters";
const TAB_KEY = "english.learnTab";

const DIFFICULTIES = [
  { id: "easy", label: "Лёгкая" },
  { id: "medium", label: "Средняя" },
  { id: "hard", label: "Сложная" },
];
const PARTS = [
  { id: "noun", label: "Сущ." },
  { id: "verb", label: "Глагол" },
  { id: "adjective", label: "Прил." },
  { id: "adverb", label: "Нареч." },
  { id: "pronoun", label: "Местоим." },
  { id: "preposition", label: "Предлог" },
  { id: "conjunction", label: "Союз" },
  { id: "phrase", label: "Фраза" },
];
const DICT_STATUSES = [
  { id: "learning", label: "Изучаем" },
  { id: "learned", label: "Изучено" },
];
const DICT_SORTS = [
  { id: "recent", label: "По активности" },
  { id: "alpha", label: "По алфавиту" },
  { id: "progress", label: "По прогрессу" },
];

function defaultFilters() {
  return {
    cards: { category_id: null, difficulty: [], part_of_speech: [] },
    dict: {
      categories: [],
      difficulty: [],
      part_of_speech: [],
      status: "",
      sort: "recent",
      order: "desc",
    },
  };
}

function loadFilters() {
  try {
    const raw = JSON.parse(localStorage.getItem(FILTER_KEY)) || {};
    const def = defaultFilters();
    return {
      cards: { ...def.cards, ...(raw.cards || {}) },
      dict: { ...def.dict, ...(raw.dict || {}) },
    };
  } catch {
    return defaultFilters();
  }
}
function saveFilters(f) {
  localStorage.setItem(FILTER_KEY, JSON.stringify(f));
}

function currentTab() {
  const parts = (location.hash || "").split("/");
  if (parts[2] === "dictionary") return "dictionary";
  if (parts[2] === "cards") return "cards";
  return localStorage.getItem(TAB_KEY) || "cards";
}

export async function renderLearn(root) {
  root.innerHTML = "";

  const state = {
    filters: loadFilters(),
    categories: [],
    tab: currentTab(),
  };

  const header = h("header", { class: "px-4 pt-4 pb-2 space-y-2 min-w-0" });
  const title = h("div", { class: "flex items-center justify-between gap-2" }, [
    h("h1", { class: "text-xl font-bold" }, "Изучение"),
    h(
      "button",
      {
        class: "btn-outline text-xs py-1.5 px-2.5",
        onclick: () => openFiltersSheet(state, onFiltersChange),
      },
      "⚙ Фильтры",
    ),
  ]);

  const segmented = h("div", { class: "segmented w-full sm:w-auto" }, [
    h(
      "button",
      {
        class: `flex-1 sm:flex-none ${state.tab === "cards" ? "is-active" : ""}`,
        onclick: () => switchTab("cards"),
      },
      "Карточки",
    ),
    h(
      "button",
      {
        class: `flex-1 sm:flex-none ${state.tab === "dictionary" ? "is-active" : ""}`,
        onclick: () => switchTab("dictionary"),
      },
      "Словарь",
    ),
  ]);

  const activeFiltersRow = h("div", { class: "flex flex-wrap gap-1.5" });

  header.append(title, segmented, activeFiltersRow);

  const contentWrap = h("section", { class: "px-4 pt-1 min-w-0 tab-wrap" });
  const content = h("div", { class: "tab-content min-w-0" });
  contentWrap.append(content);
  root.append(header, contentWrap);

  try {
    state.categories = await api.categories();
  } catch (e) {
    toast(e.message, "error");
  }

  // Новый пользователь: если в карточках ещё нет выбранной категории — выставляем первую
  if (state.filters.cards.category_id === null && state.categories.length) {
    state.filters.cards.category_id = state.categories[0].id;
    saveFilters(state.filters);
  }

  const renderSegmented = () => {
    const [cardsBtn, dictBtn] = segmented.children;
    cardsBtn.classList.toggle("is-active", state.tab === "cards");
    dictBtn.classList.toggle("is-active", state.tab === "dictionary");
  };

  const renderActiveFilters = () => {
    renderActiveFiltersRow(activeFiltersRow, state, onFiltersChange);
  };

  const switchTab = (tab) => {
    if (state.tab === tab) return;
    const direction = tab === "dictionary" ? "left" : "right";
    state.tab = tab;
    localStorage.setItem(TAB_KEY, tab);
    renderSegmented();
    renderActiveFilters();
    
    content.classList.remove("slide-in-left", "slide-in-right");
    content.classList.add(direction === "left" ? "slide-out-left" : "slide-out-right");
    
    setTimeout(() => {
      content.classList.remove("slide-out-left", "slide-out-right");
      renderCurrent();
      content.classList.add(direction === "left" ? "slide-in-right" : "slide-in-left");
    }, 180);
  };

  const onFiltersChange = () => {
    saveFilters(state.filters);
    renderActiveFilters();
    renderCurrent();
  };

  const renderCurrent = () => {
    content.innerHTML = "";
    if (state.tab === "cards") renderCards(content, state);
    else renderDictionary(content, state);
  };

  renderActiveFilters();
  renderCurrent();

  // Поддержка свайпа для переключения между вкладками на мобильных
  let touchStartX = 0;
  let touchStartY = 0;
  contentWrap.addEventListener("touchstart", (e) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });
  contentWrap.addEventListener("touchend", (e) => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < 60 || Math.abs(dy) > Math.abs(dx)) return;
    if (dx < 0 && state.tab === "cards") switchTab("dictionary");
    else if (dx > 0 && state.tab === "dictionary") switchTab("cards");
  }, { passive: true });
}

function renderActiveFiltersRow(row, state, onChange) {
  row.innerHTML = "";
  const catsById = new Map(state.categories.map((c) => [c.id, c]));

  const removeChip = (label, onRemove) =>
    h(
      "button",
      {
        class: "chip chip-clear",
        onclick: () => {
          onRemove();
          onChange();
        },
      },
      [label, h("span", { class: "ml-1 opacity-70" }, "✕")],
    );

  if (state.tab === "cards") {
    const f = state.filters.cards;
    const currentCat = catsById.get(f.category_id);
    const catLabel =
      f.category_id === "all" || !f.category_id ? "🌐 Все категории" : `${currentCat?.icon || "📁"} ${currentCat?.name_ru || "Категория"}`;
    row.append(
      h(
        "button",
        {
          class: "chip is-active",
          onclick: () => openCategoryPickerForCards(state, onChange),
        },
        [catLabel, h("span", { class: "ml-1 opacity-80" }, "›")],
      ),
    );
    f.difficulty.forEach((d) => {
      const label = DIFFICULTIES.find((x) => x.id === d)?.label || d;
      row.append(
        removeChip(`Сложность: ${label}`, () => {
          f.difficulty = f.difficulty.filter((x) => x !== d);
        }),
      );
    });
    f.part_of_speech.forEach((p) => {
      const label = PARTS.find((x) => x.id === p)?.label || p;
      row.append(
        removeChip(label, () => {
          f.part_of_speech = f.part_of_speech.filter((x) => x !== p);
        }),
      );
    });
    const hasAny = f.difficulty.length || f.part_of_speech.length;
    if (hasAny) {
      row.append(
        h(
          "button",
          {
            class: "chip chip-clear",
            onclick: () => {
              f.difficulty = [];
              f.part_of_speech = [];
              onChange();
            },
          },
          "Сбросить все",
        ),
      );
    }
    return;
  }

  const f = state.filters.dict;
  f.categories.forEach((id) => {
    const c = catsById.get(id);
    if (!c) return;
    row.append(
      removeChip(`${c.icon} ${c.name_ru}`, () => {
        f.categories = f.categories.filter((x) => x !== id);
      }),
    );
  });
  f.difficulty.forEach((d) => {
    const label = DIFFICULTIES.find((x) => x.id === d)?.label || d;
    row.append(
      removeChip(`Сложность: ${label}`, () => {
        f.difficulty = f.difficulty.filter((x) => x !== d);
      }),
    );
  });
  f.part_of_speech.forEach((p) => {
    const label = PARTS.find((x) => x.id === p)?.label || p;
    row.append(
      removeChip(label, () => {
        f.part_of_speech = f.part_of_speech.filter((x) => x !== p);
      }),
    );
  });
  if (f.status) {
    const label = DICT_STATUSES.find((x) => x.id === f.status)?.label || f.status;
    row.append(
      removeChip(`Статус: ${label}`, () => {
        f.status = "";
      }),
    );
  }
  const hasAny =
    f.categories.length || f.difficulty.length || f.part_of_speech.length || f.status;
  if (hasAny) {
    row.append(
      h(
        "button",
        {
          class: "chip chip-clear",
          onclick: () => {
            f.categories = [];
            f.difficulty = [];
            f.part_of_speech = [];
            f.status = "";
            onChange();
          },
        },
        "Сбросить все",
      ),
    );
  }
}

function openFiltersSheet(state, onChange) {
  const container = h("div", { class: "space-y-5" });
  let closeRef = null;

  const isCards = state.tab === "cards";
  const f = isCards ? state.filters.cards : state.filters.dict;

  const makeMultiGroup = (label, key, items) => {
    const chips = h("div", { class: "flex flex-wrap gap-2" });
    const rebuild = () => {
      chips.innerHTML = "";
      items.forEach((it) => {
        const active = (f[key] || []).includes(it.id);
        chips.append(
          h(
            "button",
            {
              class: `chip ${active ? "is-active" : ""}`,
              onclick: () => {
                const arr = f[key] || [];
                f[key] = active ? arr.filter((x) => x !== it.id) : [...arr, it.id];
                rebuild();
              },
            },
            it.label,
          ),
        );
      });
    };
    rebuild();
    return h("div", { class: "space-y-2" }, [
      h("div", { class: "text-sm font-medium text-slate-400" }, label),
      chips,
    ]);
  };

  const sections = [];

  if (!isCards) {
    const categoriesLabel = h("div", { class: "text-xs text-slate-400" });
    const updateCatLabel = () => {
      const n = f.categories.length;
      categoriesLabel.textContent = n ? `Выбрано: ${n}` : "Любые категории";
    };
    updateCatLabel();

    const categoriesBtn = h(
      "button",
      {
        class:
          "w-full flex items-center justify-between p-3 rounded-xl border border-white/10 bg-slate-800/50 hover:border-brand-500",
        onclick: () => {
          categoryPickerSheet(state.categories, {
            selectedIds: f.categories,
            multi: true,
            onConfirm: (ids) => {
              f.categories = ids;
              updateCatLabel();
            },
          });
        },
      },
      [
        h("div", { class: "text-left" }, [
          h("div", { class: "text-sm font-medium" }, "Выбрать категории"),
          categoriesLabel,
        ]),
        h("span", { class: "text-slate-400" }, "›"),
      ],
    );

    sections.push(
      h("div", { class: "space-y-2" }, [
        h("div", { class: "text-sm font-medium text-slate-400" }, "Категории"),
        categoriesBtn,
      ]),
    );
  } else {
    const catLabel = h("div", { class: "text-xs text-slate-400" });
    const updateCatLabel = () => {
      const cur = state.categories.find((c) => c.id === f.category_id);
      catLabel.textContent =
        f.category_id === "all" || !f.category_id
          ? "🌐 Все категории"
          : cur
            ? `${cur.icon || "📁"} ${cur.name_ru}`
            : "Не выбрано";
    };
    updateCatLabel();

    const categoryBtn = h(
      "button",
      {
        class:
          "w-full flex items-center justify-between p-3 rounded-xl border border-white/10 bg-slate-800/50 hover:border-brand-500",
        onclick: () => {
          openCategoryPickerForCards(state, () => {
            updateCatLabel();
          });
        },
      },
      [
        h("div", { class: "text-left" }, [
          h("div", { class: "text-sm font-medium" }, "Выбрать категорию"),
          catLabel,
        ]),
        h("span", { class: "text-slate-400" }, "›"),
      ],
    );

    sections.push(
      h("div", { class: "space-y-2" }, [
        h("div", { class: "text-sm font-medium text-slate-400" }, "Категория"),
        categoryBtn,
      ]),
    );
  }

  sections.push(makeMultiGroup("Сложность", "difficulty", DIFFICULTIES));
  sections.push(makeMultiGroup("Часть речи", "part_of_speech", PARTS));

  if (!isCards) {
    const chips = h("div", { class: "flex flex-wrap gap-2" });
    const rebuild = () => {
      chips.innerHTML = "";
      DICT_STATUSES.forEach((it) => {
        const active = f.status === it.id;
        chips.append(
          h(
            "button",
            {
              class: `chip ${active ? "is-active" : ""}`,
              onclick: () => {
                f.status = active ? "" : it.id;
                rebuild();
              },
            },
            it.label,
          ),
        );
      });
    };
    rebuild();
    sections.push(
      h("div", { class: "space-y-2" }, [
        h("div", { class: "text-sm font-medium text-slate-400" }, "Статус"),
        chips,
      ]),
    );
  }

  sections.forEach((s) => container.append(s));

  const footer = h("div", { class: "flex gap-2" }, [
    h(
      "button",
      {
        class: "btn-ghost flex-1",
        onclick: () => {
          if (isCards) {
            state.filters.cards.difficulty = [];
            state.filters.cards.part_of_speech = [];
          } else {
            Object.assign(state.filters.dict, {
              categories: [],
              difficulty: [],
              part_of_speech: [],
              status: "",
            });
          }
          closeRef && closeRef();
          onChange();
        },
      },
      "🧹 Сбросить",
    ),
    h(
      "button",
      {
        class: "btn-primary flex-1",
        onclick: () => {
          closeRef && closeRef();
          onChange();
        },
      },
      "Применить",
    ),
  ]);

  const { close } = sheet(container, { title: "Фильтры", footer });
  closeRef = close;
}

function openCategoryPickerForCards(state, onChange) {
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

    const allActive = state.filters.cards.category_id === "all";
    grid.append(
      h(
        "button",
        {
          class: `p-3 rounded-2xl border text-left transition ${
            allActive
              ? "bg-brand-600 text-white border-brand-500"
              : "bg-slate-800/50 border-slate-700/50 hover:border-brand-500"
          }`,
          onclick: () => {
            state.filters.cards.category_id = "all";
            saveFilters(state.filters);
            close();
            onChange();
          },
        },
        [
          h("div", { class: "text-xl mb-1" }, "🌐"),
          h("div", { class: "font-medium text-sm leading-tight" }, "Все категории"),
          h(
            "div",
            {
              class: `text-[11px] mt-0.5 ${allActive ? "text-white/80" : "text-slate-400"}`,
            },
            "Слова из всех категорий",
          ),
        ],
      ),
    );

    const filtered = state.categories.filter(
      (c) => !q || c.name_ru.toLowerCase().includes(q) || (c.name_en || "").toLowerCase().includes(q),
    );
    const visible = sortCategoriesWithPinned(filtered);
    for (const c of visible) {
      const active = state.filters.cards.category_id === c.id;
      const card = h(
        "button",
        {
          class: `category-card p-3 rounded-2xl border text-left transition ${
            active
              ? "bg-brand-600 text-white border-brand-500"
              : "bg-slate-800/50 border-slate-700/50 hover:border-brand-500"
          } ${c.is_pinned ? "is-pinned-card" : ""}`,
          onclick: () => {
            state.filters.cards.category_id = c.id;
            saveFilters(state.filters);
            close();
            onChange();
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
            `${c.learned_count}/${c.words_count} изучено`,
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

  const { close } = sheet(container, { title: "Выберите категорию" });
}

/* ------------------------- Карточки ------------------------- */

async function renderCards(host, state) {
  const cardState = {
    items: [],
    index: 0,
    loading: true,
  };

  const statusLine = h("div", { class: "text-[11px] text-slate-400 mb-1.5" });
  const cardHost = h("div", {});
  const footer = h("div", { class: "mt-2 flex items-center gap-2" });
  host.append(statusLine, cardHost, footer);

  const load = async () => {
    cardState.loading = true;
    renderLoadingCard();
    try {
      const data = await api.activeWords(cardsQuery(state));
      cardState.items = data.items || [];
      cardState.index = 0;
    } catch (e) {
      toast(e.message, "error");
      cardState.items = [];
    } finally {
      cardState.loading = false;
      renderView();
    }
  };

  const renderLoadingCard = () => {
    statusLine.textContent = "";
    cardHost.innerHTML = "";
    cardHost.append(
      h("div", { class: "glass-panel rounded-3xl p-6" }, [
        skeletonCard(),
      ]),
    );
  };

  const renderView = () => {
    cardHost.innerHTML = "";
    footer.innerHTML = "";

    if (cardState.loading) {
      renderLoadingCard();
      return;
    }
    if (!cardState.items.length) {
      statusLine.textContent = "";
      cardHost.append(
        h(
          "div",
          {
            class:
              "glass-panel rounded-3xl p-8 text-center text-slate-400 space-y-2",
          },
          [
            h("div", { class: "text-4xl" }, "✨"),
            h("div", { class: "font-medium text-slate-300" }, "Нет слов в этой выборке"),
            h(
              "div",
              { class: "text-sm" },
              "Попробуйте изменить фильтры или выбрать другую категорию.",
            ),
            h("a", { class: "btn-primary inline-block mt-3", href: "#/quiz" }, "К квизу"),
          ],
        ),
      );
      return;
    }
    const word = cardState.items[cardState.index];
    statusLine.textContent = `${cardState.index + 1} / ${cardState.items.length}`;

    const card = buildWordCard(word, {
      onPrev: () => nav(-1),
      onNext: () => nav(1),
    });
    cardHost.append(card);
    attachSwipe(card, (dir) => nav(dir === "left" ? 1 : -1));

    // Фоново отмечаем факт показа — для равномерного распределения повторений
    api.markWordViewed(word.id).catch(() => {});

    footer.append(
      h(
        "button",
        {
          class: "btn-outline text-xs py-1.5 px-2.5",
          onclick: load,
        },
        "🔀 Перемешать",
      ),
      h(
        "div",
        { class: "text-[11px] text-slate-400 ml-auto text-right leading-tight" },
        "Новые слова открываются постепенно",
      ),
    );
  };

  const nav = (delta) => {
    if (!cardState.items.length) return;
    const n = cardState.items.length;
    cardState.index = (cardState.index + delta + n) % n;
    renderView();
  };

  await load();
}

function buildWordCard(word, { onPrev, onNext }) {
  const p = word.progress || {};
  const correct = p.correct_count || 0;
  const incorrect = p.incorrect_count || 0;
  const isReview = !!p.is_learned;

  const navBtn = (label, handler) =>
    h(
      "button",
      {
        class: "btn-ghost flex-1 text-lg py-2",
        onclick: handler,
      },
      label,
    );

  const formsEl = (word.forms || []).length
    ? h("div", { class: "mt-2 pt-3 border-t border-white/10 space-y-1.5" }, [
        h("div", { class: "text-[11px] uppercase text-slate-400 font-medium" }, "Формы"),
        ...word.forms.map((f) => {
          const fp = f.progress || {};
          return h(
            "div",
            { class: "flex items-center justify-between gap-3 py-1" },
            [
              h("div", { class: "min-w-0" }, [
                h("div", { class: "text-xs text-slate-400" }, formTypeLabel(f.form_type)),
                h("div", { class: "font-medium truncate" }, f.english),
                f.transcription_ipa ? transcriptionLabel(f.transcription_ipa, { type: "ipa", extraClass: "text-xs text-slate-400", allowBlur: false }) : null,
                f.russian ? h("div", { class: "text-sm text-slate-400 truncate" }, f.russian) : null,
              ]),
              h("div", { class: "text-xs text-slate-400 whitespace-nowrap" }, [
                h("span", { class: "text-emerald-600 font-medium" }, `✓ ${fp.correct_count || 0}`),
                " · ",
                h("span", { class: "text-rose-600 font-medium" }, `✗ ${fp.incorrect_count || 0}`),
              ]),
            ],
          );
        }),
      ])
    : null;

  return h(
    "article",
    {
      class:
        "swipe-card animate-slide-up-fade glass-panel rounded-2xl p-4 sm:p-5 flex flex-col gap-2.5",
    },
    [
      h("div", { class: "flex items-center justify-between gap-2" }, [
        h("div", { class: "flex items-center gap-1.5 text-[11px] text-slate-400 min-w-0 flex-1 whitespace-nowrap overflow-hidden" }, [
          h("span", { class: "shrink-0" }, word.category.icon || "📁"),
          h("span", { class: "truncate min-w-0" }, word.category.name_ru),
          h("span", { class: "text-slate-300 shrink-0" }, "·"),
          h("span", { class: "shrink-0" }, partOfSpeechLabel(word.part_of_speech)),
          h("span", { class: "text-slate-300 shrink-0" }, "·"),
          h("span", { class: "shrink-0" }, difficultyLabel(word.difficulty)),
        ]),
        isReview
          ? h(
              "span",
              {
                class:
                  "whitespace-nowrap px-2 py-0.5 rounded-full bg-brand-900/30 text-brand-400 text-[11px] font-medium",
              },
              "🔄 Повторение",
            )
          : statusBadge(p),
      ]),
      h("div", { class: "space-y-0.5" }, [
        h("h2", { class: "leading-tight" }, [wordWithAudio(word, { size: "lg", allowBlur: false })]),
        word.transcription_ipa ? transcriptionLabel(word.transcription_ipa, { type: "ipa", allowBlur: false }) : null,
        word.transcription_ru ? transcriptionLabel(word.transcription_ru, { type: "ru", allowBlur: false }) : null,
      ]),
      h("div", { class: "text-lg sm:text-xl font-medium text-brand-400 leading-tight" }, word.russian),
      word.description
        ? h("p", { class: "text-sm text-slate-400 leading-snug" }, word.description)
        : null,
      isReview
        ? h(
            "div",
            { class: "text-[11px] text-slate-400 italic pt-1" },
            `Слово изучено · показов: ${p.view_count || 0}`,
          )
        : h("div", { class: "pt-1" }, [
            h("div", { class: "flex items-center justify-between text-[11px] text-slate-400 mb-1" }, [
              h("span", {}, `Прогресс: ${correct}/5`),
              h("span", { class: "space-x-2" }, [
                h("span", { class: "text-emerald-600" }, `✓ ${correct}`),
                h("span", { class: "text-rose-600" }, `✗ ${incorrect}`),
              ]),
            ]),
            progressBar(correct, 5),
          ]),
      formsEl,
      h("div", { class: "flex gap-2 pt-1" }, [
        navBtn("←", onPrev),
        navBtn("→", onNext),
      ]),
    ],
  );
}

/* ------------------------- Словарь ------------------------- */

async function renderDictionary(host, state) {
  const dictState = {
    items: [],
    cursor: null,
    loading: false,
    end: false,
  };

  const search = h("input", {
    class: "input",
    type: "search",
    placeholder: "Поиск по английскому/русскому",
  });

  const sortRow = h("div", { class: "flex items-center gap-2 flex-wrap" }, [
    h("span", { class: "text-xs text-slate-400" }, "Сортировка"),
    ...DICT_SORTS.map((s) =>
      h(
        "button",
        {
          class: `chip ${state.filters.dict.sort === s.id ? "is-active" : ""}`,
          onclick: () => {
            state.filters.dict.sort = s.id;
            saveFilters(state.filters);
            refreshSortChips();
            reload();
          },
        },
        s.label,
      ),
    ),
    h(
      "button",
      {
        class: "btn-outline text-xs px-2 py-1",
        onclick: () => {
          state.filters.dict.order = state.filters.dict.order === "desc" ? "asc" : "desc";
          saveFilters(state.filters);
          dirBtn.textContent = state.filters.dict.order === "desc" ? "↓" : "↑";
          reload();
        },
      },
      state.filters.dict.order === "desc" ? "↓" : "↑",
    ),
  ]);
  const dirBtn = sortRow.lastElementChild;

  const refreshSortChips = () => {
    const chips = sortRow.querySelectorAll(".chip");
    chips.forEach((ch, i) => {
      ch.classList.toggle("is-active", DICT_SORTS[i].id === state.filters.dict.sort);
    });
  };

  const list = h("div", { class: "space-y-2 mt-3" });
  const sentinel = h("div", { class: "h-10" });

  host.append(
    h("div", { class: "space-y-3" }, [search, sortRow, list, sentinel]),
  );

  let debounce = null;
  search.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(reload, 250);
  });

  const renderItems = () => {
    list.innerHTML = "";
    if (!dictState.items.length && !dictState.loading) {
      list.append(
        h(
          "div",
          {
            class: "glass-panel rounded-2xl p-6 text-center text-slate-400",
          },
          [
            h("div", { class: "text-3xl mb-2" }, "📖"),
            h("div", { class: "font-medium text-slate-300" }, "В словаре пока пусто"),
            h(
              "div",
              { class: "text-sm mt-1" },
              "Слова появятся здесь автоматически, когда начнёте их изучать.",
            ),
          ],
        ),
      );
      return;
    }
    for (const w of dictState.items) {
      list.append(buildDictRow(w));
    }
    if (dictState.loading) {
      list.append(
        h("div", { class: "dict-row animate-pulse" }, [
          h("div", { class: "skeleton w-6 h-6 rounded-full" }),
          h("div", { class: "skeleton h-4 w-1/2" }),
          h("div", { class: "skeleton h-4 w-12" }),
        ]),
      );
    }
  };

  const load = async () => {
    if (dictState.loading || dictState.end) return;
    dictState.loading = true;
    renderItems();
    try {
      const f = state.filters.dict;
      const query = {
        category_id: f.categories.length ? f.categories : undefined,
        difficulty: f.difficulty.length ? f.difficulty : undefined,
        part_of_speech: f.part_of_speech.length ? f.part_of_speech : undefined,
        status: f.status || undefined,
        q: search.value.trim() || undefined,
        sort: f.sort || "recent",
        order: f.order || "desc",
        cursor: dictState.cursor ?? undefined,
        limit: 30,
      };
      const data = await api.dictionary(query);
      dictState.items.push(...(data.items || []));
      if (data.next_cursor == null) dictState.end = true;
      else dictState.cursor = data.next_cursor;
    } catch (e) {
      toast(e.message, "error");
      dictState.end = true;
    } finally {
      dictState.loading = false;
      renderItems();
    }
  };

  const reload = async () => {
    dictState.items = [];
    dictState.cursor = null;
    dictState.end = false;
    await load();
  };

  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) load();
    },
    { rootMargin: "200px" },
  );
  observer.observe(sentinel);

  await load();
}

function buildDictRow(word) {
  const p = word.progress || {};
  const correct = p.correct_count || 0;
  return h(
    "div",
    {
      class: "dict-row",
      onclick: () => openWordModal(word.id),
    },
    [
      h("div", { class: "text-xl" }, word.category.icon || "📁"),
      h("div", { class: "min-w-0" }, [
        h("div", { class: "flex items-center gap-2" }, [
          h("div", { class: "font-semibold truncate" }, word.english),
          statusBadge(p),
        ]),
        h(
          "div",
          { class: "text-sm text-slate-400 truncate" },
          word.russian,
        ),
      ]),
      h("div", { class: "text-right" }, [
        h("div", { class: "text-xs text-slate-400 whitespace-nowrap" }, `${correct}/5`),
        h("div", { class: "w-16 mt-1" }, [progressBar(correct, 5)]),
      ]),
    ],
  );
}

async function openWordModal(wordId) {
  const body = h("div", {}, [skeletonCard()]);
  const { close } = modal(body, { title: "Слово" });
  try {
    const word = await api.word(wordId);
    body.innerHTML = "";
    body.append(buildWordDetail(word));
  } catch (e) {
    toast(e.message, "error");
    close();
  }
}

function buildWordDetail(word) {
  const p = word.progress || {};
  const correct = p.correct_count || 0;
  const incorrect = p.incorrect_count || 0;

  const formsEl = (word.forms || []).length
    ? h("div", { class: "mt-2 pt-3 border-t border-white/10 space-y-2" }, [
        h("div", { class: "text-xs uppercase text-slate-400 font-medium" }, "Формы"),
        ...word.forms.map((f) => {
          const fp = f.progress || {};
          return h(
            "div",
            { class: "flex items-center justify-between gap-3 py-1" },
            [
              h("div", { class: "min-w-0" }, [
                h("div", { class: "text-xs text-slate-400" }, formTypeLabel(f.form_type)),
                h("div", { class: "font-medium truncate" }, f.english),
                f.transcription_ipa ? transcriptionLabel(f.transcription_ipa, { type: "ipa", extraClass: "text-xs text-slate-400", allowBlur: false }) : null,
                f.russian ? h("div", { class: "text-sm text-slate-400 truncate" }, f.russian) : null,
              ]),
              h("div", { class: "text-xs text-slate-400 whitespace-nowrap" }, [
                h("span", { class: "text-emerald-600 font-medium" }, `✓ ${fp.correct_count || 0}`),
                " · ",
                h("span", { class: "text-rose-600 font-medium" }, `✗ ${fp.incorrect_count || 0}`),
              ]),
            ],
          );
        }),
      ])
    : null;

  return h("div", { class: "space-y-3" }, [
    h("div", { class: "flex items-center justify-between" }, [
      h("div", { class: "flex items-center gap-2 text-xs text-slate-400 min-w-0" }, [
        h("span", {}, word.category.icon || "📁"),
        h("span", { class: "truncate" }, word.category.name_ru),
        h("span", { class: "text-slate-300" }, "·"),
        h("span", {}, partOfSpeechLabel(word.part_of_speech)),
        h("span", { class: "text-slate-300" }, "·"),
        h("span", {}, difficultyLabel(word.difficulty)),
      ]),
      statusBadge(p),
    ]),
    h("div", {}, [
      h("h2", {}, [wordWithAudio(word, { size: "md", allowBlur: false })]),
      word.transcription_ipa ? transcriptionLabel(word.transcription_ipa, { type: "ipa", allowBlur: false }) : null,
      word.transcription_ru ? transcriptionLabel(word.transcription_ru, { type: "ru", allowBlur: false }) : null,
    ]),
    h("div", { class: "text-lg font-medium text-brand-400" }, word.russian),
    word.description
      ? h("p", { class: "text-sm text-slate-400 leading-relaxed" }, word.description)
      : null,
    h("div", {}, [
      h("div", { class: "flex items-center justify-between text-xs text-slate-400 mb-1" }, [
        h("span", {}, `Прогресс: ${correct}/5`),
        h("span", { class: "space-x-2" }, [
          h("span", { class: "text-emerald-600" }, `✓ ${correct}`),
          h("span", { class: "text-rose-600" }, `✗ ${incorrect}`),
        ]),
      ]),
      progressBar(correct, 5),
    ]),
    formsEl,
  ]);
}

/* ------------------------- helpers ------------------------- */

function cardsQuery(state) {
  const f = state.filters.cards;
  const cid = f.category_id;
  return {
    category_id: cid && cid !== "all" ? [cid] : undefined,
    difficulty: f.difficulty.length ? f.difficulty : undefined,
    part_of_speech: f.part_of_speech.length ? f.part_of_speech : undefined,
  };
}

function attachSwipe(el, handler) {
  let startX = null;
  let startY = null;
  el.addEventListener(
    "touchstart",
    (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    },
    { passive: true },
  );
  el.addEventListener(
    "touchend",
    (e) => {
      if (startX === null) return;
      const dx = e.changedTouches[0].clientX - startX;
      const dy = e.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) {
        handler(dx < 0 ? "left" : "right");
      }
      startX = null;
    },
    { passive: true },
  );
}
