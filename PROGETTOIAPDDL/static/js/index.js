document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("loadingModal");
  const modalText = modal.querySelector("p");
  const audio = document.getElementById("successSound");

  const phrases = [
    "🧩 Sto ragionando sul piano...",
    "🔎 Validazione in corso...",
    "📜 Elaborazione lore in atto...",
    "⚙️ Costruzione dominio e problema...",
    "🧠 Consulto la mia memoria logica..."
  ];

  let phraseInterval;

  function startPhraseRotation() {
    if (!modalText) return;
    modalText.textContent = phrases[0];
    let index = 1;
    phraseInterval = setInterval(() => {
      modalText.textContent = phrases[index % phrases.length];
      index++;
    }, 2000);
  }

  function stopPhraseRotation() {
    clearInterval(phraseInterval);
  }

  function playSuccessSound() {
    if (audio) {
      audio.play().catch(err => console.warn("Audio playback blocked:", err));
    }
  }

  // Mostra modal e disabilita bottone per tutti i form tranne #pipeline-form
  document.querySelectorAll("form").forEach(form => {
    if (form.id === "pipeline-form") return;

    form.addEventListener("submit", function () {
      const button = form.querySelector("button[type='submit']");
      if (button) {
        button.disabled = true;
        button.textContent = "⏳ Attendere...";
        button.style.opacity = 0.6;
      }
      modal.classList.remove("hidden");
      modal.style.display = "flex";
      startPhraseRotation();
    });
  });

  // Gestione LangGraph pipeline (fetch)
  const pipelineForm = document.getElementById("pipeline-form");
  const resultBox = document.getElementById("pipeline-result");

  if (pipelineForm) {
    pipelineForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const loreText = document.getElementById("lore-json").value.trim();
      const submitBtn = pipelineForm.querySelector("button[type='submit']");

      // Validazione JSON
      let jsonPayload;
      try {
        jsonPayload = JSON.parse(loreText);
      } catch (err) {
        resultBox.innerHTML = `<p>⚠️ <strong>JSON non valido:</strong> ${err.message}</p>`;
        resultBox.classList.remove("hidden");
        return;
      }

      // Mostra modale
      modal.classList.remove("hidden");
      modal.style.display = "flex";
      startPhraseRotation();

      // Disabilita bottone
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "⏳ Attendere...";
        submitBtn.style.opacity = 0.6;
      }

      try {
        const response = await fetch("/api/pipeline/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(jsonPayload)
        });

        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
          ? await response.json()
          : { error: "Risposta non in formato JSON." };

        if (response.ok) {
          let html = `
            <p>✅ <strong>Dominio generato:</strong></p>
            <pre>${data.domain?.slice(0, 1000) || "(vuoto)"}</pre>
            <p>✅ <strong>Problema generato:</strong></p>
            <pre>${data.problem?.slice(0, 1000) || "(vuoto)"}</pre>
            <p>🗂️ <strong>Sessione:</strong> <code>uploads/${data.session_id}</code></p>
            ${data.refined ? "<p>🔁 Raffinamento eseguito!</p>" : ""}
          `;

          const validation = data.validation;

          if (validation) {
            html += `<hr><h3 style="color:#333;">🧪 <strong>Report di Validazione</strong></h3>`;

            if (!validation.valid_syntax) {
              html += `
                <h4 style="color:red;">❌ Errori di Sintassi</h4>
                <ul>${validation.missing_sections.map(s => `<li>Sezione mancante: <code>${s}</code></li>`).join("")}</ul>`;
            }

            if (validation.undefined_objects_in_goal?.length > 0) {
              html += `
                <h4 style="color:darkred;">🚫 Oggetti non definiti nel goal</h4>
                <ul>${validation.undefined_objects_in_goal.map(obj => `<li><code>${obj}</code></li>`).join("")}</ul>`;
            }

            if (validation.undefined_actions?.length > 0) {
              html += `
                <h4 style="color:darkorange;">⚠️ Azioni non definite usate nel piano</h4>
                <ul>${validation.undefined_actions.map(a => `<li><code>${a}</code></li>`).join("")}</ul>`;
            }

            if (validation.mismatched_lore_entities?.length > 0) {
              html += `
                <h4 style="color:darkmagenta;">🔍 Entità presenti nel lore ma non negli oggetti</h4>
                <ul>${validation.mismatched_lore_entities.map(e => `<li><code>${e}</code></li>`).join("")}</ul>`;
            }

            if (validation.semantic_errors?.length > 0) {
              html += `
                <h4 style="color:orange;">⚠️ Errori Semantici</h4>
                <ul>${validation.semantic_errors.map(err => `<li>${err}</li>`).join("")}</ul>`;
            }

            html += `
              <details style="margin-top:1em;">
                <summary>📋 Visualizza JSON completo</summary>
                <pre>${JSON.stringify(validation, null, 2)}</pre>
              </details>`;
          }

          resultBox.innerHTML = html;
        } else {
          resultBox.innerHTML = `<p>❌ Errore: ${data.error || "Errore sconosciuto"}</p>`;
        }

      } catch (err) {
        resultBox.innerHTML = `<p>⚠️ Errore di rete: ${err.message}</p>`;
      }

      // Ripristina bottone
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "🚀 Esegui Pipeline";
        submitBtn.style.opacity = 1;
      }

      // Ferma animazione, suona, mostra risultato
      stopPhraseRotation();
      playSuccessSound();
      modal.classList.add("hidden");
      modal.style.display = "none";
      resultBox.classList.remove("hidden");
    });
  }
});
