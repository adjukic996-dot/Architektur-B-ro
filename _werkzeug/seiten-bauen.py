#!/usr/bin/env python3
"""Baut die Website aus inhalt.json, kapitel.json und bilder/verzeichnis.json.

Gestaltungssystem nach dem Vorbild von exoape.com: jedes Textstueck sitzt in
einer Maske und faehrt von unten herein, Bilder klappen auf.

Aufruf:  python3 _werkzeug/seiten-bauen.py

Fehlt ein Bild, ein Textbaustein oder ein Schluessel, bricht der Lauf ab.
"""
import json, pathlib, re, sys, html as H

WURZEL  = pathlib.Path(__file__).resolve().parent.parent
INHALT  = json.loads((WURZEL/"inhalt.json").read_text())
KAPITEL = json.loads((WURZEL/"kapitel.json").read_text())
BILDER  = json.loads((WURZEL/"bilder"/"verzeichnis.json").read_text())

NOINDEX = True                      # vor dem Livegang auf False
DOMAIN  = "https://www.bruecknerarchitekten.com"
BASIS   = "/Architektur-B-ro"       # GitHub Pages; bei Vercel oder eigener Domain ""

HAUPT = [
    ("startseite",                                           "",                 "Start",            "start"),
    ("projekte",                                             "projekte",         "Projekte",         "projektliste"),
    ("generalplanung",                                       "generalplanung",   "Generalplanung",   "thema"),
    ("modulares-bauen-architektur-revolutioniert",            "modulares-bauen",  "Modulares Bauen",  "thema"),
    ("beitraege__referenzen",                                "referenzen",       "Referenzen",       "einfach"),
    ("leistungen",                                           "leistungen",       "Leistungen",       "thema"),
    ("von-der-kiste-zur-piazza-fachmarktzentren-neu-gedacht", "fachmarktzentren", "Fachmarktzentren", "thema"),
    ("bauen-im-bestand",                                     "bauen-im-bestand", "Bauen im Bestand", "thema"),
    ("esg",                                                  "esg",              "ESG",              "thema"),
    ("kontakt",                                              "kontakt",          "Kontakt",          "kontakt"),
]
MENUE = [(z, t) for _, z, t, _ in HAUPT if z != ""]

PROJEKTE = sorted(k for k in INHALT
                  if k.startswith("beitraege__") and k != "beitraege__referenzen")

# Die sechs der Werkschau. Die ersten vier hebt Brueckner im eigenen Menue hervor,
# die beiden letzten stehen weit oben in ihrer Projektliste. Ihre Auswahl, nicht meine.
WERKSCHAU = [
    "beitraege__denisstrasse-lichthofe",
    "beitraege__neubau-buerogebaeude-mit-parametrisch-entwickelter-fassade",
    "beitraege__kathrein-werksviertel-in-rosenheim",
    "beitraege__meine-volksbank-raiffeisenbank-in-rosenheim",
    "beitraege__rems-waiblingen",
    "beitraege__shine-on-oberaudorf",
]

OFFENE_BILDTEXTE = []
UMBRUCH = re.compile(r"\n\s*\n")

# ------------------------------------------------------------------ Werkzeug
def e(s):
    return H.escape(str(s), quote=False)

def pfad(tiefe):
    """Verweis auf die Wurzel — bewusst './' bzw. '../', nie 'index.html'."""
    return "../" * tiefe if tiefe else "./"

def uebergang(slug):
    return "p-" + re.sub(r"[^a-z0-9-]", "-", slug.lower())

def kuerzen(text, laenge):
    text = " ".join(text.split())
    if len(text) <= laenge:
        return text
    return text[:laenge].rsplit(" ", 1)[0].rstrip(" ,;–-") + " …"

def maske(text, start=0):
    """Jede Zeile in ihr eigenes Fenster. Das ist der Kern des Systems."""
    teile = [t.strip() for t in re.split(r"\n+", str(text)) if t.strip()] or [str(text)]
    aus = []
    for i, t in enumerate(teile):
        aus.append('<span class="maske"><i style="--i:' + str(start + i) + '">'
                   + e(t) + "</i></span>")
    return "".join(aus)

def absaetze(text, klasse=""):
    k = ' class="' + klasse + '"' if klasse else ""
    return "".join("<p" + k + ">" + e(a) + "</p>"
                   for a in UMBRUCH.split(text) if a.strip())

