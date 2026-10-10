"""
Uji koleksi skenario, resolusi keluaran, dan perbandingan (S4).

VERIFIKASI perangkat lunak, bukan validasi eksperimental (ADR-004).

Seluruh operasi session_state diuji tanpa menjalankan Streamlit, memakai objek
sesi palsu — modul skenario memang menerima `st` sebagai argumen untuk itu.
"""

from __future__ import annotations

import os
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scenario import resolusi as R, state as S  # noqa: E402
from scenario.keluaran import (  # noqa: E402
    LABEL,
    URUTAN,
    Keluaran,
    Ketersediaan,
    OutputID,
    StatusBukti,
    dapat_dibandingkan,
    selisih,
    tersedia,
    tidak_tersedia,
)

TERIKAT = (OutputID.COMPRESSIVE_STRENGTH, OutputID.PERMEABILITY, OutputID.RETENTION)
DETERMINISTIK = (OutputID.MIX_TOTAL_MASS, OutputID.IPAL_MASS, OutputID.CO2_TOTAL)


class SesiPalsu:
    """Pengganti Streamlit — membuktikan lapisan skenario dapat diuji mandiri."""

    def __init__(self):
        self.session_state = {}


class KoleksiSkenario(unittest.TestCase):
    """S4-A dan S4-H butir 1, 2, 3, 8."""

    def setUp(self):
        self.st = SesiPalsu()

    def test_acuan_selalu_ada(self):
        k = S.muat(self.st)
        self.assertIn(S.ACUAN, k.nama_terpakai())
        self.assertEqual(k.aktif, S.ACUAN)

    def test_acuan_tetap_ada_setelah_semua_kustom_dihapus(self):
        a = S.tambah_kustom(self.st)
        S.hapus_kustom(self.st, a)
        self.assertEqual(S.muat(self.st).nama_terpakai(), [S.ACUAN])

    def test_acuan_tidak_dapat_diubah(self):
        S.pilih(self.st, S.ACUAN)
        with self.assertRaises(ValueError):
            S.perbarui_aktif(self.st, substitusi_ipal_persen=99.0)

    def test_acuan_tidak_dapat_dihapus(self):
        with self.assertRaises(ValueError):
            S.hapus_kustom(self.st, S.ACUAN)

    def test_acuan_kebal_mutasi_tidak_langsung(self):
        """Memutasi objek acuan yang diambil tidak boleh mencemari koleksi."""
        k = S.muat(self.st)
        diambil = k.acuan
        diambil.substitusi_ipal_persen = 99.0
        self.assertAlmostEqual(k.acuan.substitusi_ipal_persen, 15.0, delta=1e-9)

    def test_pengenal_skenario_unik(self):
        nama = [S.tambah_kustom(self.st) for _ in range(3)]
        self.assertEqual(nama, ["A", "B", "C"])
        self.assertEqual(len(set(nama)), 3)
        self.assertEqual(len(S.muat(self.st).kustom), 3)

    def test_slot_penuh_ditolak(self):
        for _ in range(3):
            S.tambah_kustom(self.st)
        self.assertTrue(S.muat(self.st).penuh())
        with self.assertRaises(RuntimeError):
            S.tambah_kustom(self.st)

    def test_hapus_satu_tidak_mengganggu_yang_lain(self):
        a = S.tambah_kustom(self.st)
        S.perbarui_aktif(self.st, substitusi_ipal_persen=20.0)
        b = S.tambah_kustom(self.st)
        S.perbarui_aktif(self.st, substitusi_ipal_persen=25.0)
        S.hapus_kustom(self.st, a)
        sisa = S.muat(self.st)
        self.assertNotIn(a, sisa.kustom)
        self.assertIn(b, sisa.kustom)
        self.assertAlmostEqual(sisa.ambil(b).substitusi_ipal_persen, 25.0, delta=1e-9)

    def test_hapus_yang_aktif_kembali_ke_acuan(self):
        a = S.tambah_kustom(self.st)
        S.hapus_kustom(self.st, a)
        self.assertEqual(S.muat(self.st).aktif, S.ACUAN)

    def test_hanya_satu_kunci_session_state(self):
        S.tambah_kustom(self.st)
        S.perbarui_aktif(self.st, substitusi_ipal_persen=18.0)
        self.assertEqual(list(self.st.session_state.keys()), [S.KUNCI])


