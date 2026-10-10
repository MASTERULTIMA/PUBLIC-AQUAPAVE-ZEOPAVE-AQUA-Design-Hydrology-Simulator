"""
Uji reproduksi — jaring pengaman sebelum refaktor.

APA YANG DIUJI BERKAS INI
    Apakah mesin perhitungan mereproduksi kembali angka yang sudah diterima
    proyek, bila diberi masukan yang sama.

APA YANG TIDAK DIUJI BERKAS INI
    Kebenaran ilmiah hasil laboratorium itu sendiri. Uji ini adalah
    VERIFIKASI perangkat lunak, bukan VALIDASI eksperimental (ADR-004).
    Lulusnya seluruh uji di sini tidak membuktikan apa pun tentang bahan;
    ia hanya membuktikan perangkat lunak masih menghitung hal yang sama.

Jalankan dari akar proyek:

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import geometri, hidrologi, kuat_tekan, permeabilitas, retensi  # noqa: E402
from data import akses  # noqa: E402


class KuatTekan(unittest.TestCase):
    """
    Acuan  : OUTPUT3 Tabel 4.1
    Status : terukur — hasil pengujian laboratorium
    Toleransi: 0,01 MPa (naskah melaporkan dua desimal)
    """

    def test_tiap_benda_uji(self):
        harapan = [13.31, 13.21, 13.04]
        for b, diharap in zip(akses.dataset_kuat_tekan(), harapan):
            with self.subTest(benda_uji=b["nama"]):
                fc = kuat_tekan.kuat_tekan_mpa(b["beban_kN"], kuat_tekan.LAB_LUAS_M2)
                self.assertAlmostEqual(fc, diharap, delta=0.01)

    def test_rerata_13_19_mpa_umur_7_hari(self):
        """Hasil utama penelitian (ADR-005)."""
        fc = [
            kuat_tekan.kuat_tekan_mpa(b["beban_kN"], kuat_tekan.LAB_LUAS_M2)
            for b in akses.dataset_kuat_tekan()
        ]
        self.assertAlmostEqual(kuat_tekan.ringkasan(fc)["rerata"], 13.19, delta=0.01)

    def test_luas_silinder_150mm(self):
        """A = 0,017671 m2 (OUTPUT3 Persamaan 3.3)."""
        self.assertAlmostEqual(
            kuat_tekan.luas_silinder_m2(150.0), 0.017671, delta=1e-6
        )

    def test_ambang_literatur_bukan_sni(self):
        """Ambang lalu lintas ringan 5 MPa berasal dari Govedarica, bukan SNI."""
        a = kuat_tekan.ambang_lalu_lintas_ringan()
        self.assertEqual(a["nilai"], 5.0)
        self.assertIn("Govedarica", a["sumber"])

    def test_hasil_utama_di_atas_ambang(self):
        self.assertGreater(13.19, kuat_tekan.ambang_lalu_lintas_ringan()["nilai"])


class Permeabilitas(unittest.TestCase):
    """
    Acuan  : OUTPUT3 §4.5, Persamaan 4.9 dan 4.10
    Metode : constant head, dikonfirmasi tim eksperimen (ADR-006)
    Status : terukur — k dihitung dari kecepatan terukur dan geometri benda uji
    Toleransi: 0,001 cm/detik
    """

    L = permeabilitas.LAB_TEBAL_CM
    A = permeabilitas.LAB_LUAS_CM2
    H = permeabilitas.LAB_TINGGI_TEKAN_CM
    V = permeabilitas.LAB_KECEPATAN_CM_PER_DETIK
    K = permeabilitas.LAB_K_CM_PER_DETIK

    def test_debit_dari_kecepatan(self):
        """Q = v * A = 5 x 225 = 1125 cm3/detik (Persamaan 4.9)."""
        self.assertAlmostEqual(
            permeabilitas.debit_dari_kecepatan(self.V, self.A), 1125.0, delta=1e-9
        )

    def test_bentuk_debit(self):
        """k = Q*L/(A*h) = 1,667 cm/detik (Persamaan 4.10)."""
        k = permeabilitas.koefisien_dari_debit(1125.0, self.L, self.A, self.H)
        self.assertAlmostEqual(k, self.K, delta=0.001)

    def test_bentuk_volume_setara(self):
        """k = V*L/(A*h*t) memberi hasil sama untuk t berapa pun."""
        for t in (1.0, 10.0, 60.0, 3600.0):
            with self.subTest(t_detik=t):
                k = permeabilitas.koefisien_dari_volume(
                    1125.0 * t, self.L, self.A, self.H, t
                )
                self.assertAlmostEqual(k, self.K, delta=0.001)

    def test_bentuk_kecepatan_setara(self):
        """k = v*L/h — luas hilang karena v sudah fluks per satuan luas."""
        k = permeabilitas.koefisien_dari_kecepatan(self.V, self.L, self.H)
        self.assertAlmostEqual(k, self.K, delta=0.001)

    def test_konsistensi_darcy(self):
        """v = k * i dengan i = h/L. Rangkaian harus konsisten."""
        i = permeabilitas.gradien_hidraulik(self.H, self.L)
        self.assertAlmostEqual(i, 3.0, delta=1e-9)
        k = permeabilitas.koefisien_dari_kecepatan(self.V, self.L, self.H)
        self.assertAlmostEqual(k * i, self.V, delta=0.001)

    def test_tidak_ada_pembagi_waktu_ganda(self):
        """
        Menyalahgunakan bentuk debit seolah bentuk volume dengan t=60 harus
        memberi hasil BERBEDA. Uji ini mengunci kekeliruan notasi lama.
        """
        benar = permeabilitas.koefisien_dari_debit(1125.0, self.L, self.A, self.H)
        keliru = permeabilitas.koefisien_dari_volume(1125.0, self.L, self.A, self.H, 60.0)
        self.assertNotAlmostEqual(benar, keliru, delta=0.001)

    def test_pembanding_literatur_bukan_ambang_karangan(self):
        """0,45 dan 0,60 cm/detik tidak boleh muncul sebagai pembanding."""
        nilai = {p["nilai"] for p in permeabilitas.pembanding_literatur()}
        self.assertNotIn(0.45, nilai)
        self.assertNotIn(0.60, nilai)
        self.assertIn(0.01, nilai)

    def test_masukan_tidak_sah_ditolak(self):
        for kwargs in (
            dict(debit_cm3_per_detik=0, tebal_cm=2, luas_cm2=225, tinggi_tekan_cm=6),
            dict(debit_cm3_per_detik=1125, tebal_cm=2, luas_cm2=0, tinggi_tekan_cm=6),
            dict(debit_cm3_per_detik=1125, tebal_cm=-2, luas_cm2=225, tinggi_tekan_cm=6),
        ):
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError):
                    permeabilitas.koefisien_dari_debit(**kwargs)


class Geometri(unittest.TestCase):
    """
    Acuan  : OUTPUT3 §4.5 — benda uji PERSEGI 15 x 15 cm, A = 225 cm2
    Status : terukur (dimensi benda uji)
    """

    def test_persegi_lab_225_cm2(self):
        A = geometri.luas_penampang(
            geometri.PERSEGI_PANJANG, lebar_cm=15.0, panjang_cm=15.0
        )
        self.assertAlmostEqual(A, 225.0, delta=1e-9)

    def test_luas_langsung(self):
        A = geometri.luas_penampang(geometri.LANGSUNG, luas_cm2=225.0)
        self.assertAlmostEqual(A, 225.0, delta=1e-9)

    def test_kompatibilitas_mundur_silinder(self):
        """Perilaku lama (diameter 150 mm) harus tidak berubah."""
        self.assertEqual(geometri.BENTUK_BAWAAN, geometri.LINGKARAN)
        A = geometri.luas_penampang(geometri.LINGKARAN, diameter_cm=15.0)
        self.assertAlmostEqual(A, 176.71, delta=0.01)

    def test_selisih_geometri_nyata(self):
        """Memakai silinder untuk benda uji persegi keliru sekitar 21%."""
        bulat = geometri.luas_penampang(geometri.LINGKARAN, diameter_cm=15.0)
        persegi = geometri.luas_penampang(
            geometri.PERSEGI_PANJANG, lebar_cm=15.0, panjang_cm=15.0
        )
        self.assertAlmostEqual((persegi - bulat) / persegi * 100.0, 21.46, delta=0.1)

    def test_bentuk_tak_dikenal_ditolak(self):
        with self.assertRaises(ValueError):
            geometri.luas_penampang("segitiga", sisi_cm=10)


class Retensi(unittest.TestCase):
    """
    Acuan  : OUTPUT3 Tabel 4.3 dan §4.4, Persamaan 4.4 sampai 4.8
    Status : terukur — tiga pengujian simulasi curah hujan
    Toleransi: 0,05 poin persen
    """

    def test_retensi_tiap_uji(self):
        harapan = [40.0, 41.0, 39.0]
        for u, diharap in zip(akses.dataset_retensi(), harapan):
            with self.subTest(uji=u["nama"]):
                r = retensi.retensi_persen(u["input_ml"], u["output_ml"])
                self.assertAlmostEqual(r, diharap, delta=0.05)

    def test_rerata_40_persen(self):
        """Nilai terkoreksi 40,0% — bukan 39,7% dari pelaporan lama."""
        r = retensi.ringkasan_lab()
        self.assertAlmostEqual(r["rerata"], 40.0, delta=0.05)

    def test_simpangan_baku_dan_cv(self):
        """SD 1,0% dan CV 2,5% seperti dilaporkan §4.4."""
        r = retensi.ringkasan_lab()
        self.assertAlmostEqual(r["simpangan_baku"], 1.0, delta=0.05)
        self.assertAlmostEqual(r["cv_persen"], 2.5, delta=0.05)

    def test_volume_terserap(self):
        self.assertAlmostEqual(
            retensi.volume_terserap_ml(1000, 600), 400.0, delta=1e-9
        )

    def test_keluaran_melebihi_masukan_ditolak(self):
        with self.assertRaises(ValueError):
            retensi.retensi_persen(1000, 1200)


class Hidrologi(unittest.TestCase):
    """
    Acuan  : OUTPUT3 §4.6 — skenario 1.000 m2 pada 50 mm/jam
    Status : MODEL — skenario perhitungan, bukan pengukuran lapangan
    Toleransi: 1 liter
    """

    def test_skenario_terdokumentasi(self):
        s = hidrologi.skenario(
            hidrologi.ACUAN_INTENSITAS_MM_PER_JAM,
            hidrologi.ACUAN_LUAS_M2,
            hidrologi.ACUAN_DURASI_JAM,
            retensi.LAB_RETENSI_RERATA_PERSEN,
        )
        self.assertAlmostEqual(
            s["air_jatuh_liter"], hidrologi.ACUAN_AIR_JATUH_LITER, delta=1.0
        )
        self.assertAlmostEqual(
            s["air_tertahan_liter"], hidrologi.ACUAN_AIR_TERTAHAN_LITER, delta=1.0
        )

    def test_status_bukti_model(self):
        """Keluaran hidrologi tidak boleh menyamar sebagai hasil pengukuran."""
        s = hidrologi.skenario(50, 1000, 1, 40.0)
        self.assertEqual(s["status_bukti"], "model")
        self.assertIn("bukan hasil pengukuran lapangan", s["catatan"])

    def test_perbandingan_simetris(self):
        """
        Dengan koefisien limpasan sama pada kedua permukaan, reduksi limpasan
        harus sama dengan tingkat retensi. Aplikasi lama menghasilkan 29,1%
        karena membandingkan C=0,85 terhadap C efektif 1,0.
        """
        s = hidrologi.skenario(50, 1000, 1, 40.0, koefisien_limpasan_konvensional=0.85)
        self.assertAlmostEqual(s["reduksi_limpasan_persen"], 40.0, delta=0.1)

    def test_koefisien_limpasan_di_luar_rentang_ditolak(self):
        with self.assertRaises(ValueError):
            hidrologi.skenario(50, 1000, 1, 40.0, koefisien_limpasan_konvensional=1.5)


class Provenans(unittest.TestCase):
    """Penjaga integritas: konstanta yang dihapus tidak boleh kembali."""

    def test_konstanta_dihapus_tetap_terkunci(self):
        for nama in ("optimasi_material_85", "ambang_permeabilitas_045",
                     "porositas_dasar_215", "kuat_tekan_205_035"):
            with self.subTest(konstanta=nama):
                with self.assertRaises(akses.NilaiDihapus):
                    akses.pastikan_tidak_dihapus(nama)

    def test_angka_kunci_konsisten_dengan_core(self):
        """konstanta.py dan mesin perhitungan tidak boleh berbeda."""
        kunci = {a["nama"]: a["nilai"] for a in akses.angka_kunci()}
        fc = [
            kuat_tekan.kuat_tekan_mpa(b["beban_kN"], kuat_tekan.LAB_LUAS_M2)
            for b in akses.dataset_kuat_tekan()
        ]
        self.assertAlmostEqual(
            kunci["KUAT_TEKAN_7_HARI"], kuat_tekan.ringkasan(fc)["rerata"], delta=0.01
        )
        self.assertAlmostEqual(
            kunci["RETENSI_RERATA"], retensi.ringkasan_lab()["rerata"], delta=0.05
        )
        self.assertAlmostEqual(
            kunci["PERMEABILITAS"],
            permeabilitas.koefisien_dari_kecepatan(5.0, 2.0, 6.0),
            delta=0.001,
        )

    def test_sdg_set_final(self):
        self.assertEqual(akses.sdg_didukung(), (9, 11, 12, 13))

    def test_status_bukti_angka_kunci(self):
        """Keempat angka kunci harus berstatus terukur."""
        for a in akses.angka_kunci():
            with self.subTest(besaran=a["nama"]):
                self.assertEqual(a["status"], akses.TERUKUR)
                self.assertFalse(a["perlu_kualifikasi"])

    def test_porositas_tetap_target(self):
        """18-25% adalah target rancangan, tidak pernah diukur."""
        self.assertEqual(akses.status("POROSITAS_TARGET_MIN"), akses.TARGET)
        self.assertEqual(akses.status("POROSITAS_TARGET_MAKS"), akses.TARGET)

    def test_estimasi_14_hari_bukan_hasil(self):
        """15,00 MPa diturunkan ke ASUMSI dan tidak boleh dipakai sebagai hasil."""
        self.assertEqual(akses.status("KUAT_TEKAN_14_HARI"), akses.ASUMSI)


if __name__ == "__main__":
    unittest.main(verbosity=2)
