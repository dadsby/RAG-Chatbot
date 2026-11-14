// Fundstelle front end. Plain JavaScript, no build step: talks to the FastAPI backend in api/main.py.
// All interface text lives in i18n.js (t() function); answers follow the language of the question.

const $ = (sel) => document.querySelector(sel);
const els = {
  status: $("#status"), docList: $("#doc-list"), docCount: $("#doc-count"),
  dropzone: $("#dropzone"), fileInput: $("#file-input"), uploadMsg: $("#upload-msg"),
  thread: $("#thread"), empty: $("#empty"), examples: $("#examples"),
  composer: $("#composer"), question: $("#question"), send: $("#send"),
  panel: $("#panel"), panelFile: $("#panel-file"), panelMeta: $("#panel-meta"),
  panelText: $("#panel-text"), panelOpen: $("#panel-open"), panelClose: $("#panel-close"),
  library: $("#library"), libraryToggle: $("#library-toggle"), scrim: $("#scrim"),
  themeToggle: $("#theme-toggle"), langSwitch: $("#lang-switch"),
};

let busy = false;
let lastFocus = null;
let titles = {};      // file name -> nice title from data/sources.csv
let health = null;    // last /api/health result
let documents = null; // last /api/documents result
let uploadState = null; // last upload message, kept so it can be re-translated
let panelState = null;  // what the source panel shows, kept for re-translation
const turns = [];       // { el, question, result, error } for re-rendering on language change

