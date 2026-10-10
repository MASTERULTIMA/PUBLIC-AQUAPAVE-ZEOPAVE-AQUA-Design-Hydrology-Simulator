"""
Kuat tekan beton — SNI 1974:2011.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

HASIL UTAMA penelitian adalah 13,19 MPa pada umur 7 hari, terukur langsung
(ADR-005). Estimasi umur 14 hari sebesar 15,00 MPa TIDAK dipakai sebagai hasil:
faktor konversinya diturunkan dari nilai itu sendiri, sehingga penurunannya
melingkar.

Konversi umur sengaja TIDAK disediakan sebagai fungsi di modul ini. Provenansi
primer tabel faktor umur (0,65 / 0,88 / 0,95 / 1,00) belum tertelusuri di dalam
proyek, dan keberlakuan faktor beton biasa pada campuran tanpa pasir
bersubstitusi 15% belum diverifikasi. Menyediakannya sebagai fungsi akan
mengundang pemakaian yang tidak dapat dipertanggungjawabkan.
"""

from __future__ import annotations

import math
from typing import Sequence

# Data uji yang dikonfirmasi (OUTPUT3 Tabel 4.1). Dipakai sebagai acuan
# reproduksi pada validation/ dan sebagai bawaan diameter pada
# ui/tabs/kuat_tekan.py. Nilainya menyalin besaran kanonik di konstanta.py.
# Kesetaraannya terhadap konstanta.py dijaga validation/test_duplikasi_kanonik.py.
LAB_UMUR_HARI = 7
LAB_DIAMETER_MM = 150.0
LAB_LUAS_M2 = 0.017671
LAB_BEBAN_KN = (235.2, 233.4, 230.4)
LAB_FC_RERATA_MPA = 13.19


def _positif(nama: str, nilai: float) -> float:
    nilai = float(nilai)
    if not math.isfinite(nilai) or nilai <= 0:
        raise ValueError(f"{nama} harus bilangan positif berhingga, diterima {nilai}")
    return nilai


def luas_silinder_m2(diameter_mm: float) -> float:
    """Luas penampang silinder dalam m^2, dari diameter dalam mm."""
    d = _positif("diameter", diameter_mm)
    return math.pi * (d / 1000.0 / 2.0) ** 2


def kuat_tekan_mpa(beban_kn: float, luas_m2: float) -> float:
    """
    f'c = P / A, dalam MPa.

    P dalam kN dikonversi ke N, A dalam m^2 dikonversi ke mm^2.

    >>> round(kuat_tekan_mpa(235.2, 0.017671), 2)
    13.31
    """
    P = _positif("beban", beban_kn)
    A = _positif("luas penampang", luas_m2)
    return (P * 1000.0) / (A * 1e6)


def ringkasan(nilai_fc: Sequence[float]) -> dict:
    """Rata-rata, simpangan baku populasi, dan koefisien variasi."""
    nilai = [float(x) for x in nilai_fc]
    if not nilai:
        raise ValueError("daftar nilai f'c kosong")
    n = len(nilai)
    rerata = sum(nilai) / n
    simpangan = 0.0 if n == 1 else math.sqrt(sum((x - rerata) ** 2 for x in nilai) / n)
    cv = (simpangan / rerata * 100.0) if rerata else 0.0
    return {"n": n, "rerata": rerata, "simpangan_baku": simpangan, "cv_persen": cv}


def ambang_lalu_lintas_ringan() -> dict:
    """
    Ambang minimum yang BENAR-BENAR disitir naskah untuk perkerasan lalu lintas
    ringan. Bukan "SNI min 10 MPa" seperti yang tertulis di aplikasi lama.
    """
    return {
        "nilai": 5.0,
        "satuan": "MPa",
        "sumber": "Govedarica et al. (2022) via OUTPUT3 §2.2",
    }
