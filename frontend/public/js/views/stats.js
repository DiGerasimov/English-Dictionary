import { api } from "../api.js";
import { h, progressBar, skeletonCard, toast } from "../ui.js";

const SORT_KEY = "english.statsSort";

const SORT_OPTIONS = [
  { id: "learned", label: "По изученным" },
  { id: "seen", label: "По просмотренным" },
  { id: "accuracy", label: "По точности" },
  { id: "name", label: "По названию" },
];

function loadSort() {
  try {
    return { sort: "learned", order: "desc", ...(JSON.parse(localStorage.getItem(SORT_KEY)) || {}) };
  } catch {
    return { sort: "learned", order: "desc" };
  }
}
function saveSort(s) {
  localStorage.setItem(SORT_KEY, JSON.stringify(s));
}

export async function renderStats(root) {
  root.innerHTML = "";
  const header = h("header", { class: "px-5 pt-5 pb-2" }, [
    h("h1", { class: "text-2xl font-bold" }, "Статистика"),
  ]);
  const kpiHost = h("section", { class: "px-5 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2" });
  const chartsHost = h("section", { class: "px-5 mt-4 space-y-4" });
  const byCatHost = h("section", { class: "px-5 mt-4 space-y-2" });
  root.append(header, kpiHost, chartsHost, byCatHost);

  for (let i = 0; i < 4; i++) {
    kpiHost.append(
      h(
        "div",
        {
          class: "glass-panel rounded-2xl p-4",
        },
        [skeletonCard()],
      ),
    );
  }

  let overview, timeline, byCategory;
  try {
    [overview, timeline, byCategory] = await Promise.all([
      api.overview(),
      api.timeline(30),
      api.byCategory(),
    ]);
  } catch (e) {
    toast(e.message, "error");
    return;
  }

  kpiHost.innerHTML = "";
  kpiHost.append(
    kpiCard("Сегодня выучено", overview.learned_today, "🎯", "emerald"),
    kpiCard("Вчера выучено", overview.learned_yesterday, "📅", "slate"),
    kpiCard("Всего изучено", overview.learned_total, "📚", "brand"),
    kpiCard("Серия дней", overview.streak_days, "🔥", "orange"),
    kpiCard("Правильно (попыток)", overview.correct_today, "✓", "emerald"),
    kpiCard("Правильно (слов)", overview.correct_today_words ?? 0, "🎯", "emerald"),
    kpiCard("Ошибок (попыток)", overview.incorrect_today, "✗", "rose"),
    kpiCard("Ошибок (слов)", overview.incorrect_today_words ?? 0, "🎯", "rose"),
    kpiCard("Всего в банке", overview.seen_total, "👁", "slate"),
    kpiCard("Точность", `${Math.round((overview.accuracy_total || 0) * 100)}%`, "📈", "brand"),
  );

  chartsHost.append(buildTimelineCard(timeline));
  chartsHost.append(buildCategoryDoughnut(byCategory));

  renderCategoryList(byCatHost, byCategory);
}

function renderCategoryList(host, byCategory) {
  host.innerHTML = "";
  host.append(
    h("div", { class: "flex items-center justify-between" }, [
      h("h2", { class: "text-lg font-semibold" }, "По категориям"),
      h(
        "div",
        { class: "text-xs text-slate-400" },
        byCategory.items.length ? `${byCategory.items.length} шт.` : "",
      ),
    ]),
  );

  if (!byCategory.items.length) {
    host.append(h("div", { class: "text-sm text-slate-400" }, "Нет данных"));
    return;
  }

  const listHost = h("div", { class: "space-y-2" });
  const sortPanel = h("div", {
    class:
      "mt-4 glass-panel rounded-2xl p-3 flex flex-wrap items-center gap-2",
  });

  host.append(listHost, sortPanel);

  const state = loadSort();

  const renderSortPanel = () => {
    sortPanel.innerHTML = "";
    sortPanel.append(
      h("span", { class: "text-xs text-slate-400 mr-1" }, "Сортировка"),
      ...SORT_OPTIONS.map((s) =>
        h(
          "button",
          {
            class: `chip ${state.sort === s.id ? "is-active" : ""}`,
            onclick: () => {
              state.sort = s.id;
              saveSort(state);
              renderSortPanel();
              renderList();
            },
          },
          s.label,
        ),
      ),
      h(
        "button",
        {
          class: "btn-outline text-xs px-2 py-1 ml-auto",
          onclick: () => {
            state.order = state.order === "desc" ? "asc" : "desc";
            saveSort(state);
            renderSortPanel();
            renderList();
          },
        },
        state.order === "desc" ? "↓ Убыв." : "↑ Возр.",
      ),
    );
  };

  const renderList = () => {
    listHost.innerHTML = "";
    const sorted = [...byCategory.items].sort(compareItems(state));
    for (const it of sorted) listHost.append(buildCategoryRow(it));
  };

  renderSortPanel();
  renderList();
}

