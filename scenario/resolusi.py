"""
Resolusi keluaran skenario — di sinilah pengaman ilmiahnya berada.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

ATURAN POKOK
------------
Hasil pengukuran laboratorium melekat pada **konfigurasi yang diuji**, bukan
pada aplikasi. Kuat tekan, permeabilitas, dan retensi hanya muncul untuk
skenario yang komposisinya sama persis dengan yang dicetak dan diuji.

Untuk komposisi lain, ketiganya dinyatakan **tidak tersedia**. Bukan nol, bukan
tanda hubung kosong, dan bukan angka hasil terkaan. Tidak ada model yang
menghubungkan tingkat substitusi ke ketiga properti itu — penelitian hanya
menguji satu komposisi dengan tiga benda uji (ADR-003), sehingga membuat
prediksi berarti mengarang.

Yang boleh dihitung ulang untuk komposisi apa pun hanyalah besaran yang memang
deterministik: massa campuran dan neraca emisi CO₂.

RANTAI KETIDAKTERSEDIAAN
------------------------
Air tertahan pada skala area diturunkan dari tingkat retensi. Bila retensi
tidak tersedia, air tertahan ikut tidak tersedia — ketidaktahuan merambat,
tidak berhenti diam-diam di tengah jalan.
"""

from __future__ import annotations

from core import emisi, hidrologi, komposisi as kmp
from data import akses

from .keluaran import (
    Keluaran,
    OutputID,
    StatusBukti,
    tersedia,
    tidak_tersedia,
)
from .state import Skenario, alasan_berbeda, cocok_konfigurasi_uji

#: Properti yang hanya berlaku untuk konfigurasi yang benar-benar diuji.
TERIKAT_KONFIGURASI_UJI: tuple[OutputID, ...] = (
    OutputID.COMPRESSIVE_STRENGTH,
    OutputID.PERMEABILITY,
    OutputID.RETENTION,
    OutputID.POROSITY,
)


def _catatan_kustom(sk: Skenario) -> str:
    beda = alasan_berbeda(sk)
    if not beda:
        return "Belum tersedia — konfigurasi ini belum diuji"
    return (
        "Belum tersedia — konfigurasi ini belum diuji. Berbeda dari acuan pada: "
        + "; ".join(beda)
    )


