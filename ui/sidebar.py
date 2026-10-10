"""
Bilah sisi — kendali global aplikasi.

TANGGUNG JAWAB TUNGGAL: menggambar seluruh kendali di bilah sisi, menuliskan
perubahannya ke skenario aktif, lalu MENGEMBALIKAN parameter bersama yang
dibutuhkan akar komposisi.

Modul ini menggambar dan mengumpulkan; ia tidak menyelesaikan sains apa pun.
Resolusi keluaran tetap milik `scenario/resolusi.py`, dan neraca emisi tetap
dihitung akar komposisi.

DUA PERSOALAN IDENTITAS WIDGET YANG SUDAH DITUTUP
-------------------------------------------------
Keduanya ditemukan pada S5-0 dan tidak boleh kembali.

1. **Kunci kendali diikat ke NAMA skenario, bukan ke nilainya.** Streamlit
   menurunkan identitas widget dari parameternya, termasuk nilai bawaan.
   Kendali di sini membaca bawaannya DARI skenario yang juga ditulisinya,
   sehingga tanpa kunci tetap setiap perubahan menggeser identitas widget dan
   masukan berikutnya hilang diam-diam.

2. **Indikator digambar setelah seluruh parameter dibaca.** Penampung dipesan
   lebih dulu agar letaknya tetap di bawah pemilih, tetapi baru diisi di
   akhir. Tanpa itu indikator melaporkan keadaan satu putaran yang lalu:
   tepat saat pengguna menggeser parameter, bilah sisi menyatakan komposisinya
   masih identik dengan acuan sementara tabel di bawahnya sudah benar
   menyatakan sebaliknya.
"""

from __future__ import annotations

from dataclasses import dataclass

from core import emisi
from scenario.state import Koleksi, Skenario
from scenario import state as skenario

from .components import scenario as komp_skenario

BERKAS_LOGO = "Asset/AQUAPAVELOGO.png"

#: Lebar tampil logo di bilah sisi, dalam piksel. Logo AQUAPAVE memuat nama
#: dan keterangan di bawah lambangnya, jadi perlu lebih lebar agar terbaca.
LEBAR_LOGO = 200

KELAS_TARGET = ["f'c 10 MPa", "f'c 12,5 MPa", "f'c 15 MPa",
                "f'c 17,5 MPa", "f'c 20 MPa"]

#: Teks bantuan berbahasa awam. Hanya menjelaskan arti, satuan, dan rentang
#: kendali — tidak memuat angka ilmiah baru.
BANTUAN_LUAS = (
    "Luas permukaan perkerasan yang dihitung, dalam meter persegi "
    "(10 sampai 10.000 m²). Dipakai tab Mulai di Sini, Retensi Air, dan "
    "Efisiensi Biaya. Terkunci pada Konfigurasi Acuan Penelitian; tambahkan "
    "skenario bila ingin mengubahnya."
)
BANTUAN_INTENSITAS = (
    "Derasnya hujan: tinggi air yang jatuh dalam satu jam (10 sampai "
    "100 mm/jam). Sebagai pegangan, 1 mm hujan di atas 1 m² sama dengan "
    "1 liter air."
)
BANTUAN_FAB = (
    "Perbandingan berat air terhadap berat bahan pengikat (semen ditambah "
    "lumpur IPAL) dalam adukan, 0,30 sampai 0,55. PARAMETER RANCANGAN: "
    "mengubahnya berarti membuat campuran yang belum pernah diuji, sehingga "
    "hasil uji laboratorium tidak lagi ditampilkan untuk skenario itu."
)
BANTUAN_TOTAL_PENGIKAT = (
    "Jumlah bahan pengikat (semen ditambah lumpur IPAL) yang dipakai untuk "
    "menghitung neraca emisi di tab Emisi CO₂, dalam ton."
)
BANTUAN_KELAS_TARGET = (
    "Kuat tekan rancangan yang ingin dicapai, dalam megapascal (MPa). Pilihan "
    "ini hanya menjadi garis pembanding pada grafik tab Kuat Tekan; bukan "
    "hasil pengukuran."
)

BANTUAN_SUBSTITUSI = (
    "PARAMETER RANCANGAN, bukan hasil pengukuran. Penelitian hanya "
    "menguji satu tingkat substitusi, yaitu 15%. Menggesernya mengubah "
    "proporsi massa dan neraca emisi CO₂ — dua besaran yang memang "
    "deterministik — tetapi TIDAK memprediksi kuat tekan, "
    "permeabilitas, atau retensi."
)


@dataclass(frozen=True)
class ParameterGlobal:
    """
    Apa yang bilah sisi serahkan kepada akar komposisi.

    Sengaja berisi nilai yang memang dipakai di luar bilah sisi saja. Skenario
    aktif dan koleksinya ikut dibawa karena akar komposisi memerlukan keduanya
    untuk resolusi dan neraca emisi — bukan agar tab dapat mengaksesnya.
    """

    koleksi: Koleksi
    skenario_aktif: Skenario
    luas_area_m2: float
    intensitas_hujan_mm_per_jam: float
    target_fc_mpa: float


