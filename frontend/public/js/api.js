const TOKEN_KEY = "english.token";
const USER_KEY = "english.user";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  getUser: () => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  setUser: (u) => localStorage.setItem(USER_KEY, JSON.stringify(u)),
};

function buildQuery(query) {
  const params = new URLSearchParams();
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) {
      v.forEach((item) => {
        if (item !== undefined && item !== null && item !== "") {
          params.append(k, item);
        }
      });
    } else {
      params.append(k, v);
    }
  });
  return params.toString();
}

async function request(path, { method = "GET", body, auth: needAuth = true, query } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (needAuth) {
    const t = auth.getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }
  let url = `/api/v1${path}`;
  if (query) {
    const s = buildQuery(query);
    if (s) url += `?${s}`;
  }
  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    auth.clear();
    location.hash = "#/login";
    throw new Error("Не авторизован");
  }
  const ct = res.headers.get("content-type") || "";
  let data = null;
  if (ct.includes("application/json")) {
    const text = await res.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        console.error("JSON parse error:", e);
      }
    }
  }
  if (!res.ok) {
    const msg = (data && data.detail) || `Ошибка ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  register: (payload) => request("/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),
  me: () => request("/auth/me"),
  updateSettings: (payload) =>
    request("/auth/me/settings", { method: "PATCH", body: payload }),
  resetProgress: () => request("/auth/me/reset-progress", { method: "POST" }),

  categories: () => request("/categories"),
  pinCategory: (id) => request(`/categories/${id}/pin`, { method: "POST" }),
  unpinCategory: (id) => request(`/categories/${id}/pin`, { method: "DELETE" }),

  activeWords: (q) => request("/words/active", { query: q }),
  dictionary: (q) => request("/words/dictionary", { query: q }),
  word: (id) => request(`/words/${id}`),
  markWordViewed: (id) => request(`/words/${id}/view`, { method: "POST" }),

  quizNext: (q) => request("/quiz/next", { query: q }),
  quizAnswer: (payload) => request("/quiz/answer", { method: "POST", body: payload }),

  overview: () => request("/stats/overview"),
  timeline: (days = 30) => request("/stats/timeline", { query: { days } }),
  byCategory: () => request("/stats/by-category"),

  ttsBatchStatus: () => request("/admin/tts/batch"),
  ttsBatchStart: () => request("/admin/tts/batch/start", { method: "POST" }),
  ttsBatchStop: () => request("/admin/tts/batch/stop", { method: "POST" }),
};

const audioUrlCache = new Map();
const audioPromiseCache = new Map();

async function fetchAudioBlobUrl(wordId) {
  if (audioUrlCache.has(wordId)) return audioUrlCache.get(wordId);
  if (audioPromiseCache.has(wordId)) return audioPromiseCache.get(wordId);

  const promise = (async () => {
    const headers = {};
    const t = auth.getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
    const res = await fetch(`/api/v1/words/${wordId}/audio`, { headers });
    if (res.status === 401) {
      auth.clear();
      location.hash = "#/login";
      throw new Error("Не авторизован");
    }
    if (!res.ok) {
      let msg = `Ошибка ${res.status}`;
      try {
        const data = await res.json();
        if (data && data.detail) msg = data.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    const ct = res.headers.get("content-type") || "audio/wav";
    const buf = await res.arrayBuffer();
    if (buf.byteLength < 200) {
      throw new Error(`Аудио пустое (${buf.byteLength} байт)`);
    }
    const blob = new Blob([buf], { type: ct });
    const url = URL.createObjectURL(blob);
    audioUrlCache.set(wordId, url);
    return url;
  })();

  audioPromiseCache.set(wordId, promise);
  try {
    return await promise;
  } finally {
    audioPromiseCache.delete(wordId);
  }
}

let currentAudio = null;

export function stopAudio() {
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    } catch {
      /* ignore */
    }
    currentAudio = null;
  }
}

export async function playWordAudio(wordId) {
  stopAudio();
  const url = await fetchAudioBlobUrl(wordId);
  stopAudio();
  
  const audio = new Audio();
  audio.preload = "auto";
  audio.src = url;
  currentAudio = audio;

  await new Promise((resolve, reject) => {
    const onError = () => {
      const err = audio.error;
      const code = err ? err.code : "?";
      reject(new Error(`Не удалось декодировать аудио (code=${code})`));
    };
    audio.addEventListener("error", onError, { once: true });
    audio.addEventListener("canplay", () => resolve(), { once: true });
    audio.load();
  });

  await audio.play();
  return audio;
}

const BG_MUSIC_KEY = "english.bgMusic";
export const bgMusic = {
  audio: new Audio("/music/Dont-Forget-Me(chosic.com).mp3"),
  state: { enabled: true, volume: 0.1 },
  init() {
    this.audio.loop = true;
    try {
      const saved = JSON.parse(localStorage.getItem(BG_MUSIC_KEY));
      if (saved) this.state = { ...this.state, ...saved };
    } catch (e) {}
    this.applySettings();

    const startOnInteract = () => {
      if (this.state.enabled && this.audio.paused) {
        this.audio.play().catch(() => {});
      }
      document.removeEventListener("click", startOnInteract);
      document.removeEventListener("keydown", startOnInteract);
    };
    document.addEventListener("click", startOnInteract);
    document.addEventListener("keydown", startOnInteract);
  },
  applySettings() {
    this.audio.volume = this.state.volume;
    if (this.state.enabled) {
      this.audio.play().catch(() => {});
    } else {
      this.audio.pause();
    }
  },
  update(enabled, volume) {
    this.state.enabled = enabled;
    this.state.volume = volume;
    localStorage.setItem(BG_MUSIC_KEY, JSON.stringify(this.state));
    this.applySettings();
  }
};

// Инициализируем фоновую музыку при загрузке модуля
bgMusic.init();