def bild(url, tiefe, alt="", lazy=True, sizes="100vw", herkunft="", nackt=False):
    if url not in BILDER:
        raise SystemExit("ABBRUCH: Bild nicht im Verzeichnis: " + url
                         + "\n  Erst  python3 _werkzeug/bilder-wandeln.py  laufen lassen.")
    g = BILDER[url]["groessen"]
    if not g:
        raise SystemExit("ABBRUCH: keine Groessen fuer " + url)
    gross = g.get("1800") or g.get(1800) or list(g.values())[-1]
    P = pfad(tiefe)
    teile = []
    for s in ("600", "1200", "1800"):
        v = g.get(s) or g.get(int(s))
        if v:
            teile.append(P + "bilder/" + v["datei"] + " " + str(v["b"]) + "w")
    satz = ", ".join(teile)
    if not alt.strip() and not nackt:
        alt = (herkunft + " — Bild") if herkunft else "Bild"
        OFFENE_BILDTEXTE.append((herkunft or "?", gross["datei"]))
    laden = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    return ('<img src="' + P + "bilder/" + gross["datei"] + '" srcset="' + satz
            + '" sizes="' + sizes + '" width="' + str(gross["b"]) + '" height="'
            + str(gross["h"]) + '" alt="' + e(alt) + '"' + laden + ">")

def rahmen(url, tiefe, alt="", sizes="100vw", herkunft="", vt="", lazy=True):
    stil = ' style="view-transition-name:' + vt + '"' if vt else ""
    return ('<figure class="rahmen" style="margin:0"' + stil + ">"
            + bild(url, tiefe, alt, lazy=lazy, sizes=sizes, herkunft=herkunft)
            + "</figure>")

def erstes_bild(bloecke):
    for b in bloecke:
        if b["art"] == "hintergrund":
            for u in b["bilder"]:
                if u in BILDER:
                    return u
        if b["art"] == "bild" and b["quelle"] in BILDER:
            return b["quelle"]
        if b["art"] == "galerie":
            for x in b["bilder"]:
                if x["quelle"] in BILDER:
                    return x["quelle"]
    return None

def alle_bilder(bloecke):
    aus = []
    for b in bloecke:
        if b["art"] == "bild":
            aus.append(b["quelle"])
        elif b["art"] == "galerie":
            aus += [x["quelle"] for x in b["bilder"]]
        elif b["art"] == "hintergrund":
            aus += b["bilder"]
    return [u for u in dict.fromkeys(aus) if u in BILDER]

def name_ort(titel):
    teile = [x.strip() for x in titel.split(",")]
    return teile[0], (teile[-1] if len(teile) > 1 else "")

# -------------------------------------------------------------------- Gerüst
BEWEGUNG_JS = r"""
(function(){
  var sanft = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var W = document.documentElement;

  /* --- 1. Ladesequenz: der Aufmacher laeuft sofort, nicht erst beim Scrollen */
  function starten(){
    W.classList.add("geladen");
    var auf = document.querySelector(".auf");
    if (auf) auf.classList.add("da");
    document.querySelectorAll(".auf .maske, .auf [data-auf]").forEach(function(x){
      x.classList.add("da");
    });
    var ersterRahmen = document.querySelector(".auf .rahmen");
    if (ersterRahmen) ersterRahmen.classList.add("da");
  }
  if (document.readyState === "complete") requestAnimationFrame(starten);
  else addEventListener("load", function(){ requestAnimationFrame(starten); });
  /* Notnagel, falls ein Bild haengt — die Seite darf nie leer bleiben. */
  setTimeout(starten, 2200);

  /* --- 2. Alles Uebrige kommt beim Scrollen an */
  var ziele = document.querySelectorAll(".maske, .rahmen, [data-auf]");
  if (!("IntersectionObserver" in window) || sanft){
    ziele.forEach(function(x){ x.classList.add("da"); });
  } else {
    var b = new IntersectionObserver(function(ein){
      ein.forEach(function(x){
        if (x.isIntersecting){ x.target.classList.add("da"); b.unobserve(x.target); }
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.05 });
    ziele.forEach(function(x){ if (!x.closest(".auf")) b.observe(x); });
  }

  /* --- 3. Menue */
  var knopf = document.getElementById("menue-knopf"), menue = document.getElementById("menue");
  if (knopf && menue){
    function um(auf){
      knopf.setAttribute("aria-expanded", auf ? "true" : "false");
      knopf.setAttribute("aria-label", auf ? "Menü schließen" : "Menü öffnen");
      menue.classList.toggle("auf", auf);
      document.body.style.overflow = auf ? "hidden" : "";
      if (auf) menue.querySelector("a").focus();
    }
    knopf.addEventListener("click", function(){
      um(knopf.getAttribute("aria-expanded") !== "true");
    });
    addEventListener("keydown", function(ev){ if (ev.key === "Escape") um(false); });
    menue.addEventListener("click", function(ev){ if (ev.target.tagName === "A") um(false); });
  }

  /* --- 4. Kapitelspur */
  var punkte = [].slice.call(document.querySelectorAll(".kapitel"));
  var spur   = [].slice.call(document.querySelectorAll(".spur li"));
  var balken = document.querySelector(".spur__balken i");
  var laeuft = false, zuletzt = -1;
  function zeichne(){
    laeuft = false;
    if (!punkte.length) return;
    var ziel = innerHeight * 0.3, beste = 0, nah = Infinity;
    punkte.forEach(function(k, i){
      var d = Math.abs(k.getBoundingClientRect().top - ziel);
      if (d < nah){ nah = d; beste = i; }
    });
    if (balken) balken.style.setProperty("--p", ((beste + 1) / punkte.length * 100).toFixed(1) + "%");
    if (beste === zuletzt) return;
    zuletzt = beste;
    spur.forEach(function(li, i){ li.classList.toggle("an", i === beste); });
  }
  if (punkte.length){
    addEventListener("scroll", function(){
      if (!laeuft){ laeuft = true; requestAnimationFrame(zeichne); }
    }, {passive:true});
    addEventListener("resize", zeichne, {passive:true});
    zeichne();
  }
})();
"""