class IdentitasKonfigurasi(unittest.TestCase):
    """S4-B — kecocokan ditentukan perbandingan terstruktur, bukan satu boolean."""

    def test_acuan_cocok_seluruh_parameter(self):
        baris = S.bandingkan_konfigurasi(S.acuan_penelitian())
        self.assertEqual(len(baris), len(S.PARAMETER_KONFIGURASI_UJI))
        self.assertTrue(all(b["cocok"] for b in baris))
        self.assertTrue(S.cocok_konfigurasi_uji(S.acuan_penelitian()))

    def test_setiap_parameter_komposisi_memutus_kecocokan(self):
        """Bukan hanya substitusi IPAL: setiap parameter uji berpengaruh."""
        for nama, _, _ in S.PARAMETER_KONFIGURASI_UJI:
            with self.subTest(parameter=nama):
                sk = replace(S.acuan_penelitian(), **{nama: getattr(S.acuan_penelitian(), nama) + 1.0})
                self.assertFalse(S.cocok_konfigurasi_uji(sk))

    def test_parameter_non_komposisi_tidak_memutus(self):
        """Luas area dan intensitas hujan bukan bagian konfigurasi uji."""
        sk = replace(
            S.acuan_penelitian(), luas_area_m2=5000.0,
            intensitas_hujan_mm_per_jam=90.0, total_pengikat_ton=50.0,
        )
        self.assertTrue(S.cocok_konfigurasi_uji(sk))

    def test_alasan_berbeda_menjelaskan(self):
        sk = replace(S.acuan_penelitian(), substitusi_ipal_persen=22.0)
        alasan = S.alasan_berbeda(sk)
        self.assertEqual(len(alasan), 1)
        self.assertIn("Substitusi", alasan[0])


class ModelKeluaran(unittest.TestCase):
    """S4-C — status bukti dan ketersediaan adalah dua hal berbeda."""

    def test_tidak_tersedia_tanpa_nilai_dan_tanpa_status(self):
        k = tidak_tersedia(OutputID.PERMEABILITY, "cm/detik")
        self.assertFalse(k.tersedia)
        self.assertIsNone(k.nilai)
        self.assertIsNone(k.status_bukti)

    def test_tidak_tersedia_menolak_nilai(self):
        with self.assertRaises(ValueError):
            Keluaran(
                id=OutputID.RETENTION, satuan="%",
                ketersediaan=Ketersediaan.TIDAK_TERSEDIA, nilai=40.0,
            )

    def test_tidak_tersedia_menolak_status_bukti(self):
        with self.assertRaises(ValueError):
            Keluaran(
                id=OutputID.RETENTION, satuan="%",
                ketersediaan=Ketersediaan.TIDAK_TERSEDIA,
                status_bukti=StatusBukti.TERUKUR,
            )

    def test_tersedia_wajib_punya_nilai_dan_status(self):
        with self.assertRaises(ValueError):
            Keluaran(
                id=OutputID.RETENTION, satuan="%",
                ketersediaan=Ketersediaan.TERSEDIA,
            )

    def test_pengenal_terpisah_dari_label(self):
        """Mengubah kata di layar tidak boleh mematahkan logika."""
        for oid in OutputID:
            with self.subTest(oid=oid):
                self.assertIn(oid, LABEL)
                self.assertNotEqual(oid.value, LABEL[oid])

    def test_urutan_memuat_seluruh_keluaran(self):
        self.assertEqual(set(URUTAN), set(OutputID))


