"""
Uji antarmuka Tab 4 — Retensi Air (S5-4).

Menjaga satu perbedaan yang sangat mudah tertukar: **retensi terukur** milik
konfigurasi yang benar-benar diuji, versus **asumsi retensi** yang dimasukkan
pengguna untuk menjelajah skenario.

Sebelum S5-4 keduanya tertukar. Penggeser retensi selalu terisi 40,0% apa pun
skenario yang aktif, sehingga komposisi yang tidak pernah dicetak langsung
menghasilkan angka hidrologi yang persis sama dengan konfigurasi penelitian —
sementara tabel perbandingan menyatakan retensinya belum tersedia.

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import ast
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import hidrologi  # noqa: E402
from data import akses  # noqa: E402
from scenario import state as skenario  # noqa: E402
from scenario.keluaran import FRASA_TIDAK_TERSEDIA  # noqa: E402
from ui.tabs import retensi_air as tab_ret  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_TAB = os.path.join(AKAR, "ui", "tabs", "retensi_air.py")
TENGGAT = 60

RETENSI_TERUKUR = 40.0
BARIS_RETENSI = "Retensi air"
BARIS_AIR_TERTAHAN = "Air tertahan pada skala area"


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def widget(at, jenis: str, label: str):
    kel = getattr(at, jenis)
    cocok = [x for x in kel if getattr(x, "label", None) == label]
    if not cocok:
        raise AssertionError(
            f"{jenis} {label!r} tidak ada; yang ada: "
            f"{[getattr(x, 'label', '?') for x in kel]}"
        )
    return cocok[0]


def ada_widget(at, jenis: str, label: str) -> bool:
    return any(getattr(x, "label", None) == label for x in getattr(at, jenis))


def skenario_kustom(at, persen: float) -> AppTest:
    at.sidebar.button[0].click().run()
    return geser_ipal(at, persen)


def geser_ipal(at, persen: float) -> AppTest:
    [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(persen).run()
    return at


def pakai_asumsi(at) -> AppTest:
    widget(at, "checkbox",
           "Lanjutkan dengan asumsi retensi saya sendiri").set_value(True).run()
    return at


# ── bagian-bagian Tab 4 ──

def kotak_retensi_aktif(at) -> str | None:
    cocok = [m.value for m in at.markdown
             if "Tingkat retensi skenario aktif" in m.value]
    return cocok[0] if cocok else None


def peringatan_retensi(at) -> str | None:
    cocok = [w.value for w in at.warning
             if BARIS_RETENSI in w.value and FRASA_TIDAK_TERSEDIA in w.value]
    return cocok[0] if cocok else None


def nilai_retensi_aktif(at) -> float:
    kotak = kotak_retensi_aktif(at)
    if kotak is None:
        raise AssertionError("kotak retensi skenario aktif tidak digambar")
    return float(re.search(r'result-value">([\d.]+) %', kotak).group(1))


def tabel_hidrologi(at) -> str | None:
    cocok = [m.value for m in at.markdown if "Volume Air Tersimpan" in m.value]
    return cocok[0] if cocok else None


def peringatan_hidrologi(at) -> str | None:
    cocok = [w.value for w in at.warning if "Hasil hidrologi" in w.value]
    return cocok[0] if cocok else None


def angka_hidrologi(at) -> dict:
    tabel = tabel_hidrologi(at)
    if tabel is None:
        raise AssertionError("tabel hidrologi tidak digambar")
    angka = [a or b for a, b in
             re.findall(r">([\d.]+) m³<|>([\d.]+)%<", tabel)]
    return {
        "volume_hujan": float(angka[0]),
        "limpasan_konvensional": float(angka[1]),
        "limpasan_zeopave": float(angka[2]),
        "air_tertahan": float(angka[3]),
        "reduksi": float(angka[4]),
    }


def status_hidrologi(at) -> str:
    return re.search(
        r'font-weight:600">(MODEL[^<]*)', tabel_hidrologi(at)).group(1)


def sel_perbandingan(at, baris: str, kolom: str) -> str:
    df = at.dataframe[0].value
    return df[df["Keluaran"] == baris].iloc[0][kolom]


def seluruh_teks(at) -> str:
    bagian = []
    for kel in (at.markdown, at.caption, at.info, at.warning, at.success, at.error):
        bagian.extend(str(getattr(e, "value", "")) for e in kel)
    return "\n".join(bagian)


# ═══════════ 1. konfigurasi acuan ═══════════

class KonfigurasiAcuan(unittest.TestCase):
    """40,0% terukur untuk komposisi yang benar-benar diuji."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_retensi_terukur_tersedia(self):
        self.assertIsNotNone(kotak_retensi_aktif(self.at))
        self.assertIsNone(peringatan_retensi(self.at))

    def test_nilai_40_persen(self):
        self.assertAlmostEqual(nilai_retensi_aktif(self.at), RETENSI_TERUKUR,
                               delta=0.05)
        self.assertAlmostEqual(nilai_retensi_aktif(self.at),
                               akses.nilai("RETENSI_RERATA"), delta=0.05)

    def test_status_bukti_terukur(self):
        self.assertIn("terukur", kotak_retensi_aktif(self.at))
        self.assertEqual(akses.status("RETENSI_RERATA"), akses.TERUKUR)

    def test_provenansi_ditampilkan(self):
        self.assertIn(akses.besaran("RETENSI_RERATA").provenans(),
                      [c.value for c in self.at.caption])

    def test_nilai_lama_39_7_tidak_kembali(self):
        self.assertNotIn("39.7", seluruh_teks(self.at))

    def test_penggeser_berangkat_dari_nilai_terukur(self):
        self.assertAlmostEqual(
            widget(self.at, "slider", "Tingkat Retensi (%)").value,
            RETENSI_TERUKUR, delta=1e-9)

    def test_hidrologi_bertumpu_pada_hasil_ukur(self):
        self.assertIn("retensi terukur konfigurasi acuan",
                      status_hidrologi(self.at))
        self.assertIn("Memakai hasil ukur konfigurasi acuan",
                      seluruh_teks(self.at))

    def test_angka_hidrologi_sama_dengan_core(self):
        """Dihitung ulang mandiri lewat core/hidrologi.py."""
        diharapkan = hidrologi.skenario(50.0, 1000.0, 1.0, RETENSI_TERUKUR,
                                        koefisien_limpasan_konvensional=0.85)
        a = angka_hidrologi(self.at)
        self.assertAlmostEqual(a["volume_hujan"],
                               diharapkan["volume_hujan_m3"], delta=0.05)
        self.assertAlmostEqual(a["air_tertahan"],
                               diharapkan["air_tertahan_m3"], delta=0.05)
        self.assertAlmostEqual(a["reduksi"],
                               diharapkan["reduksi_limpasan_persen"], delta=0.05)

    def test_diagram_aliran_digambar(self):
        self.assertIn("Neraca massa tertutup", seluruh_teks(self.at))


