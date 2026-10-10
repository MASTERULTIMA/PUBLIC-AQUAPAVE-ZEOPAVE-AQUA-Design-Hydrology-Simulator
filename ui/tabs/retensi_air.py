"""
Tab Retensi Air — simulator hidrologi skala area.

PENYAJIAN SAJA. Volume hujan, air tertahan, limpasan, dan reduksinya
seluruhnya dipanggil dari `core/hidrologi.py`. Ketersediaan retensi terukur
untuk skenario aktif berasal dari `scenario/resolusi.py` — tab ini tidak
memutuskannya sendiri (ADR-010).

DUA HAL YANG SANGAT MUDAH TERTUKAR
----------------------------------
1. **Retensi terukur.** 40,0% adalah hasil laboratorium milik konfigurasi yang
   benar-benar diuji (OUTPUT3 Tabel 4.3, terkoreksi). Ia melekat pada
   komposisi itu, bukan pada aplikasi.

2. **Retensi sebagai asumsi model.** Angka yang dimasukkan pengguna untuk
   menjelajah skenario. Ia sah sebagai alat bantu, tetapi bukan pengukuran,
   dan tidak boleh mewarisi sumber maupun status bukti hasil laboratorium.

Sebelum perbaikan ini keduanya tertukar: penggeser retensi selalu terisi
40,0% apa pun skenario yang aktif, sehingga komposisi yang tidak pernah
dicetak pun langsung menghasilkan angka hidrologi yang persis sama dengan
konfigurasi penelitian — pada saat yang sama tabel perbandingan menyatakan
retensinya belum tersedia.

Sekarang: bila retensi terukur tidak tersedia untuk skenario aktif, tidak ada
angka yang diwariskan. Pengguna harus menyatakan asumsinya sendiri secara
sadar, dan seluruh keluaran yang mengikutinya berlabel asumsi.

TIDAK ADA MODEL KOMPOSISI -> RETENSI
------------------------------------
Penelitian menguji satu campuran dengan tiga pengujian retensi. Tidak ada
dasar untuk menghubungkan tingkat substitusi ke tingkat retensi, dan modul ini
tidak boleh menciptakannya.
"""

from __future__ import annotations

import plotly.graph_objects as go

from core import hidrologi
from data import akses
from scenario.keluaran import Keluaran

from .. import gaya
from ..components import evidence as komp_bukti
from ..components import provenance as komp_provenans
from ..components import warnings as komp_catatan

#: Rentang penggeser retensi. Rentang antarmuka, bukan rentang bersumber.
RETENSI_MIN_PERSEN = 20.0
RETENSI_MAKS_PERSEN = 60.0

#: Nilai awal ketika pengguna menyatakan asumsinya sendiri untuk komposisi yang
#: belum diuji. Sengaja BUKAN nilai terukur: mengisinya dengan 40,0% akan
#: menyelundupkan hasil laboratorium kembali sebagai titik awal. Batas bawah
#: dipilih sebagai nilai paling konservatif.
RETENSI_AWAL_ASUMSI = RETENSI_MIN_PERSEN

TOLERANSI_PERSEN = 1e-9

PESAN_TANPA_PREDIKSI = (
    "AQUAPAVE tidak memprediksi tingkat retensi dari komposisi. Penelitian "
    "menguji satu campuran dengan tiga pengujian retensi, sehingga tidak ada "
    "dasar untuk menghubungkan tingkat substitusi ke tingkat retensi."
)

PESAN_HIDROLOGI_TERTAHAN = (
    "Perhitungan hidrologi membutuhkan tingkat retensi. Untuk komposisi ini "
    "retensi belum diukur, dan tidak ada nilai yang diwariskan dari "
    "konfigurasi lain. Nyatakan asumsi Anda sendiri di sebelah kiri bila "
    "ingin tetap menjelajah skenarionya."
)


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Memperkirakan berapa banyak air hujan yang tertahan sistem dan berapa "
    "yang masih melimpas, untuk luas area dan hujan tertentu. Versi "
    "terpandunya ada di tab Mulai di Sini; di sini kendalinya lebih lengkap."
)


