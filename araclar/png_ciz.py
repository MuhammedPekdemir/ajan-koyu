"""Ek paket gerektirmeyen basit PNG çizici.

Kullanım:
    python araclar/png_ciz.py tasarim.json cikti.png

tasarim.json örneği:
{
  "genislik": 128,
  "yukseklik": 128,
  "arkaplan": "#1e1e2e",
  "sekiller": [
    {"tip": "dikdortgen", "x": 10, "y": 10, "g": 50, "y2": 30, "renk": "#f38ba8"},
    {"tip": "daire", "x": 64, "y": 64, "r": 30, "renk": "#a6e3a1"},
    {"tip": "ucgen", "noktalar": [[64, 10], [118, 118], [10, 118]], "renk": "#89b4fa"}
  ]
}

Şekiller:
  dikdortgen: x, y (sol üst köşe), g (genişlik), y2 (yükseklik), renk
  daire:      x, y (merkez), r (yarıçap), renk
  ucgen:      noktalar (3 nokta), renk
Renkler "#rrggbb" biçimindedir. Şekiller listedeki sırayla üst üste çizilir.
"""

import json
import struct
import sys
import zlib


def renk_coz(metin):
    metin = metin.lstrip("#")
    return tuple(int(metin[i:i + 2], 16) for i in (0, 2, 4))


def ucgen_icinde(px, py, a, b, c):
    def isaret(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    p = (px, py)
    d1, d2, d3 = isaret(p, a, b), isaret(p, b, c), isaret(p, c, a)
    negatif = d1 < 0 or d2 < 0 or d3 < 0
    pozitif = d1 > 0 or d2 > 0 or d3 > 0
    return not (negatif and pozitif)


def ciz(tasarim):
    g = int(tasarim["genislik"])
    y = int(tasarim["yukseklik"])
    if not (1 <= g <= 512 and 1 <= y <= 512):
        raise ValueError("Genişlik ve yükseklik 1 ile 512 arasında olmalı.")
    arka = renk_coz(tasarim.get("arkaplan", "#ffffff"))
    piksel = [[arka for _ in range(g)] for _ in range(y)]

    for sekil in tasarim.get("sekiller", []):
        renk = renk_coz(sekil["renk"])
        tip = sekil["tip"]
        if tip == "dikdortgen":
            for yy in range(max(0, sekil["y"]), min(y, sekil["y"] + sekil["y2"])):
                for xx in range(max(0, sekil["x"]), min(g, sekil["x"] + sekil["g"])):
                    piksel[yy][xx] = renk
        elif tip == "daire":
            cx, cy, r = sekil["x"], sekil["y"], sekil["r"]
            for yy in range(max(0, cy - r), min(y, cy + r + 1)):
                for xx in range(max(0, cx - r), min(g, cx + r + 1)):
                    if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                        piksel[yy][xx] = renk
        elif tip == "ucgen":
            a, b, c = [tuple(n) for n in sekil["noktalar"]]
            for yy in range(y):
                for xx in range(g):
                    if ucgen_icinde(xx + 0.5, yy + 0.5, a, b, c):
                        piksel[yy][xx] = renk
        else:
            raise ValueError(f"Bilinmeyen şekil tipi: {tip}")
    return g, y, piksel


def png_yaz(yol, g, y, piksel):
    ham = b"".join(b"\x00" + bytes(k for p in satir for k in p) for satir in piksel)

    def parca(tur, veri):
        return (struct.pack(">I", len(veri)) + tur + veri
                + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF))

    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(parca(b"IHDR", struct.pack(">IIBBBBB", g, y, 8, 2, 0, 0, 0)))
        f.write(parca(b"IDAT", zlib.compress(ham, 9)))
        f.write(parca(b"IEND", b""))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Kullanım: python araclar/png_ciz.py tasarim.json cikti.png")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        tasarim = json.load(f)
    g, y, piksel = ciz(tasarim)
    png_yaz(sys.argv[2], g, y, piksel)
    print(f"Yazıldı: {sys.argv[2]} ({g}x{y})")
