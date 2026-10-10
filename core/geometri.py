"""
Geometri benda uji — luas penampang.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state. Masukan bertipe, keluaran
bertipe, deterministik.

Alasan modul ini ada: aplikasi lama hanya mendukung benda uji silinder karena
luas dihitung langsung dari diameter. Eksperimen permeabilitas yang dikonfirmasi
tim justru memakai benda uji PERSEGI 15 x 15 cm (A = 225 cm2), sehingga data
penelitian sendiri tidak dapat dimasukkan tanpa mengarang diameter setara.

Kompatibilitas mundur: BENTUK_BAWAAN tetap "lingkaran", sehingga alur kerja lama
menghasilkan angka yang sama persis.
"""

from __future__ import annotations

import math

LINGKARAN = "lingkaran"
PERSEGI_PANJANG = "persegi_panjang"
LANGSUNG = "langsung"

BENTUK_BAWAAN = LINGKARAN

BENTUK_TERSEDIA = {
    LINGKARAN: "Silinder — dari diameter",
    PERSEGI_PANJANG: "Persegi / persegi panjang — dari lebar x panjang",
    LANGSUNG: "Luas penampang dimasukkan langsung",
}


def _positif(nama: str, nilai: float) -> float:
    if nilai is None:
        raise ValueError(f"{nama} wajib diisi")
    nilai = float(nilai)
    if nilai <= 0:
        raise ValueError(f"{nama} harus lebih besar dari nol, diterima {nilai}")
    if not math.isfinite(nilai):
        raise ValueError(f"{nama} harus berupa bilangan berhingga")
    return nilai


def luas_lingkaran(diameter_cm: float) -> float:
    """Luas penampang silinder, cm^2. A = pi * (d/2)^2"""
    d = _positif("diameter", diameter_cm)
    return math.pi * (d / 2.0) ** 2


def luas_persegi_panjang(lebar_cm: float, panjang_cm: float) -> float:
    """Luas penampang persegi atau persegi panjang, cm^2. A = lebar x panjang"""
    b = _positif("lebar", lebar_cm)
    p = _positif("panjang", panjang_cm)
    return b * p


def luas_penampang(bentuk: str = BENTUK_BAWAAN, **dimensi: float) -> float:
    """
    Hitung luas penampang benda uji dalam cm^2.

    bentuk="lingkaran"        -> diameter_cm
    bentuk="persegi_panjang"  -> lebar_cm, panjang_cm
    bentuk="langsung"         -> luas_cm2

    Contoh — konfigurasi laboratorium yang dikonfirmasi (persegi 15 x 15 cm):

    >>> round(luas_penampang("persegi_panjang", lebar_cm=15, panjang_cm=15), 4)
    225.0

    Contoh — perilaku lama tetap sama (silinder 150 mm = 15 cm):

    >>> round(luas_penampang("lingkaran", diameter_cm=15), 2)
    176.71
    """
    if bentuk == LINGKARAN:
        return luas_lingkaran(dimensi["diameter_cm"])
    if bentuk == PERSEGI_PANJANG:
        return luas_persegi_panjang(dimensi["lebar_cm"], dimensi["panjang_cm"])
    if bentuk == LANGSUNG:
        return _positif("luas", dimensi["luas_cm2"])
    raise ValueError(
        f"bentuk tidak dikenal: {bentuk!r}. Pilihan: {sorted(BENTUK_TERSEDIA)}"
    )
