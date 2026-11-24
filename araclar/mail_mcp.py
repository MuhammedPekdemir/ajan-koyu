"""Kişisel outlook.com hesabı için SADECE OKUMA yapan mail MCP sunucusu.

Microsoft Graph API kullanır. Mail gönderme, silme, taşıma yoktur; izin de sadece Mail.Read.

İlk kurulum:
    1. Azure'da uygulama kaydı yapın ve client ID'yi .mcp.json içindeki MAIL_CLIENT_ID'ye yazın.
    2. Bir kez terminalde giriş yapın:
           $env:MAIL_CLIENT_ID = "<client-id>"
           python araclar/mail_mcp.py giris
       Ekrandaki kodu tarayıcıda girip hesabınızla onay verin.
       Giriş bilgisi araclar/.mail_token.json dosyasında saklanır (şifre değil, yenilenebilir anahtar).
Sonrasında Claude Code sunucuyu kendisi başlatır.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import msal

KLASOR = os.path.dirname(os.path.abspath(__file__))
TOKEN_DOSYASI = os.path.join(KLASOR, ".mail_token.json")
YETKI = "https://login.microsoftonline.com/consumers"
IZINLER = ["Mail.Read"]
GRAPH = "https://graph.microsoft.com/v1.0"


def uygulama():
    client_id = os.environ.get("MAIL_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("MAIL_CLIENT_ID ayarlı değil. .mcp.json dosyasına client ID'yi yazın.")
    onbellek = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_DOSYASI):
        with open(TOKEN_DOSYASI, encoding="utf-8") as f:
            onbellek.deserialize(f.read())
    return msal.PublicClientApplication(client_id, authority=YETKI, token_cache=onbellek), onbellek


def onbellegi_kaydet(onbellek):
    if onbellek.has_state_changed:
        with open(TOKEN_DOSYASI, "w", encoding="utf-8") as f:
            f.write(onbellek.serialize())


def erisim_anahtari():
    app, onbellek = uygulama()
    hesaplar = app.get_accounts()
    sonuc = app.acquire_token_silent(IZINLER, account=hesaplar[0]) if hesaplar else None
    onbellegi_kaydet(onbellek)
    if not sonuc or "access_token" not in sonuc:
        raise RuntimeError("Giriş yapılmamış ya da süresi dolmuş. Terminalde "
                           "'python araclar/mail_mcp.py giris' çalıştırın.")
    return sonuc["access_token"]


def graph_get(yol, parametreler=None, ek_basliklar=None):
    adres = GRAPH + yol
    if parametreler:
        adres += "?" + urllib.parse.urlencode(parametreler, quote_via=urllib.parse.quote)
    basliklar = {"Authorization": "Bearer " + erisim_anahtari(), "Accept": "application/json"}
    basliklar.update(ek_basliklar or {})
    istek = urllib.request.Request(adres, headers=basliklar, method="GET")
    with urllib.request.urlopen(istek, timeout=30) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def giris():
    app, onbellek = uygulama()
    akis = app.initiate_device_flow(scopes=IZINLER)
    if "user_code" not in akis:
        raise RuntimeError("Giriş başlatılamadı: " + json.dumps(akis, ensure_ascii=False))
    print(akis["message"])
    sonuc = app.acquire_token_by_device_flow(akis)
    onbellegi_kaydet(onbellek)
    if "access_token" in sonuc:
        print("Giriş başarılı.")
    else:
        print("Giriş başarısız:", sonuc.get("error_description", sonuc))
        sys.exit(1)


def sunucu():
    from mcp.server.mcpserver import MCPServer  # mcp 2.x (1.x'teki FastMCP'nin yeni adı)

    from mcp.server.mcpserver.exceptions import ToolError

    mcp = MCPServer("mail-okuyucu")

    def graph_get(*args, **kwargs):
        # Hata mesajı ajana açıkça ulaşsın diye ToolError'a çevrilir.
        try:
            return globals()["graph_get"](*args, **kwargs)
        except RuntimeError as hata:
            raise ToolError(str(hata)) from hata
        except urllib.error.HTTPError as hata:
            raise ToolError(f"Graph API hatası {hata.code}: {hata.read().decode('utf-8', 'replace')[:300]}") from hata

    @mcp.tool()
    def mailleri_listele(gun: int = 1, sadece_okunmamis: bool = False, adet: int = 25) -> list[dict]:
        """Gelen kutusundaki son maillerin listesi (sadece okuma).

        gun: kaç gün geriye bakılacağı (1 = son 24 saat). adet: en fazla 50.
        Her mail için id, konu, gönderen, tarih, okundu mu, önem, Outlook linki ve kısa önizleme döner.
        """
        baslangic = (datetime.now(timezone.utc) - timedelta(days=max(1, gun))).strftime("%Y-%m-%dT%H:%M:%SZ")
        filtre = f"receivedDateTime ge {baslangic}"
        if sadece_okunmamis:
            filtre += " and isRead eq false"
        veri = graph_get("/me/mailFolders/inbox/messages", {
            "$filter": filtre,
            "$orderby": "receivedDateTime desc",
            "$top": str(min(max(1, adet), 50)),
            "$select": "id,subject,from,receivedDateTime,isRead,importance,webLink,bodyPreview",
        })
        return [{
            "id": m["id"],
            "konu": m.get("subject") or "(konu yok)",
            "gonderen": ((m.get("from") or {}).get("emailAddress") or {}).get("address", ""),
            "gonderen_ad": ((m.get("from") or {}).get("emailAddress") or {}).get("name", ""),
            "tarih": m.get("receivedDateTime"),
            "okundu": m.get("isRead"),
            "onem": m.get("importance"),
            "link": m.get("webLink"),
            "onizleme": (m.get("bodyPreview") or "")[:300],
        } for m in veri.get("value", [])]

    @mcp.tool()
    def mail_oku(mail_id: str) -> dict:
        """Tek bir mailin içeriğini düz metin olarak getirir (sadece okuma, okundu işaretlenmez)."""
        m = graph_get("/me/messages/" + urllib.parse.quote(mail_id, safe=""),
                      {"$select": "subject,from,toRecipients,receivedDateTime,body,webLink"},
                      {"Prefer": 'outlook.body-content-type="text"'})
        return {
            "konu": m.get("subject"),
            "gonderen": ((m.get("from") or {}).get("emailAddress") or {}).get("address", ""),
            "alicilar": [r["emailAddress"]["address"] for r in m.get("toRecipients", [])],
            "tarih": m.get("receivedDateTime"),
            "link": m.get("webLink"),
            "icerik": ((m.get("body") or {}).get("content") or "")[:8000],
        }

    mcp.run()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "giris":
        giris()
    else:
        sunucu()
