(() => {
  "use strict";

  const themeButton = document.querySelector(".theme-toggle");
  const updateThemeLabel = () => {
    const dark = document.documentElement.dataset.theme === "dark";
    themeButton.textContent = dark ? "Light mode" : "Dark mode";
    themeButton.setAttribute("aria-label", `Switch to ${dark ? "light" : "dark"} theme`);
  };
  themeButton.hidden = false;
  updateThemeLabel();
  themeButton.addEventListener("click", () => {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    const url = new URL(window.location.href);
    url.searchParams.set("scoutTheme", theme);
    history.replaceState(null, "", url);
    updateThemeLabel();
  });

  // Carry the explicit theme only to local pages; never leak search state to GitHub.
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link || link.getAttribute("href").startsWith("#")) return;
    const url = new URL(link.href);
    const theme = new URLSearchParams(window.location.search).get("scoutTheme");
    if (theme && url.origin === window.location.origin) {
      url.searchParams.set("scoutTheme", theme);
      link.href = url.href;
    }
  });

  const carousel = document.querySelector(".hero-art");
  if (carousel) {
    const slides = Array.from(carousel.querySelectorAll(".hero-slide"));
    const dots = Array.from(carousel.querySelectorAll("[data-slide]"));
    const count = carousel.querySelector(".carousel-count");
    let current = 0;
    const showSlide = (index) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const inactive = slideIndex !== current;
        slide.inert = inactive;
        slide.setAttribute("aria-hidden", String(inactive));
      });
      dots.forEach((dot, slideIndex) => {
        dot.setAttribute("aria-pressed", String(slideIndex === current));
      });
      count.textContent = `${current + 1} / ${slides.length}`;
    };
    carousel.querySelector(".carousel-controls").hidden = false;
    carousel.querySelector(".hero-slides").dataset.ready = "true";
    count.hidden = false;
    carousel.querySelectorAll("[data-direction]").forEach((button) => {
      button.addEventListener("click", () => showSlide(current + Number(button.dataset.direction)));
    });
    dots.forEach((dot) => {
      dot.addEventListener("click", () => showSlide(Number(dot.dataset.slide)));
    });
    carousel.addEventListener("keydown", (event) => {
      if (event.target.closest(".carousel-controls")
          && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
        event.preventDefault();
        showSlide(current + (event.key === "ArrowRight" ? 1 : -1));
      }
    });
    showSlide(0);
  }

  const form = document.querySelector(".filters");
  if (!form) return;
  const cards = Array.from(document.querySelectorAll("[data-scenario]"));
  const fields = ["q", "industry", "difficulty"];
  const readFilters = () => {
    const params = new URLSearchParams(window.location.search);
    fields.forEach((name) => { form.elements[name].value = params.get(name) || ""; });
  };
  const filter = (saveUrl) => {
    const query = form.elements.q.value.trim().toLowerCase();
    const industry = form.elements.industry.value;
    const difficulty = form.elements.difficulty.value;
    let count = 0;
    cards.forEach((card) => {
      const matches = query.split(/\s+/).every((word) => card.dataset.search.includes(word))
        && (!industry || card.dataset.industry === industry)
        && (!difficulty || card.dataset.difficulty === difficulty);
      card.hidden = !matches;
      if (matches) count += 1;
    });
    document.getElementById("result-count").textContent =
      `${count} of ${cards.length} scenario${cards.length === 1 ? "" : "s"}`;
    document.getElementById("no-results").hidden = count !== 0;
    if (saveUrl) {
      const url = new URL(window.location.href);
      fields.forEach((name) => {
        const value = form.elements[name].value.trim();
        if (value) url.searchParams.set(name, value);
        else url.searchParams.delete(name);
      });
      history.replaceState(null, "", url);
    }
  };
  form.hidden = false;
  readFilters();
  filter(false);
  form.addEventListener("submit", (event) => { event.preventDefault(); filter(true); });
  form.addEventListener("input", () => filter(true));
  form.addEventListener("change", () => filter(true));
  form.addEventListener("reset", () => {
    fields.forEach((name) => { form.elements[name].value = ""; });
    filter(true);
  });
  window.addEventListener("popstate", () => { readFilters(); filter(false); });
})();
