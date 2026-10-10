"""
Uji neraca massa rancangan campuran (S3.5).

VERIFIKASI perangkat lunak, bukan validasi eksperimental (ADR-004).
Acuan: OUTPUT3 §3.3 — pengikat : agregat = 1 : 3, substitusi IPAL 15%,
air ±0,40 per kg pengikat, tanpa pasir.
"""

from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import komposisi as kmp  # noqa: E402
from data import akses  # noqa: E402


class NeracaMassaTertutup(unittest.TestCase):
    """Jumlah komponen harus sama persis dengan massa total, di semua kondisi."""

    def test_acuan_tertutup(self):
        h = kmp.rancangan_campuran(1.0)
        self.assertTrue(h["neraca_tertutup"])
        self.assertAlmostEqual(h["selisih_neraca_kg"], 0.0, delta=1e-9)

    def test_tertutup_di_banyak_kondisi(self):
        for volume in (0.1, 1.0, 12.5, 100.0):
            for sub in (0.0, 10.0, 15.0, 25.0, 100.0):
                for fab in (0.30, 0.40, 0.55):
                    with self.subTest(volume=volume, sub=sub, fab=fab):
                        h = kmp.rancangan_campuran(volume, sub, fab)
                        self.assertTrue(h["neraca_tertutup"])

    def test_pengikat_sama_dengan_semen_tambah_ipal(self):
        h = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=15.0)
        self.assertAlmostEqual(
            h["massa_semen_kg"] + h["massa_ipal_kg"], h["massa_pengikat_kg"], delta=1e-9
        )

    def test_proporsi_berjumlah_seratus(self):
        h = kmp.rancangan_campuran(1.0)
        total = (
            h["proporsi_semen_persen"] + h["proporsi_ipal_persen"]
            + h["proporsi_agregat_persen"] + h["proporsi_air_persen"]
        )
        self.assertAlmostEqual(total, 100.0, delta=1e-9)


class RasioAcuan(unittest.TestCase):
    """Rasio §3.3 harus terpelihara apa pun volumenya."""

    def test_rasio_agregat_tiga_kali_pengikat(self):
        h = kmp.rancangan_campuran(2.5)
        self.assertAlmostEqual(
            h["massa_agregat_kg"] / h["massa_pengikat_kg"], 3.0, delta=1e-9
        )

    def test_air_sesuai_faktor_air_pengikat(self):
        for fab in (0.30, 0.40, 0.55):
            with self.subTest(fab=fab):
                h = kmp.rancangan_campuran(1.0, faktor_air_pengikat=fab)
                self.assertAlmostEqual(
                    h["massa_air_kg"] / h["massa_pengikat_kg"], fab, delta=1e-9
                )

    def test_konsisten_dengan_konstanta(self):
        """Nilai bawaan modul tidak boleh menyimpang dari konstanta.py."""
        self.assertAlmostEqual(
            kmp.SUBSTITUSI_ACUAN, akses.nilai("SUBSTITUSI_IPAL"), delta=1e-9
        )
        self.assertAlmostEqual(
            kmp.FAKTOR_AIR_PENGIKAT_ACUAN, akses.nilai("FAKTOR_AIR_PENGIKAT"), delta=1e-9
        )
        self.assertAlmostEqual(
            kmp.RASIO_AGREGAT_ACUAN, akses.nilai("RASIO_PENGIKAT_AGREGAT"), delta=1e-9
        )


class SubstitusiIPAL(unittest.TestCase):
    """Substitusi 0%, acuan 15%, dan batas atas."""

    def test_substitusi_nol_tanpa_ipal(self):
        h = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=0.0)
        self.assertAlmostEqual(h["massa_ipal_kg"], 0.0, delta=1e-12)
        self.assertAlmostEqual(
            h["massa_semen_kg"], h["massa_pengikat_kg"], delta=1e-9
        )
        self.assertTrue(h["neraca_tertutup"])

    def test_acuan_penelitian_15_persen(self):
        h = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=15.0)
        self.assertTrue(h["sesuai_acuan_penelitian"])
        self.assertAlmostEqual(
            h["massa_ipal_kg"] / h["massa_pengikat_kg"] * 100.0, 15.0, delta=1e-9
        )

    def test_substitusi_penuh_tanpa_semen(self):
        h = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=100.0)
        self.assertAlmostEqual(h["massa_semen_kg"], 0.0, delta=1e-12)
        self.assertTrue(h["neraca_tertutup"])

    def test_di_luar_acuan_ditandai(self):
        """Komposisi di luar yang diuji harus menghasilkan catatan asumsi."""
        h = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=20.0)
        self.assertFalse(h["sesuai_acuan_penelitian"])
        self.assertTrue(
            any("di luar komposisi yang diuji" in a for a in h["asumsi"]),
            "substitusi non-acuan harus diberi catatan asumsi",
        )

    def test_massa_total_tidak_berubah_oleh_substitusi(self):
        """Substitusi memindahkan massa di dalam pengikat, bukan menambahnya."""
        a = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=0.0)
        b = kmp.rancangan_campuran(1.0, substitusi_ipal_persen=25.0)
        self.assertAlmostEqual(a["massa_total_kg"], b["massa_total_kg"], delta=1e-9)
        self.assertAlmostEqual(a["massa_pengikat_kg"], b["massa_pengikat_kg"], delta=1e-9)


