"""YAML yapılandırmasını okur ve doğrular.

Hatalı yapılandırma uygulama açılırken, anlaşılır bir mesajla yakalanır (hızlı başarısız olma / fail fast).
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

TURLER = ("http", "tcp", "dns")


@dataclass(frozen=True)
class Hedef:
    ad: str
    tur: str
    adres: str
    port: int | None = None
    beklenen_durum: int = 200
    zaman_asimi: float = 5.0


@dataclass(frozen=True)
class Yapilandirma:
    aralik_sn: float
    hedefler: tuple[Hedef, ...]


def _hedef_olustur(sira: int, ham: dict) -> Hedef:
    if not isinstance(ham, dict):
        raise ValueError(f"hedefler[{sira}] bir sözlük olmalı")
    for alan in ("ad", "tur", "adres"):
        if not ham.get(alan):
            raise ValueError(f"hedefler[{sira}]: '{alan}' alanı zorunlu")
    tur = str(ham["tur"]).lower()
    if tur not in TURLER:
        raise ValueError(f"hedefler[{sira}]: tur '{ham['tur']}' geçersiz, şunlardan biri olmalı: {', '.join(TURLER)}")
    adres = str(ham["adres"])
    if tur == "http" and not adres.startswith(("http://", "https://")):
        raise ValueError(f"hedefler[{sira}]: http adresi http:// veya https:// ile başlamalı")
    port = ham.get("port")
    if tur == "tcp":
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError(f"hedefler[{sira}]: tcp için 1-65535 arasında 'port' zorunlu")
    zaman_asimi = float(ham.get("zaman_asimi", 5.0))
    if zaman_asimi <= 0:
        raise ValueError(f"hedefler[{sira}]: zaman_asimi pozitif olmalı")
    return Hedef(
        ad=str(ham["ad"]), tur=tur, adres=adres, port=port,
        beklenen_durum=int(ham.get("beklenen_durum", 200)), zaman_asimi=zaman_asimi,
    )


def yapilandirma_olustur(ham: dict) -> Yapilandirma:
    if not isinstance(ham, dict):
        raise ValueError("yapılandırma bir sözlük (anahtar: değer) olmalı")
    aralik = float(ham.get("aralik_sn", 15))
    if aralik < 1:
        raise ValueError("aralik_sn en az 1 olmalı")
    hedefler = ham.get("hedefler")
    if not hedefler or not isinstance(hedefler, list):
        raise ValueError("en az bir hedef tanımlanmalı ('hedefler' listesi)")
    olusan = tuple(_hedef_olustur(i, h) for i, h in enumerate(hedefler))
    adlar = [h.ad for h in olusan]
    tekrar = {a for a in adlar if adlar.count(a) > 1}
    if tekrar:
        raise ValueError(f"hedef adları benzersiz olmalı, tekrar edenler: {', '.join(sorted(tekrar))}")
    return Yapilandirma(aralik_sn=aralik, hedefler=olusan)


def yukle(yol: str | Path) -> Yapilandirma:
    with open(yol, encoding="utf-8") as f:
        return yapilandirma_olustur(yaml.safe_load(f))
