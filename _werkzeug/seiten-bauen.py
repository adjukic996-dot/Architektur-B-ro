#!/usr/bin/env python3
"""Baut die Website aus inhalt.json, kapitel.json und bilder/verzeichnis.json.

Aufruf:  python3 _werkzeug/seiten-bauen.py

Fehlt ein Bild, ein Textbaustein oder ein Schluessel, bricht der Lauf mit einer
Meldung ab. Stillschweigend ueberspringen faellt monatelang niemandem auf.
"""
import json, pathlib, re, sys, html as H

WURZEL = pathlib.Path(__file__).resolve().parent.parent
INHALT  = json.loads((WURZEL/"inhalt.json").read_text())
KAPITEL = json.loads((WURZEL/"kapitel.json").read_text())
BILDER  = json.loads((WURZEL/"bilder"/"verzeichnis.json").read_text())

NOINDEX = True          # vor dem Livegang auf False, siehe UEBERGABE.md
DOMAIN  = "https://www.bruecknerarchitekten.com"

# Die Fehlerseite wird aus jeder Tiefe ausgeliefert und braucht deshalb absolute
# Pfade. Absolut heisst "ab der Wurzel der Domain" — GitHub Pages liefert aber
# in einem Unterordner aus. BASIS schiebt die Pfade entsprechend.
#   GitHub Pages:            "/Architektur-B-ro"
#   Vercel oder eigene Domain: ""   (dort ist die Seite schon ganz oben)
BASIS = "/Architektur-B-ro"

# ---------------------------------------------------------------- Seitenplan
# (Quelle in inhalt.json, Zieladresse, Menuetitel, Art)
HAUPT = [
    ("startseite",                                          "",                  "Start",            "start"),
    ("projekte",                                            "projekte",          "Projekte",         "projektliste"),
    ("generalplanung",                                      "generalplanung",    "Generalplanung",   "thema"),
    ("modulares-bauen-architektur-revolutioniert",           "modulares-bauen",   "Modulares Bauen",  "thema"),
    ("beitraege__referenzen",                               "referenzen",        "Referenzen",       "einfach"),
    ("leistungen",                                          "leistungen",        "Leistungen",       "thema"),
    ("von-der-kiste-zur-piazza-fachmarktzentren-neu-gedacht","fachmarktzentren",  "Fachmarktzentren", "thema"),
    ("bauen-im-bestand",                                    "bauen-im-bestand",  "Bauen im Bestand", "thema"),
    ("esg",                                                 "esg",               "ESG",              "thema"),
    ("kontakt",                                             "kontakt",           "Kontakt",          "kontakt"),
]
MENUE = [(z, t) for _, z, t, _ in HAUPT if z != ""]

PROJEKTE = sorted(k for k in INHALT
                  if k.startswith("beitraege__") and k != "beitraege__referenzen")

# ------------------------------------------------------------------ Werkzeug
def e(s):
    return H.escape(str(s), quote=False)

def pfad(tiefe):
    """Verweis auf die Wurzel. Bewusst './' bzw. '../', nie 'index.html' —
    sonst leitet der Hoster um und relative Pfade brechen (bei MAT passiert)."""
    return "../" * tiefe if tiefe else "./"

def zeilen(text, i0=0):
    """Ueberschrift in Zeilen zerlegen, jede in ihr eigenes Fenster."""
    teile = [t.strip() for t in re.split(r"\n+", text) if t.strip()]
    if not teile: teile = [text]
    return "".join(
        f'<span class="z"><i style="--i:{i0+i}">{e(t)}</i></span>' for i, t in enumerate(teile))

def kuerzen(text, laenge):
    """An der Wortgrenze kuerzen. Ein Satz, der mitten im Wort abbricht,
    sieht nach Fehler aus — auch wenn er technisch keiner ist."""
    text = " ".join(text.split())
    if len(text) <= laenge: return text
    schnitt = text[:laenge].rsplit(" ", 1)[0]
    return schnitt.rstrip(" ,;–-") + " …"

def absaetze(text, klasse=""):
    k = f' class="{klasse}"' if klasse else ""
    return "".join(f"<p{k}>{e(a)}</p>" for a in re.split(r"\n\s*\n", text) if a.strip())