class ResolusiIlmiah(unittest.TestCase):
    """S4-D dan S4-H butir 4, 5, 6 — pengaman inti."""

    def setUp(self):
        self.acuan = R.resolusi(S.acuan_penelitian())
        self.kustom = R.resolusi(
            replace(S.acuan_penelitian(), substitusi_ipal_persen=22.0)
        )

    def test_acuan_menampilkan_hasil_terukur(self):
        harapan = {
            OutputID.COMPRESSIVE_STRENGTH: 13.19,
            OutputID.PERMEABILITY: 1.667,
            OutputID.RETENTION: 40.0,
        }
        for oid, nilai in harapan.items():
            with self.subTest(oid=oid):
                k = self.acuan[oid]
                self.assertTrue(k.tersedia)
                self.assertIs(k.status_bukti, StatusBukti.TERUKUR)
                self.assertAlmostEqual(k.nilai, nilai, delta=0.01)

    def test_kustom_tidak_mewarisi_hasil_ukur(self):
        """Inti S4: hasil laboratorium melekat pada konfigurasi, bukan aplikasi."""
        for oid in TERIKAT:
            with self.subTest(oid=oid):
                k = self.kustom[oid]
                self.assertFalse(k.tersedia)
                self.assertIsNone(k.nilai)
                self.assertIsNone(k.status_bukti)

    def test_keluaran_deterministik_dihitung_ulang(self):
        self.assertAlmostEqual(
            self.acuan[OutputID.MIX_TOTAL_MASS].nilai,
            self.kustom[OutputID.MIX_TOTAL_MASS].nilai, delta=1e-9,
        )
        self.assertGreater(
            self.kustom[OutputID.IPAL_MASS].nilai,
            self.acuan[OutputID.IPAL_MASS].nilai,
        )
        self.assertLess(
            self.kustom[OutputID.CO2_TOTAL].nilai,
            self.acuan[OutputID.CO2_TOTAL].nilai,
        )
        for oid in DETERMINISTIK:
            with self.subTest(oid=oid):
                self.assertTrue(self.kustom[oid].tersedia)
                self.assertIs(self.kustom[oid].status_bukti, StatusBukti.DETERMINISTIK)

    def test_ketidaktersediaan_merambat_ke_air_tertahan(self):
        """Air tertahan diturunkan dari retensi; bila retensi hilang, ia ikut hilang."""
        self.assertTrue(self.acuan[OutputID.RUNOFF].tersedia)
        self.assertFalse(self.kustom[OutputID.RUNOFF].tersedia)

    def test_keluaran_tidak_tersedia_dirender_eksplisit(self):
        for oid in TERIKAT:
            with self.subTest(oid=oid):
                teks = self.kustom[oid].teks_nilai()
                self.assertIn("Belum tersedia", teks)
                self.assertNotEqual(teks.strip(), "")

    def test_catatan_menyebut_alasan_perbedaan(self):
        self.assertIn("Substitusi", self.kustom[OutputID.PERMEABILITY].catatan)

    def test_kustom_identik_acuan_tetap_mewarisi(self):
        """Skenario kustom yang komposisinya identik acuan tetap sah."""
        sama = R.resolusi(replace(S.acuan_penelitian(), luas_area_m2=2000.0))
        for oid in TERIKAT:
            with self.subTest(oid=oid):
                self.assertTrue(sama[oid].tersedia)

    def test_seluruh_keluaran_terselesaikan(self):
        for oid in OutputID:
            with self.subTest(oid=oid):
                self.assertIn(oid, self.acuan)
                self.assertIn(oid, self.kustom)


class Perbandingan(unittest.TestCase):
    """S4-E dan S4-H butir 7 — selisih hanya untuk pasangan yang sebanding."""

    def setUp(self):
        self.acuan = R.resolusi(S.acuan_penelitian())
        self.kustom = R.resolusi(
            replace(S.acuan_penelitian(), substitusi_ipal_persen=22.0)
        )

    def test_selisih_untuk_deterministik(self):
        d = selisih(self.acuan[OutputID.IPAL_MASS], self.kustom[OutputID.IPAL_MASS])
        self.assertIsNotNone(d)
        self.assertGreater(d["delta"], 0.0)

    def test_tidak_ada_selisih_bila_salah_satu_tidak_tersedia(self):
        for oid in TERIKAT:
            with self.subTest(oid=oid):
                self.assertIsNone(selisih(self.acuan[oid], self.kustom[oid]))

    def test_tidak_ada_selisih_antar_status_bukti_berbeda(self):
        a = tersedia(OutputID.RETENTION, 40.0, "%", StatusBukti.TERUKUR)
        b = tersedia(OutputID.RETENTION, 35.0, "%", StatusBukti.DETERMINISTIK)
        boleh, alasan = dapat_dibandingkan(a, b)
        self.assertFalse(boleh)
        self.assertIn("status bukti", alasan)
        self.assertIsNone(selisih(a, b))

    def test_tidak_ada_selisih_antar_satuan_berbeda(self):
        a = tersedia(OutputID.RETENTION, 40.0, "%", StatusBukti.TERUKUR)
        b = tersedia(OutputID.RETENTION, 400.0, "ml", StatusBukti.TERUKUR)
        boleh, alasan = dapat_dibandingkan(a, b)
        self.assertFalse(boleh)
        self.assertIn("satuan", alasan)

    def test_tidak_ada_selisih_antar_keluaran_berbeda(self):
        a = tersedia(OutputID.RETENTION, 40.0, "%", StatusBukti.TERUKUR)
        b = tersedia(OutputID.POROSITY, 25.0, "%", StatusBukti.TARGET)
        self.assertFalse(dapat_dibandingkan(a, b)[0])

    def test_ringkasan_ketersediaan(self):
        ra = R.ringkas_ketersediaan(self.acuan)
        rk = R.ringkas_ketersediaan(self.kustom)
        self.assertEqual(ra["tidak_tersedia"], 0)
        self.assertEqual(ra["terukur"], 3)
        self.assertEqual(rk["terukur"], 0)
        self.assertGreater(rk["tidak_tersedia"], 0)
        self.assertEqual(rk["tersedia"] + rk["tidak_tersedia"], rk["total"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
