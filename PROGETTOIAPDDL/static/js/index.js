document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("loadingModal");

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
          resultBox.innerHTML = `
            <p>✅ <strong>Dominio generato:</strong></p>
            <pre>${data.domain?.slice(0, 1000) || "(vuoto)"}</pre>
            <p>✅ <strong>Problema generato:</strong></p>
            <pre>${data.problem?.slice(0, 1000) || "(vuoto)"}</pre>
            <p>🗂️ <strong>Sessione:</strong> <code>uploads/${data.session_id}</code></p>
            ${data.refined ? "<p>🔁 Raffinamento eseguito!</p>" : ""}
          `;
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

      // Nascondi modal e mostra risultato
      modal.classList.add("hidden");
      modal.style.display = "none";
      resultBox.classList.remove("hidden");
    });
  }
});