# ═══════════ 2. skenario kustom tanpa asumsi ═══════════

class SkenarioKustomTanpaAsumsi(unittest.TestCase):
    """
    Komposisi yang belum diuji tidak mewarisi 40,0%, dan tanpa retensi tidak
    ada satu pun angka hidrologi yang boleh muncul.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = skenario_kustom(jalankan(), 22)

    def test_skenario_memang_kustom(self):
        k = self.at.session_state[skenario.KUNCI]
        self.assertFalse(skenario.cocok_konfigurasi_uji(k.ambil("A")))

    def test_retensi_terukur_tidak_tersedia(self):
        self.assertIsNone(
            kotak_retensi_aktif(self.at),
            "kotak retensi terukur masih digambar untuk komposisi belum diuji")
        self.assertIsNotNone(peringatan_retensi(self.at))

    def test_tidak_mewarisi_nilai_terukur(self):
        peringatan = peringatan_retensi(self.at)
        self.assertNotIn("40.0", peringatan)
        self.assertNotIn("40,0", peringatan)

    def test_tanpa_status_bukti_pada_keluaran_kosong(self):
        peringatan = peringatan_retensi(self.at)
        for status in ("terukur", "deterministik", "literatur", "target", "asumsi"):
            self.assertNotIn(status, peringatan.lower())

    def test_tidak_ada_penggeser_yang_terisi_nilai_terukur(self):
        """Inti temuan S5-4: 40,0% tidak boleh dipasang sebagai titik awal."""
        self.assertFalse(ada_widget(self.at, "slider", "Tingkat Retensi (%)"))
        for s in self.at.slider:
            if "etensi" in s.label:
                self.assertNotAlmostEqual(float(s.value), RETENSI_TERUKUR,
                                          delta=1e-9)

    def test_asumsi_tidak_aktif_secara_bawaan(self):
        self.assertFalse(widget(
            self.at, "checkbox",
            "Lanjutkan dengan asumsi retensi saya sendiri").value)

    def test_hidrologi_ikut_tidak_tersedia(self):
        """Ketidaktersediaan merambat: tanpa retensi, tidak ada air tertahan."""
        self.assertIsNone(tabel_hidrologi(self.at))
        self.assertIsNotNone(peringatan_hidrologi(self.at))
        self.assertIn(FRASA_TIDAK_TERSEDIA, peringatan_hidrologi(self.at))

    def test_tidak_ada_angka_yang_direka(self):
        peringatan = peringatan_hidrologi(self.at)
        self.assertNotIn("0.0 m³", peringatan)
        self.assertNotIn("20.0", peringatan)
        self.assertNotEqual(peringatan.strip(), "")

    def test_diagram_aliran_tidak_digambar(self):
        self.assertIn("Belum dapat digambar", seluruh_teks(self.at))

    def test_alasan_dijelaskan(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("Substitusi lumpur IPAL", teks)
        self.assertIn(tab_ret.PESAN_TANPA_PREDIKSI, [c.value for c in self.at.caption])
        self.assertIn(tab_ret.PESAN_HIDROLOGI_TERTAHAN,
                      [c.value for c in self.at.caption])

    def test_tab_dan_tabel_sepakat(self):
        self.assertEqual(
            sel_perbandingan(self.at, BARIS_RETENSI, "Skenario A"),
            FRASA_TIDAK_TERSEDIA)
        self.assertEqual(
            sel_perbandingan(self.at, BARIS_AIR_TERTAHAN, "Skenario A"),
            FRASA_TIDAK_TERSEDIA)
        self.assertIsNone(kotak_retensi_aktif(self.at))
        self.assertIsNone(tabel_hidrologi(self.at))

    def test_acuan_tetap_terukur_di_tabel(self):
        sel = sel_perbandingan(self.at, BARIS_RETENSI, "Acuan Penelitian")
        self.assertIn("40.00", sel)
        self.assertIn("terukur", sel)


# ═══════════ 3. skenario kustom dengan asumsi eksplisit ═══════════

class SkenarioKustomDenganAsumsi(unittest.TestCase):
    """
    Menjelajah skenario tetap boleh, asalkan angkanya jelas milik pengguna dan
    tidak pernah menyamar sebagai hasil pengukuran.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = pakai_asumsi(skenario_kustom(jalankan(), 22))

    def test_penggeser_asumsi_muncul(self):
        self.assertTrue(ada_widget(self.at, "slider", "Asumsi tingkat retensi (%)"))

    def test_tidak_berangkat_dari_nilai_terukur(self):
        nilai = widget(self.at, "slider", "Asumsi tingkat retensi (%)").value
        self.assertNotAlmostEqual(float(nilai), RETENSI_TERUKUR, delta=1e-9)
        self.assertAlmostEqual(float(nilai), tab_ret.RETENSI_AWAL_ASUMSI,
                               delta=1e-9)

    def test_ditandai_asumsi_pengguna(self):
        teks = "\n".join(w.value for w in self.at.warning)
        self.assertIn("adalah asumsi Anda", teks)
        self.assertIn("bukan hasil pengukuran", teks)

    def test_tidak_mewarisi_status_terukur(self):
        peringatan = [w.value for w in self.at.warning if "asumsi Anda" in w.value][0]
        self.assertNotIn("terukur", peringatan)
        self.assertNotIn("hasil penelitian", peringatan)

    def test_tidak_mewarisi_sumber_hasil_ukur(self):
        """Asumsi tidak boleh membawa provenansi OUTPUT3 Tabel 4.3."""
        peringatan = [w.value for w in self.at.warning if "asumsi Anda" in w.value][0]
        self.assertNotIn("Tabel 4.3", peringatan)
        self.assertNotIn(akses.besaran("RETENSI_RERATA").sumber, peringatan)

    def test_hidrologi_tersedia_tetapi_berstatus_asumsi(self):
        self.assertIsNotNone(tabel_hidrologi(self.at))
        self.assertIn("ASUMSI", status_hidrologi(self.at))
        self.assertIn("MODEL", status_hidrologi(self.at))
        self.assertNotIn("terukur", status_hidrologi(self.at))

    def test_angka_mengikuti_asumsi_bukan_nilai_terukur(self):
        diharapkan = hidrologi.skenario(
            50.0, 1000.0, 1.0, tab_ret.RETENSI_AWAL_ASUMSI,
            koefisien_limpasan_konvensional=0.85)
        a = angka_hidrologi(self.at)
        self.assertAlmostEqual(a["air_tertahan"],
                               diharapkan["air_tertahan_m3"], delta=0.05)
        terukur = hidrologi.skenario(50.0, 1000.0, 1.0, RETENSI_TERUKUR)
        self.assertNotAlmostEqual(a["air_tertahan"],
                                  terukur["air_tertahan_m3"], delta=0.5)

    def test_retensi_terukur_tetap_dinyatakan_tidak_tersedia(self):
        """Menyediakan asumsi tidak membuat komposisinya menjadi teruji."""
        self.assertIsNone(kotak_retensi_aktif(self.at))
        self.assertIsNotNone(peringatan_retensi(self.at))
        self.assertEqual(
            sel_perbandingan(self.at, BARIS_RETENSI, "Skenario A"),
            FRASA_TIDAK_TERSEDIA)


