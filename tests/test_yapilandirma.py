from pathlib import Path

import pytest

from izleyici.yapilandirma import yapilandirma_olustur, yukle


def gecerli(**degisiklik):
    ham = {"aralik_sn": 10, "hedefler": [{"ad": "a", "tur": "http", "adres": "https://x.com"}]}
    ham.update(degisiklik)
    return ham


def test_ornek_yapilandirma_dosyasi_gecerli():
    yap = yukle(Path(__file__).parent.parent / "izleme.yaml")
    assert len(yap.hedefler) >= 3 and yap.aralik_sn >= 1


def test_varsayilanlar():
    h = yapilandirma_olustur(gecerli()).hedefler[0]
    assert h.beklenen_durum == 200 and h.zaman_asimi == 5.0


@pytest.mark.parametrize("ham, parca", [
    ({"hedefler": []}, "en az bir hedef"),
    ({"hedefler": [{"ad": "a", "tur": "ftp", "adres": "x"}]}, "geçersiz"),
    ({"hedefler": [{"ad": "a", "tur": "http", "adres": "x.com"}]}, "http://"),
    ({"hedefler": [{"ad": "a", "tur": "tcp", "adres": "h"}]}, "port"),
    ({"hedefler": [{"ad": "a", "tur": "tcp", "adres": "h", "port": 70000}]}, "port"),
    ({"hedefler": [{"tur": "dns", "adres": "x"}]}, "'ad'"),
    ({"hedefler": [{"ad": "a", "tur": "dns", "adres": "x", "zaman_asimi": 0}]}, "pozitif"),
    ({"aralik_sn": 0, "hedefler": [{"ad": "a", "tur": "dns", "adres": "x"}]}, "aralik_sn"),
])
def test_hatali_yapilandirma_anlasilir_hata_verir(ham, parca):
    with pytest.raises(ValueError, match=parca):
        yapilandirma_olustur(ham)


def test_ayni_ad_iki_kez_kullanilamaz():
    ham = gecerli(hedefler=[
        {"ad": "a", "tur": "dns", "adres": "x"},
        {"ad": "a", "tur": "dns", "adres": "y"},
    ])
    with pytest.raises(ValueError, match="benzersiz"):
        yapilandirma_olustur(ham)
