"""
Tab Eksplorasi Kadar Substitusi — mengapa lumpur IPAL dipakai 15%.

Tab ini membandingkan enam kadar substitusi semen oleh lumpur IPAL, dari 0%
sampai 25%, dan menunjukkan alasan tim memilih 15%.

APA YANG DIHITUNG, APA YANG KUALITATIF
--------------------------------------
Dihitung (deterministik, oleh core/):
    - takaran semen, lumpur IPAL, batu sirtu, dan air per 1 m³ adukan pada
      setiap kadar — `core/komposisi.rancangan_campuran()`, dasar yang sama
      dengan tab Kalkulator Mix Design;
    - pengurangan emisi CO₂ terhadap campuran 100% semen —
      `core/emisi.reduksi_per_kadar()`, dengan faktor emisi skenario aktif.

Kualitatif (pertimbangan rancangan tim):
    - semakin banyak semen, permeabilitas semakin kecil;
    - semakin banyak lumpur IPAL, kuat tekan semakin kecil.

Kecenderungan itu SENGAJA ditampilkan sebagai arah relatif terhadap kadar
terpilih ("lebih tinggi", "lebih kecil"), bukan sebagai angka. Angka kuat tekan
dan permeabilitas hanya ditampilkan untuk kadar terpilih, yaitu nilai terukur
kanonik dari `data/akses.py`. Jangan menambahkan angka kinerja untuk kadar lain
tanpa data uji yang sesungguhnya — `validation/test_ui_substitusi.py` menjaga
batas ini.

PENYAJIAN SAJA. Tidak ada rumus di berkas ini.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core import emisi
from core import komposisi as kmp
from data import akses

from .. import gaya
from ..components import evidence as komp_bukti

#: Kadar substitusi yang dibandingkan, persen semen yang diganti lumpur IPAL.
KADAR = tuple(range(0, 30, 5))

#: Kecenderungan yang menjadi dasar pemilihan kadar.
KECENDERUNGAN = (
    ("Semakin banyak semen, permeabilitas semakin kecil.",
     "Pasta semen yang lebih banyak mengisi rongga beton poros, sehingga "
     "jalur air menyempit dan air lebih sulit meresap."),
    ("Semakin banyak lumpur IPAL, kuat tekan semakin kecil.",
     "Lumpur IPAL menggantikan sebagian semen sebagai pengikat utama, "
     "sehingga ikatan antarbutir agregat melemah."),
)

#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Membandingkan enam kadar substitusi semen oleh lumpur IPAL, dari 0% "
    "sampai 25%, dan menunjukkan mengapa 15% dipilih sebagai komposisi "
    "ZEOPAVE-AQUA."
)


def kadar_terpilih() -> float:
    """Kadar substitusi yang dipilih tim, dari besaran kanonik."""
    return float(akses.nilai("SUBSTITUSI_IPAL"))


def angka(nilai: float, desimal: int = 1) -> str:
    """
    Angka dengan pemisah Indonesia.

    >>> angka(1261.36, 1)
    '1.261,4'
    """
    teks = f"{nilai:,.{desimal}f}"
    return teks.replace(",", " ").replace(".", ",").replace(" ", ".")


def arah(kadar: float, terpilih: float) -> dict:
    """
    Posisi relatif sebuah kadar terhadap kadar terpilih.

    >>> arah(10, 15)["kuat_tekan"], arah(10, 15)["permeabilitas"]
    ('lebih tinggi', 'lebih kecil')
    >>> arah(20, 15)["kuat_tekan"], arah(20, 15)["permeabilitas"]
    ('lebih rendah', 'lebih besar')
    """
    if kadar < terpilih:
        return {"kuat_tekan": "lebih tinggi", "permeabilitas": "lebih kecil"}
    if kadar > terpilih:
        return {"kuat_tekan": "lebih rendah", "permeabilitas": "lebih besar"}
    return {"kuat_tekan": "terpilih", "permeabilitas": "terpilih"}


def baris_kadar(co2_per_ton_semen: float, co2_per_ton_ipal: float) -> list[dict]:
    """Takaran dan pengurangan CO₂ untuk setiap kadar, dihitung core/."""
    hasil = []
    reduksi = dict(emisi.reduksi_per_kadar(KADAR, co2_per_ton_semen, co2_per_ton_ipal))
    for p in KADAR:
        mix = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=float(p))
        hasil.append({
            "kadar": float(p),
            "semen_kg": mix["massa_semen_kg"],
            "ipal_kg": mix["massa_ipal_kg"],
            "agregat_kg": mix["massa_agregat_kg"],
            "air_kg": mix["massa_air_kg"],
            "reduksi_co2_persen": reduksi[float(p)],
        })
    return hasil


def render(st, co2_per_ton_semen: float, co2_per_ton_ipal: float) -> None:
    """
    Gambar tab Eksplorasi Kadar Substitusi.

    `co2_per_ton_semen` dan `co2_per_ton_ipal` — faktor emisi skenario aktif,
    sama dengan yang dipakai tab Emisi CO₂.
    """
    terpilih = kadar_terpilih()
    baris = baris_kadar(co2_per_ton_semen, co2_per_ton_ipal)

    gaya.judul_bagian(st, "Eksplorasi Kadar Substitusi Lumpur IPAL")
    gaya.pengantar(st, PENGANTAR)

    _kesimpulan(st, terpilih)
    _kecenderungan(st)
    _tabel(st, baris, terpilih)
    _grafik(st, baris, terpilih)
    _jelajah(st, baris, terpilih)


def _kesimpulan(st, terpilih: float) -> None:
    komp_bukti.kotak_hasil(
        st, f"{angka(terpilih, 0)}%",
        "kadar substitusi lumpur IPAL terpilih",
        "Titik keseimbangan antara kuat tekan, permeabilitas, dan "
        "pemanfaatan lumpur IPAL",
        rata_tengah=True,
    )
    kt = akses.besaran("KUAT_TEKAN_7_HARI")
    pm = akses.besaran("PERMEABILITAS")
    ambang = akses.besaran("AMBANG_LALU_LINTAS_RINGAN")
    st.markdown(
        f"Kadar substitusi lumpur IPAL divariasikan dari 0% sampai 25%. Kadar "
        f"{angka(terpilih, 0)}% memberi hasil paling seimbang, sehingga kadar "
        f"inilah yang dipilih untuk ZEOPAVE-AQUA."
    )
    st.markdown(
        f"- **Di bawah {angka(terpilih, 0)}% (0–10%)** — semen lebih banyak, "
        "sehingga permeabilitas lebih kecil dan air lebih sulit meresap. "
        "Lumpur IPAL yang termanfaatkan dan pengurangan CO₂ juga lebih "
        "sedikit.\n"
        f"- **Di atas {angka(terpilih, 0)}% (20–25%)** — lumpur IPAL lebih "
        "banyak, sehingga kuat tekan menurun.\n"
        f"- **Pada {angka(terpilih, 0)}%** — kuat tekan "
        f"**{angka(kt.nilai, 2)} {kt.satuan}** (umur 7 hari), di atas ambang "
        f"{angka(ambang.nilai, 0)} {ambang.satuan} untuk lalu lintas ringan, "
        f"dengan permeabilitas **{angka(pm.nilai, 3)} {pm.satuan}**, sambil "
        f"mengganti {angka(terpilih, 0)}% semen dengan lumpur IPAL."
    )


def _kecenderungan(st) -> None:
    gaya.judul_bagian(st, "Kecenderungan yang dipertimbangkan")
    kolom = st.columns(len(KECENDERUNGAN))
    for k, (judul, isi) in zip(kolom, KECENDERUNGAN):
        with k:
            st.markdown(f"**{judul}**")
            st.caption(isi)


def _tabel(st, baris: list[dict], terpilih: float) -> None:
    gaya.judul_bagian(st, "Perbandingan enam kadar substitusi")
    kt = akses.besaran("KUAT_TEKAN_7_HARI")
    pm = akses.besaran("PERMEABILITAS")
    data = []
    for b in baris:
        a = arah(b["kadar"], terpilih)
        pilih = abs(b["kadar"] - terpilih) < 1e-9
        data.append({
            "Kadar IPAL": f"{angka(b['kadar'], 0)}%" + (" (terpilih)" if pilih else ""),
            "Semen (kg/m³)": angka(b["semen_kg"]),
            "Lumpur IPAL (kg/m³)": angka(b["ipal_kg"]),
            "Pengurangan CO₂": f"{angka(b['reduksi_co2_persen'])}%",
            "Kuat tekan": (f"{angka(kt.nilai, 2)} {kt.satuan}" if pilih
                           else f"{a['kuat_tekan']} dari {angka(terpilih, 0)}%"),
            "Permeabilitas": (f"{angka(pm.nilai, 3)} {pm.satuan}" if pilih
                              else f"{a['permeabilitas']} dari {angka(terpilih, 0)}%"),
        })
    st.dataframe(pd.DataFrame(data), width="stretch", hide_index=True)
    st.caption(
        "Takaran per 1 m³ adukan, dengan dasar perhitungan yang sama seperti "
        "tab Kalkulator Mix Design: pengikat : batu sirtu = 1 : 3 dan faktor "
        "air-pengikat 0,40. Pengurangan CO₂ dibandingkan dengan campuran 100% "
        "semen, memakai faktor emisi skenario aktif."
    )


def _grafik(st, baris: list[dict], terpilih: float) -> None:
    label = [f"{angka(b['kadar'], 0)}%" for b in baris]
    pilih = [abs(b["kadar"] - terpilih) < 1e-9 for b in baris]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=label, y=[b["semen_kg"] for b in baris], name="Semen (kg/m³)",
        marker_color=["#0D47A1" if p else "#90A4AE" for p in pilih],
    ))
    fig.add_trace(go.Bar(
        x=label, y=[b["ipal_kg"] for b in baris], name="Lumpur IPAL (kg/m³)",
        marker_color=["#00897B" if p else "#B2DFDB" for p in pilih],
    ))
    fig.add_trace(go.Scatter(
        x=label, y=[b["reduksi_co2_persen"] for b in baris],
        name="Pengurangan CO₂ (%)", mode="lines+markers", yaxis="y2",
        line=dict(color="#E65100", width=3),
    ))
    fig.update_layout(
        barmode="stack", height=380,
        title="Takaran pengikat dan pengurangan CO₂ pada tiap kadar",
        xaxis=dict(title="Kadar substitusi lumpur IPAL", type="category"),
        yaxis=dict(title="kg per m³ adukan"),
        yaxis2=dict(title="Pengurangan CO₂ (%)", overlaying="y", side="right",
                    rangemode="tozero"),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=50, b=10, l=10, r=10),
        annotations=[dict(
            x=f"{angka(terpilih, 0)}%", y=1.0, yref="paper",
            text="Terpilih", showarrow=False, yanchor="bottom",
            font=dict(color="#0D47A1", size=13),
        )],
    )
    st.plotly_chart(fig, width="stretch", key="substitusi_grafik")


def _jelajah(st, baris: list[dict], terpilih: float) -> None:
    gaya.judul_bagian(st, "Jelajahi satu kadar")
    pilihan = [b["kadar"] for b in baris]
    kadar = st.select_slider(
        "Kadar substitusi lumpur IPAL (%)", options=pilihan, value=terpilih,
        format_func=lambda p: f"{angka(p, 0)}%", key="substitusi_jelajah",
        help=("Pilih kadar untuk melihat takaran bahannya per 1 m³ adukan "
              "dan kedudukannya dibandingkan kadar terpilih."),
    )
    b = next(x for x in baris if abs(x["kadar"] - kadar) < 1e-9)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Semen", f"{angka(b['semen_kg'])} kg")
    with k2:
        st.metric("Lumpur IPAL", f"{angka(b['ipal_kg'])} kg")
    with k3:
        st.metric("Batu sirtu", f"{angka(b['agregat_kg'])} kg")
    with k4:
        st.metric("Air", f"{angka(b['air_kg'])} kg")

    if abs(kadar - terpilih) < 1e-9:
        st.success(
            f"**{angka(terpilih, 0)}% — kadar terpilih.** Keseimbangan antara "
            "kuat tekan dan permeabilitas, dengan pengurangan CO₂ "
            f"{angka(b['reduksi_co2_persen'])}% dibanding campuran 100% semen."
        )
        return
    if kadar < terpilih:
        alasan = ("semen lebih banyak, sehingga kuat tekan lebih tinggi tetapi "
                  "permeabilitas lebih kecil dan air lebih sulit meresap.")
    else:
        alasan = ("lumpur IPAL lebih banyak, sehingga permeabilitas lebih "
                  "besar tetapi kuat tekan menurun.")
    st.info(
        f"**{angka(kadar, 0)}%** — dibanding kadar terpilih "
        f"{angka(terpilih, 0)}%, {alasan} Pengurangan CO₂ "
        f"{angka(b['reduksi_co2_persen'])}% dibanding campuran 100% semen."
    )
