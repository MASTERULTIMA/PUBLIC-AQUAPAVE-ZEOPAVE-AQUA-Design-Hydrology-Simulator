"""
Tab Emisi CO₂ — neraca emisi dan efisiensi material.

PENYAJIAN SAJA. Neraca emisi dihitung SEKALI di `core/emisi.py`, sebelum tab
mana pun digambar, lalu dilewatkan ke sini sebagai hasil bersama (ADR-008).
Modul ini tidak pernah menghitung ulang neracanya sendiri: bila ia melakukannya,
Tab 5 dan Tab 6 dapat menampilkan angka yang berbeda untuk skenario yang sama.

STATUS BUKTI KELUARAN
---------------------
Neraca emisi berstatus **deterministik**: ia hasil aritmetika atas parameter
yang dipilih pengguna, bukan pengukuran. Faktor emisi semen berasal dari
pustaka; faktor lumpur IPAL masih asumsi, dan naskah tidak menyebutkannya.

Karena itu tidak ada klaim penghematan hasil uji laboratorium di tab ini —
barisnya sengaja dibiarkan bertuliskan "tidak tersedia".

SKOR SDG ADALAH PENILAIAN KUALITATIF TIM
----------------------------------------
Skala 0–100 pada grafik SDG bersifat komparatif dan tidak pernah diukur. Tidak
ada metodologi penskoran yang terdokumentasi, sehingga angkanya tidak boleh
dikutip sebagai temuan penelitian. Himpunan SDG-nya sendiri kanonik dan dibaca
dari `data/akses.py`, bukan ditulis ulang di sini.
"""

from __future__ import annotations

import plotly.graph_objects as go

from core import emisi
from data import akses

from .. import gaya

#: Skor keselarasan SDG — PENILAIAN KUALITATIF TIM, bukan hasil pengukuran.
#: Dikunci pada nomor SDG; himpunan nomornya sendiri berasal dari akses.
SKOR_SDG = {9: 85, 11: 75, 12: 70, 13: 65}

#: Nama singkat untuk sumbu grafik, mengikuti tampilan sebelumnya.
NAMA_SINGKAT_SDG = {
    9: "Industri &\nInfrastruktur",
    11: "Kota\nBerkelanjutan",
    12: "Konsumsi\nBertanggung Jawab",
    13: "Penanganan\nIklim",
}

WARNA_SDG = {9: "#FF6D00", 11: "#1976D2", 12: "#6A1B9A", 13: "#2E7D32"}

CATATAN_SDG = (
    "Skor keselarasan SDG di bawah adalah **penilaian kualitatif tim** "
    "pada skala komparatif 0–100, bukan hasil pengukuran maupun penilaian "
    "resmi terhadap indikator SDG. Set SDG yang dipakai (9, 11, 12, 13) "
    "mengikuti keputusan penulis 30 Agustus 2026."
)


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Membandingkan emisi karbon dioksida (CO₂) campuran biasa dengan campuran "
    "yang sebagian semennya diganti lumpur IPAL, memakai faktor emisi dan "
    "jumlah pengikat dari bilah sisi."
)


def render(st, hasil_co2: dict) -> None:
    """
    Gambar seluruh tab Emisi CO₂.

    `hasil_co2` — neraca emisi skenario aktif, hasil `core/emisi.neraca()` yang
    dihitung sekali sebelum tab mana pun digambar (ADR-008). Ia sudah memuat
    seluruh parameter masukannya (substitusi, total pengikat, kedua faktor
    emisi), sehingga tab ini TIDAK perlu objek skenario sama sekali.

    Kontraknya satu argumen; tidak ada ketergantungan pada tab lain maupun pada
    urutan eksekusi.
    """
    gaya.judul_bagian(st, "Emisi CO₂ & Efisiensi Material")
    gaya.pengantar(st, PENGANTAR)
    st.caption(
        "Kuantifikasi manfaat lingkungan dari substitusi lumpur IPAL "
        "dan optimasi material melalui platform AQUAPAVE."
    )

    e1, e2 = st.columns(2)
    with e1:
        _panel_parameter(st, hasil_co2)
    with e2:
        _panel_neraca(st, hasil_co2)

    st.divider()
    e3, e4 = st.columns(2)
    with e3:
        _grafik_perbandingan(st, hasil_co2)
    with e4:
        _grafik_sdg(st)

    _grafik_tren(st, hasil_co2)


# ─────────────────────────── parameter ───────────────────────────

def _panel_parameter(st, h: dict) -> None:
    """
    Parameter masukan neraca, dibaca dari hasil bersama.

    Sengaja TIDAK dibaca ulang dari objek skenario: hasil bersama sudah
    membawa nilai yang benar-benar dipakai perhitungan, sehingga mustahil
    tampil angka yang berbeda dari yang menghasilkan neraca di sebelahnya.
    """
    st.markdown("**Parameter Emisi**")
    st.metric("Substitusi IPAL", f"{h['substitusi_ipal_persen']:.0f}%")
    st.caption("Nilai kanonik dari bilah sisi — sama dengan Tab 1.")
    st.metric("Total pengikat", f"{h['total_pengikat_ton']:,.1f} ton")
    st.metric("Faktor emisi semen", f"{h['faktor_emisi_semen']:.2f} ton CO₂/ton")
    st.caption(
        "Faktor emisi dan total pengikat diatur di bilah sisi. "
        "Faktor semen berasal dari pustaka; faktor lumpur IPAL masih asumsi."
    )


