# Ajan Köyü

Claude Code alt ajanlarıyla kurulmuş kişisel bir yardımcı sistemi. Bir üst ajan işleri alt ajanlara dağıtır. Her alt ajan tek bir işe odaklanır ve sadece o iş için gereken araçlara erişir. Alt ajanlar birbirini çağıramaz.

Bütün ajanlarla tek bir yerel siteden konuşulabilir.

## Ajanlar

| Ajan | Model ve efor | Görevi |
| --- | --- | --- |
| Üst ajan | Opus, orta | İşleri alt ajanlara dağıtır ve sonuçları birleştirir. |
| mail-ozetci | Sonnet, orta | Outlook maillerini okur ve günlük özet çıkarır. Mail göndermez veya silmez. |
| ai-haber | Sonnet, orta | Son 7 günün yapay zekâ haberlerini toplar ve önem sırasına koyar. Daha önce gösterdiği haberleri tekrar etmez. |
| cv-uyum | Sonnet, extra yüksek | Bir iş veya staj ilanını analiz eder ve CV'yi ilana göre uyarlar. Var olmayan bilgi eklemez. |
| spotify-liste | Sonnet | Spotify dinleme geçmişine göre çalma listesi oluşturur. |

## Gereksinimler

- Python 3.10 veya üstü
- Claude Code terminal sürümü, kurulu ve giriş yapılmış hâlde
- Mail ajanı için Claude hesabına eklenmiş Microsoft 365 bağlayıcısı
- Spotify ajanı için `spotify/client_id.txt` dosyasında bir Spotify uygulama client ID değeri

## Kullanım

Sunucuyu başlat:

```
python site/sunucu.py
```

Tarayıcıda `http://localhost:8000` adresini aç. Solda alt ajanların odaları, ortada üst ajan bulunur. Bir odaya tıklayınca sağda o ajanla sohbet açılır.

Sunucu sadece Python standart kütüphanesini kullanır. Her mesajda arka planda Claude Code'u ilgili ajanla çalıştırır. Bu yüzden API anahtarı gerekmez. Site yalnızca kendi bilgisayarından erişilebilir.

Ajanlar Claude Code içinden de doğrudan kullanılabilir. Örneğin "bugünkü maillerimi özetle" veya "AI haberlerini getir" yazmak yeterlidir.

## Kişisel dosyalar

CV ajanı ve haber ajanı aşağıdaki dosyaları kullanır. Bu dosyalar depoda yer almaz ve her kullanıcının kendisi oluşturması gerekir.

| Dosya | İçerik |
| --- | --- |
| `cv/temel/pazarlama.md` | Pazarlama alanı için temel CV |
| `cv/temel/ai-data.md` | Yapay zekâ ve veri alanı için temel CV |
| `cv/temel/dersler.md` | Alınan dersler. Yapısı için `cv/temel/dersler.ornek.md` dosyasına bakılabilir. |
| `haber/okuyucu.md` | Haber ajanının dikkate alacağı kısa okuyucu profili |

Ajanın ürettiği CV'ler `cv/ciktilar/` klasörüne kaydedilir ve depoya eklenmez.

## Klasör yapısı

```
.claude/agents/   Ajan tanımları
site/             Yerel site ve sunucu
cv/               CV şablonu ve örnek ders listesi
spotify/          Spotify yardımcı betiği
```