OFFENE_BILDTEXTE = []          # wird am Ende als offene-bildtexte.md ausgegeben

def bild(url, tiefe, alt="", klasse="rahmen", lazy=True, sizes="100vw", herkunft=""):
    if url not in BILDER:
        raise SystemExit(f"ABBRUCH: Bild nicht im Verzeichnis: {url}\n"
                         f"  Erst  python3 _werkzeug/bilder-wandeln.py  laufen lassen.")
    g = BILDER[url]["groessen"]
    if not g:
        raise SystemExit(f"ABBRUCH: keine Groessen fuer {url}")
    gross = g.get("1800") or g.get(1800) or list(g.values())[-1]
    P = pfad(tiefe)
    # Alle vorhandenen Groessen anbieten; der Browser waehlt nach sizes aus.
    teile = []
    for schluessel in ("600", "1200", "1800"):
        v = g.get(schluessel) or g.get(int(schluessel))
        if v: teile.append(f'{P}bilder/{v["datei"]} {v["b"]}w')
    satz = ", ".join(teile) or f'{P}bilder/{gross["datei"]} {gross["b"]}w'
    laden = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    if not alt.strip() and klasse:          # Dekoration (klasse="") bleibt bewusst leer
        # Behelf aus dem Seitentitel: belegbar, aber keine Beschreibung des Motivs.
        alt = f"{herkunft} — Bild" if herkunft else "Bild"
        OFFENE_BILDTEXTE.append((herkunft or "?", BILDER[url]["groessen"]
                                 and list(BILDER[url]["groessen"].values())[0]["datei"]))
    innen = (f'<img src="{P}bilder/{gross["datei"]}" srcset="{satz}" sizes="{sizes}" '
             f'width="{gross["b"]}" height="{gross["h"]}" alt="{e(alt)}"{laden}>')
    return f'<figure class="{klasse}" style="margin:0">{innen}</figure>' if klasse else innen

def erstes_bild(bloecke):
    for b in bloecke:
        if b["art"] == "hintergrund" and b["bilder"]: 
            for u in b["bilder"]:
                if u in BILDER: return u
        if b["art"] == "bild" and b["quelle"] in BILDER: return b["quelle"]
        if b["art"] == "galerie":
            for x in b["bilder"]:
                if x["quelle"] in BILDER: return x["quelle"]
    return None

# -------------------------------------------------------------------- Gerüst
BEWEGUNG_JS = r"""
(function(){
  var sanft = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Einblenden, zeilenweiser Einzug, Bildzoom */
  var ziele = document.querySelectorAll("[data-auf], .z, .rahmen");
  if (!("IntersectionObserver" in window) || sanft){
    ziele.forEach(function(x){ x.classList.add("da"); });
  } else {
    var b = new IntersectionObserver(function(ein){
      ein.forEach(function(x){ if(x.isIntersecting){ x.target.classList.add("da"); b.unobserve(x.target); } });
    }, { rootMargin:"0px 0px -10% 0px", threshold:.06 });
    ziele.forEach(function(x){ b.observe(x); });
    requestAnimationFrame(function(){
      document.querySelectorAll(".hero .z").forEach(function(x){ x.classList.add("da"); });
    });
  }

  /* Menü */
  var knopf = document.getElementById("menue-knopf"), menue = document.getElementById("menue");
  if (knopf && menue){
    function um(auf){
      knopf.setAttribute("aria-expanded", auf ? "true" : "false");
      menue.classList.toggle("auf", auf);
      document.body.style.overflow = auf ? "hidden" : "";
      if (auf) menue.querySelector("a").focus();
    }
    knopf.addEventListener("click", function(){ um(knopf.getAttribute("aria-expanded") !== "true"); });
    addEventListener("keydown", function(ev){ if(ev.key === "Escape") um(false); });
    menue.addEventListener("click", function(ev){ if(ev.target.tagName === "A") um(false); });
  }

  /* Kopfzeile, Parallaxe, Kapitelspur — alles in einer Schleife */
  var kopf    = document.querySelector(".kopf");
  var schicht = [].slice.call(document.querySelectorAll("[data-parallaxe]"));
  var punkte  = [].slice.call(document.querySelectorAll(".kapitel"));
  var spur    = [].slice.call(document.querySelectorAll(".spur li"));
  var balken  = document.querySelector(".spur__balken i");
  var laeuft = false, zuletzt = -1;

  function zeichne(){
    laeuft = false;
    if (kopf) kopf.classList.toggle("fest", scrollY > 40);

    if (!sanft) schicht.forEach(function(s){
      var r = s.parentElement.getBoundingClientRect();
      if (r.bottom < -200 || r.top > innerHeight + 200) return;
      var mitte = r.top + r.height/2 - innerHeight/2;
      s.style.transform = "translate3d(0," + (-mitte * parseFloat(s.dataset.parallaxe)).toFixed(1) + "px,0)";
    });

    if (!punkte.length) return;
    var beste = 0, nah = Infinity, ziel = innerHeight * 0.32;
    punkte.forEach(function(k, i){
      var d = Math.abs(k.getBoundingClientRect().top - ziel);
      if (d < nah){ nah = d; beste = i; }
    });
    if (balken) balken.style.setProperty("--p", ((beste+1)/punkte.length*100).toFixed(1) + "%");
    if (beste === zuletzt) return;
    zuletzt = beste;
    spur.forEach(function(li, i){ li.classList.toggle("an", i === beste); });
  }
  addEventListener("scroll", function(){ if(!laeuft){ laeuft = true; requestAnimationFrame(zeichne); } }, {passive:true});
  addEventListener("resize", zeichne, {passive:true});
  zeichne();
})();
"""

