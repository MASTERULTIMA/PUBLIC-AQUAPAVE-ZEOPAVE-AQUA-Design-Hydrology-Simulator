"""
Tab Mulai di Sini — pintu masuk bagi pengguna yang baru mengenal aplikasi.

UNTUK SIAPA
-----------
Orang yang belum pernah belajar teknik sipil. Tab ini menjelaskan apa yang
dikerjakan aplikasi, memperlihatkan sistemnya lewat model 3D, lalu menuntun
satu simulasi dari awal sampai hasilnya terbaca: pilih percobaan, tinjau
masukan, jalankan, baca hasil.

PENYAJIAN SAJA
--------------
Tidak ada rumus di berkas ini. Simulasi terpandu memanggil
`core/hidrologi.skenario()` — fungsi yang SAMA dengan yang dipakai tab Retensi
Air — sehingga kedua tab mustahil menghasilkan angka yang berbeda untuk
masukan yang sama.

TINGKAT RETENSI TIDAK DIPILIH DI SINI
-------------------------------------
Simulasi terpandu memakai retensi skenario aktif, yang datang sudah selesai
dari `scenario/resolusi.py` (ADR-009, ADR-010). Bila retensi itu tidak
tersedia — komposisi skenario aktif belum pernah diuji — tab ini TIDAK
meminjam 40,0% dari konfigurasi acuan dan tidak menawarkan angka pengganti.
Ia menyatakan ketidaktersediaannya, lalu menunjukkan dua jalan keluar: kembali
ke konfigurasi acuan, atau membuka tab Retensi Air, satu-satunya tempat
pengguna boleh memasukkan asumsi retensinya sendiri secara sadar.

MASUKAN PERCOBAAN TIDAK MENGUBAH SKENARIO
-----------------------------------------
Luas, intensitas, dan lama hujan di tab ini adalah masukan percobaan milik tab
ini saja, seperti durasi hujan di tab Retensi Air dan luas proyek di tab
Efisiensi Biaya. Ketiganya parameter lokasi — mengubahnya tidak mengubah
komposisi yang diuji (ADR-009) — dan tab ini tidak menuliskannya kembali ke
skenario di bilah sisi.

CONTOH PERCOBAAN BUKAN STANDAR
------------------------------
Percobaan siap pakai dinyatakan sebagai KELIPATAN skenario naskah (luas
sepersepuluh, hujan dua kali lebih deras, hujan tiga kali lebih lama), bukan
sebagai golongan hujan atau jenis lahan tertentu. Aplikasi tidak memiliki
sumber untuk penggolongan semacam itu, sehingga tidak mengarangnya.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from core import hidrologi
from data import akses
from scenario.keluaran import Keluaran

from .. import gaya
from ..components import evidence as komp_bukti
from ..components import model3d
from ..components import scenario as komp_skenario
from ..components import warnings as komp_catatan

#: Rentang kendali, dalam satuan masing-masing. Rentang ANTARMUKA, bukan
#: rentang bersumber: disamakan dengan kendali yang sudah ada di bilah sisi
#: (luas, intensitas) dan di tab Retensi Air (durasi). Kesamaannya dijaga
#: validation/test_ui_mulai.py.
RENTANG_LUAS_M2 = (10.0, 10000.0)
RENTANG_INTENSITAS_MM_PER_JAM = (10, 100)
RENTANG_DURASI_JAM = (0.25, 24.0)

KUNCI_PERCOBAAN = "mulai_percobaan"
KUNCI_HASIL = "mulai_hasil"

PERCOBAAN_SENDIRI = "sendiri"

PESAN_PERLU_ACUAN = (
    "Simulasi terpandu memakai tingkat retensi hasil uji laboratorium, dan "
    "hasil itu hanya berlaku untuk campuran yang benar-benar diuji. Skenario "
    "aktif di bilah sisi memakai campuran lain, jadi tidak ada angka yang "
    "dipinjamkan ke sini. Kembali ke Konfigurasi Acuan Penelitian untuk "
    "melanjutkan, atau buka tab Retensi Air bila ingin menjelajah dengan "
    "angka retensi masukan sendiri."
)

PESAN_BELUM_DIJALANKAN = (
    "Belum ada hasil. Tekan **Jalankan simulasi** pada Langkah 3 untuk "
    "menghitungnya."
)

PESAN_MASUKAN_BERUBAH = (
    "Masukan sudah berubah sejak simulasi terakhir. Hasil di bawah masih "
    "milik masukan sebelumnya — tekan **Jalankan simulasi** lagi untuk "
    "memperbaruinya."
)


@dataclass(frozen=True)
class Percobaan:
    """Satu titik awal percobaan: tiga masukan dan penjelasannya."""

    kunci: str
    judul: str
    uraian: str
    luas_m2: float
    intensitas_mm_per_jam: float
    durasi_jam: float


def daftar_percobaan(
    luas_skenario_m2: float, intensitas_skenario_mm_per_jam: float
) -> tuple[Percobaan, ...]:
    """
    Percobaan siap pakai, diturunkan dari skenario naskah yang kanonik.

    Tidak ada angka lokasi yang ditulis di sini: luas dan intensitas acuan
    dibaca dari `data/akses.py`, durasi acuan dari `core/hidrologi.py`, dan
    percobaan lain adalah kelipatannya.
    """
    luas = float(akses.nilai("SKALA_LUAS_ACUAN"))
    intensitas = float(akses.nilai("SKALA_INTENSITAS_ACUAN"))
    durasi = float(hidrologi.ACUAN_DURASI_JAM)
    sumber = akses.besaran("SKALA_LUAS_ACUAN").sumber
    return (
        Percobaan(
            "naskah", "Skenario naskah penelitian",
            f"Titik awal yang disarankan. Luas, derasnya hujan, dan lama "
            f"hujan sama dengan contoh pada naskah penelitian ({sumber}).",
            luas, intensitas, durasi,
        ),
        Percobaan(
            "area_kecil", "Area sepersepuluh",
            "Hujan yang sama di atas area sepersepuluh luasnya. Untuk "
            "melihat pengaruh luas area.",
            luas / 10.0, intensitas, durasi,
        ),
        Percobaan(
            "hujan_deras", "Hujan dua kali lebih deras",
            "Area yang sama, hujan dua kali lebih deras. Untuk melihat "
            "pengaruh derasnya hujan.",
            luas, intensitas * 2.0, durasi,
        ),
        Percobaan(
            "hujan_lama", "Hujan tiga kali lebih lama",
            "Area dan derasnya hujan sama, tetapi hujan berlangsung tiga "
            "kali lebih lama.",
            luas, intensitas, durasi * 3.0,
        ),
        Percobaan(
            PERCOBAAN_SENDIRI, "Atur sendiri",
            "Berangkat dari luas dan intensitas hujan skenario aktif di "
            "bilah sisi. Ubah sesuka Anda pada Langkah 2.",
            float(luas_skenario_m2), float(intensitas_skenario_mm_per_jam),
            durasi,
        ),
    )


def angka(nilai: float, desimal: int = 1) -> str:
    """
    Angka dengan pemisah Indonesia: titik untuk ribuan, koma untuk desimal.

    >>> angka(20000, 0)
    '20.000'
    >>> angka(42.5)
    '42,5'
    """
    teks = f"{nilai:,.{desimal}f}"
    return teks.replace(",", " ").replace(".", ",").replace(" ", ".")


def render(
    st,
    retensi_aktif: Keluaran,
    luas_area_m2: float,
    intensitas_hujan_mm_per_jam: float,
) -> None:
    """
    Gambar seluruh tab Mulai di Sini.

    `retensi_aktif` — keluaran retensi skenario aktif, hasil
    `scenario/resolusi.py`; objek yang sama dengan yang mengisi tabel
    perbandingan dan tab Retensi Air.

    `luas_area_m2` dan `intensitas_hujan_mm_per_jam` — parameter lokasi
    skenario aktif, dipakai HANYA sebagai titik awal percobaan "Atur sendiri".
    """
    _sambutan(st)

    # Dipesan sekarang, diisi setelah simulasi terpandu diproses: model 3D
    # menampilkan angka simulasi terakhir, dan angka itu baru diketahui
    # setelah tombol Jalankan dibaca di bawah.
    gaya.judul_bagian(st, "Kenali sistemnya — model 3D")
    tempat_model = st.container()

    hasil = _simulasi_terpandu(
        st, retensi_aktif, luas_area_m2, intensitas_hujan_mm_per_jam)

    with tempat_model:
        _model(st, retensi_aktif, hasil)

    _daftar_istilah(st, retensi_aktif)
    _langkah_berikutnya(st)


# ═══════════ sambutan ═══════════

def _sambutan(st) -> None:
    gaya.judul_bagian(st, "Mulai di Sini")
    st.markdown(
        "**AQUAPAVE membantu Anda memahami ZEOPAVE-AQUA**: perkerasan "
        "berpori yang membiarkan air hujan meresap lalu menahannya untuk "
        "sementara, sehingga lebih sedikit air yang melimpas ke jalan dan "
        "selokan."
    )
    st.markdown(
        "Di halaman ini Anda dapat:\n"
        "1. **Mengenal lapisannya** lewat model 3D yang bisa diputar.\n"
        "2. **Menjalankan simulasi pertama**: berapa banyak air hujan yang "
        "tertahan untuk luas dan hujan tertentu.\n"
        "3. **Melanjutkan ke tab lain** bila ingin rincian teknisnya."
    )
    st.caption(
        "Tidak perlu latar belakang teknik sipil. Istilah teknis dijelaskan "
        "di tempatnya, dan daftar istilah ada di bagian bawah halaman ini. "
        "Setiap angka di aplikasi diberi label status bukti — misalnya "
        "TERUKUR atau MODEL — supaya jelas mana hasil uji laboratorium dan "
        "mana hasil hitungan."
    )


# ═══════════ model 3D ═══════════

def _model(st, retensi_aktif: Keluaran, hasil: dict | None) -> None:
    st.caption(
        "Beginilah susunan ZEOPAVE-AQUA dari permukaan sampai ke bawah, "
        "mengikuti ilustrasi dan Tabel 4.2 pada naskah penelitian. Setelah "
        "Anda menjalankan simulasi di bawah, angka hasilnya ikut ditempel "
        "pada model ini."
    )
    model3d.render(
        st, akses.lapisan_sistem(),
        retensi_persen=retensi_aktif.nilai if retensi_aktif.tersedia else None,
        angka=_angka_untuk_model(hasil),
    )


def _angka_untuk_model(hasil: dict | None) -> dict | None:
    """Teks angka simulasi terakhir, siap ditempel pada model 3D."""
    if hasil is None:
        return None
    h = hasil["hidro"]
    lolos = h["volume_hujan_m3"] - h["air_tertahan_m3"]
    return {
        "jatuh": f"Air hujan jatuh: {angka(h['volume_hujan_m3'])} m³",
        "tertahan": f"Tertahan: {angka(h['air_tertahan_m3'])} m³",
        "lolos": f"Tidak tertahan: {angka(lolos)} m³",
    }


# ═══════════ simulasi terpandu ═══════════

def _simulasi_terpandu(
    st, retensi_aktif: Keluaran, luas_skenario: float, intensitas_skenario: float
) -> dict | None:
    """
    Empat langkah simulasi. Mengembalikan hasil simulasi terakhir yang masih
    berlaku, atau None.
    """
    gaya.judul_bagian(st, "Simulasi pertama Anda")
    st.caption(
        "Simulasi ini menjawab satu pertanyaan: **bila hujan turun di atas "
        "perkerasan ZEOPAVE-AQUA, berapa banyak air yang tertahan dan berapa "
        "yang masih melimpas?** Ikuti empat langkah di bawah."
    )

    if not retensi_aktif.tersedia:
        komp_catatan.tidak_tersedia(st, retensi_aktif)
        st.info(PESAN_PERLU_ACUAN)
        if st.button("Kembali ke Konfigurasi Acuan Penelitian",
                     key="mulai_kembali_acuan"):
            komp_skenario.aktifkan_acuan(st)
            st.rerun()
        return None

    percobaan = _langkah_pilih(st, luas_skenario, intensitas_skenario)
    masukan = _langkah_masukan(st, percobaan, retensi_aktif)
    _langkah_jalankan(st, percobaan, masukan, retensi_aktif)
    return _langkah_hasil(st, masukan, retensi_aktif)


def _langkah_pilih(st, luas_skenario: float, intensitas_skenario: float) -> Percobaan:
    st.markdown("**Langkah 1 dari 4 — Pilih percobaan**")
    pilihan = daftar_percobaan(luas_skenario, intensitas_skenario)
    kunci = st.radio(
        "Percobaan", [p.kunci for p in pilihan], key=KUNCI_PERCOBAAN,
        format_func=lambda k: next(p.judul for p in pilihan if p.kunci == k),
        captions=[p.uraian for p in pilihan],
        label_visibility="collapsed",
    )
    st.caption(
        "Percobaan di atas adalah titik awal untuk dijelajahi, dinyatakan "
        "sebagai kelipatan skenario naskah. Angkanya bukan penggolongan "
        "hujan maupun standar perencanaan."
    )
    return next(p for p in pilihan if p.kunci == kunci)


def _langkah_masukan(st, p: Percobaan, retensi_aktif: Keluaran) -> dict:
    st.markdown("**Langkah 2 dari 4 — Tinjau atau ubah masukan**")
    st.caption(
        "Tiga angka inilah yang menentukan hasil simulasi. Biarkan apa adanya "
        "untuk percobaan pertama, atau ubah untuk melihat pengaruhnya."
    )
    k1, k2, k3 = st.columns(3)
    with k1:
        luas = st.number_input(
            "Luas area (m²)", RENTANG_LUAS_M2[0], RENTANG_LUAS_M2[1],
            _dalam(p.luas_m2, RENTANG_LUAS_M2), step=50.0,
            key=f"mulai:{p.kunci}:luas",
            help=(
                "Luas permukaan perkerasan yang kehujanan, dalam meter "
                f"persegi. Dapat diisi {angka(RENTANG_LUAS_M2[0], 0)} sampai "
                f"{angka(RENTANG_LUAS_M2[1], 0)} m². Makin luas areanya, makin "
                "banyak air hujan yang jatuh di atasnya."
            ),
        )
    with k2:
        intensitas = st.slider(
            "Derasnya hujan (mm/jam)",
            RENTANG_INTENSITAS_MM_PER_JAM[0], RENTANG_INTENSITAS_MM_PER_JAM[1],
            int(_dalam(p.intensitas_mm_per_jam, RENTANG_INTENSITAS_MM_PER_JAM)),
            key=f"mulai:{p.kunci}:intensitas",
            help=(
                "Intensitas hujan: tinggi air yang jatuh dalam satu jam, "
                "dalam milimeter per jam. Sebagai pegangan, 1 mm hujan di "
                "atas 1 m² sama dengan 1 liter air."
            ),
        )
    with k3:
        durasi = st.number_input(
            "Lama hujan (jam)", RENTANG_DURASI_JAM[0], RENTANG_DURASI_JAM[1],
            _dalam(p.durasi_jam, RENTANG_DURASI_JAM), step=0.25,
            key=f"mulai:{p.kunci}:durasi",
            help=(
                "Berapa lama hujan berlangsung, dalam jam. Dapat diisi "
                f"{angka(RENTANG_DURASI_JAM[0], 2)} sampai "
                f"{angka(RENTANG_DURASI_JAM[1], 0)} jam."
            ),
        )
    st.caption(
        f"Tingkat retensi yang dipakai: **{angka(retensi_aktif.nilai)}"
        f"{retensi_aktif.satuan} · {retensi_aktif.status_bukti.value}** — "
        "hasil uji laboratorium untuk campuran skenario aktif, tidak diubah "
        "di sini. Koefisien limpasan dan asumsi retensi lain dapat dijelajahi "
        "di tab Retensi Air."
    )
    return {
        "luas_m2": float(luas),
        "intensitas_mm_per_jam": float(intensitas),
        "durasi_jam": float(durasi),
    }


def _dalam(nilai: float, rentang: tuple) -> float:
    """Jepit nilai awal ke dalam rentang kendali."""
    return float(min(max(nilai, rentang[0]), rentang[1]))


def _langkah_jalankan(
    st, p: Percobaan, masukan: dict, retensi_aktif: Keluaran
) -> None:
    st.markdown("**Langkah 3 dari 4 — Jalankan simulasi**")
    if st.button("Jalankan simulasi", type="primary", key="mulai_jalankan"):
        st.session_state[KUNCI_HASIL] = {
            "percobaan": p.judul,
            "masukan": dict(masukan),
            "retensi_persen": float(retensi_aktif.nilai),
            "status_retensi": retensi_aktif.status_bukti.value,
            "hidro": hidrologi.skenario(
                masukan["intensitas_mm_per_jam"], masukan["luas_m2"],
                masukan["durasi_jam"], retensi_aktif.nilai,
            ),
        }


def _hasil_berlaku(st, retensi_aktif: Keluaran) -> dict | None:
    """
    Hasil simulasi terakhir, hanya bila masih milik retensi skenario aktif.

    Hasil yang dihitung dengan retensi lain — misalnya sebelum pengguna
    berpindah skenario — tidak ditampilkan lagi: angkanya bukan milik
    skenario yang sekarang aktif.
    """
    hasil = st.session_state.get(KUNCI_HASIL)
    if not hasil or not retensi_aktif.tersedia:
        return None
    if abs(hasil["retensi_persen"] - float(retensi_aktif.nilai)) > 1e-9:
        return None
    return hasil


def _langkah_hasil(st, masukan: dict, retensi_aktif: Keluaran) -> dict | None:
    st.markdown("**Langkah 4 dari 4 — Baca hasilnya**")
    hasil = _hasil_berlaku(st, retensi_aktif)
    if hasil is None:
        st.info(PESAN_BELUM_DIJALANKAN)
        return None
    if hasil["masukan"] != masukan:
        st.info(PESAN_MASUKAN_BERUBAH)

    _ringkasan_hasil(st, hasil)
    _arti_hasil(st, hasil)
    _rincian_teknis(st, hasil)
    return hasil


def _ringkasan_hasil(st, hasil: dict) -> None:
    h, m = hasil["hidro"], hasil["masukan"]
    komp_bukti.kotak_hasil(
        st, f"{angka(h['air_tertahan_liter'], 0)} liter",
        "air hujan tertahan sistem pada percobaan ini",
        "KELUARAN MODEL — hasil hitungan, bukan pengukuran lapangan",
        rata_tengah=True,
    )
    st.markdown(
        f"Hujan **{angka(m['intensitas_mm_per_jam'], 0)} mm/jam** selama "
        f"**{angka(m['durasi_jam'], 2)} jam** di atas area "
        f"**{angka(m['luas_m2'], 0)} m²** menjatuhkan sekitar "
        f"**{angka(h['air_jatuh_liter'], 0)} liter** air. Dengan tingkat "
        f"retensi {angka(hasil['retensi_persen'])}%, ZEOPAVE-AQUA menahan "
        f"sekitar **{angka(h['air_tertahan_liter'], 0)} liter** di antaranya."
    )
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Air hujan yang jatuh", f"{angka(h['volume_hujan_m3'])} m³")
    with k2:
        st.metric("Air yang tertahan sistem", f"{angka(h['air_tertahan_m3'])} m³")
    with k3:
        st.metric("Limpasan dengan ZEOPAVE-AQUA",
                  f"{angka(h['limpasan_zeopave_m3'])} m³")
    with k4:
        st.metric("Pengurangan limpasan",
                  f"{angka(h['reduksi_limpasan_persen'])}%")
    st.caption("1 m³ sama dengan 1.000 liter.")


def _arti_hasil(st, hasil: dict) -> None:
    h = hasil["hidro"]
    st.markdown("**Apa artinya?**")
    st.markdown(
        f"- **Air yang tertahan** disimpan sementara di lapisan hebel dan "
        f"zeolit, sehingga tidak langsung mengalir ke jalan dan selokan. "
        f"Sebagai gambaran, {angka(h['air_tertahan_liter'], 0)} liter setara "
        f"{angka(h['air_tertahan_liter'] / 1000.0)} tandon air berukuran "
        f"1.000 liter.\n"
        f"- **Limpasan** adalah air hujan yang mengalir di permukaan menuju "
        f"saluran. Pada perkerasan biasa yang kedap air, model memberi "
        f"limpasan {angka(h['limpasan_konvensional_m3'])} m³; dengan "
        f"ZEOPAVE-AQUA menjadi {angka(h['limpasan_zeopave_m3'])} m³.\n"
        f"- **Pengurangan limpasan {angka(h['reduksi_limpasan_persen'])}%** "
        f"berarti saluran drainase menerima air lebih sedikit sebanyak itu "
        f"dibanding perkerasan biasa, menurut model ini."
    )
    komp_catatan.keterbatasan(
        st,
        "**Baca dengan hati-hati.** " + h["catatan"] + " Tingkat retensinya "
        "sendiri hasil uji laboratorium; yang merupakan hitungan adalah "
        "penerapannya pada luas dan hujan yang Anda pilih."
    )


def _rincian_teknis(st, hasil: dict) -> None:
    h, m = hasil["hidro"], hasil["masukan"]
    with st.expander("Rincian teknis dan grafik (opsional)"):
        st.caption(
            "Dihitung `core/hidrologi.py`, fungsi yang sama dengan tab "
            "Retensi Air. Volume hujan = intensitas × luas × lama hujan; air "
            "tertahan = volume hujan × tingkat retensi; limpasan = air yang "
            "tidak tertahan × koefisien limpasan."
        )
        koef = h["limpasan_konvensional_m3"] / h["volume_hujan_m3"]
        st.dataframe(pd.DataFrame([
            {"Besaran": "Luas area", "Nilai": f"{angka(m['luas_m2'], 0)} m²",
             "Status": "masukan percobaan"},
            {"Besaran": "Intensitas hujan",
             "Nilai": f"{angka(m['intensitas_mm_per_jam'], 0)} mm/jam",
             "Status": "masukan percobaan"},
            {"Besaran": "Lama hujan",
             "Nilai": f"{angka(m['durasi_jam'], 2)} jam",
             "Status": "masukan percobaan"},
            {"Besaran": "Tingkat retensi",
             "Nilai": f"{angka(hasil['retensi_persen'])}%",
             "Status": hasil["status_retensi"]},
            {"Besaran": "Koefisien limpasan perkerasan biasa",
             "Nilai": angka(koef, 2), "Status": "bawaan model"},
            {"Besaran": "Volume hujan",
             "Nilai": f"{angka(h['volume_hujan_m3'])} m³", "Status": "model"},
            {"Besaran": "Air tertahan",
             "Nilai": f"{angka(h['air_tertahan_m3'])} m³", "Status": "model"},
            {"Besaran": "Limpasan perkerasan biasa",
             "Nilai": f"{angka(h['limpasan_konvensional_m3'])} m³",
             "Status": "model"},
            {"Besaran": "Limpasan ZEOPAVE-AQUA",
             "Nilai": f"{angka(h['limpasan_zeopave_m3'])} m³", "Status": "model"},
            {"Besaran": "Pengurangan limpasan",
             "Nilai": f"{angka(h['reduksi_limpasan_persen'])}%",
             "Status": "model"},
        ]), width="stretch", hide_index=True)

        fig = go.Figure(go.Bar(
            x=["Air hujan jatuh", "Tertahan sistem",
               "Limpasan perkerasan biasa", "Limpasan ZEOPAVE-AQUA"],
            y=[h["volume_hujan_m3"], h["air_tertahan_m3"],
               h["limpasan_konvensional_m3"], h["limpasan_zeopave_m3"]],
            marker_color=["#42A5F5", "#26A69A", "#EF5350", "#1565C0"],
            text=[angka(v) for v in (
                h["volume_hujan_m3"], h["air_tertahan_m3"],
                h["limpasan_konvensional_m3"], h["limpasan_zeopave_m3"])],
            textposition="outside",
        ))
        fig.update_layout(
            title="Neraca air percobaan ini (m³) — keluaran model",
            height=320, yaxis_title="m³", margin=dict(t=44, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, width="stretch", key="mulai_grafik_neraca")
        st.caption(
            "Ingin mengubah koefisien limpasan atau melihat diagram aliran? "
            "Buka tab Retensi Air."
        )


# ═══════════ daftar istilah ═══════════

def _daftar_istilah(st, retensi_aktif: Keluaran) -> None:
    gaya.judul_bagian(st, "Daftar istilah")
    retensi = akses.besaran("RETENSI_RERATA")
    with st.expander("Istilah yang sering muncul"):
        st.markdown(
            "- **Perkerasan berpori** — lapisan jalan atau halaman yang "
            "sengaja dibuat berongga supaya air dapat meresap, tidak hanya "
            "mengalir di permukaan.\n"
            "- **Retensi air** — bagian air hujan yang ditahan sistem untuk "
            f"sementara. Retensi {angka(retensi.nilai, 0)}% berarti dari "
            f"setiap 100 liter air yang masuk, {angka(retensi.nilai, 0)} "
            "liter tertahan.\n"
            "- **Limpasan** — air hujan yang tidak meresap dan mengalir di "
            "permukaan menuju selokan. Limpasan yang besar membebani saluran "
            "dan dapat memicu genangan.\n"
            "- **Intensitas hujan** — derasnya hujan, yaitu tinggi air yang "
            "jatuh dalam satu jam (mm/jam). 1 mm hujan di atas 1 m² sama "
            "dengan 1 liter air.\n"
            "- **Koefisien limpasan (C)** — angka 0 sampai 1 yang menyatakan "
            "bagian air hujan yang menjadi limpasan pada suatu permukaan. "
            "Makin kedap permukaannya, makin mendekati 1.\n"
            "- **Permeabilitas (k)** — kemudahan air menembus suatu bahan, "
            "dalam cm/detik. Makin besar nilainya, makin cepat air lewat.\n"
            "- **Kuat tekan** — beban tekan terbesar yang sanggup ditahan "
            "beton per satuan luas sebelum hancur, dalam megapascal (MPa).\n"
            "- **Lumpur IPAL** — endapan padat dari instalasi pengolahan air "
            "limbah. Pada penelitian ini sebagian semen diganti lumpur IPAL "
            "yang sudah diolah.\n"
            "- **Konfigurasi acuan** — campuran yang benar-benar dicetak dan "
            "diuji pada penelitian. Hasil uji laboratorium hanya berlaku "
            "untuk campuran ini."
        )
    with st.expander("Cara membaca label status bukti"):
        st.markdown(
            "- **terukur** — diukur tim peneliti di laboratorium.\n"
            "- **literatur** — dikutip dari pustaka yang dirujuk naskah.\n"
            "- **model** atau **deterministik** — hasil hitungan dari "
            "masukan, bukan pengukuran.\n"
            "- **target** — nilai rancangan yang belum pernah diukur.\n"
            "- **asumsi** — nilai kerja yang belum punya sumber; perlakukan "
            "dengan hati-hati.\n"
            "- **Belum tersedia** — campuran itu belum pernah diuji, jadi "
            "aplikasi tidak menampilkan angka apa pun, termasuk taksiran."
        )


# ═══════════ langkah berikutnya ═══════════

#: Nama tab dan pertanyaan yang dijawabnya. Nama tabnya sendiri didaftarkan
#: akar komposisi; daftar ini hanya penunjuk arah bagi pembaca.
PENUNJUK_TAB = (
    ("Retensi Air",
     "Simulasi yang sama dengan kendali lebih lengkap: koefisien limpasan, "
     "asumsi retensi sendiri, dan diagram aliran air."),
    ("Kalkulator Mix Design",
     "Berapa kilogram semen, lumpur IPAL, batu sirtu, dan air untuk volume "
     "adukan tertentu."),
    ("Permeabilitas",
     "Seberapa cepat air menembus beton poros, dihitung dari data uji."),
    ("Kuat Tekan",
     "Seberapa besar beban yang sanggup ditahan beton, dihitung dari data uji."),
    ("Emisi CO₂",
     "Perbandingan emisi karbon campuran biasa dan campuran berlumpur IPAL."),
    ("Dasbor Perbandingan",
     "Ringkasan perbandingan ZEOPAVE-AQUA dengan perkerasan biasa."),
    ("Efisiensi Biaya",
     "Perkiraan biaya material per meter persegi — angkanya ilustratif."),
)


def _langkah_berikutnya(st) -> None:
    gaya.judul_bagian(st, "Ke mana setelah ini")
    st.markdown("\n".join(f"- **{nama}** — {isi}" for nama, isi in PENUNJUK_TAB))
    st.caption(
        "Bilah sisi di kiri berisi pengaturan lanjutan: di sana Anda dapat "
        "menambah skenario dan mengubah komposisi campuran. Untuk percobaan "
        "pertama, pengaturan itu tidak perlu disentuh."
    )
