"""
Tab Efisiensi Biaya — estimasi indikatif.

STATUS ILMIAH: **bukan temuan penelitian.** Naskah DevICE tidak memuat bab
biaya sama sekali, sehingga tidak satu pun angka di tab ini memiliki sumber di
dalam penelitian. Seluruh keluarannya adalah skenario perhitungan atas harga
yang diasumsikan, dan tidak boleh disajikan sebagai temuan yang tervalidasi
secara eksperimental.

Klasifikasi itu dipasang di bagian paling atas tab dan tidak boleh dilepas.

PROVENANS HARGA (PRICE-01)
--------------------------
Keenam harga satuan berasal dari **tabel perhitungan biaya proyek
ZEOPAVE-AQUA** yang disusun tim sendiri. Tabel itu membuktikan satu hal dan
hanya satu hal: angka-angka inilah yang dipakai proyek dalam perhitungannya.

Ia TIDAK membuktikan harganya benar. Tabel itu tidak memuat kolom sumber,
tanggal, pemasok, maupun satuan asal, dan tidak disertai kuitansi, nota, atau
penawaran. Karena itu statusnya "masukan perhitungan proyek historis", bukan
harga pasar, bukan kutipan pemasok, bukan hasil survei.

Kuantitas pada tabel itu (substitusi lumpur IPAL 40%, f.a.b 0,20) adalah
formulasi LAMA yang sudah digantikan C-03. Yang tetap berlaku dari tabel itu
hanyalah kolom harganya.

ASUMSI YANG BELUM TERSELESAIKAN
-------------------------------
Persoalan berikut sudah diketahui dan sudah ditandai di antarmuka lewat panel
audit masukan serta pengungkapan di sisi tabel material:

  - satuan harga hebel belum terselesaikan: tabel historis mengenakannya per
    kilogram, keterangan pembelian penulis menyebut per batang. Massa satu
    batang tidak diketahui, sehingga konversinya tidak dihitung (PRICE-01);
  - keenam harga tidak pernah diverifikasi terhadap pemasok maupun pasar;
  - berat satuan beton poros berstatus ASUMSI OPERASIONAL SEMENTARA, bukan
    hasil pengukuran (SD-16C masih terbuka).

MODEL BIAYA (S7-H)
------------------
Objek biayanya **1 m² sistem ZEOPAVE-AQUA lengkap**, tersusun dua lapisan
dengan basis kuantitas yang berbeda dan ditangani berbeda:

  beton poros   1 m² × 2 cm → 0,02 m³ × berat satuan → massa → resep diskalakan
  lapisan retensi  hebel 6 kg/m² + zeolit 1 kg/m², dipakai APA ADANYA

Pengali `UNIT_PER_M2 = 14,75` **tidak lagi dipakai satu perhitungan pun**:
setelah kuantitas retensi ditetapkan per m², mengalikannya lagi berarti
penskalaan ganda.

KETERGANTUNGAN
--------------
Tab ini berdiri sendiri: satu-satunya nilai dari luar adalah luas area
perkerasan, dipakai sebagai NILAI AWAL kendali luas proyeknya sendiri. Ia
tidak membaca skenario aktif, tidak membaca hasil bersama, dan tidak
bergantung pada tab mana pun yang sudah digambar lebih dulu.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from core import komposisi

from .. import gaya
from ..components import evidence as komp_bukti

#: Status bukti yang melekat pada keenam harga. Sengaja TIDAK memakai kata
#: "asumsi": angkanya bukan karangan, melainkan catatan perhitungan proyek.
#: Sengaja pula tidak memakai kata "pasar": tidak ada yang memverifikasinya.
STATUS_HARGA = "MASUKAN PERHITUNGAN PROYEK HISTORIS"

#: Rentang tampilan minimum grafik sensitivitas, mempertahankan tampilan lama.
SENSITIVITAS_BATAS_MIN_PERSEN = 25.0

#: Margin tampilan agar penanda komposisi sekarang tidak menempel di tepi.
#: Semata-mata jarak gambar, bukan pernyataan ilmiah.
SENSITIVITAS_MARGIN_PERSEN = 5.0

#: Keanggotaan lapisan, keputusan penulis (S7-D). Menyatakan bahan mana
#: berada di lapisan mana — TIDAK menyatakan tebal, volume, maupun basis
#: kuantitas lapisan mana pun. Ketiganya belum ada buktinya.
LAPISAN_BETON = "Beton poros"
LAPISAN_RETENSI = "Media retensi"

#: Bahan beton poros, dipetakan ke kunci keluaran `rancangan_campuran()`.
#: Kuantitasnya TIDAK ditulis di sini: ia diturunkan dari campuran kanonik
#: §3.3 lewat `core/komposisi.py` (C-03). Yang tinggal di sini hanyalah harga,
#: yang memang asumsi dan memang masukan pengguna.
BAHAN_BETON = (
    {"no": 1, "nama": "Air", "kunci": "massa_air_kg", "harga": 4_000},
    {"no": 2, "nama": "Semen", "kunci": "massa_semen_kg", "harga": 1_500},
    {"no": 3, "nama": "Kerikil", "kunci": "massa_agregat_kg", "harga": 2_000},
    {"no": 4, "nama": "Limbah Lumpur IPAL", "kunci": "massa_ipal_kg", "harga": 0},
)

#: Bahan lapisan retensi, kuantitasnya keputusan penulis PER 1 m2 (S7-E).
#: Ia BUKAN bagian campuran beton, jadi tidak diturunkan dari `komposisi`.
BAHAN_RETENSI = (
    {"no": 5, "nama": "Hebel", "kg_per_m2": 6.0, "harga": 20_000},
    {"no": 6, "nama": "Zeolit", "kg_per_m2": 1.0, "harga": 10_000},
)


#: Kuantitas resep pada tabel biaya proyek historis.
#:
#: FORMULASI LAMA — substitusi lumpur IPAL 40% dan f.a.b 0,20 — yang sudah
#: DIGANTIKAN C-03. Disimpan sebagai catatan provenans yang dapat diperiksa,
#: dan TIDAK dibaca satu perhitungan biaya pun: kuantitas aktif seluruhnya
#: datang dari `core/komposisi.rancangan_campuran()` lewat `rancangan_beton()`.
KUANTITAS_TABEL_HISTORIS = {
    "Air": 0.2,
    "Semen": 0.6,
    "Kerikil": 3.0,
    "Limbah Lumpur IPAL": 0.4,
    "Hebel": 6.0,
    "Zeolit": 1.0,
}

#: Total yang tercatat pada tabel historis untuk satu unit ZEOPAVE-AQUA.
TOTAL_TABEL_HISTORIS = 137_700.0

def harga_satuan() -> dict:
    """
    Peta nama bahan ke harga satuannya, Rp per kg sebagaimana dipakai model.

    Satu-satunya tempat kedua kelompok bahan disatukan menjadi satu peta
    harga, sehingga nilai harganya tetap hidup di satu tempat saja.

    >>> harga_satuan()["Semen"]
    1500
    >>> len(harga_satuan())
    6
    """
    return {b["nama"]: b["harga"] for b in BAHAN_BETON + BAHAN_RETENSI}


def total_tabel_historis() -> float:
    """
    Hitung ulang total tabel biaya proyek historis dari harga yang dipakai.

    **Bukan bagian dari model biaya.** Tidak satu perhitungan pun memanggilnya.
    Ia bukti provenans yang dapat dieksekusi: selama keenam harga masih sama
    dengan yang dipakai tabel historis, totalnya kembali persis Rp 137.700.
    Bila kelak seseorang menggeser salah satu harga tanpa menyadari asalnya,
    kesamaan itu hilang dan ujinya gagal — provenansnya ikut gugur.

    Kuantitas yang dipakai di sini kuantitas TABEL LAMA, bukan campuran aktif.

    >>> total_tabel_historis()
    137700.0
    >>> total_tabel_historis() == TOTAL_TABEL_HISTORIS
    True
    """
    harga = harga_satuan()
    return float(sum(harga[n] * v for n, v in KUANTITAS_TABEL_HISTORIS.items()))


def material_bawaan() -> list[dict]:
    """
    Daftar bahan beserta kuantitas per 1 m2 sistem.

    Bahan beton poros diturunkan dari campuran kanonik §3.3; bahan retensi
    dipakai apa adanya. Tidak ada kuantitas campuran yang ditulis ulang di
    lapisan antarmuka (C-03).
    """
    r = rancangan_beton()
    beton = [
        {"no": b["no"], "nama": b["nama"], "vol": r[b["kunci"]], "satuan": "kg",
         "harga": b["harga"], "lapisan": LAPISAN_BETON}
        for b in BAHAN_BETON
    ]
    retensi = [
        {"no": b["no"], "nama": b["nama"], "vol": b["kg_per_m2"], "satuan": "kg",
         "harga": b["harga"], "lapisan": LAPISAN_RETENSI}
        for b in BAHAN_RETENSI
    ]
    return beton + retensi

#: Luas satuan objek biaya (keputusan penulis S7-E): 1 m2.
LUAS_SATUAN_M2 = 1.0

#: Tebal lapisan, keputusan penulis (S7-E).
TEBAL_BETON_M = 0.02
TEBAL_RETENSI_M = 0.075


@dataclass(frozen=True)
class AsumsiOperasional:
    """
    Nilai yang dipakai perhitungan tetapi **bukan** hasil pengukuran.

    Statusnya ikut ke mana pun nilainya dipakai, sehingga antarmuka tidak dapat
    menampilkannya tanpa menampilkan pula bahwa ia asumsi.
    """

    nilai: float
    satuan: str
    status: str
    catatan: str

    def label(self) -> str:
        return f"{self.nilai:,.0f} {self.satuan} — {self.status}"


#: SATU-SATUNYA tempat kerapatan beton poros hidup di dalam tab ini.
#:
#: Diizinkan penulis (S7-H) sebagai **asumsi operasional sementara** untuk
#: mengubah geometri 2 cm menjadi kuantitas bahan per m2. Ia BUKAN:
#: hasil pengukuran, kerapatan benda uji keras, hasil adukan segar terukur,
#: maupun sifat material ZEOPAVE yang sudah mapan.
#:
#: SD-16C tetap terbuka. Lihat register S7 untuk bukti yang akan menutupnya.
KERAPATAN_BETON_POROS = AsumsiOperasional(
    nilai=1850.0,
    satuan="kg/m³",
    status="asumsi operasional sementara",
    catatan=(
        "Diizinkan penulis untuk dipakai operasional, bukan hasil pengukuran "
        "pada formulasi beton poros ZEOPAVE. Naskah tidak menyebut berat "
        "satuan. Seluruh kuantitas dan biaya beton poros per m² bergantung "
        "pada angka ini; bila kelak diukur, semuanya ikut berubah."
    ),
)

#: Basis kuantitas tiap lapisan, keputusan penulis (S7-E).
#: Lapisan retensi: 6 kg hebel + 1 kg zeolit PER 1 m2 — langsung terpakai.
#: Beton poros: keempat bahannya PROPORSI PER 1 kg PENGIKAT, bukan massa per
#: m2. Diturunkan dari angkanya sendiri: semen 0,6 + IPAL 0,4 = 1,0 kg
#: pengikat, kerikil 3,0 = 3x pengikat, air 0,2 = 0,2x pengikat.
BASIS_PER_M2 = "per 1 m²"

#: TIDAK DIPAKAI LAGI sebagai pengali (S7-E).
#:
#: Angka ini dahulu mengubah "total per unit" menjadi "total per m2". Setelah
#: penulis menetapkan hebel 6 kg dan zeolit 1 kg PER 1 m2, mengalikannya lagi
#: dengan 14,75 berarti menghitung 88,5 kg hebel per m2 — penskalaan ganda.
#: Konstanta dipertahankan agar riwayatnya dapat ditelusuri, tetapi tidak lagi
#: dipakai satu perhitungan pun.
UNIT_PER_M2 = 14.75

#: Rantai perhitungan beton poros, ditampilkan apa adanya di antarmuka.
def rantai_beton() -> str:
    g = geometri_beton()
    r = rancangan_beton()
    return (
        f"{LUAS_SATUAN_M2:.0f} m² × {TEBAL_BETON_M*100:.0f} cm "
        f"= {g['volume_m3']:.2f} m³ "
        f"× {KERAPATAN_BETON_POROS.nilai:,.0f} {KERAPATAN_BETON_POROS.satuan} "
        f"= {g['massa_kg']:.0f} kg beton poros per m², dibagi menurut campuran "
        f"§3.3 (substitusi {r['substitusi_ipal_persen']:.0f}%, "
        f"f.a.b {r['faktor_air_pengikat']:.2f})"
    )

LEBAR_KOLOM = [0.5, 2.5, 1.2, 1.2, 1.8, 1.8]


#: Kegunaan tab ini dalam bahasa awam, untuk pembaca yang baru mengenalnya.
PENGANTAR = (
    "Memperkirakan biaya material sistem per meter persegi dari harga satuan "
    "yang dapat Anda ubah dan kuantitas campuran penelitian, lalu "
    "menghitung biaya proyek dan membandingkannya dengan perkerasan biasa."
)


def render(st, area_m2: float) -> None:
    """
    Gambar seluruh tab Efisiensi Biaya.

    `area_m2` — luas area perkerasan dari bilah sisi, dipakai HANYA sebagai
    nilai awal kendali "Luas Area Proyek" milik tab ini. Pengguna dapat
    menggesernya secara bebas setelahnya; tab tidak menuliskannya kembali ke
    skenario.

    Kontraknya satu skalar. Tab ini tidak membaca skenario aktif, tidak
    membaca hasil bersama, dan tidak bergantung pada urutan eksekusi tab.
    """
    gaya.judul_bagian(st, "Estimasi Biaya Pembuatan ZEOPAVE-AQUA")
    gaya.pengantar(st, PENGANTAR)

    baris_biaya = _masukan_material(st)
    hasil = biaya_lapisan(baris_biaya)
    _kartu_total(st, hasil)

    proyek = _estimasi_proyek(st, hasil, area_m2)
    _grafik(st, baris_biaya, proyek)
    _keuntungan_ipal(st, baris_biaya, proyek["luas_proyek"])
    _sensitivitas(st, baris_biaya, hasil)


# ─────────────────────── audit masukan ───────────────────────

# ─────────────────────── masukan material ───────────────────────

def _masukan_material(st) -> list[dict]:
    """Tabel harga satuan dan volume per unit, seluruhnya dapat disunting."""
    st.markdown("---")
    st.markdown("#### Harga Satuan & Kuantitas Material (per 1 m² sistem)")
    st.caption(
        "Kuantitas beton poros diturunkan dari rancangan campuran (substitusi "
        "lumpur IPAL 15%, air 0,40 per kg pengikat) pada volume 1 m² × 2 cm. "
        "**Harga dapat disunting**; kuantitas mengikuti rancangan campuran."
    )

    kepala = st.columns(LEBAR_KOLOM)
    for h, judul in zip(kepala, ["No", "Material", "Volume (kg)", "Satuan",
                                 "Harga Satuan (Rp)", "Jumlah (Rp)"]):
        h.markdown(f"**{judul}**")

    baris_biaya = []
    for m in material_bawaan():
        c0, c1, c2, c3, c4, c5 = st.columns(LEBAR_KOLOM)
        with c0:
            st.markdown(f"**{m['no']}**")
        with c1:
            nama = st.text_input(
                f"Nama {m['no']}", m["nama"],
                key=f"nama_{m['no']}", label_visibility="collapsed")
        with c2:
            # C-03: kuantitas adalah identitas campuran, bukan skenario
            # pengguna. Ia ditampilkan, bukan disunting.
            vol = m["vol"]
            st.markdown(
                f"<div style='padding-top:8px'>{vol:,.4f}</div>",
                unsafe_allow_html=True)
        with c3:
            satuan = st.text_input(
                f"Satuan {m['no']}", m["satuan"],
                key=f"satuan_{m['no']}", label_visibility="collapsed")
        with c4:
            harga = st.number_input(
                f"Harga {m['no']}", value=float(m["harga"]), min_value=0.0,
                step=500.0, key=f"harga_{m['no']}", label_visibility="collapsed",
                format="%.0f")
        subtotal = vol * harga
        with c5:
            st.markdown(
                f"<div style='padding-top:8px;font-weight:600'>Rp {subtotal:,.0f}</div>",
                unsafe_allow_html=True)
        baris_biaya.append({"nama": nama, "vol": vol, "satuan": satuan,
                            "harga": harga, "subtotal": subtotal,
                            "lapisan": m["lapisan"]})

    st.markdown("---")
    with st.expander("Tambah Material Lain"):
        ex_col = st.columns([2.5, 1.2, 1.8])
        with ex_col[0]:
            ex_nama = st.text_input("Nama Material", "Admixture")
        with ex_col[1]:
            ex_vol = st.number_input("Volume (kg)", 0.0, 100.0, 0.0, step=0.1)
        with ex_col[2]:
            ex_harga = st.number_input("Harga Satuan (Rp)", 0.0, 1_000_000.0, 0.0,
                                       step=500.0)
        if ex_vol > 0:
            baris_biaya.append({
                "nama": ex_nama, "vol": ex_vol, "satuan": "kg",
                "harga": ex_harga, "subtotal": ex_vol * ex_harga,
                # Lapisan bahan tambahan belum ditetapkan; jangan mengarangnya.
                "lapisan": None,
            })
    return baris_biaya


def geometri_beton() -> dict:
    """
    Volume dan massa lapisan beton poros untuk satu satuan luas.

    Rantainya eksplisit dan dapat diperiksa:
    luas × tebal → volume → × kerapatan → massa.

    Kerapatannya **asumsi operasional sementara**, bukan pengukuran.

    >>> g = geometri_beton()
    >>> g["volume_m3"], g["massa_kg"]
    (0.02, 37.0)
    """
    volume = LUAS_SATUAN_M2 * TEBAL_BETON_M
    return {
        "luas_m2": LUAS_SATUAN_M2,
        "tebal_m": TEBAL_BETON_M,
        "volume_m3": volume,
        "massa_kg": volume * KERAPATAN_BETON_POROS.nilai,
        "kerapatan": KERAPATAN_BETON_POROS,
    }


def rancangan_beton(substitusi_ipal_persen: float = None) -> dict:
    """
    Neraca massa beton poros untuk 1 m² setebal 2 cm, dari campuran kanonik.

    Seluruh kuantitasnya diturunkan `core/komposisi.rancangan_campuran()`,
    yang mengimplementasikan OUTPUT3 §3.3: pengikat : agregat = 1 : 3,
    substitusi lumpur IPAL 15%, air 0,40 per kg pengikat, tanpa pasir.

    C-03: Tab 7 dahulu memakai kuantitas yang tersirat substitusi 40% dan
    f.a.b 0,20 — campuran yang tidak pernah dicetak. Penulis menetapkan Tab 7
    mewakili campuran eksperimen §3.3, sehingga kuantitasnya kini dibaca dari
    sumber kanonik alih-alih ditulis ulang di sini.

    `substitusi_ipal_persen` hanya dipakai kurva sensitivitas; bawaannya
    mengikuti nilai kanonik.

    Kerapatannya tetap **asumsi operasional sementara** (SD-16C terbuka).
    Identitas campuran terselesaikan; basis penskalaannya belum.

    >>> r = rancangan_beton()
    >>> round(r["massa_total_kg"], 2), round(r["substitusi_ipal_persen"], 1)
    (37.0, 15.0)
    >>> round(r["massa_ipal_kg"], 4)
    1.2614
    """
    volume = geometri_beton()["volume_m3"]
    if substitusi_ipal_persen is None:
        return komposisi.rancangan_campuran(
            volume, berat_satuan_kg_m3=KERAPATAN_BETON_POROS.nilai)
    return komposisi.rancangan_campuran(
        volume, substitusi_ipal_persen=substitusi_ipal_persen,
        berat_satuan_kg_m3=KERAPATAN_BETON_POROS.nilai)


def biaya_lapisan(baris_biaya: list[dict]) -> dict:
    """
    Biaya tiap lapisan untuk 1 m² sistem, beserta basis kuantitasnya.

    **Dua basis yang berbeda, ditangani berbeda:**

    Lapisan retensi sudah berbasis per 1 m² (keputusan penulis: hebel 6 kg,
    zeolit 1 kg per m²), sehingga biayanya dipakai **apa adanya**. Ia TIDAK
    dikalikan faktor resep beton, dan tidak diturunkan dari tebal 7,5 cm —
    pembagian tebal itu antara hebel dan zeolit masih belum diketahui.

    Kuantitas beton poros **sudah** per m²: ia diturunkan campuran kanonik
    §3.3 pada volume 1 m² × 2 cm (C-03), sehingga tidak ada faktor penskalaan
    resep lagi. Kerapatannya tetap **asumsi operasional sementara**.

    >>> h = biaya_lapisan([
    ...     {"nama": "Semen", "vol": 7.1477, "harga": 1500.0, "lapisan": LAPISAN_BETON},
    ...     {"nama": "Hebel", "vol": 6.0, "harga": 20000.0, "lapisan": LAPISAN_RETENSI},
    ... ])
    >>> h["retensi_per_m2"]
    120000.0
    >>> round(h["beton_per_m2"], 2)
    10721.55
    """
    beton = [b for b in baris_biaya if b.get("lapisan") == LAPISAN_BETON]
    retensi = [b for b in baris_biaya if b.get("lapisan") == LAPISAN_RETENSI]
    lain = [b for b in baris_biaya if b.get("lapisan") not in
            (LAPISAN_BETON, LAPISAN_RETENSI)]

    beton_per_m2 = sum(b["vol"] * b["harga"] for b in beton)
    retensi_per_m2 = sum(b["vol"] * b["harga"] for b in retensi)

    return {
        # lapisan beton poros — sudah per m2, diturunkan campuran kanonik
        "beton_massa_per_m2_kg": sum(b["vol"] for b in beton),
        "beton_per_m2": beton_per_m2,
        "bahan_beton_per_m2": {b["nama"]: b["vol"] for b in beton},
        # lapisan retensi — sudah per m2, TIDAK diskalakan
        "retensi_per_m2": retensi_per_m2,
        "retensi_massa_per_m2_kg": sum(b["vol"] for b in retensi),
        # bahan tambahan pengguna: lapisannya belum ditetapkan, jadi tidak
        # diskalakan maupun dimasukkan ke total sistem.
        "tambahan": sum(b["vol"] * b["harga"] for b in lain),
        "sistem_per_m2": beton_per_m2 + retensi_per_m2,
        "kerapatan": KERAPATAN_BETON_POROS,
    }


def _kartu_total(st, hasil: dict) -> None:
    """Biaya per lapisan dan total sistem, seluruhnya per 1 m²."""
    st.markdown("---")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1B5E20,#388E3C);border-radius:12px;
                padding:22px 28px;color:white;margin-bottom:18px">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px">
        <div>
          <div style="font-size:0.85rem;opacity:0.8">Beton poros — {BASIS_PER_M2}</div>
          <div style="font-size:1.6rem;font-weight:700;margin-top:4px">Rp {hasil["beton_per_m2"]:,.2f}</div>
          <div style="font-size:0.75rem;opacity:0.75;margin-top:4px">
            tebal {TEBAL_BETON_M*100:.0f} cm · {hasil["beton_massa_per_m2_kg"]:.1f} kg/m²
          </div>
        </div>
        <div>
          <div style="font-size:0.85rem;opacity:0.8">Lapisan retensi — {BASIS_PER_M2}</div>
          <div style="font-size:1.6rem;font-weight:700;margin-top:4px">Rp {hasil["retensi_per_m2"]:,.2f}</div>
          <div style="font-size:0.75rem;opacity:0.75;margin-top:4px">
            {hasil["retensi_massa_per_m2_kg"]:.1f} kg/m² · tebal {TEBAL_RETENSI_M*100:.1f} cm
          </div>
        </div>
        <div>
          <div style="font-size:0.85rem;opacity:0.8">SISTEM LENGKAP — {BASIS_PER_M2}</div>
          <div style="font-size:1.6rem;font-weight:700;margin-top:4px">Rp {hasil["sistem_per_m2"]:,.2f}</div>
          <div style="font-size:0.75rem;opacity:0.75;margin-top:4px">
            beton poros + lapisan retensi
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Rantai perhitungan beton poros: " + rantai_beton())


# ─────────────────────── estimasi proyek ───────────────────────

def _estimasi_proyek(st, hasil: dict, area_m2: float) -> dict:
    """Biaya proyek, overhead, PPN, dan pembanding perkerasan konvensional."""
    st.markdown("#### Estimasi Biaya Proyek")
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        luas_proyek = st.number_input(
            "Luas Area Proyek (m²)", 10.0, 100_000.0, float(area_m2), step=50.0,
            help=("Luas perkerasan yang akan dibangun, dalam meter persegi "
                  "(10 sampai 100.000 m²). Nilai awalnya mengikuti luas area "
                  "di bilah sisi."))
    with bc2:
        overhead_pct = st.slider(
            "Overhead & Upah Kerja (%)", 0, 60, 20,
            help=("Tambahan di atas biaya material untuk upah dan biaya tak "
                  "langsung, sebagai persen dari biaya material (0 sampai "
                  "60%)."))
    with bc3:
        ppn_pct = st.slider(
            "PPN (%)", 0, 15, 11,
            help=("Pajak pertambahan nilai, sebagai persen dari biaya setelah "
                  "overhead (0 sampai 15%). Sesuaikan dengan tarif yang "
                  "berlaku untuk proyek Anda."))

    # S7-H: kedua lapisan kini berbasis per m2, jadi biaya material proyek
    # mencakup sistem lengkap.
    biaya_material = hasil["sistem_per_m2"] * luas_proyek
    biaya_overhead = biaya_material * (overhead_pct / 100)
    subtotal_biaya = biaya_material + biaya_overhead
    biaya_ppn = subtotal_biaya * (ppn_pct / 100)
    total_proyek = subtotal_biaya + biaya_ppn

    harga_konv_m2 = st.number_input(
        "Harga Perkerasan Konvensional / Aspal (Rp/m²) — Pembanding",
        100_000.0, 5_000_000.0, 450_000.0, step=10_000.0,
        help=("Harga pembanding per meter persegi untuk perkerasan biasa, "
              "dalam rupiah. Sesuaikan dengan harga di lokasi proyek."))
    total_konv = harga_konv_m2 * luas_proyek
    selisih_pct = ((total_proyek - total_konv) / total_konv * 100) if total_konv else 0.0

    st.dataframe(pd.DataFrame({
        "Komponen Biaya": [
            "Biaya Material — sistem lengkap",
            f"Overhead & Upah Kerja ({overhead_pct}%)",
            "Sub-Total",
            f"PPN ({ppn_pct}%)",
            "TOTAL PROYEK",
        ],
        "Jumlah (Rp)": [
            f"Rp {biaya_material:,.0f}",
            f"Rp {biaya_overhead:,.0f}",
            f"Rp {subtotal_biaya:,.0f}",
            f"Rp {biaya_ppn:,.0f}",
            f"Rp {total_proyek:,.0f}",
        ],
    }), width="stretch", hide_index=True)

    # C-08: aritmetikanya sah DI DALAM skenario, tetapi keunggulan ekonomi
    # nyata belum dibuktikan apa pun — harganya asumsi dan kerapatannya asumsi
    # operasional. Lencana karena itu tidak memakai penanda kelulusan dan
    # menyebut kedua ketergantungan itu.
    arah = "lebih mahal" if selisih_pct > 0 else "lebih murah"
    lencana = komp_bukti.lencana(
        f"{abs(selisih_pct):.1f}% {arah} dari pembanding",
        komp_bukti.PERINGATAN,
    )
    st.markdown(f"""
    <div style="margin:12px 0">
      {lencana}&nbsp;&nbsp;
      <span style="color:#555;font-size:0.88rem">
        (Konvensional: Rp {total_konv:,.0f} | ZEOPAVE-AQUA: Rp {total_proyek:,.0f})
      </span>
    </div>
    """, unsafe_allow_html=True)

    return {
        "luas_proyek": luas_proyek,
        "overhead_pct": overhead_pct,
        "ppn_pct": ppn_pct,
        "biaya_material": biaya_material,
        "biaya_overhead": biaya_overhead,
        "subtotal_biaya": subtotal_biaya,
        "biaya_ppn": biaya_ppn,
        "total_proyek": total_proyek,
    }


# ─────────────────────────── grafik ───────────────────────────

def _grafik(st, baris_biaya: list[dict], p: dict) -> None:
    """Komposisi biaya material dan rincian bertingkat biaya proyek."""
    st.divider()
    gc1, gc2 = st.columns(2)

    with gc1:
        label_pie = [b["nama"] for b in baris_biaya if b["subtotal"] > 0]
        nilai_pie = [b["subtotal"] for b in baris_biaya if b["subtotal"] > 0]
        fig = go.Figure(go.Pie(
            labels=label_pie, values=nilai_pie, hole=0.42,
            marker_colors=["#42A5F5", "#1565C0", "#E65100", "#00897B",
                           "#7B1FA2", "#F9A825"],
            textinfo="label+percent",
        ))
        fig.update_layout(
            title="Komposisi Biaya Material per Unit",
            height=340, margin=dict(t=50, b=10, l=10, r=10), showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")

    with gc2:
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "total", "relative", "total"],
            x=["Material", f"Overhead\n{p['overhead_pct']}%", "Sub-Total",
               f"PPN\n{p['ppn_pct']}%", "Total Proyek"],
            y=[p["biaya_material"], p["biaya_overhead"], 0, p["biaya_ppn"], 0],
            connector=dict(line=dict(color="#ccc")),
            increasing=dict(marker_color="#1565C0"),
            totals=dict(marker_color="#00897B"),
            text=[
                f"Rp {p['biaya_material']/1e6:.1f}M",
                f"Rp {p['biaya_overhead']/1e6:.1f}M",
                f"Rp {p['subtotal_biaya']/1e6:.1f}M",
                f"Rp {p['biaya_ppn']/1e6:.1f}M",
                f"Rp {p['total_proyek']/1e6:.1f}M",
            ],
            textposition="outside",
        ))
        fig.update_layout(
            title=f"Rincian Biaya Proyek {p['luas_proyek']:.0f} m²",
            height=340, yaxis_title="Biaya (Rp)",
            margin=dict(t=50, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, width="stretch")


# ─────────────────────── keuntungan IPAL ───────────────────────

def _cari_baris(baris_biaya: list[dict], kata: str):
    return next((b for b in baris_biaya if kata in b["nama"].lower()), None)


def _keuntungan_ipal(st, baris_biaya: list[dict],
                     luas_proyek: float) -> None:
    """
    Penghematan dari mengandaikan lumpur IPAL gratis.

    Kuantitas IPAL-nya datang dari baris tabel material, yang sejak C-03
    diturunkan dari campuran kanonik §3.3 — bukan lagi representasi kedua
    yang berdiri sendiri. Cadangannya pun membaca `rancangan_beton()`.

    Penghematannya SELISIH harga per kg pengikat yang digantikan, bukan harga
    semen saja (C-09).
    """
    st.markdown("#### Keuntungan Biaya dari Substitusi Semen oleh Lumpur IPAL")
    baris_ipal = _cari_baris(baris_biaya, "ipal")
    baris_semen = _cari_baris(baris_biaya, "semen")
    # C-03: cadangan kuantitas diambil dari campuran kanonik, bukan dari
    # literal sisa formulasi lama (0,4 kg adalah IPAL pada substitusi 40%).
    vol_ipal = (baris_ipal["vol"] if baris_ipal
                else rancangan_beton()["massa_ipal_kg"])
    harga_ipal = baris_ipal["harga"] if baris_ipal else 0.0
    harga_semen = baris_semen["harga"] if baris_semen else 1_500

    # C-09 (S7-B): penghematan adalah SELISIH harga per kg pengikat yang
    # digantikan. Versi sebelumnya memakai harga semen saja, sehingga angkanya
    # tidak bergerak ketika pengguna memberi harga pada lumpur IPAL. Dengan
    # harga IPAL bawaan Rp 0 kedua rumus memberi angka yang sama.
    # S7-H: kuantitas IPAL diturunkan dari geometri — resep IPAL dikalikan
    # faktor resep yang berasal dari volume 1 m2 x 2 cm dan kerapatan asumsi
    # operasional. Tidak ada pengali 14,75 di mana pun.
    ipal_per_m2 = vol_ipal
    ipal_proyek_kg = ipal_per_m2 * luas_proyek
    hemat_per_m2 = ipal_per_m2 * (harga_semen - harga_ipal)

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric(
            "Penghematan per m² (vs semen)", f"Rp {hemat_per_m2:,.0f}",
            delta=f"IPAL Rp {harga_ipal:,.0f}/kg vs semen Rp {harga_semen:,.0f}/kg",
        )
    with sc2:
        st.metric(f"Penghematan proyek {luas_proyek:,.0f} m²",
                  f"Rp {hemat_per_m2 * luas_proyek:,.0f}", delta="↓ biaya material")
    with sc3:
        st.metric("Lumpur IPAL terpakai", f"{ipal_proyek_kg:,.1f} kg",
                  delta=f"{ipal_per_m2:.2f} kg/m²")
    st.caption(
        f"Kuantitas lumpur IPAL diturunkan dari geometri: {rantai_beton()}. "
        "Lumpur IPAL menggantikan semen menurut massa, 1 kg per 1 kg."
    )


def kurva_sensitivitas(harga: dict, retensi_per_m2: float = 0.0) -> tuple:
    """
    Biaya sistem lengkap per m² terhadap tingkat substitusi lumpur IPAL.

    Tiap titik dihitung ulang lewat `core/komposisi.rancangan_campuran()` pada
    tingkat substitusi bersangkutan, sehingga **neraca massanya terjamin oleh
    model domain**, bukan oleh aritmetika yang diulang di sini. Total pengikat
    kekal secara struktural: `rancangan_campuran` membagi massa menurut rasio
    1 : agregat : f.a.b lalu memecah pengikat menurut substitusi.

    `harga` — Rp per kg, berkunci nama bahan.

    Yang bervariasi hanya beton poros; substitusi IPAL tidak menyentuh hebel
    maupun zeolit, sehingga biaya retensi masuk sebagai **tambahan tetap**.

    Penanda komposisi sekarang dijamin berada di dalam rentang sumbu (C-05A).

    RIWAYAT SATUAN. Sampai S7-D kurva dikalikan 14,75 dan dilabeli "per m²",
    padahal pengali itu tidak pernah terbukti. S7-E menurunkannya menjadi per
    kg pengikat; S7-H menaikkannya menjadi per m² setelah geometri ditetapkan.
    C-03 mengganti sumber kuantitasnya menjadi campuran kanonik §3.3.

    Kurva ini aritmetika skenario. Tidak satu pun titik di sepanjangnya pernah
    dicetak maupun diuji (ADR-009).

    >>> h = {"Air": 4000.0, "Semen": 1500.0, "Kerikil": 2000.0,
    ...      "Limbah Lumpur IPAL": 0.0}
    >>> pct, biaya, kini, batas = kurva_sensitivitas(h, retensi_per_m2=130000.0)
    >>> round(kini, 1), batas
    (15.0, 25.0)
    >>> round(biaya[15])
    204631
    """
    kini = rancangan_beton()["substitusi_ipal_persen"]
    batas_atas = max(
        SENSITIVITAS_BATAS_MIN_PERSEN,
        math.ceil(kini) + SENSITIVITAS_MARGIN_PERSEN,
    )
    pct_range = np.arange(0, batas_atas + 1, 1)
    biaya_range = []
    for p in pct_range:
        r = rancangan_beton(substitusi_ipal_persen=float(p))
        biaya_range.append(
            sum(r[b["kunci"]] * harga.get(b["nama"], 0.0) for b in BAHAN_BETON)
            + retensi_per_m2
        )
    return pct_range, biaya_range, kini, batas_atas


def _sensitivitas(st, baris_biaya: list[dict], hasil: dict) -> None:
    """Biaya material per m² terhadap tingkat substitusi IPAL."""
    st.markdown("#### Sensitivitas Biaya Sistem per m² vs % Substitusi IPAL")

    harga = {b["nama"]: b["harga"] for b in baris_biaya}
    pct_range, biaya_range, substitusi_kini, _ = kurva_sensitivitas(
        harga, retensi_per_m2=hasil["retensi_per_m2"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pct_range, y=biaya_range, mode="lines",
        fill="tozeroy", fillcolor="rgba(21,101,192,0.12)",
        line=dict(color="#1565C0", width=2.5), name="Biaya per m²",
    ))
    fig.add_vline(
        x=substitusi_kini, line_dash="dash", line_color="#E65100",
        annotation_text=f"Komposisi sekarang ({substitusi_kini:.0f}% IPAL)",
    )
    fig.update_layout(
        title="Biaya sistem per m² vs % Substitusi IPAL",
        xaxis_title="% Substitusi IPAL (dari total pengikat)",
        yaxis_title="Biaya sistem per m² (Rp)",
        height=300, margin=dict(t=50, b=10, l=10, r=10),
    )
    fig.update_yaxes(tickformat=",")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Hanya lapisan beton poros yang bervariasi; biaya lapisan retensi tetap."
    )
