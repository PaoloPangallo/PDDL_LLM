document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("loadingModal");
  const modalText = modal && modal.querySelector("p");
  const audio = document.getElementById("successSound");
  const pipelineForm = document.getElementById("pipeline-form");
  const resultBox = document.getElementById("pipeline-result");
  const loreSelect = document.getElementById("lore_path");

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
      audio.play().catch(err => console.warn("🔇 Audio blocked:", err));
    }
  }

  // Popola il select delle lore
  if (loreSelect) {
    fetch("/api/lore_titles")
      .then(res => res.json())
      .then(data => {
        loreSelect.innerHTML = "<option value=''>📘 Seleziona una storia</option>";
        data.forEach(item => {
          const opt = document.createElement("option");
          opt.value = item.filename;
          opt.textContent = item.title;
          loreSelect.appendChild(opt);
        });
      })
      .catch(err => {
        console.error("Errore nel caricamento titoli:", err);
        loreSelect.innerHTML = "<option disabled>⚠️ Errore nel caricamento</option>";
      });
  }

  // Gestione submit del form
  if (pipelineForm) {
    pipelineForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const selectedPath = loreSelect && loreSelect.value.trim();
      if (!selectedPath) {
        resultBox.innerHTML = `<p>⚠️ <strong>Seleziona una storia</strong></p>`;
        resultBox.classList.remove("hidden");
        return;
      }

      const submitBtn = pipelineForm.querySelector("button[type='submit']");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "⏳ Attendere...";
        submitBtn.style.opacity = 0.6;
      }
      if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
      }
      startPhraseRotation();

      try {
        const response = await fetch("/api/pipeline/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lore_path: selectedPath })
        });

        const data = response.headers.get("content-type")?.includes("application/json")
          ? await response.json()
          : { error: "Risposta non in JSON." };

        if (response.ok) {
          // Destrutturazione con fallback
          const {
            missing_sections = [],
            undefined_objects_in_goal = [],
            undefined_actions = [],
            mismatched_lore_entities = [],
            semantic_errors = []
          } = (data.validation || {});

          let html = `
            <p>✅ <strong>Dominio generato:</strong></p>
            <pre>${data.domain?.slice(0, 1000) || "(vuoto)"}</pre>
            <p>✅ <strong>Problema generato:</strong></p>
            <pre>${data.problem?.slice(0, 1000) || "(vuoto)"}</pre>
            <p>🗂️ <strong>Sessione:</strong> <code>uploads/${data.session_id}</code></p>
            ${data.refined ? "<p>🔁 Raffinamento eseguito!</p>" : ""}
          `;

          if (data.validation) {
            html += `<hr><h3>🧪 <strong>Report di Validazione</strong></h3>`;

            if (!data.validation.valid_syntax) {
              html += `<h4 style="color:red;">❌ Errori di Sintassi</h4><ul>`
                + missing_sections.map(s => `<li><code>${s}</code></li>`).join("")
                + `</ul>`;
            }
            if (undefined_objects_in_goal.length) {
              html += `<h4>🚫 Oggetti non definiti nel goal</h4><ul>`
                + undefined_objects_in_goal.map(o => `<li><code>${o}</code></li>`).join("")
                + `</ul>`;
            }
            if (undefined_actions.length) {
              html += `<h4>⚠️ Azioni non definite usate</h4><ul>`
                + undefined_actions.map(a => `<li><code>${a}</code></li>`).join("")
                + `</ul>`;
            }
            if (mismatched_lore_entities.length) {
              html += `<h4>🔍 Entità lore non in oggetti</h4><ul>`
                + mismatched_lore_entities.map(x => `<li><code>${x}</code></li>`).join("")
                + `</ul>`;
            }
            if (semantic_errors.length) {
              html += `<h4>⚠️ Errori Semantici</h4><ul>`
                + semantic_errors.map(err => `<li>${err}</li>`).join("")
                + `</ul>`;
            }

            html += `<details style="margin-top:1em;"><summary>📋 JSON completo</summary><pre>`
              + JSON.stringify(data.validation, null, 2)
              + `</pre></details>`;
          }

          resultBox.innerHTML = html;
        } else {
          resultBox.innerHTML = `<p>❌ Errore: ${data.error}</p>`;
        }
      } catch (err) {
        resultBox.innerHTML = `<p>⚠️ Errore di rete: ${err.message}</p>`;
      } finally {
        stopPhraseRotation();
        playSuccessSound();
        if (modal) {
          modal.classList.add("hidden");
          modal.style.display = "none";
        }
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "🚀 Esegui Pipeline";
          submitBtn.style.opacity = 1;
        }
        resultBox.classList.remove("hidden");
      }
    });
  }
});
