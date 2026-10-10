"""
Uji duplikasi kanonik — penjaga agar salinan di core/ tidak menyimpang diam-diam.

APA YANG DIUJI BERKAS INI
    Hubungan antara besaran kanonik di `konstanta.py` dan salinan
    implementasinya di dalam `core/`. Bila keduanya seharusnya sama, uji di
    sini gagal ketika salah satu sisi diubah sendirian.

APA YANG TIDAK DIUJI BERKAS INI
    Kebenaran ilmiah nilainya. Lulusnya seluruh uji di sini hanya membuktikan
    kedua sisi masih sepakat — bukan bahwa yang disepakati itu benar. Validasi
    ilmiah tetap ada di test_reproduksi.py dan pada bukti proyek (ADR-004).

MENGAPA SALINAN INI ADA
    `core/` sengaja tidak mengimpor apa pun dari proyek — hanya `math` dan
    `typing`. Kemandirian itu membuat lapisan perhitungan dapat diuji dan
    dipindahkan tanpa membawa serta seluruh rantai provenansi. Harganya adalah
    salinan nilai, dan salinan yang tidak dijaga akan menyimpang cepat atau
    lambat. Berkas ini membayar harga itu.

    Salinan di `core/` BUKAN kewenangan tandingan menurut ADR-011: yang
    berwenang tetap `konstanta.py`. Bila keduanya berbeda, yang salah adalah
    salinannya.

EMPAT KELAS HUBUNGAN
    A  alias semantik eksak    — besaran sama, wajib sama persis
    B  hubungan turunan        — nilainya dihitung dari nilai lain
    C  kebetulan senilai       — angkanya sama, besarannya berbeda; JANGAN diikat
    D  pemetaan ambigu         — bukti proyek belum menentukan; JANGAN disamakan

Jalankan dari akar proyek:

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import io
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import konstanta  # noqa: E402
from core import emisi, hidrologi, komposisi, kuat_tekan, permeabilitas, retensi  # noqa: E402
from data import akses  # noqa: E402
from scenario import state  # noqa: E402
from ui.tabs import kuat_tekan as tab_kuat_tekan  # noqa: E402
from ui.tabs import biaya as tab_biaya  # noqa: E402
from ui.tabs import permeabilitas as tab_permeabilitas  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sumber(modul) -> str:
    return io.open(inspect.getsourcefile(modul), encoding="utf8").read()


# ---------------------------------------------------------------------------
# KELAS A — alias semantik eksak
#
# (besaran kanonik, modul core, nama salinan, pengambil nilai)
# Nilainya diambil lewat pemanggilan, bukan disalin sebagai literal, supaya
# berkas uji ini tidak menjadi salinan ketiga.
# ---------------------------------------------------------------------------
ALIAS_EKSAK = (
    ("PERM_TEBAL_SAMPEL", "permeabilitas", "LAB_TEBAL_CM",
     lambda: permeabilitas.LAB_TEBAL_CM),
    ("PERM_LUAS_PENAMPANG", "permeabilitas", "LAB_LUAS_CM2",
     lambda: permeabilitas.LAB_LUAS_CM2),
    ("PERM_TINGGI_TEKANAN", "permeabilitas", "LAB_TINGGI_TEKAN_CM",
     lambda: permeabilitas.LAB_TINGGI_TEKAN_CM),
    ("PERM_KECEPATAN_ALIRAN", "permeabilitas", "LAB_KECEPATAN_CM_PER_DETIK",
     lambda: permeabilitas.LAB_KECEPATAN_CM_PER_DETIK),
    ("PERMEABILITAS", "permeabilitas", "LAB_K_CM_PER_DETIK",
     lambda: permeabilitas.LAB_K_CM_PER_DETIK),
    ("PERM_BETON_KONVENSIONAL", "permeabilitas", "pembanding_literatur()[0]",
     lambda: permeabilitas.pembanding_literatur()[0]["nilai"]),
    ("PERM_ZHU_MIN", "permeabilitas", "pembanding_literatur()[1]",
     lambda: permeabilitas.pembanding_literatur()[1]["nilai"]),
    ("PERM_ZHU_MAKS", "permeabilitas", "pembanding_literatur()[2]",
     lambda: permeabilitas.pembanding_literatur()[2]["nilai"]),
    ("UMUR_UJI_HARI", "kuat_tekan", "LAB_UMUR_HARI",
     lambda: kuat_tekan.LAB_UMUR_HARI),
    ("LUAS_SILINDER", "kuat_tekan", "LAB_LUAS_M2",
     lambda: kuat_tekan.LAB_LUAS_M2),
    ("KUAT_TEKAN_7_HARI", "kuat_tekan", "LAB_FC_RERATA_MPA",
     lambda: kuat_tekan.LAB_FC_RERATA_MPA),
    ("AMBANG_LALU_LINTAS_RINGAN", "kuat_tekan", "ambang_lalu_lintas_ringan()",
     lambda: kuat_tekan.ambang_lalu_lintas_ringan()["nilai"]),
    ("RETENSI_RERATA", "retensi", "LAB_RETENSI_RERATA_PERSEN",
     lambda: retensi.LAB_RETENSI_RERATA_PERSEN),
    ("RETENSI_SIMPANGAN_BAKU", "retensi", "LAB_SIMPANGAN_BAKU_PERSEN",
     lambda: retensi.LAB_SIMPANGAN_BAKU_PERSEN),
    ("RETENSI_KOEF_VARIASI", "retensi", "LAB_CV_PERSEN",
     lambda: retensi.LAB_CV_PERSEN),
    ("SKALA_LUAS_ACUAN", "hidrologi", "ACUAN_LUAS_M2",
     lambda: hidrologi.ACUAN_LUAS_M2),
    ("SKALA_INTENSITAS_ACUAN", "hidrologi", "ACUAN_INTENSITAS_MM_PER_JAM",
     lambda: hidrologi.ACUAN_INTENSITAS_MM_PER_JAM),
    ("SKALA_AIR_JATUH", "hidrologi", "ACUAN_AIR_JATUH_LITER",
     lambda: hidrologi.ACUAN_AIR_JATUH_LITER),
    ("SKALA_AIR_TERTAHAN", "hidrologi", "ACUAN_AIR_TERTAHAN_LITER",
     lambda: hidrologi.ACUAN_AIR_TERTAHAN_LITER),
    ("BERAT_SATUAN_BETON", "komposisi", "BERAT_SATUAN_ASUMSI",
     lambda: komposisi.BERAT_SATUAN_ASUMSI),
    ("RASIO_PENGIKAT_AGREGAT", "komposisi", "RASIO_AGREGAT_ACUAN",
     lambda: komposisi.RASIO_AGREGAT_ACUAN),
    ("SUBSTITUSI_IPAL", "komposisi", "SUBSTITUSI_ACUAN",
     lambda: komposisi.SUBSTITUSI_ACUAN),
    ("FAKTOR_AIR_PENGIKAT", "komposisi", "FAKTOR_AIR_PENGIKAT_ACUAN",
     lambda: komposisi.FAKTOR_AIR_PENGIKAT_ACUAN),
    ("CO2_PER_TON_SEMEN_MIN", "emisi", "rentang_faktor_emisi_semen()['min']",
     lambda: emisi.rentang_faktor_emisi_semen()["min"]),
    ("CO2_PER_TON_SEMEN_MAKS", "emisi", "rentang_faktor_emisi_semen()['maks']",
     lambda: emisi.rentang_faktor_emisi_semen()["maks"]),
)

#: Nama modul-level di core/ yang sudah diklasifikasikan, per modul.
#: Dipakai uji cakupan di bawah: konstanta baru wajib masuk peta.
TERPETAKAN = {
    "hidrologi": {
        "ACUAN_LUAS_M2": "A", "ACUAN_INTENSITAS_MM_PER_JAM": "A",
        "ACUAN_AIR_JATUH_LITER": "A", "ACUAN_AIR_TERTAHAN_LITER": "A",
        "ACUAN_DURASI_JAM": "C",
    },
    "komposisi": {
        "BERAT_SATUAN_ASUMSI": "A", "RASIO_AGREGAT_ACUAN": "A",
        "SUBSTITUSI_ACUAN": "A", "FAKTOR_AIR_PENGIKAT_ACUAN": "A",
        "_MASSA_BENDA_UJI_KG": "A",
        "_DIAMETER_SILINDER_M": "B", "_TINGGI_SILINDER_M": "D",
    },
    "kuat_tekan": {
        "LAB_UMUR_HARI": "A", "LAB_LUAS_M2": "A", "LAB_FC_RERATA_MPA": "A",
        "LAB_BEBAN_KN": "A", "LAB_DIAMETER_MM": "B",
    },
    "permeabilitas": {
        "LAB_TEBAL_CM": "A", "LAB_LUAS_CM2": "A", "LAB_TINGGI_TEKAN_CM": "A",
        "LAB_KECEPATAN_CM_PER_DETIK": "A", "LAB_K_CM_PER_DETIK": "A",
    },
    "retensi": {
        "LAB_UJI": "A", "LAB_RETENSI_RERATA_PERSEN": "A",
        "LAB_SIMPANGAN_BAKU_PERSEN": "A", "LAB_CV_PERSEN": "A",
    },
    "emisi": {},
    "geometri": {},
}

MODUL = {
    "emisi": emisi, "hidrologi": hidrologi, "komposisi": komposisi,
    "kuat_tekan": kuat_tekan, "permeabilitas": permeabilitas,
    "retensi": retensi,
}

#: Konstanta modul-level di lapisan skenario, diklasifikasikan seperti core/.
#: Terpisah dari MODUL karena `scenario/state.py` MEMANG mengimpor konstanta.py
#: — kemandirian yang dijaga untuk core/ tidak berlaku di sini.
TERPETAKAN_SKENARIO = {
    "KUNCI": "bukan besaran (kunci session state)",
    "ACUAN": "bukan besaran (nama skenario acuan)",
    "NAMA_KUSTOM": "bukan besaran (nama skenario)",
    "PARAMETER_KONFIGURASI_UJI": "bukan besaran (definisi konfigurasi uji)",
    "ACUAN_SUBSTITUSI_IPAL": "A",
    "ACUAN_FAKTOR_AIR_PENGIKAT": "A",
    "ACUAN_RASIO_AGREGAT": "A",
}


class AliasEksak(unittest.TestCase):
    """KELAS A — besaran yang sama wajib bernilai sama persis di kedua sisi."""

    def test_setiap_alias_sama_persis(self):
        for kanonik, modul, nama, ambil in ALIAS_EKSAK:
            with self.subTest(kanonik=kanonik, salinan=f"core.{modul}.{nama}"):
                self.assertEqual(
                    float(akses.nilai(kanonik)), float(ambil()),
                    f"core.{modul}.{nama} menyimpang dari konstanta.{kanonik}. "
                    f"Yang berwenang adalah konstanta.py (ADR-011); perbaiki salinannya.",
                )

    def test_beban_benda_uji_sama_dengan_dataset_kanonik(self):
        kanonik = tuple(float(b["beban_kN"]) for b in akses.dataset_kuat_tekan())
        self.assertEqual(
            kanonik, tuple(float(x) for x in kuat_tekan.LAB_BEBAN_KN),
            "core.kuat_tekan.LAB_BEBAN_KN menyimpang dari akses.dataset_kuat_tekan()",
        )

    def test_massa_benda_uji_sama_dengan_dataset_kanonik(self):
        """Masukan SD-16C: massa benda uji harus tetap satu angka, bukan dua."""
        kanonik = tuple(float(b["berat_kg"]) for b in akses.dataset_kuat_tekan())
        self.assertEqual(
            kanonik, tuple(float(x) for x in komposisi._MASSA_BENDA_UJI_KG),
            "core.komposisi._MASSA_BENDA_UJI_KG menyimpang dari "
            "akses.dataset_kuat_tekan(). Berat satuan tersirat dihitung darinya.",
        )

    def test_uji_retensi_sama_dengan_dataset_kanonik(self):
        def bentuk(baris):
            return tuple(
                (u["nama"], float(u["input_ml"]), float(u["output_ml"])) for u in baris
            )

        self.assertEqual(
            bentuk(akses.dataset_retensi()), bentuk(retensi.LAB_UJI),
            "core.retensi.LAB_UJI menyimpang dari akses.dataset_retensi()",
        )

    def test_jumlah_alias_terjaga(self):
        """Peta tidak boleh menyusut diam-diam."""
        self.assertEqual(len(ALIAS_EKSAK), 25)


class HubunganTurunan(unittest.TestCase):
    """
    KELAS B — nilai yang dihitung dari nilai lain.

    Yang dijaga adalah HUBUNGANNYA, bukan literalnya. Membekukan literal di
    sini hanya akan membuat berkas uji menjadi salinan ketiga.

    Beberapa nilai kanonik adalah pembulatan hasil hitungan. Toleransinya
    ditetapkan menurut jumlah desimal yang benar-benar dipakai nilai kanonik,
    bukan dipilih agar uji lulus.
    """

    def test_luas_silinder_dari_diameter(self):
        self.assertAlmostEqual(
            float(akses.nilai("LUAS_SILINDER")),
            kuat_tekan.luas_silinder_m2(kuat_tekan.LAB_DIAMETER_MM),
            delta=5e-7,  # LUAS_SILINDER ditulis 6 desimal
        )

    def test_kuat_tekan_rerata_dari_dataset(self):
        fc = [
            kuat_tekan.kuat_tekan_mpa(b["beban_kN"], kuat_tekan.LAB_LUAS_M2)
            for b in akses.dataset_kuat_tekan()
        ]
        self.assertAlmostEqual(
            float(akses.nilai("KUAT_TEKAN_7_HARI")),
            kuat_tekan.ringkasan(fc)["rerata"],
            delta=5e-3,  # KUAT_TEKAN_7_HARI ditulis 2 desimal
        )

    def test_debit_dari_kecepatan_dan_luas(self):
        self.assertAlmostEqual(
            float(akses.nilai("PERM_DEBIT")),
            permeabilitas.debit_dari_kecepatan(
                permeabilitas.LAB_KECEPATAN_CM_PER_DETIK,
                permeabilitas.LAB_LUAS_CM2,
            ),
            delta=1e-9,
        )

    def test_gradien_hidraulik_dari_geometri(self):
        self.assertAlmostEqual(
            float(akses.nilai("PERM_GRADIEN_HIDRAULIK")),
            permeabilitas.gradien_hidraulik(
                permeabilitas.LAB_TINGGI_TEKAN_CM, permeabilitas.LAB_TEBAL_CM
            ),
            delta=1e-9,
        )

    def test_permeabilitas_dari_konfigurasi_lab(self):
        """k = Q*L/(A*h) memakai konfigurasi lab, bukan angka yang ditulis ulang."""
        q = permeabilitas.debit_dari_kecepatan(
            permeabilitas.LAB_KECEPATAN_CM_PER_DETIK, permeabilitas.LAB_LUAS_CM2
        )
        self.assertAlmostEqual(
            float(akses.nilai("PERMEABILITAS")),
            permeabilitas.koefisien_dari_debit(
                q, permeabilitas.LAB_TEBAL_CM, permeabilitas.LAB_LUAS_CM2,
                permeabilitas.LAB_TINGGI_TEKAN_CM,
            ),
            delta=5e-4,  # PERMEABILITAS ditulis 3 desimal
        )

    def test_ringkasan_retensi_dari_dataset(self):
        r = retensi.ringkasan(
            [
                retensi.retensi_persen(u["input_ml"], u["output_ml"])
                for u in akses.dataset_retensi()
            ]
        )
        for kanonik, kunci in (
            ("RETENSI_RERATA", "rerata"),
            ("RETENSI_SIMPANGAN_BAKU", "simpangan_baku"),
            ("RETENSI_KOEF_VARIASI", "cv_persen"),
        ):
            with self.subTest(besaran=kanonik):
                self.assertAlmostEqual(
                    float(akses.nilai(kanonik)), r[kunci], delta=5e-2
                )

    def test_air_jatuh_dari_skenario_acuan(self):
        m3 = hidrologi.volume_hujan_m3(
            hidrologi.ACUAN_INTENSITAS_MM_PER_JAM,
            hidrologi.ACUAN_LUAS_M2,
            hidrologi.ACUAN_DURASI_JAM,
        )
        self.assertAlmostEqual(
            float(akses.nilai("SKALA_AIR_JATUH")), m3 * 1000.0, delta=1.0
        )

    def test_air_tertahan_dari_air_jatuh_dan_retensi(self):
        self.assertAlmostEqual(
            float(akses.nilai("SKALA_AIR_TERTAHAN")),
            float(akses.nilai("SKALA_AIR_JATUH"))
            * float(akses.nilai("RETENSI_RERATA")) / 100.0,
            delta=1.0,
        )

    def test_diameter_silinder_konsisten_antar_modul_core(self):
        """komposisi memakai meter, kuat_tekan memakai milimeter."""
        self.assertAlmostEqual(
            komposisi._DIAMETER_SILINDER_M,
            kuat_tekan.LAB_DIAMETER_MM / 1000.0,
            delta=1e-12,
        )


class KebetulanSenilai(unittest.TestCase):
    """
    KELAS C — angka yang kebetulan sama, besaran yang berbeda.

    Sengaja TIDAK diikat. Uji di sini menjaga agar pemeliharaan berikutnya
    tidak "merapikan" kebetulan ini menjadi ikatan yang keliru.
    """

    def test_ambang_kuat_tekan_bukan_kecepatan_aliran(self):
        """5,0 MPa dan 5,0 cm/detik: nilainya sama, satuannya tidak."""
        self.assertEqual(
            float(akses.nilai("AMBANG_LALU_LINTAS_RINGAN")),
            float(akses.nilai("PERM_KECEPATAN_ALIRAN")),
        )
        self.assertNotEqual(
            akses.besaran("AMBANG_LALU_LINTAS_RINGAN").satuan,
            akses.besaran("PERM_KECEPATAN_ALIRAN").satuan,
        )

    def test_gradien_hidraulik_bukan_rasio_agregat(self):
        """3,0 tanpa satuan dan 3,0 kg agregat per kg pengikat."""
        self.assertEqual(
            float(akses.nilai("PERM_GRADIEN_HIDRAULIK")),
            float(akses.nilai("RASIO_PENGIKAT_AGREGAT")),
        )
        self.assertNotEqual(
            akses.besaran("PERM_GRADIEN_HIDRAULIK").satuan,
            akses.besaran("RASIO_PENGIKAT_AGREGAT").satuan,
        )

    def test_substitusi_persen_bukan_kuat_tekan_mpa(self):
        """15,0 % substitusi dan 15,00 MPa estimasi umur 14 hari."""
        self.assertEqual(
            float(akses.nilai("SUBSTITUSI_IPAL")),
            float(akses.nilai("KUAT_TEKAN_14_HARI")),
        )
        self.assertNotEqual(
            akses.besaran("SUBSTITUSI_IPAL").satuan,
            akses.besaran("KUAT_TEKAN_14_HARI").satuan,
        )

    def test_durasi_acuan_bukan_simpangan_baku_retensi(self):
        """hidrologi.ACUAN_DURASI_JAM = 1,0 jam; RETENSI_SIMPANGAN_BAKU = 1,0 %."""
        self.assertEqual(
            hidrologi.ACUAN_DURASI_JAM, float(akses.nilai("RETENSI_SIMPANGAN_BAKU"))
        )
        self.assertEqual(akses.besaran("RETENSI_SIMPANGAN_BAKU").satuan, "%")
        # Tidak ada besaran kanonik untuk durasi acuan; jangan diada-adakan.
        durasi = [n for n, _ in konstanta.daftar_provenans() if "DURASI" in n]
        self.assertEqual(durasi, [])

    def test_batas_grafik_substitusi_tidak_terikat_porositas(self):
        """
        emisi.tren_substitusi(maks_persen=25) kebetulan senilai
        POROSITAS_TARGET_MAKS = 25 %. Keduanya tidak berhubungan.
        """
        self.assertEqual(
            inspect.signature(emisi.tren_substitusi).parameters["maks_persen"].default,
            25,
        )
        self.assertEqual(float(akses.nilai("POROSITAS_TARGET_MAKS")), 25.0)
        self.assertNotIn(
            "POROSITAS", _sumber(emisi),
            "core/emisi.py tidak boleh mengikat batas sumbu grafik ke porositas",
        )


class PemetaanAmbigu(unittest.TestCase):
    """
    KELAS D — bukti proyek belum menentukan apakah kedua sisi sama.

    Tidak boleh disamakan lewat uji. Menyamakannya berarti memutuskan
    keputusan ilmiah yang masih terbuka.
    """

    def test_tinggi_silinder_tetap_andaian_tanpa_padanan_kanonik(self):
        """
        komposisi._TINGGI_SILINDER_M = 0,300 m adalah ANDAIAN (SD-16C).
        Tidak ada besaran kanonik untuk tinggi benda uji, dan tidak boleh
        diada-adakan selama SD-16C terbuka.
        """
        self.assertEqual(komposisi._TINGGI_SILINDER_M, 0.300)
        tinggi = [
            n for n, _ in konstanta.daftar_provenans() if "TINGGI_SILINDER" in n
        ]
        self.assertEqual(tinggi, [], "SD-16C masih terbuka; jangan buat besaran kanonik")

    def test_selisih_berat_satuan_tetap_dilaporkan_bukan_dipilih(self):
        """
        1.850 kg/m3 (asumsi) dan berat satuan tersirat benda uji tidak
        disamakan. Modul melaporkan selisihnya, tidak memilih salah satu.
        """
        hasil = komposisi.berat_satuan_tersirat_benda_uji()
        self.assertNotAlmostEqual(
            hasil["berat_satuan_kg_m3"],
            float(akses.nilai("BERAT_SATUAN_BETON")),
            delta=1.0,
        )
        self.assertIn("indikatif", hasil["catatan"])
        # Bawaan modul tetap nilai kanonik; tersirat tidak menggantikannya.
        self.assertEqual(
            komposisi.BERAT_SATUAN_ASUMSI, float(akses.nilai("BERAT_SATUAN_BETON"))
        )

    def test_koefisien_limpasan_bawaan_tanpa_padanan_kanonik(self):
        """0,85 adalah bawaan antarmuka tanpa sumber (SD-12), bukan kanonik."""
        bawaan = inspect.signature(hidrologi.skenario).parameters[
            "koefisien_limpasan_konvensional"
        ].default
        self.assertEqual(bawaan, 0.85)
        senilai = [
            n for n, b in konstanta.daftar_provenans() if float(b.nilai) == 0.85
        ]
        self.assertEqual(senilai, [], "SD-12 masih terbuka; jangan jadikan kanonik")


class BawaanSkenario(unittest.TestCase):
    """
    KELAS A — bawaan `Skenario` yang menyalin besaran kanonik.

    Lapisan ini luput dari audit S6-F, yang berhenti di `core/`. Dua salinan
    ternyata dapat menyimpang tanpa satu pun dari 511 uji gagal:

        scenario.state.ACUAN_RASIO_AGREGAT
        Skenario.rasio_agregat  -> diubah 3,0 menjadi 4,0: suite tetap hijau
        Skenario.berat_satuan_kg_m3 -> diubah 1.850 menjadi 1.500: suite tetap hijau

    Keduanya bawaan setiap skenario, jadi penyimpangannya langsung mengubah
    proporsi material yang ditampilkan Tab 1.
    """

    #: (nama bidang Skenario, nama besaran kanonik)
    BAWAAN_KANONIK = (
        ("substitusi_ipal_persen", "SUBSTITUSI_IPAL"),
        ("faktor_air_pengikat", "FAKTOR_AIR_PENGIKAT"),
        ("rasio_agregat", "RASIO_PENGIKAT_AGREGAT"),
        ("luas_area_m2", "SKALA_LUAS_ACUAN"),
        ("intensitas_hujan_mm_per_jam", "SKALA_INTENSITAS_ACUAN"),
        ("berat_satuan_kg_m3", "BERAT_SATUAN_BETON"),
        ("co2_per_ton_ipal", "CO2_PER_TON_IPAL"),
    )

    #: (nama konstanta modul, nama besaran kanonik)
    ACUAN_MODUL = (
        ("ACUAN_SUBSTITUSI_IPAL", "SUBSTITUSI_IPAL"),
        ("ACUAN_FAKTOR_AIR_PENGIKAT", "FAKTOR_AIR_PENGIKAT"),
        ("ACUAN_RASIO_AGREGAT", "RASIO_PENGIKAT_AGREGAT"),
    )

    def test_bawaan_skenario_sama_dengan_kanonik(self):
        bidang = {f.name: f for f in dataclasses.fields(state.Skenario)}
        for nama, kanonik in self.BAWAAN_KANONIK:
            with self.subTest(bidang=nama, kanonik=kanonik):
                self.assertIn(nama, bidang, f"bidang {nama} hilang dari Skenario")
                self.assertEqual(
                    float(akses.nilai(kanonik)), float(bidang[nama].default),
                    f"bawaan Skenario.{nama} menyimpang dari konstanta.{kanonik}. "
                    f"Yang berwenang adalah konstanta.py (ADR-011).",
                )

    def test_konstanta_acuan_modul_sama_dengan_kanonik(self):
        for nama, kanonik in self.ACUAN_MODUL:
            with self.subTest(konstanta=nama, kanonik=kanonik):
                self.assertEqual(
                    float(akses.nilai(kanonik)), float(getattr(state, nama)),
                    f"scenario.state.{nama} menyimpang dari konstanta.{kanonik}",
                )

    def test_faktor_emisi_semen_bawaan_di_dalam_rentang_tersitir(self):
        """
        KELAS E — 0,85 kebetulan titik tengah 0,8-0,9, tetapi TIDAK ada
        dokumentasi yang menyatakan titik tengah sebagai aturan. Yang diuji
        hanyalah invarian yang memang bersumber: bawaan harus berada di dalam
        rentang yang disitir naskah. Titik tengahnya sengaja tidak ditegakkan.
        """
        bawaan = float(
            {f.name: f for f in dataclasses.fields(state.Skenario)}[
                "co2_per_ton_semen"
            ].default
        )
        self.assertGreaterEqual(bawaan, float(akses.nilai("CO2_PER_TON_SEMEN_MIN")))
        self.assertLessEqual(bawaan, float(akses.nilai("CO2_PER_TON_SEMEN_MAKS")))

    def test_bawaan_tanpa_padanan_kanonik_tetap_bebas(self):
        """
        KELAS D — bawaan yang sengaja TIDAK diikat: durasi hujan, total
        pengikat, dan volume adukan tidak punya besaran kanonik.
        """
        bidang = {f.name: f for f in dataclasses.fields(state.Skenario)}
        for nama in ("durasi_hujan_jam", "total_pengikat_ton", "volume_adukan_m3"):
            with self.subTest(bidang=nama):
                self.assertIn(nama, bidang)
        senilai = [
            n for n, b in konstanta.daftar_provenans()
            if float(b.nilai) == float(bidang["total_pengikat_ton"].default)
        ]
        self.assertEqual(senilai, [], "total pengikat bukan besaran kanonik")


class KebetulanAntarmuka(unittest.TestCase):
    """
    KELAS D pada lapisan antarmuka — angka sama, benda uji berbeda.

    Sengaja TIDAK diikat. Uji di sini menjaga agar pemeliharaan berikutnya
    tidak menyamakan dua benda uji yang memang berlainan.
    """

    def test_diameter_bawaan_tab2_bukan_silinder_tekan(self):
        """
        Tab 2 menawarkan mode lingkaran berdiameter 150 mm, senilai silinder
        tekan. Benda uji permeabilitas penelitian PERSEGI 15 x 15 cm, bukan
        lingkaran, sehingga keduanya bukan besaran yang sama.
        """
        self.assertEqual(
            tab_permeabilitas.BAWAAN_DIAMETER_MM, kuat_tekan.LAB_DIAMETER_MM
        )
        # Yang membuktikan keduanya berbeda: luas acuan penelitian persegi.
        self.assertAlmostEqual(
            tab_permeabilitas.ACUAN_LEBAR_CM * tab_permeabilitas.ACUAN_PANJANG_CM,
            float(akses.nilai("PERM_LUAS_PENAMPANG")),
            delta=1e-9,
        )
        self.assertNotAlmostEqual(
            math.pi * (tab_permeabilitas.BAWAAN_DIAMETER_MM / 10.0 / 2.0) ** 2,
            float(akses.nilai("PERM_LUAS_PENAMPANG")),
            delta=1.0,
        )

    def test_benda_uji_tambahan_bukan_data_laboratorium(self):
        """Bawaan penambahan benda uji ke-4 bukan bagian dataset penelitian."""
        beban = [float(b["beban_kN"]) for b in akses.dataset_kuat_tekan()]
        berat = [float(b["berat_kg"]) for b in akses.dataset_kuat_tekan()]
        self.assertNotIn(float(tab_kuat_tekan.BEBAN_TAMBAHAN_KN), beban)
        self.assertNotIn(float(tab_kuat_tekan.BERAT_TAMBAHAN_KG), berat)


class AsumsiOperasionalTab7(unittest.TestCase):
    """
    KELAS A — asumsi kerapatan Tab 7 menyalin besaran kanonik.

    S7-H memberi Tab 7 `KERAPATAN_BETON_POROS`, asumsi operasional lokal
    bernilai 1.850 kg/m³. Nilainya sama dengan `BERAT_SATUAN_BETON`, tetapi
    S6-F dan S6-H tidak pernah memetakannya — ia salinan **keempat** yang
    berada di luar penjagaan.

    Tab 7 sengaja tidak mengimpor `konstanta.py` (keputusan S7-H), sehingga
    penjagaannya harus di sini: uji membaca kedua sisi, kodenya tidak.

    Yang dijaga hanya kesetaraan NILAI. Statusnya memang berbeda dan boleh
    berbeda: kanonik berstatus `asumsi`, Tab 7 berstatus asumsi operasional
    sementara. SD-16C tetap terbuka bagi keduanya.
    """

    def test_kerapatan_tab7_sama_dengan_kanonik(self):
        self.assertAlmostEqual(
            float(akses.nilai("BERAT_SATUAN_BETON")),
            tab_biaya.KERAPATAN_BETON_POROS.nilai, delta=1e-9,
            msg="asumsi kerapatan Tab 7 menyimpang dari konstanta."
                "BERAT_SATUAN_BETON; bila berat satuan kelak diukur, Tab 7 "
                "harus ikut, bukan diam-diam tertinggal.",
        )

    def test_kerapatan_tab7_tetap_ditandai_asumsi(self):
        """Nilai boleh sama; klaim buktinya tidak boleh naik."""
        k = tab_biaya.KERAPATAN_BETON_POROS
        self.assertIn("asumsi", k.status.lower())
        self.assertEqual(akses.status("BERAT_SATUAN_BETON"), akses.ASUMSI)

    def test_geometri_tab7_bukan_geometri_benda_uji(self):
        """
        Tebal 2 cm lapisan perkerasan kebetulan senilai tebal benda uji
        permeabilitas (L = 2 cm). Keduanya BESARAN BERBEDA: yang satu tebal
        lapisan terpasang, yang lain tebal benda uji laboratorium.

        Uji ini menjaga agar keduanya tidak pernah disatukan.
        """
        self.assertAlmostEqual(
            tab_biaya.TEBAL_BETON_M * 100.0, permeabilitas.LAB_TEBAL_CM,
            delta=1e-9)
        with io.open(inspect.getsourcefile(tab_biaya), encoding="utf8") as f:
            sumber = f.read()
        # Tab 7 tidak boleh mengambil tebalnya dari modul benda uji.
        self.assertNotIn("LAB_TEBAL", sumber)
        self.assertNotIn("permeabilitas", sumber)


class CakupanPeta(unittest.TestCase):
    """
    Penjaga peta itu sendiri.

    Konstanta baru di `core/` wajib diklasifikasikan A/B/C/D sebelum uji ini
    lulus. Tanpa uji ini, peta akan usang tanpa ada yang gagal.
    """

    def test_setiap_konstanta_core_sudah_diklasifikasikan(self):
        for nama_modul, modul in MODUL.items():
            pohon = ast.parse(_sumber(modul))
            ditemukan = set()
            for simpul in pohon.body:
                if not isinstance(simpul, ast.Assign):
                    continue
                for sasaran in simpul.targets:
                    if not isinstance(sasaran, ast.Name):
                        continue
                    try:
                        nilai = ast.literal_eval(simpul.value)
                    except (ValueError, SyntaxError):
                        continue
                    if isinstance(nilai, str) or isinstance(nilai, (set, frozenset)):
                        continue  # penanda bentuk geometri, bukan besaran
                    ditemukan.add(sasaran.id)
            belum = sorted(ditemukan - set(TERPETAKAN[nama_modul]))
            with self.subTest(modul=nama_modul):
                self.assertEqual(
                    belum, [],
                    f"konstanta baru di core/{nama_modul}.py belum diklasifikasikan "
                    f"A/B/C/D pada TERPETAKAN: {belum}",
                )

    def test_setiap_konstanta_skenario_sudah_diklasifikasikan(self):
        """Lapisan skenario ikut dijaga sejak S6-H."""
        pohon = ast.parse(_sumber(state))
        ditemukan = set()
        for simpul in pohon.body:
            if not isinstance(simpul, ast.Assign):
                continue
            for sasaran in simpul.targets:
                if isinstance(sasaran, ast.Name) and sasaran.id.isupper():
                    ditemukan.add(sasaran.id)
        belum = sorted(ditemukan - set(TERPETAKAN_SKENARIO))
        self.assertEqual(
            belum, [],
            f"konstanta baru di scenario/state.py belum diklasifikasikan: {belum}",
        )

    def test_bidang_skenario_baru_ikut_dipertimbangkan(self):
        """
        Bidang baru pada `Skenario` wajib dipertimbangkan: terikat kanonik
        (BAWAAN_KANONIK) atau sengaja bebas (kelas D/E yang didaftar di sini).
        """
        bebas = {
            "durasi_hujan_jam", "total_pengikat_ton", "volume_adukan_m3",
            "co2_per_ton_semen",
        }
        terikat = {n for n, _ in BawaanSkenario.BAWAAN_KANONIK}
        semua = {f.name for f in dataclasses.fields(state.Skenario)}
        belum = sorted(semua - terikat - bebas)
        self.assertEqual(
            belum, [],
            f"bidang Skenario baru belum diklasifikasikan terikat/bebas: {belum}",
        )

    def test_peta_tidak_menyebut_konstanta_yang_sudah_hilang(self):
        for nama_modul, modul in MODUL.items():
            for nama in TERPETAKAN[nama_modul]:
                with self.subTest(modul=nama_modul, konstanta=nama):
                    self.assertTrue(
                        hasattr(modul, nama),
                        f"peta menyebut core/{nama_modul}.{nama} yang sudah tidak ada",
                    )

    def test_core_tetap_mandiri_dari_lapisan_provenansi(self):
        """
        Salinan ini ada justru karena core/ tidak mengimpor konstanta.py.
        Bila kemandirian itu hilang, salinannya harus dihapus, bukan dijaga.
        """
        for nama_modul, modul in MODUL.items():
            with self.subTest(modul=nama_modul):
                teks = _sumber(modul)
                pohon = ast.parse(teks)
                impor = set()
                for simpul in ast.walk(pohon):
                    if isinstance(simpul, ast.Import):
                        impor.update(a.name.split(".")[0] for a in simpul.names)
                    elif isinstance(simpul, ast.ImportFrom) and simpul.module:
                        impor.add(simpul.module.split(".")[0])
                self.assertEqual(
                    impor & {"konstanta", "data", "ui", "scenario"}, set(),
                    f"core/{nama_modul}.py mulai mengimpor lapisan lain",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