def kopf(titel, beschreibung, ziel, tiefe, bildurl=None):
    P = pfad(tiefe)
    kanon = DOMAIN + "/" + (ziel + "/" if ziel else "")
    robots = '<meta name="robots" content="noindex, nofollow">\n' if NOINDEX else ""
    # Eine Fehlerseite bekommt kein canonical — sie ist keine Adresse, die
    # indexiert werden soll.
    kanon_tag = "" if ziel == "404" else f'<link rel="canonical" href="{kanon}">\n'
    og = ""
    if bildurl and bildurl in BILDER:
        g = BILDER[bildurl]["groessen"]
        d = (g.get("1800") or list(g.values())[-1])["datei"]
        og = f'<meta property="og:image" content="{DOMAIN}/bilder/{d}">\n'
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titel)} — Brückner Architekten</title>
<meta name="description" content="{e(beschreibung)[:300]}">
{robots}{kanon_tag}<meta property="og:title" content="{e(titel)} — Brückner Architekten">
<meta property="og:type" content="website">
{og}<link rel="preload" href="{P}fonts/instrument-sans.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{P}fonts/instrument-serif.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{P}stil.css">
</head>
<body>

<header class="kopf">
  <div class="bahn kopf__innen">
    <a class="marke" href="{P}"><span>Brückner</span><span>Architekten</span></a>
    <button class="menue-knopf" id="menue-knopf" type="button"
            aria-expanded="false" aria-controls="menue" aria-label="Menü öffnen">
      <i></i><i></i>
    </button>
  </div>
</header>

<nav class="menue" id="menue" aria-label="Hauptmenü">
  <div class="bahn">
    <ul>
{menue_eintraege(ziel, tiefe)}
    </ul>
    <div class="menue__fuss">
      <a href="{P}impressum/">Impressum</a>
      <a href="{P}datenschutz/">Datenschutz</a>
      <a href="tel:+498912664000">+49 (89) 1266 40-0</a>
      <a href="mailto:date@bruecknerarchitekten.de">date@bruecknerarchitekten.de</a>
    </div>
  </div>
</nav>

