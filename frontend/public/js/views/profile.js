import { api, auth, bgMusic } from "../api.js";
import { h, modal, toast } from "../ui.js";

export async function renderProfile(root) {
  root.innerHTML = "";
  let user = auth.getUser() || {};

  try {
    user = await api.me();
    auth.setUser(user);
  } catch {
    /* ignore — покажем то, что есть */
  }

  const activeInput = h("input", {
    type: "number",
    class: "input",
    min: "1",
    max: "50",
    value: String(user.active_slots ?? 5),
  });
  const dailyInput = h("input", {
    type: "number",
    class: "input",
    min: "1",
    max: "100",
    value: String(user.daily_new_limit ?? 10),
  });
  const voiceCheckbox = h("input", {
    type: "checkbox",
    class: "accent-brand-500 w-4 h-4",
    checked: user.voice_mode ? "checked" : undefined,
  });
  const saveBtn = h(
    "button",
    {
      class: "btn-primary w-full",
      onclick: async () => {
        const active = Number(activeInput.value);
        const daily = Number(dailyInput.value);
        if (!Number.isFinite(active) || active < 1 || active > 50) {
          toast("Слотов должно быть от 1 до 50", "error");
          return;
        }
        if (!Number.isFinite(daily) || daily < 1 || daily > 100) {
          toast("Дневной лимит должен быть от 1 до 100", "error");
          return;
        }
        
        const musicToggle = document.getElementById("bg-music-toggle");
        const musicVolume = document.getElementById("bg-music-volume");
        if (musicToggle && musicVolume) {
          bgMusic.update(musicToggle.checked, Number(musicVolume.value) / 100);
        }

        saveBtn.disabled = true;
        try {
          const updated = await api.updateSettings({
            active_slots: active,
            daily_new_limit: daily,
            voice_mode: voiceCheckbox.checked,
          });
          auth.setUser(updated);
          toast("Настройки сохранены", "success");
        } catch (e) {
          toast(e.message, "error");
        } finally {
          saveBtn.disabled = false;
        }
      },
    },
    "Сохранить",
  );

  root.append(
    h("div", { class: "px-5 pt-6 space-y-5" }, [
      h("h1", { class: "text-2xl font-bold" }, "Профиль"),
      h(
        "div",
        { class: "glass-panel rounded-2xl p-5 space-y-2" },
        [
          h("div", { class: "text-xs uppercase text-slate-400" }, "Имя"),
          h("div", { class: "text-base font-medium" }, user.username || "—"),
          h("div", { class: "text-xs uppercase text-slate-400 pt-2" }, "Email"),
          h("div", { class: "text-base font-medium" }, user.email || "—"),
        ],
      ),
      h(
        "div",
        { class: "glass-panel rounded-2xl p-5 space-y-4" },
        [
          h("div", {}, [
            h("div", { class: "text-base font-semibold" }, "Настройки обучения"),
            h(
              "div",
              { class: "text-xs text-slate-400 mt-1" },
              "Новые слова открываются автоматически по мере прогресса, чтобы не перегрузить.",
            ),
          ]),
          h("div", { class: "space-y-1" }, [
            h("label", { class: "text-sm font-medium text-slate-300" }, "Активных слов в категории"),
            activeInput,
            h(
              "div",
              { class: "text-xs text-slate-400" },
              "Сколько непройденных слов держать открытыми одновременно в каждой категории.",
            ),
          ]),
          h("div", { class: "space-y-1" }, [
            h(
              "label",
              { class: "text-sm font-medium text-slate-300" },
              "Новых слов в сутки в категории",
            ),
            dailyInput,
            h(
              "div",
              { class: "text-xs text-slate-400" },
              "Максимум новых слов, которые система откроет за сутки в каждой категории отдельно.",
            ),
          ]),
          h("div", { class: "pt-2 border-t border-white/10 space-y-2" }, [
            h(
              "button",
              {
                class: "btn-outline w-full text-sm",
                onclick: async (e) => {
                  const btn = e.currentTarget;
                  btn.disabled = true;
                  const prevText = btn.textContent;
                  btn.textContent = "Открываем…";
                  try {
                    const pwd = prompt("Введите пароль для подтверждения:");
                    if (!pwd) {
                      btn.disabled = false;
                      btn.textContent = prevText;
                      return;
                    }
                    const res = await api.refillWords(pwd);
                    const n = Number(res?.activated || 0);
                    if (n > 0) {
                      toast(`Открыто новых слов: ${n}`, "success");
                    } else {
                      toast("Нет новых слов для открытия", "info");
                    }
                  } catch (err) {
                    toast(err.message, "error");
                  } finally {
                    btn.disabled = false;
                    btn.textContent = prevText;
                  }
                },
              },
              "Получить новые слова сейчас",
            ),
            h(
              "div",
              { class: "text-xs text-slate-400" },
              "Открывает новые слова во всех категориях, не дожидаясь следующего дня. Лимит «новых слов в сутки» игнорируется.",
            ),
          ]),
          h("div", { class: "pt-2 border-t border-white/10 space-y-1" }, [
            h(
              "label",
              {
                class:
                  "flex items-center gap-2 cursor-pointer select-none text-sm font-medium text-slate-300",
              },
              [
                voiceCheckbox,
                h("span", {}, "Тренировка на слух (блюр слова)"),
              ],
            ),
            h(
              "div",
              { class: "text-xs text-slate-400" },
              "Английское слово скрывается под блюром, нажимайте на динамик, чтобы прослушать. Кликом по слову можно раскрыть.",
            ),
          ]),
          h("div", { class: "pt-2 border-t border-white/10 space-y-3" }, [
            h("div", { class: "flex items-center justify-between" }, [
              h(
                "label",
                {
                  class: "flex items-center gap-2 cursor-pointer select-none text-sm font-medium text-slate-300",
                },
                [
                  h("input", {
                    type: "checkbox",
                    class: "accent-brand-500 w-4 h-4",
                    id: "bg-music-toggle",
                  }),
                  h("span", {}, "Фоновая музыка"),
                ],
              ),
            ]),
            h("div", { class: "flex items-center gap-3" }, [
              h("span", { class: "text-xs text-slate-400" }, "🔈"),
              h("input", {
                type: "range",
                id: "bg-music-volume",
                class: "flex-1 accent-brand-500",
                min: "0",
                max: "100",
              }),
              h("span", { class: "text-xs text-slate-400" }, "🔊"),
            ]),
          ]),
          saveBtn,
        ],
      ),
      user.is_admin ? renderAdminTTSBlock() : null,
      h(
        "div",
        {
          class: "glass-panel rounded-2xl p-5 border-rose-500/30 space-y-3",
        },
        [
          h("div", { class: "text-base font-semibold text-rose-400" }, "Опасная зона"),
          h(
            "div",
            { class: "text-xs text-slate-400" },
            "Полный сброс удалит все изучаемые и изученные слова, счётчики и историю квизов. Откатить нельзя.",
          ),
          h(
            "button",
            {
              class:
                "w-full py-2.5 px-4 rounded-xl border border-rose-500/50 text-rose-400 font-semibold hover:bg-rose-500/10 transition",
              onclick: () => openResetConfirm(),
            },
            "Обнулить прогресс",
          ),
        ],
      ),
      h(
        "button",
        {
          class: "btn-ghost w-full text-rose-600",
          onclick: () => {
            auth.clear();
            location.hash = "#/login";
          },
        },
        "Выйти",
      ),
    ])
  );

  setTimeout(() => {
    const musicToggle = document.getElementById("bg-music-toggle");
    const musicVolume = document.getElementById("bg-music-volume");
    if (musicToggle && musicVolume) {
      musicToggle.checked = bgMusic.state.enabled;
      musicVolume.value = Math.round(bgMusic.state.volume * 100);
      
      musicVolume.addEventListener("input", (e) => {
        bgMusic.update(musicToggle.checked, Number(e.target.value) / 100);
      });
      musicToggle.addEventListener("change", (e) => {
        bgMusic.update(e.target.checked, Number(musicVolume.value) / 100);
      });
    }
  }, 0);
}