def render(
    st,
    retensi_aktif: Keluaran,
    luas_area_m2: float,
    intensitas_hujan_mm_per_jam: float,
) -> None:
    """
    Gambar seluruh tab Retensi Air.

    `retensi_aktif` — keluaran retensi untuk skenario yang sedang aktif, hasil
    `scenario/resolusi.py`. Objek yang SAMA dengan yang mengisi tabel
    perbandingan (ADR-008, ADR-010), sehingga tab dan tabel mustahil berbeda.

    `luas_area_m2` dan `intensitas_hujan_mm_per_jam` — parameter lokasi dari
    bilah sisi. Dilewatkan sebagai skalar eksplisit, bukan lewat objek
    skenario: keduanya memang satu-satunya bagian skenario yang dipakai tab
    ini, dan mengubahnya tidak membatalkan hasil laboratorium (ADR-009).
    """
    gaya.judul_bagian(st, "Simulator Sistem Retensi Air — ZEOPAVE-AQUA")
    gaya.pengantar(st, PENGANTAR)
    st.caption(
        "Simulasikan kemampuan ZEOPAVE-AQUA dalam mengurangi limpasan permukaan "
        "dan menyimpan air hujan untuk lokasi Anda."
    )

    _retensi_skenario_aktif(st, retensi_aktif)
    st.divider()

    r1, r2 = st.columns(2)
    with r1:
        retensi_persen, berstatus_terukur, durasi_jam, koef_limpasan = (
            _masukan_lokasi(st, retensi_aktif)
        )
    with r2:
        hidro = _panel_hidrologi(
            st, retensi_persen, berstatus_terukur,
            luas_area_m2, intensitas_hujan_mm_per_jam, durasi_jam, koef_limpasan,
        )

    st.divider()
    komp_catatan.asumsi(
        st,
        "Grafik *retensi terhadap intensitas hujan* dihapus. Kemiringan "
        "−0,08 %/(mm/jam) yang dipakai sebelumnya tidak bersumber, dan satu "
        "titik pengujian pada satu intensitas tidak dapat mendukung sebuah "
        "kemiringan. Pengujian pada beberapa intensitas diperlukan (Saran 9)."
    )
    _diagram_aliran(st, hidro)


# ═══════════ 1. retensi skenario aktif ═══════════

def _retensi_skenario_aktif(st, k: Keluaran) -> None:
    """
    Retensi untuk skenario yang sedang aktif.

    Ketersediaannya datang sudah selesai dari lapisan skenario. Tab ini hanya
    menggambar jawabannya.
    """
    st.markdown("**Retensi Skenario Aktif**")

    if not k.tersedia:
        komp_catatan.tidak_tersedia(st, k)
        st.caption(PESAN_TANPA_PREDIKSI)
        return

    komp_bukti.kotak_hasil(
        st, f"{k.nilai:.1f} {k.satuan}",
        f"Tingkat retensi skenario aktif — {k.status_bukti.value}",
        "HASIL UKUR KONFIGURASI ACUAN — rerata tiga pengujian",
        rata_tengah=True,
    )
    komp_provenans.keterangan(st, akses.besaran("RETENSI_RERATA"))


# ═══════════ 2. masukan lokasi dan basis retensi ═══════════

def _masukan_lokasi(st, k: Keluaran) -> tuple[float | None, bool, float, float]:
    """
    Parameter lokasi dan basis tingkat retensi.

    Mengembalikan `(retensi_persen, berstatus_terukur, durasi_jam,
    koef_limpasan)`. `retensi_persen` bernilai None bila retensi terukur tidak
    tersedia dan pengguna belum menyatakan asumsinya — keadaan itulah yang
    membuat seluruh keluaran hidrologi ikut tidak tersedia.
    """
    st.markdown("**Parameter Lokasi**")

    retensi_persen, berstatus_terukur = _basis_retensi(st, k)

    # SD-07 ditutup (keputusan penulis): kendali "Kedalaman Struktural
    # Perkerasan" (bawaan 300 mm) dan "Tebal Lapisan Hebel–Zeolit" (bawaan
    # 150 mm) DIHAPUS. Keduanya tidak pernah memengaruhi satu angka pun —
    # core/hidrologi.skenario() tidak menerima parameter tebal sama sekali —
    # dan bawaannya tidak punya sumber di dalam penelitian.
    #
    # Kendali itu sisa dari perhitungan kapasitas simpan (luas × tebal × 0,25)
    # yang dihapus karena koefisiennya tidak bersumber. Penghapusan ini
    # membuang antarmuka mati, BUKAN mengubah model hidrologi: tebal tidak
    # pernah menjadi masukannya. Tebal sistem terpasang yang dikonfirmasi
    # penulis hidup di ui/tabs/biaya.py dan tidak dipindahkan ke sini.

    koef_limpasan = st.slider(
        "Koefisien Limpasan Sebelum ZEOPAVE (C)", 0.5, 0.95, 0.85,
        help="Perkotaan kedap air tipikal: 0,85–0,95",
    )
    durasi_jam = st.number_input(
        "Durasi Hujan (jam)", 0.25, 24.0, 1.0, 0.25,
        help="Berapa lama hujan berlangsung, dalam jam (0,25 sampai 24 jam).",
    )
    return retensi_persen, berstatus_terukur, durasi_jam, koef_limpasan


