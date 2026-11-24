# Ajan Köyü

Claude Code alt ajanlarıyla kurulmuş kişisel bir yardımcı sistemi. Bir üst ajan işleri alt ajanlara dağıtır. Alt ajanlar birbirini çağıramaz, her biri tek bir işe odaklanır ve sadece o iş için gereken araçlara erişir.

## Ajanlar

Ajan tanımları `.claude/agents/` klasöründedir.

| Ajan | Model ve efor | Ne yapar |
| --- | --- | --- |
| mail-ozetci | Sonnet, orta | Outlook maillerini Microsoft 365 bağlayıcısıyla okur ve günlük özet çıkarır. Sadece okur, mail göndermez veya silmez. |
| ai-haber | Sonnet, orta | Son 7 günün yapay zekâ haberlerini web'den toplar, önem sırasına koyar ve daha önce gösterdiklerini tekrar etmez. |
| cv-uyum | Sonnet, extra yüksek | Bir iş veya staj ilanını analiz eder, temel CV'yi ve ders listesini kullanarak ilana göre CV hazırlar. Bilgi uydurmaz. |
| spotify-liste | Sonnet | Spotify dinleme geçmişine göre çalma listesi oluşturur. |

Üst ajan Opus ile orta eforda çalışır ve işleri bu ajanlara dağıtır.

## Yerel site

Bütün ajanlarla tek bir sayfadan konuşmak için yerel bir site vardır. Solda alt ajanların odaları, ortada üst ajan bulunur. Bir odaya tıklayınca sağda sohbet açılır.

Çalıştırmak için:

```
python site/sunucu.py
```

Ardından tarayıcıda `http://localhost:8000` adresini aç.

Sunucu sadece Python standart kütüphanesini kullanır. Her mesajda arka planda Claude Code'u (`claude -p`) ilgili ajanla çalıştırır. Bu yüzden Claude Code'un terminal sürümünün kurulu ve giriş yapılmış olması gerekir. API anahtarı gerekmez. Site yalnızca kendi bilgisayarından erişilebilir.

## Kurulum notları

- Mail ajanı için Claude hesabına Microsoft 365 bağlayıcısı eklenmiş olmalıdır.
- Spotify ajanı için `spotify/client_id.txt` dosyasına kendi Spotify uygulamanın client ID değeri yazılmalıdır.
- CV ajanı aşağıdaki kişisel dosyaları kullanır.

## Kişisel dosyalar

Bu dosyalar depoda yer almaz ve her kullanıcının kendi bilgisayarında oluşturması gerekir:

- `cv/temel/pazarlama.md` ve `cv/temel/ai-data.md`: iki farklı alana göre hazırlanmış temel CV'ler
- `cv/temel/dersler.md`: alınan dersler (yapısı için `cv/temel/dersler.ornek.md` dosyasına bak)
- `haber/okuyucu.md`: haber ajanının dikkate alacağı kısa okuyucu profili
- `cv/ciktilar/`: ajanın ürettiği CV'ler

## Klasör yapısı

```
.claude/agents/   Ajan tanımları
site/             Yerel site ve sunucu
cv/               CV şablonu ve örnek ders listesi
araclar/          Yardımcı araçlar (mail MCP sunucusu, PNG çizici)
spotify/          Spotify yardımcı betiği
```
