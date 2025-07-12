// static/js/narrative.js
// Streaming real-time LLM responses (SSE)
document.addEventListener("DOMContentLoaded", () => {
  const loreSelect = document.getElementById("lore-select");
  const startBtn   = document.getElementById("start-narrative");
  const stopBtn    = document.getElementById("stop-narrative");
  const spinner    = document.getElementById("start-spinner");
  const statusTxt  = document.getElementById("status-text");
  const log        = document.getElementById("narrative-log");
  const rawDebug   = document.getElementById("raw-debug");
  const form       = document.getElementById("narrative-form");
  const feedbackIn = document.getElementById("feedback-input");

  let threadId = null;
  let source   = null;

  function append(text, cls = "narration") {
    const p = document.createElement("p");
    p.className = cls === "question"
      ? "mb-2 text-muted fst-italic"
      : "mb-2";
    p.textContent = text;
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
  }

  function handleChunk(event) {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      payload = event.data;
    }

    // raw debug
    if (rawDebug) {
      const d = document.createElement("details");
      d.className = "small text-secondary";
      const summary = document.createElement("summary");
      summary.textContent = `[${event.type}]`;
      d.appendChild(summary);
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(payload, null, 2);
      d.appendChild(pre);
      rawDebug.appendChild(d);
      rawDebug.scrollTop = rawDebug.scrollHeight;
    }

    if (event.type === 'narration') {
      const narration = typeof payload === 'string' ? payload : payload.narration;
      if (narration) append(`🗣️ ${narration}`, 'narration');
    }

    if (event.type === 'question') {
      const question = typeof payload === 'string' ? payload : payload.question;
      if (question) append(`❓ ${question}`, 'question');
    }

    if (event.type === 'step') {
      const step = typeof payload === 'string' ? payload : payload.step;
      if (step) append(`➡️ Step in corso: ${step}`, 'question');
    }

    if (event.type === 'append') {
      const action = typeof payload === 'string' ? payload : payload.action;
      if (action) append(`📌 Step arricchito: ${action}`, 'narration');
    }

    if (event.type === 'done') {
      append('✅ Avventura completata.', 'narration');
      updateUIOnEnd();
    }

    if (event.type === 'error') {
      append('❌ Errore nella narrazione.', 'question');
      updateUIOnEnd();
    }
  }

  function closeStream() {
    if (source) {
      source.close();
      source = null;
    }
  }

  function updateUIOnStart() {
    startBtn.disabled = true;
    spinner.classList.remove('d-none');
    statusTxt.textContent = '⏳ Caricamento…';
    statusTxt.classList.remove('d-none');
    stopBtn.classList.remove('d-none');
    form.classList.remove('d-none');
    log.innerHTML = '';
    rawDebug.innerHTML = '';
    feedbackIn.value = '';
  }

  function updateUIOnEnd() {
    startBtn.disabled = false;
    spinner.classList.add('d-none');
    statusTxt.classList.add('d-none');
    stopBtn.classList.add('d-none');
    form.classList.add('d-none');
  }

  function startStream(feedback) {
    closeStream();
    const lore = loreSelect.value;
    const params = new URLSearchParams({ thread_id: threadId, lore });
    if (feedback) params.set('feedback', feedback);
    source = new EventSource(`/narrative/stream?${params}`);
    ['narration','question','append','step','done','error'].forEach(evt => {
      source.addEventListener(evt, handleChunk);
    });
    source.onerror = () => {
      closeStream();
      updateUIOnEnd();
    };
  }

  startBtn.addEventListener('click', () => {
    if (!loreSelect.value) {
      alert('Seleziona una lore.');
      return;
    }
    threadId = `narrative-${Date.now()}`;
    updateUIOnStart();
    startStream();
  });

  stopBtn.addEventListener('click', () => {
    append('✋ Narrazione interrotta.');
    closeStream();
    updateUIOnEnd();
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    const fb = feedbackIn.value.trim();
    if (!fb) return;
    append(`🧠 ${fb}`, 'question');
    feedbackIn.value = '';
    startStream(fb);
  });
});
