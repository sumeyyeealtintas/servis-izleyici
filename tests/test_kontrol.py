import asyncio
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from izleyici.kontrol import dns_kontrol, http_kontrol, kontrol_et, tcp_kontrol
from izleyici.yapilandirma import Hedef


class _Isleyici(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/yavas":
            import time
            time.sleep(1.5)
        kod = 500 if self.path == "/hata" else 200
        self.send_response(kod)
        self.end_headers()
        self.wfile.write(b"x")

    def log_message(self, *args):  # test çıktısını kirletmesin
        pass


@pytest.fixture(scope="module")
def http_sunucu():
    sunucu = HTTPServer(("127.0.0.1", 0), _Isleyici)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{sunucu.server_port}"
    sunucu.shutdown()


def bos_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_http_basarili(http_sunucu):
    sonuc = asyncio.run(http_kontrol(Hedef("t", "http", http_sunucu + "/")))
    assert sonuc.basarili and sonuc.ayrinti == "HTTP 200" and sonuc.sure_sn > 0


def test_http_beklenmeyen_durum_basarisiz(http_sunucu):
    sonuc = asyncio.run(http_kontrol(Hedef("t", "http", http_sunucu + "/hata")))
    assert not sonuc.basarili
    assert "500" in sonuc.ayrinti and sonuc.sure_sn is None


def test_http_beklenen_durum_ozellestirilebilir(http_sunucu):
    sonuc = asyncio.run(http_kontrol(Hedef("t", "http", http_sunucu + "/hata", beklenen_durum=500)))
    assert sonuc.basarili


def test_http_zaman_asimi(http_sunucu):
    sonuc = asyncio.run(http_kontrol(Hedef("t", "http", http_sunucu + "/yavas", zaman_asimi=0.3)))
    assert not sonuc.basarili and "zaman aşımı" in sonuc.ayrinti


def test_http_baglanti_hatasi_istisna_firlatmaz():
    sonuc = asyncio.run(http_kontrol(Hedef("t", "http", f"http://127.0.0.1:{bos_port()}/", zaman_asimi=2)))
    assert not sonuc.basarili  # istisna yerine başarısız sonuç dönmeli


def test_tcp_acik_ve_kapali_port():
    async def senaryo():
        sunucu = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
        port = sunucu.sockets[0].getsockname()[1]
        async with sunucu:
            acik = await tcp_kontrol(Hedef("t", "tcp", "127.0.0.1", port=port, zaman_asimi=2))
        kapali = await tcp_kontrol(Hedef("t", "tcp", "127.0.0.1", port=bos_port(), zaman_asimi=2))
        return acik, kapali

    acik, kapali = asyncio.run(senaryo())
    assert acik.basarili and "açık" in acik.ayrinti
    assert not kapali.basarili


def test_dns_localhost_cozulur():
    sonuc = asyncio.run(dns_kontrol(Hedef("t", "dns", "localhost")))
    assert sonuc.basarili and "çözüldü" in sonuc.ayrinti


def test_dns_olmayan_alan_basarisiz():
    sonuc = asyncio.run(dns_kontrol(Hedef("t", "dns", "bu-alan-yok.invalid", zaman_asimi=3)))
    assert not sonuc.basarili


def test_kontrol_et_dogru_turu_secer(http_sunucu):
    assert asyncio.run(kontrol_et(Hedef("a", "http", http_sunucu + "/"))).tur == "http"
    assert asyncio.run(kontrol_et(Hedef("b", "dns", "localhost"))).tur == "dns"
