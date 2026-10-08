"""Regenerates the menu block of menu.html from the owner's menu (data below).

Run from the project root:  python tools/build_menu.py
Everything between the <nav class="menu-nav"> and the closing note is replaced.
"""
import html
import pathlib
import re

# (name, description, price)  — price is shown as typed; "a / b" is rendered LTR
FOOD = [
    ("לחם הבית", "מוגש עם חריף, שמן זית/בלסמי ושום קונפי", "35"),
    ("קולורבי מדורה", "על מצע של לאבנה ורודה, צ'ילי אדום, שמן זעתר, כוסברה ופטרוזיליה", "48"),
    ("אספרגוס וזוקיני על סקורדיליה", "אספרגוס וזוקיני על סקורדיליה יוונית, שקדים, שמן צ'ילי, שמן ירוק וצ'ילי אדום", "58"),
    ("תפו״א", "קרעי תפוחי אדמה, פפריקה מעושנת, איולי שום, כוסברה, פטרוזיליה ופרמז'ן", "42"),
    ("סלט שוק", "חתוך גס — קולורבי, עגבניה, גזר, מלפפון, בצל סגול, צנונית, בצל ירוק, זיתי קלמטה, שקדים ושמן זית", "52"),
    ("נקניקיות עגל/בווריה (כשר)", "2 נקניקיות עסיסיות, חרדל, קרושונים וכרוב כבוש", "72"),
    ("פלטת גבינות", "4 סוגי גבינות, ריבה, קרקרים וענבים", "75"),
    ("פלטת שרקטורי", "5 סוגי נקניקי בוטיק: סלמי פפטו, סלמי נאפולי, סרוולד, בריסקט ומעדן אווז. עם חרדל, קרושונים וכרוב כבוש", "99"),
    ("זוקיני פסטה", "רצועות זוקיני, צנונית, בצל ירוק, בצל סגול וזיתי קלמטה ברוטב כוסברה, פטרוזיליה ופרמז'ן", "58"),
    ("פופקורן דג", "מוגש עם איולי שום ולימון", "65"),
    ("גרבלץ סלמון", "סלמון כבוש בכבישה קרה של הדרים, סלק, כרוב סגול ברוטב שמן ירוק ורוטב הדרים (צ'ילי חריף, פינגר ליים, בצל ירוק ושמיר)", "69"),
]

COCKTAILS = [
    ("Blossom", "ג'ין טנקרי, צינזאנו לבן, תמצית אלדרפלאוור, טוניק פיבר טרי ים תיכוני"),
    ("Saffron", "ג'וני ווקר בלונד, אפרול, מחית פסיפלורה ולימון"),
    ("Legacy", "ג'וני ווקר בלונד, תמצית למון גראס, נענע, תפוח ירוק ולימון"),
    ("Mirage", "וודקה קטל וואן, קמפרי, מחית תות, מיץ אננס ולימון"),
    ("Solara", "טקילה אספולון בלאנקו, גראנד מרנייה, סירופ אגבה, ריבת פלפלים חריפים ולימון"),
    ("Haven", "טקילה אספולון בלאנקו, תמצית אננס, עלי אורוגולה ולימון"),
    ("Oak", "קוניאק, קורביזיה, אפרול, רכז רימונים, תמצית פסיפלורה ולימון"),
    ("Fable", "ג'ין טנקרי מושרה בזעתר טרי, תמצית למון גראס, תפוח ירוק וג'ינג'ר"),
    ("Flare", "ג'וני ווקר בלונד מושרה בחמאה חומה, תמצית פלנרום ולימון"),
    ("Halo", "אפרול, ג'ין טנקרי סביליה, שרבט תפוזים ופרוסקו"),
]
COCKTAIL_PRICE = "54"

BEER = [
    ("בירה מהחבית — אסטרייה", "", "34"),
    ("בירה בקבוק — בלאנק", "", "31"),
]

# spirits: price is "double / single"
SPIRITS = [
    ("וודקה", [("קטל וואן", "50 / 26"), ("סמירנוף", "44 / 23")]),
    ("וויסקי", [("ג'וני ווקר רד לייבל", "43 / 23"), ("ג'וני ווקר בלונד", "43 / 23"),
                ("ג'וני ווקר בלק לייבל", "49 / 26"), ("ג'יימסון", "43 / 23")]),
    ("ג'ין", [("ברודוג", "49 / 25"), ("טנקרי", "50 / 26"), ("טנקרי סביליה", "52 / 27"), ("גורדונס", "44 / 23")]),
    ("רום", [("פלנטיישן", "40 / 21"), ("קפטן מורגן ספייסי", "42 / 22")]),
    ("אניס", [("ערק שליט", "40 / 21"), ("אוזו", "43 / 24")]),
    ("טקילה", [("אספולון בלנקו", "48 / 25"), ("אספולון רפסדו", "52 / 27")]),
    ("קוניאק", [("קורווזיה VS", "55 / 29")]),
]
MIXER = ("תוספת ערבוב", "תפוזים, לימונדה, טוניק, אקסל, סודה", "10")

