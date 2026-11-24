"""Ajan Köyü yerel sunucusu.

Çalıştır:  python site/sunucu.py
Aç:        http://localhost:8000

Her odaya yazılan mesaj, arkada Claude Code'u (claude.exe -p) o ajanla çalıştırır.
API anahtarı gerekmez; Claude Code'un giriş yaptığı hesap kullanılır.
Sadece bu bilgisayardan erişilir (127.0.0.1).
"""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJE = Path(__file__).resolve().parent.parent
SITE = Path(__file__).resolve().parent
CLAUDE = os.environ.get("CLAUDE_EXE", str(Path.home() / ".local" / "bin" / "claude.exe"))
PORT = 8000
ZAMAN_ASIMI = 900  # saniye

# Microsoft 365 bağlayıcısının terminal sürümündeki araç adları (sadece okuma).
MAIL_ARACLARI = os.environ.get(
    "MAIL_ARACLARI",
    "mcp__claude_ai_Microsoft_365__outlook_email_search mcp__claude_ai_Microsoft_365__read_resource",
)

ODALAR = {
    "top": ["--model", "opus", "--effort", "medium",
            "--allowedTools", "Agent Read Glob Grep WebSearch WebFetch Write(cv/ciktilar/**) Write(haber/**) " + MAIL_ARACLARI],
    "mail": ["--agent", "mail-ozetci", "--model", "sonnet", "--effort", "medium",
             "--allowedTools", MAIL_ARACLARI],
    "haber": ["--agent", "ai-haber", "--model", "sonnet", "--effort", "medium",
              "--allowedTools", "WebSearch WebFetch Read Write(haber/**)"],
    "cv": ["--agent", "cv-uyum", "--model", "sonnet", "--effort", "xhigh",
           "--allowedTools", "Read Glob Write(cv/ciktilar/**)"],
}

oturumlar = {}          # oda -> Claude Code oturum kimliği (sohbet devam etsin diye)
kilitler = {k: threading.Lock() for k in ODALAR}


def calistir(oda, mesaj):
    args = [CLAUDE, "-p", "--output-format", "json", "--permission-mode", "dontAsk"] + ODALAR[oda]
    if oda in oturumlar:
        args += ["--resume", oturumlar[oda]]
    sonuc = subprocess.run(args, input=mesaj, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(PROJE), timeout=ZAMAN_ASIMI)
    try:
        veri = json.loads(sonuc.stdout)
    except json.JSONDecodeError:
        hata = (sonuc.stderr or sonuc.stdout or "Bilinmeyen hata").strip()
        return {"hata": hata[:2000]}
    if veri.get("session_id"):
        oturumlar[oda] = veri["session_id"]
    if veri.get("is_error"):
        return {"hata": str(veri.get("result") or veri.get("subtype") or "Hata")[:2000]}
    return {"metin": veri.get("result", "")}


class Isleyici(BaseHTTPRequestHandler):
    def _gonder(self, kod, govde, tur="application/json; charset=utf-8"):
        veri = govde if isinstance(govde, bytes) else json.dumps(govde, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._gonder(200, (SITE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path.startswith("/cv/"):
            # Sadece cv/ciktilar altındaki HTML çıktıları göster.
            hedef = (PROJE / self.path.lstrip("/")).resolve()
            izinli = (PROJE / "cv" / "ciktilar").resolve()
            if izinli in hedef.parents and hedef.suffix == ".html" and hedef.is_file():
                return self._gonder(200, hedef.read_bytes(), "text/html; charset=utf-8")
        self._gonder(404, {"hata": "Bulunamadı"})

    def do_POST(self):
        uzunluk = int(self.headers.get("Content-Length") or 0)
        try:
            istek = json.loads(self.rfile.read(uzunluk) or b"{}")
        except json.JSONDecodeError:
            return self._gonder(400, {"hata": "Geçersiz istek"})
        oda = istek.get("oda")
        if oda not in ODALAR:
            return self._gonder(400, {"hata": "Böyle bir oda yok"})
        if self.path == "/api/sifirla":
            oturumlar.pop(oda, None)
            return self._gonder(200, {"tamam": True})
        if self.path != "/api/sohbet":
            return self._gonder(404, {"hata": "Bulunamadı"})
        mesaj = str(istek.get("mesaj") or "").strip()
        if not mesaj:
            return self._gonder(400, {"hata": "Mesaj boş"})
        if not kilitler[oda].acquire(blocking=False):
            return self._gonder(409, {"hata": "Bu oda şu an çalışıyor, bitmesini bekle."})
        try:
            self._gonder(200, calistir(oda, mesaj))
        except subprocess.TimeoutExpired:
            self._gonder(200, {"hata": "Zaman aşımı (15 dk)."})
        except FileNotFoundError:
            self._gonder(200, {"hata": "claude.exe bulunamadı: " + CLAUDE})
        finally:
            kilitler[oda].release()

    def log_message(self, fmt, *args):
        print("[sunucu]", fmt % args)


if __name__ == "__main__":
    print(f"Ajan Köyü: http://localhost:{PORT}  (kapatmak için Ctrl+C)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Isleyici).serve_forever()
