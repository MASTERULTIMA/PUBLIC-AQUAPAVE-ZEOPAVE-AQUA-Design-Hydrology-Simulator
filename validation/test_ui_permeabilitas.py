"""
Uji antarmuka Tab 2 — Permeabilitas (S5-2).

Melengkapi validation/test_ui.py, yang menjaga pengaman skenario di tingkat
aplikasi. Berkas ini menjaga satu tab yang kini hidup di modulnya sendiri,
`ui/tabs/permeabilitas.py`.

Dua hal yang dijaga di sini dan tidak dijaga di tempat lain:

  1. **Reproduksi konfigurasi laboratorium.** Nilai bawaan tab harus
     menghasilkan A = 225 cm2 dan k = 1,667 cm/detik. Bila suatu hari nilai
     bawaannya bergeser, tab berhenti mereproduksi OUTPUT3 §4.5 tanpa ada
     yang menyadarinya.

  2. **Lapisan tampilan tidak boleh punya rumusnya sendiri.** Setiap k yang
     muncul di layar dihitung ulang secara mandiri di dalam uji ini memakai
     core/permeabilitas.py, lalu dibandingkan. Rumus yang tergandakan dan
     kemudian menyimpang akan langsung terlihat.

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

from core import geometri  # noqa: E402
from core import permeabilitas as perm  # noqa: E402
from data import akses  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_TAB = os.path.join(AKAR, "ui", "tabs", "permeabilitas.py")
TENGGAT = 60


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def widget(at, jenis: str, label: str):
    """Widget Tab 2 menurut labelnya."""
    kel = getattr(at, jenis)
    cocok = [x for x in kel if getattr(x, "label", None) == label]
    if not cocok:
        raise AssertionError(
            f"{jenis} {label!r} tidak ada; yang ada: "
            f"{[getattr(x, 'label', '?') for x in kel]}"
        )
    return cocok[0]


def mode_kustom(at) -> AppTest:
    """Matikan mode acuan sehingga kendali geometri dapat disunting."""
    widget(at, "toggle", "Konfigurasi Acuan Penelitian").set_value(False).run()
    return at


def teks_luas(at) -> str:
    """Baris 'Luas penampang terhitung' milik Tab 2."""
    cocok = [m.value for m in at.markdown if "Luas penampang terhitung" in m.value]
    if not cocok:
        raise AssertionError("baris luas penampang tidak digambar")
    return cocok[0]


def luas_terhitung(at) -> float:
    return float(re.search(r"terhitung:\*\* ([\d.]+) cm²", teks_luas(at)).group(1))


def gradien(at) -> float:
    return float(re.search(r"i = h/L:\*\* ([\d.]+)", teks_luas(at)).group(1))


def kotak_hasil(at) -> str:
    """Kotak hasil rerata k milik Tab 2."""
    cocok = [m.value for m in at.markdown if "Koefisien permeabilitas rerata" in m.value]
    if not cocok:
        raise AssertionError("kotak hasil permeabilitas tidak digambar")
    return cocok[0]


def k_rerata(at) -> float:
    return float(re.search(r'result-value">([\d.]+) cm/dtk', kotak_hasil(at)).group(1))


def tabel_uji(at):
    """Tabel per-pengujian milik Tab 2, dikenali dari kolomnya."""
    for d in at.dataframe:
        if "k (cm/dtk)" in d.value.columns:
            return d.value
    raise AssertionError("tabel pengujian permeabilitas tidak digambar")


# ═══════════════ 1. reproduksi konfigurasi laboratorium ═══════════════

class ReproduksiAcuanPenelitian(unittest.TestCase):
    """
    Nilai bawaan tab HARUS mereproduksi eksperimen yang dikonfirmasi:
    persegi 15 × 15 cm, L = 2 cm, h = 6 cm, Q = 1.125 cm³/detik.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_mode_acuan_aktif_secara_bawaan(self):
        self.assertTrue(widget(self.at, "toggle", "Konfigurasi Acuan Penelitian").value)

    def test_luas_penampang_225_cm2(self):
        self.assertAlmostEqual(luas_terhitung(self.at), 225.00, delta=0.01)
        self.assertAlmostEqual(luas_terhitung(self.at), perm.LAB_LUAS_CM2, delta=0.01)

    def test_koefisien_1_667_cm_per_detik(self):
        self.assertAlmostEqual(k_rerata(self.at), perm.LAB_K_CM_PER_DETIK, delta=0.001)

    def test_gradien_hidraulik_h_per_L(self):
        """i = h/L = 6/2 = 3."""
        self.assertAlmostEqual(gradien(self.at), 3.00, delta=0.01)

    def test_geometri_bawaan_persegi_bukan_silinder_setara(self):
        """
        Benda uji penelitian persegi, dan tidak boleh diam-diam diganti
        silinder berdiameter setara.
        """
        sb = widget(self.at, "selectbox", "Bentuk benda uji")
        self.assertEqual(sb.value, geometri.PERSEGI_PANJANG)
        self.assertAlmostEqual(
            widget(self.at, "number_input", "Lebar (cm)").value, 15.0, delta=1e-9)
        self.assertAlmostEqual(
            widget(self.at, "number_input", "Panjang (cm)").value, 15.0, delta=1e-9)

    def test_tebal_dan_tinggi_tekan_sesuai_laboratorium(self):
        self.assertAlmostEqual(
            widget(self.at, "number_input", "Tebal benda uji L (cm)").value,
            perm.LAB_TEBAL_CM, delta=1e-9)
        self.assertAlmostEqual(
            widget(self.at, "number_input", "Tinggi tekan tetap h (cm)").value,
            perm.LAB_TINGGI_TEKAN_CM, delta=1e-9)

    def test_debit_bawaan_setara_kecepatan_5_cm_per_detik(self):
        """Q = v · A = 5 × 225 = 1.125 cm³/detik."""
        self.assertAlmostEqual(
            widget(self.at, "number_input", "Q1 (cm³/detik)").value,
            perm.debit_dari_kecepatan(
                perm.LAB_KECEPATAN_CM_PER_DETIK, perm.LAB_LUAS_CM2),
            delta=1e-9,
        )

    def test_kendali_terkunci_pada_mode_acuan(self):
        """Konfigurasi yang diuji tidak boleh tergeser tanpa sengaja."""
        for label in ("Lebar (cm)", "Panjang (cm)", "Tebal benda uji L (cm)",
                      "Tinggi tekan tetap h (cm)"):
            self.assertTrue(
                widget(self.at, "number_input", label).disabled,
                f"{label} harus terkunci pada mode acuan",
            )
        self.assertTrue(widget(self.at, "selectbox", "Bentuk benda uji").disabled)

    def test_metode_constant_head_dinyatakan(self):
        teks = "\n".join(
            m.value for m in list(self.at.markdown) + list(self.at.caption))
        self.assertIn("Constant Head", teks)
        self.assertNotIn("falling head", teks.lower())

    def test_kepatuhan_sni_tidak_diklaim_penuh(self):
        """SNI 2435:2008 disebut sebagai rujukan persamaan, bukan sertifikat."""
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("SNI 2435:2008", teks)
        self.assertIn("belum diverifikasi", teks)


