"""
Penjaga keluaran terpuji — nilai yang dihapus ADR-001 tidak boleh kembali (S6-B).

MENGAPA PENJAGA LAMA GAGAL
--------------------------
`data/akses.pastikan_tidak_dihapus()` menolak kode yang MEMINTA sebuah
konstanta terhapus. Ia berdiri di pintu `akses`, dan hanya di sana.

Tabel dasbor tidak pernah lewat pintu itu. Ia menuliskan angkanya langsung
sebagai literal teks tampilan, sehingga empat nilai yang sudah dihapus hidup
kembali tanpa satu pun uji gagal:

    "0,45–0,75 cm/dtk ✅"        ambang_permeabilitas_045 + target_permeabilitas_060
    "ACI 522 ≥ 0,14 cm/dtk"      aci_522_014
    "SNI — min 10 MPa"           sni_min_10_mpa
    "15,00 MPa (lab) ✅"          asumsi disajikan sebagai hasil laboratorium

Penjaga di berkas ini menutup kelasnya, bukan keempat kalimatnya: ia
menjalankan aplikasi sungguhan lalu memeriksa KELUARAN YANG DIRENDER terhadap
pola yang tercatat di `konstanta.DIHAPUS`. Menambahkan nilai terhapus baru
beserta polanya otomatis memperluas penjagaan ini.

APA YANG DIPERIKSA DAN APA YANG TIDAK
-------------------------------------
Diperiksa: **permukaan klaim terstruktur** — setiap sel dataframe dan setiap
label, nilai, serta delta metrik, di seluruh tab.

Tidak diperiksa: prosa. Keterangan, peringatan, dan paragraf penjelasan boleh
menyebut angka yang dihapus, karena di sanalah proyek MENJELASKAN
penghapusannya. Tab 2 misalnya menulis "Ambang 0,45 cm/dtk dan target
0,60 cm/dtk yang dipakai versi sebelumnya tidak ada di naskah mana pun dan
telah dihapus" — kalimat itu justru harus tetap ada.

Pembedaannya bukan kompromi melainkan justru intinya: klaim ilmiah hidup di
tabel dan metrik, penjelasan hidup di prosa.

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

from data import akses  # noqa: E402
from scenario import state as skenario  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
TENGGAT = 90


def jalankan(kustom: float | None = None) -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    if kustom is not None:
        at.sidebar.button[0].click().run()
        [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(kustom).run()
    return at


def permukaan_klaim(at) -> list[tuple[str, str]]:
    """
    Setiap tempat aplikasi menyatakan sebuah KLAIM, bukan menjelaskan sesuatu.

    Sel dataframe dan metrik. Prosa sengaja dikecualikan — lihat catatan modul.
    """
    permukaan = []
    for i, d in enumerate(at.dataframe):
        df = d.value
        for kolom in df.columns:
            permukaan.append((f"dataframe[{i}].kolom", str(kolom)))
            for nilai in df[kolom]:
                permukaan.append((f"dataframe[{i}][{kolom}]", str(nilai)))
    for m in at.metric:
        for bagian in (m.label, m.value, m.delta):
            if bagian:
                permukaan.append(("metric", str(bagian)))
    return permukaan


class PenjagaKeluaranTerlarang(unittest.TestCase):
    """Nilai terhapus tidak boleh muncul di permukaan klaim mana pun."""

    @classmethod
    def setUpClass(cls):
        cls.acuan = jalankan()
        cls.kustom = jalankan(kustom=22)

    def _sapu(self, at, keadaan: str) -> None:
        pola = akses.pola_dihapus()
        self.assertTrue(pola, "registri pola kosong — penjaga tidak menjaga apa pun")
        for nama, daftar_pola in pola.items():
            for p in daftar_pola:
                rx = re.compile(p, re.IGNORECASE)
                for tempat, teks in permukaan_klaim(at):
                    self.assertIsNone(
                        rx.search(teks),
                        f"[{keadaan}] nilai yang dihapus ADR-001 muncul kembali "
                        f"di {tempat}: {nama!r} cocok dengan pola {p!r} pada "
                        f"teks {teks!r}. Alasan penghapusan: "
                        f"{akses.daftar_dihapus()[nama].alasan}",
                    )

    def test_konfigurasi_acuan(self):
        self._sapu(self.acuan, "acuan")

    def test_skenario_kustom(self):
        self._sapu(self.kustom, "kustom 22%")

    def test_penjaga_benar_benar_menangkap(self):
        """
        Penjaga harus gagal bila nilai terhapus benar-benar muncul.

        Tanpa uji ini, penjaga yang polanya salah tulis akan lulus selamanya
        tanpa pernah menjaga apa pun.
        """
        contoh = [
            ("dataframe[0][ZEOPAVE-AQUA]", "0,45–0,75 cm/dtk ✅"),
            ("dataframe[0][Referensi]", "ACI 522 ≥ 0,14 cm/dtk"),
            ("dataframe[0][Referensi]", "SNI — min 10 MPa (lalu lintas ringan)"),
            ("metric", "21,5 %"),
        ]
        pola = [re.compile(p, re.IGNORECASE)
                for daftar in akses.pola_dihapus().values() for p in daftar]
        for tempat, teks in contoh:
            self.assertTrue(
                any(rx.search(teks) for rx in pola),
                f"penjaga TIDAK menangkap nilai terlarang {teks!r} di {tempat}",
            )

    def test_prosa_boleh_menjelaskan_penghapusan(self):
        """
        Kalimat yang MENJELASKAN sebuah penghapusan harus tetap boleh ada.

        Tab 2 menerangkan mengapa ambang 0,45 dan target 0,60 cm/dtk dihapus.
        Penjaga tidak boleh memaksa kalimat itu dihilangkan.
        """
        prosa = "\n".join(c.value for c in self.acuan.caption)
        self.assertIn("0,45 cm/dtk", prosa)
        self.assertIn("telah dihapus", prosa)

    def test_registri_pola_menutup_temuan_s6a(self):
        """Keempat nilai temuan S6-A wajib punya pola pengenal."""
        pola = akses.pola_dihapus()
        for nama in ("ambang_permeabilitas_045", "target_permeabilitas_060",
                     "aci_522_014", "sni_min_10_mpa"):
            self.assertIn(nama, pola, f"{nama} tanpa pola — tidak terjaga")

    def test_setiap_pola_adalah_regex_sah(self):
        for nama, daftar in akses.pola_dihapus().items():
            for p in daftar:
                try:
                    re.compile(p)
                except re.error as e:
                    self.fail(f"pola {nama} tidak sah: {p!r} ({e})")

    def test_penjaga_lama_tetap_berlaku(self):
        """Pintu akses tetap tertutup; penjaga baru menambah, bukan mengganti."""
        for nama in akses.daftar_dihapus():
            with self.assertRaises(akses.NilaiDihapus):
                akses.besaran(nama)


class SkenarioKustomTetapAman(unittest.TestCase):
    """Penjaga tidak boleh menutupi kebocoran hasil ukur."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan(kustom=22)

    def test_skenario_memang_kustom(self):
        k = self.at.session_state[skenario.KUNCI]
        self.assertFalse(skenario.cocok_konfigurasi_uji(k.ambil("A")))

    def test_tabel_perbandingan_tetap_menyatakan_tidak_tersedia(self):
        from scenario.keluaran import FRASA_TIDAK_TERSEDIA
        df = self.at.dataframe[0].value
        for baris in ("Kuat tekan (7 hari)", "Koefisien permeabilitas",
                      "Retensi air", "Air tertahan pada skala area"):
            sel = df[df["Keluaran"] == baris].iloc[0]["Skenario A"]
            self.assertEqual(sel, FRASA_TIDAK_TERSEDIA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