function openResetConfirm() {
  const COUNTDOWN = 5;
  let remaining = COUNTDOWN;

  const pwdInput = h("input", {
    type: "password",
    class: "w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-sm",
    placeholder: "Пароль для подтверждения",
    autocomplete: "current-password",
  });

  const confirmBtn = h(
    "button",
    {
      class:
        "flex-1 py-2.5 px-4 rounded-xl bg-rose-500 text-white font-semibold disabled:opacity-60 disabled:cursor-not-allowed",
      disabled: "disabled",
      onclick: async () => {
        const pwd = pwdInput.value.trim();
        if (!pwd) {
          toast("Введите пароль", "error");
          return;
        }
        confirmBtn.disabled = true;
        confirmBtn.textContent = "Сбрасываем…";
        try {
          await api.resetProgress(pwd);
          toast("Прогресс сброшен", "success");
          close();
          location.hash = "#/learn";
          window.dispatchEvent(new HashChangeEvent("hashchange"));
        } catch (e) {
          toast(e.message, "error");
          confirmBtn.disabled = false;
          confirmBtn.textContent = "Да, обнулить";
        }
      },
    },
    `Подтвердите через ${remaining}`,
  );

  const cancelBtn = h(
    "button",
    {
      class: "flex-1 btn-ghost",
      onclick: () => close(),
    },
    "Отмена",
  );

  const body = h("div", { class: "space-y-4" }, [
    h(
      "p",
      { class: "text-sm text-slate-400 leading-relaxed" },
      "Будут удалены все изучаемые и изученные слова, счётчики и история квизов. Это действие необратимо.",
    ),
    pwdInput,
    h("div", { class: "flex gap-2" }, [cancelBtn, confirmBtn]),
  ]);

  const interval = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(interval);
      confirmBtn.disabled = false;
      confirmBtn.textContent = "Да, обнулить";
    } else {
      confirmBtn.textContent = `Подтвердите через ${remaining}`;
    }
  }, 1000);

  const { close: rawClose } = modal(body, { title: "Сбросить весь прогресс?" });
  const close = () => {
    clearInterval(interval);
    rawClose();
  };
}

