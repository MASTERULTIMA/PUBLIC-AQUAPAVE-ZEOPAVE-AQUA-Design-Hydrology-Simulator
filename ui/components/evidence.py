"""
Penyajian status bukti dan ketersediaan.

Dua sumbu yang sengaja dipisah (ADR-009) juga dipisah di lapisan tampilan:

  - **status bukti** menjawab seberapa kuat dukungan sebuah nilai, dan hanya
    berarti bila nilainya memang ada;
  - **ketersediaan** menjawab ada atau tidaknya nilai itu untuk skenario ini.

Karena itu komponen di bawah tidak pernah menggambar lencana status bukti
untuk keluaran yang tidak tersedia — "belum tersedia" bukan mutu bukti yang
rendah, melainkan ketiadaan hasil.
"""

from __future__ import annotations

from scenario.keluaran import FRASA_TIDAK_TERSEDIA, Keluaran

#: Warna kartu KPI, dipakai berulang sesuai urutan.
WARNA_KPI = ("biru", "teal", "hijau", "oranye")

#: Jenis lencana lulus/gagal/peringatan.
LULUS = "badge-lulus"
GAGAL = "badge-gagal"
PERINGATAN = "badge-warn"


def lencana(teks: str, jenis: str = LULUS) -> str:
    """Potongan HTML satu lencana. Mengembalikan teks, tidak menggambar."""
    return f'<span class="{jenis}">{teks}</span>'


def lencana_ambang(teks_lulus: str, teks_gagal: str, lulus: bool) -> str:
    """Lencana lulus/gagal terhadap sebuah ambang."""
    return lencana(teks_lulus if lulus else teks_gagal, LULUS if lulus else GAGAL)


def kotak_hasil(
    st,
    nilai: str,
    label: str,
    keterangan: str | None = None,
    lencana_html: str | None = None,
    rata_tengah: bool = False,
) -> None:
    """
    Kotak hasil menonjol — idiom `.result-box` yang berulang di lima tab.

    `nilai` dan `label` diterima sebagai teks yang sudah diformat: pemformatan
    angka adalah urusan pemanggil, bukan urusan komponen.
    """
    gaya = ' style="text-align:center"' if rata_tengah else ""
    baris_kecil = f"<br><small>{keterangan}</small>" if keterangan else ""
    ekor = f"<br>{lencana_html}" if lencana_html else ""
    st.markdown(
        f"""
        <div class="result-box"{gaya}>
          <div class="result-value">{nilai}</div>
          <div class="result-label">{label}{baris_kecil}</div>
          {ekor}
        </div>""",
        unsafe_allow_html=True,
    )


def kartu_angka_kunci(st, angka: list[dict]) -> None:
    """
    Petak kartu KPI dari data/akses.py.

    Setiap kartu membawa status buktinya sendiri, sehingga angka utama tidak
    pernah tampil tanpa keterangan asal-usulnya.
    """
    kartu = []
    for i, a in enumerate(angka):
        nilai = f"{a['nilai']:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        kartu.append(
            f"""
  <div class="kpi-card {WARNA_KPI[i % len(WARNA_KPI)]}">
    <div class="kpi-value">{nilai} <span style="font-size:1rem">{a['satuan']}</span></div>
    <div class="kpi-label">{a['label']}</div>
    <div class="kpi-status">{a['status'].upper()}</div>
  </div>"""
        )
    st.markdown(f'<div class="kpi-grid">{"".join(kartu)}</div>', unsafe_allow_html=True)


def teks_bukti(k: Keluaran) -> str:
    """
    Teks satu keluaran: nilai beserta status buktinya, atau kalimat
    ketidaktersediaan.

    Keluaran yang tidak tersedia TIDAK diberi status bukti apa pun.
    """
    if not k.tersedia:
        return FRASA_TIDAK_TERSEDIA
    return f"{k.teks_nilai()}  ·  {k.status_bukti.value}"


def ringkasan_ketersediaan(st, judul: str, ringkas: dict) -> None:
    """Berapa keluaran yang tersedia, dan berapa di antaranya terukur."""
    st.metric(
        judul,
        f"{ringkas['tersedia']}/{ringkas['total']} keluaran",
        delta=f"{ringkas['terukur']} terukur",
        delta_color="normal" if ringkas["terukur"] else "off",
    )