# ═══════════════════ 2. ketiga mode geometri ═══════════════════

class ModeGeometri(unittest.TestCase):
    """
    Ketiga bentuk yang didukung core/geometri.py harus tetap dapat dipakai,
    dan luasnya harus sama dengan yang dihitung lapisan core.
    """

    def test_lingkaran_kompatibel_mundur(self):
        """Alur kerja silinder lama: Ø150 mm -> A = 176,71 cm²."""
        at = mode_kustom(jalankan())
        widget(at, "selectbox", "Bentuk benda uji").set_value(geometri.LINGKARAN).run()
        diharapkan = geometri.luas_penampang(geometri.LINGKARAN, diameter_cm=15.0)
        self.assertAlmostEqual(luas_terhitung(at), diharapkan, delta=0.01)
        self.assertAlmostEqual(luas_terhitung(at), 176.71, delta=0.01)
        self.assertEqual(list(at.exception), [])

    def test_persegi_panjang(self):
        at = mode_kustom(jalankan())
        widget(at, "selectbox", "Bentuk benda uji").set_value(
            geometri.PERSEGI_PANJANG).run()
        widget(at, "number_input", "Lebar (cm)").set_value(20.0).run()
        widget(at, "number_input", "Panjang (cm)").set_value(10.0).run()
        diharapkan = geometri.luas_penampang(
            geometri.PERSEGI_PANJANG, lebar_cm=20.0, panjang_cm=10.0)
        self.assertAlmostEqual(luas_terhitung(at), diharapkan, delta=0.01)
        self.assertAlmostEqual(luas_terhitung(at), 200.00, delta=0.01)

    def test_luas_dimasukkan_langsung(self):
        at = mode_kustom(jalankan())
        widget(at, "selectbox", "Bentuk benda uji").set_value(geometri.LANGSUNG).run()
        widget(at, "number_input", "Luas penampang A (cm²)").set_value(300.0).run()
        self.assertAlmostEqual(luas_terhitung(at), 300.00, delta=0.01)

    def test_luas_langsung_225_mereproduksi_hasil_penelitian(self):
        """Jalan lain menuju konfigurasi yang sama harus memberi k yang sama."""
        at = mode_kustom(jalankan())
        widget(at, "selectbox", "Bentuk benda uji").set_value(geometri.LANGSUNG).run()
        widget(at, "number_input", "Luas penampang A (cm²)").set_value(
            perm.LAB_LUAS_CM2).run()
        self.assertAlmostEqual(k_rerata(at), perm.LAB_K_CM_PER_DETIK, delta=0.001)

    def test_ketiga_bentuk_tersedia_di_pemilih(self):
        at = mode_kustom(jalankan())
        self.assertEqual(
            set(widget(at, "selectbox", "Bentuk benda uji").options),
            set(geometri.BENTUK_TERSEDIA.values()),
        )

    def test_luas_mengubah_hasil_sesuai_core(self):
        """Luas berubah -> k berubah persis seperti hitungan core."""
        at = mode_kustom(jalankan())
        widget(at, "selectbox", "Bentuk benda uji").set_value(geometri.LINGKARAN).run()
        A = geometri.luas_penampang(geometri.LINGKARAN, diameter_cm=15.0)
        diharapkan = perm.koefisien_dari_debit(
            perm.debit_dari_kecepatan(perm.LAB_KECEPATAN_CM_PER_DETIK,
                                      perm.LAB_LUAS_CM2),
            perm.LAB_TEBAL_CM, A, perm.LAB_TINGGI_TEKAN_CM,
        )
        self.assertAlmostEqual(k_rerata(at), diharapkan, delta=0.001)
        self.assertNotAlmostEqual(k_rerata(at), perm.LAB_K_CM_PER_DETIK, delta=0.01)


