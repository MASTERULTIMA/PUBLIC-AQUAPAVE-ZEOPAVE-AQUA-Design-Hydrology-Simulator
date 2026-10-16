"""
Uji antarmuka tab Eksplorasi Kadar Substitusi.

Yang dijaga:

1. Takaran bahan dan pengurangan CO₂ pada setiap kadar berasal dari core/,
   bukan angka yang ditulis di tab.
2. Kadar terpilih dibaca dari besaran kanonik, bukan literal.
3. Angka kuat tekan dan permeabilitas hanya tampil untuk kadar terpilih
   (nilai terukur kanonik). Kadar lain hanya diberi arah relatif.

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import emisi  # noqa: E402
from core import komposisi as kmp  # noqa: E402
from data import akses  # noqa: E402
from ui.tabs import substitusi as tab_sub  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
JUDUL_TAB = "Eksplorasi Kadar Substitusi"


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=60)
    at.run()
    return at


def tab(at):
    cocok = [t for t in at.tabs if t.label == JUDUL_TAB]
    if not cocok:
        raise AssertionError("tab Eksplorasi Kadar Substitusi tidak ada")
    return cocok[0]


class TabTergambar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()
        cls.t = tab(cls.at)
        cls.tabel = cls.t.dataframe[0].value

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_berada_setelah_kalkulator_mix_design(self):
        label = [t.label for t in self.at.tabs]
        self.assertEqual(label.index(JUDUL_TAB),
                         label.index("Kalkulator Mix Design") + 1)

    def test_enam_kadar_nol_sampai_dua_puluh_lima(self):
        self.assertEqual(tab_sub.KADAR, (0, 5, 10, 15, 20, 25))
        self.assertEqual(len(self.tabel), len(tab_sub.KADAR))

    def test_kadar_terpilih_dari_besaran_kanonik(self):
        terpilih = akses.nilai("SUBSTITUSI_IPAL")
        self.assertEqual(tab_sub.kadar_terpilih(), terpilih)
        baris = [k for k in self.tabel["Kadar IPAL"] if "terpilih" in k]
        self.assertEqual(baris, [f"{tab_sub.angka(terpilih, 0)}% (terpilih)"])

    def test_angka_kinerja_hanya_untuk_kadar_terpilih(self):
        for _, b in self.tabel.iterrows():
            with self.subTest(kadar=b["Kadar IPAL"]):
                ada_angka_kt = re.search(r"\d+,\d+ MPa", b["Kuat tekan"])
                ada_angka_pm = re.search(r"\d+,\d+ cm/detik", b["Permeabilitas"])
                if "terpilih" in b["Kadar IPAL"]:
                    self.assertTrue(ada_angka_kt and ada_angka_pm)
                else:
                    self.assertIsNone(ada_angka_kt)
                    self.assertIsNone(ada_angka_pm)

    def test_nilai_terpilih_adalah_nilai_terukur_kanonik(self):
        b = self.tabel[self.tabel["Kadar IPAL"].str.contains("terpilih")].iloc[0]
        kt = akses.besaran("KUAT_TEKAN_7_HARI")
        pm = akses.besaran("PERMEABILITAS")
        self.assertEqual(b["Kuat tekan"], f"{tab_sub.angka(kt.nilai, 2)} {kt.satuan}")
        self.assertEqual(b["Permeabilitas"], f"{tab_sub.angka(pm.nilai, 3)} {pm.satuan}")

    def test_arah_mengikuti_kecenderungan(self):
        """Semen lebih banyak: permeabilitas lebih kecil; IPAL lebih banyak: kuat tekan lebih rendah."""
        for _, b in self.tabel.iterrows():
            if "terpilih" in b["Kadar IPAL"]:
                continue
            kadar = float(b["Kadar IPAL"].rstrip("%"))
            with self.subTest(kadar=kadar):
                if kadar < tab_sub.kadar_terpilih():
                    self.assertTrue(b["Kuat tekan"].startswith("lebih tinggi"))
                    self.assertTrue(b["Permeabilitas"].startswith("lebih kecil"))
                else:
                    self.assertTrue(b["Kuat tekan"].startswith("lebih rendah"))
                    self.assertTrue(b["Permeabilitas"].startswith("lebih besar"))


class TakaranDariCore(unittest.TestCase):

    def test_takaran_sama_dengan_core_komposisi(self):
        for b in tab_sub.baris_kadar(0.85, 0.05):
            with self.subTest(kadar=b["kadar"]):
                mix = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=b["kadar"])
                self.assertAlmostEqual(b["semen_kg"], mix["massa_semen_kg"])
                self.assertAlmostEqual(b["ipal_kg"], mix["massa_ipal_kg"])
                self.assertAlmostEqual(b["agregat_kg"], mix["massa_agregat_kg"])
                self.assertAlmostEqual(b["air_kg"], mix["massa_air_kg"])

    def test_pengurangan_co2_sama_dengan_core_emisi(self):
        for b in tab_sub.baris_kadar(0.85, 0.05):
            with self.subTest(kadar=b["kadar"]):
                self.assertAlmostEqual(
                    b["reduksi_co2_persen"],
                    emisi.neraca(1.0, b["kadar"], 0.85, 0.05)["reduksi_persen"])

    def test_semen_turun_dan_ipal_naik_seiring_kadar(self):
        baris = tab_sub.baris_kadar(0.85, 0.05)
        semen = [b["semen_kg"] for b in baris]
        ipal = [b["ipal_kg"] for b in baris]
        self.assertEqual(semen, sorted(semen, reverse=True))
        self.assertEqual(ipal, sorted(ipal))


class Penjelajah(unittest.TestCase):

    def test_kadar_lain_menampilkan_takaran_dan_arah(self):
        at = jalankan()
        tab(at).select_slider[0].set_value(25.0).run()
        t = tab(at)
        metrik = {m.label: m.value for m in t.metric}
        mix = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=25.0)
        self.assertEqual(metrik["Lumpur IPAL"], f"{tab_sub.angka(mix['massa_ipal_kg'])} kg")
        teks = " ".join(i.value for i in t.info)
        self.assertIn("kuat tekan menurun", teks)
        self.assertNotRegex(teks, r"\d+,\d+ MPa")


if __name__ == "__main__":
    unittest.main(verbosity=2)