def resolusi(sk: Skenario) -> dict[OutputID, Keluaran]:
    """
    Selesaikan seluruh keluaran untuk satu skenario.

    >>> from .state import acuan_penelitian
    >>> r = resolusi(acuan_penelitian())
    >>> r[OutputID.COMPRESSIVE_STRENGTH].tersedia
    True
    >>> round(r[OutputID.COMPRESSIVE_STRENGTH].nilai, 2)
    13.19

    >>> from dataclasses import replace
    >>> kustom = replace(acuan_penelitian(), substitusi_ipal_persen=20.0)
    >>> r2 = resolusi(kustom)
    >>> r2[OutputID.COMPRESSIVE_STRENGTH].tersedia
    False
    >>> r2[OutputID.MIX_TOTAL_MASS].tersedia
    True
    """
    cocok = cocok_konfigurasi_uji(sk)
    catatan = _catatan_kustom(sk)
    hasil: dict[OutputID, Keluaran] = {}

    # ── deterministik: selalu dihitung ulang, untuk komposisi apa pun ──
    mix = kmp.rancangan_campuran(
        volume_m3=sk.volume_adukan_m3,
        substitusi_ipal_persen=sk.substitusi_ipal_persen,
        faktor_air_pengikat=sk.faktor_air_pengikat,
        berat_satuan_kg_m3=sk.berat_satuan_kg_m3,
        rasio_agregat=sk.rasio_agregat,
    )
    hasil[OutputID.MIX_TOTAL_MASS] = tersedia(
        OutputID.MIX_TOTAL_MASS, mix["massa_total_kg"], "kg",
        StatusBukti.DETERMINISTIK, "core/komposisi.py · OUTPUT3 §3.3",
        "Neraca massa tertutup; berat satuan berstatus asumsi.",
    )
    hasil[OutputID.IPAL_MASS] = tersedia(
        OutputID.IPAL_MASS, mix["massa_ipal_kg"], "kg",
        StatusBukti.DETERMINISTIK, "core/komposisi.py · OUTPUT3 §3.3",
        "Substitusi memindahkan massa di dalam pengikat.",
    )

    co2 = emisi.neraca(
        total_pengikat_ton=sk.total_pengikat_ton,
        substitusi_ipal_persen=sk.substitusi_ipal_persen,
        co2_per_ton_semen=sk.co2_per_ton_semen,
        co2_per_ton_ipal=sk.co2_per_ton_ipal,
    )
    hasil[OutputID.CO2_TOTAL] = tersedia(
        OutputID.CO2_TOTAL, co2["co2_zeopave_ton"], "ton CO₂",
        StatusBukti.DETERMINISTIK,
        "core/emisi.py · Scrivener et al. (2018); Habert et al. (2020)",
        "Faktor emisi lumpur IPAL masih asumsi.",
    )

    # ── terikat konfigurasi uji: hanya untuk komposisi yang benar-benar diuji ──
    if cocok:
        kt = akses.besaran("KUAT_TEKAN_7_HARI")
        hasil[OutputID.COMPRESSIVE_STRENGTH] = tersedia(
            OutputID.COMPRESSIVE_STRENGTH, kt.nilai, kt.satuan,
            StatusBukti.TERUKUR, kt.sumber, kt.catatan,
        )
        pm = akses.besaran("PERMEABILITAS")
        hasil[OutputID.PERMEABILITY] = tersedia(
            OutputID.PERMEABILITY, pm.nilai, pm.satuan,
            StatusBukti.TERUKUR, pm.sumber, pm.catatan,
        )
        rt = akses.besaran("RETENSI_RERATA")
        hasil[OutputID.RETENTION] = tersedia(
            OutputID.RETENTION, rt.nilai, rt.satuan,
            StatusBukti.TERUKUR, rt.sumber, rt.catatan,
        )
        po_min = akses.besaran("POROSITAS_TARGET_MIN")
        po_maks = akses.besaran("POROSITAS_TARGET_MAKS")
        hasil[OutputID.POROSITY] = tersedia(
            OutputID.POROSITY, po_maks.nilai, po_maks.satuan,
            StatusBukti.TARGET, po_maks.sumber,
            f"Target rancangan {po_min.nilai:.0f}–{po_maks.nilai:.0f}% — "
            "tidak pernah diukur pada benda uji penelitian ini.",
        )
    else:
        hasil[OutputID.COMPRESSIVE_STRENGTH] = tidak_tersedia(
            OutputID.COMPRESSIVE_STRENGTH, "MPa", catatan)
        hasil[OutputID.PERMEABILITY] = tidak_tersedia(
            OutputID.PERMEABILITY, "cm/detik", catatan)
        hasil[OutputID.RETENTION] = tidak_tersedia(
            OutputID.RETENTION, "%", catatan)
        hasil[OutputID.POROSITY] = tidak_tersedia(
            OutputID.POROSITY, "%", catatan)

    # ── rantai: air tertahan bergantung pada retensi ──
    retensi = hasil[OutputID.RETENTION]
    if retensi.tersedia:
        sk_hidro = hidrologi.skenario(
            sk.intensitas_hujan_mm_per_jam, sk.luas_area_m2,
            sk.durasi_hujan_jam, retensi.nilai,
        )
        hasil[OutputID.RUNOFF] = tersedia(
            OutputID.RUNOFF, sk_hidro["air_tertahan_liter"], "liter",
            StatusBukti.DETERMINISTIK, "core/hidrologi.py · OUTPUT3 §4.6",
            "Ekstrapolasi skala dari retensi skala laboratorium, bukan "
            "pengukuran lapangan.",
        )
    else:
        hasil[OutputID.RUNOFF] = tidak_tersedia(
            OutputID.RUNOFF, "liter",
            "Belum tersedia — diturunkan dari tingkat retensi, yang belum "
            "diketahui untuk konfigurasi ini",
        )

    return hasil


def ringkas_ketersediaan(hasil: dict[OutputID, Keluaran]) -> dict:
    """Hitungan cepat untuk hierarki informasi di antarmuka."""
    tersedia_n = sum(1 for k in hasil.values() if k.tersedia)
    return {
        "total": len(hasil),
        "tersedia": tersedia_n,
        "tidak_tersedia": len(hasil) - tersedia_n,
        "terukur": sum(
            1 for k in hasil.values()
            if k.tersedia and k.status_bukti is StatusBukti.TERUKUR
        ),
    }