# ═══════════ 4. menggeser retensi pada konfigurasi acuan ═══════════

class MenggeserRetensiPadaAcuan(unittest.TestCase):
    """Begitu digeser dari nilai terukur, angkanya menjadi asumsi pengguna."""

    @classmethod
    def setUpClass(cls):
        at = jalankan()
        widget(at, "slider", "Tingkat Retensi (%)").set_value(35.0).run()
        cls.at = at

    def test_ditandai_asumsi_bukan_hasil_ukur(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("asumsi Anda", teks)
        self.assertIn("bukan lagi hasil ukur", teks)

    def test_nilai_terukur_tetap_disebutkan(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("tetap 40.0%", teks)

    def test_status_hidrologi_ikut_menjadi_asumsi(self):
        self.assertIn("ASUMSI", status_hidrologi(self.at))

    def test_retensi_terukur_skenario_aktif_tidak_berubah(self):
        """Menggeser kendali tidak mengubah hasil pengukuran."""
        self.assertAlmostEqual(nilai_retensi_aktif(self.at), RETENSI_TERUKUR,
                               delta=0.05)


# ═══════════ 5. identitas dipulihkan ═══════════

class IdentitasDipulihkan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        at = skenario_kustom(jalankan(), 22)
        cls.saat_berbeda_tab = kotak_retensi_aktif(at)
        cls.saat_berbeda_tabel = sel_perbandingan(at, BARIS_RETENSI, "Skenario A")
        cls.at = geser_ipal(at, int(skenario.ACUAN_SUBSTITUSI_IPAL))

    def test_sempat_tidak_tersedia(self):
        self.assertIsNone(self.saat_berbeda_tab)
        self.assertEqual(self.saat_berbeda_tabel, FRASA_TIDAK_TERSEDIA)

    def test_identitas_pulih(self):
        k = self.at.session_state[skenario.KUNCI]
        self.assertTrue(skenario.cocok_konfigurasi_uji(k.ambil("A")))

    def test_retensi_terukur_kembali_tersedia(self):
        self.assertIsNotNone(kotak_retensi_aktif(self.at))
        self.assertAlmostEqual(nilai_retensi_aktif(self.at), RETENSI_TERUKUR,
                               delta=0.05)
        self.assertIn("terukur", kotak_retensi_aktif(self.at))

    def test_hidrologi_kembali_tersedia(self):
        self.assertIsNotNone(tabel_hidrologi(self.at))
        self.assertIn("retensi terukur konfigurasi acuan", status_hidrologi(self.at))

    def test_tabel_perbandingan_ikut_pulih(self):
        sel = sel_perbandingan(self.at, BARIS_RETENSI, "Skenario A")
        self.assertIn("40.00", sel)
        self.assertIn("terukur", sel)


# ═══════════ 6. batas arsitektur ═══════════

class BatasArsitektur(unittest.TestCase):

    def _sumber(self) -> str:
        with open(BERKAS_TAB, encoding="utf8") as f:
            return f.read()

    def _impor(self) -> set:
        jalur = set()
        for simpul in ast.walk(ast.parse(self._sumber(), filename=BERKAS_TAB)):
            if isinstance(simpul, ast.Import):
                jalur.update(a.name for a in simpul.names)
            elif isinstance(simpul, ast.ImportFrom) and simpul.module:
                jalur.add(simpul.module)
        return jalur

    def test_tidak_mengimpor_streamlit(self):
        self.assertNotIn("streamlit", {j.split(".")[0] for j in self._impor()})

    def test_memakai_core_dan_data_kanonik(self):
        self.assertIn("core", {j.split(".")[0] for j in self._impor()})
        self.assertIn("data", {j.split(".")[0] for j in self._impor()})

    def test_membaca_model_keluaran_tanpa_menyelesaikannya_sendiri(self):
        impor = self._impor()
        self.assertIn("scenario.keluaran", impor)
        self.assertNotIn("scenario.resolusi", impor)
        self.assertNotIn("scenario.state", impor)

    def test_tidak_menduplikasi_aturan_identitas_konfigurasi(self):
        sumber = self._sumber()
        for terlarang in ("cocok_konfigurasi_uji", "substitusi_ipal_persen",
                          "alasan_berbeda", "PARAMETER_KONFIGURASI_UJI",
                          "faktor_air_pengikat", "rasio_agregat"):
            self.assertNotIn(
                terlarang, sumber,
                f"aturan ADR-009 tergandakan di lapisan tampilan: {terlarang}")

    def test_tanpa_model_komposisi_ke_retensi(self):
        """Tidak boleh ada fungsi yang menebak retensi dari komposisi."""
        sumber = self._sumber()
        for terlarang in ("def prediksi", "def taksir", "def estimasi_retensi",
                          "regresi", "interpolasi"):
            self.assertNotIn(terlarang, sumber.lower())
        for nama in dir(hidrologi):
            self.assertNotIn("prediksi", nama.lower())
            self.assertNotIn("komposisi", nama.lower())

    def test_tanpa_rumus_hidrologi_tergandakan(self):
        sumber = self._sumber()
        self.assertNotIn("math", {j.split(".")[0] for j in self._impor()})
        for pola in ("/ 1000.0", "* (r / 100", "volume_hujan *"):
            self.assertNotIn(pola, sumber, f"rumus core tergandakan: {pola}")
        self.assertIn("hidrologi.skenario", sumber)

    def test_kontrak_render(self):
        for simpul in ast.walk(ast.parse(self._sumber(), filename=BERKAS_TAB)):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                self.assertEqual(
                    [a.arg for a in simpul.args.args],
                    ["st", "retensi_aktif", "luas_area_m2",
                     "intensitas_hujan_mm_per_jam"],
                    "kontrak Tab 4 harus tetap minimal dan eksplisit")
                return
        self.fail("fungsi render() tidak ditemukan")

    def test_aquapave_hanya_mengorkestrasi(self):
        with open(BERKAS_APLIKASI, encoding="utf8") as f:
            isi = f.read()
        self.assertIn(
            "tab_retensi_air.render(st, RETENSI_AKTIF, area_m2, intensitas_hujan)",
            isi)
        self.assertIn("RETENSI_AKTIF = HASIL_SKENARIO_AKTIF[OutputID.RETENTION]", isi)
        for sisa in ("Tingkat Retensi (%)", "Koefisien Limpasan Sebelum",
                     "hidrologi.skenario", "Sankey"):
            self.assertNotIn(sisa, isi, f"sisa Tab 4 tertinggal di AQUAPAVE.py: {sisa}")


# ═══════════ S7-J: kendali tebal yang tidak berpengaruh ═══════════

class KendaliTebalSudahDihapus(unittest.TestCase):
    """
    SD-07 ditutup: penulis memutuskan **menghapus** kedua kendali tebal.

    Keduanya tidak pernah memengaruhi satu angka pun, dan bawaannya (300 mm
    dan 150 mm) tidak punya sumber di dalam penelitian. Penghapusan ini
    membuang antarmuka mati; ia **bukan** perubahan model hidrologi, dan
    **bukan** penyelarasan dengan geometri Tab 7.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_kedua_kendali_tidak_ada_lagi(self):
        label = [w.label for w in list(self.at.number_input) + list(self.at.slider)]
        self.assertNotIn("Kedalaman Struktural Perkerasan (mm)", label)
        self.assertNotIn("Tebal Lapisan Hebel–Zeolit (mm)", label)

    def test_tidak_ada_sisa_di_sumber(self):
        """Variabel, label, dan keterangan yatimnya ikut hilang."""
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        pohon = ast.parse(sumber)
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.Name) and simpul.id in (
                "kedalaman_mm", "tebal_zeolit", "CATATAN_KENDALI_MATI"
            ):
                self.fail(f"sisa kendali mati: {simpul.id}")

    def test_masukan_hidrologi_tetap_utuh(self):
        """
        Penghapusan tidak boleh menyentuh masukan yang benar-benar dipakai
        core/hidrologi.skenario().
        """
        label = [w.label for w in list(self.at.number_input) + list(self.at.slider)]
        for wajib in ("Durasi Hujan (jam)",
                      "Koefisien Limpasan Sebelum ZEOPAVE (C)"):
            self.assertIn(wajib, label)

    def test_tebal_tidak_dipindahkan_dari_tab_biaya(self):
        """
        Penghapusan BUKAN penyelarasan: geometri 2 cm dan 7,5 cm tetap hidup
        di Tab 7 saja, dan tidak boleh muncul di sini sebagai penggantinya.
        """
        from ui.tabs import biaya as tab_biaya

        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        self.assertNotIn("TEBAL_BETON_M", sumber)
        self.assertNotIn("TEBAL_RETENSI_M", sumber)
        # Tab 7 tetap memiliki dan memakai geometrinya sendiri.
        self.assertAlmostEqual(tab_biaya.TEBAL_BETON_M, 0.02, delta=1e-12)
        self.assertAlmostEqual(tab_biaya.TEBAL_RETENSI_M, 0.075, delta=1e-12)

    def test_model_hidrologi_tetap_tanpa_parameter_tebal(self):
        """core/hidrologi.py tidak disentuh: tebal tidak pernah masukannya."""
        import inspect

        from core import hidrologi

        param = set(inspect.signature(hidrologi.skenario).parameters)
        self.assertEqual(
            param,
            {"intensitas_mm_per_jam", "luas_m2", "durasi_jam", "retensi_persen",
             "koefisien_limpasan_konvensional"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