# wine: (name, glass, bottle)
WINE = [
    ("יינות אדומים", [("בן זמרה חמרא בלנד", "42", "200"), ("קאסה דה מורז", "42", "200")]),
    ("יין לבן", [("שבלי", "52", "250"), ("פורניר סוביניון בלאן (צרפתי)", "52", "250"),
                 ("בן זמרה שרדונה", "52", "250")]),
    ("רוזה", [("וילה אלבור", "42", "200"), ("רוזה בן זמרה", "42", "200")]),
]

e = html.escape


def dish(num, name, desc, price, level="h3", price_cls="dish__price"):
    d = f'              <p class="dish__desc">{e(desc, quote=False)}</p>\n' if desc else ""
    return (
        '          <article class="dish reveal">\n'
        f'            <span class="dish__num">{num:02d}</span>\n'
        '            <div class="dish__body">\n'
        f'              <{level} class="dish__name">{e(name, quote=False)}</{level}>\n'
        f'{d}'
        '            </div>\n'
        f'            <span class="{price_cls}">{e(price, quote=False)}</span>\n'
        '          </article>\n'
    )


def course(cid, title, body, note=""):
    n = f'        <p class="course__note">{e(note, quote=False)}</p>\n' if note else ""
    return (
        '      <section class="course">\n'
        f'        <div class="course__head" id="{cid}">\n'
        f'          <h2 class="course__title">{e(title, quote=False)}</h2>\n'
        '        </div>\n'
        f'{n}'
        f'{body}'
        '      </section>\n\n'
    )


def dish_list(inner, single=False):
    cls = "dish-list dish-list--single" if single else "dish-list"
    return f'        <div class="{cls}">\n{inner}        </div>\n'


def sub(title):
    return f'        <h3 class="course__sub">{e(title, quote=False)}</h3>\n'


out = []

out.append(course("cocktails", "קוקטיילים", dish_list(
    "".join(dish(i + 1, n, d, COCKTAIL_PRICE) for i, (n, d) in enumerate(COCKTAILS)))))

out.append(course("food", "אוכל", dish_list(
    "".join(dish(i + 1, n, d, p) for i, (n, d, p) in enumerate(FOOD)))))

out.append(course("beer", "בירות", dish_list(
    "".join(dish(i + 1, n, d, p) for i, (n, d, p) in enumerate(BEER)), single=True)))

spirits = ""
for title, items in SPIRITS:
    spirits += sub(title) + dish_list(
        "".join(dish(i + 1, n, "", p, level="h4") for i, (n, p) in enumerate(items)), single=True)
spirits += sub(MIXER[0]) + dish_list(dish(1, MIXER[0], MIXER[1], MIXER[2], level="h4"), single=True)
out.append(course("spirits", "משקאות חריפים", spirits, note="מחירים: כפול / רגיל"))

wine = ""
for title, items in WINE:
    wine += sub(title) + dish_list(
        "".join(dish(i + 1, n, "", f"כוס {g} · בקבוק {b}", level="h4", price_cls="dish__price dish__price--rtl")
                for i, (n, g, b) in enumerate(items)), single=True)
out.append(course("wine", "יין", wine))

NAV = (
    '      <nav class="menu-nav" aria-label="מעבר בין חלקי התפריט">\n'
    '        <a href="#cocktails">קוקטיילים</a>\n'
    '        <a href="#food">אוכל</a>\n'
    '        <a href="#beer">בירות</a>\n'
    '        <a href="#spirits">משקאות חריפים</a>\n'
    '        <a href="#wine">יין</a>\n'
    '      </nav>\n\n'
)
NOTE = (
    '      <p class="menu-note">\n'
    '        המחירים בשקלים חדשים.\n'
    '      </p>\n'
)

p = pathlib.Path(__file__).resolve().parent.parent / "menu.html"
src = p.read_text(encoding="utf-8")
start = src.index('      <nav class="menu-nav"')
m = re.search(r'      <p class="menu-note">.*?</p>\n', src, re.S)
assert m, "menu-note not found"
new = src[:start] + NAV + "".join(out) + NOTE + src[m.end():]
new = new.replace("התפריט מתחלף לפי העונה. מה שכתוב כאן הוא הקבוע שלנו.",
                  "התפריט של לולו — אוכל, קוקטיילים ושתייה.")
p.write_text(new, encoding="utf-8")
print("menu.html regenerated:", len(new), "chars")
