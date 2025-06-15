document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("loadingModal");
  document.querySelectorAll("form").forEach(form => {
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
});