# ═══════════════ 3. dua bentuk masukan yang setara ═══════════════

class BentukMasukan(unittest.TestCase):
    """Bentuk debit dan bentuk volume harus memberi hasil yang sama."""

    def test_bentuk_debit_bawaan(self):
        at = jalankan()
        self.assertEqual(widget(at, "radio", "Bentuk masukan").value, "Debit volumetrik")
        self.assertIn("Q (cm³/dtk)", tabel_uji(at).columns)

    def test_bentuk_volume_memberi_hasil_sama(self):
        """V = 1.125 cm³ selama t = 1 detik identik dengan Q = 1.125 cm³/detik."""
        at = jalankan()
        widget(at, "radio", "Bentuk masukan").set_value(
            "Volume terkumpul + waktu").run()
        tabel = tabel_uji(at)
        self.assertIn("V (cm³)", tabel.columns)
        self.assertIn("t (dtk)", tabel.columns)
        self.assertAlmostEqual(k_rerata(at), perm.LAB_K_CM_PER_DETIK, delta=0.001)

    def test_waktu_tidak_dibagikan_dua_kali(self):
        """
        Regresi utama modul: pada bentuk debit, waktu sudah terkandung di
        dalam Q dan tidak boleh dibagikan lagi.
        """
        at = jalankan()
        tabel = tabel_uji(at)
        self.assertNotIn("t (dtk)", tabel.columns)
        self.assertAlmostEqual(
            float(tabel["k (cm/dtk)"].iloc[0]), perm.LAB_K_CM_PER_DETIK, delta=0.001)

    def test_beberapa_pengujian_diringkas(self):
        at = jalankan()
        widget(at, "number_input", "Jumlah pengujian").set_value(3).run()
        self.assertEqual(len(tabel_uji(at)), 3)
        self.assertIn("(n = 3)", kotak_hasil(at))


# ═══════════════ 4. batas masukan fisik ═══════════════