def menue_eintraege(aktiv, tiefe):
    P = pfad(tiefe)
    aus = []
    for i, (z, t) in enumerate(MENUE):
        hier = ' aria-current="page"' if z == aktiv else ""
        aus.append('      <li><a href="' + P + z + '/" style="--i:' + str(i) + '"'
                   + hier + ">" + e(t) + "</a></li>")
    return "\n".join(aus)

def kopf(titel, beschreibung, ziel, tiefe, bildurl=None):
    P = pfad(tiefe)
    kanon = DOMAIN + "/" + (ziel + "/" if ziel else "")
    robots = '<meta name="robots" content="noindex, nofollow">\n' if NOINDEX else ""
    kanon_tag = "" if ziel == "404" else '<link rel="canonical" href="' + kanon + '">\n'
    og = ""
    if bildurl and bildurl in BILDER:
        g = BILDER[bildurl]["groessen"]
        d = (g.get("1800") or list(g.values())[-1])["datei"]
        og = '<meta property="og:image" content="' + DOMAIN + "/bilder/" + d + '">\n'
    return """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>document.documentElement.className+=" js"</script>
<title>""" + e(titel) + """ — Brückner Architekten</title>
<meta name="description" content=\"""" + e(beschreibung)[:300] + """\">
""" + robots + kanon_tag + """<meta property="og:title" content=\"""" + e(titel) + """ — Brückner Architekten">
<meta property="og:type" content="website">
""" + og + """<link rel="preload" href=\"""" + P + """fonts/instrument-sans.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href=\"""" + P + """fonts/instrument-serif.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href=\"""" + P + """stil.css">
</head>
<body>

<header class="kopf">
  <div class="bahn kopf__innen">
    <a class="marke-wort" href=\"""" + P + """\"><span>Brückner</span><span>Architekten</span></a>
    <button class="menue-knopf" id="menue-knopf" type="button"
            aria-expanded="false" aria-controls="menue" aria-label="Menü öffnen">
      <i></i><i></i>
    </button>
  </div>
</header>

<nav class="menue" id="menue" aria-label="Hauptmenü">
  <div class="bahn">
    <ul>
""" + menue_eintraege(ziel, tiefe) + """
    </ul>
    <div class="menue__fuss">
      <a href=\"""" + P + """impressum/">Impressum</a>
      <a href=\"""" + P + """datenschutz/">Datenschutz</a>
      <a href="tel:+498912664000">+49 (89) 1266 40-0</a>
      <a href="mailto:date@bruecknerarchitekten.de">date@bruecknerarchitekten.de</a>
    </div>
  </div>
</nav>

<main>
"""

def aufmacher(titel, vorspann, bildurl, tiefe, klein=False, vt="", nachweis="Brückner Architekten"):
    k = " auf--klein" if klein else ""
    b = ""
    if bildurl:
        stil = ' style="view-transition-name:' + vt + '"' if vt else ""
        b = ('<div class="auf__bild"' + stil + ">"
             + bild(bildurl, tiefe, "", lazy=False, sizes="100vw", nackt=True) + "</div>")
    vor = ('<p class="auf__vor" data-auf>' + e(vorspann) + "</p>") if vorspann else ""
    return """
  <section class="auf""" + k + """\">
    """ + b + """
    <div class="auf__tuch"></div>
    <div class="bahn auf__innen">
      """ + vor + """
      <h1 class="riesig">""" + maske(titel) + """</h1>
    </div>
    <span class="auf__nachweis klein">""" + e(nachweis) + """</span>
  </section>
"""

def kopfzeile(marke, zahl=""):
    z = '<span class="zahl">' + e(zahl) + "</span>" if zahl else ""
    return ('<div class="kopfzeile"><h2 class="marke"><span class="maske"><i>'
            + e(marke) + "</i></span></h2>" + z + "</div>")

