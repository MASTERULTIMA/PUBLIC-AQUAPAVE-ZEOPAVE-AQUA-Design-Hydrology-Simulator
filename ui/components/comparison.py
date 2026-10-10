"""
Penyajian perbandingan skenario.

ATURAN SELISIH TIDAK DIPUTUSKAN DI SINI
---------------------------------------
Boleh atau tidaknya dua keluaran dibandingkan ditentukan
scenario/keluaran.selisih(), yang mengembalikan None untuk pasangan yang tidak
sebanding. Modul ini hanya menggambar hasilnya: bila selisihnya None, tidak
ada apa pun yang ditulis — bukan nol, bukan tanda hubung.
"""

from __future__ import annotations

import pandas as pd

from scenario import state as skenario
from scenario.keluaran import LABEL, URUTAN, Keluaran, OutputID, selisih

from .evidence import ringkasan_ketersediaan, teks_bukti
from .scenario import JUDUL_SKENARIO

#: Keterangan baku di bawah tabel perbandingan.
CATATAN_TABEL = (
    "Selisih hanya ditampilkan bila kedua keluaran tersedia, bersatuan sama, dan "
    "berstatus bukti sama. Membandingkan hasil terukur terhadap keluaran model "
    "menghasilkan angka yang tidak bermakna, sehingga sengaja dikosongkan. "
    "Kuat tekan, permeabilitas, dan retensi hanya tersedia untuk konfigurasi "
    "yang benar-benar diuji — tidak ada model yang memprediksi ketiganya dari "
    "komposisi."
)


def teks_sel(k: Keluaran, acuan: Keluaran | None = None) -> str:
    """
    Isi satu sel tabel perbandingan.

    Keluaran yang tersedia tampil sebagai nilai, satuan, dan status bukti,
    ditambah selisih terhadap acuan bila memang sebanding. Keluaran yang tidak
    tersedia tampil sebagai kalimat ketidaktersediaan, tanpa status bukti.
    """
    teks = teks_bukti(k)
    if not k.tersedia or acuan is None:
        return teks
    d = selisih(acuan, k)
    if d and abs(d["delta"]) > 1e-9:
        teks += f"  ({d['delta']:+,.2f})"
    return teks


def baris_tabel(hasil: dict[str, dict[OutputID, Keluaran]], kolom: list[str]) -> list[dict]:
    """Susun baris tabel perbandingan, satu baris per keluaran."""
    hasil_acuan = hasil[skenario.ACUAN]
    baris = []
    for oid in URUTAN:
        r = {"Keluaran": LABEL[oid]}
        for n in kolom:
            acuan = hasil_acuan[oid] if n != skenario.ACUAN else None
            r[JUDUL_SKENARIO[n]] = teks_sel(hasil[n][oid], acuan)
        baris.append(r)
    return baris


def tabel(st, hasil: dict, kolom: list[str]) -> None:
    """Gambar tabel perbandingan beserta keterangan bakunya."""
    if len(kolom) == 1:
        st.caption(
            "Hanya konfigurasi acuan yang aktif. Tambahkan skenario kustom di "
            "bilah sisi untuk membandingkan komposisi lain berdampingan."
        )
    st.dataframe(
        pd.DataFrame(baris_tabel(hasil, kolom)), width="stretch", hide_index=True
    )


def ringkasan(st, ringkas_per_skenario: dict, kolom: list[str]) -> None:
    """Satu metrik ketersediaan per skenario, berdampingan."""
    kols = st.columns(len(kolom))
    for i, n in enumerate(kolom):
        with kols[i]:
            ringkasan_ketersediaan(st, JUDUL_SKENARIO[n], ringkas_per_skenario[n])
