"""Servis sağlık kontrolleri: HTTP, TCP ve DNS.

Her kontrol bir `Sonuc` döndürür ve ASLA istisna fırlatmaz: hata, sonucun içinde taşınır.
Böylece bir hedefin çökmesi izleyicinin kendisini çökertmez.
"""
import asyncio
import socket
import time
from dataclasses import dataclass

import httpx

from .yapilandirma import Hedef


@dataclass(frozen=True)
class Sonuc:
    ad: str
    tur: str
    basarili: bool
    sure_sn: float | None      # Başarısızsa ölçülemeyebilir
    ayrinti: str               # "HTTP 200", "bağlantı reddedildi" gibi kısa açıklama
    zaman: float               # Unix zamanı (kontrolün yapıldığı an)


def _sonuc(hedef: Hedef, basarili: bool, baslangic: float, ayrinti: str) -> Sonuc:
    sure = time.perf_counter() - baslangic
    return Sonuc(hedef.ad, hedef.tur, basarili, sure if basarili else None, ayrinti, time.time())


async def http_kontrol(hedef: Hedef, istemci: httpx.AsyncClient | None = None) -> Sonuc:
    baslangic = time.perf_counter()
    kendi_istemcimiz = istemci is None
    istemci = istemci or httpx.AsyncClient(timeout=hedef.zaman_asimi, follow_redirects=True)
    try:
        cevap = await istemci.get(hedef.adres)
        tamam = cevap.status_code == hedef.beklenen_durum
        ayrinti = f"HTTP {cevap.status_code}" + ("" if tamam else f" (beklenen {hedef.beklenen_durum})")
        return _sonuc(hedef, tamam, baslangic, ayrinti)
    except httpx.TimeoutException:
        return _sonuc(hedef, False, baslangic, f"zaman aşımı ({hedef.zaman_asimi:g} sn)")
    except httpx.HTTPError as hata:
        return _sonuc(hedef, False, baslangic, f"{type(hata).__name__}: {hata}"[:120])
    finally:
        if kendi_istemcimiz:
            await istemci.aclose()


async def tcp_kontrol(hedef: Hedef) -> Sonuc:
    baslangic = time.perf_counter()
    try:
        _, yazici = await asyncio.wait_for(
            asyncio.open_connection(hedef.adres, hedef.port), hedef.zaman_asimi
        )
        yazici.close()
        await yazici.wait_closed()
        return _sonuc(hedef, True, baslangic, f"{hedef.adres}:{hedef.port} açık")
    except asyncio.TimeoutError:
        return _sonuc(hedef, False, baslangic, f"zaman aşımı ({hedef.zaman_asimi:g} sn)")
    except OSError as hata:
        return _sonuc(hedef, False, baslangic, f"bağlanılamadı: {hata.strerror or hata}"[:120])


async def dns_kontrol(hedef: Hedef) -> Sonuc:
    baslangic = time.perf_counter()
    try:
        donus = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(hedef.adres, None, type=socket.SOCK_STREAM),
            hedef.zaman_asimi,
        )
        adresler = sorted({kayit[4][0] for kayit in donus})
        return _sonuc(hedef, True, baslangic, "çözüldü: " + ", ".join(adresler[:3]))
    except asyncio.TimeoutError:
        return _sonuc(hedef, False, baslangic, f"zaman aşımı ({hedef.zaman_asimi:g} sn)")
    except OSError as hata:
        return _sonuc(hedef, False, baslangic, f"çözülemedi: {hata}"[:120])


async def kontrol_et(hedef: Hedef, http_istemcisi: httpx.AsyncClient | None = None) -> Sonuc:
    """Hedefin türüne göre doğru kontrolü çalıştırır."""
    if hedef.tur == "http":
        return await http_kontrol(hedef, http_istemcisi)
    if hedef.tur == "tcp":
        return await tcp_kontrol(hedef)
    return await dns_kontrol(hedef)
