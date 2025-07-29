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
  let isWaitingForEdit = false;
  let currentState = null;
  const allValidations = [];
  const allRefines     = [];
  const generatedFiles = {};
  let reconnectAttempts = 0;
  let maxReconnectAttempts = 3;
  let reconnectDelay = 2000;
  let pipelineActive = false;
  let expectingEvents = false;

  console.log("✅ DOMContentLoaded fired, elementi caricati");

  /* ───────────── helper UI ────────────────────────────────────────────── */  
  function createFileLinksContainer() {
    const container = document.createElement("div");
    container.id = "file-links";
    container.className = "mt-3 p-3 border rounded bg-light";
    container.innerHTML = `
      <h6 class="mb-2">📁 File Generati</h6>
      <div id="file-links-content"></div>
    `;
    
    const rawContainer = rawEl.closest('.card-body') || document.body;
    if (pipelineDetails && pipelineDetails.parentElement) {
      pipelineDetails.parentElement.appendChild(container);
    } else {
      document.body.appendChild(container);
    }
      return container;
  }

  function updateFileLinks(urls = {}) {
    const content = document.getElementById("file-links-content");
    if (!content) return;

    Object.assign(generatedFiles, urls);
    
    let html = "";
    for (const [key, url] of Object.entries(generatedFiles)) {
      if (url) {
        const label = key.replace(/_url$/, '').replace(/_/g, ' ').toUpperCase();
        html += `<a href="${url}" class="btn btn-sm btn-outline-primary me-2 mb-1" target="_blank">
          📄 ${label}
        </a>`;
      }
    }
    
    content.innerHTML = html || "<small class='text-muted'>Nessun file disponibile</small>";
  }

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
    Object.keys(generatedFiles).forEach(key => delete generatedFiles[key]);

    if (validationWrap) validationWrap.innerHTML = "";
    if (refineWrap)     refineWrap.innerHTML     = "";

    updateFileLinks();
    hideEditPanel(); 
    storyWrap.classList.add("d-none");
    feedbackForm.classList.add("d-none");
    isPaused = false;
    isWaitingForEdit = false;
    currentState = null;
    
    closeEventSource();
    append("💬 Pronto per eseguire la pipeline…", "system");
  }

  function showEditPanel(domain = "", problem = "") {
    domainTA.value  = domain;
    problemTA.value = problem;
    editPanel.classList.remove("d-none");
    feedbackForm.classList.add("d-none");
    isWaitingForEdit = true;
    
    setTimeout(() => {
      editPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }
  
  function hideEditPanel() {
    editPanel.classList.add("d-none");
    domainTA.value = problemTA.value = "";
    isWaitingForEdit = false;
    feedbackForm.classList.add("d-none");
  }

  function closeEventSource() {
    if (source) {
      console.log("🔌 Chiudo EventSource - ReadyState:", source.readyState);
      source.close();
      source = null;
      reconnectAttempts = 0;
    }
  }

  function createEventSource(url) {
    console.log(`🔗 Creando EventSource: ${url}`);
    
    if (source) {
      closeEventSource();
    }
    
    source = new EventSource(url);
    
    source.onopen = () => {
      console.log("✅ EventSource connesso");
      reconnectAttempts = 0;
      pipelineActive = true;
    };
    
    source.onerror = (error) => {
      console.error("❌ EventSource error - ReadyState:", source.readyState, error);
      
      if (source.readyState === EventSource.CLOSED) {
        console.log("🔌 EventSource chiuso dal server");
        
        if (expectingEvents && reconnectAttempts < maxReconnectAttempts) {
          console.log(`🔄 Tentativo riconnessione ${reconnectAttempts + 1}/${maxReconnectAttempts}`);
          setTimeout(() => {
            attemptReconnection(url);
          }, reconnectDelay);
        } else if (!expectingEvents) {
          console.log("✅ Chiusura normale - pipeline completata");
          pipelineActive = false;
        } else {
          console.log("❌ Max tentativi riconnessione raggiunti");
          append("❌ Impossibile riconnettersi al server", "system");
          pipelineActive = false;
          expectingEvents = false;
        }
      }
    };
    
    attachPipelineListeners(source);
    return source;
  }
  
  function attemptReconnection(baseUrl) {
    reconnectAttempts++;
    
    const reconnectUrl = baseUrl.includes('resume_after_feedback') 
      ? baseUrl 
      : `${baseUrl}&reconnect=true&attempt=${reconnectAttempts}`;
      
    append(`🔄 Tentativo riconnessione ${reconnectAttempts}...`, "system");
    createEventSource(reconnectUrl);
  }

  /* ───────────── gestione stato pipeline ──────────────────────────────── */
  async function checkPipelineStatus() {
    try {
      const response = await fetch(`/status/${threadId}`);
      if (response.ok) {
        const status = await response.json();
        currentState = status;
        
        if (status.waiting_for_edit) {
          isWaitingForEdit = true;
          isPaused = true;
        }
        
        console.log("📊 Status aggiornato:", status);
        return status;
      }
    } catch (err) {
      console.warn("⚠️ Impossibile verificare stato pipeline:", err);
    }
    return null;
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

  /* ───────────── listeners SSE dinamici ──────────────────── */
  function attachPipelineListeners(es) {
    es.addEventListener("PipelineStarted", e => {
      pipelineActive = true;
      expectingEvents = true;
      append("🚀 Pipeline avviata", "system");
    });

    es.addEventListener("Generate", e => {
      const data = JSON.parse(e.data);
      const { domain, problem, prompt } = data;
      
      if (prompt) {
        promptEl.textContent = prompt;
        append("📝 Prompt generato", "bot");
      }
      rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
      append("🧠 Generazione completata", "bot");
      
      updateFileLinks({
        domain_url: data.domain_url,
        problem_url: data.problem_url,
        raw_response_url: data.raw_response_url
      });
    });

    es.addEventListener("PreparePrompt", e => {
      append("📜 Prompt impostato", "bot");
    });
    
    es.addEventListener("GenerateVision", e => {
      const data = JSON.parse(e.data);
      append("👁️ Vision JSON pronto", "bot");
      
      if (data.vision_url) {
        updateFileLinks({ vision_url: data.vision_url });
      }
    });
    
    es.addEventListener("GenerateSpec", e => {
      const data = JSON.parse(e.data);
      append("📐 Spec JSON pronto", "bot");
      
      if (data.spec_url) {
        updateFileLinks({ spec_url: data.spec_url });
      }
    });

    es.addEventListener("TemplateFallback", e => {
      const { domain, problem } = JSON.parse(e.data);
      rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
      append("🏗️ PDDL generati da template", "bot");
    });

    es.addEventListener("Validate", e => {
      const data = JSON.parse(e.data);
      const { validation } = data;
      allValidations.push(validation);
      renderValidationTimeline();
      append(`📋 Validazione #${allValidations.length} completata`, "bot");
      
      if (data.validation_url) {
        updateFileLinks({ validation_url: data.validation_url });
      }
    });

    es.addEventListener("Refine", e => {
      const data = JSON.parse(e.data);
      const { refined_domain, refined_problem } = data;
      allRefines.push({ domain: refined_domain, problem: refined_problem });
      renderRefineTimeline();
      append(`🔧 Refine #${allRefines.length} completato`, "bot");
      
      updateFileLinks({
        refined_domain_url: data.refined_domain_url,
        refined_problem_url: data.refined_problem_url
      });
    });

    es.addEventListener("ChatFeedback", e => {
      console.log("📨 ChatFeedback ricevuto - pipeline in pausa per editing");
      const data = JSON.parse(e.data);
      
      const domain = data.refined_domain || data.domain || "";
      const problem = data.refined_problem || data.problem || "";
      
      showEditPanel(domain, problem);
      rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
      
      append("✏️ Modifica live disponibile - edita e invia.", "system");
      isPaused = true;
      expectingEvents = true;
      
      updateFileLinks({
        domain_url: data.domain_url,
        problem_url: data.problem_url,
        refined_domain_url: data.refined_domain_url,
        refined_problem_url: data.refined_problem_url
      });
    });

    es.addEventListener("PauseForFeedback", e => {
      console.log("⏸️ PauseForFeedback ricevuto");
      const data = JSON.parse(e.data || "{}");
      isPaused = true;
      append("⏳ Pipeline in pausa - attendo modifiche...", "system");
      
      if (data.domain || data.problem) {
        const domain = data.refined_domain || data.domain || "";
        const problem = data.refined_problem || data.problem || "";
        showEditPanel(domain, problem);
      }
    });

    es.addEventListener("stream_paused", e => {
      console.log("⏸️ Stream in pausa, pannello di editing attivo");
      isPaused = true;
      
      const data = JSON.parse(e.data || "{}");
      if (data.domain || data.problem) {
        const domain = data.refined_domain || data.domain || "";
        const problem = data.refined_problem || data.problem || "";
        showEditPanel(domain, problem);
      }
    });

    es.addEventListener("status_interrupt", e => {
      const data = JSON.parse(e.data);
      console.log("🔄 Status interrupt:", data);
      
      if (data.waiting_for_edit) {
        isWaitingForEdit = true;
        isPaused = true;
        append("⏳ Attendo modifiche dell'utente...", "system");
      }
    });

    es.addEventListener("messages", e => {
      const data = JSON.parse(e.data);
      if (data.message) {
        append(data.message, data.type || "system");
      }
    });

    es.addEventListener("status", e => {
      const status = e.data;
      console.log(`📊 Status update: ${status}`);
      
      if (status === "awaiting_feedback") {
        append("⏳ In attesa di feedback…", "system");
        if (!isWaitingForEdit) {
          feedbackForm.classList.add("d-none");
        }
      } else if (status === "_waiting_for_edit") {
        isWaitingForEdit = true;
        isPaused = true;
        append("✏️ In attesa di modifiche PDDL...", "system");
      } else if (status === "_resume_after_feedback") {
        append("🔄 Ripresa pipeline dopo feedback...", "system");
        isPaused = false;
        isWaitingForEdit = false;
        hideEditPanel();
      }
    });

    es.addEventListener("GeneratePlan", e => {
      const data = JSON.parse(e.data);
      console.log("🎯 GeneratePlan ricevuto:", data);
      
      if (data.status === "success" && data.found_plan) {
        append(`✅ Piano generato con successo!`, "bot");
        append(`📊 Fonte: ${data.source || 'unknown'}`, "system");
        
        showPlanResult(data.plan, data.plan_log);
        
        if (data.plan_url) {
          updateFileLinks({ plan_url: data.plan_url });
        }
      } else if (data.status === "failed") {
        append(`❌ Planning fallito: ${data.error || 'Nessun piano trovato'}`, "bot");
        
        if (data.plan_log) {
          showPlanResult(null, data.plan_log, true);
        }
      }
      expectingEvents = true;
    });

    es.addEventListener("PipelineCompleted", e => {
      const data = JSON.parse(e.data);
      console.log("🏁 PipelineCompleted ricevuto:", data);
      append("🏁 Pipeline completata con successo.", "success");
      
      if (data.plan) {
        showPlanResult(data.plan, null);
        append(`📊 Piano con ${data.plan.split('\n').filter(l => l.trim()).length} azioni`, "system");
      }
      if (data.plan_url) {
        updateFileLinks({ plan_url: data.plan_url });
      }
      
      pipelineActive = false;
      expectingEvents = false;
      isPaused = false;
      isWaitingForEdit = false;
      
      setTimeout(() => {
        if (source && source.readyState === EventSource.OPEN) {
          console.log("⏰ Timeout post-completamento, chiusura stream");
          closeEventSource();
        }
      }, 3000);
    });

    es.addEventListener("done", () => {
      console.log("🏁 Evento 'done' ricevuto");
      append("🏁 Pipeline terminata.", "system");

      pipelineActive = false;
      expectingEvents = false;
      
      if (!isPaused && !isWaitingForEdit) {
        feedbackForm.classList.add("d-none");
      }
      
      setTimeout(() => closeEventSource(), 1000);
      
      isPaused = false;
      isWaitingForEdit = false;
      currentState = { ...(currentState || {}), _done_received: true };
    });

    es.addEventListener("stream_complete", e => {
      console.log("🎌 Stream completato definitivamente");
      append("🎌 Streaming completato.", "system");
      closeEventSource();
    });

    es.onerror = (error) => {
      console.error("❌ EventSource error - ReadyState:", source.readyState, error);
      
      if (source.readyState === EventSource.CLOSED) {
        console.log("🔌 EventSource chiuso dal server");
        
        if (expectingEvents && reconnectAttempts < maxReconnectAttempts) {
          console.log(`🔄 Tentativo riconnessione ${reconnectAttempts + 1}/${maxReconnectAttempts}`);
          setTimeout(() => {
            attemptReconnection(url);
          }, reconnectDelay);
        } else if (!expectingEvents) {
          console.log("✅ Chiusura normale - pipeline completata");
          pipelineActive = false;
        } else {
          console.log("❌ Max tentativi riconnessione raggiunti");
          append("❌ Impossibile riconnettersi al server", "system");
          pipelineActive = false;
          expectingEvents = false;
        }
      }
    };
  }

  /* ───────────── avvio streaming UNIFICATO ──────────────────────────── */
  async function startStreaming() {
    const lore   = loreSelect.value;
    const reset  = resetCheckbox.checked;
    const story  = (lore === "_free_") ? storyTA.value.trim() : null;

    if (!lore) {
      append("❗ Devi prima selezionare una lore.", "bot");
      return;
    }
    if (lore === "_free_" && !story) {
      append("❗ Inserisci la tua storia prima di avviare.", "bot");
      return;
    }
    if (reset) {
      resetAll();
    }

    const qsStory = story ? `&custom_story=${encodeURIComponent(story)}` : "";
    const resetParam = reset ? "&reset=true" : "";
    const url = `/stream?lore=${encodeURIComponent(lore)}&thread_id=${threadId}${resetParam}${qsStory}`;

    console.log(`🚀 Apertura stream: ${url}`);
    
    if (source) {
      closeEventSource();
    }
    
    expectingEvents = true;
    pipelineActive = true;
    createEventSource(url);
    
    append("🔗 Connessione streaming attiva", "system");
    resetCheckbox.checked = false;
  }

  /* ───────────── feedback PDDL - AGGIORNATO ──────────────────────────── */
  async function sendFeedback(domain, problem, message = "") {
    try {
      console.log("🔄 Invio feedback PDDL...");
      
      const payload = {
        lore: loreSelect.value,
        thread_id: threadId,
        domain,
        problem
      };
      
      if (message.trim()) {
        payload.message = message.trim();
      }
      
      const response = await fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        append(`❌ Errore: ${data.error}`, "bot");
        return false;
      }

      if (data.response) {
        append(`🤖 ${data.response}`, "bot");
      }

      if (data.refined_domain && data.refined_problem) {
        rawEl.textContent = `=== DOMAIN ===\n${data.refined_domain}\n\n=== PROBLEM ===\n${data.refined_problem}`;
        append("🔧 PDDL raffinati ricevuti", "system");
      }

      if (data.validation) {
        allValidations.push(data.validation);
        renderValidationTimeline();
        append("📋 Validazione aggiornata", "system");
      }

      updateFileLinks({
        domain_url: data.domain_url,
        problem_url: data.problem_url,
        refined_domain_url: data.refined_domain_url,
        refined_problem_url: data.refined_problem_url,
        validation_url: data.validation_url
      });

      append("✅ Feedback inviato con successo", "system");
      
      hideEditPanel();
      isPaused = false;
      isWaitingForEdit = false;

      expectingEvents = true;

      if (!source || source.readyState === EventSource.CLOSED) {
        console.log("🔄 EventSource non attivo dopo feedback, riconnessione...");
        append("🔌 Riconnessione stream per eventi finali...", "system");
        
        const resumeUrl = `/stream?lore=${encodeURIComponent(loreSelect.value)}&thread_id=${threadId}&resume_after_feedback=true`;
        createEventSource(resumeUrl);
      } else {
        console.log("📡 EventSource attivo, attesa eventi finali...");
        append("⏳ Attesa completamento pipeline...", "system");
      }
      
      return true;

    } catch (err) {
      console.error("Errore durante invio feedback:", err);
      append("❌ Impossibile inviare il feedback", "bot");
      return false;
    }
  }

  /* ───────────── resume stream dopo feedback ─────────────────────────── */
  async function resumeStream() {
  try {
    console.log("🔄 Ripresa stream dopo feedback...");
    
    if (source && source.readyState !== EventSource.CONNECTING) {
      console.log("🔌 Chiusura stream precedente...");
      closeEventSource();
    }
    
    const url = `/stream?lore=${encodeURIComponent(loreSelect.value)}&thread_id=${encodeURIComponent(threadId)}&resume_after_feedback=true`;
    
    console.log(`🚀 Riapertura stream: ${url}`);
    source = new EventSource(url);
    attachPipelineListeners(source);
    
    append("💫 Stream ripreso, continuando pipeline...", "system");
    
    setTimeout(() => {
      if (source && source.readyState === EventSource.OPEN && !isPaused) {
        console.log("⏰ Timeout sicurezza - controllo stato pipeline...");
        checkFinalPipelineStatus();
      }
    }, 30000); // 30 secondi
    
  } catch (err) {
    console.error("Errore durante resume stream:", err);
    append("❌ Impossibile riprendere lo stream", "bot");
  }
}

  /* ───────────── event listeners ──────────────────────────────────────── */
  
  runBtn.addEventListener("click", startStreaming);

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
        if (data.response) {
          append(`🤖 ${data.response}`, "bot");
        }
        append("✅ Feedback ricevuto.", "system");
        
        if (data.waiting_for_edit && (data.domain || data.problem)) {
          showEditPanel(data.domain || "", data.problem || "");
        } else {
          feedbackForm.classList.add("d-none");
        }
      }
    } catch (err) {
      console.error("Errore invio feedback:", err);
      append("❌ Errore nell'invio del feedback", "bot");
    } finally {
      feedbackForm.classList.remove("disabled");
    }
  });

  sendEditBtn.addEventListener("click", async () => {
    const domain  = domainTA.value.trim();
    const problem = problemTA.value.trim();
    const message = feedbackInput.value.trim();
    
    if (!domain || !problem) {
      append("❗ Domain e problem non possono essere vuoti", "bot");
      return;
    }

    sendEditBtn.disabled = true;
    append("🚀 Invio PDDL modificati…", "user");

    try {
      const success = await sendFeedback(domain, problem, message);
      
      if (success) {
        append("✅ PDDL inviati. Pipeline ripresa...", "system");
        feedbackInput.value = "";
      }
    } catch (err) {
      console.error("Errore durante invio edit:", err);
      append("❌ Impossibile inviare le modifiche", "bot");
    } finally {
      sendEditBtn.disabled = false;
    }
  });

  /* ───────────── gestione piano generato ────────────────────────────── */
  function showPlanResult(plan, log, isError = false) {
    let planAccordion = document.getElementById("collapsePlan");
    
    if (!planAccordion) {
      const pipelineDetails = document.getElementById("pipeline-details");
      if (pipelineDetails) {
        const planItem = document.createElement("div");
        planItem.className = "accordion-item";
        planItem.innerHTML = `
          <h2 class="accordion-header" id="headingPlan">
            <button class="accordion-button collapsed" type="button"
                    data-bs-toggle="collapse" data-bs-target="#collapsePlan"
                    aria-expanded="false" aria-controls="collapsePlan">
              🎯 Piano Generato
            </button>
          </h2>
          <div id="collapsePlan" class="accordion-collapse collapse"
              aria-labelledby="headingPlan" data-bs-parent="#pipeline-details">
            <div class="accordion-body p-0">
              <div id="plan-content" class="m-3"></div>
            </div>
          </div>`;
        
        pipelineDetails.appendChild(planItem);
        planAccordion = document.getElementById("collapsePlan");
      }
    }
    
    const planContent = document.getElementById("plan-content");
    if (planContent) {
      let html = "";
      
      if (plan && !isError) {
        html += `
          <div class="alert alert-success">
            <h6 class="alert-heading">✅ Piano trovato!</h6>
          </div>
          <h6 class="text-success mb-2">📋 Actions:</h6>
          <pre class="bg-light p-3 border rounded">${escapeHtml(plan)}</pre>
        `;
      } else if (isError) {
        html += `
          <div class="alert alert-danger">
            <h6 class="alert-heading">❌ Planning fallito</h6>
          </div>
        `;
      }
      
      if (log) {
        html += `
          <h6 class="text-muted mt-3 mb-2">📄 Log Fast-Downward:</h6>
          <pre class="small bg-light p-2 border rounded" style="max-height: 300px; overflow-y: auto;">${escapeHtml(log)}</pre>
        `;
      }
      
      planContent.innerHTML = html;
      
      if (planAccordion && planAccordion.classList.contains("collapse")) {
        const bsCollapse = new bootstrap.Collapse(planAccordion, { show: true });
      }
    }
  }

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function checkFinalPipelineStatus() {
  try {
    const response = await fetch(`/status/${threadId}`);
    if (response.ok) {
      const status = await response.json();
      console.log("📊 Status finale controllo:", status);
      
      if (status.completed && !currentState?._pipeline_completed) {
        append("🏁 Pipeline completata (da controllo status).", "system");
        
        if (status.plan) {
          showPlanResult(status.plan, status.plan_log);
        }
        
        if (status.plan_url) {
          updateFileLinks({ plan_url: status.plan_url });
        }
        
        closeEventSource();
      }
    }
  } catch (err) {
    console.warn("⚠️ Errore controllo status finale:", err);
  }
}

  /* ───────────── cleanup e inizializzazione ─────────────────────────── */
  
  window.addEventListener("beforeunload", () => {
    expectingEvents = false;
    pipelineActive = false;
    closeEventSource();
  });

  feedbackForm.classList.add("d-none");
  hideEditPanel();
  updateFileLinks();
  
  console.log("✅ Pipeline.js inizializzato - VERSIONE EVENTSOURCE ROBUSTA");
});