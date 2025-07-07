// ======================
// 🛠️ Funzioni di utilità
// ======================

export function showModal() {
  const modal = document.getElementById("loadingModal");
  modal?.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  modal.style.display = "flex";
}

export function hideModal() {
  const modal = document.getElementById("loadingModal");
  modal?.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  modal.style.display = "none";
}

export function safePlay(audio) {
  try {
    audio?.play().catch(err => console.warn("🔇 Audio bloccato:", err));
  } catch {}
}

export function playSuccessSound() {
  const audio = document.getElementById("successSound");
  safePlay(audio);
}

export function playErrorSound() {
  const audio = document.getElementById("errorSound");
  safePlay(audio);
}

export async function loadLoreTitles(selectId = "lore_path_select") {
  try {
    const res = await fetch("/api/lore_titles");
    const data = await res.json();
    const select = document.getElementById(selectId);
    select.innerHTML = "";
    data.forEach(item => {
      const opt = document.createElement("option");
      opt.value = item.filename;
      opt.textContent = item.title;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Errore nel caricamento lore:", err);
    const select = document.getElementById(selectId);
    if (select)
      select.innerHTML = '<option disabled>⚠️ Errore nel caricamento</option>';
  }
}