class MasukanTidakSah(unittest.TestCase):
    """
    Nilai fisik yang tidak masuk akal harus tertahan di antarmuka, bukan
    diserahkan ke lapisan core untuk menaikkan kekecualian di hadapan
    pengguna.

    core/permeabilitas.py menolak nilai <= 0. Antarmuka menjaga agar keadaan
    itu tidak pernah tercapai, dengan batas bawah setiap kendali di atas nol.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = mode_kustom(jalankan())

    KENDALI = (
        "Diameter benda uji (mm)",
        "Tebal benda uji L (cm)",
        "Tinggi tekan tetap h (cm)",
        "Q1 (cm³/detik)",
    )

    def test_batas_bawah_selalu_di_atas_nol(self):
        for label in self.KENDALI:
            w = widget(self.at, "number_input", label)
            self.assertTrue(w.proto.has_min, f"{label} tanpa batas bawah")
            self.assertGreater(w.proto.min, 0.0, f"{label} mengizinkan nilai <= 0")

    def test_core_menolak_nilai_tidak_sah(self):
        """Pengaman lapisan dalam tetap ada, bukan digantikan batas antarmuka."""
        with self.assertRaises(ValueError):
            perm.koefisien_dari_debit(0.0, 2.0, 225.0, 6.0)
        with self.assertRaises(ValueError):
            perm.koefisien_dari_debit(1125.0, 2.0, -1.0, 6.0)
        with self.assertRaises(ValueError):
            perm.gradien_hidraulik(6.0, 0.0)

    def test_nilai_ekstrem_tetap_terhitung_tanpa_kegagalan(self):
        at = mode_kustom(jalankan())
        widget(at, "number_input", "Tebal benda uji L (cm)").set_value(50.0).run()
        widget(at, "number_input", "Tinggi tekan tetap h (cm)").set_value(1.0).run()
        self.assertEqual(list(at.exception), [])
        self.assertGreater(k_rerata(at), 0.0)


# ═══════════════ 5. satuan, bukti, dan provenansi ═══════════════

class SatuanDanProvenansi(unittest.TestCase):
    """Angka tanpa satuan dan tanpa asal-usul tidak boleh muncul."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_satuan_hasil(self):
        self.assertIn("cm/dtk", kotak_hasil(self.at))

    def test_satuan_luas_dan_gradien(self):
        """Gradien hidraulik tidak bersatuan dan tidak boleh diberi satuan."""
        self.assertIn("cm²", teks_luas(self.at))
        self.assertNotRegex(teks_luas(self.at), r"i = h/L:\*\* [\d.]+ \w")

    def test_satuan_kolom_tabel(self):
        for kolom in tabel_uji(self.at).columns:
            if kolom != "Pengujian":
                self.assertRegex(kolom, r"\((cm³/dtk|cm³|dtk|cm/dtk)\)")

    def test_sebaran_ditampilkan_bersama_rerata(self):
        self.assertIn("simpangan baku", kotak_hasil(self.at))
        self.assertIn("CV", kotak_hasil(self.at))

    def test_provenansi_hasil_laboratorium_terlihat(self):
        teks = "\n".join(m.value for m in self.at.markdown)
        self.assertIn(akses.besaran("PERMEABILITAS").provenans(), teks)

    def test_pembanding_pustaka_bersumber(self):
        teks = "\n".join(m.value for m in self.at.markdown)
        for q in perm.pembanding_literatur():
            self.assertIn(q["sumber"], teks)

    def test_tanpa_vonis_lulus_gagal(self):
        """
        Tab ini sengaja tidak memberi vonis. Ambang 0,45 cm/dtk dan target
        0,60 cm/dtk yang dipakai versi lama tidak ada di naskah mana pun dan
        telah dihapus (ADR-001), sehingga tidak ada dasar untuk meluluskan
        atau menggagalkan sebuah nilai k.
        """
        self.assertNotIn("badge-", kotak_hasil(self.at))
        alasan = [c.value for c in self.at.caption
                  if "0,45 cm/dtk" in c.value and "ADR-001" in c.value]
        self.assertTrue(alasan, "alasan penghapusan ambang tidak dijelaskan")

    def test_pembanding_hanya_yang_disitir(self):
        """Hanya nilai pustaka yang benar-benar disitir yang boleh muncul."""
        nilai = {q["nilai"] for q in perm.pembanding_literatur()}
        self.assertEqual(nilai, {0.01, 0.574, 0.764})
        self.assertNotIn(0.45, nilai)
        self.assertNotIn(0.60, nilai)

    def test_hasil_pengguna_tidak_disebut_pengukuran(self):
        """
        Hitungan kalkulator adalah hasil hitungan atas masukan pengguna, bukan
        pengukuran laboratorium. Keduanya muncul terpisah di grafik.
        """
        self.assertNotIn("terukur", kotak_hasil(self.at).lower())
        teks = "\n".join(m.value for m in self.at.markdown)
        self.assertIn("Hasil lab penelitian", teks)