def schlussband(tiefe, dunkel=True):
    P = pfad(tiefe)
    k = " dunkel" if dunkel else ""
    return """
  <section class="schluss""" + k + """\">
    <div class="bahn">
      <h2 class="gross">""" + maske("Wir haben Ihr\nInteresse geweckt?") + """</h2>
      <p class="klein" data-auf style="--i:2;margin-top:var(--s3)">Sie haben Fragen oder wollen einen Termin vereinbaren?</p>
      <div class="schluss__knoepfe" data-auf style="--i:3">
        <a class="knopf" href=\"""" + P + """kontakt/"><span>Kontakt aufnehmen</span></a>
        <a class="knopf" href="tel:+498912664000"><span>+49 (89) 1266 40-0</span></a>
      </div>
    </div>
  </section>
"""

def fuss(tiefe):
    P = pfad(tiefe)
    spalten = "\n".join('<li><a href="' + P + z + '/">' + e(t) + "</a></li>" for z, t in MENUE)
    schild = '<span class="schild">Entwurf — nicht freigegeben</span>' if NOINDEX else ""
    return """
</main>

<footer class="fuss">
  <div class="bahn">
    <div class="fuss__raster">
      <div>
        <h2>Brückner Architekten GmbH</h2>
        <p>Gabriel-Max-Straße 4<br>81545 München</p>
        <p style="margin-top:var(--s2)">
          <a href="tel:+498912664000">+49 (89) 1266 40-0</a><br>
          <a href="mailto:date@bruecknerarchitekten.de">date@bruecknerarchitekten.de</a>
        </p>
      </div>
      <div><h2>Seiten</h2><ul>""" + spalten + """</ul></div>
      <div><h2>Rechtliches</h2><ul>
        <li><a href=\"""" + P + """impressum/">Impressum</a></li>
        <li><a href=\"""" + P + """datenschutz/">Datenschutz</a></li>
      </ul></div>
    </div>
    <div class="fuss__unten">
      <span>© Brückner Architekten GmbH</span>
      <span>Entwurf webgipfel — nicht freigegeben</span>
    </div>
  </div>
</footer>
""" + schild + """
<script>""" + BEWEGUNG_JS + """</script>
</body>
</html>
"""

# ------------------------------------------------------------------ Seitenarten
def start_bauen(tiefe):
    s = INHALT["startseite"]; bl = s["bloecke"]
    aufm = erstes_bild(bl)
    haltung = next((b["text"] for b in bl if b["art"] == "text" and len(b["text"]) > 200), "")
    vorspann = kuerzen(UMBRUCH.split(haltung)[0] if haltung else "", 185)

    aus = [aufmacher("Sehnsuchtsorte\nschaffen.", vorspann, aufm, tiefe)]

    # --- Werkschau ---------------------------------------------------------
    plaetze = ["a", "b", "c", "d", "e", "f"]
    karten = []
    for i, k in enumerate(WERKSCHAU):
        if k not in INHALT:
            raise SystemExit("ABBRUCH: WERKSCHAU nennt '" + k + "' — gibt es nicht in inhalt.json")
        u = erstes_bild(INHALT[k]["bloecke"])
        if not u:
            raise SystemExit("ABBRUCH: '" + k + "' hat kein Bild und kann nicht in die Werkschau")
        pr = INHALT[k]; slug = k.replace("beitraege__", "")
        name, ort = name_ort(pr["titel"])
        karten.append("""
    <a class="wp wp--""" + plaetze[i] + '" href="' + pfad(tiefe) + "projekte/" + slug + """/">
      """ + rahmen(u, tiefe, pr["titel"], sizes="(min-width:56rem) 50vw, 100vw",
                   herkunft=pr["titel"], vt=uebergang(slug)) + """
      <div class="wp__fuss">
        <h3 class="mittel">""" + e(name) + """</h3>
        """ + ('<span class="wp__ort">' + e(ort) + "</span>" if ort else "") + """
      </div>
    </a>""")

    aus.append("""
  <section class="bahn">
    """ + kopfzeile("Ausgewählte Projekte", str(len(PROJEKTE)) + " Arbeiten") + """
    <div class="werkschau">""" + "".join(karten) + """</div>
    <p style="margin-top:var(--s6)" data-auf>
      <a class="knopf" href=\"""" + pfad(tiefe) + """projekte/"><span>Alle Projekte</span></a></p>
  </section>""")

    # --- Haltung, dunkel ---------------------------------------------------
    rest = UMBRUCH.split(haltung)
    satz = kuerzen(rest[1] if len(rest) > 1 else (rest[0] if rest else ""), 240)
    aus.append("""
  <section class="dunkel">
    <div class="bahn">
      <h2 class="gross" style="max-width:17ch">""" + maske("Aus einer Hand\nsicher realisiert\nseit 1973.") + """</h2>
      <p class="fliess" data-auf style="--i:3;margin-top:var(--s4)">""" + e(satz) + """</p>
    </div>
  </section>""")

    # --- Themen ------------------------------------------------------------
    themen = [(q, z, tt) for q, z, tt, art in HAUPT if art == "thema"]
    reihen = []
    for i, (q, z, tt) in enumerate(themen, 1):
        txt = kuerzen(INHALT[q].get("beschreibung", ""), 110)
        reihen.append("""
      <a class="reihe" href=\"""" + pfad(tiefe) + z + """/" data-auf style="--i:""" + str(i) + """\">
        <span class="reihe__nr">""" + ("%02d" % i) + """</span>
        <h3 class="mittel">""" + e(tt) + """</h3>
        <span class="reihe__text">""" + e(txt) + """</span>
        <span class="reihe__pfeil">→</span>
      </a>""")
    aus.append("""
  <section class="bahn">
    """ + kopfzeile("Was wir tun", str(len(themen)) + " Felder") + """
    """ + "".join(reihen) + """
  </section>""")

    aus.append(schlussband(tiefe))
    return "".join(aus)

