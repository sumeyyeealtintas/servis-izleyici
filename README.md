# 📡 Servis İzleyici

[![Testler](https://github.com/sumeyyeealtintas/servis-izleyici/actions/workflows/ci.yml/badge.svg)](https://github.com/sumeyyeealtintas/servis-izleyici/actions/workflows/ci.yml)

Web siteleri, TCP portları ve DNS kayıtlarını **periyodik olarak kontrol eden** ve sonuçları **Prometheus formatında sunan** küçük bir izleme (monitoring) servisi. Docker Compose ile Prometheus ve Grafana'yla birlikte tek komutla ayağa kalkar.

> "Servis çalışıyor mu, ne kadar hızlı yanıt veriyor, çökerse kim haber verecek?" sorusunun cevabı.

```
  hedefler (HTTP / TCP / DNS)
            ▲
            │  eşzamanlı kontrol (asyncio)
     ┌──────┴───────┐   /metrics    ┌────────────┐   ┌─────────┐
     │ Servis İzleyici│ ───────────▶ │ Prometheus │──▶│ Grafana │
     └──────────────┘               └─────┬──────┘   └─────────┘
                                          ▼
                                   uyarı kuralları
```

## 🧰 Teknolojiler
Python 3.12 · FastAPI · asyncio · httpx · PyYAML · Prometheus · Grafana · Docker · Docker Compose · GitHub Actions · pytest

## ✨ Özellikler
- **3 kontrol türü:** HTTP (beklenen durum kodu), TCP (port açık mı), DNS (alan adı çözülüyor mu)
- **Eşzamanlı kontrol:** tüm hedefler `asyncio.gather` ile aynı anda kontrol edilir; yavaş bir hedef diğerlerini geciktirmez (bunu doğrulayan test vardır)
- **Dayanıklılık:** bir hedefin çökmesi, zaman aşımı ya da bağlantı hatası izleyiciyi çökertmez; hata sonucun içinde taşınır
- **Prometheus metrikleri** (`/metrics`), standart text exposition formatında, kütüphane kullanmadan üretildi (biçim nasıl çalışıyor görmek için)
- **Anlaşılır yapılandırma hataları:** YAML doğrulanır, hatalı dosya açılışta Türkçe mesajla reddedilir
- **Hazır uyarı kuralları:** `HedefKapali`, `YavasYanit`, `IzleyiciVeriGelmiyor`
- Docker: root olmayan kullanıcı, `HEALTHCHECK`, sabitlenmiş imaj sürümleri

## 🚀 Çalıştırma
**Yerel:**
```bash
pip install -r requirements.txt
uvicorn izleyici.uygulama:uygulama_olustur --factory --port 8000
```
- `http://localhost:8000/docs` Swagger arayüzü
- `http://localhost:8000/durum` hedeflerin anlık durumu (JSON)
- `http://localhost:8000/metrics` Prometheus metrikleri

**Tüm yığın (izleyici + Prometheus + Grafana):**
```bash
docker compose up -d --build
```
| Servis | Adres |
|---|---|
| İzleyici | http://localhost:8000 |
| Prometheus | http://localhost:9090 (uyarılar: `/alerts`) |
| Grafana | http://localhost:3000 (admin / admin, ilk girişte şifreyi değiştirin) |

Grafana'da Prometheus veri kaynağı hazır gelir. Örnek sorgular:
```promql
izleyici_hedef_ayakta                           # 1 = ayakta, 0 = kapalı
izleyici_yanit_suresi_saniye{tur="http"}        # yanıt süreleri
sum by (hedef) (rate(izleyici_kontrol_total{sonuc="basarisiz"}[5m]))   # hata oranı
```

## ⚙️ Yapılandırma (`izleme.yaml`)
```yaml
aralik_sn: 15
hedefler:
  - {ad: github-web, tur: http, adres: "https://github.com", beklenen_durum: 200}
  - {ad: github-dns, tur: dns,  adres: github.com}
  - {ad: dns-sunucu, tur: tcp,  adres: 1.1.1.1, port: 53, zaman_asimi: 3}
```
Dosya yolu `IZLEME_YAPILANDIRMA` ortam değişkeniyle değiştirilebilir.

## 🧪 Test
```bash
pytest -q        # 27 test
```
Testler gerçek bir yerel HTTP ve TCP sunucusu açarak kontrol fonksiyonlarını dener: başarılı/başarısız durum, zaman aşımı, kapalı port, geçersiz DNS, yapılandırma doğrulama, Prometheus biçimi, etiket kaçırma, sayaçlar ve eşzamanlılık.
GitHub Actions testleri çalıştırır, ardından Docker imajını derler ve compose dosyasını doğrular.

## 📁 Yapı
```
├── izleyici/
│   ├── kontrol.py        # HTTP / TCP / DNS kontrolleri
│   ├── yapilandirma.py   # YAML okuma ve doğrulama
│   ├── metrikler.py      # Prometheus metin biçimi, sayaçlar
│   └── uygulama.py       # FastAPI + arka plan döngüsü
├── prometheus/           # scrape ayarı ve uyarı kuralları
├── grafana/provisioning/ # hazır veri kaynağı
├── Dockerfile · docker-compose.yml
└── tests/
```

## ⚠️ Doğrulama Notu
27 testin tamamı geçer ve servis gerçek hedeflere (GitHub, DNS, Cloudflare) karşı çalıştırılıp doğrulandı. **Docker imajının derlenmesi ve `docker compose config` doğrulaması her push'ta GitHub Actions'ta çalışır** (rozete bakın). Tam yığının (izleyici + Prometheus + Grafana) çalışır halde uçtan uca denenmesi yerel Docker ile ayrıca yapılmalıdır.

## 🔭 Geliştirme Fikirleri
- Alertmanager + Telegram bildirimi
- Hazır Grafana panosu (JSON olarak)
- TLS sertifika bitiş süresi kontrolü
- Hedef başına özel HTTP başlıkları ve içerik kontrolü