/* ---------------------------------------------------------------- helpers */

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Title from sources.csv if known, else "satzung_studienrecht_2026.pdf" -> "Satzung studienrecht 2026"
function prettyName(file) {
  if (titles[file]) return titles[file];
  const base = file.replace(/\.pdf$/i, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  return base.charAt(0).toUpperCase() + base.slice(1);
}

// Short label for citation pills: the title without "(...)", cut at a word boundary.
function shortName(file) {
  const s = prettyName(file).replace(/\s*\(.*?\)\s*/g, " ").trim();
  if (s.length <= 26) return s;
  return s.slice(0, 26).replace(/\s+\S*$/, "") + "…";
}

const seconds = (ms) => `${(ms / 1000).toFixed(1)} s`;
const pdfUrl = (file, page) => `/api/documents/${encodeURIComponent(file)}/file#page=${page}`;

async function api(path, options = {}) {
  const res = await fetch(path, options);
  let body = null;
  try { body = await res.json(); } catch (e) { /* not JSON */ }
  if (!res.ok) {
    const detail = body && body.detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : null;
    const err = new Error(msg || t("requestFailed", res.status));
    err.server = Boolean(msg);
    throw err;
  }
  return body;
}

/* ---------------------------------------------------------------- status + library */

function renderStatus() {
  if (health === null) { els.status.textContent = ""; return; }
  const ok = health !== false;
  els.status.textContent = ok ? t("statusOk", health.llm, health.chunks) : t("statusDown");
  els.status.classList.toggle("is-error", !ok);
}

async function loadStatus() {
  try { health = await api("/api/health"); } catch (e) { health = false; }
  renderStatus();
}

function renderDocuments(highlight) {
  if (documents === null) return;
  if (documents === false) {
    els.docList.innerHTML = `<li class="doc-empty">${t("docsFailed")}</li>`;
    return;
  }
  els.docList.setAttribute("aria-busy", "false");
  els.docCount.textContent = documents.length ? t("files", documents.length) : "";
  if (!documents.length) {
    els.docList.innerHTML = `<li class="doc-empty">${t("noDocs")}</li>`;
    return;
  }
  els.docList.innerHTML = documents.map((d) => `
    <li>
      <a class="doc${d.name === highlight ? " is-new" : ""}" href="${pdfUrl(d.name, 1)}" target="_blank" rel="noopener" title="${escapeHtml(d.name)}">
        <i class="ph ph-file-text" aria-hidden="true"></i>
        <span>
          <span class="doc-name">${escapeHtml(prettyName(d.name))}</span>
          <span class="doc-meta">${t("pagesPassages", d.pages ?? "?", d.chunks)}</span>
        </span>
      </a>
    </li>`).join("");
}

async function loadDocuments(highlight) {
  try {
    documents = (await api("/api/documents")).documents;
    titles = Object.fromEntries(documents.filter((d) => d.title).map((d) => [d.name, d.title]));
  } catch (e) {
    documents = false;
  }
  renderDocuments(highlight);
}

/* ---------------------------------------------------------------- upload */

function renderUploadMsg() {
  const s = uploadState;
  els.uploadMsg.hidden = !s;
  if (!s) return;
  els.uploadMsg.textContent = typeof s.text === "function" ? s.text() : s.text;
  els.uploadMsg.className = `upload-msg${s.kind ? ` is-${s.kind}` : ""}`;
}
function setUpload(text, kind) { uploadState = text ? { text, kind } : null; renderUploadMsg(); }

async function upload(file) {
  if (!file) return;
  if (!/\.pdf$/i.test(file.name)) { setUpload(() => t("onlyPdf"), "error"); return; }
  els.dropzone.classList.add("is-busy");
  setUpload(() => t("indexing", file.name));
  const form = new FormData();
  form.append("file", file);
  try {
    const r = await api("/api/documents", { method: "POST", body: form });
    if (r.warning) setUpload(() => t("scanned", r.name), "warn");
    else setUpload(() => t("added", prettyName(r.name), r.chunks, r.seconds), "ok");
    await Promise.all([loadDocuments(r.name), loadStatus()]);
  } catch (e) {
    const msg = e.message;
    setUpload(() => tServer(msg), "error");
  } finally {
    els.dropzone.classList.remove("is-busy");
    els.fileInput.value = "";
  }
}

els.fileInput.addEventListener("change", () => upload(els.fileInput.files[0]));
["dragenter", "dragover"].forEach((type) => els.dropzone.addEventListener(type, (e) => {
  e.preventDefault(); els.dropzone.classList.add("is-over");
}));
["dragleave", "drop"].forEach((type) => els.dropzone.addEventListener(type, (e) => {
  e.preventDefault(); els.dropzone.classList.remove("is-over");
}));
els.dropzone.addEventListener("drop", (e) => upload(e.dataTransfer.files[0]));

/* ---------------------------------------------------------------- answer rendering */

const CITATION = /\[([^\[\],]+?\.pdf),\s*(?:p\.|S\.|page)\s*(\d+)\]/gi;

// Tiny, safe markdown: escape first, then bold, lists, paragraphs, citation pills.
function renderAnswer(text) {
  const withCites = escapeHtml(text).replace(CITATION, (_, file, page) => {
    const f = file.trim();
    return `<button type="button" class="cite" data-source="${f}" data-page="${page}" aria-label="${escapeHtml(t("openSourceAria", prettyName(f), page))}">` +
      `<i class="ph ph-file-text" aria-hidden="true"></i>${escapeHtml(shortName(f))} · ${LANG === "de" ? "S." : "p."} ${page}</button>`;
  });
  const lines = withCites.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").split("\n");
  const out = [];
  let group = null;
  const flush = () => {
    if (!group) return;
    if (group.type === "p") out.push(`<p>${group.items.join("<br>")}</p>`);
    else out.push(`<${group.type}>${group.items.map((i) => `<li>${i}</li>`).join("")}</${group.type}>`);
    group = null;
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    const type = bullet ? "ul" : numbered ? "ol" : "p";
    if (!group || group.type !== type) { flush(); group = { type, items: [] }; }
    group.items.push(bullet ? bullet[1] : numbered ? numbered[1] : line);
  }
  flush();
  return out.join("");
}

function sourcesHtml(sources) {
  return sources.map((s, i) => `
    <button type="button" class="source" data-index="${i}">
      <span class="source-title">${escapeHtml(prettyName(s.source))}, ${t("page")} ${s.page}</span>
      <span class="source-score" title="${t("scoreTip")}">${s.score.toFixed(2)}</span>
      <span class="source-snippet">${escapeHtml(s.text.slice(0, 220))}</span>
    </button>`).join("");
}

function metaHtml(r) {
  const tm = r.timing;
  const steps = tm.translate_ms !== undefined
    ? `<span title="${t("translateTip")}">${t("translate")} ${seconds(tm.translate_ms)}</span>` +
      `<span title="${t("searchTip")}">${t("search")} ${seconds(tm.search_ms)}</span>` +
      `<span title="${t("rerankTip")}">${t("rerank")} ${seconds(tm.rerank_ms)}</span>`
    : `<span>${t("search")} ${seconds(tm.retrieval_ms)}</span>`;
  return r.refused_by === "threshold"
    ? `${steps}<span>${t("notAsked")}</span>`
    : `${steps}<span title="${t("answerTip")}">${t("answer")} ${seconds(tm.llm_ms)}</span>`;
}

function renderResult(turn) {
  const r = turn.result;
  const a = turn.el.querySelector(".a");
  const wasOpen = a.querySelector(".sources-toggle")?.getAttribute("aria-expanded") === "true";
  const body = r.refused
    ? `<div class="refusal"><i class="ph ph-file-dashed" aria-hidden="true"></i>
         <div><strong>${escapeHtml(r.answer)}</strong><span>${t("refusalHint")}</span></div></div>`
    : `<div class="a-body">${renderAnswer(r.answer)}</div>`;

  a.innerHTML = `${body}
    <div class="a-meta">
      <button type="button" class="sources-toggle" aria-expanded="${wasOpen}">
        <i class="ph ph-caret-right" aria-hidden="true"></i>${t("retrieved", r.sources.length)}
      </button>
      ${metaHtml(r)}
    </div>
    <div class="sources"${wasOpen ? "" : " hidden"}>${sourcesHtml(r.sources)}</div>`;

  const toggle = a.querySelector(".sources-toggle");
  const list = a.querySelector(".sources");
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    list.hidden = open;
  });
  list.addEventListener("click", (e) => {
    const btn = e.target.closest(".source");
    if (!btn) return;
    const s = r.sources[Number(btn.dataset.index)];
    openSource(r, s.source, s.page, btn);
  });
  a.querySelectorAll(".cite").forEach((btn) =>
    btn.addEventListener("click", () => openSource(r, btn.dataset.source, Number(btn.dataset.page), btn)));
}

