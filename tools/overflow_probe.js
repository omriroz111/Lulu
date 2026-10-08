// Paste into the browser console (or run via the preview tool) at any viewport.
// Reports horizontal overflow and the elements that cause it.
(function () {
  var vw = document.documentElement.clientWidth;
  var sw = document.documentElement.scrollWidth;
  var bad = [];
  document.querySelectorAll("body *").forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (!r.width || getComputedStyle(el).position === "fixed") return;
    if (r.right > vw + 1 || r.left < -1) {
      if (!el.closest(".mobile-menu") && !el.closest(".lightbox")) {
        bad.push((el.className && el.className.baseVal === undefined ? "." + String(el.className).split(" ")[0] : el.tagName) +
          " [" + Math.round(r.left) + "→" + Math.round(r.right) + "]");
      }
    }
  });
  return { vw: vw, scrollW: sw, overflow: sw > vw, offenders: bad.slice(0, 8) };
})();
