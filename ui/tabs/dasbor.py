"""
Tab Dasbor Perbandingan Kinerja.

PENYAJIAN SAJA. Dasbor tidak menghitung sains apa pun sendiri: neraca emisi
datang sebagai hasil bersama (ADR-008), dan air tertahan datang sudah selesai
dari `scenario/resolusi.py` (ADR-010). Modul ini menggambar jawabannya.

TIGA JENIS ANGKA YANG SENGAJA DIPISAH
-------------------------------------
1. **Penilaian kualitatif tim** — radar kinerja. Skala 0–100 komparatif, tanpa
   metodologi penskoran terdokumentasi. Bukan pengukuran, bukan literatur,
   bukan model. Tidak boleh dikutip sebagai temuan penelitian.

2. **Data konfigurasi acuan** — tabel perbandingan rinci. Ia menggambarkan
   ZEOPAVE-AQUA sebagai artefak penelitian terhadap perkerasan konvensional,
   BUKAN skenario yang sedang aktif.

3. **Ringkasan dampak skenario aktif** — satu-satunya bagian yang memang milik
   skenario aktif, dan karenanya satu-satunya yang tunduk pada ketersediaan.

RINGKASAN DAMPAK MENGIKUTI KETERSEDIAAN
---------------------------------------
Air tertahan diturunkan dari tingkat retensi. Bila retensi belum diukur untuk
komposisi yang sedang aktif, air tertahan ikut tidak tersedia — dasbor tidak
boleh diam-diam memakai 40,0% milik konfigurasi acuan, sebagaimana Tab 4 juga
tidak boleh (S5-4).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data import akses
from scenario.keluaran import Keluaran

from .. import gaya
from ..components import warnings as komp_catatan

#: Radar kinerja — PENILAIAN KUALITATIF TIM, bukan hasil pengukuran.
#: Skala 0-100 komparatif; tidak ada metodologi penskoran terdokumentasi.
KATEGORI_RADAR = (
    "Permeabilitas", "Retensi Air", "Efisiensi CO₂",
    "Porositas", "Kuat Tekan Struktural", "Pemanfaatan IPAL",
)
SKOR_ZEOPAVE = (95, 80, 75, 85, 65, 90)
SKOR_KONVENSIONAL = (5, 0, 20, 5, 85, 0)

PERINGATAN_RADAR = (
    "**Skor radar di bawah adalah penilaian kualitatif tim, bukan hasil "
    "pengukuran.** Skala 0–100 bersifat **komparatif dan relatif**: ia "
    "menyatakan posisi relatif kedua jenis perkerasan menurut penilaian tim "
    "peneliti, bukan persentase dari suatu nilai maksimum yang terukur. "
    "Tidak ada metodologi penskoran yang terdokumentasi, dan angka-angka ini "
    "tidak boleh dikutip sebagai temuan penelitian."
)

#: SD-06 ditutup (keputusan penulis): metrik "Lumpur IPAL Termanfaatkan" dan
#: "CO2 Terhindarkan" DIPENSIUNKAN dari dasbor, beserta konstanta
#: IPAL_TON_PER_100_M2 = 0,8 yang memberi makan keduanya.
#:
#: Sebabnya bukan angkanya kurang tepat, melainkan angkanya mewakili BAHAN
#: YANG SALAH. Penelusuran menemukan satu-satunya "0,8 per 100 m2" di dalam
#: sumber proyek adalah kalimat Abstrak naskah tentang kebutuhan SEMEN, dan
#: klaim itu sendiri sudah ditandai untuk dikoreksi karena tanpa perhitungan
#: pendukung.
#:
#: TIDAK DIGANTI angka lain.
#:
#: Saat SD-06 diputuskan, dua basis perhitungan masih bersaing: resep Tab 7
#: (substitusi 40%) memberi sekitar 3,52 t/1.000 m2, campuran kanonik
#: (substitusi 15%) memberi sekitar 1,26 t/1.000 m2. C-03 kemudian menutup
#: persaingan itu — Tab 7 memakai campuran kanonik, sehingga kini hanya satu
#: basis tersisa, sekitar 1,26 t/1.000 m2.
#:
#: Metrik ini tetap dipensiunkan, dan sebabnya bergeser: bukan lagi karena
#: basisnya bersaing, melainkan karena memulihkannya adalah keputusan penulis
#: yang belum diambil, dan karena basis itu masih bertumpu sepenuhnya pada
#: berat satuan beton poros yang berstatus asumsi (SD-16C terbuka).
#:
#: Ini pemensiunan keluaran, BUKAN pembatalan model emisi. core/emisi.neraca()
#: tetap berlaku dan tetap dipakai Tab 5 lewat hasil bersama.
CATATAN_METRIK_DIPENSIUNKAN = (
    "Metrik **lumpur IPAL termanfaatkan** dan **CO₂ terhindarkan** untuk luas "
    "proyek dipensiunkan: keduanya bertumpu pada tonase yang ternyata mewakili "
    "kebutuhan **semen**, bukan lumpur IPAL. Keduanya tidak diganti angka lain "
    "karena memulihkannya adalah keputusan penulis yang belum diambil, dan "
    "karena basis penggantinya bertumpu pada berat satuan beton poros yang "
    "masih berstatus asumsi. Neraca emisi CO₂ skenario aktif tetap tersedia "
    "di tab Emisi CO₂."
)

#: Kalimat baku untuk sel yang tidak punya dasar di dalam sumber proyek.
TIDAK_BERSUMBER = "tidak ada sumber di dalam penelitian"

PESAN_AIR_TIDAK_TERSEDIA = (
    "Air tertahan diturunkan dari tingkat retensi, yang belum diukur untuk "
    "komposisi ini. Dasbor tidak memakai nilai konfigurasi lain sebagai "
    "penggantinya. Gunakan tab Retensi Air bila ingin menjelajah skenario "
    "dengan asumsi Anda sendiri."
)


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Ringkasan berdampingan antara ZEOPAVE-AQUA dan perkerasan biasa yang "
    "kedap air. Sebagian isinya penilaian kualitatif, dan ditandai demikian."
)


def render(
    st,
    retensi_aktif: Keluaran,
    air_tertahan_aktif: Keluaran,
) -> None:
    """
    Gambar seluruh dasbor.

    `retensi_aktif` dan `air_tertahan_aktif` — keluaran yang sudah diselesaikan
    `scenario/resolusi.py`, objek yang sama dengan pengisi tabel perbandingan
    (ADR-010). Ketersediaannya tidak diputuskan di sini.

    KONTRAK DIPERSEMPIT PADA SD-06. Dasbor dahulu menerima `hasil_co2` dan
    `luas_area_m2`, keduanya HANYA untuk memberi makan metrik lumpur IPAL dan
    CO2 per luas proyek. Kedua metrik itu dipensiunkan, sehingga kedua
    parameter menjadi mati dan ikut dihapus daripada dibiarkan menggantung.

    Neraca emisi bersama TIDAK dibatalkan: `core/emisi.neraca()` tetap
    dihitung sekali di akar komposisi dan tetap dibaca Tab 5 (ADR-008).
    Yang berubah hanya: dasbor tidak lagi termasuk pembacanya.
    """
    gaya.judul_bagian(st, "Dasbor Perbandingan Kinerja")
    gaya.pengantar(st, PENGANTAR)
    st.caption(
        "ZEOPAVE-AQUA vs Perkerasan Konvensional Kedap Air — "
        "perbandingan teknis dan lingkungan secara komprehensif."
    )

    _radar_kualitatif(st)
    _tabel_perbandingan(st)

    st.divider()
    _ringkasan_dampak(st, retensi_aktif, air_tertahan_aktif)


# ═══════════ 1. penilaian kualitatif tim ═══════════

def _radar_kualitatif(st) -> None:
    """Radar kinerja. Penilaian tim, dan dinyatakan begitu sebelum digambar."""
    komp_catatan.keterbatasan(st, PERINGATAN_RADAR)

    kategori = list(KATEGORI_RADAR)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(SKOR_ZEOPAVE) + [SKOR_ZEOPAVE[0]],
        theta=kategori + [kategori[0]],
        fill="toself", name="ZEOPAVE-AQUA",
        line=dict(color="#1565C0", width=2.5),
        fillcolor="rgba(21,101,192,0.2)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=list(SKOR_KONVENSIONAL) + [SKOR_KONVENSIONAL[0]],
        theta=kategori + [kategori[0]],
        fill="toself", name="Perkerasan Konvensional",
        line=dict(color="#EF5350", width=2.5),
        fillcolor="rgba(239,83,80,0.1)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True, height=420,
        title="Radar Kinerja Multi-Kriteria (penilaian kualitatif tim)",
        margin=dict(t=50, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, width="stretch")


# ═══════════ 2. data konfigurasi acuan ═══════════

def _angka(b, desimal: int = 2) -> str:
    """
    Angka besaran dengan koma desimal, mengikuti penulisan Indonesia.

    Jumlah desimal ditentukan pemanggil agar ketelitian yang dilaporkan naskah
    tidak hilang: retensi tetap 40,0% dan bukan 40%.
    """
    return f"{b.nilai:.{desimal}f}".replace(".", ",")


def _sel(b, desimal: int = 2, awalan: str = "") -> str:
    """Satu sel klaim: nilai, satuan, dan status buktinya — dari sumber kanonik."""
    return f"{awalan}{_angka(b, desimal)} {b.satuan} ({b.status})"


def baris_perbandingan() -> list[dict]:
    """
    Baris tabel perbandingan, dibangun dari nilai kanonik.

    Setiap klaim ilmiah di sini melewati `data/akses.py`, sehingga penjaga
    ADR-001 hidup pada jalurnya. Sebelum S6-B seluruh selnya adalah literal
    teks, dan lewat pintu itulah empat nilai yang sudah dihapus kembali:
    0,45–0,75 cm/dtk, ACI 522 ≥ 0,14, SNI min 10 MPa, dan 15,00 MPa "(lab)".

    Sel yang tidak punya dasar di dalam sumber proyek dinyatakan begitu apa
    adanya. Tidak ada tanda centang: status bukti ditulis sebagai kata,
    sehingga target dan keluaran model tidak dapat naik pangkat menjadi
    pencapaian hanya karena tanda grafis.
    """
    perm = akses.besaran("PERMEABILITAS")
    perm_konv = akses.besaran("PERM_BETON_KONVENSIONAL")
    poro_min = akses.besaran("POROSITAS_TARGET_MIN")
    poro_maks = akses.besaran("POROSITAS_TARGET_MAKS")
    kuat = akses.besaran("KUAT_TEKAN_7_HARI")
    umur = akses.besaran("UMUR_UJI_HARI")
    ambang = akses.besaran("AMBANG_LALU_LINTAS_RINGAN")
    retensi = akses.besaran("RETENSI_RERATA")
    co2_min = akses.besaran("CO2_PER_TON_SEMEN_MIN")
    co2_maks = akses.besaran("CO2_PER_TON_SEMEN_MAKS")
    ipal = akses.besaran("SUBSTITUSI_IPAL")
    tertahan = akses.besaran("SKALA_AIR_TERTAHAN")
    luas = akses.besaran("SKALA_LUAS_ACUAN")

    return [
        {
            "Parameter": "Permeabilitas",
            "Perkerasan Konvensional": f"< {_angka(perm_konv, 2)} {perm_konv.satuan} "
                                       f"({perm_konv.status})",
            "ZEOPAVE-AQUA": _sel(perm, 3),
            "Sumber": f"{perm.sumber}; pembanding {perm_konv.sumber}",
        },
        {
            "Parameter": "Porositas",
            "Perkerasan Konvensional": TIDAK_BERSUMBER,
            "ZEOPAVE-AQUA": f"{_angka(poro_min, 0)}–{_angka(poro_maks, 0)} "
                            f"{poro_maks.satuan} ({poro_maks.status} — belum diukur)",
            "Sumber": poro_maks.sumber,
        },
        {
            "Parameter": f"Kuat Tekan ({umur.nilai:.0f} {umur.satuan})",
            "Perkerasan Konvensional": TIDAK_BERSUMBER,
            "ZEOPAVE-AQUA": _sel(kuat, 2),
            "Sumber": f"{kuat.sumber}; ambang {_angka(ambang, 0)} {ambang.satuan} "
                      f"— {ambang.sumber}",
        },
        {
            "Parameter": "Retensi Air",
            "Perkerasan Konvensional": TIDAK_BERSUMBER,
            "ZEOPAVE-AQUA": _sel(retensi, 1),
            "Sumber": retensi.sumber,
        },
        {
            "Parameter": "Reduksi Limpasan",
            "Perkerasan Konvensional": TIDAK_BERSUMBER,
            "ZEOPAVE-AQUA": "tidak diukur",
            "Sumber": TIDAK_BERSUMBER,
        },
        {
            "Parameter": "CO₂ per ton semen",
            "Perkerasan Konvensional": f"{_angka(co2_min, 1)}–{_angka(co2_maks, 1)} "
                                       f"{co2_maks.satuan} ({co2_maks.status})",
            "ZEOPAVE-AQUA": "bergantung faktor emisi yang dipilih — lihat Tab 5 "
                            "(deterministik)",
            "Sumber": co2_min.sumber,
        },
        {
            "Parameter": "Pemanfaatan Lumpur IPAL",
            "Perkerasan Konvensional": "tidak ada",
            "ZEOPAVE-AQUA": f"substitusi {_sel(ipal, 0)}",
            "Sumber": ipal.sumber,
        },
        {
            "Parameter": "Optimasi Material",
            "Perkerasan Konvensional": TIDAK_BERSUMBER,
            "ZEOPAVE-AQUA": "tidak tersedia — klaim dihapus (ADR-001)",
            "Sumber": TIDAK_BERSUMBER,
        },
        {
            "Parameter": "Kapasitas Mitigasi Banjir",
            "Perkerasan Konvensional": "tidak ada",
            "ZEOPAVE-AQUA": f"{tertahan.nilai:,.0f}".replace(",", ".")
                            + f" {tertahan.satuan} per {luas.nilai:,.0f}".replace(",", ".")
                            + f" {luas.satuan} ({tertahan.status})",
            "Sumber": tertahan.sumber,
        },
    ]


def _tabel_perbandingan(st) -> None:
    """
    Tabel perbandingan rinci — konfigurasi acuan terhadap perkerasan
    konvensional, bukan skenario yang sedang aktif.
    """
    st.markdown("**Tabel Perbandingan Rinci**")
    st.dataframe(pd.DataFrame(baris_perbandingan()), width="stretch",
                 hide_index=True)
    st.caption(
        "Tabel ini menggambarkan **konfigurasi acuan penelitian** terhadap "
        "perkerasan konvensional, bukan skenario yang sedang aktif. Dampak "
        "skenario aktif ada di bawah."
    )
    st.caption(
        f"Setiap angka di atas berasal dari sumber kanonik proyek beserta status "
        f"buktinya. Sel bertuliskan “{TIDAK_BERSUMBER}” berarti "
        "penelitian ini tidak memuat dasarnya — bukan berarti nilainya nol."
    )


# ═══════════ 3. ringkasan dampak skenario aktif ═══════════

def _ringkasan_dampak(st, retensi: Keluaran, air_tertahan: Keluaran) -> None:
    """
    Dampak untuk lokasi pengguna pada skenario yang sedang aktif.

    Air tertahan mengikuti ketersediaan retensi. Metrik lumpur IPAL dan CO2
    per luas proyek dipensiunkan pada SD-06; keduanya dahulu bertumpu pada
    tonase yang mewakili kebutuhan semen, bukan lumpur IPAL.
    """
    st.markdown("**Ringkasan Dampak untuk Lokasi Anda**")
    m1, m2 = st.columns(2)

    with m1:
        if air_tertahan.tersedia:
            st.metric(
                "Air Tersimpan (hujan 1 jam)",
                f"{air_tertahan.nilai / 1000.0:.0f} m³",
                delta=f"+{retensi.nilai:.0f}% vs 0%",
            )
        else:
            komp_catatan.tidak_tersedia(st, air_tertahan)
            st.caption(PESAN_AIR_TIDAK_TERSEDIA)
    with m2:
        st.metric("Optimasi Material", "n/a", delta="klaim dihapus",
                  delta_color="off")

    st.caption(CATATAN_METRIK_DIPENSIUNKAN)
