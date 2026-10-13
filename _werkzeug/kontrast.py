#!/usr/bin/env python3
"""Kontrastwerte nach WCAG 2.2 fuer die Farbpalette Brueckner Architekten.

Aufruf:  python3 _werkzeug/kontrast.py
Halbtransparente Farben werden vorher gegen ihren Untergrund aufgeloest —
sonst misst man die Farbe, nicht das, was man sieht.
"""
import colorsys

def _srgb(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def leuchtdichte(hexf):
    h = hexf.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)

def kontrast(vorne, hinten):
    a, b = leuchtdichte(vorne), leuchtdichte(hinten)
    return round((max(a, b) + 0.05) / (min(a, b) + 0.05), 2)

def aufloesen(vorne, hinten, deckkraft):
    """rgba(vorne, deckkraft) auf hinten -> tatsaechliche Farbe"""
    v = [int(vorne.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    h = [int(hinten.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(
        round(v[i] * deckkraft + h[i] * (1 - deckkraft)) for i in range(3))

def anpassen(hexf, ziel, grund, richtung=+1):
    """Farbton behalten, Helligkeit schieben, bis das Ziel erreicht ist."""
    h = hexf.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    farbton, hell, saettigung = colorsys.rgb_to_hls(r, g, b)
    for i in range(1, 400):
        l2 = min(1, max(0, hell + richtung * i * 0.0025))
        r2, g2, b2 = colorsys.hls_to_rgb(farbton, l2, saettigung)
        neu = "#%02x%02x%02x" % (round(r2*255), round(g2*255), round(b2*255))
        if kontrast(neu, grund) >= ziel:
            return neu, kontrast(neu, grund)
    return None, None

FARBEN = {
    "nacht": "#363C38", "elfenbein": "#E0DCDB", "messing": "#C0A177",
    "petrol": "#0B5368", "gedaempft-hell": "#AAA39A", "gedaempft-dunkel": "#676057",
    "weiss": "#FFFFFF",
}

PRUEFUNGEN = [
    ("Text auf Nacht",      "#363C38", ["elfenbein", "messing", "gedaempft-hell", "weiss"], 4.5),
    ("Text auf Elfenbein",  "#E0DCDB", ["nacht", "petrol", "gedaempft-dunkel"],             4.5),
    ("Text auf Petrol",     "#0B5368", ["weiss", "elfenbein"],                              4.5),
    ("Fokusring dunkel",    "#363C38", ["messing"],                                         3.0),
    ("Fokusring hell",      "#E0DCDB", ["petrol"],                                          3.0),
]

if __name__ == "__main__":
    fehler = 0
    for titel, grund, namen, ziel in PRUEFUNGEN:
        print(f"\n{titel}  (Ziel {ziel}:1, Grund {grund})")
        for n in namen:
            v = kontrast(FARBEN[n], grund)
            gut = v >= ziel
            fehler += 0 if gut else 1
            print(f"  {n:<18} {FARBEN[n]}  {v:>6}:1  {'ok' if gut else 'DURCHGEFALLEN'}")

    print("\nLinien: halbtransparentes Elfenbein auf Nacht")
    for d in (0.14, 0.20, 0.26, 0.32):
        f = aufloesen("#E0DCDB", "#363C38", d)
        print(f"  {int(d*100):>3} %  -> {f}  {kontrast(f, '#363C38'):>5}:1")
    print("\n  Hinweis: keiner dieser Werte erreicht 3:1. Trennlinien gelten als")
    print("  Dekoration; alles Zustandstragende bekommt eine deckende Farbe.")

    print(f"\n{'Alle Pruefungen bestanden.' if not fehler else str(fehler) + ' DURCHGEFALLEN'}")
