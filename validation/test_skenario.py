"""
Uji keadaan skenario dan aliran data bersama (S3).

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

Dijalankan bersama uji lain:

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import emisi, kuat_tekan  # noqa: E402
from data import akses  # noqa: E402
from scenario import state as skenario  # noqa: E402


class SesiPalsu:
    """
    Pengganti Streamlit untuk pengujian.

    Modul skenario menerima `st` sebagai argumen justru agar dapat diuji tanpa
    menjalankan Streamlit sama sekali.
    """

    def __init__(self):
        self.session_state = {}


class SkenarioTunggal(unittest.TestCase):
    """
    S3-A — substitusi IPAL harus punya SATU nilai kanonik per skenario.

    Sebelum S3 nilai ini dimasukkan di tiga tempat berbeda dan bisa berbeda-beda
    tanpa disadari. Sejak S4 nilai kanonik itu hidup di dalam koleksi skenario,
    sehingga uji di bawah memakai antarmuka koleksi.
    """

    def setUp(self):
        self.st = SesiPalsu()

    def test_bawaan_mengikuti_acuan_penelitian(self):
        s = skenario.skenario_aktif(self.st)
        self.assertAlmostEqual(s.substitusi_ipal_persen, 15.0, delta=1e-9)
        self.assertTrue(skenario.cocok_konfigurasi_uji(s))

    def test_bawaan_konsisten_dengan_konstanta(self):
        """Nilai bawaan tidak boleh menyimpang dari konstanta.py."""
        s = skenario.skenario_aktif(self.st)
        self.assertAlmostEqual(
            s.substitusi_ipal_persen, akses.nilai("SUBSTITUSI_IPAL"), delta=1e-9
        )
        self.assertAlmostEqual(
            s.faktor_air_pengikat, akses.nilai("FAKTOR_AIR_PENGIKAT"), delta=1e-9
        )

    def test_hanya_satu_kunci_session_state(self):
        """Tidak ada salinan tersembunyi di kunci lain."""
        skenario.tambah_kustom(self.st)
        skenario.perbarui_aktif(self.st, substitusi_ipal_persen=20.0)
        self.assertEqual(list(self.st.session_state.keys()), [skenario.KUNCI])

    def test_pembaruan_terlihat_oleh_seluruh_pembaca(self):
        """
        Inti S3-A: setelah nilai diubah sekali, setiap pembaca melihat nilai
        yang sama. Tidak mungkin dua tab menghitung dengan angka berbeda.
        """
        skenario.tambah_kustom(self.st)
        skenario.perbarui_aktif(self.st, substitusi_ipal_persen=22.0)
        pembaca_tab1 = skenario.skenario_aktif(self.st).substitusi_ipal_persen
        pembaca_tab5 = skenario.skenario_aktif(self.st).substitusi_ipal_persen
        pembaca_tab6 = skenario.skenario_aktif(self.st).substitusi_ipal_persen
        self.assertEqual(pembaca_tab1, 22.0)
        self.assertEqual(pembaca_tab1, pembaca_tab5)
        self.assertEqual(pembaca_tab5, pembaca_tab6)

    def test_skenario_kustom_terdeteksi(self):
        skenario.tambah_kustom(self.st)
        skenario.perbarui_aktif(self.st, substitusi_ipal_persen=20.0)
        self.assertFalse(
            skenario.cocok_konfigurasi_uji(skenario.skenario_aktif(self.st))
        )

    def test_pulihkan_acuan(self):
        skenario.tambah_kustom(self.st)
        skenario.perbarui_aktif(
            self.st, substitusi_ipal_persen=25.0, faktor_air_pengikat=0.55
        )
        skenario.pulihkan_acuan(self.st)
        s = skenario.skenario_aktif(self.st)
        self.assertTrue(skenario.cocok_konfigurasi_uji(s))
        self.assertAlmostEqual(s.substitusi_ipal_persen, 15.0, delta=1e-9)

    def test_bidang_tak_dikenal_ditolak(self):
        skenario.tambah_kustom(self.st)
        with self.assertRaises(AttributeError):
            skenario.perbarui_aktif(self.st, bidang_ngawur=1)


class AliranDataEmisi(unittest.TestCase):
    """
    S3-B — Tab 5 dan Tab 6 harus membaca hasil yang sama.

    Sebelumnya Tab 6 meminjam variabel lokal milik Tab 5, sehingga aplikasi
    bergantung pada urutan eksekusi.
    """

    def test_neraca_deterministik(self):
        a = emisi.neraca(10.0, 15.0, 0.85, 0.05)
        b = emisi.neraca(10.0, 15.0, 0.85, 0.05)
        self.assertEqual(a, b)

    def test_neraca_dari_skenario(self):
        """Satu skenario menghasilkan satu neraca, dipakai bersama tab mana pun."""
        st = SesiPalsu()
        s = skenario.skenario_aktif(st)
        hasil = emisi.neraca(
            s.total_pengikat_ton, s.substitusi_ipal_persen,
            s.co2_per_ton_semen, s.co2_per_ton_ipal,
        )
        self.assertAlmostEqual(hasil["co2_konvensional_ton"], 8.5, delta=0.01)
        self.assertAlmostEqual(hasil["co2_zeopave_ton"], 7.3, delta=0.01)
        self.assertAlmostEqual(hasil["reduksi_persen"], 14.1, delta=0.1)

    def test_substitusi_nol_tidak_menghemat(self):
        h = emisi.neraca(10.0, 0.0, 0.85, 0.05)
        self.assertAlmostEqual(h["co2_dihemat_ton"], 0.0, delta=1e-9)
        self.assertAlmostEqual(h["reduksi_persen"], 0.0, delta=1e-9)

    def test_neraca_massa_tertutup(self):
        h = emisi.neraca(10.0, 15.0, 0.85, 0.05)
        self.assertAlmostEqual(
            h["semen_terpakai_ton"] + h["ipal_terpakai_ton"],
            h["total_pengikat_ton"], delta=1e-9,
        )

    def test_masukan_tidak_sah_ditolak(self):
        with self.assertRaises(ValueError):
            emisi.neraca(10.0, 150.0, 0.85, 0.05)     # substitusi > 100%
        with self.assertRaises(ValueError):
            emisi.neraca(0.0, 15.0, 0.85, 0.05)       # pengikat nol
        with self.assertRaises(ValueError):
            emisi.neraca(10.0, 15.0, 0.85, -0.1)      # faktor negatif


class KuatTekanTidakTertimpa(unittest.TestCase):
    """
    S3-C — hasil utama 13,19 MPa tidak boleh tergantikan estimasi konversi umur.
    """

    FAKTOR_UMUR = {7: 0.65, 14: 0.879, 21: 0.95, 28: 1.00, 56: 1.09, 90: 1.15}

    def _rerata_terukur(self):
        fc = [
            kuat_tekan.kuat_tekan_mpa(b["beban_kN"], kuat_tekan.LAB_LUAS_M2)
            for b in akses.dataset_kuat_tekan()
        ]
        return kuat_tekan.ringkasan(fc)["rerata"]

    def test_hasil_utama_tetap_13_19(self):
        self.assertAlmostEqual(self._rerata_terukur(), 13.19, delta=0.01)

    def test_core_tidak_menyediakan_konversi_umur(self):
        """
        core/kuat_tekan.py sengaja TIDAK mengekspor fungsi konversi umur,
        sehingga estimasi tidak dapat masuk diam-diam ke jalur hasil utama.
        """
        for nama in dir(kuat_tekan):
            self.assertNotIn(
                "konversi", nama.lower(),
                f"core/kuat_tekan.py tidak boleh mengekspor konversi umur: {nama}",
            )

    def test_estimasi_15_mpa_bukan_hasil_utama(self):
        """15,00 MPa berstatus asumsi dan tidak muncul di angka kunci."""
        self.assertEqual(akses.status("KUAT_TEKAN_14_HARI"), akses.ASUMSI)
        kunci = {a["nama"] for a in akses.angka_kunci()}
        self.assertNotIn("KUAT_TEKAN_14_HARI", kunci)
        self.assertIn("KUAT_TEKAN_7_HARI", kunci)

    def test_estimasi_umur_tidak_mengubah_nilai_terukur(self):
        """
        Menerapkan faktor umur menghasilkan angka BARU; nilai terukur tetap utuh.
        """
        terukur = self._rerata_terukur()
        estimasi = terukur / self.FAKTOR_UMUR[7]
        self.assertAlmostEqual(self._rerata_terukur(), terukur, delta=1e-12)
        self.assertNotAlmostEqual(estimasi, terukur, delta=0.5)

    def test_hasil_utama_dibandingkan_ambang_pustaka(self):
        """Perbandingan memakai ambang 5 MPa dari pustaka, bukan target sidebar."""
        ambang = kuat_tekan.ambang_lalu_lintas_ringan()
        self.assertEqual(ambang["nilai"], 5.0)
        self.assertGreater(self._rerata_terukur(), ambang["nilai"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