def thema_bauen(quelle, ziel, titel, tiefe):
    seite = INHALT[quelle]; bl = seite["bloecke"]
    kap = KAPITEL.get(quelle)
    if not kap:
        raise SystemExit("ABBRUCH: keine Kapitel fuer '" + quelle + "' in kapitel.json")
    nummern, n = {}, 0
    for i, b in enumerate(bl):
        if b["art"] == "ueberschrift":
            n += 1
            nummern[n] = i
    h1 = next((b["text"] for b in bl if b["art"] == "ueberschrift" and b["stufe"] == 1), titel)
    aufm = erstes_bild(bl)
    aus = [aufmacher(h1, kuerzen(seite.get("beschreibung", ""), 180), aufm, tiefe, klein=True)]

    spur = "\n".join('        <li><a href="#kapitel-' + str(i + 1) + '"><b>'
                     + ("%02d" % (i + 1)) + "</b><span>" + e(k["titel"]) + "</span></a></li>"
                     for i, k in enumerate(kap))

    benutzt = {aufm}
    teile = []
    for i, k in enumerate(kap):
        inner = []
        for nr in k["abschnitte"]:
            if nr not in nummern:
                raise SystemExit("ABBRUCH: Abschnitt " + str(nr) + " gibt es auf '" + quelle
                                 + "' nicht (nur 1.." + str(n) + "). kapitel.json pruefen.")
            start = nummern[nr]
            inner.append("<h3>" + e(bl[start]["text"]) + "</h3>")
            j = start + 1
            while j < len(bl) and bl[j]["art"] != "ueberschrift":
                b = bl[j]
                if b["art"] == "text":
                    inner.append('<div data-auf>' + absaetze(b["text"]) + "</div>")
                elif b["art"] == "bild" and b["quelle"] in BILDER and b["quelle"] not in benutzt:
                    benutzt.add(b["quelle"])
                    inner.append('<div style="margin-block:var(--s4)">'
                                 + rahmen(b["quelle"], tiefe, b.get("alt", ""),
                                          sizes="(min-width:64rem) 58vw, 100vw",
                                          herkunft=titel) + "</div>")
                j += 1
        teile.append("""
      <section class="kapitel" id="kapitel-""" + str(i + 1) + """\">
        <h2 class="kapitel__titel mittel">""" + maske(k["titel"]) + """</h2>
        """ + "".join(inner) + """
      </section>""")

    aus.append("""
  <div class="bahn" style="padding-block:var(--s6)">
    <div class="mit-spur">
      <nav class="spur" aria-label="Abschnitte dieser Seite">
        <ol>
""" + spur + """
        </ol>
        <div class="spur__balken"><i></i></div>
      </nav>
      <div>""" + "".join(teile) + """</div>
    </div>
  </div>""")

    uebrig = [u for u in alle_bilder(bl) if u not in benutzt]
    if uebrig:
        aus.append("""
  <section style="padding:0">
    <div class="rahmen" style="aspect-ratio:21/9">"""
                   + bild(uebrig[0], tiefe, "", sizes="100vw", nackt=True) + """</div>
  </section>""")

    aus.append(schlussband(tiefe))
    return "".join(aus)

def projekt_bauen(quelle, tiefe):
    seite = INHALT[quelle]; bl = seite["bloecke"]
    h1 = next((b["text"] for b in bl if b["art"] == "ueberschrift"), seite["titel"])
    aufm = erstes_bild(bl)
    vt = uebergang(quelle.replace("beitraege__", ""))
    aus = [aufmacher(h1, kuerzen(seite.get("beschreibung", ""), 170), aufm, tiefe,
                     klein=True, vt=vt)]
    inner, gesehen = [], {aufm}
    for b in bl:
        if b["art"] == "ueberschrift" and b["text"] != h1:
            inner.append('<h2 class="mittel" style="margin-top:var(--s5)">'
                         + maske(b["text"]) + "</h2>")
        elif b["art"] == "text":
            inner.append('<div class="fliess" data-auf>' + absaetze(b["text"]) + "</div>")
        elif b["art"] in ("bild", "galerie", "hintergrund"):
            urls = ([b["quelle"]] if b["art"] == "bild"
                    else [x["quelle"] for x in b["bilder"]] if b["art"] == "galerie"
                    else b["bilder"])
            for u in urls:
                if u in BILDER and u not in gesehen:
                    gesehen.add(u)
                    inner.append('<div style="margin-block:var(--s5)">'
                                 + rahmen(u, tiefe, "", sizes="(min-width:70rem) 72vw, 100vw",
                                          herkunft=seite["titel"]) + "</div>")
    aus.append('<section class="bahn">' + "".join(inner) + "</section>")
    aus.append(schlussband(tiefe))
    return "".join(aus)

