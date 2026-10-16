"""
Neraca emisi CO2 dari substitusi semen.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

KELAS BUKTI
    Perhitungannya deterministik (kelas B): sebuah neraca massa linear.
    Faktor emisi semen berasal dari pustaka (kelas C): 0,8-0,9 ton CO2 per ton
    semen (Scrivener et al., 2018; Habert et al., 2020).
    Faktor emisi lumpur IPAL adalah ASUMSI: naskah tidak menyebutnya, dan
    karbon tertanamnya belum pernah dihitung untuk sumber lumpur ini.

Modul ini menghitung neraca sekali, lalu hasilnya dipakai bersama oleh tab
mana pun yang membutuhkannya. Sebelumnya Tab 6 membaca variabel lokal milik
Tab 5, sehingga aplikasi bergantung pada urutan eksekusi (ADR-008).
"""

from __future__ import annotations

import math


def _positif(nama: str, nilai: float) -> float:
    nilai = float(nilai)
    if not math.isfinite(nilai) or nilai <= 0:
        raise ValueError(f"{nama} harus bilangan positif berhingga, diterima {nilai}")
    return nilai


def _persen(nama: str, nilai: float) -> float:
    nilai = float(nilai)
    if not 0.0 <= nilai <= 100.0:
        raise ValueError(f"{nama} harus 0-100 persen, diterima {nilai}")
    return nilai


def neraca(
    total_pengikat_ton: float,
    substitusi_ipal_persen: float,
    co2_per_ton_semen: float,
    co2_per_ton_ipal: float,
) -> dict:
    """
    Neraca emisi untuk sejumlah pengikat tertentu.

    Mengembalikan dict berisi emisi konvensional (100% semen), emisi ZEOPAVE,
    penghematan, dan persentase reduksinya.

    >>> h = neraca(10.0, 15.0, 0.85, 0.05)
    >>> round(h["co2_konvensional_ton"], 2), round(h["co2_zeopave_ton"], 2)
    (8.5, 7.3)
    >>> round(h["reduksi_persen"], 1)
    14.1
    """
    total = _positif("total pengikat", total_pengikat_ton)
    sub = _persen("substitusi IPAL", substitusi_ipal_persen)
    e_semen = _positif("faktor emisi semen", co2_per_ton_semen)

    e_ipal = float(co2_per_ton_ipal)
    if not math.isfinite(e_ipal) or e_ipal < 0:
        raise ValueError(f"faktor emisi IPAL tidak boleh negatif, diterima {e_ipal}")

    semen_ton = total * (1.0 - sub / 100.0)
    ipal_ton = total * (sub / 100.0)

    konv = total * e_semen
    zeopave = semen_ton * e_semen + ipal_ton * e_ipal
    hemat = konv - zeopave

    return {
        "status_bukti": "model",
        "total_pengikat_ton": total,
        "substitusi_ipal_persen": sub,
        "semen_terpakai_ton": semen_ton,
        "ipal_terpakai_ton": ipal_ton,
        "co2_konvensional_ton": konv,
        "co2_zeopave_ton": zeopave,
        "co2_dihemat_ton": hemat,
        "reduksi_persen": (hemat / konv * 100.0) if konv else 0.0,
        "faktor_emisi_semen": e_semen,
        "faktor_emisi_ipal": e_ipal,
    }


def tren_substitusi(
    total_pengikat_ton: float,
    co2_per_ton_semen: float,
    co2_per_ton_ipal: float,
    maks_persen: int = 25,
) -> list[tuple[float, float]]:
    """Pasangan (substitusi %, emisi ton) dari 0 sampai maks_persen."""
    return [
        (float(p), neraca(total_pengikat_ton, p, co2_per_ton_semen, co2_per_ton_ipal)["co2_zeopave_ton"])
        for p in range(0, int(maks_persen) + 1)
    ]


def reduksi_per_kadar(
    kadar_persen,
    co2_per_ton_semen: float,
    co2_per_ton_ipal: float,
) -> list[tuple[float, float]]:
    """
    Pasangan (substitusi %, pengurangan CO2 %) terhadap campuran 100% semen.

    Persentasenya tidak bergantung pada jumlah pengikat, jadi dihitung untuk
    1 ton pengikat.

    >>> [(p, round(r, 1)) for p, r in reduksi_per_kadar([0, 15], 0.85, 0.05)]
    [(0.0, 0.0), (15.0, 14.1)]
    """
    return [
        (float(p), neraca(1.0, p, co2_per_ton_semen, co2_per_ton_ipal)["reduksi_persen"])
        for p in kadar_persen
    ]


def rentang_faktor_emisi_semen() -> dict:
    """Rentang faktor emisi semen yang disitir naskah."""
    return {
        "min": 0.8,
        "maks": 0.9,
        "satuan": "ton CO₂ per ton semen",
        "sumber": "Scrivener et al. (2018); Habert et al. (2020)",
    }
