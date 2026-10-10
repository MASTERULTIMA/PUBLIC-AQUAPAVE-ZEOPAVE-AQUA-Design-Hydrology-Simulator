"""
Retensi air prototipe — metode simulasi curah hujan.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

Sumber: OUTPUT3 §4.4, Tabel 4.3, Persamaan 4.4 sampai 4.8.
Nilai rerata resmi setelah koreksi penulis adalah 40,0% (ADR: keputusan
penulis 30 Agustus 2026). Angka 39,7% pada pelaporan sebelumnya merupakan
ketidaksesuaian penyalinan dan tidak dipakai lagi.

Simpangan baku dan koefisien variasi pada naskah (1,0% dan 2,5%) dihitung
dengan pembagi (n-1), yaitu simpangan baku SAMPEL. Modul ini memakai konvensi
yang sama agar reproduksinya cocok.
"""

from __future__ import annotations

import math
from typing import Sequence

# Data uji yang dikonfirmasi (OUTPUT3 Tabel 4.3), menyalin
# akses.dataset_retensi() dan besaran kanonik turunannya.
# Kesetaraannya terhadap konstanta.py dijaga validation/test_duplikasi_kanonik.py.
LAB_UJI = (
    {"nama": "Uji 1", "input_ml": 1000.0, "output_ml": 600.0},
    {"nama": "Uji 2", "input_ml": 1000.0, "output_ml": 590.0},
    {"nama": "Uji 3", "input_ml": 1000.0, "output_ml": 610.0},
)
LAB_RETENSI_RERATA_PERSEN = 40.0
LAB_SIMPANGAN_BAKU_PERSEN = 1.0
LAB_CV_PERSEN = 2.5


def volume_terserap_ml(input_ml: float, output_ml: float) -> float:
    """V_terserap = V_input - V_output (Persamaan 4.4), dalam ml."""
    vin = float(input_ml)
    vout = float(output_ml)
    if vin <= 0:
        raise ValueError("volume masukan harus lebih besar dari nol")
    if vout < 0:
        raise ValueError("volume keluaran tidak boleh negatif")
    if vout > vin:
        raise ValueError("volume keluaran tidak boleh melebihi volume masukan")
    return vin - vout


def retensi_persen(input_ml: float, output_ml: float) -> float:
    """
    Retensi = V_terserap / V_input * 100 (Persamaan 4.5).

    >>> round(retensi_persen(1000, 600), 1)
    40.0
    """
    return volume_terserap_ml(input_ml, output_ml) / float(input_ml) * 100.0


def ringkasan(nilai_retensi: Sequence[float]) -> dict:
    """
    Rata-rata (Pers. 4.6), simpangan baku sampel (Pers. 4.7), dan koefisien
    variasi (Pers. 4.8).

    >>> r = ringkasan([40.0, 41.0, 39.0])
    >>> round(r["rerata"], 1), round(r["simpangan_baku"], 1), round(r["cv_persen"], 1)
    (40.0, 1.0, 2.5)
    """
    nilai = [float(x) for x in nilai_retensi]
    if not nilai:
        raise ValueError("daftar nilai retensi kosong")
    n = len(nilai)
    rerata = sum(nilai) / n
    if n == 1:
        simpangan = 0.0
    else:
        simpangan = math.sqrt(sum((x - rerata) ** 2 for x in nilai) / (n - 1))
    cv = (simpangan / rerata * 100.0) if rerata else 0.0
    return {"n": n, "rerata": rerata, "simpangan_baku": simpangan, "cv_persen": cv}


def ringkasan_lab() -> dict:
    """Ringkasan atas ketiga pengujian yang terdokumentasi di Tabel 4.3."""
    return ringkasan([retensi_persen(u["input_ml"], u["output_ml"]) for u in LAB_UJI])
