#!/usr/bin/env python3
"""Wandelt die aufgenommenen Bilder nach WebP in zwei Groessen.

Aufruf:  python3 _werkzeug/bilder-wandeln.py
Ergebnis: bilder/<name>-1200.webp und <name>-1800.webp  +  bilder/verzeichnis.json

Ein Bild, das in inhalt.json steht, aber nicht in der Aufnahme liegt, bricht den
Lauf ab. Stillschweigend ueberspringen faellt monatelang niemandem auf.
"""
import json, pathlib, re, sys
from PIL import Image

QUELLE = pathlib.Path("_aufnahme/bilder")
ZIEL   = pathlib.Path("bilder"); ZIEL.mkdir(exist_ok=True)
BREITEN = (600, 1200, 1800)

# Diese drei Bilder verweist die bestehende Seite auf die Subdomain
# neu.bruecknerarchitekten.com — die loest nicht mehr auf. Fuer Besucher der
# heutigen Seite sind das kaputte Bilder. Sie koennen nicht nachgebaut werden
# und stehen deshalb in der Liste offener Punkte (BRIEF 4.4), nicht hier.
TOTE_BILDER = {
    "https://neu.bruecknerarchitekten.com/wp-content/uploads/2022/08/04-jahreszeiten-Winter.webp",
    "https://neu.bruecknerarchitekten.com/wp-content/uploads/2022/08/03-jahreszeiten-Herbst.webp",
    "https://neu.bruecknerarchitekten.com/wp-content/uploads/2022/08/02-jahreszeiten-Sommer.webp",
}
GUETE = 78

def dateiname(url):
    return re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/")[-1].split("?")[0])

def kurzname(url):
    roh = dateiname(url).rsplit(".", 1)[0].lower()
    roh = re.sub(r"-(?:scaled|\d+x\d+)$", "", roh)
    roh = re.sub(r"[^a-z0-9]+", "-", roh).strip("-")
    return roh[:52] or "bild"

def bilder_aus(inhalt):
    """alle Bildadressen, die der Generator spaeter braucht"""
    aus = []
    for seite in inhalt.values():
        for b in seite["bloecke"]:
            if b["art"] == "bild":      aus.append(b["quelle"])
            elif b["art"] == "galerie": aus += [x["quelle"] for x in b["bilder"]]
            elif b["art"] == "hintergrund": aus += b["bilder"]
    return list(dict.fromkeys(aus))

def main():
    inhalt = json.loads(pathlib.Path("inhalt.json").read_text())
    urls = bilder_aus(inhalt)
    print(f"{len(urls)} Bilder aus inhalt.json\n")

    tot = [u for u in urls if u in TOTE_BILDER]
    urls = [u for u in urls if u not in TOTE_BILDER]
    if tot:
        print(f"UEBERSPRUNGEN — {len(tot)} Bilder liegen auf der toten Subdomain neu.:")
        for u in tot: print("   ", u.split("/")[-1])
        print()

    verzeichnis, fehlend = {}, []
    alt_summe = neu_summe = 0
    namen_vergeben = {}

    for url in urls:
        q = QUELLE / dateiname(url)
        if not q.exists():
            fehlend.append(url); continue
        name = kurzname(url)
        while name in namen_vergeben and namen_vergeben[name] != url:
            name += "-2"
        namen_vergeben[name] = url

        try:
            im = Image.open(q)
        except Exception as e:
            fehlend.append(f"{url}  (nicht lesbar: {e})"); continue

        durchsichtig = im.mode in ("RGBA", "LA", "P") and "transparency" in im.info or im.mode == "RGBA"
        im = im.convert("RGBA" if durchsichtig else "RGB")
        alt_summe += q.stat().st_size
        eintrag = {"quelle": url, "original": [im.width, im.height], "groessen": {}}

        for br in BREITEN:
            if im.width <= br and br != BREITEN[0]:
                continue                      # nie ueber die echte Aufloesung hinaus
            b = min(br, im.width)
            h = round(im.height * b / im.width)
            z = ZIEL / f"{name}-{br}.webp"
            im.resize((b, h), Image.LANCZOS).save(z, "WEBP", quality=GUETE, method=6)
            neu_summe += z.stat().st_size
            eintrag["groessen"][br] = {"datei": z.name, "b": b, "h": h, "bytes": z.stat().st_size}
        verzeichnis[url] = eintrag

    if fehlend:
        print("ABBRUCH — diese Bilder fehlen in der Aufnahme:")
        for f in fehlend: print("   ", f)
        sys.exit(1)

    (ZIEL / "verzeichnis.json").write_text(json.dumps(verzeichnis, ensure_ascii=False, indent=1))
    print(f"{len(verzeichnis)} Bilder gewandelt")
    print(f"vorher {alt_summe/1048576:>7.1f} MB")
    print(f"nachher{neu_summe/1048576:>7.1f} MB   ({100-neu_summe/alt_summe*100:.1f} % weniger)")

if __name__ == "__main__":
    main()
