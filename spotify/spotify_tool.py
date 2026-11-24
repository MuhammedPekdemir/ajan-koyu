"""Spotify Web API aracı (sadece standart kütüphane).

Kullanım:
  python spotify_tool.py giris                      # ilk sefer: tarayıcıda izin ver
  python spotify_tool.py zevk [--begeni 300]        # beğenilenler + en çok dinlenenler + son çalınanlar (JSON)
  python spotify_tool.py liste --ad cl --dosya sarkilar.txt [--hedef 100]

sarkilar.txt: her satırda "Şarkı - Sanatçı".
Client ID: SPOTIFY_CLIENT_ID ortam değişkeni ya da bu klasördeki client_id.txt.
Spotify uygulamasında Redirect URI: http://127.0.0.1:8888/callback
"""
import argparse, base64, hashlib, http.server, json, os, secrets, sys, time
import urllib.parse, urllib.request, urllib.error, webbrowser
from collections import Counter

DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(DIR, ".token.json")
REDIRECT = "http://127.0.0.1:8888/callback"
SCOPES = ("user-library-read user-top-read user-read-recently-played "
          "playlist-read-private playlist-modify-private playlist-modify-public")
API = "https://api.spotify.com/v1"

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def client_id():
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    path = os.path.join(DIR, "client_id.txt")
    if not cid and os.path.exists(path):
        cid = open(path, encoding="utf-8").read().strip()
    if not cid:
        sys.exit("HATA: Client ID yok. client_id.txt dosyasına ya da SPOTIFY_CLIENT_ID'ye yaz.")
    return cid


def post_form(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode(),
                                 {"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def save_token(tok):
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    old = load_token() or {}
    if "refresh_token" not in tok and "refresh_token" in old:
        tok["refresh_token"] = old["refresh_token"]
    json.dump(tok, open(TOKEN_FILE, "w", encoding="utf-8"))
    return tok


def load_token():
    if os.path.exists(TOKEN_FILE):
        return json.load(open(TOKEN_FILE, encoding="utf-8"))


def login():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id(), "response_type": "code", "redirect_uri": REDIRECT,
        "scope": SCOPES, "code_challenge_method": "S256", "code_challenge": challenge, "state": state})
    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Tamam, bu sekmeyi kapatabilirsin.".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 8888), H)
    srv.timeout = 300
    print("Tarayıcıda Spotify izni açılıyor. Açılmazsa bu adrese git:\n" + url, flush=True)
    webbrowser.open(url)
    srv.handle_request()
    if result.get("state") != state or "code" not in result:
        sys.exit("HATA: Giriş başarısız: " + str(result.get("error", "yanıt yok")))
    save_token(post_form("https://accounts.spotify.com/api/token", {
        "grant_type": "authorization_code", "code": result["code"], "redirect_uri": REDIRECT,
        "client_id": client_id(), "code_verifier": verifier}))
    print("Giriş tamam.")


def token():
    tok = load_token()
    if not tok:
        sys.exit("HATA: Giriş yapılmamış. Önce: python spotify_tool.py giris")
    if time.time() > tok["expires_at"]:
        tok = save_token(post_form("https://accounts.spotify.com/api/token", {
            "grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": client_id()}))
    return tok["access_token"]


def api(method, path, body=None, params=None):
    url = path if path.startswith("http") else API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for _ in range(5):
        req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                     {"Authorization": "Bearer " + token(), "Content-Type": "application/json"},
                                     method=method)
        try:
            with urllib.request.urlopen(req) as r:
                data = r.read()
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "2")) + 1)
                continue
            raise
    raise RuntimeError("Çok fazla 429 yanıtı")


def paged(path, limit_total, page=50, params=None):
    items, url, p = [], path, dict(params or {}, limit=page)
    while url and len(items) < limit_total:
        d = api("GET", url, params=p)
        items += d.get("items", [])
        url, p = d.get("next"), None
    return items[:limit_total]


def fmt(t):
    return f'{t["name"]} - {", ".join(a["name"] for a in t["artists"])}'


