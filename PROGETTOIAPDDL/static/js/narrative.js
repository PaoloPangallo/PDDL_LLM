// static/js/narrative.js
// Streaming real-time LLM responses (SSE) – versione robusta

document.addEventListener("DOMContentLoaded", () => {
  /* ---------- CACHE DOM ---------- */
  const loreSelect  = document.getElementById("lore-select");
  const startBtn    = document.getElementById("start-narrative");
  const stopBtn     = document.getElementById("stop-narrative");
  const spinner     = document.getElementById("start-spinner");
  const statusTxt   = document.getElementById("status-text");
  const log         = document.getElementById("narrative-log");
  const rawDebug    = document.getElementById("raw-debug");
  const form        = document.getElementById("narrative-form");
  const feedbackIn  = document.getElementById("feedback-input");

  /* ---------- STATE ---------- */
  let threadId = null;
  let source   = null;

  /* ---------- UI helpers ---------- */
  const showForm  = () => { form.classList.remove("d-none"); form.style.display = "flex"; feedbackIn.focus(); };
  const hideForm  = () => { form.classList.add("d-none");   form.style.display = "none"; };
  const clearUI   = () => { log.innerHTML = ""; rawDebug.innerHTML = ""; feedbackIn.value = ""; };

  /** Append a message to log */
  function append(msg, type = "log") {
    const p = document.createElement("p");
    p.className = {
      narration: "narration mb-2",
      question : "question mb-2 text-muted fst-italic",
      tech     : "small text-secondary mb-1",
      log      : "mb-2"
    }[type] || "mb-2";

    p.innerHTML = (typeof msg === "object")
      ? `<pre class="m-0">${JSON.stringify(msg, null, 2)}</pre>`
      : msg;

    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
  }

  /* ---------- Handle each SSE event ---------- */
  function handleEvt(evtType, payload) {
    switch (evtType) {
      case "loadplan":
        handleLoadPlan(payload);
        break;

      case "narrateStep":
      case "narratestep":
        append(`⚙️ Step ${payload.step} in corso…`, "tech");
        break;

      case "narration":
        append(`🗣️ ${payload.narration}`, "narration");
        break;

      case "question":
        append(`❓ ${payload.question}`, "question");
        showForm();
        break;

      case "chatfeedback":
        append(payload.message || "💬 Puoi inviare un feedback ora.", "question");
        showForm();
        break;

      case "append":
      case "appendtoplan":
        append(`📌 Step arricchito: ${payload.action}`, "narration");
        hideForm();
        break;

      case "done":
        append(payload.message || "✅ Avventura completata.", "log");
        updateUIEnd();
        break;

      case "error":
        append(payload.message || "❌ Errore nella narrazione.", "question");
        updateUIEnd();
        break;

      default:
        if (window.showTechEvents) append(`⚙️ Evento tecnico: ${evtType}`, "tech");
    }
  }

  /* ---------- LoadPlan pretty print ---------- */
  function handleLoadPlan(payload) {
    if (payload.lore?.description) append(`📘 <strong>Lore</strong>: ${payload.lore.description}`, "question");

    const steps = payload.plan_steps || [];
    append(`📦 Piano caricato con ${steps.length} step:`, "log");
    steps.forEach(s => append(`🔹 [${s.step}] ${s.action} (costo: ${s.step_cost}, cumulativo: ${s.cumulative_cost})`, "log"));
  }

  /* ---------- SSE Open ---------- */
  function startStream(extraFeedback = "") {
    if (source) source.close();

    threadId = threadId || `narrative-${Date.now()}`;
    const params = new URLSearchParams({ thread_id: threadId, lore: loreSelect.value });
    if (extraFeedback) params.set("feedback", extraFeedback);

    source = new EventSource(`/narrative/stream?${params}`);

    source.addEventListener("message", (e) => {            // fallback generico
      console.warn("Evento generico non gestito:", e.data);
    });

    // Gestione di tutti gli eventi previsti
    [
      "LoadPlan","NarrateStep","Narration","Question",
      "ChatFeedback","Append","AppendToPlan",
      "Done","Error","NarrateStep","ApplyLoreUpdate",
      "NextStep","step"
    ].forEach(name => {
      source.addEventListener(name, e => {
        // normalizza in minuscolo per semplicità
        let payload;
        try { payload = JSON.parse(e.data); } catch { payload = e.data; }
        handleEvt(name.toLowerCase(), payload);
      });
    });

    source.onerror = () => { console.error("SSE errore/chiuso"); updateUIEnd(); };
  }

  /* ---------- UI helpers ---------- */
  function updateUIStart() {
    startBtn.disabled = true;
    spinner.classList.remove("d-none");
    statusTxt.classList.remove("d-none");
    stopBtn.classList.remove("d-none");
    hideForm();
    clearUI();
  }
  function updateUIEnd() {
    startBtn.disabled = false;
    spinner.classList.add("d-none");
    statusTxt.classList.add("d-none");
    stopBtn.classList.add("d-none");
    hideForm();
  }

  /* ---------- BUTTONS ---------- */
  startBtn.addEventListener("click", () => {
    if (!loreSelect.value) return alert("Seleziona una lore.");
    threadId = `narrative-${Date.now()}`;
    document.body.dataset.threadId = threadId;
    updateUIStart();
    startStream();
  });

  stopBtn.addEventListener("click", () => {
    append("✋ Narrazione interrotta.", "question");
    source?.close();
    updateUIEnd();
  });

  /* ---------- FEEDBACK FORM ---------- */
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const fb = feedbackIn.value.trim();
    if (!fb) return;

    append(`🧠 ${fb}`, "question");
    hideForm(); feedbackIn.value = "";

    try {
      const res = await fetch("/narrative/message", {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify({ thread_id: threadId, feedback: fb })
      });
      const json = await res.json();

      if (json.done) {
        append("✅ Narrazione terminata.", "log");
        updateUIEnd();
      } else {
        // riprendi lo stream senza extra feedback
        startStream();
      }
    } catch (err) {
      console.error(err);
      append("❌ Errore nell'invio del feedback.", "question");
      updateUIEnd();
    }
  });
});
