"""
Skenario hidrologi — ekstrapolasi skala dari retensi skala laboratorium.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

STATUS BUKTI: seluruh keluaran modul ini berstatus MODEL, bukan pengukuran.
Naskah menyatakannya eksplisit pada §4.6 dan BAB V: perhitungan skala
merupakan skenario perhitungan, bukan hasil pengukuran lapangan, dan
mengandaikan tingkat retensi skala laboratorium berlaku sama pada skala yang
jauh lebih besar.

Skenario acuan yang terdokumentasi (OUTPUT3 §4.6):
    luas 1.000 m2, intensitas 50 mm/jam, durasi 1 jam
    -> 50.000 liter air jatuh, 40% tertahan = 20.000 liter

Perbandingan terhadap perkerasan konvensional dibuat SIMETRIS: kedua permukaan
memakai koefisien limpasan masing-masing. Aplikasi lama membandingkan C = 0,85
untuk konvensional terhadap C efektif 1,0 untuk ZEOPAVE, yang menghasilkan
angka reduksi yang menyesatkan.
"""

from __future__ import annotations

import math

# Skenario acuan (OUTPUT3 §4.6), menyalin besaran kanonik SKALA_*.
# Kesetaraannya terhadap konstanta.py dijaga validation/test_duplikasi_kanonik.py.
ACUAN_LUAS_M2 = 1000.0
ACUAN_INTENSITAS_MM_PER_JAM = 50.0
ACUAN_DURASI_JAM = 1.0
ACUAN_AIR_JATUH_LITER = 50000.0
ACUAN_AIR_TERTAHAN_LITER = 20000.0


def _positif(nama: str, nilai: float) -> float:
    nilai = float(nilai)
    if not math.isfinite(nilai) or nilai <= 0:
        raise ValueError(f"{nama} harus bilangan positif berhingga, diterima {nilai}")
    return nilai


def volume_hujan_m3(intensitas_mm_per_jam: float, luas_m2: float, durasi_jam: float) -> float:
    """
    Volume air hujan yang jatuh, dalam m3. V = (i/1000) * A * t

    >>> volume_hujan_m3(50, 1000, 1)
    50.0
    """
    i = _positif("intensitas hujan", intensitas_mm_per_jam)
    A = _positif("luas area", luas_m2)
    t = _positif("durasi hujan", durasi_jam)
    return (i / 1000.0) * A * t


def volume_tertahan_m3(volume_hujan: float, retensi_persen: float) -> float:
    """Volume air yang tertahan sistem, dalam m3."""
    V = _positif("volume hujan", volume_hujan)
    r = float(retensi_persen)
    if not 0.0 <= r <= 100.0:
        raise ValueError(f"retensi harus 0-100 persen, diterima {r}")
    return V * (r / 100.0)


def limpasan_m3(volume_hujan: float, koefisien_limpasan: float) -> float:
    """Limpasan permukaan, dalam m3. Q = C * V"""
    V = _positif("volume hujan", volume_hujan)
    C = float(koefisien_limpasan)
    if not 0.0 <= C <= 1.0:
        raise ValueError(f"koefisien limpasan harus 0-1, diterima {C}")
    return V * C


def skenario(
    intensitas_mm_per_jam: float,
    luas_m2: float,
    durasi_jam: float,
    retensi_persen: float,
    koefisien_limpasan_konvensional: float = 0.85,
) -> dict:
    """
    Jalankan satu skenario hidrologi. Seluruh keluaran berstatus MODEL.

    Perbandingan dibuat simetris: limpasan ZEOPAVE dihitung sebagai bagian
    air yang TIDAK tertahan, dikalikan koefisien limpasan yang sama dengan
    permukaan konvensional untuk sisa air tersebut.

    >>> s = skenario(50, 1000, 1, 40.0)
    >>> round(s["air_jatuh_liter"]), round(s["air_tertahan_liter"])
    (50000, 20000)
    """
    V = volume_hujan_m3(intensitas_mm_per_jam, luas_m2, durasi_jam)
    tertahan = volume_tertahan_m3(V, retensi_persen)
    sisa = V - tertahan

    C = float(koefisien_limpasan_konvensional)
    limpasan_konv = limpasan_m3(V, C)
    limpasan_zeopave = sisa * C

    reduksi = ((limpasan_konv - limpasan_zeopave) / limpasan_konv * 100.0) if limpasan_konv else 0.0

    return {
        "status_bukti": "model",
        "catatan": (
            "Skenario perhitungan, bukan hasil pengukuran lapangan. Mengandaikan "
            "tingkat retensi skala laboratorium berlaku pada skala yang jauh lebih besar."
        ),
        "volume_hujan_m3": V,
        "air_jatuh_liter": V * 1000.0,
        "air_tertahan_m3": tertahan,
        "air_tertahan_liter": tertahan * 1000.0,
        "limpasan_konvensional_m3": limpasan_konv,
        "limpasan_zeopave_m3": limpasan_zeopave,
        "reduksi_limpasan_persen": reduksi,
    }
