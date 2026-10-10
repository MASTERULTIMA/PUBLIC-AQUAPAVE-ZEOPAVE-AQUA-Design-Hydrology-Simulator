"""
Pemberitahuan berdasarkan KATEGORI ILMIAHNYA, bukan berdasarkan warnanya.

Sebelum lapisan ini ada, pilihan antara st.info, st.warning, dan st.error
diambil per tempat dan tidak konsisten: pembatasan yang setara bisa tampil
sebagai info di satu tab dan warning di tab lain. Fungsi di bawah menamai
kategorinya, sehingga pemanggil memilih *makna* dan bukan *warna*.

Empat kategori yang dipakai proyek ini:

  acuan            konfigurasi yang benar-benar diuji laboratorium
  asumsi           parameter rancangan atau penyederhanaan model
  keterbatasan     batas yang membuat sebuah angka tidak boleh dikutip jauh
  tak_tervalidasi  keluaran yang tidak punya sumber di dalam penelitian
"""

from __future__ import annotations

from scenario.keluaran import FRASA_TIDAK_TERSEDIA, Keluaran


def acuan(st, teks: str) -> None:
    """Menandai konfigurasi yang benar-benar dicetak dan diuji."""
    st.success(teks)


def asumsi(st, teks: str) -> None:
    """Menandai parameter rancangan atau penyederhanaan model."""
    st.info(teks)


def keterbatasan(st, teks: str) -> None:
    """Menandai batas penafsiran sebuah angka."""
    st.warning(teks)


def tak_tervalidasi(st, teks: str) -> None:
    """Menandai keluaran yang tidak bersumber di dalam penelitian."""
    st.error(teks)


def tidak_tersedia(st, k: Keluaran) -> None:
    """
    Penyajian baku keluaran yang tidak tersedia.

    SATU-SATUNYA cara lapisan tampilan boleh menggambarkan hasil yang tidak
    ada. Tidak ada nol, tidak ada sel kosong, dan tidak ada angka terkaan —
    sel kosong itulah temuannya (ADR-009).
    """
    if k.tersedia:
        raise ValueError(
            f"{k.id.value}: keluaran ini tersedia; "
            "jangan menggambarnya sebagai tidak tersedia"
        )
    st.warning(f"**{k.label}** — {FRASA_TIDAK_TERSEDIA}")
    if k.catatan and k.catatan != FRASA_TIDAK_TERSEDIA:
        st.caption(k.catatan)
