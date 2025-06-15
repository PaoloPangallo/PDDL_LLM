document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("sendBtn");
    const userMessage = document.getElementById("userMessage");
    const replyBox = document.getElementById("llmReply");
    const preview = document.getElementById("autoPromptPreview");
    const fullPrompt = document.getElementById("fullPromptPreview");
    const useSuggestionBtn = document.getElementById("useSuggestionBtn");

    let defaultPrompt = "⚠️ Nessun messaggio predefinito.";
    let validationSummary = "✅ I file sembrano sintatticamente corretti.";

    try {
        const valJson = JSON.parse(document.getElementById("validationData").textContent);
        const missing = (valJson.missing_sections || []).join(", ");
        const undefinedObjs = (valJson.undefined_objects_in_goal || []).join(", ");
        const undefinedActs = (valJson.undefined_actions || []).join(", ");

        if (!valJson.valid_syntax) {
            validationSummary = "⚠️ Il file PDDL non è valido.\n";
            if (missing) validationSummary += `- Sezioni mancanti: ${missing}\n`;
            if (undefinedObjs) validationSummary += `- Oggetti non definiti nel goal: ${undefinedObjs}\n`;
            if (undefinedActs) validationSummary += `- Azioni non definite: ${undefinedActs}\n`;
        }

        defaultPrompt = `I file PDDL generati sono invalidi. Mancano queste sezioni obbligatorie: ${missing}.
Per favore, rigenera i file usando solo la sintassi PDDL standard, includendo tutte le sezioni richieste come (:types), (:predicates), (:init), (:goal), (:action ...), ecc.`;

        if (preview) preview.textContent = defaultPrompt;
    } catch (err) {
        console.warn("validationData non disponibile o non valido");
    }

    const updateFullPromptPreview = () => {
        const domain = document.querySelector("textarea[readonly]:nth-of-type(1)")?.value || "(domain non disponibile)";
        const problem = document.querySelector("textarea[readonly]:nth-of-type(2)")?.value || "(problem non disponibile)";
        const msg = userMessage.value.trim() || defaultPrompt;

        const composed = `
Questi sono i file PDDL generati:

=== DOMAIN START ===
${domain}
=== DOMAIN END ===

=== PROBLEM START ===
${problem}
=== PROBLEM END ===

${validationSummary}

L'utente ha detto:
"${msg}"

🔁 Rispondi in modo utile e dettagliato. Se necessario, suggerisci correzioni ai file PDDL (standard PDDL), includi sezioni mancanti, predicati non definiti o errori di goal.
`;
        if (fullPrompt) fullPrompt.textContent = composed.trim();
    };

    // aggiorna live quando si scrive
    userMessage.addEventListener("input", updateFullPromptPreview);
    useSuggestionBtn?.addEventListener("click", () => {
        userMessage.value = defaultPrompt;
        updateFullPromptPreview();
    });

    updateFullPromptPreview(); // iniziale
});