function renderError(turn) {
  const a = turn.el.querySelector(".a");
  const message = turn.error === "offline" ? t("backendDown") : tServer(turn.error);
  a.innerHTML = `<div class="error" role="alert"><i class="ph ph-warning-circle" aria-hidden="true"></i>
    <span>${escapeHtml(message)}</span>
    <button type="button" class="chip">${t("tryAgain")}</button></div>`;
  a.querySelector(".chip").addEventListener("click", () => {
    turns.splice(turns.indexOf(turn), 1);
    turn.el.remove();
    ask(turn.question);
  });
}

/* ---------------------------------------------------------------- source panel */

const STOP = new Set("what when where which does have this that with from your about und oder der die das ist wie was wann darf kann eine einen einer für mit von nach".split(" "));

function highlight(text, question) {
  const terms = [...new Set((question.toLowerCase().match(/[\p{L}\d]{4,}/gu) || []).filter((w) => !STOP.has(w)))];
  const html = escapeHtml(text);
  if (!terms.length) return html;
  const re = new RegExp(`(${terms.map((x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "giu");
  return html.replace(re, "<mark>$1</mark>");
}

function renderPanel() {
  if (!panelState) return;
  const { result, source, page } = panelState;
  const chunks = result.sources.filter((s) => s.source === source && s.page === page);
  els.panelFile.textContent = prettyName(source);
  els.panelMeta.textContent = chunks.length
    ? `${t("pageCap")} ${page} · ${t("relevance")} ${Math.max(...chunks.map((c) => c.score)).toFixed(2)}`
    : `${t("pageCap")} ${page}`;
  els.panelText.innerHTML = chunks.length
    ? chunks.map((c) => highlight(c.text, result.question)).join("\n\n")
    : escapeHtml(t("notRetrieved"));
  els.panelOpen.href = pdfUrl(source, page);
}

function openSource(result, source, page, trigger) {
  lastFocus = trigger || document.activeElement;
  panelState = { result, source, page };
  renderPanel();
  els.panel.hidden = false;
  $("#app").classList.add("has-panel");
  els.scrim.hidden = false;
  els.panel.classList.remove("is-open");
  void els.panel.offsetWidth; // restart the slide-in animation
  els.panel.classList.add("is-open");
  els.panelClose.focus();
}

function closePanel() {
  if (els.panel.hidden) return;
  els.panel.hidden = true;
  panelState = null;
  $("#app").classList.remove("has-panel");
  if (!els.library.classList.contains("is-open")) els.scrim.hidden = true;
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
}
els.panelClose.addEventListener("click", closePanel);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closePanel(); toggleLibrary(false); }
});

/* ---------------------------------------------------------------- asking */

function renderWorking(turn) {
  turn.el.querySelector(".a").innerHTML = `
    <div class="working" aria-label="${t("workingAria")}">
      <p class="working-label">${t("searching")}…</p>
      <div class="skeleton-line"></div><div class="skeleton-line"></div>
      <div class="skeleton-line"></div><div class="skeleton-line"></div>
    </div>`;
}

function renderTurn(turn) {
  if (turn.result) renderResult(turn);
  else if (turn.error) renderError(turn);
  else renderWorking(turn);
}

function newTurn(question) {
  els.empty?.remove();
  const el = document.createElement("article");
  el.className = "turn turn-in";
  el.innerHTML = `<div class="q">${escapeHtml(question)}</div><div class="a"></div>`;
  els.thread.appendChild(el);
  const turn = { el, question, result: null, error: null, started: performance.now() };
  turns.push(turn);
  renderWorking(turn);
  el.scrollIntoView({ block: "start" });
  return turn;
}

async function ask(question) {
  question = question.trim();
  if (!question || busy) return;
  busy = true;
  updateSend();
  const turn = newTurn(question);
  const timer = setInterval(() => {
    const label = turn.el.querySelector(".working-label");
    if (!label) return;
    const s = (performance.now() - turn.started) / 1000;
    label.textContent = `${s < 2 ? t("searching") : t("writing")}… ${s.toFixed(0)} s`;
  }, 500);
  try {
    turn.result = await api("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch (e) {
    turn.error = e.message === "Failed to fetch" ? "offline" : e.message;
  } finally {
    clearInterval(timer);
    renderTurn(turn);
    busy = false;
    updateSend();
  }
}

function updateSend() {
  els.send.disabled = busy || els.question.value.trim().length < 2;
}

function autosize() {
  els.question.style.height = "auto";
  els.question.style.height = `${Math.min(els.question.scrollHeight, 180)}px`;
}

els.question.addEventListener("input", () => { autosize(); updateSend(); });
els.question.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); els.composer.requestSubmit(); }
});
els.composer.addEventListener("submit", (e) => {
  e.preventDefault();
  if (els.send.disabled) return;
  const q = els.question.value;
  els.question.value = "";
  autosize();
  ask(q);
});

function renderExamples() {
  if (!els.examples || !document.contains(els.examples)) return;
  els.examples.innerHTML = t("examples").map((q) => `<button class="chip" type="button">${escapeHtml(q)}</button>`).join("");
}
els.examples.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) ask(chip.textContent);
});

/* ---------------------------------------------------------------- language */

function setLanguage(lang, { animate = true } = {}) {
  LANG = lang;
  document.documentElement.lang = lang;
  try { localStorage.setItem("lang", lang); } catch (e) { /* storage blocked */ }
  els.langSwitch.dataset.active = lang;
  els.langSwitch.querySelectorAll("[data-lang]").forEach((b) =>
    b.setAttribute("aria-checked", String(b.dataset.lang === lang)));

  applyStaticText();
  renderExamples();
  renderStatus();
  renderDocuments();
  renderUploadMsg();
  renderPanel();
  turns.forEach(renderTurn);

  // Short crossfade so the swap reads as one change, not a flicker (CSS respects reduced motion).
  if (animate) {
    document.body.classList.remove("lang-swap");
    void document.body.offsetWidth;
    document.body.classList.add("lang-swap");
  }
}

els.langSwitch.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-lang]");
  if (btn && btn.dataset.lang !== LANG) setLanguage(btn.dataset.lang);
});
els.langSwitch.addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    e.preventDefault();
    const next = LANG === "en" ? "de" : "en";
    setLanguage(next);
    els.langSwitch.querySelector(`[data-lang="${next}"]`).focus();
  }
});

/* ---------------------------------------------------------------- theme + mobile library */

els.themeToggle.addEventListener("click", () => {
  const root = document.documentElement;
  const isDark = root.dataset.theme
    ? root.dataset.theme === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = isDark ? "light" : "dark";
  try { localStorage.setItem("theme", root.dataset.theme); } catch (e) { /* storage blocked */ }
});

function toggleLibrary(force) {
  const open = typeof force === "boolean" ? force : !els.library.classList.contains("is-open");
  els.library.classList.toggle("is-open", open);
  els.scrim.hidden = !open && els.panel.hidden;
  els.libraryToggle.setAttribute("aria-expanded", String(open));
}
els.libraryToggle.addEventListener("click", () => toggleLibrary());
els.scrim.addEventListener("click", () => { toggleLibrary(false); closePanel(); });

/* ---------------------------------------------------------------- start */

setLanguage(LANG, { animate: false });
loadStatus();
loadDocuments();
els.question.focus();
