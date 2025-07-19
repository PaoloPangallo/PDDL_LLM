/* static/js/pipeline.js - FIXED ──────────────────────────────────────
   Fix per evitare reset indesiderati della pipeline
   ----------------------------------------------------------------*/

document.addEventListener("DOMContentLoaded", () => {
  /* elementi di configurazione / controllo ------------------------------ */
  const threadId      = "session-1";
  const loreSelect    = document.getElementById("lore-select");
  const runBtn        = document.getElementById("run-from-scratch");
  const resetCheckbox = document.getElementById("reset-checkbox");
  const storyWrap     = document.getElementById("custom-story-wrap");
  const storyTA       = document.getElementById("custom-story");

  /* output console/chat -------------------------------------------------- */
  const chatLog  = document.getElementById("chat-log");
  const promptEl = document.getElementById("prompt-content");
  const rawEl    = document.getElementById("raw-content");

  /* form feedback testuale ---------------------------------------------- */
  const feedbackForm   = document.getElementById("chatbot-form");
  const feedbackInput  = document.getElementById("user-input");

  /* pannello live-edit --------------------------------------------------- */
  const editPanel   = document.getElementById("live-edit-panel");
  const domainTA    = document.getElementById("domain-edit");
  const problemTA   = document.getElementById("problem-edit");
  const sendEditBtn = document.getElementById("send-edit-btn");

  /* contenitori timeline dinamici --------------------------------------- */
  const validationWrap = document.getElementById("validation-list");
  const refineWrap     = document.getElementById("refine-list");

  /* stato locale --------------------------------------------------------- */
  let source = null;
  let isPaused = false;
  let isWaitingForEdit = false; // NEW: Flag specifico per editing
  const allValidations = [];
  const allRefines     = [];

  console.log("✅ DOMContentLoaded fired, elementi caricati");

  /* ───────────── helper UI ────────────────────────────────────────────── */
  function append(text, cls = "system") {
    const div = document.createElement("div");
    div.className = `chat-message ${cls}`;
    div.innerHTML = text;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function resetAll() {
    chatLog.innerHTML    = "";
    promptEl.textContent = "";
    rawEl.textContent    = "";
    
    allValidations.length = 0;
    allRefines.length = 0;

    if (validationWrap) validationWrap.innerHTML = "";
    if (refineWrap)     refineWrap.innerHTML     = "";

    hideEditPanel(); 
    storyWrap.classList.add("d-none");
    feedbackForm.classList.add("d-none");
    isPaused = false;
    isWaitingForEdit = false; // Reset anche questo flag
    
    closeEventSource();
    append("💬 Pronto per eseguire la pipeline…", "system");
  }

  function showEditPanel(domain = "", problem = "") {
    domainTA.value  = domain;
    problemTA.value = problem;
    editPanel.classList.remove("d-none");
    isWaitingForEdit = true; // Imposta flag editing
  }
  
  function hideEditPanel() {
    editPanel.classList.add("d-none");
    domainTA.value = problemTA.value = "";
    isWaitingForEdit = false; // Reset flag editing
  }

  function closeEventSource() {
    if (source) {
      console.log("🔌 Chiudo EventSource");
      source.close();
      source = null;
    }
  }

  /* ───────────── rendering timeline ───────────────────────────────────── */
  function renderValidationTimeline() {
    if (!validationWrap) return;
    validationWrap.innerHTML = "";
    allValidations.forEach((val, idx) => {
      const item = document.createElement("div");
      item.className = "accordion-item";
      item.innerHTML = `
        <h2 class="accordion-header" id="valHead${idx}">
          <button class="accordion-button ${idx > 0 ? "collapsed" : ""}"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#valCollapse${idx}"
                  aria-expanded="${idx === 0}"
                  aria-controls="valCollapse${idx}">
            🔍 Validation #${idx + 1}
          </button>
        </h2>
        <div id="valCollapse${idx}"
             class="accordion-collapse collapse ${idx === 0 ? "show" : ""}"
             aria-labelledby="valHead${idx}">
          <div class="accordion-body">
            <pre>${JSON.stringify(val, null, 2)}</pre>
          </div>
        </div>`;
      validationWrap.appendChild(item);
    });
  }

  function renderRefineTimeline() {
    if (!refineWrap) return;
    refineWrap.innerHTML = "";
    allRefines.forEach((r, idx) => {
      const col = document.createElement("div");
      col.className = "col";
      col.innerHTML = `
        <div class="card shadow-sm">
          <div class="card-header">Refine #${idx + 1}</div>
          <div class="card-body">
            <h6 class="text-muted">domain.pddl</h6>
            <pre class="small bg-light p-2 border rounded">${r.domain}</pre>
            <h6 class="text-muted mt-3">problem.pddl</h6>
            <pre class="small bg-light p-2 border rounded">${r.problem}</pre>
          </div>
        </div>`;
      refineWrap.appendChild(col);
    });
  }

  /* ───────────── listeners SSE dinamici ──────────────────────────────── */
  function attachPipelineListeners(es) {
    es.addEventListener("Generate", e => {
      const { domain, problem, prompt } = JSON.parse(e.data);
      if (prompt) {
        promptEl.textContent = prompt;
        append("📝 Prompt generato", "bot");
      }
      rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
      append("🧠 Generazione completata", "bot");
    });

    es.addEventListener("PreparePrompt", e => {
      append("📜 Prompt impostato", "bot");
    });
    
    es.addEventListener("GenerateVision", e => {
      append("👁️ Vision JSON pronto", "bot");
    });
    
    es.addEventListener("GenerateSpec", e => {
      append("📐 Spec JSON pronto", "bot");
    });

    es.addEventListener("TemplateFallback", e => {
      const { domain, problem } = JSON.parse(e.data);
      rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
      append("🏗️ PDDL generati da template", "bot");
    });

    es.addEventListener("Validate", e => {
      const { validation } = JSON.parse(e.data);
      allValidations.push(validation);
      renderValidationTimeline();
      append(`📋 Validazione #${allValidations.length} completata`, "bot");
    });

    es.addEventListener("Refine", e => {
      const { refined_domain, refined_problem } = JSON.parse(e.data);
      allRefines.push({ domain: refined_domain, problem: refined_problem });
      renderRefineTimeline();
      append(`🔧 Refine #${allRefines.length} completato`, "bot");
    });

    es.addEventListener("ChatFeedback", e => {
      console.log("📨 ChatFeedback ricevuto - pipeline in pausa per editing");
      const { domain, problem } = JSON.parse(e.data);
      
      showEditPanel(domain, problem);
      rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
      
      // Scroll verso il pannello di editing
      setTimeout(() => {
        editPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
      
      append("✏️ Modifica live disponibile - edita e invia.", "system");
      feedbackForm.classList.add("d-none");
      isPaused = true;
      
      // IMPORTANTE: NON chiudere EventSource qui, è ancora necessario per il resume
    });

    es.addEventListener("PauseForFeedback", () => {
      console.log("⏸️ PauseForFeedback ricevuto");
      isPaused = true;
      append("⏳ Pipeline in pausa - attendo modifiche...", "system");
    });

    es.addEventListener("stream_paused", () => {
      console.log("⏸️ Stream in pausa, pannello di editing attivo");
      isPaused = true;
    });

    es.addEventListener("status", e => {
      const status = e.data;
      if (status === "awaiting_feedback") {
        append("⏳ In attesa di modifica/feedback…", "system");
        if (!isWaitingForEdit) { // Mostra form solo se non stiamo aspettando edit
          feedbackForm.classList.remove("d-none");
        }
      }
      console.log(`📊 Status update: ${status}`);
    });

    es.addEventListener("done", () => {
      console.log("🏁 Pipeline completata");
      append("🏁 Pipeline terminata.", "system");
      
      if (!isPaused && !isWaitingForEdit) {
        feedbackForm.classList.remove("d-none");
      }
      
      closeEventSource();
      isPaused = false;
      isWaitingForEdit = false;
    });

    es.addEventListener("error", e => {
      console.error("❌ Errore EventSource:", e);
      append("❌ Errore nella comunicazione", "bot");
    });

    es.onerror = (err) => {
      console.log(`🔌 EventSource error - ReadyState: ${es.readyState}`);
      
      if (es.readyState === EventSource.CLOSED) {
        console.log("EventSource chiuso normalmente");
        return;
      }
      
      console.error("❌ SSE ERROR:", err);
      append("❌ Errore nello streaming", "bot");
    };
  }

  /* ───────────── avvio streaming UNIFICATO ──────────────────────────── */
  function startStreaming() {
    const lore   = loreSelect.value;
    const reset  = resetCheckbox.checked;
    const story  = (lore === "_free_") ? storyTA.value.trim() : null;

    // Validazione input
    if (!lore) {
      append("❗ Devi prima selezionare una lore.", "bot");
      return;
    }
    if (lore === "_free_" && !story) {
      append("❗ Inserisci la tua storia prima di avviare.", "bot");
      return;
    }

    // Reset UI e stato solo se necessario
    if (reset) {
      resetAll();
    }
    
    //append("💬 Inizio/continua pipeline (streaming)…", "system");

    // Costruzione URL - reset solo se esplicitamente richiesto
    const qsStory = story ? `&custom_story=${encodeURIComponent(story)}` : "";
    const url = `/stream?lore=${encodeURIComponent(lore)}&thread_id=${threadId}` +
                (reset ? "&reset=true" : "") + qsStory;

    console.log(`🚀 Apertura stream: ${url}`);
    //closeEventSource(); // Assicura pulizia precedente
    
    source = new EventSource(url);
    attachPipelineListeners(source);
    
    append("🔗 Connessione streaming attiva", "system");
    resetCheckbox.checked = false; // Reset checkbox
  }

  /* ───────────── resume dopo editing - FIXED ────────────────────────── */
  async function resumeAfterEdit(domain, problem) {
    try {
      console.log("🔄 Invio modifiche e resume...");
      
      const response = await fetch("/resume", { //l'endpoint era message
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lore: loreSelect.value,
          thread_id: threadId,
          domain,
          problem
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        append(`❌ Errore: ${data.error}`, "bot");
        return false;
      }

      // CHIAVE: Riapri stream SENZA reset per continuare la pipeline
      const url = `/stream?lore=${encodeURIComponent(loreSelect.value)}&thread_id=${encodeURIComponent(threadId)}`;
      // NON aggiungere &reset=true qui!
      
      //closeEventSource();
      
      source = new EventSource(url);
      attachPipelineListeners(source);
      
      append("💬 Pipeline ripresa dopo modifiche...", "system");
      isPaused = false;
      
      return true;

    } catch (err) {
      console.error("Errore durante resume:", err);
      append("❌ Impossibile riprendere la pipeline", "bot");
      return false;
    }
  }

  /* ───────────── event listeners ──────────────────────────────────────── */
  
  // Avvio pipeline
  runBtn.addEventListener("click", startStreaming);

  // Cambio lore
  loreSelect.addEventListener("change", () => {
    resetAll();
    if (loreSelect.value === "_free_") {
      storyWrap.classList.remove("d-none");
      append("📝 Inserisci la tua storia nel box soprastante.", "system");
    } else {
      storyWrap.classList.add("d-none");
      append(`📘 Lore selezionata: <strong>${loreSelect.value}</strong>`, "system");
    }
  });

  // Feedback testuale
  feedbackForm.addEventListener("submit", async e => {
    e.preventDefault();
    const msg = feedbackInput.value.trim();
    if (!msg) return;

    feedbackForm.classList.add("disabled");
    append(msg, "user");
    feedbackInput.value = "";

    try {
      const res = await fetch("/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          lore: loreSelect.value, 
          thread_id: threadId, 
          message: msg 
        })
      });

      const data = await res.json();
      
      if (data.error) {
        append(`❌ Errore: ${data.error}`, "bot");
      } else {
        append("✅ Feedback ricevuto.", "system");
        feedbackForm.classList.add("d-none");
      }
    } catch (err) {
      console.error("Errore invio feedback:", err);
      append("❌ Errore nell'invio del feedback", "bot");
    } finally {
      feedbackForm.classList.remove("disabled");
    }
  });

  // Invio PDDL modificati - FIXED
  sendEditBtn.addEventListener("click", async () => {
    const domain  = domainTA.value.trim();
    const problem = problemTA.value.trim();
    
    if (!domain || !problem) {
      append("❗ domain/problem non possono essere vuoti", "bot");
      return;
    }

    sendEditBtn.disabled = true;
    append("🚀 Invio PDDL modificati…", "user");

    try {
      const success = await resumeAfterEdit(domain, problem);
      
      if (success) {
        append("✅ PDDL inviati. Pipeline ripresa...", "system");
        hideEditPanel(); // Nasconde pannello dopo successo
      }
    } catch (err) {
      console.error("Errore durante invio edit:", err);
      append("❌ Impossibile inviare le modifiche", "bot");
    } finally {
      sendEditBtn.disabled = false;
    }
  });

  /* ───────────── cleanup e inizializzazione ─────────────────────────── */
  
  // Cleanup alla chiusura della pagina
  window.addEventListener("beforeunload", () => {
    closeEventSource();
  });

  // Inizializzazione UI
  feedbackForm.classList.add("d-none");
  hideEditPanel();
  
  console.log("✅ Pipeline.js inizializzato correttamente - VERSION FIXED");
});