def projektliste_bauen(tiefe):
    karten = []
    for i, k in enumerate(PROJEKTE):
        s = INHALT[k]; slug = k.replace("beitraege__", "")
        u = erstes_bild(s["bloecke"])
        name, ort = name_ort(s["titel"])
        vt = uebergang(slug) if k in WERKSCHAU else ""
        bildteil = (rahmen(u, tiefe, s["titel"],
                           sizes="(min-width:70rem) 32vw, (min-width:44rem) 48vw, 100vw",
                           herkunft=s["titel"], vt=vt)
                    if u else '<div class="rahmen" style="aspect-ratio:4/3"></div>')
        karten.append("""
      <a class="karte" href=\"""" + pfad(tiefe) + "projekte/" + slug + """/" data-auf style="--i:""" + str(i % 3) + """\">
        """ + bildteil + """
        <div class="wp__fuss">
          <h3 class="mittel" style="font-size:1.25rem">""" + e(name) + """</h3>
          """ + ('<span class="wp__ort">' + e(ort) + "</span>" if ort else "") + """
        </div>
      </a>""")
    return """
  <section class="auf auf--klein">
    <div class="auf__tuch" style="background:var(--nacht)"></div>
    <div class="bahn auf__innen">
      <h1 class="riesig">""" + maske("Projekte") + """</h1>
      <p class="auf__vor" data-auf style="--i:2;margin:var(--s3) 0 0">"""  \
        + str(len(PROJEKTE)) + """ Bauten und Entwürfe.</p>
    </div>
  </section>
  <section class="bahn">
    """ + kopfzeile("Alle Arbeiten", str(len(PROJEKTE)) + " Projekte") + """
    <div class="raster">""" + "".join(karten) + """</div>
  </section>
""" + schlussband(tiefe)

def einfach_bauen(quelle, titel, tiefe):
    seite = INHALT[quelle]; bl = seite["bloecke"]
    h1 = next((b["text"] for b in bl if b["art"] == "ueberschrift" and b["stufe"] == 1), titel)
    aufm = erstes_bild(bl)
    aus = [aufmacher(h1, kuerzen(seite.get("beschreibung", ""), 170), aufm, tiefe, klein=True)]
    inner = []
    for b in bl:
        if b["art"] == "ueberschrift" and b["text"] != h1:
            inner.append('<h2 class="gross" style="margin-top:var(--s5);max-width:18ch">'
                         + maske(b["text"]) + "</h2>")
        elif b["art"] == "text":
            inner.append('<div class="fliess" data-auf style="margin-top:var(--s3)">'
                         + absaetze(b["text"]) + "</div>")
    aus.append('<section class="bahn">' + "".join(inner) + "</section>")
    aus.append(schlussband(tiefe))
    return "".join(aus)

def kontakt_bauen(tiefe):
    return """
  <section class="auf auf--klein">
    <div class="auf__tuch" style="background:var(--nacht)"></div>
    <div class="bahn auf__innen">
      <h1 class="riesig">""" + maske("Kontakt") + """</h1>
    </div>
  </section>
  <section class="bahn">
    <div class="fliess" data-auf>
      <p><strong>Brückner Architekten GmbH</strong><br>Gabriel-Max-Straße 4<br>81545 München</p>
      <p style="margin-top:var(--s3)">
        Telefon <a href="tel:+498912664000" style="text-decoration:underline;text-underline-offset:3px">+49 (89) 1266 40-0</a><br>
        E-Mail <a href="mailto:date@bruecknerarchitekten.de" style="text-decoration:underline;text-underline-offset:3px">date@bruecknerarchitekten.de</a></p>
      <p style="margin-top:var(--s4)" class="luecke">[FEHLT: Öffnungszeiten, Anfahrtsbeschreibung und
        Ansprechpartner je Thema — auf der bestehenden Seite nur als eingebettete Karte und über
        Calendly vorhanden, beides wird bewusst nicht übernommen.]</p>
    </div>
  </section>
""" + schlussband(tiefe)

