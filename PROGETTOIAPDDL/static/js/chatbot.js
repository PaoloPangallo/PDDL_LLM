import { showModal, hideModal, playSuccessSound, playErrorSound } from "./utils.js";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("chatbot-form");
  const input = document.getElementById("chatbot-input");
  const log = document.getElementById("chat-log");

  async function sendChatMessage() {
    const message = input.value.trim();
    if (!message) return;

    const thread_id = localStorage.getItem("thread_id") || crypto.randomUUID();
    localStorage.setItem("thread_id", thread_id);

    appendEntry("user", message);
    input.value = "";
    input.disabled = true;
    showModal();

    try {
      const res = await fetch("/api/chatbot/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, thread_id, auto_mode: true })
      });
      const data = await res.json();
      appendEntry("bot", data.response || "🤖 Nessuna risposta ricevuta.");

      if (data.domain || data.problem) {
        log.innerHTML += `
        <details class="chat-entry bot">
          <summary>📄 Dettagli PDDL</summary>
          <pre><strong>Domain:</strong>\n${data.domain || "(vuoto)"}\n\n<strong>Problem:</strong>\n${data.problem || "(vuoto)"}</pre>
        </details>`;
      }

      playSuccessSound();
    } catch (err) {
      appendEntry("error", "❌ Errore nella comunicazione con il bot.");
      console.error("Chatbot error:", err);
      playErrorSound();
    } finally {
      input.disabled = false;
      hideModal();
      log.scrollTop = log.scrollHeight;
    }
  }

  function appendEntry(role, content) {
    const div = document.createElement("div");
    div.className = `chat-entry ${role}`;
    div.innerHTML = `<strong>${role === "user" ? "👤 Tu" : "🤖 Bot"}:</strong> ${content}`;
    log.appendChild(div);
  }

  form?.addEventListener("submit", e => {
    e.preventDefault();
    sendChatMessage();
  });
});
