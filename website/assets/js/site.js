/*
 * Behavior shared by every page: the mobile menu, scroll reveals and the
 * word by word tagline reveal. Loaded with `defer` on every page.
 */
(function () {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- mobile menu ----------

  const toggle = document.querySelector(".nav__toggle");
  const menu = document.getElementById("menu");
  if (toggle && menu) {
    const items = menu.querySelectorAll("li");
    // Links arrive one after another: 60ms apart, the whole sequence within 400ms
    const step = Math.min(60, 400 / Math.max(items.length, 1));
    const setOpen = (open) => {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      menu.classList.toggle("is-open", open);
      menu.inert = !open;
      document.body.style.overflow = open ? "hidden" : "";
      items.forEach((li, i) => { li.style.transitionDelay = open ? `${i * step}ms` : "0ms"; });
    };
    setOpen(false);
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && menu.classList.contains("is-open")) {
        setOpen(false);
        toggle.focus();
      }
    });
    window.matchMedia("(min-width: 901px)").addEventListener("change", (e) => { if (e.matches) setOpen(false); });
  }

  // ---------- scroll reveals: rise and fade in once ----------

  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && reveals.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -10% 0px" });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("is-visible"));
  }

  // ---------- tagline: each word turns from muted to full color as it crosses a line ----------

  document.querySelectorAll("[data-word-reveal]").forEach((block) => {
    const words = block.textContent.trim().split(/\s+/);
    block.setAttribute("aria-label", words.join(" "));
    block.textContent = "";
    const spans = words.map((word, i) => {
      const span = document.createElement("span");
      span.className = "word";
      span.setAttribute("aria-hidden", "true");
      span.textContent = word;
      block.appendChild(span);
      if (i < words.length - 1) block.appendChild(document.createTextNode(" "));
      return span;
    });
    if (reduceMotion || !("IntersectionObserver" in window)) {
      spans.forEach((s) => s.classList.add("is-lit"));
      return;
    }
    // The trigger line sits 40% up from the bottom of the screen
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-lit");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -40% 0px" });
    spans.forEach((s) => io.observe(s));
  });

})();