def render(st) -> ParameterGlobal:
    """Gambar bilah sisi dan kembalikan parameter bersamanya."""
    with st.sidebar:
        st.image(BERKAS_LOGO, width=LEBAR_LOGO)
        st.markdown("### Parameter Global")
        st.caption(
            "Pengaturan lanjutan. Baru pertama kali? Mulai dari tab "
            "Mulai di Sini — bagian ini tidak perlu diubah dulu."
        )

        kol = komp_skenario.pemilih(st)
        sk = skenario.skenario_aktif(st)
        acuan_aktif = kol.aktif == skenario.ACUAN

        # Dipesan sekarang, diisi setelah seluruh parameter dibaca.
        tempat_indikator = st.empty()

        def kunci(parameter: str) -> str:
            return komp_skenario.kunci(kol.aktif, parameter)

        st.divider()
        st.caption(
            "Parameter di bawah berlaku untuk skenario aktif dan seluruh tab. "
            "Substitusi lumpur IPAL hanya dapat diubah di sini."
        )

        luas_area, intensitas, sk = _parameter_komposisi(st, sk, acuan_aktif, kunci)
        sk = _faktor_emisi(st, sk, acuan_aktif, kunci)

        with tempat_indikator.container():
            komp_skenario.indikator(st, kol, sk)

        target_fc_mpa = _kelas_target(st)
        _tentang(st)

    return ParameterGlobal(
        koleksi=skenario.muat(st),
        skenario_aktif=sk,
        luas_area_m2=luas_area,
        intensitas_hujan_mm_per_jam=intensitas,
        target_fc_mpa=target_fc_mpa,
    )


def _parameter_komposisi(st, sk, acuan_aktif, kunci):
    """Lokasi dan komposisi campuran. Mengembalikan (luas, intensitas, sk)."""
    luas_area = st.number_input(
        "Luas Area Perkerasan (m²)", 10.0, 10000.0, sk.luas_area_m2, step=50.0,
        disabled=acuan_aktif, help=BANTUAN_LUAS, key=kunci("luas_area_m2"),
    )
    intensitas = st.slider(
        "Intensitas Hujan (mm/jam)", 10, 100,
        int(sk.intensitas_hujan_mm_per_jam), disabled=acuan_aktif,
        help=BANTUAN_INTENSITAS, key=kunci("intensitas_hujan_mm_per_jam"),
    )

    st.markdown("**Komposisi Campuran**")
    ipal_pct = st.slider(
        "Substitusi Lumpur IPAL (%)", 0, 25,
        int(sk.substitusi_ipal_persen), disabled=acuan_aktif,
        help=BANTUAN_SUBSTITUSI, key=kunci("substitusi_ipal_persen"),
    )
    rasio_ab = st.slider(
        "Faktor Air-Pengikat (f.a.b)", 0.30, 0.55, sk.faktor_air_pengikat, 0.01,
        disabled=acuan_aktif, help=BANTUAN_FAB, key=kunci("faktor_air_pengikat"),
    )

    if not acuan_aktif:
        skenario.perbarui_aktif(
            st,
            substitusi_ipal_persen=float(ipal_pct),
            faktor_air_pengikat=float(rasio_ab),
            luas_area_m2=float(luas_area),
            intensitas_hujan_mm_per_jam=float(intensitas),
        )
        sk = skenario.skenario_aktif(st)
    return luas_area, intensitas, sk


def _faktor_emisi(st, sk, acuan_aktif, kunci):
    """Faktor emisi dan total pengikat. Mengembalikan skenario mutakhir."""
    with st.expander("Faktor emisi CO₂"):
        rentang = emisi.rentang_faktor_emisi_semen()
        co2_opc = st.number_input(
            "CO₂ per ton semen (ton CO₂/ton)", 0.7, 1.0, sk.co2_per_ton_semen, 0.01,
            disabled=acuan_aktif,
            help=f"Pustaka: {rentang['min']}–{rentang['maks']} {rentang['satuan']}. {rentang['sumber']}",
            key=kunci("co2_per_ton_semen"),
        )
        co2_ipal = st.number_input(
            "CO₂ per ton lumpur IPAL (ton CO₂/ton)", 0.0, 0.3, sk.co2_per_ton_ipal, 0.01,
            disabled=acuan_aktif,
            help="ASUMSI — naskah tidak menyebut faktor ini.",
            key=kunci("co2_per_ton_ipal"),
        )
        total_pengikat = st.number_input(
            "Total pengikat (ton)", 1.0, 1000.0, sk.total_pengikat_ton,
            disabled=acuan_aktif, help=BANTUAN_TOTAL_PENGIKAT,
            key=kunci("total_pengikat_ton"),
        )
        if not acuan_aktif:
            skenario.perbarui_aktif(
                st,
                co2_per_ton_semen=float(co2_opc),
                co2_per_ton_ipal=float(co2_ipal),
                total_pengikat_ton=float(total_pengikat),
            )
            sk = skenario.skenario_aktif(st)
    return sk


def _kelas_target(st) -> float:
    """
    Kelas kuat tekan target.

    Parameter rancangan pilihan pengguna, bukan hasil pengukuran. Dipakai
    hanya sebagai garis acuan pada grafik Tab 3.
    """
    st.divider()
    target_fc = st.selectbox(
        "Kelas Kuat Tekan Target", KELAS_TARGET, help=BANTUAN_KELAS_TARGET)
    return float(target_fc.replace(",", ".").split()[1])


def _tentang(st) -> None:
    st.divider()
    st.markdown("**Tentang AQUAPAVE**")
    st.caption(
        "Platform optimasi digital untuk perkerasan berpori ZEOPAVE-AQUA. "
        "Dikembangkan oleh Teknik Sipil dan Teknologi Informasi."
    )
