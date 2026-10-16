"""
AQUAPAVE — akar komposisi.

Berkas ini MENYUSUN aplikasi; ia tidak mengimplementasikan apa pun. Sains
dihitung di core/, nilainya berasal dari data/akses.py yang membungkus
konstanta.py, ketersediaan diselesaikan scenario/resolusi.py, dan seluruh
penyajian hidup di ui/.

Yang tersisa di sini hanya sembilan hal: impor, konfigurasi halaman, lembar
gaya, bilah sisi, resolusi skenario, hasil bersama, pembuatan tab, panggilan
tiap tab, dan footer.

Tab pertama, Mulai di Sini, adalah pintu masuk bagi pengguna baru. Tujuh tab
sesudahnya adalah tab teknis; urutan dan isinya tidak berubah.

Satu-satunya modul produksi yang mengimpor Streamlit adalah berkas ini. Objek
`st` dilewatkan sebagai argumen ke setiap fungsi ui/.
"""

import streamlit as st

from core import emisi
from data import akses
from scenario import resolusi
from scenario.keluaran import OutputID
from ui import beranda, gaya, sidebar
from ui.tabs import biaya as tab_biaya
from ui.tabs import dasbor as tab_dasbor
from ui.tabs import emisi_co2 as tab_emisi_co2
from ui.tabs import kuat_tekan as tab_kuat_tekan
from ui.tabs import mix_design as tab_mix_design
from ui.tabs import mulai as tab_mulai
from ui.tabs import permeabilitas as tab_permeabilitas
from ui.tabs import retensi_air as tab_retensi_air
from ui.tabs import substitusi as tab_substitusi

# ─── Konfigurasi Halaman ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AQUAPAVE | Optimasi Desain",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Lembar Gaya ────────────────────────────────────────────────────────────────
gaya.pasang(st)


# ─── Bilah Sisi ──────────────────────────────────────────────────────────────────
# Menggambar seluruh kendali global dan mengembalikan parameter bersamanya.
PARAM = sidebar.render(st)
_sk = PARAM.skenario_aktif
area_m2 = PARAM.luas_area_m2
intensitas_hujan = PARAM.intensitas_hujan_mm_per_jam
target_fc_val = PARAM.target_fc_mpa

# ─── Beranda ─────────────────────────────────────────────────────────────────────
beranda.panji(st)
beranda.kartu_angka_kunci(st, akses.angka_kunci())

# ─── Resolusi Skenario ───────────────────────────────────────────────────────────
# SATU resolusi untuk seluruh aplikasi. Pandangan perbandingan dan tab
# membaca objek yang sama, sehingga keduanya mustahil menyatakan hal yang
# berbeda tentang konfigurasi yang sama (ADR-009, ADR-010).
_kolom_skenario = PARAM.koleksi.nama_terpakai()
_hasil = {n: resolusi.resolusi(PARAM.koleksi.ambil(n)) for n in _kolom_skenario}

beranda.perbandingan_skenario(
    st, _hasil, _kolom_skenario,
    {n: resolusi.ringkas_ketersediaan(_hasil[n]) for n in _kolom_skenario},
)

# ─── Hasil Bersama ───────────────────────────────────────────────────────────────
# Dihitung SEKALI, sebelum tab mana pun digambar. Tab 5 dan Tab 6 sama-sama
# membaca objek ini, sehingga tidak ada tab yang bergantung pada urutan
# eksekusi tab lain (ADR-008).
HASIL_CO2 = emisi.neraca(
    total_pengikat_ton=_sk.total_pengikat_ton,
    substitusi_ipal_persen=_sk.substitusi_ipal_persen,
    co2_per_ton_semen=_sk.co2_per_ton_semen,
    co2_per_ton_ipal=_sk.co2_per_ton_ipal,
)

# Keluaran skenario aktif berasal dari resolusi yang SAMA dengan pengisi tabel
# perbandingan di atas — bukan dihitung ulang dengan aturan sendiri.
HASIL_SKENARIO_AKTIF = _hasil[PARAM.koleksi.aktif]
KUAT_TEKAN_AKTIF = HASIL_SKENARIO_AKTIF[OutputID.COMPRESSIVE_STRENGTH]
RETENSI_AKTIF = HASIL_SKENARIO_AKTIF[OutputID.RETENTION]
AIR_TERTAHAN_AKTIF = HASIL_SKENARIO_AKTIF[OutputID.RUNOFF]


# ─── Tab ─────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "Mulai di Sini",
    "Kalkulator Mix Design",
    "Eksplorasi Kadar Substitusi",
    "Permeabilitas",
    "Kuat Tekan",
    "Retensi Air",
    "Emisi CO₂",
    "Dasbor Perbandingan",
    "Efisiensi Biaya",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB MULAI DI SINI   (badan tab: ui/tabs/mulai.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    tab_mulai.render(st, RETENSI_AKTIF, area_m2, intensitas_hujan)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — KALKULATOR MIX DESIGN   (badan tab: ui/tabs/mix_design.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    tab_mix_design.render(
        st, _sk.substitusi_ipal_persen, _sk.faktor_air_pengikat)


# ════════════════════════════════════════════════════════════════════════════════
# TAB EKSPLORASI KADAR SUBSTITUSI   (badan tab: ui/tabs/substitusi.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    tab_substitusi.render(st, _sk.co2_per_ton_semen, _sk.co2_per_ton_ipal)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — PERMEABILITAS   (badan tab: ui/tabs/permeabilitas.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    tab_permeabilitas.render(st)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — KUAT TEKAN   (badan tab: ui/tabs/kuat_tekan.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    tab_kuat_tekan.render(st, KUAT_TEKAN_AKTIF, target_fc_val)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — RETENSI AIR   (badan tab: ui/tabs/retensi_air.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    tab_retensi_air.render(st, RETENSI_AKTIF, area_m2, intensitas_hujan)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — EMISI CO₂   (badan tab: ui/tabs/emisi_co2.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    tab_emisi_co2.render(st, HASIL_CO2)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 6 — DASBOR PERBANDINGAN   (badan tab: ui/tabs/dasbor.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    tab_dasbor.render(st, RETENSI_AKTIF, AIR_TERTAHAN_AKTIF)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 7 — EFISIENSI BIAYA   (badan tab: ui/tabs/biaya.py)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    tab_biaya.render(st, area_m2)


# ─── Footer ─────────────────────────────────────────────────────────────────────
beranda.footer(st)