def _basis_retensi(st, k: Keluaran) -> tuple[float | None, bool]:
    """
    Dari mana angka retensi yang dipakai simulator berasal.

    Dua jalur yang sengaja tidak pernah bertemu:

    - retensi terukur TERSEDIA — penggeser berangkat dari nilai terukur, dan
      selama tidak digeser, keluarannya memang bertumpu pada hasil ukur;
    - retensi terukur TIDAK tersedia — tidak ada nilai yang diwariskan.
      Pengguna harus menyatakan asumsinya sendiri secara sadar lebih dulu.
    """
    if k.tersedia:
        nilai = st.slider(
            "Tingkat Retensi (%)", RETENSI_MIN_PERSEN, RETENSI_MAKS_PERSEN,
            float(k.nilai), 0.1, key="retensi_dari_ukur",
            help=(
                f"Berangkat dari hasil ukur konfigurasi acuan: {k.nilai:.1f}% "
                "(OUTPUT3 Tabel 4.3, terkoreksi). Menggesernya mengubah angka "
                "ini menjadi asumsi Anda sendiri."
            ),
        )
        terukur = abs(nilai - float(k.nilai)) <= TOLERANSI_PERSEN
        if terukur:
            st.caption(
                f"Memakai hasil ukur konfigurasi acuan: **{k.nilai:.1f}% · "
                f"{k.status_bukti.value}**."
            )
        else:
            st.caption(
                f"**{nilai:.1f}% · asumsi Anda** — bukan lagi hasil ukur. "
                f"Nilai terukur konfigurasi acuan tetap {k.nilai:.1f}%."
            )
        return nilai, terukur

    st.markdown("**Tingkat Retensi (%)**")
    st.caption(
        "Retensi belum diukur untuk komposisi ini, sehingga tidak ada nilai "
        "yang dipasang sebagai titik awal."
    )
    pakai_asumsi = st.checkbox(
        "Lanjutkan dengan asumsi retensi saya sendiri",
        value=False, key="retensi_pakai_asumsi",
        help=(
            "Angka yang Anda masukkan adalah ASUMSI untuk menjelajah skenario, "
            "bukan hasil pengukuran komposisi ini, dan tidak boleh dilaporkan "
            "sebagai temuan."
        ),
    )
    if not pakai_asumsi:
        return None, False

    nilai = st.slider(
        "Asumsi tingkat retensi (%)", RETENSI_MIN_PERSEN, RETENSI_MAKS_PERSEN,
        RETENSI_AWAL_ASUMSI, 0.1, key="retensi_asumsi_pengguna",
        help=("Persentase air hujan yang Anda andaikan tertahan sistem. "
              "Angka ini andaian Anda sendiri, bukan hasil pengukuran."),
    )
    komp_catatan.keterbatasan(
        st,
        f"**{nilai:.1f}% adalah asumsi Anda**, bukan hasil pengukuran. "
        "Komposisi ini belum pernah diuji retensinya, dan seluruh angka "
        "hidrologi di sebelah kanan mewarisi status asumsi itu."
    )
    return nilai, False


# ═══════════ 3. keluaran hidrologi ═══════════

