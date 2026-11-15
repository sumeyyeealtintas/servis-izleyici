import asyncio
import time

from fastapi.testclient import TestClient

from izleyici.kontrol import Sonuc
from izleyici.metrikler import MetrikDeposu, etiket_kacir
from izleyici.uygulama import uygulama_olustur
from izleyici.yapilandirma import yapilandirma_olustur


def sonuc(ad="web", basarili=True, sure=0.123):
    return Sonuc(ad, "http", basarili, sure if basarili else None, "HTTP 200", time.time())


def test_prometheus_bicimi():
    d = MetrikDeposu()
    d.kaydet(sonuc("web", True, 0.25))
    d.kaydet(sonuc("api", False))
    metin = d.prometheus_metni()
    assert "# TYPE izleyici_hedef_ayakta gauge" in metin
    assert 'izleyici_hedef_ayakta{hedef="web",tur="http"} 1' in metin
    assert 'izleyici_hedef_ayakta{hedef="api",tur="http"} 0' in metin
    assert 'izleyici_yanit_suresi_saniye{hedef="web",tur="http"} 0.250000' in metin
    assert metin.endswith("\n")


def test_basarisiz_hedefin_sure_metrigi_yoktur():
    d = MetrikDeposu()
    d.kaydet(sonuc("api", False))
    assert 'yanit_suresi_saniye{hedef="api"' not in d.prometheus_metni()


def test_sayac_artar_ve_sonuca_gore_ayrilir():
    d = MetrikDeposu()
    for _ in range(3):
        d.kaydet(sonuc("web", True))
    d.kaydet(sonuc("web", False))
    metin = d.prometheus_metni()
    assert 'izleyici_kontrol_total{hedef="web",tur="http",sonuc="basarili"} 3' in metin
    assert 'izleyici_kontrol_total{hedef="web",tur="http",sonuc="basarisiz"} 1' in metin


def test_etiket_degeri_kacirilir():
    assert etiket_kacir('a"b\\c\nd') == 'a\\"b\\\\c\\nd'


def test_son_sonuc_ustune_yazilir():
    d = MetrikDeposu()
    d.kaydet(sonuc("web", False))
    d.kaydet(sonuc("web", True))
    assert [s.basarili for s in d.son_sonuclar()] == [True]


def _uygulama():
    yap = yapilandirma_olustur({"aralik_sn": 60, "hedefler": [
        {"ad": "yerel-dns", "tur": "dns", "adres": "localhost"},
        {"ad": "olu-port", "tur": "tcp", "adres": "127.0.0.1", "port": 1, "zaman_asimi": 1},
    ]})
    return uygulama_olustur(yap, otomatik_dongu=False)


def test_uc_noktalar():
    app = _uygulama()
    istemci = TestClient(app)
    assert istemci.get("/saglik").json() == {"durum": "ok"}

    asyncio.run(app.state.izleyici.tur_calistir())     # arka plan döngüsü yerine bir tur elle

    durum = istemci.get("/durum").json()
    assert durum["toplam"] == 2 and durum["ayakta"] == 1
    adlar = {h["ad"]: h["ayakta"] for h in durum["hedefler"]}
    assert adlar == {"yerel-dns": True, "olu-port": False}

    r = istemci.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert 'izleyici_hedef_ayakta{hedef="olu-port",tur="tcp"} 0' in r.text


def test_hedefler_es_zamanli_kontrol_edilir():
    """Yavaş bir hedef, diğerlerinin kontrolünü geciktirmemeli (asyncio.gather)."""
    yap = yapilandirma_olustur({"aralik_sn": 60, "hedefler": [
        {"ad": f"d{i}", "tur": "tcp", "adres": "10.255.255.1", "port": 81, "zaman_asimi": 1.0} for i in range(4)
    ]})
    app = uygulama_olustur(yap, otomatik_dongu=False)
    baslangic = time.perf_counter()
    asyncio.run(app.state.izleyici.tur_calistir())
    gecen = time.perf_counter() - baslangic
    # 4 hedef x 1 sn zaman aşımı: sıralı olsaydı >= 4 sn sürerdi
    assert gecen < 3.0
