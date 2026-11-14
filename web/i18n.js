// All interface text in English and German. Answers themselves follow the language of the question.

const STRINGS = {
  en: {
    showLibrary: "Show library",
    language: "Interface language",
    switchTheme: "Switch color theme",
    library: "Library",
    files: (n) => `${n} ${n === 1 ? "file" : "files"}`,
    addPdf: "Add a PDF",
    dropHint: "Drop a file here or browse",
    heroTitle: "Ask your documents.<br>Get the page it's on.",
    heroText: "Answers come only from the PDFs in your library, in German or English, with a citation you can open.",
    examples: [
      "What is the StEOP and how do I complete it?",
      "Can I bring my dog to campus?",
      "How much does student parking cost per semester?",
      "Wie oft darf ich eine Prüfung wiederholen?",
    ],
    yourQuestion: "Your question",
    placeholder: "Ask a question about your PDFs",
    ask: "Ask",
    composerHint: "Enter to send, Shift + Enter for a new line",
    source: "Source",
    closeSource: "Close source",
    passageLabel: "Passage the answer is based on",
    openPdf: "Open PDF at this page",

    statusOk: (llm, n) => `${llm} · ${n} passages indexed`,
    statusDown: "Backend not reachable",
    pagesPassages: (p, c) => `${p} pages · ${c} passages`,
    noDocs: "No documents yet. Add a PDF above to start asking questions.",
    docsFailed: "Couldn't load the library. Is the backend running?",
    onlyPdf: "Only PDF files can be added.",
    indexing: (name) => `Reading and indexing ${name}…`,
    added: (title, chunks, s) => `Added ${title} (${chunks} passages, ${s} s).`,
    scanned: (name) => `${name}: no text found. It may be a scanned PDF.`,

    searching: "Searching your documents",
    writing: "Writing the answer",
    workingAria: "Working on the answer",
    retrieved: (n) => `Retrieved passages (${n})`,
    translate: "Translate", translateTip: "The LLM rewrites the question in German and English",
    search: "Search", searchTip: "Vector + keyword search",
    rerank: "Rerank", rerankTip: "Cross-encoder reranking",
    answer: "Answer", answerTip: "The LLM writes the answer",
    notAsked: "No relevant passage, model not asked",
    refusalHint: "Try rephrasing, or add the PDF that covers this.",
    page: "page", pageCap: "Page", relevance: "relevance",
    scoreTip: "Reranker relevance score",
    openSourceAria: (title, page) => `Open source ${title}, page ${page}`,
    notRetrieved: "This page was cited but isn't among the retrieved passages. Open the PDF to check it.",
    tryAgain: "Try again",
    backendDown: "Can't reach the backend. Is it still running?",
    requestFailed: (code) => `Request failed (${code})`,
    serverErrors: {
      "Only PDF files are supported": "Only PDF files can be added.",
      "This file doesn't look like a PDF": "This file doesn't look like a PDF.",
    },
  },

  de: {
    showLibrary: "Bibliothek anzeigen",
    language: "Sprache der Oberfläche",
    switchTheme: "Farbschema wechseln",
    library: "Bibliothek",
    files: (n) => `${n} ${n === 1 ? "Datei" : "Dateien"}`,
    addPdf: "PDF hinzufügen",
    dropHint: "Datei hierher ziehen oder auswählen",
    heroTitle: "Frag deine Dokumente.<br>Mit der Seite, wo's steht.",
    heroText: "Antworten kommen nur aus den PDFs in deiner Bibliothek, auf Deutsch oder Englisch, mit einer Quelle zum Anklicken.",
    examples: [
      "Wie oft darf ich eine Prüfung wiederholen?",
      "Was kostet das Parkticket für Studierende?",
      "Darf ich meinen Hund mit auf den Campus nehmen?",
      "What is the StEOP and how do I complete it?",
    ],
    yourQuestion: "Deine Frage",
    placeholder: "Stell eine Frage zu deinen PDFs",
    ask: "Fragen",
    composerHint: "Enter zum Senden, Shift + Enter für eine neue Zeile",
    source: "Quelle",
    closeSource: "Quelle schließen",
    passageLabel: "Textstelle, auf der die Antwort beruht",
    openPdf: "PDF auf dieser Seite öffnen",

    statusOk: (llm, n) => `${llm} · ${n} Textstellen indexiert`,
    statusDown: "Backend nicht erreichbar",
    pagesPassages: (p, c) => `${p} Seiten · ${c} Textstellen`,
    noDocs: "Noch keine Dokumente. Füge oben ein PDF hinzu, um Fragen zu stellen.",
    docsFailed: "Bibliothek konnte nicht geladen werden. Läuft das Backend?",
    onlyPdf: "Es können nur PDF-Dateien hinzugefügt werden.",
    indexing: (name) => `${name} wird gelesen und indexiert…`,
    added: (title, chunks, s) => `${title} hinzugefügt (${chunks} Textstellen, ${s} s).`,
    scanned: (name) => `${name}: kein Text gefunden. Vielleicht ein gescanntes PDF.`,

    searching: "Dokumente werden durchsucht",
    writing: "Antwort wird geschrieben",
    workingAria: "Antwort wird erstellt",
    retrieved: (n) => `Gefundene Textstellen (${n})`,
    translate: "Übersetzen", translateTip: "Das LLM formuliert die Frage auf Deutsch und Englisch",
    search: "Suche", searchTip: "Vektor- und Stichwortsuche",
    rerank: "Reranking", rerankTip: "Neu-Sortierung mit Cross-Encoder",
    answer: "Antwort", answerTip: "Das LLM schreibt die Antwort",
    notAsked: "Keine passende Textstelle, Modell nicht gefragt",
    refusalHint: "Versuch es mit anderen Worten oder füge das passende PDF hinzu.",
    page: "Seite", pageCap: "Seite", relevance: "Relevanz",
    scoreTip: "Relevanz-Score des Rerankers",
    openSourceAria: (title, page) => `Quelle ${title}, Seite ${page} öffnen`,
    notRetrieved: "Diese Seite wurde zitiert, ist aber nicht unter den gefundenen Textstellen. Öffne das PDF, um sie zu prüfen.",
    tryAgain: "Nochmal versuchen",
    backendDown: "Backend nicht erreichbar. Läuft es noch?",
    requestFailed: (code) => `Anfrage fehlgeschlagen (${code})`,
    serverErrors: {
      "Only PDF files are supported": "Es können nur PDF-Dateien hinzugefügt werden.",
      "This file doesn't look like a PDF": "Diese Datei scheint kein PDF zu sein.",
      "No text found. It may be a scanned PDF.": "Kein Text gefunden. Vielleicht ein gescanntes PDF.",
    },
  },
};

let LANG = document.documentElement.lang === "de" ? "de" : "en";

// t("key") or t("key", arg1, arg2) for strings that take values
function t(key, ...args) {
  const value = STRINGS[LANG][key] ?? STRINGS.en[key];
  return typeof value === "function" ? value(...args) : value;
}

// Translate backend error messages we know; pass others through unchanged
function tServer(message) {
  return STRINGS[LANG].serverErrors[message] || message;
}

// Fill every element marked with data-i18n* attributes
function applyStaticText() {
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => { el.innerHTML = t(el.dataset.i18nHtml); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nAria)); });
}