function compareItems(state) {
  const dir = state.order === "asc" ? 1 : -1;
  return (a, b) => {
    let av, bv;
    switch (state.sort) {
      case "seen":
        av = a.seen_count;
        bv = b.seen_count;
        break;
      case "accuracy":
        av = a.accuracy || 0;
        bv = b.accuracy || 0;
        break;
      case "name":
        return dir * a.name_ru.localeCompare(b.name_ru, "ru");
      case "learned":
      default:
        av = a.learned_count;
        bv = b.learned_count;
        break;
    }
    if (av === bv) return a.name_ru.localeCompare(b.name_ru, "ru");
    return dir * (av - bv);
  };
}

function kpiCard(label, value, icon, tone = "slate") {
  const toneClass =
    {
      emerald: "text-emerald-400",
      rose: "text-rose-400",
      brand: "text-brand-400",
      orange: "text-orange-400",
      slate: "text-slate-300",
    }[tone] || "text-slate-300";
  return h(
    "div",
    { class: "glass-panel rounded-2xl p-4" },
    [
      h("div", { class: "flex items-center justify-between" }, [
        h("div", { class: "text-xs text-slate-400" }, label),
        h("div", { class: "text-base" }, icon),
      ]),
      h("div", { class: `text-2xl font-bold mt-2 ${toneClass}` }, String(value)),
    ],
  );
}

function buildTimelineCard(timeline) {
  const wrap = h("div", { class: "glass-panel rounded-2xl p-4" });
  wrap.append(
    h("div", { class: "flex items-center justify-between mb-3" }, [
      h("div", { class: "text-sm font-semibold" }, "Активность за 30 дней"),
      h("div", { class: "text-xs text-slate-400" }, "изучено · верно · ошибки"),
    ]),
  );
  const canvasWrap = h("div", { class: "relative h-60" });
  const canvas = h("canvas", {});
  canvasWrap.append(canvas);
  wrap.append(canvasWrap);

  const labels = timeline.points.map((p) => p.date.slice(5));
  const learned = timeline.points.map((p) => p.learned);
  const correct = timeline.points.map((p) => p.correct);
  const incorrect = timeline.points.map((p) => p.incorrect);

  requestAnimationFrame(() => {
    new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Изучено",
            data: learned,
            borderColor: "#3a5dff",
            backgroundColor: "rgba(58,93,255,0.15)",
            fill: true,
            tension: 0.35,
          },
          {
            label: "Верно",
            data: correct,
            borderColor: "#22c55e",
            backgroundColor: "rgba(34,197,94,0.1)",
            fill: false,
            tension: 0.35,
          },
          {
            label: "Ошибок",
            data: incorrect,
            borderColor: "#ef4444",
            backgroundColor: "rgba(239,68,68,0.1)",
            fill: false,
            tension: 0.35,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        plugins: { legend: { labels: { boxWidth: 12 } } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } },
          x: { ticks: { maxTicksLimit: 8, autoSkip: true } },
        },
      },
    });
  });

  return wrap;
}

function buildCategoryDoughnut(byCategory) {
  const wrap = h("div", { class: "glass-panel rounded-2xl p-4" });
  wrap.append(h("div", { class: "text-sm font-semibold mb-3" }, "Изученные слова по категориям"));
  const items = byCategory.items.filter((c) => c.learned_count > 0);
  if (!items.length) {
    wrap.append(
      h("div", { class: "text-sm text-slate-400 py-4" }, "Пока нет изученных слов."),
    );
    return wrap;
  }
  const canvasWrap = h("div", { class: "relative h-64" });
  const canvas = h("canvas", {});
  canvasWrap.append(canvas);
  wrap.append(canvasWrap);

  requestAnimationFrame(() => {
    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: items.map((c) => `${c.icon} ${c.name_ru}`),
        datasets: [
          {
            data: items.map((c) => c.learned_count),
            backgroundColor: [
              "#3a5dff",
              "#22c55e",
              "#f59e0b",
              "#ef4444",
              "#8b5cf6",
              "#ec4899",
              "#06b6d4",
              "#14b8a6",
              "#f97316",
              "#84cc16",
              "#a855f7",
              "#eab308",
            ],
            borderWidth: 0,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 12, padding: 8 } },
        },
      },
    });
  });
  return wrap;
}

function buildCategoryRow(it) {
  const acc = Math.round((it.accuracy || 0) * 100);
  return h(
    "div",
    { class: "glass-panel rounded-2xl p-3" },
    [
      h("div", { class: "flex items-center justify-between gap-3" }, [
        h("div", { class: "flex items-center gap-2 min-w-0" }, [
          h("span", { class: "text-lg" }, it.icon || "📁"),
          h("div", { class: "min-w-0" }, [
            h("div", { class: "font-medium text-sm truncate" }, it.name_ru),
            h(
              "div",
              { class: "text-[11px] text-slate-400" },
              `В банке: ${it.seen_count} · Изучено: ${it.learned_count} · Всего: ${it.words_count}`,
            ),
          ]),
        ]),
        h(
          "div",
          { class: "text-xs text-slate-400 whitespace-nowrap" },
          `точность ${acc}%`,
        ),
      ]),
      h(
        "div",
        { class: "mt-2" },
        progressBar(it.learned_count, Math.max(1, it.words_count)),
      ),
    ],
  );
}
