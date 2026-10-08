/* Lulu — nav, reveals, gallery lightbox. No dependencies. */
(function () {
  "use strict";

  var root = document.documentElement;

  // Tells the inline head script that the site's JS is alive, so it
  // keeps the .js flag (and the reveal animations) in place.
  window.__luluReady = true;

  /* ---------- sticky nav ---------- */
  var nav = document.querySelector("[data-nav]");
  if (nav) {
    var onScroll = function () {
      nav.classList.toggle("is-stuck", window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- mobile menu ---------- */
  var toggle = document.querySelector("[data-nav-toggle]");
  var mobileMenu = document.querySelector("[data-mobile-menu]");
  if (toggle && mobileMenu) {
    var setMenu = function (open) {
      document.body.classList.toggle("menu-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      mobileMenu.setAttribute("aria-hidden", open ? "false" : "true");
    };
    toggle.addEventListener("click", function () {
      setMenu(!document.body.classList.contains("menu-open"));
    });
    mobileMenu.addEventListener("click", function (e) {
      if (e.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setMenu(false);
    });

    // Unfolding a foldable or rotating a tablet crosses the breakpoint where
    // the overlay no longer exists; drop the open state so the page is not
    // left scroll-locked behind nothing.
    var wide = window.matchMedia("(min-width: 761px)");
    var onWide = function (e) { if (e.matches) setMenu(false); };
    if (wide.addEventListener) wide.addEventListener("change", onWide);
    else if (wide.addListener) wide.addListener(onWide);
    // some engines only re-evaluate media queries on the next paint; a resize
    // listener catches the unfold immediately
    window.addEventListener("resize", function () { onWide(wide); });
  }

  /* ---------- scroll reveals ----------
     The stylesheet only hides .reveal while <html> carries .js, and the
     failsafe below strips .js if anything goes wrong — so content can
     never end up permanently invisible. */
  var reveals = [].slice.call(document.querySelectorAll(".reveal"));

  var revealAll = function () {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  };

  if (!reveals.length) {
    root.classList.remove("js");
  } else if (!("IntersectionObserver" in window)) {
    root.classList.remove("js");
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });

    reveals.forEach(function (el) { io.observe(el); });

    // Failsafe: if the observer never fires (hidden tab, odd embed),
    // show everything anyway rather than leaving a blank page.
    setTimeout(revealAll, 2200);
  }

  /* ---------- gallery lightbox ---------- */
  var lightbox = document.querySelector("[data-lightbox]");
  if (lightbox) {
    var lbImg = lightbox.querySelector("img");
    var tiles = [].slice.call(document.querySelectorAll("[data-tile]"));
    var index = -1;
    var lastFocus = null;

    var show = function (i) {
      if (!tiles.length) return;
      index = (i + tiles.length) % tiles.length;
      var source = tiles[index].querySelector("img");
      lbImg.src = source.getAttribute("src");
      lbImg.alt = source.getAttribute("alt") || "";
    };

    // Everything behind the dialog. While it is open this is made inert, so
    // keyboard focus and screen readers stay inside the dialog instead of
    // wandering the page underneath it.
    var behind = [].slice.call(document.body.children).filter(function (el) {
      return el !== lightbox;
    });

    var setBehindInert = function (on) {
      behind.forEach(function (el) { el.inert = on; });
    };

    var open = function (i) {
      lastFocus = document.activeElement;
      show(i);
      lightbox.classList.add("is-open");
      lightbox.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      setBehindInert(true);

      // The dialog is visibility:hidden until .is-open paints, and a hidden
      // element cannot take focus — so focus on the next frame, not this one.
      var closeBtn = lightbox.querySelector("[data-lb-close]");
      if (closeBtn) {
        requestAnimationFrame(function () { closeBtn.focus(); });
      }
    };

    var close = function () {
      lightbox.classList.remove("is-open");
      lightbox.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      setBehindInert(false);
      if (lastFocus) lastFocus.focus();
    };

    // Fallback trap for browsers without inert: keep Tab inside the dialog.
    var trapTab = function (e) {
      if (e.key !== "Tab" || !lightbox.classList.contains("is-open")) return;
      var stops = [].slice.call(
        lightbox.querySelectorAll("button, [href], input, select, textarea")
      ).filter(function (el) { return !el.disabled; });
      if (!stops.length) return;
      var first = stops[0];
      var last = stops[stops.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trapTab);

    tiles.forEach(function (tile, i) {
      tile.addEventListener("click", function () { open(i); });
    });

    lightbox.addEventListener("click", function (e) {
      if (e.target.closest("[data-lb-close]") || e.target === lightbox) return close();
      if (e.target.closest("[data-lb-prev]")) return show(index - 1);
      if (e.target.closest("[data-lb-next]")) return show(index + 1);
    });

    document.addEventListener("keydown", function (e) {
      if (!lightbox.classList.contains("is-open")) return;
      if (e.key === "Escape") close();
      // RTL page, but the images read left-to-right in the strip order.
      if (e.key === "ArrowRight") show(index - 1);
      if (e.key === "ArrowLeft") show(index + 1);
    });
  }

  /* ---------- the block runs the height of the page ----------
     Aligned to the hero artwork so the column is a continuation of the
     drawn block: same x range, starting exactly at the artwork's foot. */
  var plinth = document.querySelector("[data-plinth]");
  var artSvg = document.querySelector("[data-art] svg");

  if (plinth && artSvg) {
    var placePlinth = function () {
      var r = artSvg.getBoundingClientRect();
      if (!r.width) return;
      var k = r.width / 620;               // viewBox unit -> css px
      plinth.style.left = r.left + window.scrollX + 85 * k + "px";
      plinth.style.width = 440 * k + "px";
      // Start a pixel high, tucked behind the artwork. The join lands on a
      // fractional device pixel, and the antialiased bottom row of the SVG
      // would otherwise let the near-black page show through as a hairline.
      plinth.style.top = r.top + window.scrollY + 780 * k - 1 + "px";
      plinth.style.setProperty("--u", k + "px");
    };

    placePlinth();
    window.addEventListener("resize", placePlinth);
    window.addEventListener("load", placePlinth);
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(placePlinth);
    }

    // The artwork moves and resizes without firing a resize event — lazy
    // images and late fonts reflow the page under it. Watching the boxes
    // catches those; nothing here changes the document height, so the
    // observer cannot feed itself.
    if ("ResizeObserver" in window) {
      var ro = new ResizeObserver(placePlinth);
      ro.observe(artSvg);
      ro.observe(document.body);
    }
  }

  /* ---------- menu page: highlight the section being read ---------- */
  var spy = document.querySelector(".menu-nav");
  if (spy) {
    var chips = [].slice.call(spy.querySelectorAll('a[href^="#"]'));
    var chipFor = {};
    chips.forEach(function (a) { chipFor[a.getAttribute("href").slice(1)] = a; });
    var heads = [].slice.call(document.querySelectorAll(".course__head[id]")).filter(function (h) {
      return chipFor[h.id];
    });
    var current = null;
    var activate = function (id) {
      if (id === current) return;
      current = id;
      chips.forEach(function (a) {
        if (a === chipFor[id]) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      });
      // on phones the chips scroll sideways: keep the live one in view
      var live = chipFor[id];
      if (live && spy.scrollWidth > spy.clientWidth) {
        // scrollIntoView copes with RTL scroll offsets, which scrollTo does not
        live.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
      }
    };
    // The live section is the last heading that has reached the sticky bar.
    // Measuring on scroll beats an IntersectionObserver band here: jumping to
    // a section from a chip lands the heading just outside any thin band.
    var spyUpdate = function () {
      var line = spy.getBoundingClientRect().bottom + 24;
      var live = null;
      heads.forEach(function (h) { if (h.getBoundingClientRect().top <= line) live = h; });
      if (live) activate(live.id);
      else if (current) {
        current = null;
        chips.forEach(function (a) { a.removeAttribute("aria-current"); });
      }
    };
    // five rect reads per scroll event is cheap enough that no throttling is needed
    window.addEventListener("scroll", spyUpdate, { passive: true });
    spyUpdate();
  }

  /* ---------- inert buttons ----------
     Nothing on the site is inert any more: Instagram and the reservation
     button (Ontopo) both link out. The handler stays for any control that is
     ever marked data-inert again, so a placeholder button cannot navigate. */
  [].slice.call(document.querySelectorAll("[data-inert]")).forEach(function (el) {
    el.addEventListener("click", function (e) { e.preventDefault(); });
  });
})();