def _panel_neraca(st, h: dict) -> None:
    """Neraca emisi. Baris klaim laboratorium sengaja tetap tidak tersedia."""
    st.markdown(f"""
        <div class="result-box2">
          <table style="width:100%;border-collapse:collapse">
            <tr><th style="text-align:left;color:#FFF">Indikator</th>
                <th style="text-align:right;color:#FFF">Nilai</th></tr>
            <tr><td>CO₂ — Konvensional (100% OPC)</td>
                <td style="text-align:right;color:#C62828;font-weight:700">{h['co2_konvensional_ton']:.2f} ton CO₂</td></tr>
            <tr><td>CO₂ — ZEOPAVE-AQUA</td>
                <td style="text-align:right;color:#388E3C;font-weight:700">{h['co2_zeopave_ton']:.2f} ton CO₂</td></tr>
            <tr><td>Reduksi Emisi CO₂</td>
                <td style="text-align:right;color:#00897B;font-weight:700">{h['co2_dihemat_ton']:.2f} ton ({h['reduksi_persen']:.1f}%)</td></tr>
            <tr><td>Lumpur IPAL Dialihkan dari TPA</td>
                <td style="text-align:right;font-weight:700">{h['ipal_terpakai_ton']:.2f} ton</td></tr>
            <tr><td>Klaim penghematan uji laboratorium</td>
                <td style="text-align:right;font-weight:700">tidak tersedia</td></tr>
          </table>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────── grafik ───────────────────────────

def _grafik_perbandingan(st, h: dict) -> None:
    """Emisi konvensional terhadap ZEOPAVE-AQUA pada substitusi saat ini."""
    sub = h["substitusi_ipal_persen"]
    fig = go.Figure(go.Bar(
        x=["Konvensional\n(100% OPC)", f"ZEOPAVE-AQUA\n({sub}% IPAL)"],
        y=[h["co2_konvensional_ton"], h["co2_zeopave_ton"]],
        marker_color=["#EF5350", "#66BB6A"],
        text=[f"{h['co2_konvensional_ton']:.2f} t",
              f"{h['co2_zeopave_ton']:.2f} t"],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Perbandingan Emisi CO₂<br><sup>Reduksi: {h['reduksi_persen']:.1f}%</sup>",
        height=320, yaxis_title="CO₂ (ton)",
        margin=dict(t=50, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")


def _grafik_sdg(st) -> None:
    """
    Keselarasan SDG — PENILAIAN KUALITATIF TIM.

    Himpunan SDG dibaca dari sumber kanonik agar tidak ada dua daftar yang
    dapat menyimpang. Skornya sendiri tetap penilaian tim dan tidak pernah
    berubah status menjadi hasil pengukuran.
    """
    st.caption(CATATAN_SDG)
    nomor = akses.sdg_didukung()
    label = [f"SDG {n}\n{NAMA_SINGKAT_SDG[n]}" for n in nomor]
    nilai = [SKOR_SDG[n] for n in nomor]

    fig = go.Figure(go.Bar(
        x=label, y=nilai,
        marker_color=[WARNA_SDG[n] for n in nomor],
        text=[f"{v}%" for v in nilai], textposition="outside",
    ))
    fig.update_layout(
        title="Keselarasan SDGs — penilaian kualitatif tim",
        height=320, yaxis_range=[0, 100], yaxis_title="Keselarasan (%)",
        margin=dict(t=50, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")


def _grafik_tren(st, h: dict) -> None:
    """Emisi total terhadap tingkat substitusi, dihitung core/emisi.py."""
    st.markdown("**Tren Reduksi CO₂ vs % Substitusi IPAL**")
    tren = emisi.tren_substitusi(
        h["total_pengikat_ton"], h["faktor_emisi_semen"],
        h["faktor_emisi_ipal"], maks_persen=25,
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[t[0] for t in tren], y=[t[1] for t in tren], mode="lines",
        fill="tozeroy", fillcolor="rgba(102,187,106,0.15)",
        line=dict(color="#388E3C", width=2.5),
    ))
    fig.add_vline(
        x=h["substitusi_ipal_persen"], line_dash="dash", line_color="#E65100",
        annotation_text=f"Saat ini: {h['substitusi_ipal_persen']}%",
    )
    fig.update_layout(
        title="Total Emisi CO₂ vs Substitusi IPAL",
        xaxis_title="Substitusi Lumpur IPAL (%)", yaxis_title="CO₂ (ton)",
        height=280, margin=dict(t=40, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")
