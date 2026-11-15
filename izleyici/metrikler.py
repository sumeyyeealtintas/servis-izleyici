"""Prometheus metrik deposu.

Prometheus "text exposition format" çıktısını kütüphane kullanmadan üretir; böylece biçimin
nasıl çalıştığı görünür. (Üretimde `prometheus_client` kullanmak da iyi bir seçenektir.)
Biçim: https://prometheus.io/docs/instrumenting/exposition_formats/
"""
from collections import defaultdict
from threading import Lock

from .kontrol import Sonuc


def etiket_kacir(deger: str) -> str:
    """Etiket değerindeki \\, " ve satır sonunu biçime uygun kaçırır."""
    return deger.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _etiketler(**kv: str) -> str:
    return "{" + ",".join(f'{k}="{etiket_kacir(v)}"' for k, v in kv.items()) + "}"


class MetrikDeposu:
    def __init__(self) -> None:
        self._son: dict[str, Sonuc] = {}
        self._sayac: dict[tuple[str, str, str], int] = defaultdict(int)
        self._kilit = Lock()

    def kaydet(self, sonuc: Sonuc) -> None:
        with self._kilit:
            self._son[sonuc.ad] = sonuc
            self._sayac[(sonuc.ad, sonuc.tur, "basarili" if sonuc.basarili else "basarisiz")] += 1

    def son_sonuclar(self) -> list[Sonuc]:
        with self._kilit:
            return sorted(self._son.values(), key=lambda s: s.ad)

    def prometheus_metni(self) -> str:
        with self._kilit:
            son = sorted(self._son.values(), key=lambda s: s.ad)
            sayac = sorted(self._sayac.items())

        satirlar = [
            "# HELP izleyici_hedef_ayakta Hedef son kontrolde çalışıyor mu (1 = evet, 0 = hayır).",
            "# TYPE izleyici_hedef_ayakta gauge",
        ]
        for s in son:
            satirlar.append(f"izleyici_hedef_ayakta{_etiketler(hedef=s.ad, tur=s.tur)} {int(s.basarili)}")

        satirlar += [
            "# HELP izleyici_yanit_suresi_saniye Son başarılı kontrolün süresi (saniye).",
            "# TYPE izleyici_yanit_suresi_saniye gauge",
        ]
        for s in son:
            if s.sure_sn is not None:
                satirlar.append(
                    f"izleyici_yanit_suresi_saniye{_etiketler(hedef=s.ad, tur=s.tur)} {s.sure_sn:.6f}"
                )

        satirlar += [
            "# HELP izleyici_kontrol_total Yapılan toplam kontrol sayısı.",
            "# TYPE izleyici_kontrol_total counter",
        ]
        for (ad, tur, sonuc), adet in sayac:
            satirlar.append(f"izleyici_kontrol_total{_etiketler(hedef=ad, tur=tur, sonuc=sonuc)} {adet}")

        return "\n".join(satirlar) + "\n"
