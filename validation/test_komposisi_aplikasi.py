"""
Uji akar komposisi (S5-7).

Setelah seluruh tab dan prolog diekstraksi, AQUAPAVE.py hanya MENYUSUN
aplikasi. Berkas ini menjaga susunan itu tetap benar: satu resolusi, satu
neraca emisi, satu tempat yang mengimpor Streamlit, dan tidak ada
implementasi yang menyelinap kembali.

Uji di sini melengkapi validation/test_ui.py, yang menjaga perilaku ilmiahnya.
Yang dijaga di sini adalah BENTUK susunannya.

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import ast
import os
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from streamlit.testing.v1 import AppTest  # noqa: E402

from scenario import state as skenario  # noqa: E402
from scenario.keluaran import FRASA_TIDAK_TERSEDIA  # noqa: E402
from ui import sidebar  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
DIR_UI = os.path.join(AKAR, "ui")
TENGGAT = 60

MODUL_TAB = ("mulai", "permeabilitas", "kuat_tekan", "retensi_air",
             "emisi_co2", "dasbor", "biaya", "mix_design")

#: Satu tab pembuka (Mulai di Sini) ditambah tujuh tab teknis.
JUMLAH_TAB = len(MODUL_TAB)


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def sumber(berkas: str) -> str:
    with open(berkas, encoding="utf8") as f:
        return f.read()


def pohon(berkas: str) -> ast.Module:
    return ast.parse(sumber(berkas), filename=berkas)


def impor(berkas: str) -> set:
    """Jalur modul lengkap yang benar-benar diimpor, dibaca dari AST."""
    jalur = set()
    for simpul in ast.walk(pohon(berkas)):
        if isinstance(simpul, ast.Import):
            jalur.update(a.name for a in simpul.names)
        elif isinstance(simpul, ast.ImportFrom) and simpul.module:
            jalur.add(simpul.module)
    return jalur


def berkas_produksi() -> list[str]:
    """Seluruh modul produksi: akar komposisi plus core/data/scenario/ui."""
    daftar = [BERKAS_APLIKASI]
    for paket in ("core", "data", "scenario", "ui"):
        for akar, _, berkas in os.walk(os.path.join(AKAR, paket)):
            if "__pycache__" in akar:
                continue
            daftar.extend(os.path.join(akar, f) for f in berkas if f.endswith(".py"))
    return daftar


def koleksi(at) -> skenario.Koleksi:
    return at.session_state[skenario.KUNCI]


def sel_perbandingan(at, baris: str, kolom: str) -> str:
    df = at.dataframe[0].value
    return df[df["Keluaran"] == baris].iloc[0][kolom]


def geser_ipal(at, persen):
    [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(persen).run()
    return at


# ═══════════ 1. aplikasi tersusun dan hidup ═══════════

class AplikasiTersusun(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_delapan_tab(self):
        self.assertEqual(len(self.at.tabs), JUMLAH_TAB)

    def test_tab_pembuka_di_urutan_pertama(self):
        """Pengguna baru disambut tab Mulai di Sini, bukan tab teknis."""
        self.assertEqual(self.at.tabs[0].label, "Mulai di Sini")

    def test_koleksi_skenario_terinisialisasi(self):
        k = koleksi(self.at)
        self.assertEqual(k.aktif, skenario.ACUAN)
        self.assertEqual(k.kustom, {})

    def test_acuan_selalu_ada(self):
        self.assertIn(skenario.ACUAN, koleksi(self.at).nama_terpakai())

    def test_beranda_dan_footer_digambar(self):
        teks = "\n".join(m.value for m in self.at.markdown)
        self.assertIn("hero-banner", teks)
        self.assertIn('class="footer"', teks)


# ═══════════ 2. akar komposisi tetap tipis ═══════════

class AkarKomposisi(unittest.TestCase):
    """
    AQUAPAVE.py menyusun, tidak mengimplementasikan.

    Yang diperiksa bukan jumlah barisnya melainkan bentuknya: tidak ada
    penyajian, tidak ada perhitungan, dan setiap tab dipanggil lewat satu
    fungsi render.
    """

    def test_setiap_tab_dipanggil_lewat_modulnya(self):
        isi = sumber(BERKAS_APLIKASI)
        for m in MODUL_TAB:
            self.assertIn(f"tab_{m}.render(", isi, f"Tab {m} tidak dipanggil")

    def test_tanpa_penyajian_langsung(self):
        """
        Selain st.set_page_config dan st.tabs, akar komposisi tidak boleh
        memanggil primitif penyajian Streamlit apa pun.
        """
        DIIZINKAN = {"set_page_config", "tabs"}
        dipakai = set()
        for simpul in ast.walk(pohon(BERKAS_APLIKASI)):
            if (isinstance(simpul, ast.Call)
                    and isinstance(simpul.func, ast.Attribute)
                    and isinstance(simpul.func.value, ast.Name)
                    and simpul.func.value.id == "st"):
                dipakai.add(simpul.func.attr)
        self.assertEqual(
            dipakai - DIIZINKAN, set(),
            "penyajian menyelinap kembali ke akar komposisi")

    def test_tanpa_html_mentah(self):
        self.assertNotIn("unsafe_allow_html", sumber(BERKAS_APLIKASI))

    def test_tanpa_perhitungan_ilmiah(self):
        """
        Satu-satunya panggilan core/ yang boleh ada di sini adalah neraca
        emisi, karena ia hasil bersama yang memang milik akar komposisi.
        """
        isi = sumber(BERKAS_APLIKASI)
        for terlarang in ("kmp.", "ktk.", "ret.", "hidrologi.", "perm.",
                          "geometri."):
            self.assertNotIn(terlarang, isi, f"perhitungan di akar: {terlarang}")

    def test_tanpa_impor_yatim(self):
        """Setiap nama yang diimpor harus benar-benar dipakai."""
        p = pohon(BERKAS_APLIKASI)
        diimpor = set()
        for simpul in ast.walk(p):
            if isinstance(simpul, (ast.Import, ast.ImportFrom)):
                for a in simpul.names:
                    diimpor.add(a.asname or a.name.split(".")[0])
        dipakai = {n.id for n in ast.walk(p)
                   if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        self.assertEqual(diimpor - dipakai, set(), "impor yatim di akar komposisi")


# ═══════════ 3. resolusi dan hasil bersama ═══════════

class HasilBersama(unittest.TestCase):
    """Satu resolusi, satu neraca, disiapkan sebelum tab dibuat."""

    def test_resolusi_hanya_sekali(self):
        isi = sumber(BERKAS_APLIKASI)
        self.assertEqual(isi.count("resolusi.resolusi("), 1)

    def test_neraca_co2_hanya_sekali(self):
        isi = sumber(BERKAS_APLIKASI)
        self.assertEqual(isi.count("emisi.neraca("), 1)

    def test_hasil_bersama_disiapkan_sebelum_tab(self):
        isi = sumber(BERKAS_APLIKASI)
        batas = isi.index("tabs = st.tabs(")
        for nama in ("HASIL_CO2 = emisi.neraca(",
                     "HASIL_SKENARIO_AKTIF = _hasil[",
                     "KUAT_TEKAN_AKTIF = HASIL_SKENARIO_AKTIF[",
                     "RETENSI_AKTIF = HASIL_SKENARIO_AKTIF[",
                     "AIR_TERTAHAN_AKTIF = HASIL_SKENARIO_AKTIF["):
            self.assertLess(isi.index(nama), batas,
                            f"{nama} disiapkan setelah tab dibuat")

    def test_keluaran_tab_berasal_dari_resolusi_yang_sama(self):
        """
        Nilai yang dilewatkan ke tab diambil dari dict resolusi yang juga
        mengisi pandangan perbandingan — bukan dihitung ulang.
        """
        isi = sumber(BERKAS_APLIKASI)
        self.assertIn("HASIL_SKENARIO_AKTIF = _hasil[PARAM.koleksi.aktif]", isi)

    def test_tab_tidak_menghitung_neraca_sendiri(self):
        for m in MODUL_TAB:
            berkas = os.path.join(DIR_UI, "tabs", f"{m}.py")
            for simpul in ast.walk(pohon(berkas)):
                if (isinstance(simpul, ast.Call)
                        and isinstance(simpul.func, ast.Attribute)
                        and simpul.func.attr == "neraca"):
                    self.fail(f"{m} menghitung neraca CO₂ sendiri")

    #: Nama yang sah dibaca sebuah blok tab: `st`, wadah tab, modul tab itu
    #: sendiri, dan hasil bersama yang disiapkan sebelum deretan tab dibuat.
    DISIAPKAN = {
        "st", "tabs", "_sk", "area_m2", "intensitas_hujan", "target_fc_val",
        "HASIL_CO2", "KUAT_TEKAN_AKTIF", "RETENSI_AKTIF", "AIR_TERTAHAN_AKTIF",
    } | {f"tab_{m}" for m in MODUL_TAB}

    def test_urutan_tab_tidak_berpengaruh(self):
        """
        Dibaca dari pohon sintaks, bukan dicari sebagai teks: nama modul
        `tab_mix_design` memuat potongan `_mix`, dan pencarian teks akan
        menandainya sebagai kebocoran padahal bukan.

        Setiap blok `with tabs[i]:` hanya boleh membaca nama yang sudah
        disiapkan sebelum deretan tab dibuat. Bila sebuah blok membaca nama
        milik blok lain, urutan penggambaran menjadi berpengaruh (ADR-008).
        """
        diperiksa = 0
        for simpul in ast.walk(pohon(BERKAS_APLIKASI)):
            if not isinstance(simpul, ast.With):
                continue
            konteks = simpul.items[0].context_expr
            if not (isinstance(konteks, ast.Subscript)
                    and isinstance(konteks.value, ast.Name)
                    and konteks.value.id == "tabs"):
                continue
            diperiksa += 1
            dibaca = {n.id for n in ast.walk(simpul)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            bocor = dibaca - self.DISIAPKAN
            self.assertEqual(
                bocor, set(),
                f"blok tab membaca nama yang tidak disiapkan lebih dulu: {bocor}")
        self.assertEqual(diperiksa, JUMLAH_TAB, "tidak semua blok tab diperiksa")


# ═══════════ 4. batas arsitektur ═══════════

class BatasArsitektur(unittest.TestCase):

    def test_hanya_akar_yang_mengimpor_streamlit(self):
        for berkas in berkas_produksi():
            teratas = {j.split(".")[0] for j in impor(berkas)}
            if os.path.abspath(berkas) == os.path.abspath(BERKAS_APLIKASI):
                self.assertIn("streamlit", teratas)
            else:
                self.assertNotIn(
                    "streamlit", teratas,
                    f"{berkas} mengimpor Streamlit; hanya akar komposisi boleh")

    def test_lapisan_ilmiah_tidak_mengimpor_ui(self):
        for paket in ("core", "data", "scenario"):
            for f in sorted(os.listdir(os.path.join(AKAR, paket))):
                if not f.endswith(".py"):
                    continue
                teratas = {j.split(".")[0]
                           for j in impor(os.path.join(AKAR, paket, f))}
                self.assertNotIn("ui", teratas, f"{paket}/{f} bergantung pada ui/")

    def test_modul_ui_baru_tidak_menyelesaikan_resolusi(self):
        for berkas in (os.path.join(DIR_UI, "sidebar.py"),
                       os.path.join(DIR_UI, "beranda.py")):
            self.assertNotIn("scenario.resolusi", impor(berkas))

    def test_beranda_tidak_menduplikasi_aturan_ketersediaan(self):
        isi = sumber(os.path.join(DIR_UI, "beranda.py"))
        for terlarang in ("cocok_konfigurasi_uji", "tidak_tersedia(",
                          "PARAMETER_KONFIGURASI_UJI", "StatusBukti."):
            self.assertNotIn(terlarang, isi)

    def test_seluruh_modul_tab_terimpor_mandiri(self):
        import importlib
        for m in MODUL_TAB:
            modul = importlib.import_module(f"ui.tabs.{m}")
            self.assertTrue(hasattr(modul, "render"), f"{m} tanpa render()")

    def test_tanpa_impor_melingkar(self):
        import importlib
        for nama in ("ui.sidebar", "ui.beranda", "ui.gaya", "ui.components",
                     "scenario.resolusi"):
            importlib.import_module(nama)

    def test_kontrak_render_sidebar(self):
        for simpul in ast.walk(pohon(os.path.join(DIR_UI, "sidebar.py"))):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                self.assertEqual([a.arg for a in simpul.args.args], ["st"])
                return
        self.fail("sidebar.render() tidak ditemukan")

    def test_parameter_global_hanya_membawa_yang_dipakai(self):
        bidang = set(sidebar.ParameterGlobal.__dataclass_fields__)
        self.assertEqual(
            bidang,
            {"koleksi", "skenario_aktif", "luas_area_m2",
             "intensitas_hujan_mm_per_jam", "target_fc_mpa"})


# ═══════════ 5. daur hidup skenario tetap utuh ═══════════

class DaurHidupSkenario(unittest.TestCase):
    """Jaminan S4 dan perbaikan identitas widget S5-0 tidak boleh regresi."""

    def test_tambah_ubah_pulihkan(self):
        at = jalankan()
        at.sidebar.button[0].click().run()
        self.assertEqual(koleksi(at).aktif, "A")

        geser_ipal(at, 22)
        self.assertFalse(skenario.cocok_konfigurasi_uji(koleksi(at).ambil("A")))
        self.assertEqual(
            sel_perbandingan(at, "Kuat tekan (7 hari)", "Skenario A"),
            FRASA_TIDAK_TERSEDIA)

        geser_ipal(at, int(skenario.ACUAN_SUBSTITUSI_IPAL))
        self.assertTrue(skenario.cocok_konfigurasi_uji(koleksi(at).ambil("A")))
        sel = sel_perbandingan(at, "Kuat tekan (7 hari)", "Skenario A")
        self.assertIn("13.19", sel)
        self.assertIn("terukur", sel)

    def test_identitas_widget_tetap_stabil(self):
        """Masukan berturut-turut tidak boleh hilang (regresi S5-0)."""
        at = jalankan()
        at.sidebar.button[0].click().run()
        for minta in (22, 15, 20, 10):
            geser_ipal(at, minta)
            self.assertAlmostEqual(
                koleksi(at).ambil("A").substitusi_ipal_persen, minta, delta=1e-9,
                msg=f"masukan {minta}% hilang")

    def test_berpindah_skenario(self):
        at = jalankan()
        at.sidebar.button[0].click().run()
        geser_ipal(at, 20)
        at.sidebar.radio[0].set_value(skenario.ACUAN).run()
        self.assertEqual(koleksi(at).aktif, skenario.ACUAN)
        at.sidebar.radio[0].set_value("A").run()
        self.assertEqual(koleksi(at).aktif, "A")

    def test_hapus_kustom_acuan_bertahan(self):
        at = jalankan()
        at.sidebar.button[0].click().run()
        at.sidebar.button[1].click().run()
        k = koleksi(at)
        self.assertEqual(k.kustom, {})
        self.assertEqual(k.aktif, skenario.ACUAN)
        self.assertTrue(at.sidebar.button[1].disabled)

    def test_acuan_terkunci(self):
        at = jalankan()
        for s in at.sidebar.slider:
            self.assertTrue(s.disabled, f"{s.label} dapat disunting pada acuan")


# ═══════════ 6. pandangan perbandingan ═══════════

class PandanganPerbandingan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_di_atas_tab_bukan_salah_satu_tab(self):
        self.assertEqual(len(self.at.tabs), JUMLAH_TAB)
        self.assertNotIn("Perbandingan Skenario",
                         [t.label for t in self.at.tabs])
        self.assertIn("Perbandingan Skenario",
                      "\n".join(m.value for m in self.at.markdown))

    def test_menampilkan_acuan(self):
        self.assertIn("Acuan Penelitian", self.at.dataframe[0].value.columns)

    def test_membedakan_status_bukti(self):
        df = self.at.dataframe[0].value
        kolom = "\n".join(str(v) for v in df["Acuan Penelitian"])
        for status in ("terukur", "deterministik", "target"):
            self.assertIn(status, kolom)

    def test_menampilkan_skenario_kustom(self):
        at = jalankan()
        at.sidebar.button[0].click().run()
        self.assertIn("Skenario A", at.dataframe[0].value.columns)

    def test_ketidaktersediaan_dinyatakan_eksplisit(self):
        at = jalankan()
        at.sidebar.button[0].click().run()
        geser_ipal(at, 22)
        kolom = "\n".join(str(v) for v in at.dataframe[0].value["Skenario A"])
        self.assertIn(FRASA_TIDAK_TERSEDIA, kolom)
        self.assertNotIn("0.00 MPa", kolom)

    def test_catatan_aturan_selisih_tampil(self):
        from ui.components import comparison as komp_banding
        self.assertIn(komp_banding.CATATAN_TABEL,
                      [c.value for c in self.at.caption])

    def test_beranda_menerima_hasil_bukan_menghitungnya(self):
        for simpul in ast.walk(pohon(os.path.join(DIR_UI, "beranda.py"))):
            if (isinstance(simpul, ast.FunctionDef)
                    and simpul.name == "perbandingan_skenario"):
                self.assertEqual(
                    [a.arg for a in simpul.args.args],
                    ["st", "hasil", "kolom", "ringkas"])
                return
        self.fail("beranda.perbandingan_skenario() tidak ditemukan")


if __name__ == "__main__":
    unittest.main(verbosity=2)