<main>
"""

def menue_eintraege(aktiv, tiefe):
    P = pfad(tiefe)
    aus = []
    for i, (z, t) in enumerate(MENUE):
        hier = ' aria-current="page"' if z == aktiv else ""
        aus.append(f'      <li><a href="{P}{z}/" style="--i:{i}"{hier}>{e(t)}</a></li>')
    return "\n".join(aus)

def schlussband(tiefe, hell=False):
    P = pfad(tiefe)
    k = " hell" if hell else ""
    return f"""
  <section class="schluss{k}">
    <div class="bahn">
      <h2 data-auf>{zeilen("Wir haben Ihr Interesse geweckt?")}</h2>
      <p data-auf style="--verzug:1">Sie haben Fragen oder wollen einen Termin mit uns vereinbaren?</p>
      <div class="schluss__knoepfe" data-auf style="--verzug:2">
        <a class="knopf" href="{P}kontakt/"><span>Kontakt aufnehmen</span></a>
        <a class="knopf" href="tel:+498912664000"><span>+49 (89) 1266 40-0</span></a>
      </div>
    </div>
  </section>
"""

def fuss(tiefe):
    P = pfad(tiefe)
    spalten = "\n".join(f'<li><a href="{P}{z}/">{e(t)}</a></li>' for z, t in MENUE)
    schild = '<a class="schild" href="#">Entwurf — nicht freigegeben</a>' if NOINDEX else ""
    return f"""
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
      <div>
        <h2>Seiten</h2>
        <ul>{spalten}</ul>
      </div>
      <div>
        <h2>Rechtliches</h2>
        <ul>
          <li><a href="{P}impressum/">Impressum</a></li>
          <li><a href="{P}datenschutz/">Datenschutz</a></li>
        </ul>
      </div>
    </div>
    <div class="fuss__unten">
      <span>© Brückner Architekten GmbH</span>
      <span>Entwurf webgipfel — nicht freigegeben</span>
    </div>
  </div>
</footer>
{schild}
<script>{BEWEGUNG_JS}</script>
</body>
</html>
"""

# ------------------------------------------------------------------ Seitenarten
def hero(titel, text, bildurl, tiefe, klein=False):
    k = " hero--klein" if klein else ""
    b = ""
    if bildurl:
        b = (f'<div class="hero__bild" data-parallaxe="0.18">'
             f'{bild(bildurl, tiefe, "", klasse="", lazy=False)}</div>')
    unter = f'<div class="hero__unter" data-auf style="--verzug:2"><p>{e(text)}</p></div>' if text else ""
    return f"""
  <section class="hero{k}">
    {b}
    <div class="hero__schleier"></div>
    <div class="bahn hero__innen">
      <h1>{zeilen(titel)}</h1>
      {unter}
    </div>
  </section>