def zevk(n_begeni):
    liked = [i["track"] for i in paged("/me/tracks", n_begeni) if i.get("track")]
    out = {"begeni_sayisi_okunan": len(liked)}
    artists = Counter(a["name"] for t in liked for a in t["artists"])
    out["begeni_en_cok_sanatcilar"] = artists.most_common(40)
    out["begeni_ornek"] = [fmt(t) for t in liked[:150]]
    for term in ("short_term", "medium_term"):
        try:
            out[f"top_sarkilar_{term}"] = [fmt(t) for t in paged("/me/top/tracks", 50, params={"time_range": term})]
            out[f"top_sanatcilar_{term}"] = [a["name"] for a in paged("/me/top/artists", 50, params={"time_range": term})]
        except urllib.error.HTTPError as e:
            out[f"top_{term}_hata"] = e.code
    try:
        out["son_calinanlar"] = [fmt(i["track"]) for i in api("GET", "/me/player/recently-played", params={"limit": 50})["items"]]
    except urllib.error.HTTPError as e:
        out["son_calinanlar_hata"] = e.code
    print(json.dumps(out, ensure_ascii=False, indent=1))


def search(line):
    if " - " in line:
        name, artist = line.split(" - ", 1)
        queries = [f'track:"{name.strip()}" artist:"{artist.strip()}"', f"{name} {artist}"]
    else:
        queries = [line]
    for q in queries:
        items = api("GET", "/search", params={"q": q, "type": "track", "limit": 5}).get("tracks", {}).get("items", [])
        if items:
            return items[0]


def playlist_items_path(pid):
    return f"/playlists/{pid}/items"


def add_items(pid, uris):
    for i in range(0, len(uris), 100):
        chunk = uris[i:i + 100]
        try:
            api("POST", playlist_items_path(pid), {"uris": chunk})
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            api("POST", f"/playlists/{pid}/tracks", {"uris": chunk})


def existing_uris(pid):
    try:
        items = paged(playlist_items_path(pid), 10000)
    except urllib.error.HTTPError:
        items = paged(f"/playlists/{pid}/tracks", 10000)
    return {(i.get("item") or i.get("track") or {}).get("uri") for i in items} - {None}


def liste(ad, dosya, hedef):
    me = api("GET", "/me")
    pl = next((p for p in paged("/me/playlists", 500)
               if p and p["name"] == ad and p["owner"]["id"] == me["id"]), None)
    if pl:
        print(f"Var olan '{ad}' listesi kullanılıyor.")
    else:
        body = {"name": ad, "public": False, "description": "Beğenilenler ve dinlemelere göre hazırlandı."}
        try:
            pl = api("POST", "/me/playlists", body)
        except urllib.error.HTTPError:
            pl = api("POST", f"/users/{me['id']}/playlists", body)
        print(f"'{ad}' listesi oluşturuldu.")
    pid = pl["id"]
    have = existing_uris(pid)
    lines = [l.strip() for l in open(dosya, encoding="utf-8") if l.strip()]
    new, bulunamayan = [], []
    for line in lines:
        if len(have) + len(new) >= hedef:
            break
        t = search(line)
        if not t:
            bulunamayan.append(line)
        elif t["uri"] not in have and t["uri"] not in new:
            new.append(t["uri"])
    add_items(pid, new)
    toplam = len(existing_uris(pid))
    print(json.dumps({"liste": pl["external_urls"]["spotify"], "eklenen": len(new),
                      "listedeki_toplam": toplam, "eksik": max(0, hedef - toplam),
                      "bulunamayan": bulunamayan}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("giris")
    z = sub.add_parser("zevk"); z.add_argument("--begeni", type=int, default=300)
    l = sub.add_parser("liste"); l.add_argument("--ad", required=True); l.add_argument("--dosya", required=True)
    l.add_argument("--hedef", type=int, default=100)
    a = ap.parse_args()
    if a.cmd == "giris":
        login()
    elif a.cmd == "zevk":
        zevk(a.begeni)
    else:
        liste(a.ad, a.dosya, a.hedef)