# ------------------------------------------------------------------ Rechtstexte
IMPRESSUM = """<h2>Angaben gemäß § 5 DDG</h2>
<p>Brückner Architekten GmbH<br>Gabriel-Max-Straße 4<br>81545 München</p>
<h3>Vertreten durch</h3>
<p>Laurent Brückner, Susanne Brückner, Peter Röllgen, Florian Wenisch</p>
<h3>Kontakt</h3>
<p>Telefon: +49 (89) 1266 40-0<br>E-Mail: date@bruecknerarchitekten.de</p>
<p class="luecke">[FEHLT: zweite Rufnummer — im bisherigen Impressum steht -46, im Seitenkopf -99 als Fax. Welche stimmt?]</p>
<h3>Registereintrag</h3>
<p>Eintragung im Handelsregister.<br>Registergericht: Amtsgericht Traunstein<br>Registernummer: HRB 18412</p>
<p class="luecke">[FEHLT: Gegenprüfung im Register — Sitz München bei Registergericht Traunstein ist zu bestätigen.]</p>
<h3>Umsatzsteuer</h3>
<p>Umsatzsteuer-Identifikationsnummer gemäß § 27a Umsatzsteuergesetz: DE 260718455</p>
<h3>Berufsbezeichnung und berufsrechtliche Regelungen</h3>
<p>Berufsbezeichnung: Architekten<br>Zuständige Kammer: Bayerische Architektenkammer<br>Verliehen durch: Deutschland</p>
<p>Es gelten folgende berufsrechtliche Regelungen: Berufsordnung, Baugewerbliche Tätigkeit.
   Einsehbar unter <a href="https://www.byak.de/" rel="noopener">byak.de</a>.</p>
<p class="luecke">[FEHLT: Eintragungsnummern der einzelnen Architektinnen und Architekten bei der Bayerischen Architektenkammer.]</p>
<h3>Angaben zur Berufshaftpflichtversicherung</h3>
<p>Name und Sitz des Versicherers: R+V Allgemeine Versicherung AG, Mittlerer Pfad 24, 70499 Stuttgart<br>
   Geltungsraum der Versicherung: Deutschland</p>
<h3>Bildrechte</h3>
<p>Alle Bildrechte liegen bei Brückner Architekten.</p>
<p class="luecke">[FEHLT: schriftliche Bestätigung, getrennt für Fotografien und für Renderings.]</p>
<h2>Haftung für Inhalte</h2>
<p>Als Diensteanbieter sind wir gemäß § 7 Abs. 1 DDG für eigene Inhalte auf diesen Seiten nach den
   allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 DDG sind wir als Diensteanbieter jedoch nicht
   verpflichtet, übermittelte oder gespeicherte fremde Informationen zu überwachen.</p>
<h2>Haftung für Links</h2>
<p>Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen Einfluss haben.
   Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen.</p>
<p class="luecke">[ENTWURF — vor dem Livegang anwaltlich prüfen lassen. Dies ist keine Rechtsauskunft.]</p>"""

DATENSCHUTZ = """<p class="luecke">[ENTWURF — neu geschrieben, weil diese Seite anders als die bisherige
   keine fremden Dienste einbindet. Vor dem Livegang anwaltlich prüfen lassen. Keine Rechtsauskunft.]</p>
<h2>Verantwortlicher</h2>
<p>Brückner Architekten GmbH<br>Gabriel-Max-Straße 4<br>81545 München<br>
   E-Mail: date@bruecknerarchitekten.de</p>
<p class="luecke">[FEHLT: Datenschutzbeauftragter — nach § 38 BDSG ab 20 Personen, die ständig mit der
   automatisierten Verarbeitung befasst sind. Ist einer benannt?]</p>
<h2>Welche Daten diese Website verarbeitet</h2>
<p>Diese Website bindet keine Dienste Dritter ein. Es werden keine Schriften, Karten, Videos,
   Terminbuchungen oder Statistikdienste von fremden Servern geladen. Es werden keine Cookies gesetzt,
   die eine Einwilligung erfordern würden. Deshalb gibt es kein Einwilligungsbanner.</p>
<h2>Server-Protokolldateien</h2>
<p>Beim Aufruf dieser Website werden durch den Hoster automatisch Daten erhoben, die Ihr Browser
   übermittelt: aufgerufene Adresse, Zeitpunkt, übertragene Datenmenge, Browsertyp, Betriebssystem
   und IP-Adresse. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO.</p>
<p class="luecke">[FEHLT: Name und Anschrift des Hosters sowie Speicherdauer, sobald das Hosting
   entschieden ist. Auftragsverarbeitungsvertrag ist dann abzuschließen.]</p>
<h2>Kontaktaufnahme</h2>
<p>Wenn Sie uns per E-Mail oder Telefon kontaktieren, verarbeiten wir Ihre Angaben zur Bearbeitung der
   Anfrage. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, soweit die Anfrage der Anbahnung eines
   Vertrags dient, sonst lit. f. Gesetzliche Aufbewahrungsfristen nach § 257 HGB und § 147 AO
   bleiben unberührt.</p>
<h2>Ihre Rechte</h2>
<p>Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung (Art. 17),
   Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch (Art. 21).
   Außerdem können Sie sich bei einer Aufsichtsbehörde beschweren (Art. 77 DSGVO).</p>"""