"""

def ueberschriften(bloecke):
    return [b for b in bloecke if b["art"] == "ueberschrift"]

def thema_bauen(quelle, ziel, titel, tiefe):
    seite = INHALT[quelle]
    bl = seite["bloecke"]
    kap = KAPITEL.get(quelle)
    if not kap:
        raise SystemExit(f"ABBRUCH: keine Kapitel fuer '{quelle}' in kapitel.json")

    # Überschriften durchnummerieren, damit kapitel.json darauf zeigen kann
    nummern, n = {}, 0
    for i, b in enumerate(bl):
        if b["art"] == "ueberschrift":
            n += 1; nummern[n] = i

    h1 = next((b["text"] for b in bl if b["art"] == "ueberschrift" and b["stufe"] == 1), titel)
    aufm = erstes_bild(bl)
    aus = [hero(h1, seite.get("beschreibung", ""), aufm, tiefe)]

    # Kapitelspur
    spur = "\n".join(
        f'        <li><a href="#kapitel-{i+1}"><b>{i+1:02d}</b><span>{e(k["titel"])}</span></a></li>'
        for i, k in enumerate(kap))

    teile = []
    benutzte_bilder = {aufm}
    for i, k in enumerate(kap):
        inner = []
        for nr in k["abschnitte"]:
            if nr not in nummern:
                raise SystemExit(f"ABBRUCH: Abschnitt {nr} gibt es auf '{quelle}' nicht "
                                 f"(nur 1..{n}). kapitel.json pruefen.")
            start = nummern[nr]
            inner.append(f'<h3>{e(bl[start]["text"])}</h3>')
            j = start + 1
            while j < len(bl) and bl[j]["art"] != "ueberschrift":
                b = bl[j]
                if b["art"] == "text":
                    inner.append(absaetze(b["text"]))
                elif b["art"] == "bild" and b["quelle"] in BILDER and b["quelle"] not in benutzte_bilder:
                    benutzte_bilder.add(b["quelle"])
                    inner.append(f'<div data-auf style="margin-block:var(--s3)">'
                                 f'{bild(b["quelle"], tiefe, b.get("alt",""), sizes="(min-width:64rem) 60vw, 100vw", herkunft=titel)}</div>')
                j += 1
        teile.append(f"""
      <section class="kapitel" id="kapitel-{i+1}">
        <h2 class="kapitel__titel" data-auf>{e(k["titel"])}</h2>
        {"".join(inner)}
      </section>""")

    aus.append(f"""
  <div class="bahn" style="padding-block:var(--s6)">
    <div class="mit-spur">
      <nav class="spur" aria-label="Abschnitte dieser Seite">
        <ol>
{spur}
        </ol>
        <div class="spur__balken"><i></i></div>
      </nav>
      <div>{"".join(teile)}</div>
    </div>
  </div>""")

    # Bildband aus einem noch ungenutzten Bild
    rest = [u for u in (erstes_bild([b]) for b in bl) if u and u not in benutzte_bilder]
    if rest:
        aus.append(f"""
  <section class="band" style="padding:0">
    <div class="band__bild" data-parallaxe="0.14">{bild(rest[0], tiefe, "", klasse="", lazy=True)}</div>
  </section>""")

    aus.append(schlussband(tiefe))
    return "".join(aus)

def einfach_bauen(quelle, titel, tiefe):
    seite = INHALT[quelle]; bl = seite["bloecke"]
    h1 = next((b["text"] for b in bl if b["art"] == "ueberschrift" and b["stufe"] == 1), titel)
    aufm = erstes_bild(bl)
    aus = [hero(h1, seite.get("beschreibung",""), aufm, tiefe, klein=True)]
    inner = []
    for b in bl:
        if b["art"] == "ueberschrift" and b["text"] != h1:
            inner.append(f'<h2 class="abs-titel" data-auf style="margin-top:var(--s5)">{e(b["text"])}</h2>')
        elif b["art"] == "text":
            inner.append(f'<div class="abs-text" data-auf>{absaetze(b["text"])}</div>')
    aus.append(f'<section class="bahn">{"".join(inner)}</section>')
    aus.append(schlussband(tiefe))
    return "".join(aus)

def projekt_bauen(quelle, tiefe):
    seite = INHALT[quelle]; bl = seite["bloecke"]
    h1 = next((b["text"] for b in bl if b["art"] == "ueberschrift"), seite["titel"])
    aufm = erstes_bild(bl)
    aus = [hero(h1, seite.get("beschreibung",""), aufm, tiefe, klein=True)]
    inner, gesehen = [], {aufm}
    for b in bl:
        if b["art"] == "ueberschrift" and b["text"] != h1:
            inner.append(f'<h2 class="abs-titel" data-auf style="margin-top:var(--s5)">{e(b["text"])}</h2>')
        elif b["art"] == "text":
            inner.append(f'<div class="abs-text" data-auf>{absaetze(b["text"])}</div>')
        elif b["art"] in ("bild","galerie","hintergrund"):
            urls = ([b["quelle"]] if b["art"]=="bild"
                    else [x["quelle"] for x in b["bilder"]] if b["art"]=="galerie"
                    else b["bilder"])
            for u in urls:
                if u in BILDER and u not in gesehen:
                    gesehen.add(u)
                    inner.append(f'<div data-auf style="margin-block:var(--s4)">'
                                 f'{bild(u, tiefe, "", sizes="(min-width:68rem) 70vw, 100vw", herkunft=seite["titel"])}</div>')
    aus.append(f'<section class="bahn">{"".join(inner)}</section>')
    aus.append(schlussband(tiefe))
    return "".join(aus)

def projektliste_bauen(tiefe):
    karten = []
    for i, k in enumerate(PROJEKTE):
        s = INHALT[k]; slug = k.replace("beitraege__","")
        u = erstes_bild(s["bloecke"])
        bildteil = (bild(u, tiefe, s["titel"], sizes="(min-width:68rem) 33vw, (min-width:44rem) 50vw, 100vw")
                    if u else '<div class="rahmen" style="aspect-ratio:4/3;background:rgba(224,220,219,.07)"></div>')
        karten.append(f"""
      <a class="karte" href="{pfad(tiefe)}projekte/{slug}/" data-auf style="--verzug:{i%3}">
        {bildteil}
        <h3>{e(s["titel"])}</h3>
      </a>""")
    return f"""
  <section class="hero hero--klein">
    <div class="hero__schleier"></div>
    <div class="bahn hero__innen">
      <h1>{zeilen("Projekte")}</h1>
      <div class="hero__unter" data-auf style="--verzug:1">
        <p>{len(PROJEKTE)} Bauten und Entwürfe aus dem Werk von Brückner Architekten.</p>
      </div>
    </div>
  </section>
  <section class="bahn">
    <h2 class="kennung" data-auf>Alle Projekte</h2>
    <div class="raster">{"".join(karten)}</div></section>
{schlussband(tiefe)}"""

def start_bauen(tiefe):
    s = INHALT["startseite"]; bl = s["bloecke"]
    aufm = erstes_bild(bl)
    h1 = "Sehnsuchtsorte schaffen."
    aus = [hero(h1, "", aufm, tiefe)]
    haltung = next((b["text"] for b in bl if b["art"]=="text" and len(b["text"])>200), "")
    erster = re.split(r"\n\s*\n", haltung)[0] if haltung else ""
    haltung_html = absaetze(erster)
    aus.append(f"""
  <section class="bahn">
    <div class="abs-text" data-auf style="max-width:40ch;font-size:clamp(1.25rem,2.6vw,1.75rem);
         line-height:1.3;font-family:var(--anzeige)">{haltung_html}</div>
  </section>""")
    # Themeneinstiege als große Reihen
    reihen = []
    themen = [(q, z, t) for q, z, t, art in HAUPT if art == "thema"]
    for i, (q, z, t) in enumerate(themen, 1):
        txt = kuerzen(INHALT[q].get("beschreibung", ""), 110)
        reihen.append(f"""
      <a class="reihe" href="{pfad(tiefe)}{z}/" data-auf>
        <span class="reihe__nr">{i:02d}</span>
        <h3>{e(t)}</h3>
        <span class="reihe__text">{e(txt)}</span>
        <span class="reihe__pfeil">→</span>
      </a>""")
    aus.append(f'<section class="bahn"><h2 class="kennung" data-auf>Themen</h2>{"".join(reihen)}</section>')
    # Ausgewählte Projekte
    karten = []
    for i, k in enumerate(PROJEKTE[:6]):
        p = INHALT[k]; slug = k.replace("beitraege__","")
        u = erstes_bild(p["bloecke"])
        if not u: continue
        karten.append(f"""
      <a class="karte" href="{pfad(tiefe)}projekte/{slug}/" data-auf style="--verzug:{i%3}">
        {bild(u, tiefe, p["titel"], sizes="(min-width:68rem) 33vw, 100vw")}
        <h3>{e(p["titel"])}</h3>
      </a>""")
    aus.append(f"""
  <section class="bahn">
    <h2 class="kennung" data-auf>Ausgewählte Projekte</h2>
    <div class="raster">{"".join(karten)}</div>
    <p style="margin-top:var(--s4)" data-auf>
      <a class="knopf" href="{pfad(tiefe)}projekte/"><span>Alle Projekte</span></a></p>
  </section>""")
    aus.append(schlussband(tiefe))
    return "".join(aus)

def kontakt_bauen(tiefe):
    titelzeilen = zeilen("Kontaktieren\nSie uns")
    return f"""
  <section class="hero hero--klein">
    <div class="hero__schleier"></div>
    <div class="bahn hero__innen">
      <h1>{titelzeilen}</h1>
    </div>
  </section>
  <section class="bahn">
    <div class="abs-text" data-auf>
      <p><strong>Brückner Architekten GmbH</strong><br>
         Gabriel-Max-Straße 4<br>81545 München</p>
      <p style="margin-top:var(--s3)">
        Telefon <a href="tel:+498912664000">+49 (89) 1266 40-0</a><br>
        E-Mail <a href="mailto:date@bruecknerarchitekten.de">date@bruecknerarchitekten.de</a></p>
      <p style="margin-top:var(--s3)" class="luecke">[FEHLT: Öffnungszeiten, Anfahrtsbeschreibung,
        Ansprechpartner je Thema — auf der bestehenden Seite nur als eingebettete Karte und
        Calendly vorhanden, beides wird nicht übernommen (DESIGN 8).]</p>
    </div>
  </section>
{schlussband(tiefe)}"""

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
   verpflichtet, übermittelte oder gespeicherte fremde Informationen zu überwachen oder nach Umständen
   zu forschen, die auf eine rechtswidrige Tätigkeit hinweisen.</p>
<h2>Haftung für Links</h2>
<p>Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen Einfluss haben.
   Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen.</p>
<p class="luecke">[ENTWURF — vor dem Livegang anwaltlich prüfen lassen. Dies ist keine Rechtsauskunft.]</p>"""

