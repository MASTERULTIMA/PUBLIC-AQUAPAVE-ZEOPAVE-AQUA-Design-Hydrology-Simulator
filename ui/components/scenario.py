"""
Kendali skenario: pemilih, indikator acuan, dan identitas kendali masukan.

IDENTITAS WIDGET DIIKAT KE SKENARIO
-----------------------------------
Streamlit menurunkan identitas sebuah widget dari parameternya, termasuk nilai
bawaannya. Kendali di bilah sisi membaca nilai bawaannya DARI skenario yang
juga ditulisinya, sehingga setiap perubahan menggeser identitas widget itu
sendiri: masukan berikutnya terkirim dengan identitas lama, tidak dikenali,
lalu dibuang diam-diam. Akibatnya pengguna menggeser penggeser, nilainya
melompat kembali, dan baru perubahan berikutnya yang benar-benar tersimpan.

Perbaikannya adalah memberi setiap kendali kunci tetap yang diikat ke NAMA
skenario, bukan ke nilainya:

    aquapave_kendali:A:substitusi_ipal_persen

Identitas menjadi stabil selama skenario aktif tidak berganti, sehingga
masukan tidak lagi hilang. Karena kuncinya mengandung nama skenario, berpindah
skenario tetap memuat ulang kendali dari nilai skenario yang bersangkutan —
bukan mewarisi nilai skenario sebelumnya.
"""

from __future__ import annotations

from scenario import state as skenario

#: Awalan kunci session_state untuk kendali masukan.
PRAWALAN_KENDALI = "aquapave_kendali"

#: Kunci tetap untuk pemilih skenario aktif.
#:
#: Pemilih menghadapi persoalan identitas yang sama seperti kendali lain,
#: tetapi tidak dapat diikat ke nama skenario: nilainya JUSTRU nama skenario
#: itu. Karena itu kuncinya tetap, dan sinkronisasi terhadap koleksi dilakukan
#: dengan menghapus kunci ketika koleksinya berubah.
KUNCI_PEMILIH = "aquapave_skenario_terpilih"

#: Label tampilan setiap skenario.
LABEL_SKENARIO = {
    skenario.ACUAN: "Konfigurasi Acuan Penelitian",
    **{n: f"Skenario Kustom {n}" for n in skenario.NAMA_KUSTOM},
}

#: Judul ringkas untuk kolom tabel perbandingan.
JUDUL_SKENARIO = {
    skenario.ACUAN: "Acuan Penelitian",
    **{n: f"Skenario {n}" for n in skenario.NAMA_KUSTOM},
}


def kunci(nama_skenario: str, parameter: str) -> str:
    """Kunci session_state tetap untuk satu kendali pada satu skenario."""
    return f"{PRAWALAN_KENDALI}:{nama_skenario}:{parameter}"


def bersihkan_kendali(st, nama_skenario: str) -> None:
    """
    Hapus seluruh kendali milik satu skenario.

    Dipanggil saat skenario dihapus. Tanpa ini, menambahkan skenario baru
    dengan nama yang sama akan mewarisi nilai kendali milik skenario lama,
    bukan memulai dari acuan penelitian seperti yang dijanjikan.
    """
    awalan = f"{PRAWALAN_KENDALI}:{nama_skenario}:"
    for k in [k for k in list(st.session_state.keys())
              if isinstance(k, str) and k.startswith(awalan)]:
        del st.session_state[k]


def pemilih(st):
    """
    Pemilih skenario aktif beserta tombol tambah dan hapus.

    Mengembalikan koleksi yang sudah mutakhir.
    """
    kol = skenario.muat(st)
    st.markdown("**Skenario**")

    nama = kol.nama_terpakai()
    if st.session_state.get(KUNCI_PEMILIH) not in nama:
        st.session_state[KUNCI_PEMILIH] = kol.aktif

    aktif = st.radio(
        "Skenario aktif", nama, key=KUNCI_PEMILIH,
        format_func=lambda n: LABEL_SKENARIO[n], label_visibility="collapsed",
    )
    if aktif != kol.aktif:
        skenario.pilih(st, aktif)
        kol = skenario.muat(st)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Tambah skenario", disabled=kol.penuh(), width="stretch"):
            baru = skenario.tambah_kustom(st, dari=kol.aktif)
            bersihkan_kendali(st, baru)
            _lupakan_pilihan(st)
            st.rerun()
    with c2:
        if st.button(
            "Hapus skenario", disabled=kol.aktif == skenario.ACUAN, width="stretch"
        ):
            dihapus = kol.aktif
            skenario.hapus_kustom(st, dihapus)
            bersihkan_kendali(st, dihapus)
            _lupakan_pilihan(st)
            st.rerun()

    return skenario.muat(st)


def _lupakan_pilihan(st) -> None:
    """
    Lupakan pilihan tersimpan agar pemilih diselaraskan ulang dari koleksi.

    Dipakai setelah menambah atau menghapus skenario. Menulis langsung ke
    kunci widget yang sudah digambar pada putaran yang sama tidak dapat
    diandalkan; menghapusnya membuat cabang sinkronisasi di atas mengisinya
    kembali dari `kol.aktif` pada putaran berikutnya.
    """
    if KUNCI_PEMILIH in st.session_state:
        del st.session_state[KUNCI_PEMILIH]


def indikator(st, kol, sk) -> None:
    """
    Keterangan status skenario aktif.

    Tiga keadaan yang sengaja dibedakan: acuan penelitian, kustom yang berbeda
    dari acuan, dan kustom yang kebetulan identik dengan acuan. Keadaan ketiga
    penting karena hasil ukur memang kembali tersedia ketika komposisinya
    dipulihkan persis.
    """
    if kol.aktif == skenario.ACUAN:
        st.success(
            "**Konfigurasi Acuan Penelitian** — komposisi yang benar-benar "
            "dicetak dan diuji laboratorium. Tidak dapat diubah; hasil "
            "pengukuran melekat padanya."
        )
        return

    beda = skenario.alasan_berbeda(sk)
    if beda:
        st.warning(
            "**Skenario Kustom** — berbeda dari acuan pada: " + "; ".join(beda)
        )
    else:
        st.info(
            "**Skenario Kustom** — komposisinya saat ini identik dengan acuan "
            "penelitian, sehingga hasil pengukuran kembali berlaku."
        )


def aktifkan_acuan(st) -> None:
    """
    Jadikan konfigurasi acuan penelitian skenario aktif.

    Dipakai tab Mulai di Sini ketika skenario aktif tidak memiliki hasil ukur:
    pemula diberi jalan kembali satu tombol, tanpa harus mencari pemilih di
    bilah sisi. Skenario kustom TIDAK dihapus; hanya pilihan aktifnya yang
    berpindah. Pemanggil bertanggung jawab memanggil `st.rerun()`.
    """
    skenario.pilih(st, skenario.ACUAN)
    _lupakan_pilihan(st)
