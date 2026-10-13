#!/usr/bin/env python3
"""Liest die aufgenommenen Elementor-Seiten in eine Datenstruktur.

Aufruf:  python3 _werkzeug/inhalt-lesen.py
Ergebnis: inhalt.json  —  pro Seite Titel, Beschreibung und Bloecke in
Dokumentreihenfolge (ueberschrift / text / bild / galerie).

Erfindet nichts. Was nicht in der Aufnahme steht, steht auch hier nicht.
"""
import re, json, pathlib, html as H

ROH = pathlib.Path("_aufnahme/roh")
ZIEL = pathlib.Path("inhalt.json")

def saeubern(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</p>", "\n\n", s)
    # Ohne diese Zeile kleben Listenpunkte aneinander — auf /generalplanung/ entstand
    # so "1-9GrundstuecksanalyseMachtbarkeitsstudien", 41 Zeichen ohne Leerraum,
    # das die Seite auf 320 px um 41 px gesprengt hat.
    s = re.sub(r"(?is)</(li|h[1-6]|td|tr|div)>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = H.unescape(s).replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return "\n".join(z.strip() for z in s.split("\n")).strip()

# Widgets in Dokumentreihenfolge einsammeln
WIDGET = re.compile(
    r'<div[^>]*class="[^"]*elementor-widget[^"]*"[^>]*data-widget_type="([a-z0-9_.-]+)"[^>]*>(.*?)'
    r'(?=<div[^>]*data-widget_type=|<footer|</body)', re.I | re.S)

BILD = re.compile(r'(?i)<img[^>]+(?:data-src|src)="([^"]+\.(?:jpe?g|png|webp))"[^>]*>')
ALT  = re.compile(r'(?i)alt="([^"]*)"')
EINSTELLUNG = re.compile(r'data-settings="([^"]*)"')

def bloecke_aus(roh):
    """Alle Inhaltstraeger in Dokumentreihenfolge: Widgets UND Abschnitts-
    hintergruende. Elementor legt Aufmacherbilder als Diaschau im data-settings
    ab — ohne die faende man auf der Startseite kein einziges Bild."""
    marken = []

    for m in WIDGET.finditer(roh):
        typ, inhalt = m.group(1), m.group(2)
        art = typ.split(".")[0]
        if art == "heading":
            t = saeubern(inhalt)
            stufe = 1 if re.search(r"(?i)<h1", inhalt) else 2
            if t: marken.append((m.start(), {"art": "ueberschrift", "stufe": stufe, "text": t}))
        elif art in ("text-editor", "theme-post-content"):
            t = saeubern(inhalt)
            if len(t) > 24: marken.append((m.start(), {"art": "text", "text": t}))
        elif art in ("image", "theme-post-featured-image"):
            b = BILD.search(inhalt)
            if b:
                a = ALT.search(inhalt)
                marken.append((m.start(), {"art": "bild", "quelle": b.group(1),
                                           "alt": H.unescape(a.group(1)) if a else ""}))
        elif art in ("gallery", "image-gallery", "image-carousel"):
            bilder = [{"quelle": x.group(1), "alt": ""} for x in BILD.finditer(inhalt)]
            if bilder: marken.append((m.start(), {"art": "galerie", "bilder": bilder}))

    for m in EINSTELLUNG.finditer(roh):
        # Als JSON lesen, nicht mit einem Muster durchsuchen: sonst bleiben
        # \u00a9 und \u0308 als Buchstabenfolge stehen und die Datei wird nie gefunden.
        try:
            daten = json.loads(H.unescape(m.group(1)))
        except Exception:
            continue
        urls = []
        def sammeln(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "url" and isinstance(v, str): urls.append(v)
                    else: sammeln(v)
            elif isinstance(x, list):
                for v in x: sammeln(v)
        sammeln(daten)
        urls = [u for u in urls if re.search(r"(?i)\.(jpe?g|png|webp)$", u)]
        if urls:
            marken.append((m.start(), {"art": "hintergrund", "bilder": urls}))

    marken.sort(key=lambda x: x[0])
    return [b for _, b in marken]

def main():
    if not ROH.exists():
        raise SystemExit("FEHLER: _aufnahme/roh/ fehlt. Erst die Aufnahme laufen lassen.")
    seiten = {}
    for p in sorted(ROH.glob("*.html")):
        roh = p.read_text()
        titel = (re.search(r"(?is)<title>(.*?)</title>", roh) or [None, ""])[1]
        besch = (re.search(r'(?is)<meta name="description" content="(.*?)"', roh) or [None, ""])[1]
        b = bloecke_aus(roh)
        seiten[p.stem] = {
            "titel": H.unescape(titel).replace(" - Brückner Architekten München", "")
                                      .replace(" - Brückner Architekten", "").strip(),
            "beschreibung": H.unescape(besch).strip(),
            "bloecke": b,
        }
        ueber = sum(1 for x in b if x["art"] == "ueberschrift")
        txt   = sum(len(x["text"]) for x in b if x["art"] == "text")
        bild  = sum(1 if x["art"] == "bild" else len(x.get("bilder", [])) for x in b)
        print(f"  {p.stem[:52]:54} {ueber:>2} Ü  {txt:>6} Z  {bild:>2} Bild")
    ZIEL.write_text(json.dumps(seiten, ensure_ascii=False, indent=1))
    leer = [k for k, v in seiten.items() if not v["bloecke"]]
    print(f"\n{len(seiten)} Seiten -> {ZIEL}")
    if leer:
        print(f"OHNE INHALT ({len(leer)}): " + ", ".join(leer))

if __name__ == "__main__":
    main()
