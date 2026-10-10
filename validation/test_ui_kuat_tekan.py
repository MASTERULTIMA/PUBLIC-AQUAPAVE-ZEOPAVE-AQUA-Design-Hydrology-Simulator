"""
Uji antarmuka Tab 3 — Kuat Tekan (S5-3, dikoreksi S5-3.1).

Menjaga hasil utama penelitian, 13,19 MPa pada umur 7 hari, tetap menjadi
hasil utama: terukur langsung, melekat pada konfigurasi yang benar-benar
diuji, tidak tertimpa estimasi konversi umur, dan tidak digantikan model
prediksi apa pun.

Dua ketidaksesuaian yang ditemukan pada audit S5-3 telah ditutup pada S5-3.1,
sehingga uji yang dahulu berstatus `expectedFailure` kini uji biasa:

  1. Tab 3 kini memperoleh ketersediaan kuat tekan dari `scenario/resolusi.py`,
     resolusi yang sama dengan yang mengisi tabel perbandingan (ADR-010).
  2. Umur eksperimen kini berasal dari sumber kanonik (`UMUR_UJI_HARI`), bukan
     dari kendali antarmuka. Pemilih umur berubah menjadi pemilih umur TARGET
     estimasi, dan umur eksperimen dikeluarkan dari pilihannya.

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import ast
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import kuat_tekan as ktk  # noqa: E402
from data import akses  # noqa: E402
from scenario import state as skenario  # noqa: E402
from scenario.keluaran import FRASA_TIDAK_TERSEDIA  # noqa: E402
from ui.tabs import kuat_tekan as tab_ktk  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_TAB = os.path.join(AKAR, "ui", "tabs", "kuat_tekan.py")
TENGGAT = 60

HASIL_UTAMA_MPA = 13.19
UMUR_EKSPERIMEN = 7


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def widget(at, jenis: str, label: str):
    kel = getattr(at, jenis)
    cocok = [x for x in kel if getattr(x, "label", None) == label]
    if not cocok:
        raise AssertionError(
            f"{jenis} {label!r} tidak ada; yang ada: "
            f"{[getattr(x, 'label', '?') for x in kel]}"
        )
    return cocok[0]


def skenario_kustom(at, persen: float) -> AppTest:
    at.sidebar.button[0].click().run()
    [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(persen).run()
    return at


def geser_ipal(at, persen: float) -> AppTest:
    [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(persen).run()
    return at


# ── dua bagian Tab 3 yang sengaja dipisah ──

def kotak_skenario_aktif(at) -> str | None:
    """Kotak hasil skenario aktif, atau None bila hasilnya tidak tersedia."""
    cocok = [m.value for m in at.markdown if "Kuat tekan skenario aktif" in m.value]
    return cocok[0] if cocok else None


def peringatan_skenario_aktif(at) -> str | None:
    """Pernyataan ketidaktersediaan untuk skenario aktif."""
    cocok = [w.value for w in at.warning
             if FRASA_TIDAK_TERSEDIA in w.value and "Kuat tekan" in w.value]
    return cocok[0] if cocok else None


def fc_skenario_aktif(at) -> float:
    kotak = kotak_skenario_aktif(at)
    if kotak is None:
        raise AssertionError("hasil skenario aktif tidak digambar")
    return float(re.search(r'result-value">([\d.]+) MPa', kotak).group(1))


def umur_skenario_aktif(at) -> int:
    return int(re.search(r"pada umur (\d+) hari", kotak_skenario_aktif(at)).group(1))


def kotak_data_uji(at) -> str:
    """Kotak rerata data eksperimen konfigurasi acuan / kalkulator."""
    cocok = [m.value for m in at.markdown if "Rerata f'c" in m.value]
    if not cocok:
        raise AssertionError("kotak data eksperimen tidak digambar")
    return cocok[0]


def fc_data_uji(at) -> float:
    return float(re.search(r'result-value">([\d.]+) MPa', kotak_data_uji(at)).group(1))


def teks_estimasi(at) -> str:
    cocok = [m.value for m in at.markdown if "estimasi umur" in m.value]
    if not cocok:
        raise AssertionError("panel estimasi konversi umur tidak digambar")
    return cocok[0]


def tabel_benda_uji(at):
    for d in at.dataframe:
        if "Benda Uji" in d.value.columns:
            return d.value
    raise AssertionError("tabel benda uji tidak digambar")


def seluruh_teks(at) -> str:
    bagian = []
    for kelompok in (at.markdown, at.caption, at.info, at.warning,
                     at.success, at.error):
        bagian.extend(str(getattr(e, "value", "")) for e in kelompok)
    return "\n".join(bagian)


def sel_perbandingan(at, baris: str, kolom: str) -> str:
    df = at.dataframe[0].value
    return df[df["Keluaran"] == baris].iloc[0][kolom]


BARIS_KUAT_TEKAN = "Kuat tekan (7 hari)"


# ═══════════ UJI 1 — konfigurasi acuan penelitian ═══════════

class KonfigurasiAcuan(unittest.TestCase):
    """13,19 MPa, terukur, umur 7 hari, sebagai hasil utama."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_hasil_skenario_aktif_tersedia(self):
        self.assertIsNotNone(kotak_skenario_aktif(self.at))
        self.assertIsNone(peringatan_skenario_aktif(self.at))

    def test_hasil_utama_13_19_mpa(self):
        self.assertAlmostEqual(fc_skenario_aktif(self.at), HASIL_UTAMA_MPA, delta=0.01)

    def test_status_bukti_terukur(self):
        self.assertIn("terukur", kotak_skenario_aktif(self.at))

    def test_umur_eksperimen_7_hari(self):
        self.assertEqual(umur_skenario_aktif(self.at), UMUR_EKSPERIMEN)

    def test_ditandai_hasil_utama(self):
        kotak = kotak_skenario_aktif(self.at)
        self.assertIn("HASIL UTAMA", kotak)
        self.assertIn("pengukuran langsung, tanpa konversi umur", kotak)

    def test_provenansi_terlihat(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn(akses.besaran("KUAT_TEKAN_7_HARI").provenans(), seluruh_teks(self.at))
        self.assertIn(ktk.ambang_lalu_lintas_ringan()["sumber"], teks)

    def test_ambang_pustaka_bukan_target_bilah_sisi(self):
        """Pembandingnya 5 MPa dari Govedarica, bukan kelas target pengguna."""
        ambang = ktk.ambang_lalu_lintas_ringan()
        self.assertEqual(ambang["nilai"], 5.0)
        self.assertIn(f"{ambang['nilai']:.0f} MPa", kotak_skenario_aktif(self.at))

    def test_data_uji_bawaan_dari_sumber_kanonik(self):
        for i, b in enumerate(akses.dataset_kuat_tekan()):
            self.assertAlmostEqual(
                widget(self.at, "number_input", f"Beban P{i+1} (kN)").value,
                b["beban_kN"], delta=1e-9)
            self.assertAlmostEqual(
                widget(self.at, "number_input", f"Berat W{i+1} (kg)").value,
                b["berat_kg"], delta=1e-9)

    def test_nilai_layar_sama_dengan_hitungan_core(self):
        """Setiap f'c dihitung ulang mandiri lewat core/kuat_tekan.py."""
        luas = ktk.luas_silinder_m2(ktk.LAB_DIAMETER_MM)
        diharapkan = [
            ktk.kuat_tekan_mpa(b["beban_kN"], luas)
            for b in akses.dataset_kuat_tekan()
        ]
        tabel = tabel_benda_uji(self.at)
        kolom_fc = [k for k in tabel.columns if k.startswith("f'c @")][0]
        self.assertIn(f"@ {UMUR_EKSPERIMEN} hari", kolom_fc)
        for i, nilai in enumerate(diharapkan):
            self.assertAlmostEqual(float(tabel[kolom_fc].iloc[i]), round(nilai, 2),
                                   delta=0.01)
        self.assertAlmostEqual(
            fc_data_uji(self.at), ktk.ringkasan(diharapkan)["rerata"], delta=0.01)

    def test_sebaran_ditampilkan_bersama_rerata(self):
        self.assertIn("simpangan baku", kotak_data_uji(self.at))
        self.assertIn("CV", kotak_data_uji(self.at))

    def test_estimasi_tidak_menggantikan_hasil_utama(self):
        self.assertNotIn("15.00 MPa", kotak_skenario_aktif(self.at))
        self.assertAlmostEqual(fc_skenario_aktif(self.at), HASIL_UTAMA_MPA, delta=0.01)


# ═══════════ UJI 2 — komposisi kustom ═══════════

class SkenarioKustom(unittest.TestCase):
    """
    Komposisi yang belum diuji tidak boleh mewarisi hasil pengukuran —
    di tab, bukan hanya di tabel perbandingan.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = skenario_kustom(jalankan(), 22)

    def test_skenario_memang_menjadi_kustom(self):
        k = self.at.session_state[skenario.KUNCI]
        self.assertFalse(skenario.cocok_konfigurasi_uji(k.ambil("A")))

    def test_hasil_skenario_aktif_tidak_tersedia(self):
        """TEMUAN 1 DITUTUP: Tab 3 kini mengikuti pengikatan konfigurasi uji."""
        self.assertIsNone(
            kotak_skenario_aktif(self.at),
            "kotak hasil utama masih digambar untuk komposisi yang belum diuji",
        )
        self.assertIsNotNone(peringatan_skenario_aktif(self.at))
        self.assertIn(FRASA_TIDAK_TERSEDIA, peringatan_skenario_aktif(self.at))

    def test_tidak_ada_klaim_hasil_utama_untuk_komposisi_kustom(self):
        peringatan = peringatan_skenario_aktif(self.at)
        self.assertNotIn("HASIL UTAMA", peringatan)
        self.assertNotIn("13.19", peringatan)

    def test_tanpa_status_bukti_pada_keluaran_kosong(self):
        """"Belum tersedia" bukan kategori bukti sejajar "terukur" (ADR-009)."""
        peringatan = peringatan_skenario_aktif(self.at)
        for status in ("terukur", "deterministik", "literatur", "target", "asumsi"):
            self.assertNotIn(status, peringatan.lower())

    def test_alasan_ketidaktersediaan_dijelaskan(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("Substitusi lumpur IPAL", teks)
        self.assertIn("22", teks)

    def test_dinyatakan_tidak_ada_prediksi(self):
        self.assertIn(tab_ktk.PESAN_TANPA_PREDIKSI,
                      [c.value for c in self.at.caption])

    def test_tidak_ada_nol_atau_sel_kosong(self):
        peringatan = peringatan_skenario_aktif(self.at)
        self.assertNotIn("0.00", peringatan)
        self.assertNotEqual(peringatan.strip(), "")

    def test_perbandingan_menyatakan_belum_tersedia(self):
        """Pengaman ADR-009 pada tabel perbandingan tetap utuh."""
        self.assertEqual(
            sel_perbandingan(self.at, BARIS_KUAT_TEKAN, "Skenario A"),
            FRASA_TIDAK_TERSEDIA,
        )

    def test_tab_dan_tabel_sepakat(self):
        """Inti ADR-010: satu resolusi, sehingga keduanya mustahil berbeda."""
        tabel_kosong = (
            sel_perbandingan(self.at, BARIS_KUAT_TEKAN, "Skenario A")
            == FRASA_TIDAK_TERSEDIA
        )
        tab_kosong = kotak_skenario_aktif(self.at) is None
        self.assertEqual(tabel_kosong, tab_kosong)

    def test_acuan_tetap_terukur_di_tabel(self):
        sel = sel_perbandingan(self.at, BARIS_KUAT_TEKAN, "Acuan Penelitian")
        self.assertIn("13.19", sel)
        self.assertIn("terukur", sel)


# ═══════════ UJI 3 — data eksperimen acuan saat kustom aktif ═══════════

class DataEksperimenSaatKustomAktif(unittest.TestCase):
    """
    Data penelitian tetap dapat diperiksa, tetapi harus jelas miliknya siapa.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = skenario_kustom(jalankan(), 22)

    def test_data_eksperimen_tetap_dapat_diperiksa(self):
        self.assertAlmostEqual(fc_data_uji(self.at), HASIL_UTAMA_MPA, delta=0.01)
        self.assertEqual(len(tabel_benda_uji(self.at)), 3)

    def test_berlabel_milik_konfigurasi_acuan(self):
        teks = seluruh_teks(self.at)
        self.assertIn("Data Eksperimen Konfigurasi Acuan", teks)
        self.assertIn("DATA KONFIGURASI ACUAN", kotak_data_uji(self.at))
        self.assertIn("benda uji penelitian", kotak_data_uji(self.at))

    def test_dinyatakan_bukan_milik_skenario_aktif(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("bukan milik", teks)
        self.assertIn("skenario yang sedang aktif", teks)

    def test_tidak_mengklaim_hasil_utama(self):
        """Kotak data acuan tidak boleh menyamar sebagai hasil skenario aktif."""
        self.assertNotIn("HASIL UTAMA", kotak_data_uji(self.at))
        self.assertNotIn("skenario aktif", kotak_data_uji(self.at))

    def test_kendali_terkunci_pada_mode_data_penelitian(self):
        for label in ("Diameter Silinder (mm)", "Jumlah Benda Uji",
                      "Beban P1 (kN)", "Berat W1 (kg)"):
            self.assertTrue(
                widget(self.at, "number_input", label).disabled,
                f"{label} harus terkunci saat memakai data penelitian",
            )

    def test_kalkulator_bebas_berhenti_menyebut_hasil_penelitian(self):
        at = skenario_kustom(jalankan(), 22)
        widget(at, "toggle", "Pakai data uji penelitian").set_value(False).run()
        widget(at, "number_input", "Beban P1 (kN)").set_value(100.0).run()
        kotak = kotak_data_uji(at)
        self.assertIn("HITUNGAN ANDA", kotak)
        self.assertNotIn("benda uji penelitian", kotak)
        self.assertNotIn("terukur", kotak)


# ═══════════ UJI 4 — identitas dipulihkan ═══════════

class IdentitasDipulihkan(unittest.TestCase):
    """Bug identitas widget S5-0 tidak boleh kembali."""

    @classmethod
    def setUpClass(cls):
        at = skenario_kustom(jalankan(), 22)
        cls.saat_berbeda_tabel = sel_perbandingan(at, BARIS_KUAT_TEKAN, "Skenario A")
        cls.saat_berbeda_tab = kotak_skenario_aktif(at)
        cls.at = geser_ipal(at, int(skenario.ACUAN_SUBSTITUSI_IPAL))

    def test_sempat_tidak_tersedia(self):
        self.assertEqual(self.saat_berbeda_tabel, FRASA_TIDAK_TERSEDIA)
        self.assertIsNone(self.saat_berbeda_tab)

    def test_identitas_pulih(self):
        k = self.at.session_state[skenario.KUNCI]
        self.assertTrue(skenario.cocok_konfigurasi_uji(k.ambil("A")))

    def test_hasil_ukur_kembali_tersedia_di_tabel(self):
        sel = sel_perbandingan(self.at, BARIS_KUAT_TEKAN, "Skenario A")
        self.assertIn("13.19", sel)
        self.assertIn("terukur", sel)

    def test_hasil_ukur_kembali_tersedia_di_tab(self):
        self.assertIsNotNone(kotak_skenario_aktif(self.at))
        self.assertAlmostEqual(fc_skenario_aktif(self.at), HASIL_UTAMA_MPA, delta=0.01)
        self.assertEqual(umur_skenario_aktif(self.at), UMUR_EKSPERIMEN)
        self.assertIn("terukur", kotak_skenario_aktif(self.at))


# ═══════════ UJI 5 & 6 — umur eksperimen vs umur target ═══════════

class UmurEksperimenDanTarget(unittest.TestCase):
    """
    TEMUAN 2 DITUTUP. Umur eksperimen adalah fakta kanonik; yang dapat dipilih
    pengguna hanyalah umur TARGET estimasi.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_umur_eksperimen_dari_sumber_kanonik(self):
        self.assertEqual(tab_ktk.umur_uji_hari(), int(akses.nilai("UMUR_UJI_HARI")))
        self.assertEqual(tab_ktk.umur_uji_hari(), ktk.LAB_UMUR_HARI)
        self.assertEqual(umur_skenario_aktif(self.at), UMUR_EKSPERIMEN)

    def test_tidak_ada_pemilih_umur_eksperimen(self):
        """Umur eksperimen bukan pilihan antarmuka."""
        label = [s.label for s in self.at.selectbox]
        self.assertNotIn("Umur Pengujian (hari)", label)
        self.assertIn("Target umur estimasi (hari)", label)

    def test_umur_eksperimen_disebutkan_dengan_sumbernya(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn(f"Diuji pada umur {UMUR_EKSPERIMEN} hari", teks)
        self.assertIn(akses.besaran("UMUR_UJI_HARI").sumber, teks)

    def test_mengubah_target_tidak_mengubah_hasil_utama(self):
        for target in ("21", "28", "90"):
            at = jalankan()
            widget(at, "selectbox", "Target umur estimasi (hari)").set_value(
                target).run()
            self.assertAlmostEqual(
                fc_skenario_aktif(at), HASIL_UTAMA_MPA, delta=0.01,
                msg=f"hasil utama berubah saat target {target} hari dipilih")
            self.assertEqual(umur_skenario_aktif(at), UMUR_EKSPERIMEN)
            self.assertIn(f"estimasi umur {target} hari", teks_estimasi(at))

    def test_hanya_bagian_estimasi_yang_berubah(self):
        at28 = jalankan()
        widget(at28, "selectbox", "Target umur estimasi (hari)").set_value("28").run()
        self.assertEqual(kotak_skenario_aktif(at28), kotak_skenario_aktif(self.at))
        self.assertEqual(kotak_data_uji(at28), kotak_data_uji(self.at))
        self.assertNotEqual(teks_estimasi(at28), teks_estimasi(self.at))


# ═══════════ UJI 7 — kasus umur sama ═══════════

class KasusUmurSama(unittest.TestCase):
    """
    Umur eksperimen tidak boleh menjadi target estimasi: untuk umur itu sudah
    ada hasil pengukuran, sehingga estimasinya hanya akan menghasilkan angka
    yang bersaing dengan nilai terukur.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_umur_eksperimen_bukan_pilihan_target(self):
        opsi = widget(self.at, "selectbox", "Target umur estimasi (hari)").options
        self.assertNotIn(str(UMUR_EKSPERIMEN), opsi)
        self.assertNotIn(UMUR_EKSPERIMEN, tab_ktk.umur_target_tersedia())

    def test_target_lain_tetap_tersedia(self):
        self.assertEqual(tab_ktk.umur_target_tersedia(), [14, 21, 28, 56, 90])

    def test_alasan_pengecualian_dijelaskan(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn(f"Umur {UMUR_EKSPERIMEN} hari tidak ada di daftar target", teks)
        self.assertIn("sudah\nada hasil pengukuran".replace("\n", " "), teks)

    def test_angka_menyesatkan_tidak_muncul(self):
        """13,19 / 0,65 = 20,29 MPa tidak boleh muncul sebagai estimasi 7 hari."""
        self.assertNotIn("20.29", seluruh_teks(self.at))

    def test_penskalaan_umur_sama_akan_mengembalikan_nilai_terukur(self):
        """
        Andaikan umur eksperimen dipaksa menjadi target, modelnya memberi
        kembali nilai terukur — bukan angka baru. Pengecualian di antarmuka
        adalah pengaman kedua, bukan penutup kekeliruan aritmetika.
        """
        umur = tab_ktk.umur_uji_hari()
        f = tab_ktk.FAKTOR_UMUR
        self.assertAlmostEqual(
            HASIL_UTAMA_MPA / f[umur] * f[umur], HASIL_UTAMA_MPA, delta=1e-9)


# ═══════════ UJI 8 — estimasi tetap sekunder, tanpa model prediksi ═══════════

class EstimasiTetapSekunder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_disembunyikan_di_panel_terpisah(self):
        self.assertNotIn("estimasi umur", kotak_skenario_aktif(self.at))
        self.assertNotIn("estimasi umur", kotak_data_uji(self.at))
        self.assertIn("estimasi umur", teks_estimasi(self.at))

    def test_berlabel_estimasi(self):
        self.assertIn("ESTIMASI", teks_estimasi(self.at))
        self.assertNotIn("terukur pada umur 14", teks_estimasi(self.at))

    def test_diberi_peringatan_provenansi(self):
        teks = "\n".join(w.value for w in self.at.warning)
        self.assertIn("belum tertelusuri", teks)
        self.assertIn("ADR-005", teks)
        self.assertIn("ESTIMASI", teks)

    def test_dinyatakan_bukan_hasil_pengukuran(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("tidak dipakai di mana pun sebagai hasil", teks)
        self.assertIn("tidak menimpa nilai terukur", teks)

    def test_estimasi_14_hari_tetap_berstatus_asumsi(self):
        self.assertEqual(akses.status("KUAT_TEKAN_14_HARI"), akses.ASUMSI)
        kunci = {a["nama"] for a in akses.angka_kunci()}
        self.assertNotIn("KUAT_TEKAN_14_HARI", kunci)
        self.assertIn("KUAT_TEKAN_7_HARI", kunci)

    def test_selisih_terhadap_catatan_naskah_ditampilkan(self):
        """
        Naskah mencatat 15,00 MPa pada 14 hari; penskalaan memberi angka lain.
        Selisih itu bukti provenansi faktor belum selesai, jadi ditampilkan.
        """
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("naskah mencatat 15.00 MPa", teks)
        self.assertIn("belum", teks)

    def test_faktor_umur_tinggal_di_lapisan_tampilan(self):
        self.assertIn(7, tab_ktk.FAKTOR_UMUR)
        self.assertFalse(hasattr(ktk, "FAKTOR_UMUR"))

    def test_core_tidak_menyediakan_konversi_maupun_prediksi(self):
        for nama in dir(ktk):
            self.assertNotIn("konversi", nama.lower())
            self.assertNotIn("prediksi", nama.lower())
            self.assertNotIn("predict", nama.lower())

    def test_tidak_ada_prediksi_dari_komposisi(self):
        """
        Menggeser substitusi tidak boleh menghasilkan kuat tekan yang berbeda:
        kalau berubah, sebuah model prediksi telah lahir diam-diam.
        """
        at = skenario_kustom(jalankan(), 22)
        self.assertAlmostEqual(fc_data_uji(at), fc_data_uji(self.at), delta=1e-9)
        self.assertIsNone(kotak_skenario_aktif(at))


# ═══════════ batas arsitektur ═══════════

class BatasArsitektur(unittest.TestCase):
    """Modul tab menyajikan; core/ menghitung; scenario/ memutuskan ketersediaan."""

    def _sumber(self) -> str:
        with open(BERKAS_TAB, encoding="utf8") as f:
            return f.read()

    def _impor(self) -> set:
        """Jalur modul lengkap yang diimpor, bukan hanya paket teratasnya."""
        jalur = set()
        for simpul in ast.walk(ast.parse(self._sumber(), filename=BERKAS_TAB)):
            if isinstance(simpul, ast.Import):
                jalur.update(a.name for a in simpul.names)
            elif isinstance(simpul, ast.ImportFrom) and simpul.module:
                jalur.add(simpul.module)
        return jalur

    def test_tidak_mengimpor_streamlit(self):
        self.assertNotIn("streamlit", {j.split(".")[0] for j in self._impor()})

    def test_memakai_core_dan_data_kanonik(self):
        self.assertIn("core", {j.split(".")[0] for j in self._impor()})
        self.assertIn("data", {j.split(".")[0] for j in self._impor()})

    def test_membaca_model_keluaran_tanpa_menyelesaikannya_sendiri(self):
        """
        Tab boleh mengenal TIPE keluaran, tetapi tidak boleh menyelesaikan
        ketersediaannya sendiri: resolusi tetap satu, di lapisan skenario.
        """
        impor = self._impor()
        self.assertIn("scenario.keluaran", impor)
        self.assertNotIn("scenario.resolusi", impor)
        self.assertNotIn("scenario.state", impor)

    def test_tidak_menduplikasi_aturan_identitas_konfigurasi(self):
        sumber = self._sumber()
        for terlarang in ("cocok_konfigurasi_uji", "substitusi_ipal_persen",
                          "alasan_berbeda", "PARAMETER_KONFIGURASI_UJI"):
            self.assertNotIn(
                terlarang, sumber,
                f"aturan ADR-009 tergandakan di lapisan tampilan: {terlarang}",
            )

    def test_kontrak_render(self):
        for simpul in ast.walk(ast.parse(self._sumber(), filename=BERKAS_TAB)):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                self.assertEqual(
                    [a.arg for a in simpul.args.args],
                    ["st", "kuat_tekan_aktif", "target_fc_mpa"],
                    "kontrak Tab 3 harus tetap minimal dan eksplisit",
                )
                return
        self.fail("fungsi render() tidak ditemukan")

    def test_rumus_kuat_tekan_tidak_tergandakan(self):
        sumber = self._sumber()
        self.assertNotIn("math", {j.split(".")[0] for j in self._impor()})
        for pola in ("math.pi", "1e6", "1000.0", "/ 2.0) ** 2"):
            self.assertNotIn(pola, sumber, f"rumus core tergandakan: {pola}")
        for wajib in ("ktk.luas_silinder_m2", "ktk.kuat_tekan_mpa", "ktk.ringkasan"):
            self.assertIn(wajib, sumber, f"{wajib} seharusnya dipanggil dari core/")

    def test_aquapave_hanya_mengorkestrasi(self):
        with open(BERKAS_APLIKASI, encoding="utf8") as f:
            isi = f.read()
        self.assertIn(
            "tab_kuat_tekan.render(st, KUAT_TEKAN_AKTIF, target_fc_val)", isi)
        for sisa in ("FAKTOR_UMUR", "luas_silinder_m2", "kuat_tekan_mpa",
                     "Jumlah Benda Uji", "Beban P"):
            self.assertNotIn(sisa, isi, f"sisa Tab 3 tertinggal di AQUAPAVE.py: {sisa}")

    def test_keluaran_dibagikan_dari_resolusi_yang_sama(self):
        """
        AQUAPAVE.py mengambil keluaran skenario aktif dari resolusi yang sama
        dengan yang mengisi tabel perbandingan (ADR-008 + ADR-010).
        """
        with open(BERKAS_APLIKASI, encoding="utf8") as f:
            isi = f.read()
        self.assertIn("HASIL_SKENARIO_AKTIF = _hasil[", isi)
        self.assertIn(
            "KUAT_TEKAN_AKTIF = HASIL_SKENARIO_AKTIF[OutputID.COMPRESSIVE_STRENGTH]",
            isi)

    def test_target_bilah_sisi_sampai_ke_tab(self):
        at = jalankan()
        widget(at, "selectbox", "Kelas Kuat Tekan Target").set_value("f'c 20 MPa").run()
        self.assertEqual(list(at.exception), [])
        self.assertAlmostEqual(fc_skenario_aktif(at), HASIL_UTAMA_MPA, delta=0.01)


# ═══════════ SD-16B: faktor umur tanpa atribusi standar ═══════════

class FaktorUmurTanpaAtribusiStandar(unittest.TestCase):
    """
    SD-16B. Tabel faktor umur pernah berjudul "Faktor Konversi Umur (SNI)".

    Tidak ada satu pun catatan proyek yang menautkannya ke SNI: besaran
    kanoniknya berstatus ASUMSI dengan catatan bahwa naskah tidak menyitir
    sumber mana pun, dan tab ini sendiri menyatakan provenansinya belum
    tertelusuri. Label itu adalah klaim yang dibantah aplikasinya sendiri.

    Yang dijaga di sini INVARIANNYA, bukan kalimatnya: tabel faktor umur tidak
    boleh membawa atribusi standar, dan status buktinya wajib ikut tampil.
    PBI 1971 juga tidak boleh naik pangkat menjadi sumber — ADR-005
    mencatatnya sebagai kemiripan angka, bukan sitasi.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    #: Nama standar yang tidak boleh muncul sebagai sumber tabel faktor umur.
    STANDAR = ("SNI", "PBI", "ASTM", "ACI", "BS ", "EN ")

    def _teks_sekitar_tabel(self) -> str:
        """Judul dan keterangan yang menemani tabel faktor umur."""
        potong = [str(getattr(e, "value", "")) for e in self.at.markdown
                  if "Faktor Konversi Umur" in str(getattr(e, "value", ""))]
        self.assertEqual(len(potong), 1, "judul tabel faktor umur tidak tunggal")
        return potong[0]

    def test_judul_tabel_tanpa_atribusi_standar(self):
        judul = self._teks_sekitar_tabel()
        for nama in self.STANDAR:
            self.assertNotIn(
                nama, judul,
                f"atribusi tanpa dasar kembali ke judul tabel faktor umur: {nama}")

    def test_status_bukti_menemani_tabel(self):
        """
        Tabel digambar di luar panel estimasi yang terlipat, jadi peringatan
        di dalam panel itu tidak menemaninya. Statusnya wajib ada di sisinya.
        """
        keterangan = [str(getattr(e, "value", "")) for e in self.at.caption]
        self.assertIn(tab_ktk.CATATAN_FAKTOR_UMUR, keterangan)

    def test_status_memakai_taksonomi_bukti_repositori(self):
        c = tab_ktk.CATATAN_FAKTOR_UMUR.lower()
        self.assertIn("asumsi", c)
        self.assertIn("belum", c)
        self.assertIn("tertelusuri", c)
        # Kemiripan boleh disebut; sitasi tidak.
        self.assertIn("tidak menyitirnya", c)

    def test_pbi_tidak_naik_pangkat_menjadi_sumber(self):
        """
        PBI boleh disebut sebagai kemiripan, tetapi tidak boleh muncul sebagai
        sumber, standar acuan, atau dasar tabel.
        """
        c = tab_ktk.CATATAN_FAKTOR_UMUR.lower()
        for klaim in ("berdasarkan pbi", "sesuai pbi", "mengacu pbi",
                      "sumber: pbi", "menurut pbi"):
            self.assertNotIn(klaim, c)

    def test_besaran_kanonik_tetap_asumsi(self):
        """Statusnya tidak boleh naik menjadi literatur karena label dicabut."""
        self.assertEqual(akses.status("FAKTOR_KONVERSI_7_KE_14"), akses.ASUMSI)

    def test_nilai_faktor_tidak_bergeser(self):
        """Mencabut atribusi bukan alasan mengubah angka."""
        self.assertEqual(
            tab_ktk.FAKTOR_UMUR,
            {7: 0.65, 14: 0.879, 21: 0.95, 28: 1.00, 56: 1.09, 90: 1.15})

    def test_judul_tab_boleh_menyebut_sni_1974(self):
        """
        Pembedaan yang menentukan: SNI 1974:2011 adalah standar UJI KUAT
        TEKAN (f'c = P/A) dan memang tercatat di proyek. Yang tidak bersumber
        hanyalah tabel faktor umurnya. Uji ini menjaga agar pencabutan atribusi
        tidak melebar dan menghapus sitasi yang sah.
        """
        self.assertIn("SNI 1974:2011", seluruh_teks(self.at))


if __name__ == "__main__":
    unittest.main(verbosity=2)
