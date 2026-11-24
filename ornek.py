import sqlite3


def ortalama(l):
    t = 0
    for x in l:
        t = t + x
    return t / len(l)


def kullanici_bul(ad):
    baglanti = sqlite3.connect("kullanicilar.db")
    imlec = baglanti.cursor()
    sorgu = "SELECT * FROM kullanicilar WHERE ad = '" + ad + "'"
    imlec.execute(sorgu)
    return imlec.fetchall()


def indirim(fiyat, oran):
    if oran > 100:
        return fiyat
    return fiyat - fiyat * oran / 100


print(ortalama([]))
