// static/js/pipeline.js
document.addEventListener("DOMContentLoaded", () => {
  const loreSelect = document.getElementById("lore-select");
  const runBtn     = document.getElementById("run-from-scratch");
  const chatLog    = document.getElementById("chat-log");
  const promptEl   = document.getElementById("prompt-content");
  const rawEl      = document.getElementById("raw-content");
  const valEl      = document.getElementById("validation-content");
  const refineEl   = document.getElementById("refine-content");
  const form       = document.getElementById("chatbot-form");
  const input      = document.getElementById("user-input");
  const resetCheckbox = document.getElementById("reset-checkbox");


  let source = null;
  const threadId = "session-1";

  function append(text, cls = "system") {
    const d = document.createElement("div");
    d.className = `chat-message ${cls}`;
    d.innerHTML = text;
    chatLog.appendChild(d);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function resetAll() {
    chatLog.innerHTML    = "";
    promptEl.textContent = "";
    rawEl.textContent    = "";
    valEl.textContent    = "";
    refineEl.textContent = "";
    append("💬 Pronto per eseguire la pipeline…", "system");
    form.classList.add("d-none");
  }

  form.classList.add("d-none");

  loreSelect.addEventListener("change", () => {
    resetAll();
    append(`📘 Lore selezionata: <strong>${loreSelect.value}</strong>`, "system");
  });

  function attachPipelineListeners(source) {
  const allValidations = [];
  const allRefines = [];

  source.addEventListener("BuildPrompt", e => {
    const { prompt } = JSON.parse(e.data);
    promptEl.textContent = prompt;
    append("📝 Prompt generato", "bot");
  });

  source.addEventListener("Generate", e => {
    const { domain, problem } = JSON.parse(e.data);
    rawEl.textContent = `=== DOMAIN ===\n${domain}\n\n=== PROBLEM ===\n${problem}`;
    append("🧠 Generazione completata", "bot");
  });

  source.addEventListener("Validate", e => {
    const { validation } = JSON.parse(e.data);
    allValidations.push(validation);
    valEl.textContent = JSON.stringify(validation, null, 2);
    append(`📋 Validazione #${allValidations.length} completata`, "bot");
    renderValidationTimeline(allValidations);
  });

  source.addEventListener("Refine", e => {
    const { refined_domain, refined_problem } = JSON.parse(e.data);
    allRefines.push({ domain: refined_domain, problem: refined_problem });
    refineEl.textContent = 
      `=== DOMAIN REFINED ===\n${refined_domain}\n\n=== PROBLEM REFINED ===\n${refined_problem}`;
    append(`🔧 Refine #${allRefines.length} completato`, "bot");
    renderRefineTimeline(allRefines);
  });

  source.addEventListener("messages", e => {
    const msgs = JSON.parse(e.data);
    if (Array.isArray(msgs)) {
      msgs.forEach(m => {
        if (m.type === "ai" && m.content) {
          append(m.content, "bot");
        }
      });
    }
  });


  function renderValidationTimeline(validations) {
  const container = document.getElementById("validation-timeline");
  container.innerHTML = "";
  validations.forEach((val, idx) => {
    const item = document.createElement("div");
    item.className = "accordion-item";
    item.innerHTML = `
      <h2 class="accordion-header" id="valHead${idx}">
        <button class="accordion-button ${idx > 0 ? 'collapsed' : ''}" type="button"
                data-bs-toggle="collapse" data-bs-target="#valCollapse${idx}"
                aria-expanded="${idx === 0}" aria-controls="valCollapse${idx}">
          🔍 Validation #${idx + 1}
        </button>
      </h2>
      <div id="valCollapse${idx}" class="accordion-collapse collapse ${idx === 0 ? 'show' : ''}"
           aria-labelledby="valHead${idx}">
        <div class="accordion-body">
          <pre>${JSON.stringify(val, null, 2)}</pre>
        </div>
      </div>
    `;
    container.appendChild(item);
  });
}

function renderRefineTimeline(refines) {
  const container = document.getElementById("refine-timeline");
  container.innerHTML = "";
  refines.forEach((r, idx) => {
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
      </div>
    `;
    container.appendChild(col);
  });
}


  source.addEventListener("status", e => {
    const status = e.data;
    if (status === "awaiting_feedback") {
      append("🙋 La pipeline è in attesa di un tuo feedback.", "system");
      form.classList.remove("d-none");
      source.close();
    }
  });

  source.addEventListener("done", () => {
    append("🏁 Pipeline terminata. Ora puoi inviare un feedback.", "system");
    form.classList.remove("d-none");
    source.close();
  });

  source.onerror = err => {
    console.error("❌ SSE ERROR", err);
    append("❌ Errore nello streaming", "bot");
    source.close();
  };
}


function startStreaming() {
  const lore = loreSelect.value;
  const reset = resetCheckbox.checked;

  if (!lore) {
    append("❗ Devi prima selezionare una lore.", "bot");
    return;
  }

  resetAll();
  append("💬 Inizio pipeline (streaming)…", "system");

  // Se è richiesto il reset, faccio prima una POST a /message per cancellare la memoria
  if (reset) {
    append("♻️ Reset richiesto. Ripartiamo da zero…", "system");

    fetch("/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lore, thread_id: threadId, reset: true })
    })
    .then(() => {
      // Dopo il reset, avvia il flusso SSE
      if (source) source.close();
      source = new EventSource(`/stream?lore=${encodeURIComponent(lore)}&thread_id=${threadId}&reset=true`);
      attachPipelineListeners(source);
      resetCheckbox.checked = false;
    })
    .catch(err => {
      console.error("❌ Errore durante il reset", err);
      append("❌ Errore durante il reset della sessione", "bot");
    });

  } else {
    // Nessun reset: avvia subito il flusso SSE
    if (source) source.close();
    source = new EventSource(`/stream?lore=${encodeURIComponent(lore)}&thread_id=${threadId}`);
    attachPipelineListeners(source);
  }
}


  runBtn.addEventListener("click", startStreaming);


  form.addEventListener("submit", async e => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;

  form.classList.add("disabled");
  append(msg, "user");
  input.value = "";

  const lore = loreSelect.value;
  const reset = resetCheckbox.checked;

  const res = await fetch("/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lore, thread_id: threadId, message: msg, reset })
  });

  form.classList.remove("disabled");
  resetCheckbox.checked = false;

  const data = await res.json();

  if (data.error) {
    append(`❌ Errore: ${data.error}`, "bot");
    return;
  }

  if (data.refined_domain) {
    append("🔧 Nuovo domain.pddl:", "bot");
    append(`<pre>${data.refined_domain}</pre>`);
  }
  if (data.refined_problem) {
    append("🔧 Nuovo problem.pddl:", "bot");
    append(`<pre>${data.refined_problem}</pre>`);
  }

  append("✅ Feedback ricevuto. La pipeline è terminata correttamente.", "system");
  form.classList.add("d-none");
}); 
})