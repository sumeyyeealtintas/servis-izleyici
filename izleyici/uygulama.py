"""FastAPI uygulaması: arka planda hedefleri periyodik kontrol eder, /metrics ile sunar."""
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from .kontrol import kontrol_et
from .metrikler import MetrikDeposu
from .yapilandirma import Yapilandirma, yukle


class Izleyici:
    """Hedefleri eşzamanlı kontrol eden çekirdek sınıf."""

    def __init__(self, yapilandirma: Yapilandirma, depo: MetrikDeposu) -> None:
        self.yapilandirma = yapilandirma
        self.depo = depo

    async def tur_calistir(self) -> None:
        """Tüm hedefleri aynı anda bir kez kontrol eder (asyncio.gather)."""
        async with httpx.AsyncClient(follow_redirects=True) as istemci:
            sonuclar = await asyncio.gather(
                *(kontrol_et(h, istemci if h.tur == "http" else None) for h in self.yapilandirma.hedefler)
            )
        for sonuc in sonuclar:
            self.depo.kaydet(sonuc)

    async def surekli_calis(self) -> None:
        while True:
            await self.tur_calistir()
            await asyncio.sleep(self.yapilandirma.aralik_sn)


def uygulama_olustur(yapilandirma: Yapilandirma | None = None, otomatik_dongu: bool = True) -> FastAPI:
    if yapilandirma is None:
        yapilandirma = yukle(Path(os.getenv("IZLEME_YAPILANDIRMA", "izleme.yaml")))
    depo = MetrikDeposu()
    izleyici = Izleyici(yapilandirma, depo)

    @asynccontextmanager
    async def omur(_: FastAPI):
        gorev = asyncio.create_task(izleyici.surekli_calis()) if otomatik_dongu else None
        yield
        if gorev:
            gorev.cancel()

    app = FastAPI(title="Servis İzleyici", version="1.0.0", lifespan=omur)
    app.state.izleyici = izleyici

    @app.get("/saglik", tags=["Sistem"])
    def saglik():
        return {"durum": "ok"}

    @app.get("/metrics", response_class=PlainTextResponse, tags=["Prometheus"])
    def metrikler():
        return PlainTextResponse(depo.prometheus_metni(), media_type="text/plain; version=0.0.4; charset=utf-8")

    @app.get("/durum", tags=["İzleme"])
    def durum():
        sonuclar = depo.son_sonuclar()
        return {
            "toplam": len(sonuclar),
            "ayakta": sum(s.basarili for s in sonuclar),
            "hedefler": [
                {"ad": s.ad, "tur": s.tur, "ayakta": s.basarili, "sure_ms": None if s.sure_sn is None else round(s.sure_sn * 1000, 1),
                 "ayrinti": s.ayrinti}
                for s in sonuclar
            ],
        }

    return app
