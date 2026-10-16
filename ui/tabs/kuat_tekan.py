"""
Tab Kuat Tekan — SNI 1974:2011.

PENYAJIAN SAJA. Luas silinder, f'c = P/A, dan ringkasan statistiknya seluruhnya
dipanggil dari `core/kuat_tekan.py`. Data uji dan umur pengujiannya berasal
dari `data/akses.py`. Ketersediaan hasil untuk skenario aktif berasal dari
`scenario/resolusi.py` — tab ini tidak memutuskannya sendiri.

TIGA HAL YANG SENGAJA DIPISAH
-----------------------------
1. **Hasil skenario aktif.** Diselesaikan lapisan skenario. Untuk konfigurasi
   yang benar-benar diuji: 13,19 MPa, terukur, umur 7 hari. Untuk komposisi
   lain: belum tersedia — dan tidak ada prediksi yang menggantikannya.

2. **Data eksperimen konfigurasi acuan.** Ketiga benda uji penelitian apa
   adanya, boleh diperiksa kapan pun, tetapi selalu berlabel milik konfigurasi
   acuan — bukan milik skenario yang sedang aktif. Kendalinya dapat dibuka
   untuk menghitung benda uji sendiri, dan begitu dibuka hasilnya berhenti
   disebut hasil penelitian.

3. **Estimasi konversi umur.** Sekunder, tersembunyi di panel terpisah, dan
   berstatus estimasi. Tidak pernah menimpa nilai terukur.

UMUR PENGUJIAN BUKAN UMUR TARGET
--------------------------------
Umur eksperimen adalah FAKTA yang tercatat: 7 hari (OUTPUT3 §4.2, lewat
`akses.besaran("UMUR_UJI_HARI")`). Ia tidak berasal dari kendali antarmuka dan
tidak dapat digeser pengguna.

Yang dapat dipilih pengguna hanyalah umur TARGET estimasi, dan umur eksperimen
sengaja tidak termasuk pilihannya: untuk umur itu sudah ada hasil pengukuran,
sehingga mengestimasinya hanya akan menghasilkan angka yang bersaing dengan
pengukuran yang sudah ada.

FAKTOR UMUR TETAP DI LAPISAN TAMPILAN
-------------------------------------
`core/kuat_tekan.py` sengaja TIDAK menyediakan fungsi konversi umur (ADR-005):
provenansi primer tabel faktornya belum tertelusuri, dan keberlakuan faktor
beton biasa pada campuran tanpa pasir bersubstitusi 15% belum diverifikasi.
Memindahkannya ke core/ akan mengubah alat bantu pembaca menjadi model.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core import kuat_tekan as ktk
from data import akses
from scenario.keluaran import Keluaran

from .. import gaya
from ..components import evidence as komp_bukti
from ..components import provenance as komp_provenans
from ..components import warnings as komp_catatan

#: Tabel faktor umur — ALAT BANTU, bukan model.
#: Provenansi primer belum tertelusuri (ADR-005). Lihat catatan modul.
FAKTOR_UMUR = {7: 0.65, 14: 0.879, 21: 0.95, 28: 1.00, 56: 1.09, 90: 1.15}

#: Status bukti tabel faktor umur, ikut ke mana pun tabelnya digambar.
#:
#: SD-16B. Judul tabel ini dahulu berbunyi "Faktor Konversi Umur (SNI)".
#: Tidak ada satu pun catatan proyek yang menautkannya ke SNI mana pun:
#: `konstanta.FAKTOR_KONVERSI_7_KE_14` berstatus ASUMSI dengan catatan
#: "naskah tidak menyitir sumber mana pun", dan docstring modul ini sendiri
#: menyatakan provenansi primernya belum tertelusuri.
#:
#: PBI 1971 juga TIDAK dipasang sebagai gantinya. ADR-005 mencatatnya sebagai
#: KEMIRIPAN angka, bukan sitasi — naskah tidak menyebut PBI di mana pun.
#: Mengganti satu atribusi tak berdasar dengan atribusi tak berdasar lain
#: bukan perbaikan. Yang benar: tidak menyebut sumber, dan menyatakan status.
CATATAN_FAKTOR_UMUR = (
    "Status bukti: **asumsi** — provenansi primer tabel ini **belum "
    "tertelusuri**. Tidak ada standar yang tercatat sebagai sumbernya di "
    "dalam penelitian ini. Nilainya menyerupai tabel PBI 1971 yang banyak "
    "direproduksi, tetapi Hasil Uji tidak menyitirnya (ADR-005). Tabel ini alat "
    "bantu pembaca, bukan model: keluarannya estimasi, bukan hasil pengukuran."
)

BAWAAN_DIAMETER_MM = ktk.LAB_DIAMETER_MM
BAWAAN_JUMLAH_BENDA_UJI = 3

#: Nilai bawaan bila pengguna menambah benda uji melebihi data penelitian.
BEBAN_TAMBAHAN_KN = 230.0
BERAT_TAMBAHAN_KG = 6.5

PESAN_TANPA_PREDIKSI = (
    "AQUAPAVE tidak memprediksi kuat tekan dari komposisi. Penelitian menguji "
    "satu campuran dengan tiga benda uji, sehingga tidak ada dasar untuk "
    "menghubungkan tingkat substitusi ke kuat tekan."
)


def umur_uji_hari() -> int:
    """
    Umur pengujian eksperimen, dari sumber kanonik.

    Bukan dari kendali antarmuka: ini fakta yang tercatat, bukan pilihan.
    """
    return int(akses.nilai("UMUR_UJI_HARI"))


def umur_target_tersedia() -> list[int]:
    """
    Umur yang boleh dipilih sebagai TARGET estimasi.

    Umur eksperimen sengaja dikeluarkan: untuk umur itu sudah ada hasil
    pengukuran, sehingga estimasinya tidak diperlukan dan hanya akan
    menghasilkan angka yang bersaing dengan nilai terukur.
    """
    return [u for u in sorted(FAKTOR_UMUR) if u != umur_uji_hari()]


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Kuat tekan menyatakan seberapa besar beban yang sanggup ditahan beton "
    "sebelum hancur, dalam megapascal (MPa). Tab ini menghitungnya dari beban "
    "uji dan ukuran benda uji silinder."
)


def render(st, kuat_tekan_aktif: Keluaran, target_fc_mpa: float) -> None:
    """
    Gambar seluruh tab Kuat Tekan.

    `kuat_tekan_aktif` — keluaran kuat tekan untuk skenario yang sedang aktif,
    hasil `scenario/resolusi.py`. Objek yang SAMA dengan yang mengisi kolom
    skenario aktif pada tabel perbandingan, dilewatkan mengikuti pola hasil
    bersama ADR-008. Karena tab dan tabel membaca satu objek, keduanya
    mustahil menyatakan hal yang berbeda tentang konfigurasi yang sama.

    `target_fc_mpa` — kelas kuat tekan target dari bilah sisi, dipakai hanya
    sebagai garis acuan pada grafik. Bukan hasil pengukuran, dan tidak pernah
    dipakai sebagai vonis atas hasil utama.
    """
    gaya.judul_bagian(st, "Kuat Tekan Beton — SNI 1974:2011")
    gaya.pengantar(st, PENGANTAR)
    st.caption(
        "Hitung f'c dari beban uji silinder memakai core/kuat_tekan.py. Hasil utama "
        "penelitian adalah 13,19 MPa pada umur 7 hari, terukur langsung tanpa konversi."
    )

    _hasil_skenario_aktif(st, kuat_tekan_aktif)
    st.divider()

    t1, t2 = st.columns(2)
    with t1:
        pakai_data_penelitian, diameter_mm, beban_kn, berat_kg = _masukan_pengujian(st)
    with t2:
        fc_rerata = _panel_data_uji(
            st, pakai_data_penelitian, diameter_mm, beban_kn, berat_kg
        )
        _panel_estimasi_umur(st, fc_rerata, pakai_data_penelitian)
        _grafik_perkembangan(st, fc_rerata, target_fc_mpa)
        _tabel_faktor_umur(st)


# ═══════════════ 1. hasil skenario aktif ═══════════════

def _hasil_skenario_aktif(st, k: Keluaran) -> None:
    """
    Kuat tekan skenario yang sedang aktif.

    Ketersediaannya TIDAK diputuskan di sini. Ia datang sudah selesai dari
    `scenario/resolusi.py`, lapisan yang sama yang mengisi tabel perbandingan.
    Tab ini hanya menggambar jawabannya (ADR-010).
    """
    st.markdown("**Hasil Skenario Aktif**")

    if not k.tersedia:
        komp_catatan.tidak_tersedia(st, k)
        st.caption(PESAN_TANPA_PREDIKSI)
        return

    umur = umur_uji_hari()
    ambang = ktk.ambang_lalu_lintas_ringan()
    lencana = komp_bukti.lencana_ambang(
        f"Di atas ambang {ambang['nilai']:.0f} MPa untuk lalu lintas ringan",
        f"Di bawah ambang {ambang['nilai']:.0f} MPa untuk lalu lintas ringan",
        k.nilai >= ambang["nilai"],
    )
    komp_bukti.kotak_hasil(
        st, f"{k.nilai:.2f} {k.satuan}",
        f"Kuat tekan skenario aktif — {k.status_bukti.value} pada umur "
        f"{umur} hari",
        "HASIL UTAMA — pengukuran langsung, tanpa konversi umur",
        lencana_html=lencana, rata_tengah=True,
    )
    komp_provenans.keterangan(st, akses.besaran("KUAT_TEKAN_7_HARI"))
    st.caption(f"Ambang perbandingan: {ambang['sumber']}.")


# ═══════════════ 2. data eksperimen konfigurasi acuan ═══════════════

def _bawaan_benda_uji(indeks: int) -> tuple[float, float]:
    """
    Beban dan berat bawaan benda uji ke-`indeks`, dari data uji kanonik
    (OUTPUT3 Tabel 4.1) lewat data/akses.py.
    """
    dataset = akses.dataset_kuat_tekan()
    if indeks < len(dataset):
        b = dataset[indeks]
        return float(b["beban_kN"]), float(b["berat_kg"])
    return BEBAN_TAMBAHAN_KN, BERAT_TAMBAHAN_KG


def _masukan_pengujian(st) -> tuple[bool, float, list[float], list[float]]:
    """
    Geometri silinder dan beban tiap benda uji.

    Pada mode data penelitian seluruh kendali dikunci, sehingga bagian ini
    benar-benar mereproduksi OUTPUT3 Tabel 4.1. Membukanya mengubah bagian ini
    menjadi kalkulator, dan hasilnya berhenti disebut hasil penelitian.
    """
    st.markdown("**Data Eksperimen Konfigurasi Acuan**")
    pakai_data_penelitian = st.toggle(
        "Pakai data uji penelitian",
        value=True,
        help=(
            "Aktif: ketiga benda uji penelitian apa adanya (Hasil Uji), "
            "silinder Ø150 mm, umur 7 hari. "
            "Nonaktif: kalkulator bebas untuk benda uji Anda sendiri — hasilnya "
            "adalah hitungan Anda, bukan hasil pengukuran penelitian."
        ),
    )
    st.caption(
        f"Diuji pada umur {umur_uji_hari()} hari "
        f"({akses.besaran('UMUR_UJI_HARI').sumber}). Umur ini fakta yang "
        "tercatat, bukan pilihan antarmuka."
    )

    diameter_mm = st.number_input(
        "Diameter Silinder (mm)", 100.0, 200.0, BAWAAN_DIAMETER_MM,
        disabled=pakai_data_penelitian,
        help=("Garis tengah benda uji berbentuk silinder, dalam milimeter "
              "(100 sampai 200 mm). Dipakai untuk menghitung luas bidang "
              "yang ditekan."),
    )
    n_benda = st.number_input(
        "Jumlah Benda Uji", 1, 10, BAWAAN_JUMLAH_BENDA_UJI,
        disabled=pakai_data_penelitian,
        help=("Berapa silinder yang diuji (1 sampai 10). Kuat tekan "
              "dilaporkan sebagai rata-ratanya."),
    )

    beban_kn: list[float] = []
    berat_kg: list[float] = []
    for i in range(int(n_benda)):
        bawaan_p, bawaan_w = _bawaan_benda_uji(i)
        ca, cb = st.columns(2)
        with ca:
            beban_kn.append(st.number_input(
                f"Beban P{i+1} (kN)", 0.0, 2000.0, bawaan_p, key=f"P{i}",
                disabled=pakai_data_penelitian,
                help=("Beban tekan terbesar yang ditahan benda uji sebelum "
                      "hancur, dalam kilonewton (kN)."),
            ))
        with cb:
            berat_kg.append(st.number_input(
                f"Berat W{i+1} (kg)", 0.0, 30.0, bawaan_w, key=f"W{i}",
                disabled=pakai_data_penelitian,
                help="Berat benda uji, dalam kilogram.",
            ))
    return pakai_data_penelitian, diameter_mm, beban_kn, berat_kg


def _panel_data_uji(
    st, pakai_data_penelitian: bool, diameter_mm: float,
    beban_kn: list[float], berat_kg: list[float],
) -> float:
    """
    Tabel per benda uji dan reratanya. Mengembalikan reratanya.

    Seluruh angkanya berasal dari core/kuat_tekan.py; tidak ada rumus di sini.
    """
    luas_m2 = ktk.luas_silinder_m2(diameter_mm)
    umur = umur_uji_hari()

    fc_list: list[float] = []
    baris: list[dict] = []
    for i, P in enumerate(beban_kn):
        fc = ktk.kuat_tekan_mpa(P, luas_m2)
        fc_list.append(fc)
        baris.append({
            "Benda Uji":              f"BU-{i+1}",
            "Berat (kg)":             berat_kg[i],
            "Beban (kN)":             P,
            f"f'c @ {umur} hari (MPa)": round(fc, 2),
            "Luas (m²)":              round(luas_m2, 6),
        })

    ring = ktk.ringkasan(fc_list)
    st.dataframe(pd.DataFrame(baris), width="stretch", hide_index=True)

    if pakai_data_penelitian:
        label = (
            f"Rerata f'c tiga benda uji penelitian — umur {umur} hari, "
            f"simpangan baku ±{ring['simpangan_baku']:.2f} MPa &nbsp;·&nbsp; "
            f"CV {ring['cv_persen']:.1f}%"
        )
        keterangan = "DATA KONFIGURASI ACUAN — Hasil Uji"
    else:
        label = (
            f"Rerata f'c dari beban yang Anda masukkan — simpangan baku "
            f"±{ring['simpangan_baku']:.2f} MPa &nbsp;·&nbsp; "
            f"CV {ring['cv_persen']:.1f}%"
        )
        keterangan = "HITUNGAN ANDA — bukan hasil pengukuran penelitian"

    komp_bukti.kotak_hasil(
        st, f"{ring['rerata']:.2f} MPa", label, keterangan, rata_tengah=True
    )
    if pakai_data_penelitian:
        st.caption(
            "Data ini milik **konfigurasi acuan penelitian**, bukan milik "
            "skenario yang sedang aktif. Ketersediaannya untuk skenario aktif "
            "dinyatakan di bagian atas tab."
        )
    else:
        st.caption(
            "Beban yang Anda masukkan bukan data penelitian. Hasilnya adalah "
            "hitungan deterministik atas masukan Anda sendiri."
        )
    return ring["rerata"]


# ═══════════════ 3. estimasi konversi umur ═══════════════

def _panel_estimasi_umur(st, fc_rerata: float, pakai_data_penelitian: bool) -> None:
    """
    Estimasi kuat tekan pada umur TARGET — sekunder dan tersembunyi.

    Titik tolaknya selalu nilai pada umur eksperimen yang tercatat, lalu
    diskalakan ke umur target memakai tabel faktor. Umur eksperimen tidak ada
    di daftar target: untuk umur itu sudah ada pengukuran.
    """
    umur = umur_uji_hari()
    with st.expander("Estimasi konversi umur — bukan hasil pengukuran"):
        komp_catatan.keterbatasan(
            st,
            "Provenansi primer faktor umur di bawah **belum tertelusuri**. "
            "Nilainya menyerupai tabel PBI 1971 yang banyak direproduksi, "
            "tetapi Hasil Uji ini tidak menyitirnya. Keluaran di sini "
            "adalah ESTIMASI dan tidak boleh dilaporkan sebagai hasil "
            "pengukuran (ADR-005)."
        )
        st.caption(
            f"Umur {umur} hari tidak ada di daftar target: untuk umur itu sudah "
            "ada hasil pengukuran, sehingga estimasinya tidak diperlukan."
        )

        target = st.selectbox(
            "Target umur estimasi (hari)", umur_target_tersedia(),
            help=(
                "Umur yang ingin diestimasi. Umur EKSPERIMEN tidak dapat "
                "diubah di sini — ia fakta yang tercatat, bukan pilihan."
            ),
        )
        estimasi = fc_rerata / FAKTOR_UMUR[umur] * FAKTOR_UMUR[target]
        asal = (
            "rerata terukur konfigurasi acuan" if pakai_data_penelitian
            else "rerata hitungan Anda"
        )
        st.markdown(
            f"Dari {asal} {fc_rerata:.2f} MPa pada umur {umur} hari, dengan "
            f"faktor {FAKTOR_UMUR[umur]} → {FAKTOR_UMUR[target]}, diperoleh "
            f"estimasi umur {target} hari sebesar **{estimasi:.2f} MPa** "
            "(ESTIMASI)."
        )
        st.caption(
            "Estimasi ini tidak dipakai di mana pun sebagai hasil, dan tidak "
            "menimpa nilai terukur di atas."
        )

        _catatan_estimasi_naskah(st)


def _catatan_estimasi_naskah(st) -> None:
    """
    Angka konversi yang tercatat di naskah, disandingkan apa adanya.

    Naskah mencatat 15,00 MPa pada umur 14 hari, sementara penskalaan dengan
    tabel faktor yang sama dari umur 7 hari memberi angka yang berbeda.
    Selisih itu sendiri adalah bukti bahwa provenansi faktornya belum
    terselesaikan, sehingga ditampilkan dan tidak disembunyikan.
    """
    b14 = akses.besaran("KUAT_TEKAN_14_HARI")
    umur = umur_uji_hari()
    umur_naskah = int(akses.nilai("UMUR_KONVERSI_HARI"))
    dari_tabel = (
        akses.nilai("KUAT_TEKAN_7_HARI")
        / FAKTOR_UMUR[umur] * FAKTOR_UMUR[umur_naskah]
    )
    st.caption(
        f"Catatan: Hasil Uji mencatat {b14.nilai:.2f} MPa pada umur "
        f"{umur_naskah} hari ({b14.label_status}), sementara penskalaan nilai "
        f"kanonik {akses.nilai('KUAT_TEKAN_7_HARI'):.2f} MPa dengan tabel "
        f"faktor yang sama memberi {dari_tabel:.2f} MPa. Selisih ini belum "
        "terselesaikan dan menjadi alasan tambahan mengapa faktor umur tidak "
        "dipakai sebagai jalur hasil."
    )


def _grafik_perkembangan(st, fc_rerata: float, target_fc_mpa: float) -> None:
    """
    Kurva perkembangan kuat tekan terhadap umur.

    Seluruh kurva ini ESTIMASI: ia dibentuk dengan menskalakan satu nilai
    memakai tabel faktor yang sama. Penelitian hanya menguji satu umur,
    sehingga tidak ada titik ukur kedua yang dapat mendukungnya.
    """
    umur = umur_uji_hari()
    umur_plot = sorted(FAKTOR_UMUR)
    fc_prog = [fc_rerata / FAKTOR_UMUR[umur] * FAKTOR_UMUR[u] for u in umur_plot]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=umur_plot, y=fc_prog, mode="lines+markers",
        name="Campuran Anda", line=dict(color="#1565C0", width=3),
        marker=dict(size=8, color="#1565C0"),
    ))
    fig.add_trace(go.Scatter(
        x=[umur], y=[fc_rerata], mode="markers",
        name=f"Terukur ({umur} hari)",
        marker=dict(size=14, color="#00897B", symbol="diamond"),
    ))
    fig.add_hline(
        y=target_fc_mpa, line_dash="dash", line_color="#E65100",
        annotation_text=f"Target f'c = {target_fc_mpa} MPa",
    )
    fig.update_layout(
        title="Perkembangan Kuat Tekan terhadap Umur (estimasi)",
        height=300, xaxis_title="Umur (hari)", yaxis_title="f'c (MPa)",
        margin=dict(t=40, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Hanya titik umur {umur} hari yang terukur; sisanya estimasi dari "
        "tabel faktor yang provenansinya belum tertelusuri."
    )


def _tabel_faktor_umur(st) -> None:
    """
    Tabel faktor umur apa adanya, agar angkanya dapat diperiksa pembaca.

    Tabel ini digambar di kolom utama, DI LUAR panel estimasi yang terlipat,
    sehingga peringatan di dalam panel itu tidak menemaninya. Karena itu
    statusnya dinyatakan di sini juga: provenans ikut ke mana pun angkanya
    tampil (ADR-011), bukan hanya di tempat yang kebetulan sedang terbuka.
    """
    st.markdown("**Faktor Konversi Umur**")
    st.dataframe(
        pd.DataFrame({
            "Umur (hari)":     list(FAKTOR_UMUR.keys()),
            "Faktor Konversi": list(FAKTOR_UMUR.values()),
        }),
        width="stretch", hide_index=True,
    )
    st.caption(CATATAN_FAKTOR_UMUR)
