import { showModal, hideModal, playSuccessSound, playErrorSound } from "./utils.js";

const API_ENDPOINT = "/api/pipeline/run";
const MAX_PREVIEW_LENGTH = 3000;
const PROGRESS_INTERVAL_MS = 2000;
const STEPS = [
  "📜 Lettura lore...",
  "⚙️ Generazione PDDL...",
  "🧪 Validazione sintattico-semantica...",
  "🏁 Esecuzione planner..."
];

export default class PipelineRunner {
  constructor() {
    this.form         = document.querySelector("[data-js=pipelineForm]");
    this.resultBox    = document.querySelector("[data-js=pipelineResult]");
    this.feedbackBox  = document.querySelector("[data-js=jsonFeedback]");
    this.stepItems    = Array.from(document.querySelectorAll("[data-js=stepItem]"));
    this.progressFill = document.querySelector("[data-js=progressFill]");
    this.loadingMsg   = document.querySelector("[data-js=loadingMessage]");

    this.timerId = null;
    this.currentStep = 0;

    this._bindEvents();
  }

  _bindEvents() {
    if (!this.form) return;
    this.form.addEventListener("submit", this._onSubmit.bind(this));
  }

  _onSubmit(evt) {
    evt.preventDefault();
    const select = this.form.querySelector("[data-js=lorePathSelect]");
    const path   = select?.value;

    if (!path) {
      this._showFeedback("❌ Seleziona un file lore valido.");
      playErrorSound();
      select.classList.add("input-error");
      return;
    }

    select.classList.remove("input-error");
    this._clearFeedback();
    this._disableForm();
    showModal();
    this._startProgress();

    this._runPipeline({ lore_path: path })
      .then(data => this._handleResponse(data))
      .catch(err => this._handleNetworkError(err))
      .finally(() => this._cleanupUI());
  }

  async _runPipeline(body) {
    const res = await fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Server responded ${res.status}: ${text}`);
    }
    return res.json();
  }

  _handleResponse(data) {
    if (data.error) {
      this.resultBox.textContent = data.error;
      playErrorSound();
    } else {
      this.resultBox.innerHTML = "";
      this._renderResult(data);
      playSuccessSound();
    }
  }

  _handleNetworkError(err) {
    this.resultBox.textContent = `❌ Errore di rete: ${err.message}`;
    playErrorSound();
  }

  _cleanupUI() {
    clearInterval(this.timerId);
    this._enableForm();
    hideModal();
    this.resultBox.classList.remove("hidden");
  }

  _disableForm() {
    this.form.querySelector("button").disabled = true;
  }

  _enableForm() {
    this.form.querySelector("button").disabled = false;
  }

  _showFeedback(msg) {
    this.feedbackBox.textContent = msg;
  }

  _clearFeedback() {
    this.feedbackBox.textContent = "";
  }

  _startProgress() {
    this.currentStep = 0;
    this._updateStep(0);

    this.timerId = setInterval(() => {
      this.currentStep++;
      if (this.currentStep >= STEPS.length) {
        clearInterval(this.timerId);
      } else {
        this._updateStep(this.currentStep);
      }
    }, PROGRESS_INTERVAL_MS);
  }

  _updateStep(idx) {
    this.loadingMsg.textContent = STEPS[idx];
    this.progressFill.style.width = `${((idx + 1) / STEPS.length) * 100}%`;
    this.stepItems.forEach((li, i) => {
      li.classList.toggle("active-step", i === idx);
    });
  }

  _renderResult(data) {
    const card = document.createElement("div");
    card.classList.add("result-card");

    const domTitle = document.createElement("h3");
    domTitle.textContent = "✅ Dominio";
    const domPre = document.createElement("pre");
    domPre.textContent = data.domain?.slice(0, MAX_PREVIEW_LENGTH) || "(vuoto)";
    card.append(domTitle, domPre);

    if (data.session_id && data.domain) {
      const dlLink = document.createElement("a");
      dlLink.href = `/uploads/${data.session_id}/domain.pddl`;
      dlLink.textContent = "Scarica dominio completo";
      dlLink.setAttribute("download", "");
      card.appendChild(dlLink);
    }

    const probTitle = document.createElement("h3");
    probTitle.textContent = "✅ Problema";
    const probPre = document.createElement("pre");
    probPre.textContent = data.problem?.slice(0, MAX_PREVIEW_LENGTH) || "(vuoto)";
    card.append(probTitle, probPre);

    if (data.session_id && data.problem) {
      const dlLinkP = document.createElement("a");
      dlLinkP.href = `/uploads/${data.session_id}/problem.pddl`;
      dlLinkP.textContent = "Scarica problema completo";
      dlLinkP.setAttribute("download", "");
      card.appendChild(dlLinkP);
    }

    if (data.validation) {
      const report = this._renderValidationReport(data.validation);
      card.append(report);
    }

    this.resultBox.appendChild(card);
  }

  _renderValidationReport(v) {
    const container = document.createElement("div");
    container.innerHTML = DOMPurify.sanitize(`
      <hr>
      <h3>🧪 <strong>Report di Validazione</strong></h3>
      <ul>
        ${
          !v.valid_syntax
            ? `<li style="color:red;">❌ Errori di sintassi: ${
                (v.missing_sections || []).map(s => `<code>${s}</code>`).join(", ")
              }</li>`
            : ""
        }
        ${
          (v.undefined_objects_in_goal || []).length
            ? `<li>🎯 Oggetti non nel goal: ${
                v.undefined_objects_in_goal.map(o => `<code>${o}</code>`).join(", ")
              }</li>`
            : ""
        }
        ${
          (v.semantic_errors || []).length
            ? `<li>⚠️ Semantica: ${
                v.semantic_errors.map(e => `<code>${e}</code>`).join(", ")
              }</li>`
            : ""
        }
      </ul>
      <details>
        <summary>📋 JSON completo</summary>
        <pre>${JSON.stringify(v, null, 2)}</pre>
      </details>
    `);
    return container;
  }
}

// 🔄 Popola dinamicamente la tendina dei file lore
async function loadLoreOptions() {
  const select = document.querySelector("[data-js=lorePathSelect]");
  if (!select) return;

  try {
    const res = await fetch("/api/lore_files");
    const files = await res.json();

    select.innerHTML = `<option value="">-- Seleziona lore --</option>`;
    files.forEach(file => {
      const option = document.createElement("option");
      option.value = file;
      option.textContent = file;
      select.appendChild(option);
    });
  } catch (err) {
    console.error("Errore nel caricamento dei file lore:", err);
  }
}

// 🚀 Inizializzazione
document.addEventListener("DOMContentLoaded", () => {
  new PipelineRunner();
  loadLoreOptions();
});
