"""
Penyajian provenansi: dari mana sebuah angka berasal.

Setiap besaran di konstanta.py membawa sumber, status, dan catatan. Komponen
di sini menampilkannya apa adanya. Tidak ada angka yang boleh muncul di layar
tanpa jalur menuju asal-usulnya — itulah alasan lapisan ini ada.
"""

from __future__ import annotations


def keterangan(st, besaran) -> None:
    """Satu baris provenansi di bawah sebuah nilai."""
    st.caption(besaran.provenans())


def daftar(st, besaran_iter) -> None:
    """Daftar provenansi beberapa besaran sekaligus."""
    for b in besaran_iter:
        st.markdown(f"**{b.label if hasattr(b, 'label') else b.sumber}** — {b.provenans()}")


def panel_angka_kunci(st, angka: list[dict]) -> None:
    """
    Panel provenansi untuk kartu KPI.

    `angka` adalah keluaran data/akses.angka_kunci(), yang sudah membawa
    label dan kalimat provenansi lengkap.
    """
    with st.expander("Provenansi angka di atas"):
        for a in angka:
            st.markdown(f"**{a['label']}** — {a['provenans']}")
        st.caption(
            "Status bukti mengikuti ADR-002: terukur, literatur, model, target, "
            "asumsi. Hanya nilai berstatus terukur dan literatur yang disajikan "
            "tanpa kualifikasi."
        )


def panel_keterbatasan(st, judul: str, butir: list[str]) -> None:
    """
    Panel keterbatasan penelitian.

    Keterbatasan ditulis sebagai daftar butir agar dapat dibaca sekilas, bukan
    dikubur di dalam paragraf.
    """
    with st.expander(judul):
        for b in butir:
            st.markdown(f"- {b}")