class AsumsiTerekspos(unittest.TestCase):
    """Asumsi yang belum terselesaikan tidak boleh disembunyikan."""

    def test_berat_satuan_ditandai_asumsi(self):
        h = kmp.rancangan_campuran(1.0)
        self.assertTrue(
            any("ASUMSI" in a for a in h["asumsi"]),
            "berat satuan 1850 kg/m³ harus ditandai sebagai asumsi",
        )

    def test_berat_satuan_tersirat_benda_uji(self):
        """Data benda uji menyiratkan sekitar 1.280 kg/m³, jauh dari 1.850."""
        b = kmp.berat_satuan_tersirat_benda_uji()
        self.assertAlmostEqual(b["berat_satuan_kg_m3"], 1280.0, delta=5.0)
        self.assertLess(b["selisih_terhadap_asumsi_persen"], -25.0)

    def test_status_bukti_model(self):
        """Rancangan campuran adalah keluaran model, bukan pengukuran."""
        self.assertEqual(kmp.rancangan_campuran(1.0)["status_bukti"], "model")


class AgregatHanyaBatuSirtu(unittest.TestCase):
    """
    Hebel dan zeolit BUKAN bahan campuran (OUTPUT3 §3.4.2, Tabel 4.2).

    Uji ini mengunci perbaikan Temuan - Hebel Zeolit Bukan Agregat.
    """

    def test_komponen_hanya_empat(self):
        nama = {r["Material"] for r in kmp.komponen(kmp.rancangan_campuran(1.0))}
        self.assertEqual(nama, {"Semen OPC", "Lumpur IPAL", "Batu Sirtu", "Air"})

    def test_tidak_ada_hebel_atau_zeolit_di_campuran(self):
        h = kmp.rancangan_campuran(1.0)
        gabung = " ".join(str(k) for k in h.keys()).lower()
        self.assertNotIn("hebel", gabung)
        self.assertNotIn("zeolit", gabung)

    def test_catatan_agregat_menjelaskan(self):
        h = kmp.rancangan_campuran(1.0)
        self.assertIn("batu sirtu", h["catatan_agregat"].lower())
        self.assertIn("lapisan terpisah", h["catatan_agregat"].lower())


class MasukanTidakSah(unittest.TestCase):
    """Masukan tidak sah harus gagal keras, bukan diam-diam menghasilkan angka."""

    def test_volume_nol_atau_negatif(self):
        for v in (0.0, -1.0):
            with self.subTest(volume=v):
                with self.assertRaises(ValueError):
                    kmp.rancangan_campuran(v)

    def test_substitusi_di_luar_rentang(self):
        for s in (-1.0, 101.0):
            with self.subTest(substitusi=s):
                with self.assertRaises(ValueError):
                    kmp.rancangan_campuran(1.0, substitusi_ipal_persen=s)

    def test_faktor_air_pengikat_nol(self):
        with self.assertRaises(ValueError):
            kmp.rancangan_campuran(1.0, faktor_air_pengikat=0.0)

    def test_berat_satuan_negatif(self):
        with self.assertRaises(ValueError):
            kmp.rancangan_campuran(1.0, berat_satuan_kg_m3=-100.0)

    def test_nilai_tak_hingga_ditolak(self):
        with self.assertRaises(ValueError):
            kmp.rancangan_campuran(float("inf"))
        with self.assertRaises(ValueError):
            kmp.rancangan_campuran(1.0, substitusi_ipal_persen=float("nan"))


class KonsistensiSatuan(unittest.TestCase):
    """Satuan harus konsisten: kg/m3 x m3 = kg, dan massa berskala linear."""

    def test_massa_total_dari_berat_satuan_dan_volume(self):
        self.assertAlmostEqual(kmp.massa_total_kg(1850.0, 2.0), 3700.0, delta=1e-9)

    def test_massa_berskala_linear_terhadap_volume(self):
        satu = kmp.rancangan_campuran(1.0)
        sepuluh = kmp.rancangan_campuran(10.0)
        for kunci in ("massa_total_kg", "massa_pengikat_kg", "massa_semen_kg",
                      "massa_ipal_kg", "massa_agregat_kg", "massa_air_kg"):
            with self.subTest(kunci=kunci):
                self.assertAlmostEqual(sepuluh[kunci], satu[kunci] * 10.0, delta=1e-6)

    def test_proporsi_tidak_bergantung_volume(self):
        satu = kmp.rancangan_campuran(1.0)
        seratus = kmp.rancangan_campuran(100.0)
        self.assertAlmostEqual(
            satu["proporsi_semen_persen"], seratus["proporsi_semen_persen"], delta=1e-9
        )

    def test_berat_satuan_mengubah_massa_bukan_proporsi(self):
        a = kmp.rancangan_campuran(1.0, berat_satuan_kg_m3=1850.0)
        b = kmp.rancangan_campuran(1.0, berat_satuan_kg_m3=1280.0)
        self.assertLess(b["massa_total_kg"], a["massa_total_kg"])
        self.assertAlmostEqual(
            a["proporsi_agregat_persen"], b["proporsi_agregat_persen"], delta=1e-9
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
