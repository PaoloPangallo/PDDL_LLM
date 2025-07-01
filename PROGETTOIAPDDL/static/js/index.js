document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("loadingModal");
  const loadingMessage = document.getElementById("loadingMessage");
  const audioSuccess = document.getElementById("successSound");
  const audioError = document.getElementById("errorSound");
  const resultBox = document.getElementById("pipeline-result");
  const feedbackBox = document.getElementById("json-feedback");

  const stepElements = [
    document.getElementById("step-0"),
    document.getElementById("step-1"),
    document.getElementById("step-2"),
    document.getElementById("step-3")
  ];
  const progressFill = document.getElementById("progressFill");
  const progressBar = document.querySelector(".progress-bar");

  const phases = [
    { text: "📜 Lettura lore...", value: 25 },
    { text: "⚙️ Generazione PDDL...", value: 50 },
    { text: "🧪 Validazione sintattico-semantica...", value: 75 },
    { text: "🏑 Esecuzione planner...", value: 100 }
  ];

  let phraseInterval;

  function updateStep(index) {
    loadingMessage.textContent = phases[index].text;
    progressBar?.setAttribute("aria-valuenow", phases[index].value);
    progressFill.style.width = `${phases[index].value}%`;
    stepElements.forEach(el => el?.classList.remove("active-step"));
    stepElements[index]?.classList.add("active-step");
  }

  function startPhraseRotation() {
    if (!loadingMessage || !progressFill || !stepElements.length) return;
    let index = 0;
    updateStep(index);
    phraseInterval = setInterval(() => {
      index++;
      if (index >= phases.length) {
        clearInterval(phraseInterval);
        return;
      }
      updateStep(index);
    }, 2000);
  }

  function showModal() {
    modal?.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    modal.style.display = "flex";
    startPhraseRotation();
  }

  function hideModal() {
    modal?.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
    modal.style.display = "none";
    clearInterval(phraseInterval);
  }

  function playSuccessSound() {
    audioSuccess?.play().catch(err => console.warn("🔇 Audio successo bloccato:", err));
  }

  function playErrorSound() {
    audioError?.play().catch(err => console.warn("🔇 Audio errore bloccato:", err));
  }

  // ⏳ Show loading for all non-pipeline forms
  document.querySelectorAll("form").forEach(form => {
    if (form.id === "pipeline-form") return;
    form.addEventListener("submit", async () => {
      const button = form.querySelector("button[type='submit']");
      if (button) {
        button.disabled = true;
        button.textContent = "⏳ Attendere...";
        button.style.opacity = 0.6;
      }
      showModal();
      await new Promise(resolve => setTimeout(resolve, 100));
    });
  });

  // 🚀 Pipeline form con select lore_path
  const pipelineForm = document.getElementById("pipeline-form");
  if (pipelineForm) {
    pipelineForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const select = document.getElementById("lore_path_select");
      const selectedPath = select?.value;
      const submitBtn = pipelineForm.querySelector("button[type='submit']");

      if (!selectedPath) {
        feedbackBox.textContent = "❌ Seleziona un file lore valido.";
        select.classList.add("input-error");
        playErrorSound();
        return;
      }

      select.classList.remove("input-error");
      feedbackBox.textContent = "";
      showModal();

      pipelineForm.querySelectorAll("select, button").forEach(el => el.disabled = true);

      try {
        const response = await fetch("/api/pipeline/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lore_path: selectedPath })
        });

        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
          ? await response.json()
          : { error: "Risposta non in formato JSON." };

        resultBox.innerHTML = renderPipelineResult(data);
        if (data.error) playErrorSound();
        else playSuccessSound();
      } catch (err) {
        resultBox.innerHTML = `<p>⚠️ Errore di rete: ${err.message}</p>`;
        playErrorSound();
      }

      pipelineForm.querySelectorAll("select, button").forEach(el => el.disabled = false);
      submitBtn.textContent = "🚀 Esegui Pipeline";
      submitBtn.style.opacity = 1;
      hideModal();
      resultBox.classList.remove("hidden");
      resultBox.scrollIntoView({ behavior: "smooth" });
    });
  }

  // 🔽 Carica menu a tendina lore_path (per pipeline)
  fetch("/api/lore_titles")
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById("lore_path_select") || document.getElementById("lore_path");
      if (!select) return;
      select.innerHTML = "";
      if (data.length === 0) {
        const option = document.createElement("option");
        option.disabled = true;
        option.textContent = "❌ Nessun file lore trovato.";
        select.appendChild(option);
        return;
      }
      data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.filename;
        option.textContent = item.title;
        select.appendChild(option);
      });
    })
    .catch(err => {
      console.error("Errore nel caricamento lore:", err);
      const select = document.getElementById("lore_path_select");
      if (select) {
        select.innerHTML = '<option disabled>⚠️ Errore nel caricamento</option>';
      }
    });

  function renderPipelineResult(data) {
    if (!data || data.error) return `<div class="result-card"><p>❌ Errore: ${data.error || "Errore sconosciuto"}</p></div>`;

    let html = `<div class="result-card">`;

    html += `<h3>✅ <strong>Dominio generato:</strong></h3>
             <pre class="code-box">${data.domain?.slice(0, 3000) || "(vuoto)"}</pre>`;

    html += `<h3>✅ <strong>Problema generato:</strong></h3>
             <pre class="code-box">${data.problem?.slice(0, 3000) || "(vuoto)"}</pre>`;

    html += `<p>🗂️ <strong>Sessione:</strong> <code>uploads/${data.session_id}</code></p>`;
    if (data.refined) html += `<p>🔁 Raffinamento eseguito!</p>`;

    const v = data.validation;
    if (v) {
      html += `<hr><h3>🧪 <strong>Report di Validazione</strong></h3><ul>`;
      if (!v.valid_syntax)
        html += `<li style="color:red;">❌ Errori di sintassi. Sezioni mancanti: ${v.missing_sections.map(s => `<code>${s}</code>`).join(", ")}</li>`;
      if (v.undefined_objects_in_goal?.length)
        html += `<li style="color:darkred;">🎯 Oggetti non definiti nel goal: ${v.undefined_objects_in_goal.map(o => `<code>${o}</code>`).join(", ")}</li>`;
      if (v.undefined_actions?.length)
        html += `<li style="color:orange;">⚠️ Azioni non definite usate nel piano: ${v.undefined_actions.map(a => `<code>${a}</code>`).join(", ")}</li>`;
      if (v.mismatched_lore_entities?.length)
        html += `<li style="color:darkmagenta;">🔍 Entità nel lore ma non negli oggetti: ${v.mismatched_lore_entities.map(e => `<code>${e}</code>`).join(", ")}</li>`;
      if (v.semantic_errors?.length)
        html += `<li style="color:blue;">⚠️ Errori semantici: ${v.semantic_errors.map(e => `<code>${e}</code>`).join(", ")}</li>`;
      html += `</ul>`;

      html += `<details style="margin-top:1em;">
                 <summary>📋 Visualizza JSON completo</summary>
                 <pre class="code-box">${JSON.stringify(v, null, 2)}</pre>
               </details>`;
    }

    html += `</div>`;
    return html;
  }

  // ------------------------
  // CHATBOT INTEGRATION
  // ------------------------
 // CHATBOT INTEGRATION
const chatbotOutput = document.getElementById('chatbot-output');
const chatbotInput = document.getElementById('chatbot-input');
const chatbotSend = document.getElementById('chatbot-send');

if (chatbotSend && chatbotInput && chatbotOutput) {
  chatbotSend.addEventListener('click', async () => {
    const userMessage = chatbotInput.value.trim();
    if (!userMessage) return;

    // Mostra messaggio utente
    chatbotOutput.innerHTML += `<div class="chat-bubble user">${userMessage}</div>`;
    chatbotInput.value = '';
    chatbotOutput.scrollTop = chatbotOutput.scrollHeight;

    try {
      const res = await fetch('/api/chatbot/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });

      const data = await res.json();
      const responses = data.responses || [data.reply] || ["❌ Nessuna risposta ricevuta."];

      responses.forEach(r => {
        chatbotOutput.innerHTML += `<div class="chat-bubble assistant">${r}</div>`;
      });

      chatbotOutput.scrollTop = chatbotOutput.scrollHeight;
    } catch (error) {
      chatbotOutput.innerHTML += `<div class="chat-bubble error">❌ Errore di comunicazione con il bot.</div>`;
    }
  });

  chatbotInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      chatbotSend.click();
    }
  });
}

})