function renderAdminTTSBlock() {
  const statusLine = h("div", { class: "text-xs text-slate-400" }, "Загрузка…");
  const progressWrap = h("div", { class: "w-full bg-white/10 rounded-full h-2 shadow-inner" });
  const progressBar = h("div", {
    class: "bg-gradient-to-r from-brand-500 to-brand-300 h-2 rounded-full transition-all shadow-[0_0_10px_rgba(167,139,250,0.8)]",
    style: "width: 0%",
  });
  progressWrap.append(progressBar);

  const countsLine = h("div", { class: "text-sm text-slate-300" }, "—");
  const recentLine = h("div", { class: "text-[11px] text-slate-400 break-words" }, "");
  const errorLine = h("div", { class: "text-xs text-rose-600" }, "");
  const currentLine = h("div", { class: "text-xs text-slate-400" }, "");

  const startBtn = h(
    "button",
    {
      class: "btn-primary flex-1",
      onclick: async () => {
        startBtn.disabled = true;
        try {
          await api.ttsBatchStart();
          toast("Генерация запущена", "success");
          await refresh();
          ensurePolling();
        } catch (e) {
          toast(e.message, "error");
        } finally {
          startBtn.disabled = false;
        }
      },
    },
    "▶ Запустить",
  );

  const stopBtn = h(
    "button",
    {
      class:
        "flex-1 py-2.5 px-4 rounded-xl border border-slate-600 text-slate-300 font-semibold hover:bg-slate-800 transition disabled:opacity-50",
      onclick: async () => {
        stopBtn.disabled = true;
        try {
          await api.ttsBatchStop();
          toast("Остановка после текущего батча…", "info");
          await refresh();
        } catch (e) {
          toast(e.message, "error");
        }
      },
    },
    "■ Стоп",
  );

  const card = h(
    "div",
    { class: "glass-panel rounded-2xl p-5 space-y-3" },
    [
      h("div", {}, [
        h("div", { class: "text-base font-semibold" }, "Озвучка (админ)"),
        h(
          "div",
          { class: "text-xs text-slate-400 mt-1" },
          "Фоновая генерация недостающих аудио по всем словам. Можно останавливать и запускать заново — продолжит с того места, где обрывалось.",
        ),
      ]),
      statusLine,
      countsLine,
      progressWrap,
      currentLine,
      recentLine,
      errorLine,
      h("div", { class: "flex gap-2 pt-1" }, [startBtn, stopBtn]),
    ],
  );

  let pollTimer = null;

  const apply = (data) => {
    const status = data.status || "idle";
    const total = data.total || 0;
    const processed = data.processed || 0;
    const errors = data.errors || 0;
    const pct = total ? Math.min(100, Math.round((processed / total) * 100)) : 0;

    const statusLabels = {
      idle: "Ожидает",
      running: "Генерируется",
      stopping: "Останавливается…",
      done: "Готово",
      error: "Ошибка",
    };
    statusLine.textContent = `${statusLabels[status] || status} · движок ${data.engine || "?"} / ${data.voice || "?"} · параллельно ${data.concurrency || 1}${
      data.elapsed_seconds != null ? ` · ${data.elapsed_seconds}s` : ""
    }`;

    countsLine.textContent = `Обработано: ${processed} / ${total} · ошибок: ${errors}`;
    progressBar.style.width = `${pct}%`;
    currentLine.textContent = data.current_word ? `Сейчас: ${data.current_word}` : "";
    recentLine.textContent =
      data.recent && data.recent.length ? `Последние: ${data.recent.slice(-10).join(", ")}` : "";
    errorLine.textContent = data.last_error ? `Последняя ошибка: ${data.last_error}` : "";

    const isActive = status === "running" || status === "stopping";
    startBtn.disabled = isActive;
    stopBtn.disabled = status !== "running";
  };

  const refresh = async () => {
    try {
      const data = await api.ttsBatchStatus();
      apply(data);
      return data;
    } catch (e) {
      statusLine.textContent = `Ошибка загрузки статуса: ${e.message}`;
      return null;
    }
  };

  const ensurePolling = () => {
    if (pollTimer) return;
    pollTimer = setInterval(async () => {
      const data = await refresh();
      if (!data) return;
      if (data.status !== "running" && data.status !== "stopping") {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    }, 1500);
  };

  refresh().then((data) => {
    if (data && (data.status === "running" || data.status === "stopping")) {
      ensurePolling();
    }
  });

  return card;
}