# ═══════════════ 6. batas arsitektur ═══════════════

class BatasArsitektur(unittest.TestCase):
    """
    Modul tab hanya menyajikan. Perhitungan tetap milik core/.
    """

    def _pohon(self):
        with open(BERKAS_TAB, encoding="utf8") as f:
            return ast.parse(f.read(), filename=BERKAS_TAB)

    def _impor(self):
        paket = set()
        for simpul in ast.walk(self._pohon()):
            if isinstance(simpul, ast.Import):
                paket.update(a.name.split(".")[0] for a in simpul.names)
            elif isinstance(simpul, ast.ImportFrom) and simpul.module:
                paket.add(simpul.module.split(".")[0])
        return paket

    def test_tidak_mengimpor_streamlit(self):
        self.assertNotIn("streamlit", self._impor())

    def test_memakai_lapisan_perhitungan(self):
        self.assertIn("core", self._impor())

    def test_tidak_bergantung_pada_skenario(self):
        """
        Kontrak Tab 2 hanya `st`. Ia tidak membaca skenario aktif maupun hasil
        bersama, sehingga tidak bergantung pada urutan eksekusi tab lain.
        """
        self.assertNotIn("scenario", self._impor())

    def test_kontrak_render_hanya_st(self):
        for simpul in ast.walk(self._pohon()):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                arg = [a.arg for a in simpul.args.args]
                self.assertEqual(
                    arg, ["st"],
                    "kontrak Tab 2 harus tetap minimal; jangan menambah "
                    "ketergantungan yang tidak benar-benar dibutuhkan",
                )
                return
        self.fail("fungsi render() tidak ditemukan")

    #: Satu-satunya aritmetika yang boleh ada di lapisan tampilan: konversi
    #: satuan milimeter ke sentimeter, dan penurunan debit acuan dari konstanta
    #: laboratorium. Keduanya bukan persamaan permeabilitas.
    ARITMETIKA_DIIZINKAN = {
        "diam_mm / 10.0",
        "perm.LAB_KECEPATAN_CM_PER_DETIK * perm.LAB_LUAS_CM2",
    }

    def test_tanpa_rumus_permeabilitas_di_lapisan_tampilan(self):
        """
        Rumus k tidak boleh digandakan di sini.

        Diperiksa dari pohon sintaks, bukan dicari sebagai teks: dokumentasi
        yang MENULISKAN k = Q·L/(A·h) tidak sama dengan menghitungnya.
        """
        with open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        pohon = ast.parse(sumber, filename=BERKAS_TAB)
        ditemukan = []
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.BinOp) and isinstance(
                    simpul.op, (ast.Div, ast.Mult, ast.Pow)):
                potongan = ast.get_source_segment(sumber, simpul)
                if potongan and potongan not in self.ARITMETIKA_DIIZINKAN:
                    ditemukan.append(potongan)
        self.assertEqual(
            ditemukan, [],
            "aritmetika fisik di lapisan tampilan; perhitungan milik core/: "
            + "; ".join(ditemukan),
        )

    def test_aquapave_hanya_mengorkestrasi_tab_ini(self):
        """Badan Tab 2 tidak boleh tertinggal sebagian di berkas aplikasi."""
        with open(BERKAS_APLIKASI, encoding="utf8") as f:
            isi = f.read()
        self.assertIn("tab_permeabilitas.render(st)", isi)
        for sisa in ("koefisien_dari_debit", "koefisien_dari_volume",
                     "gradien_hidraulik", "pembanding_literatur",
                     "Bentuk benda uji", "Tinggi tekan tetap"):
            self.assertNotIn(sisa, isi, f"sisa Tab 2 tertinggal di AQUAPAVE.py: {sisa}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
