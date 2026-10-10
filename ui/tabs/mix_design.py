"""
Tab Kalkulator Mix Design — neraca massa rancangan campuran.

PENYAJIAN SAJA. Seluruh neraca massa dihitung `core/komposisi.py`; nilai
terukur dan target rancangan berasal dari `data/akses.py`.

AGREGATNYA BATU SIRTU SAJA
--------------------------
Hebel dan zeolit BUKAN bahan campuran beton, melainkan media retensi pada
lapisan terpisah di bawah beton poros (OUTPUT3 Tabel 4.2, §3.4.2). Pemilah
fraksi agregat menjadi sirtu/hebel/zeolit pada versi lama memodelkan sistem
material yang berbeda dari yang diteliti, dan sudah dihapus. Jangan
dikembalikan.

ACUAN KINERJA MILIK KONFIGURASI ACUAN, BUKAN SKENARIO AKTIF
-----------------------------------------------------------
Penaksir porositas, permeabilitas, dan kuat tekan dari komposisi sudah dihapus
(ADR-001): koefisiennya tidak bersumber, dan porositas tidak pernah diukur
pada benda uji penelitian ini sehingga tidak ada yang dapat mengkalibrasinya.

Bagian bawah tab menampilkan nilai terukur dan target rancangan milik
KONFIGURASI ACUAN PENELITIAN. Kepemilikan itu dinyatakan pada judul bagian,
label tiap kartu, dan keterangannya sekaligus — bukan hanya pada satu catatan
kaki. Alasannya: komposisi di bagian atas tab dapat digeser pengguna ke nilai
mana pun, sehingga tanpa pernyataan kepemilikan yang jelas ketiga angka itu
mudah terbaca sebagai hasil ukur komposisi yang sedang disusun.

Tab ini tidak memutuskan ketersediaan apa pun. Pertanyaan "apakah angka ini
berlaku untuk skenario aktif" milik lapisan resolusi (ADR-009, ADR-010), dan
jawabannya tampil di tabel perbandingan serta tab Kuat Tekan dan Retensi Air.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core import komposisi as kmp
from core import kuat_tekan as ktk
from data import akses

from .. import gaya
from ..components import evidence as komp_bukti
from ..components import provenance as komp_provenans
from ..components import warnings as komp_catatan

CATATAN_AGREGAT = (
    "**Agregat pada campuran ini adalah batu sirtu saja.** Hebel dan zeolit "
    "bukan bahan campuran beton, melainkan media retensi pada **lapisan "
    "terpisah** di bawah beton poros (OUTPUT3 Tabel 4.2, §3.4.2). Pemilah "
    "fraksi agregat menjadi sirtu/hebel/zeolit pada versi sebelumnya "
    "memodelkan sistem material yang berbeda dari yang diteliti, dan telah "
    "dihapus."
)

JUDUL_ACUAN_KINERJA = "**Acuan Kinerja — Konfigurasi Acuan Penelitian**"

CATATAN_ACUAN_KINERJA = (
    "Penaksir porositas, permeabilitas, dan kuat tekan dari komposisi telah "
    "dihapus (ADR-001). Koefisiennya tidak bersumber, dan porositas tidak "
    "pernah diukur pada benda uji penelitian ini sehingga tidak ada yang "
    "dapat mengkalibrasinya. Yang ditampilkan di bawah adalah nilai terukur "
    "dan target rancangan, bukan prediksi dari komposisi di atas."
)

KEPEMILIKAN_ACUAN_KINERJA = (
    "Ketiga angka di bawah milik **konfigurasi acuan penelitian**, bukan milik "
    "skenario yang sedang aktif. Ketersediaannya untuk skenario aktif "
    "dinyatakan pada tabel perbandingan di atas deretan tab, serta pada tab "
    "Kuat Tekan dan Retensi Air."
)

BANTUAN_BERAT_SATUAN = (
    "ASUMSI — tidak disebut naskah. Massa benda uji justru "
    "menyiratkan sekitar 1.280 kg/m³. Dapat diubah untuk melihat "
    "pengaruhnya terhadap neraca massa."
)


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Menghitung berapa kilogram semen, lumpur IPAL, batu sirtu, dan air yang "
    "diperlukan untuk membuat adukan beton poros dengan volume tertentu. "
    "\"Mix design\" berarti rancangan takaran campuran."
)


def render(st, substitusi_ipal_persen: float, faktor_air_pengikat: float) -> None:
    """
    Gambar seluruh tab Kalkulator Mix Design.

    Kontraknya dua skalar komposisi, bukan objek skenario: keduanya memang
    satu-satunya bagian skenario yang dipakai tab ini, dan keduanya hanya
    dibaca — nilai kanoniknya tetap dikendalikan bilah sisi.

    Tab ini tidak membaca hasil bersama maupun keluaran resolusi, sehingga
    tidak bergantung pada urutan eksekusi tab lain.
    """
    gaya.judul_bagian(st, "Optimizer Mix Design — ZEOPAVE-AQUA")
    gaya.pengantar(st, PENGANTAR)
    st.caption(
        "Neraca massa rancangan campuran beton poros mengikuti OUTPUT3 §3.3: "
        "rasio pengikat : agregat = 1 : 3, tanpa pasir. Perhitungan dilakukan "
        "core/komposisi.py."
    )
    komp_catatan.asumsi(st, CATATAN_AGREGAT)

    k1, k2 = st.columns([1, 1])
    with k1:
        volume_m3, berat_satuan = _parameter_rancangan(
            st, substitusi_ipal_persen, faktor_air_pengikat)
    with k2:
        mix = _hasil_rancangan(
            st, volume_m3, substitusi_ipal_persen, faktor_air_pengikat,
            berat_satuan)

    _panel_asumsi(st, mix)
    _acuan_kinerja(st)


# ─────────────────────── parameter rancangan ───────────────────────

def _parameter_rancangan(
    st, substitusi_ipal_persen: float, faktor_air_pengikat: float
) -> tuple[float, float]:
    """Parameter kanonik dari bilah sisi, ditambah volume dan berat satuan."""
    st.markdown("**Parameter Rancangan**")
    st.metric("Substitusi Lumpur IPAL", f"{substitusi_ipal_persen:.0f}%")
    st.metric("Faktor Air-Pengikat (f.a.b)", f"{faktor_air_pengikat:.2f}")
    st.caption(
        "Keduanya nilai kanonik dari bilah sisi dan berlaku untuk seluruh tab. "
        "Ubah di sana bila perlu."
    )

    volume_m3 = st.number_input(
        "Volume Adukan (m³)", 0.1, 100.0, 1.0, 0.1,
        help=("Banyaknya adukan beton poros yang ingin dibuat, dalam meter "
              "kubik (0,1 sampai 100 m³). 1 m³ sama dengan 1.000 liter."),
    )
    berat_satuan = st.number_input(
        "Berat Satuan Beton Poros (kg/m³)", 800.0, 2600.0,
        kmp.BERAT_SATUAN_ASUMSI, 10.0, help=BANTUAN_BERAT_SATUAN,
    )
    return volume_m3, berat_satuan


# ─────────────────────── hasil rancangan ───────────────────────

def _hasil_rancangan(
    st, volume_m3: float, substitusi_ipal_persen: float,
    faktor_air_pengikat: float, berat_satuan: float,
) -> dict:
    """Neraca massa beserta pemeriksaan ketertutupannya."""
    mix = kmp.rancangan_campuran(
        volume_m3=volume_m3,
        substitusi_ipal_persen=substitusi_ipal_persen,
        faktor_air_pengikat=faktor_air_pengikat,
        berat_satuan_kg_m3=berat_satuan,
    )

    st.markdown("**Hasil Rancangan Campuran**")
    tabel = pd.DataFrame([
        {"Material": r["Material"],
         "Massa (kg)": round(r["Massa (kg)"], 1),
         "Proporsi (%)": round(r["Proporsi (%)"], 1)}
        for r in kmp.komponen(mix)
    ])
    st.dataframe(tabel, width="stretch", hide_index=True)

    if mix["neraca_tertutup"]:
        st.caption(
            f"Neraca massa tertutup: jumlah komponen "
            f"{mix['jumlah_komponen_kg']:,.1f} kg = massa total "
            f"{mix['massa_total_kg']:,.1f} kg."
        )
    else:
        st.error(
            f"Neraca massa TIDAK tertutup — selisih "
            f"{mix['selisih_neraca_kg']:.6f} kg."
        )

    fig = go.Figure(go.Pie(
        labels=tabel["Material"], values=tabel["Massa (kg)"], hole=0.42,
        marker_colors=["#1565C0", "#00897B", "#E65100", "#0288D1"],
    ))
    fig.update_layout(
        title="Komposisi Campuran",
        height=300, margin=dict(t=40, b=10, l=10, r=10),
        showlegend=True, legend=dict(font_size=11),
    )
    st.plotly_chart(fig, width="stretch")
    return mix


def _panel_asumsi(st, mix: dict) -> None:
    """Asumsi yang belum terselesaikan, dibuka apa adanya."""
    if not mix["asumsi"]:
        return
    with st.expander(f"Asumsi yang belum terselesaikan ({len(mix['asumsi'])})"):
        for a in mix["asumsi"]:
            st.markdown(f"- {a}")
        st.caption(mix["catatan_agregat"])


# ─────────────────────── acuan kinerja ───────────────────────

def _acuan_kinerja(st) -> None:
    """
    Nilai terukur dan target rancangan MILIK KONFIGURASI ACUAN.

    Bagian ini adalah informasi konfigurasi acuan, bukan keluaran skenario
    aktif. Perbedaannya penting justru karena keduanya berada pada satu layar:
    komposisi di bagian atas tab dapat diubah pengguna, sementara ketiga angka
    di sini selamanya milik campuran yang benar-benar dicetak dan diuji.

    Karena itu kepemilikannya dinyatakan pada tiga tempat sekaligus — judul
    bagian, label tiap kartu, dan keterangan di bawah judul — bukan hanya pada
    satu catatan kaki yang mudah terlewat.

    Tab ini TIDAK menyelesaikan ketersediaan apa pun. Pertanyaan "apakah angka
    ini berlaku untuk skenario yang sedang aktif" dijawab lapisan resolusi
    (ADR-009, ADR-010), dan jawabannya ditampilkan tabel perbandingan serta tab
    Kuat Tekan dan Retensi Air. Menyalin jawaban itu ke sini akan membuat
    aturan ketersediaan kedua, justru yang dilarang ADR-010.
    """
    st.divider()
    st.markdown(JUDUL_ACUAN_KINERJA)
    st.caption(KEPEMILIKAN_ACUAN_KINERJA)
    st.caption(CATATAN_ACUAN_KINERJA)

    k3, k4, k5 = st.columns(3)
    kt = akses.besaran("KUAT_TEKAN_7_HARI")
    pm = akses.besaran("PERMEABILITAS")
    po_min = akses.besaran("POROSITAS_TARGET_MIN")
    po_maks = akses.besaran("POROSITAS_TARGET_MAKS")
    umur = akses.besaran("UMUR_UJI_HARI")

    with k3:
        komp_bukti.kotak_hasil(
            st, f"{po_min.nilai:.0f}–{po_maks.nilai:.0f}%",
            "Porositas — konfigurasi acuan",
            f"{po_maks.status.upper()} — belum diukur",
        )
        komp_provenans.keterangan(st, po_min)

    with k4:
        komp_bukti.kotak_hasil(
            st, f'{pm.nilai:.3f}<span style="font-size:1rem"> cm/dtk</span>',
            "Permeabilitas — konfigurasi acuan",
            f"{pm.status} · constant head, benda uji persegi",
        )
        komp_provenans.keterangan(st, pm)

    with k5:
        komp_bukti.kotak_hasil(
            st, f'{kt.nilai:.2f}<span style="font-size:1rem"> MPa</span>',
            "Kuat tekan — konfigurasi acuan",
            f"{kt.status} pada umur {umur.nilai:.0f} {umur.satuan} — hasil utama",
        )
        komp_provenans.keterangan(st, kt)

    ambang = ktk.ambang_lalu_lintas_ringan()
    st.caption(
        f"Ambang perkerasan lalu lintas ringan: {ambang['nilai']:.0f} "
        f"{ambang['satuan']} — {ambang['sumber']}."
    )