def _panel_hidrologi(
    st, retensi_persen: float | None, berstatus_terukur: bool,
    luas_area_m2: float, intensitas_hujan_mm_per_jam: float,
    durasi_jam: float, koef_limpasan: float,
) -> dict | None:
    """
    Keluaran hidrologi skala area, atau None bila retensinya tidak diketahui.

    Ketidaktersediaan merambat: air tertahan diturunkan dari tingkat retensi,
    sehingga tanpa retensi tidak ada satu pun angka yang boleh muncul —
    bukan nol, bukan sel kosong (ADR-009).
    """
    st.markdown("**Hasil Analisis Hidrologi**")

    if retensi_persen is None:
        komp_catatan.keterbatasan(
            st, f"**Hasil hidrologi** — {komp_catatan.FRASA_TIDAK_TERSEDIA}"
        )
        st.caption(PESAN_HIDROLOGI_TERTAHAN)
        return None

    hidro = hidrologi.skenario(
        intensitas_hujan_mm_per_jam, luas_area_m2, durasi_jam, retensi_persen,
        koefisien_limpasan_konvensional=koef_limpasan,
    )
    dasar = (
        "MODEL — bertumpu pada retensi terukur konfigurasi acuan"
        if berstatus_terukur
        else "MODEL — bertumpu pada ASUMSI retensi yang Anda masukkan"
    )
    st.markdown(f"""
        <div class="result-box2">
          <table style="width:100%;border-collapse:collapse">
            <tr><td>Total Volume Hujan</td>
                <td style="text-align:right;font-weight:600">{hidro['volume_hujan_m3']:.1f} m³</td></tr>
            <tr><td>Limpasan Perkerasan Konvensional</td>
                <td style="text-align:right;font-weight:600;color:#C62828">{hidro['limpasan_konvensional_m3']:.1f} m³</td></tr>
            <tr><td>Limpasan ZEOPAVE-AQUA</td>
                <td style="text-align:right;font-weight:600;color:#1565C0">{hidro['limpasan_zeopave_m3']:.1f} m³</td></tr>
            <tr><td>Volume Air Tersimpan</td>
                <td style="text-align:right;font-weight:600;color:#388E3C">{hidro['air_tertahan_m3']:.1f} m³</td></tr>
            <tr><td>Reduksi Limpasan</td>
                <td style="text-align:right;font-weight:600;color:#00897B">{hidro['reduksi_limpasan_persen']:.1f}%</td></tr>
            <tr><td>Status bukti keluaran</td>
                <td style="text-align:right;font-weight:600">{dasar}</td></tr>
          </table>
        </div>
        """, unsafe_allow_html=True)
    st.caption(hidro["catatan"])
    return hidro


def _diagram_aliran(st, hidro: dict | None) -> None:
    """Sankey neraca air. Tidak digambar bila hidrologinya tidak tersedia."""
    st.markdown("**Diagram Aliran Air (Sankey)**")
    if hidro is None:
        st.caption(
            "Belum dapat digambar — neraca air memerlukan tingkat retensi, "
            "yang belum diketahui untuk konfigurasi ini."
        )
        return

    st.caption(
        "Neraca massa tertutup: seluruh curah hujan terbagi habis menjadi air "
        "yang tertahan sistem dan air yang melimpas. Versi sebelumnya memecah "
        "aliran ke simpanan zeolit dan perkolasi alami memakai pembagi 0,55 dan "
        "0,30 yang tidak bersumber, sehingga sebagian air hilang di percabangan."
    )
    tertahan = hidro["air_tertahan_m3"]
    melimpas = hidro["volume_hujan_m3"] - tertahan
    fig = go.Figure(go.Sankey(
        node=dict(
            label=["Curah Hujan", "Tertahan Sistem", "Melimpas"],
            color=["#42A5F5", "#26A69A", "#EF5350"],
            pad=15, thickness=20,
        ),
        link=dict(
            source=[0, 0], target=[1, 2],
            value=[tertahan, melimpas],
            color=["rgba(38,166,154,0.4)", "rgba(239,83,80,0.3)"],
        ),
    ))
    fig.update_layout(
        title="Aliran Air Melalui Sistem ZEOPAVE-AQUA (m³)",
        height=340, margin=dict(t=40, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")
