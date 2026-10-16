"""
Tab Permeabilitas — metode constant head.

PENYAJIAN SAJA. Tidak ada persamaan permeabilitas di berkas ini: seluruhnya
dipanggil dari `core/permeabilitas.py`, dan luas penampang dari
`core/geometri.py`. Bila sebuah rumus muncul di sini, itu bug arsitektur.

Metode fisik dikonfirmasi tim eksperimen sebagai constant head (ADR-006).
Konfigurasi laboratorium yang direproduksi tab ini:

    benda uji persegi 15 x 15 cm  ->  A = 225 cm2
    tebal L = 2 cm
    tinggi tekan tetap h = 6 cm
    kecepatan aliran v = 5 cm/detik  ->  Q = v * A = 1.125 cm3/detik
    k = Q * L / (A * h) = 1,667 cm/detik

DUA HAL YANG BERBEDA DI SATU TAB
--------------------------------
1. **Acuan penelitian** — konfigurasi yang benar-benar diuji, beserta hasil
   pengukurannya. Berstatus bukti *terukur*.
2. **Kalkulator** — geometri dan data yang dimasukkan pengguna, dihitung
   dengan persamaan yang sama. Berstatus *deterministik*, bukan terukur.

Keduanya memakai persamaan yang sama, tetapi tidak boleh disajikan sebagai hal
yang sama. Angka yang keluar dari kalkulator adalah hasil hitungan atas
masukan pengguna, bukan pengukuran laboratorium — dan tab ini harus terus
menyatakan perbedaan itu.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core import geometri
from core import permeabilitas as perm
from data import akses

from .. import gaya
from ..components import evidence as komp_bukti
from ..components import warnings as komp_catatan

#: Nilai bawaan yang mereproduksi konfigurasi laboratorium (OUTPUT3 §4.5).
ACUAN_LEBAR_CM = 15.0
ACUAN_PANJANG_CM = 15.0
ACUAN_TEBAL_CM = perm.LAB_TEBAL_CM
ACUAN_TINGGI_TEKAN_CM = perm.LAB_TINGGI_TEKAN_CM
ACUAN_DEBIT_CM3_PER_DETIK = perm.LAB_KECEPATAN_CM_PER_DETIK * perm.LAB_LUAS_CM2

#: Diameter bawaan alur kerja silinder lama, dipertahankan apa adanya.
BAWAAN_DIAMETER_MM = 150.0

MODUS_DEBIT = "Debit volumetrik"
MODUS_VOLUME = "Volume terkumpul + waktu"


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Permeabilitas menyatakan seberapa cepat air menembus beton poros. Tab "
    "ini menghitungnya dari data uji aliran air melalui benda uji. Makin "
    "besar nilai k (cm/detik), makin cepat air meresap."
)


def render(st) -> None:
    """
    Gambar seluruh tab Permeabilitas.

    Kontraknya hanya `st`. Tab ini tidak membaca skenario aktif, neraca CO2,
    luas area, maupun variabel apa pun milik tab lain: ia berdiri sendiri dan
    tidak bergantung pada urutan eksekusi.
    """
    gaya.judul_bagian(st, "Permeabilitas — Metode Constant Head")
    gaya.pengantar(st, PENGANTAR)
    st.caption(
        "Metode constant head, dikonfirmasi tim eksperimen (ADR-006). Persamaan "
        "didokumentasikan dengan rujukan SNI 2435:2008. Kesesuaian peralatan dan "
        "prosedur terhadap seluruh ketentuan standar tersebut belum diverifikasi "
        "butir demi butir, sehingga kepatuhan penuh tidak dinyatakan."
    )

    mode_acuan = _pemilih_mode(st)

    p1, p2 = st.columns(2)
    with p1:
        luas_cm2, tebal_cm, tinggi_tekan_cm = _masukan_geometri(st, mode_acuan)
        nilai_k, baris = _masukan_pengujian(st, tebal_cm, luas_cm2, tinggi_tekan_cm)
    with p2:
        _panel_hasil(st, nilai_k, baris, luas_cm2, tebal_cm, tinggi_tekan_cm)


# ────────────────────────────── mode ──────────────────────────────

def _pemilih_mode(st) -> bool:
    """
    Acuan penelitian atau kalkulator bebas.

    Pada mode acuan seluruh kendali geometri dikunci pada nilai yang
    benar-benar diuji, sehingga tab mereproduksi OUTPUT3 §4.5 apa adanya.
    """
    mode_acuan = st.toggle(
        "Konfigurasi Acuan Penelitian",
        value=True,
        help=(
            "Aktif: memakai benda uji yang benar-benar diuji laboratorium "
            "(persegi 15 × 15 cm, L = 2 cm, h = 6 cm, Q = 1.125 cm³/detik), "
            "sehingga tab ini mereproduksi Hasil Uji. "
            "Nonaktif: mode perhitungan bebas untuk benda uji Anda sendiri."
        ),
    )
    if mode_acuan:
        komp_catatan.acuan(
            st,
            "**Konfigurasi Acuan Penelitian** — benda uji persegi 15 × 15 cm "
            "(A = 225 cm²), L = 2 cm, h = 6 cm. Hasil Uji."
        )
    else:
        st.info("**Mode perhitungan kustom** — masukkan geometri dan data Anda sendiri.")
    return mode_acuan


# ──────────────────────────── geometri ────────────────────────────

def _masukan_geometri(st, mode_acuan: bool) -> tuple[float, float, float]:
    """
    Geometri benda uji: luas penampang, tebal, dan tinggi tekan.

    Ketiga bentuk yang didukung `core/geometri.py` tetap tersedia. Bentuk
    bawaan pada mode acuan adalah PERSEGI PANJANG karena benda uji penelitian
    memang persegi 15 × 15 cm; alur kerja silinder lama tidak dihapus dan
    angkanya tidak berubah.
    """
    st.markdown("**Geometri Benda Uji**")
    pilihan = list(geometri.BENTUK_TERSEDIA.keys())
    bentuk = st.selectbox(
        "Bentuk benda uji",
        pilihan,
        index=pilihan.index(
            geometri.PERSEGI_PANJANG if mode_acuan else geometri.LINGKARAN
        ),
        disabled=mode_acuan,
        format_func=lambda b: geometri.BENTUK_TERSEDIA[b],
        help=(
            "Nilai bawaan mengikuti benda uji penelitian ini: persegi 15 × 15 cm. "
            "Alur kerja silinder lama tetap tersedia dan perilakunya tidak berubah."
        ),
    )

    if bentuk == geometri.LINGKARAN:
        diam_mm = st.number_input(
            "Diameter benda uji (mm)", 50.0, 300.0, BAWAAN_DIAMETER_MM,
            help=("Garis tengah benda uji berbentuk lingkaran, dalam "
                  "milimeter (50 sampai 300 mm)."),
        )
        luas_cm2 = geometri.luas_penampang(
            geometri.LINGKARAN, diameter_cm=diam_mm / 10.0
        )
    elif bentuk == geometri.PERSEGI_PANJANG:
        g1, g2 = st.columns(2)
        with g1:
            lebar_cm = st.number_input(
                "Lebar (cm)", 1.0, 100.0, ACUAN_LEBAR_CM, disabled=mode_acuan,
                help="Lebar bidang benda uji yang dilalui air, dalam sentimeter.",
            )
        with g2:
            panjang_cm = st.number_input(
                "Panjang (cm)", 1.0, 100.0, ACUAN_PANJANG_CM, disabled=mode_acuan,
                help="Panjang bidang benda uji yang dilalui air, dalam sentimeter.",
            )
        luas_cm2 = geometri.luas_penampang(
            geometri.PERSEGI_PANJANG, lebar_cm=lebar_cm, panjang_cm=panjang_cm
        )
    else:
        luas_cm2 = geometri.luas_penampang(
            geometri.LANGSUNG,
            luas_cm2=st.number_input(
                "Luas penampang A (cm²)", 1.0, 5000.0, perm.LAB_LUAS_CM2,
                help=("Luas bidang benda uji yang dilalui air, dalam "
                      "sentimeter persegi."),
            ),
        )

    tebal_cm = st.number_input(
        "Tebal benda uji L (cm)", 0.5, 50.0, ACUAN_TEBAL_CM, disabled=mode_acuan,
        help="Tebal benda uji yang harus ditembus air, dalam sentimeter.",
    )
    tinggi_tekan_cm = st.number_input(
        "Tinggi tekan tetap h (cm)", 1.0, 100.0, ACUAN_TINGGI_TEKAN_CM,
        disabled=mode_acuan,
        help=("Selisih tinggi muka air yang mendorong air menembus benda "
              "uji, dijaga tetap selama pengujian, dalam sentimeter."),
    )
    return luas_cm2, tebal_cm, tinggi_tekan_cm


# ───────────────────────── data pengujian ─────────────────────────

def _masukan_pengujian(
    st, tebal_cm: float, luas_cm2: float, tinggi_tekan_cm: float
) -> tuple[list[float], list[dict]]:
    """
    Data pengujian dalam salah satu dari dua bentuk yang setara secara aljabar.

    Pembagi waktu HANYA ada pada bentuk volume. Pada bentuk debit, waktu sudah
    terkandung di dalam Q dan tidak boleh dibagikan lagi — lihat catatan modul
    `core/permeabilitas.py`.
    """
    st.markdown("**Data Pengujian**")
    modus = st.radio(
        "Bentuk masukan",
        [MODUS_DEBIT, MODUS_VOLUME],
        help=(
            "Keduanya identik secara aljabar. Bila Q dimasukkan sebagai debit "
            "(cm³/detik), waktu sudah terkandung di dalamnya dan tidak dibagikan lagi."
        ),
    )

    n_uji = int(st.number_input(
        "Jumlah pengujian", 1, 10, 1,
        help="Berapa kali pengujian diulang (1 sampai 10)."))
    nilai_k: list[float] = []
    baris: list[dict] = []
    for i in range(n_uji):
        ca, cb = st.columns(2)
        if modus.startswith("Volume"):
            with ca:
                V = st.number_input(
                    f"V{i+1} (cm³)", 0.1, 1_000_000.0,
                    ACUAN_DEBIT_CM3_PER_DETIK, key=f"V{i}",
                    help=("Volume air yang tertampung selama pengujian, "
                          "dalam sentimeter kubik."),
                )
            with cb:
                t = st.number_input(
                    f"t{i+1} (detik)", 0.1, 3600.0, 1.0, key=f"t{i}",
                    help="Lama penampungan air, dalam detik.")
            k_i = perm.koefisien_dari_volume(V, tebal_cm, luas_cm2, tinggi_tekan_cm, t)
            baris.append({"Pengujian": f"Uji {i+1}", "V (cm³)": V, "t (dtk)": t,
                          "k (cm/dtk)": round(k_i, 4)})
        else:
            with ca:
                Q = st.number_input(
                    f"Q{i+1} (cm³/detik)", 0.1, 100_000.0,
                    ACUAN_DEBIT_CM3_PER_DETIK, key=f"Q{i}",
                    help=("Debit: volume air yang lewat tiap detik, dalam "
                          "sentimeter kubik per detik."),
                )
            with cb:
                st.caption("Waktu sudah terkandung di dalam debit.")
            k_i = perm.koefisien_dari_debit(Q, tebal_cm, luas_cm2, tinggi_tekan_cm)
            baris.append({"Pengujian": f"Uji {i+1}", "Q (cm³/dtk)": Q,
                          "k (cm/dtk)": round(k_i, 4)})
        nilai_k.append(k_i)
    return nilai_k, baris


# ─────────────────────────── hasil ───────────────────────────

def _panel_hasil(
    st,
    nilai_k: list[float],
    baris: list[dict],
    luas_cm2: float,
    tebal_cm: float,
    tinggi_tekan_cm: float,
) -> None:
    """Ringkasan hitungan pengguna, lalu pembanding pustaka dan hasil lab."""
    ringkas = perm.ringkasan(nilai_k)
    i_grad = perm.gradien_hidraulik(tinggi_tekan_cm, tebal_cm)

    st.markdown(
        f"**Luas penampang terhitung:** {luas_cm2:.2f} cm²  ·  "
        f"**gradien hidraulik i = h/L:** {i_grad:.2f}"
    )
    st.dataframe(pd.DataFrame(baris), width="stretch", hide_index=True)

    komp_bukti.kotak_hasil(
        st, f"{ringkas['rerata']:.4f} cm/dtk",
        f"Koefisien permeabilitas rerata (n = {ringkas['n']})",
        f"simpangan baku ±{ringkas['simpangan_baku']:.4f} · "
        f"CV {ringkas['cv_persen']:.1f}%",
        rata_tengah=True,
    )

    st.caption(
        "Tidak ada badge lulus/gagal di sini. Ambang 0,45 cm/dtk dan target "
        "0,60 cm/dtk yang dipakai versi sebelumnya tidak ada di Hasil Uji "
        "dan telah dihapus (ADR-001). Yang ditampilkan di bawah adalah "
        "pembanding dari pustaka yang benar-benar disitir."
    )

    _grafik_pembanding(st, ringkas["rerata"])


def _grafik_pembanding(st, rerata_pengguna: float) -> None:
    """
    Hitungan pengguna disandingkan dengan pustaka dan hasil laboratorium.

    Ketiganya sengaja diberi batang terpisah dan berwarna berbeda: nilai
    pustaka, hasil lab penelitian, dan hitungan pengguna bukan hal yang sama,
    dan provenansi masing-masing tetap dapat dibuka di bawah grafik.
    """
    pembanding = perm.pembanding_literatur()
    hasil_lab = akses.besaran("PERMEABILITAS")

    label = [q["nama"] for q in pembanding] + ["Hasil lab penelitian", "Campuran Anda"]
    nilai = [q["nilai"] for q in pembanding] + [hasil_lab.nilai, rerata_pengguna]

    fig = go.Figure(go.Bar(
        x=label, y=nilai,
        marker_color=["#90A4AE", "#90A4AE", "#90A4AE", "#00897B", "#1565C0"],
        text=[f"{v:.3f}" for v in nilai], textposition="outside",
    ))
    fig.update_layout(
        title="Perbandingan koefisien permeabilitas (cm/dtk)",
        height=340, yaxis_title="k (cm/dtk)", margin=dict(t=44, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")

    with st.expander("Sumber pembanding dan hasil laboratorium"):
        for q in pembanding:
            st.markdown(
                f"- **{q['nama']}** — {q['nilai']} {q['satuan']} "
                f"({q['sifat']}). {q['sumber']}"
            )
        st.markdown(f"- **Hasil lab penelitian** — {hasil_lab.provenans()}")
