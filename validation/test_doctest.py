"""
Pengumpul doctest — contoh yang dapat dieksekusi ikut dijalankan suite.

APA YANG DIUJI BERKAS INI
    Seluruh contoh `>>>` di dalam docstring modul produksi. Contoh semacam itu
    adalah kontrak yang dapat dieksekusi: ia menyatakan apa yang dihasilkan
    sebuah fungsi untuk masukan tertentu.

MENGAPA BERKAS INI ADA
    Sampai S6-G, contoh-contoh itu ada tetapi TIDAK PERNAH DIJALANKAN. Perintah
    resmi proyek hanya menemukan berkas `test_*.py`, dan doctest bukan salah
    satunya. Akibatnya 34 contoh di 15 fungsi memberi kesan terverifikasi
    padahal tidak, dan dua di antaranya ternyata memang salah.

    Berkas ini menutup celah itu lewat protokol `load_tests` unittest, sehingga
    doctest ikut terkumpul oleh perintah yang sudah ada:

        python -m unittest discover -s validation -v

    Tidak ada perintah kedua yang harus diingat, tidak ada dependensi baru, dan
    tidak ada berkas konfigurasi baru.

APA YANG TIDAK DIUJI BERKAS INI
    Kebenaran ilmiah nilainya. Doctest yang lulus hanya membuktikan fungsi
    masih menghasilkan apa yang didokumentasikan — bukan bahwa yang
    didokumentasikan itu benar secara ilmiah (ADR-004).

MODUL YANG SENGAJA DIKECUALIKAN
    `AQUAPAVE.py` — akar komposisi. Mengimpornya menjalankan aplikasi, bukan
    memuat definisi. Ia tidak memuat doctest.
"""

from __future__ import annotations

import doctest
import importlib
import os
import pkgutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Paket yang disapu. Ditulis eksplisit agar modul baru di paket baru harus
#: didaftarkan sadar, bukan ikut terbawa diam-diam.
PAKET = (".", "core", "data", "scenario", "ui", "ui/components", "ui/tabs")

#: Akar komposisi: mengimpornya menjalankan aplikasi.
DIKECUALIKAN = frozenset({"AQUAPAVE"})


def nama_modul() -> list[str]:
    """Nama modul produksi yang dapat diimpor, terurut."""
    hasil = []
    for paket in PAKET:
        direktori = os.path.join(AKAR, paket)
        for berkas in sorted(os.listdir(direktori)):
            if not berkas.endswith(".py") or berkas == "__init__.py":
                continue
            batang = berkas[:-3]
            nama = batang if paket == "." else paket.replace("/", ".") + "." + batang
            if nama in DIKECUALIKAN:
                continue
            hasil.append(nama)
    return hasil


def modul_bercontoh() -> list[str]:
    """Modul yang benar-benar memuat contoh dapat dieksekusi."""
    pencari = doctest.DocTestFinder()
    hasil = []
    for nama in nama_modul():
        modul = importlib.import_module(nama)
        if any(t.examples for t in pencari.find(modul)):
            hasil.append(nama)
    return hasil


def load_tests(loader, tests, pattern):  # noqa: ARG001  (protokol unittest)
    """Protokol unittest: sisipkan setiap doctest ke dalam suite biasa."""
    for nama in modul_bercontoh():
        tests.addTests(doctest.DocTestSuite(importlib.import_module(nama)))
    return tests


class PengumpulanDoctest(unittest.TestCase):
    """
    Penjaga pengumpulnya sendiri.

    Tanpa uji ini, `load_tests` yang berhenti bekerja akan membuat suite tetap
    hijau sambil diam-diam berhenti menjalankan seluruh doctest — persis
    kegagalan yang dibereskan S6-G.
    """

    def test_ada_contoh_yang_terkumpul(self):
        self.assertGreater(len(modul_bercontoh()), 0)

    def test_jumlah_contoh_tidak_menyusut(self):
        """
        Contoh boleh bertambah; berkurang berarti kontrak yang hilang.
        Perbarui angka ini hanya bila penghapusannya memang disengaja.
        """
        pencari = doctest.DocTestFinder()
        jumlah = sum(
            len(t.examples)
            for nama in modul_bercontoh()
            for t in pencari.find(importlib.import_module(nama))
        )
        self.assertGreaterEqual(
            jumlah, 35,
            "jumlah contoh dapat dieksekusi menyusut; kontrak hilang?",
        )

    def test_setiap_modul_produksi_dapat_diimpor(self):
        """Modul yang gagal diimpor akan lolos dari pengumpulan tanpa jejak."""
        for nama in nama_modul():
            with self.subTest(modul=nama):
                importlib.import_module(nama)


if __name__ == "__main__":
    unittest.main(verbosity=2)
