/* Progressive enhancement only: the site works without JavaScript. */
(function () {
  "use strict";

  var header = document.querySelector("[data-header]");
  var toggle = document.querySelector("[data-nav-toggle]");
  var menu = document.querySelector("[data-nav-menu]");

  // Header border once the page is scrolled.
  if (header) {
    var onScroll = function () { header.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Mobile menu.
  if (toggle && menu) {
    var label = toggle.querySelector(".sr-only");
    var setOpen = function (open) {
      menu.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      if (label) label.textContent = open ? "Close menu" : "Open menu";
    };
    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });
    menu.addEventListener("click", function (event) {
      if (event.target.closest("a")) setOpen(false);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menu.classList.contains("is-open")) {
        setOpen(false);
        toggle.focus();
      }
    });
    window.matchMedia("(min-width: 861px)").addEventListener("change", function (e) {
      if (e.matches) setOpen(false);
    });
  }

  // Active section indicator (home page) and table of contents (project pages).
  function trackSections(sections, linkFor) {
    if (!("IntersectionObserver" in window) || !sections.length) return;
    var visible = new Map();
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { visible.set(entry.target.id, entry.isIntersecting ? entry.intersectionRatio : 0); });
      var best = null, bestRatio = 0;
      sections.forEach(function (s) {
        var r = visible.get(s.id) || 0;
        if (r > bestRatio) { best = s.id; bestRatio = r; }
      });
      if (!best) return;
      sections.forEach(function (s) {
        var link = linkFor(s.id);
        if (link) link.classList.toggle("is-active", s.id === best);
      });
    }, { rootMargin: "-80px 0px -45% 0px", threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] });
    sections.forEach(function (s) { observer.observe(s); });
  }

  if (document.body.classList.contains("page-home")) {
    trackSections(
      Array.prototype.slice.call(document.querySelectorAll("[data-section]")),
      function (id) { return document.querySelector('[data-section-link="' + id + '"]'); }
    );
  }

  var toc = document.querySelector(".case__toc");
  if (toc) {
    var ids = Array.prototype.map.call(toc.querySelectorAll("a"), function (a) { return a.getAttribute("href").slice(1); });
    trackSections(
      ids.map(function (id) { return document.getElementById(id); }).filter(Boolean),
      function (id) { return toc.querySelector('a[href="#' + id + '"]'); }
    );
  }

  // Print button on the resume page.
  var printButton = document.querySelector("[data-print]");
  if (printButton) printButton.addEventListener("click", function () { window.print(); });
})();
