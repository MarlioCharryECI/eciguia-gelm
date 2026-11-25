// EciGuía · comportamiento de la interfaz (delegación de eventos: funciona con mensajes nuevos del chat)
(() => {
  // Tema: recuerda la preferencia del usuario (si el navegador no permite guardarla, igual funciona)
  try {
    const saved = localStorage.getItem("eciguia-theme");
    if (saved === "dark") document.body.classList.add("dark");
    if (saved === "light") document.body.classList.remove("dark");
  } catch (e) {}

  function sendQuestion(text) {
    const box = document.querySelector(".eg-input textarea");
    if (!box) return;
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(box, text);
    box.dispatchEvent(new Event("input", { bubbles: true }));
    setTimeout(() => {
      const btn = document.querySelector(".eg-input button.submit-button, .eg-input button[aria-label='Submit']");
      if (btn) btn.click();
      else box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true }));
    }, 60);
  }

  // El chat de Gradio filtra el HTML de su estado vacío y borra el viewBox de los SVG (íconos y logo
  // se verían recortados). Se restaura cada vez que ese contenido aparece.
  function fixSvgs(root) {
    root.querySelectorAll("svg.eg-logo:not([viewBox])").forEach((s) => s.setAttribute("viewBox", "0 0 256 256"));
    root.querySelectorAll("svg.lucide:not([viewBox])").forEach((s) => s.setAttribute("viewBox", "0 0 24 24"));
  }
  new MutationObserver(() => fixSvgs(document)).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener("DOMContentLoaded", () => fixSvgs(document));

  // Enviar solo se habilita cuando hay texto. Se revisa también cada 300 ms porque Gradio vacía la caja
  // por código al enviar, sin disparar el evento input.
  function syncSend() {
    const box = document.querySelector(".eg-input textarea");
    const btn = document.querySelector(".eg-input button.submit-button");
    if (box && btn) btn.disabled = !box.value.trim();
  }
  document.addEventListener("input", (event) => { if (event.target.closest(".eg-input")) syncSend(); });
  setInterval(syncSend, 300);

  document.addEventListener("click", (event) => {
    const ask = event.target.closest(".eg-ask");
    // el filtro también borra data-q en el estado vacío: el texto del botón es la pregunta
    if (ask) { sendQuestion(ask.dataset.q || ask.textContent.trim()); return; }

    const cite = event.target.closest(".eg-cite");
    if (cite) {
      const msg = cite.closest(".eg-msg");
      const card = msg && msg.querySelector(`.eg-src[data-src="${cite.dataset.cite}"]`);
      if (card) {
        card.open = true;
        card.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
        card.classList.add("is-flash");
        setTimeout(() => card.classList.remove("is-flash"), 1200);
      }
      return;
    }

    if (event.target.closest(".eg-theme")) {
      const dark = document.body.classList.toggle("dark");
      try { localStorage.setItem("eciguia-theme", dark ? "dark" : "light"); } catch (e) {}
    }
  });
})();
