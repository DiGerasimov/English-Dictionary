import { api, auth } from "./api.js";
import { h, toast } from "./ui.js";
import { renderLearn } from "./views/learn.js";
import { renderQuiz } from "./views/quiz.js";
import { renderStats } from "./views/stats.js";
import { renderProfile } from "./views/profile.js";

const app = document.getElementById("app");

const NAV_ITEMS = [
  { id: "learn", hash: "#/learn", icon: "📖", label: "Изучать" },
  { id: "quiz", hash: "#/quiz", icon: "🎯", label: "Квиз" },
  { id: "stats", hash: "#/stats", icon: "📊", label: "Статистика" },
  { id: "profile", hash: "#/profile", icon: "👤", label: "Профиль" },
];

const routes = {
  "#/login": renderAuth,
  "#/learn": (root) => guard(root, "learn", renderLearn),
  "#/learn/cards": (root) => guard(root, "learn", renderLearn),
  "#/learn/dictionary": (root) => guard(root, "learn", renderLearn),
  "#/quiz": (root) => guard(root, "quiz", renderQuiz),
  "#/stats": (root) => guard(root, "stats", renderStats),
  "#/profile": (root) => guard(root, "profile", renderProfile),
};

function guard(root, activeId, fn) {
  if (!auth.getToken()) {
    location.hash = "#/login";
    return;
  }
  renderShell(root, activeId, fn);
}

function renderShell(root, activeId, pageFn) {
  root.innerHTML = "";
  root.className = "min-h-screen";

  const shell = h("div", { class: "app-shell" });

  const side = h("aside", { class: "side-nav" }, [
    h("div", { class: "flex items-center gap-2 px-2 mb-6" }, [
      h("div", { class: "text-2xl" }, "📚"),
      h("div", { class: "font-bold text-lg" }, "English Cards"),
    ]),
    h(
      "nav",
      { class: "flex flex-col gap-1" },
      NAV_ITEMS.map((n) =>
        h(
          "a",
          {
            href: n.hash,
            class: `side-link ${activeId === n.id ? "is-active" : ""}`,
          },
          [h("span", { class: "text-xl" }, n.icon), h("span", {}, n.label)],
        ),
      ),
    ),
  ]);

  const mainCol = h("div", {
    class: "main-col max-w-3xl w-full mx-auto lg:mx-0 min-w-0",
  });
  const main = h("main", { class: "flex-1 min-w-0 w-full" });
  mainCol.append(main);

  shell.append(side, mainCol);
  root.append(shell);

  const mobileNav = h(
    "nav",
    {
      class:
        "mobile-tabbar fixed bottom-0 left-0 right-0 z-40 border-t border-white/10 bg-slate-950/80 backdrop-blur-xl",
    },
    [
      h(
        "div",
        { class: "max-w-3xl mx-auto grid grid-cols-4 h-16" },
        NAV_ITEMS.map((n) =>
          h(
            "a",
            {
              href: n.hash,
              class: `tab-link ${activeId === n.id ? "is-active" : ""}`,
            },
            [
              h("span", { class: "text-xl" }, n.icon),
              h("span", { class: "text-[11px] mt-0.5" }, n.label),
            ],
          ),
        ),
      ),
    ],
  );
  root.append(mobileNav);

  pageFn(main);
}

function renderAuth(root) {
  root.innerHTML = "";
  root.className = "min-h-screen flex flex-col";
  const tpl = document.getElementById("tpl-auth");
  const node = tpl.content.firstElementChild.cloneNode(true);
  root.append(node);

  const tabs = node.querySelectorAll(".tab-btn");
  const forms = {
    login: node.querySelector('[data-form="login"]'),
    register: node.querySelector('[data-form="register"]'),
  };
  const errorBox = node.querySelector("[data-error]");

  const showTab = (tab) => {
    tabs.forEach((b) => b.classList.toggle("is-active", b.dataset.tab === tab));
    tabs.forEach((b) => b.classList.toggle("bg-slate-800", b.dataset.tab === tab));
    tabs.forEach((b) => b.classList.toggle("shadow-sm", b.dataset.tab === tab));
    tabs.forEach((b) => b.classList.toggle("text-white", b.dataset.tab === tab));
    forms.login.classList.toggle("hidden", tab !== "login");
    forms.register.classList.toggle("hidden", tab !== "register");
    errorBox.classList.add("hidden");
  };
  tabs.forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

  const showError = (msg) => {
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  };

  forms.login.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.classList.add("hidden");
    const fd = new FormData(forms.login);
    try {
      const tok = await api.login({
        email: fd.get("email"),
        password: fd.get("password"),
      });
      auth.setToken(tok.access_token);
      const me = await api.me();
      auth.setUser(me);
      location.hash = "#/learn";
    } catch (err) {
      showError(err.message);
    }
  });

  forms.register.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.classList.add("hidden");
    const fd = new FormData(forms.register);
    try {
      const tok = await api.register({
        email: fd.get("email"),
        username: fd.get("username"),
        password: fd.get("password"),
      });
      auth.setToken(tok.access_token);
      const me = await api.me();
      auth.setUser(me);
      toast("Добро пожаловать!", "success");
      location.hash = "#/learn";
    } catch (err) {
      showError(err.message);
    }
  });
}

function route() {
  const hash = location.hash || (auth.getToken() ? "#/learn" : "#/login");
  if (!location.hash) {
    location.hash = hash;
    return;
  }
  const fn = routes[hash] || routes["#/learn"];
  try {
    fn(app);
  } catch (e) {
    console.error(e);
    toast(e.message || "Ошибка", "error");
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("load", route);