DATENSCHUTZ = """<p class="luecke">[ENTWURF — neu geschrieben, weil diese Seite anders als die bisherige
   keine fremden Dienste einbindet. Vor dem Livegang anwaltlich prüfen lassen. Dies ist keine Rechtsauskunft.]</p>
<h2>Verantwortlicher</h2>
<p>Brückner Architekten GmbH<br>Gabriel-Max-Straße 4<br>81545 München<br>
   E-Mail: date@bruecknerarchitekten.de</p>
<p class="luecke">[FEHLT: Datenschutzbeauftragter — nach § 38 BDSG ab 20 Personen, die ständig mit der
   automatisierten Verarbeitung befasst sind. Ist einer benannt?]</p>
<h2>Welche Daten diese Website verarbeitet</h2>
<p>Diese Website bindet keine Dienste Dritter ein. Es werden keine Schriften, Karten, Videos,
   Terminbuchungen oder Statistikdienste von fremden Servern geladen. Es werden keine Cookies gesetzt,
   die eine Einwilligung erfordern würden. Deshalb gibt es auf dieser Website kein Einwilligungsbanner.</p>
<h2>Server-Protokolldateien</h2>
<p>Beim Aufruf dieser Website werden durch den Hoster automatisch Daten erhoben, die Ihr Browser
   übermittelt: aufgerufene Adresse, Zeitpunkt, übertragene Datenmenge, Browsertyp und Betriebssystem
   sowie die IP-Adresse. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO — das berechtigte Interesse am
   technisch sicheren Betrieb.</p>
<p class="luecke">[FEHLT: Name und Anschrift des Hosters sowie Speicherdauer der Protokolldateien,
   sobald das Hosting entschieden ist. Auftragsverarbeitungsvertrag ist dann abzuschließen.]</p>
<h2>Kontaktaufnahme</h2>
<p>Wenn Sie uns per E-Mail oder Telefon kontaktieren, verarbeiten wir Ihre Angaben zur Bearbeitung der
   Anfrage. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, soweit die Anfrage der Anbahnung eines
   Vertrags dient, sonst lit. f. Wir löschen die Daten, sobald sie nicht mehr erforderlich sind;
   gesetzliche Aufbewahrungsfristen nach § 257 HGB und § 147 AO bleiben unberührt.</p>
<h2>Ihre Rechte</h2>
<p>Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung (Art. 17),
   Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch (Art. 21).
   Außerdem können Sie sich bei einer Aufsichtsbehörde beschweren (Art. 77 DSGVO) — zuständig ist in der
   Regel die Behörde Ihres Aufenthaltsorts oder unseres Firmensitzes.</p>"""

