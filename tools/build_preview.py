"""Packs the whole site into ONE self-contained HTML file for phones / sharing.

The six pages become sections of a single document with a tiny hash router;
fonts, photos, the rendered glass and the drawn logo letter are inlined. Nothing is fetched except
Google Fonts (Assistant), which falls back to system sans if offline.

    python tools/build_preview.py OUT_DIR

Writes OUT_DIR/lulu-site-preview.html (complete document) and
OUT_DIR/lulu-preview.html (fragment for publishing as an Artifact, which wraps
it in its own head).
"""
import base64
import pathlib
import re
import sys

base = pathlib.Path(__file__).resolve().parent.parent
out_dir = pathlib.Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)

PAGES = ["index", "menu", "gallery", "about", "location", "accessibility"]


def read(name):
    return (base / name).read_text(encoding="utf-8")


def between(s, start, end):
    i = s.index(start)
    return s[i:s.index(end, i)]


def data_uri(path, mime):
    return "data:%s;base64,%s" % (mime, base64.b64encode(path.read_bytes()).decode())


css = read("assets/css/style.css")
woff2 = data_uri(base / "assets/fonts/DMSerifDisplay-Regular.woff2", "font/woff2")
css = css.replace('url("../fonts/DMSerifDisplay-Regular.woff2")', 'url("%s")' % woff2)
css = re.sub(r',\s*url\("\.\./fonts/DMSerifDisplay-Regular\.ttf"\)\s*format\("truetype"\)', "", css)
css = css.replace('url("../img/plaster.webp")', 'url("%s")' % data_uri(base / "assets/img/plaster.webp", "image/webp"))
assert "../fonts/" not in css and "../img/" not in css

js = read("assets/js/main.js")

idx = read("index.html")
header = between(idx, '<header class="nav"', "</header>") + "</header>"
mobile = between(idx, '<div class="mobile-menu"', "<!-- the block").rstrip()
footer = between(idx, '<footer class="footer">', "</footer>") + "</footer>"
plinth = '<div class="plinth" data-plinth aria-hidden="true"><span></span><span></span></div>'
lightbox = between(read("gallery.html"), '<div class="lightbox"', '<footer class="footer">').rstrip()
header = header.replace(' aria-current="page"', "")
mobile = mobile.replace(' aria-current="page"', "")

sections = []
for slug in PAGES:
    src = read(slug + ".html")
    body = between(src, '<main id="main">', "</main>")[len('<main id="main">'):]
    sections.append('<div class="page" id="page-%s">%s</div>' % (slug, body))

doc = "\n".join([header, mobile, '<main id="main">'] + sections + ["</main>", footer])

for photo in sorted((base / "photos").glob("*.jpg")):
    doc = doc.replace('src="photos/%s"' % photo.name, 'src="%s"' % data_uri(photo, "image/jpeg"))
doc = doc.replace('src="assets/brand-u.svg"', 'src="%s"' % data_uri(base / "assets/brand-u.svg", "image/svg+xml"))
doc = doc.replace('href="assets/img/coupe.webp"', 'href="%s"' % data_uri(base / "assets/img/coupe.webp", "image/webp"))
assert 'src="photos/' not in doc and 'src="assets/' not in doc and 'href="assets/' not in doc

for slug in PAGES:
    doc = doc.replace('href="%s.html"' % slug, 'href="#/%s"' % slug)
    lightbox = lightbox.replace('href="%s.html"' % slug, 'href="#/%s"' % slug)

# Artifact viewers block third-party frames; the real site keeps the map embed.
MAP = ('<a class="map-stand-in" href="https://www.google.com/maps?q=%D7%99%D7%A2%D7%A7%D7%91%2022%2C%20%D7%A8%D7%97%D7%95%D7%91%D7%95%D7%AA" '
       'target="_blank" rel="noopener noreferrer"><span>רחוב יעקב 22, רחובות</span>'
       '<span>פתיחת המפה ב־Google Maps ←</span></a>')
doc, n = re.subn(r"<iframe\b.*?</iframe>", MAP, doc, flags=re.S)
assert n == 1 and "<iframe" not in doc

ROUTER = """
(function () {
  var slugs = %s, pages = {};
  slugs.forEach(function (s) { pages[s] = document.getElementById("page-" + s); });
  function go(slug, top) {
    if (!pages[slug]) slug = "index";
    slugs.forEach(function (s) { pages[s].classList.toggle("is-active", s === slug); });
    document.body.dataset.page = slug;
    [].forEach.call(document.querySelectorAll('a[href^="#/"]'), function (a) {
      if (a.getAttribute("href") === "#/" + slug) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    document.body.classList.remove("menu-open");
    if (top) window.scrollTo(0, 0);
  }
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a) return;
    var h = a.getAttribute("href");
    e.preventDefault();
    if (h.indexOf("#/") === 0) {
      if (location.hash !== h) location.hash = h; else go(h.slice(2), true);
    } else if (h.length > 1) {
      var t = document.querySelector(".page.is-active " + h);
      if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
  window.addEventListener("hashchange", function () {
    go((location.hash || "").replace("#/", "") || "index", true);
  });
  go((location.hash || "").replace("#/", "") || "index", false);
}());
""" % ("[" + ",".join('"%s"' % s for s in PAGES) + "]")

PREVIEW_CSS = """
.page { display: none; }
.page.is-active { display: block; }
body:not([data-page="index"]) .plinth { display: none; }
.map-stand-in { display: grid; place-content: center; gap: .6rem; height: 100%; min-height: 260px;
  text-align: center; padding: 2rem; background: var(--ink-2); border: 1px solid var(--line);
  border-radius: 2px; color: var(--fg-dim); }
.map-stand-in span:last-child { color: var(--amber); font-size: .8125rem; }
"""

STYLE = "<style>\n@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@200;300;400;500;600&display=swap');\n%s\n%s\n</style>" % (css, PREVIEW_CSS)
BODY = "\n".join(['<a class="skip-link" href="#main">דילוג לתוכן המרכזי</a>', doc, plinth, lightbox,
                  "<script>" + ROUTER + "</script>", "<script>" + js + "</script>"])

(out_dir / "lulu-preview.html").write_text("<title>Lulu Bar</title>\n" + STYLE + "\n" + BODY, encoding="utf-8")
(out_dir / "lulu-site-preview.html").write_text("\n".join([
    "<!DOCTYPE html>", '<html lang="he" dir="rtl">', "<head>", '<meta charset="UTF-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<meta name="theme-color" content="#0a1416">', "<title>Lulu — מסעדה ובר ברחובות</title>",
    STYLE, "</head>", "<body>", BODY, "</body>", "</html>"]), encoding="utf-8")
print("built", out_dir)