def rechtstext_bauen(titel, inhalt):
    return """
  <section class="auf auf--klein">
    <div class="auf__tuch" style="background:var(--nacht)"></div>
    <div class="bahn auf__innen"><h1 class="riesig">""" + maske(titel) + """</h1></div>
  </section>
  <section class="bahn"><div class="rechtstext" data-auf>""" + inhalt + """</div></section>
"""

# ---------------------------------------------------------------------- Lauf
def schreiben(ziel, html):
    p = WURZEL / (ziel + "/index.html" if ziel else "index.html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html)
    return p, len(html)

def main():
    gebaut = []
    for quelle, ziel, titel, art in HAUPT:
        if quelle not in INHALT:
            raise SystemExit("ABBRUCH: '" + quelle + "' fehlt in inhalt.json")
        tiefe = len([x for x in ziel.split("/") if x])
        s = INHALT[quelle]
        aufm = erstes_bild(s["bloecke"])
        if art == "start":          rumpf = start_bauen(tiefe)
        elif art == "thema":        rumpf = thema_bauen(quelle, ziel, titel, tiefe)
        elif art == "projektliste": rumpf = projektliste_bauen(tiefe)
        elif art == "kontakt":      rumpf = kontakt_bauen(tiefe)
        else:                       rumpf = einfach_bauen(quelle, titel, tiefe)
        html = kopf(titel, s.get("beschreibung", ""), ziel, tiefe, aufm) + rumpf + fuss(tiefe)
        gebaut.append(schreiben(ziel, html))

    for k in PROJEKTE:
        slug = k.replace("beitraege__", "")
        ziel = "projekte/" + slug
        s = INHALT[k]
        html = (kopf(s["titel"], s.get("beschreibung", ""), ziel, 2, erstes_bild(s["bloecke"]))
                + projekt_bauen(k, 2) + fuss(2))
        gebaut.append(schreiben(ziel, html))

    for ziel, titel, inhalt in [("impressum", "Impressum", IMPRESSUM),
                                ("datenschutz", "Datenschutz", DATENSCHUTZ)]:
        html = (kopf(titel, titel + " von Brückner Architekten GmbH, München.", ziel, 1)
                + rechtstext_bauen(titel, inhalt) + fuss(1))
        gebaut.append(schreiben(ziel, html))

    # Fehlerseite: absolute Pfade, deshalb der Basispfad.
    fehler = (kopf("Seite nicht gefunden", "Diese Seite gibt es nicht.", "404", 0)
              .replace('href="./', 'href="' + BASIS + "/")
              .replace('"./stil.css"', '"' + BASIS + '/stil.css"')
              + """
  <section class="auf auf--klein">
    <div class="auf__tuch" style="background:var(--nacht)"></div>
    <div class="bahn auf__innen">
      <h1 class="riesig">""" + maske("Seite nicht\ngefunden") + """</h1>
      <p class="auf__vor" data-auf style="--i:2;margin:var(--s3) 0 0">Die Adresse existiert nicht oder nicht mehr.</p>
      <p data-auf style="--i:3;margin-top:var(--s3)">
        <a class="knopf" href=\"""" + BASIS + """/"><span>Zur Startseite</span></a></p>
    </div>
  </section>"""
              + fuss(0).replace('href="./', 'href="' + BASIS + "/"))
    p = WURZEL / "404.html"; p.write_text(fehler); gebaut.append((p, len(fehler)))

    (WURZEL / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n" if NOINDEX
        else "User-agent: *\nAllow: /\n\nSitemap: " + DOMAIN + "/sitemap.xml\n")

    if OFFENE_BILDTEXTE:
        md = ["# Offene Bildbeschreibungen", "",
              "Diese Bilder tragen Inhalt und brauchen einen Alternativtext, der sagt,",
              "WAS zu sehen ist. Der jetzige Text ist ein Behelf aus dem Seitentitel.", "",
              "| Seite | Bilddatei | Beschreibung eintragen |", "|---|---|---|"]
        for h, d in sorted(set(OFFENE_BILDTEXTE)):
            md.append("| " + h + " | `" + d + "` | |")
        (WURZEL / "offene-bildtexte.md").write_text("\n".join(md) + "\n")
        print("  " + str(len(set(OFFENE_BILDTEXTE))) + " Bilder ohne echte Beschreibung")

    gesamt = sum(n for _, n in gebaut)
    print(str(len(gebaut)) + " Seiten gebaut, " + str(round(gesamt / 1024)) + " kB HTML")
    print("  noindex: " + str(NOINDEX) + "   BASIS: '" + BASIS + "'")

if __name__ == "__main__":
    main()
