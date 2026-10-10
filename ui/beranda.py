"""
Beranda — isi halaman di luar tab.

TANGGUNG JAWAB TUNGGAL: menggambar bagian halaman yang bukan milik tab mana
pun — panji utama, kartu angka kunci beserta provenansinya, pandangan
perbandingan skenario, dan footer.

PANDANGAN PERBANDINGAN BUKAN TAB
--------------------------------
Perbandingan skenario sengaja berada DI ATAS deretan tab, bukan menjadi tab
kedelapan: ia pandangan utama aplikasi, dan tab di bawahnya adalah rinciannya.
Di sanalah pengguna melihat sekaligus apa yang diketahui, apa yang dihitung,
apa yang ditargetkan, dan apa yang belum diketahui.

Tabelnya berada di dalam panel lipat. Selama baru ada satu skenario — belum
ada yang dibandingkan — panel itu tertutup agar pengguna baru tidak disambut
tabel teknis sebelum sempat membaca tab Mulai di Sini. Begitu skenario kedua
ditambahkan, panel terbuka dengan sendirinya. Isi tabelnya tidak berubah.

Modul ini MENGGAMBAR hasil resolusi; ia tidak pernah menyelesaikannya sendiri.
Keluaran yang sudah selesai diserahkan akar komposisi, dan aturan status bukti
serta ketersediaan tetap hidup di `scenario/` (ADR-009, ADR-010).
"""

from __future__ import annotations

from scenario.keluaran import Keluaran, OutputID

from . import gaya
from .components import comparison as komp_banding
from .components import evidence as komp_bukti
from .components import provenance as komp_provenans

PANJI = """
<div class="hero-banner">
  <div class="hero-title">AQUAPAVE</div>
  <div class="hero-sub">
    Platform Optimasi Desain ZEOPAVE-AQUA —
    Perkerasan Berpori dengan Sistem Retensi Air untuk Mitigasi Banjir
  </div>
  <div class="hero-ajak">
    Baru pertama kali di sini? Buka tab <b>Mulai di Sini</b> di bawah: kenali
    lapisan sistemnya lewat model 3D, lalu jalankan simulasi pertama Anda
    dalam empat langkah.
  </div>
</div>
"""

FOOTER = """
<div class="footer">
  <b>AQUAPAVE</b> — Platform Optimasi Desain Digital untuk Perkerasan Berpori ZEOPAVE-AQUA<br>
  Mendukung SDG 9 · SDG 11 · SDG 12 · SDG 13
</div>
"""


def panji(st) -> None:
    """Panji utama aplikasi."""
    st.markdown(PANJI, unsafe_allow_html=True)


def kartu_angka_kunci(st, angka: list[dict]) -> None:
    """
    Kartu angka kunci beserta panel provenansinya.

    `angka` berasal dari `data/akses.angka_kunci()` — bukan angka yang ditulis
    tangan. Setiap kartu membawa status bukti dan sumbernya, dan panel di
    bawahnya membuka kalimat provenansi lengkapnya.
    """
    st.caption(
        "Empat angka kunci dari penelitian. Tulisan kecil di bawah tiap angka "
        "menyatakan status buktinya — hasil uji laboratorium, nilai dari "
        "pustaka, atau hasil hitungan."
    )
    komp_bukti.kartu_angka_kunci(st, angka)
    komp_provenans.panel_angka_kunci(st, angka)


def perbandingan_skenario(
    st,
    hasil: dict[str, dict[OutputID, Keluaran]],
    kolom: list[str],
    ringkas: dict[str, dict],
) -> None:
    """
    Pandangan perbandingan skenario.

    `hasil` dan `ringkas` sudah diselesaikan `scenario/resolusi.py`. Modul ini
    hanya menyerahkannya kepada komponen tabel, yang menampilkan selisih hanya
    untuk pasangan yang memang sebanding.
    """
    gaya.judul_bagian(st, "Perbandingan Skenario")
    membandingkan = len(kolom) > 1
    if membandingkan:
        st.caption(
            "Hasil setiap skenario berdampingan. Selisih hanya ditampilkan "
            "untuk pasangan yang memang sebanding."
        )
    else:
        st.caption(
            "Saat ini hanya ada Konfigurasi Acuan Penelitian. Tambahkan "
            "skenario di bilah sisi bila ingin membandingkan campuran lain; "
            "tabel di bawah akan terbuka dengan sendirinya."
        )
    with st.expander("Tabel perbandingan skenario", expanded=membandingkan):
        komp_banding.tabel(st, hasil, kolom)
        komp_banding.ringkasan(st, ringkas, kolom)
        st.caption(komp_banding.CATATAN_TABEL)
    st.divider()


def footer(st) -> None:
    st.markdown(FOOTER, unsafe_allow_html=True)