def rechtstext_bauen(titel, html, tiefe):
    return f"""
  <section class="hero hero--klein">
    <div class="hero__schleier"></div>
    <div class="bahn hero__innen"><h1>{zeilen(titel)}</h1></div>
  </section>
  <section class="bahn"><div class="rechtstext" data-auf>{html}</div></section>
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
            raise SystemExit(f"ABBRUCH: '{quelle}' fehlt in inhalt.json")
        tiefe = len([x for x in ziel.split("/") if x])
        s = INHALT[quelle]
        aufm = erstes_bild(s["bloecke"])
        rumpf = {"start": lambda: start_bauen(tiefe),
                 "thema": lambda: thema_bauen(quelle, ziel, titel, tiefe),
                 "projektliste": lambda: projektliste_bauen(tiefe),
                 "kontakt": lambda: kontakt_bauen(tiefe),
                 "einfach": lambda: einfach_bauen(quelle, titel, tiefe)}[art]()
        html = kopf(titel, s.get("beschreibung",""), ziel, tiefe, aufm) + rumpf + fuss(tiefe)
        gebaut.append(schreiben(ziel, html))

    for k in PROJEKTE:
        slug = k.replace("beitraege__","")
        ziel = f"projekte/{slug}"; tiefe = 2
        s = INHALT[k]
        html = (kopf(s["titel"], s.get("beschreibung",""), ziel, tiefe, erstes_bild(s["bloecke"]))
                + projekt_bauen(k, tiefe) + fuss(tiefe))
        gebaut.append(schreiben(ziel, html))

    for ziel, titel, inhalt in [("impressum","Impressum",IMPRESSUM),
                                ("datenschutz","Datenschutz",DATENSCHUTZ)]:
        html = kopf(titel, f"{titel} von Brückner Architekten GmbH, München.", ziel, 1) \
             + rechtstext_bauen(titel, inhalt, 1) + fuss(1)
        gebaut.append(schreiben(ziel, html))

    # Fehlerseite: liegt an der Wurzel, wird aus jeder Tiefe ausgeliefert ->
    # absolute Pfade, sonst brechen die Verweise (bekannte Falle).
    fehler_titel = zeilen("Seite nicht\ngefunden")
    html = (kopf("Seite nicht gefunden", "Diese Seite gibt es nicht.", "404", 0)
            .replace('href="./', f'href="{BASIS}/').replace('"./stil.css"', f'"{BASIS}/stil.css"')
            .replace('href="./fonts/', f'href="{BASIS}/fonts/')
            + f"""
  <section class="hero hero--klein">
    <div class="hero__schleier"></div>
    <div class="bahn hero__innen">
      <h1>{fehler_titel}</h1>
      <div class="hero__unter" data-auf><p>Die Adresse existiert nicht oder nicht mehr.</p>
      <a class="knopf" href="{BASIS}/"><span>Zur Startseite</span></a></div>
    </div>
  </section>"""
            + fuss(0).replace('href="./', f'href="{BASIS}/'))
    p = WURZEL/"404.html"; p.write_text(html); gebaut.append((p, len(html)))

    (WURZEL/"robots.txt").write_text(
        "User-agent: *\nDisallow: /\n" if NOINDEX else
        f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")

    if OFFENE_BILDTEXTE:
        md = ["# Offene Bildbeschreibungen", "",
                  "Diese Bilder tragen Inhalt und brauchen einen Alternativtext, der sagt,",
                  "WAS zu sehen ist. Der jetzige Text ist ein Behelf aus dem Seitentitel.",
                  "Erfinden lässt sich das nicht — das weiß nur der Kunde.", "",
                  "| Seite | Bilddatei | Beschreibung eintragen |", "|---|---|---|"]
        for h, d in sorted(set(OFFENE_BILDTEXTE)):
            md.append(f"| {h} | `{d}` | |")
        (WURZEL/"offene-bildtexte.md").write_text("\n".join(md) + "\n")
        print(f"  {len(set(OFFENE_BILDTEXTE))} Bilder ohne echte Beschreibung -> offene-bildtexte.md")

    gesamt = sum(n for _, n in gebaut)
    print(f"{len(gebaut)} Seiten gebaut, {gesamt/1024:.0f} kB HTML")
    print(f"  noindex: {NOINDEX}   robots.txt: {'alles gesperrt' if NOINDEX else 'offen'}")

if __name__ == "__main__":
    main()
