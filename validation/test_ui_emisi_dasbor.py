"""
Uji antarmuka Tab 5 dan Tab 6 — Emisi CO₂ dan Dasbor (S5-5).

Keduanya diuji bersama karena keduanya memakai satu hasil bersama: neraca
emisi yang dihitung SEKALI sebelum tab mana pun digambar (ADR-008). Menguji
salah satunya saja tidak akan menangkap kembalinya ketergantungan urutan
eksekusi antartab.

Dua hal yang dijaga di sini dan tidak di tempat lain:

  1. **Satu neraca CO₂ yang berwenang.** Tidak satu pun modul tab menghitung
     ulang neracanya, dan menggambar Tab 6 lebih dulu daripada Tab 5 tidak
     mengubah apa pun.

  2. **Dasbor tunduk pada ketersediaan.** Air tertahan diturunkan dari retensi;
     bila retensi belum diukur untuk komposisi aktif, dasbor tidak boleh
     diam-diam memakai 40,0% milik konfigurasi acuan (koreksi S5-5, mengikuti
     pola S5-4).

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

from core import emisi  # noqa: E402
from data import akses  # noqa: E402
from scenario import resolusi  # noqa: E402
from scenario import state as skenario  # noqa: E402
from scenario.keluaran import FRASA_TIDAK_TERSEDIA, OutputID  # noqa: E402
from ui.tabs import dasbor as tab_dasbor  # noqa: E402
from ui.tabs import emisi_co2 as tab_co2  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_TAB = os.path.join(AKAR, "ui", "tabs", "dasbor.py")
BERKAS_CO2 = os.path.join(AKAR, "ui", "tabs", "emisi_co2.py")
BERKAS_DASBOR = os.path.join(AKAR, "ui", "tabs", "dasbor.py")
TENGGAT = 60

METRIK_AIR = "Air Tersimpan (hujan 1 jam)"
METRIK_IPAL = "Lumpur IPAL Termanfaatkan"
METRIK_CO2 = "CO₂ Terhindarkan"


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def skenario_kustom(at, persen: float) -> AppTest:
    at.sidebar.button[0].click().run()
    return geser_ipal(at, persen)


def geser_ipal(at, persen: float) -> AppTest:
    [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(persen).run()
    return at


def metrik(at, label: str):
    cocok = [m for m in at.metric if m.label == label]
    return cocok[0] if cocok else None


def tabel_co2(at) -> str:
    cocok = [m.value for m in at.markdown if "CO₂ — Konvensional" in m.value]
    if not cocok:
        raise AssertionError("tabel neraca CO₂ tidak digambar")
    return cocok[0]


def angka_co2(at) -> dict:
    tabel = tabel_co2(at)
    ton = [float(x) for x in re.findall(r">([\d.]+) ton CO₂<", tabel)]
    return {"konvensional": ton[0], "zeopave": ton[1]}


def peringatan_air(at) -> str | None:
    cocok = [w.value for w in at.warning
             if "Air tertahan" in w.value and FRASA_TIDAK_TERSEDIA in w.value]
    return cocok[0] if cocok else None


def seluruh_teks(at) -> str:
    bagian = []
    for kel in (at.markdown, at.caption, at.info, at.warning, at.success, at.error):
        bagian.extend(str(getattr(e, "value", "")) for e in kel)
    return "\n".join(bagian)


def sel_perbandingan(at, baris: str, kolom: str) -> str:
    df = at.dataframe[0].value
    return df[df["Keluaran"] == baris].iloc[0][kolom]


# ── st palsu, untuk menggambar tab tanpa Streamlit ──

class WadahPalsu:
    def __init__(self, induk):
        self.induk = induk

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class StPalsu:
    """Perekam panggilan; cukup untuk kedua modul tab ini."""

    def __init__(self):
        self.dicatat: list[tuple] = []

    def columns(self, n):
        return [WadahPalsu(self) for _ in range(n if isinstance(n, int) else len(n))]

    def markdown(self, teks, **_):
        self.dicatat.append(("markdown", teks))

    def caption(self, teks, **_):
        self.dicatat.append(("caption", teks))

    def metric(self, label, value, delta=None, **_):
        self.dicatat.append(("metric", label, value, delta))

    def warning(self, teks, **_):
        self.dicatat.append(("warning", teks))

    def divider(self):
        self.dicatat.append(("divider",))

    def plotly_chart(self, fig, **_):
        self.dicatat.append(("plotly", fig.layout.title.text))

    def dataframe(self, df, **_):
        self.dicatat.append(("dataframe", df.to_csv(index=False)))


def pohon_modul(berkas: str) -> ast.Module:
    """Pohon sintaks sebuah berkas — dipakai pemeriksaan berlingkup fungsi."""
    with open(berkas, encoding="utf8") as f:
        return ast.parse(f.read(), filename=berkas)


def keluaran_acuan():
    return resolusi.resolusi(skenario.acuan_penelitian())


def neraca_acuan():
    s = skenario.acuan_penelitian()
    return emisi.neraca(s.total_pengikat_ton, s.substitusi_ipal_persen,
                        s.co2_per_ton_semen, s.co2_per_ton_ipal)


# ═══════════ A. hasil bersama CO₂ dan urutan tab ═══════════

class HasilBersamaCO2(unittest.TestCase):
    """Satu neraca yang berwenang, dibaca kedua tab tanpa dihitung ulang."""

    def test_kedua_modul_tidak_menghitung_neraca(self):
        """
        Dibaca dari pohon sintaks: dokumentasi yang MENYEBUT emisi.neraca()
        tidak sama dengan memanggilnya.
        """
        for berkas in (BERKAS_CO2, BERKAS_DASBOR):
            with open(berkas, encoding="utf8") as f:
                pohon = ast.parse(f.read(), filename=berkas)
            for simpul in ast.walk(pohon):
                if isinstance(simpul, ast.Call):
                    f_ = simpul.func
                    if isinstance(f_, ast.Attribute) and f_.attr == "neraca":
                        self.fail(f"{berkas} memanggil neraca CO₂ sendiri")

    def test_dasbor_tidak_mengimpor_core_emisi(self):
        with open(BERKAS_DASBOR, encoding="utf8") as f:
            isi = f.read()
        self.assertNotIn("from core import", isi)

    def test_tab_tidak_saling_mengimpor(self):
        for berkas, lawan in ((BERKAS_CO2, "dasbor"), (BERKAS_DASBOR, "emisi_co2")):
            with open(berkas, encoding="utf8") as f:
                isi = f.read()
            self.assertNotIn(lawan, isi, f"{berkas} bergantung pada tab lain")

    def test_urutan_menggambar_tidak_berpengaruh(self):
        """
        Regresi ADR-008: menggambar dasbor lebih dulu harus memberi hasil yang
        sama persis dengan menggambar Tab 5 lebih dulu.
        """
        h = neraca_acuan()
        k = keluaran_acuan()
        argumen_dasbor = (k[OutputID.RETENTION], k[OutputID.RUNOFF])

        maju_co2, maju_dasbor = StPalsu(), StPalsu()
        tab_co2.render(maju_co2, h)
        tab_dasbor.render(maju_dasbor, *argumen_dasbor)

        mundur_dasbor, mundur_co2 = StPalsu(), StPalsu()
        tab_dasbor.render(mundur_dasbor, *argumen_dasbor)
        tab_co2.render(mundur_co2, h)

        self.assertEqual(maju_co2.dicatat, mundur_co2.dicatat)
        self.assertEqual(maju_dasbor.dicatat, mundur_dasbor.dicatat)

    def test_menggambar_dua_kali_tidak_mengubah_hasil_bersama(self):
        """Menggambar tidak boleh memutasi neraca yang dibagikan."""
        h = neraca_acuan()
        salinan = dict(h)
        tab_co2.render(StPalsu(), h)
        k = keluaran_acuan()
        tab_dasbor.render(StPalsu(), k[OutputID.RETENTION], k[OutputID.RUNOFF])
        self.assertEqual(h, salinan)

    def test_kedua_tampilan_konsisten(self):
        at = jalankan()
        h = neraca_acuan()
        a = angka_co2(at)
        self.assertAlmostEqual(a["konvensional"], h["co2_konvensional_ton"],
                               delta=0.01)
        self.assertAlmostEqual(a["zeopave"], h["co2_zeopave_ton"], delta=0.01)
        # SD-06: metrik CO2 dasbor dipensiunkan; Tab 5 tetap sumber tunggalnya.
        self.assertNotIn(METRIK_CO2, [m.label for m in at.metric])


# ═══════════ B. konfigurasi acuan ═══════════

class KonfigurasiAcuan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_neraca_co2_tampil(self):
        h = neraca_acuan()
        a = angka_co2(self.at)
        self.assertAlmostEqual(a["zeopave"], h["co2_zeopave_ton"], delta=0.01)

    def test_klaim_laboratorium_tetap_tidak_tersedia(self):
        self.assertIn("Klaim penghematan uji laboratorium", tabel_co2(self.at))
        self.assertIn("tidak tersedia", tabel_co2(self.at))

    def test_air_tersimpan_tersedia(self):
        m = metrik(self.at, METRIK_AIR)
        self.assertIsNotNone(m)
        self.assertEqual(m.value, "20 m³")
        self.assertIn("40", m.delta)

    def test_air_tersimpan_sama_dengan_resolusi(self):
        """Dasbor memakai keluaran resolusi, bukan hitungannya sendiri."""
        k = keluaran_acuan()[OutputID.RUNOFF]
        self.assertAlmostEqual(
            float(metrik(self.at, METRIK_AIR).value.split()[0]),
            k.nilai / 1000.0, delta=0.5)

    def test_metrik_lain_utuh(self):
        """SD-06: metrik IPAL dipensiunkan; yang tersisa tetap utuh."""
        self.assertIsNone(metrik(self.at, METRIK_IPAL))
        self.assertEqual(metrik(self.at, "Optimasi Material").value, "n/a")

    def test_himpunan_sdg_kanonik(self):
        self.assertEqual(set(tab_co2.SKOR_SDG), set(akses.sdg_didukung()))
        self.assertEqual(set(tab_co2.NAMA_SINGKAT_SDG), set(akses.sdg_didukung()))
        for n in akses.sdg_didukung():
            self.assertIn(f"SDG {n}", seluruh_teks(self.at))


# ═══════════ C. skenario kustom ═══════════

class SkenarioKustom(unittest.TestCase):
    """
    CO₂ deterministik dihitung ulang; hasil ukur tetap tidak tersedia; dasbor
    berhenti memakai retensi konfigurasi acuan.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = skenario_kustom(jalankan(), 22)
        cls.acuan = jalankan()

    def test_co2_dihitung_ulang(self):
        a = angka_co2(self.at)
        b = angka_co2(self.acuan)
        self.assertNotAlmostEqual(a["zeopave"], b["zeopave"], delta=0.01)
        s = self.at.session_state[skenario.KUNCI].ambil("A")
        h = emisi.neraca(s.total_pengikat_ton, s.substitusi_ipal_persen,
                         s.co2_per_ton_semen, s.co2_per_ton_ipal)
        self.assertAlmostEqual(a["zeopave"], h["co2_zeopave_ton"], delta=0.01)

    def test_air_tersimpan_tidak_tersedia(self):
        """KOREKSI S5-5: 40,0% tidak lagi dipakai diam-diam."""
        self.assertIsNone(
            metrik(self.at, METRIK_AIR),
            "dasbor masih menampilkan air tersimpan untuk komposisi belum diuji")
        self.assertIsNotNone(peringatan_air(self.at))
        self.assertIn(FRASA_TIDAK_TERSEDIA, peringatan_air(self.at))

    def test_tidak_ada_angka_yang_direka(self):
        peringatan = peringatan_air(self.at)
        self.assertNotIn("20 m³", peringatan)
        self.assertNotIn("40%", peringatan)
        self.assertNotIn("0 m³", peringatan)

    def test_alasan_dan_arah_dijelaskan(self):
        self.assertIn(tab_dasbor.PESAN_AIR_TIDAK_TERSEDIA,
                      [c.value for c in self.at.caption])

    def test_tanpa_status_bukti_pada_keluaran_kosong(self):
        peringatan = peringatan_air(self.at)
        for status in ("terukur", "deterministik", "literatur", "target", "asumsi"):
            self.assertNotIn(status, peringatan.lower())

    def test_hasil_ukur_tetap_tidak_tersedia_di_tabel(self):
        for baris in ("Kuat tekan (7 hari)", "Koefisien permeabilitas",
                      "Retensi air", "Air tertahan pada skala area"):
            self.assertEqual(
                sel_perbandingan(self.at, baris, "Skenario A"),
                FRASA_TIDAK_TERSEDIA)

    def test_dasbor_sepakat_dengan_tabel_perbandingan(self):
        tabel_kosong = (
            sel_perbandingan(self.at, "Air tertahan pada skala area", "Skenario A")
            == FRASA_TIDAK_TERSEDIA)
        dasbor_kosong = metrik(self.at, METRIK_AIR) is None
        self.assertEqual(tabel_kosong, dasbor_kosong)

    def test_metrik_dipensiunkan_tetap_absen_pada_skenario_kustom(self):
        """
        SD-06: kedua metrik dipensiunkan untuk SEMUA skenario, bukan hanya
        konfigurasi acuan. Ketidakhadirannya tidak boleh bergantung skenario.
        """
        self.assertIsNone(metrik(self.at, METRIK_IPAL))
        self.assertIsNone(metrik(self.at, METRIK_CO2))

    def test_dasbor_tidak_menawarkan_asumsi_sendiri(self):
        """
        Asumsi retensi dinyatakan di tab Retensi Air, satu tempat saja. Dasbor
        mengarahkan ke sana, bukan menyediakan kendali kedua yang bersaing.
        """
        self.assertEqual(
            [c.label for c in self.at.checkbox
             if "asumsi" in c.label.lower() and "Dasbor" in c.label], [])
        self.assertIn("tab Retensi Air", tab_dasbor.PESAN_AIR_TIDAK_TERSEDIA)


# ═══════════ D. identitas dipulihkan ═══════════

class IdentitasDipulihkan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        at = skenario_kustom(jalankan(), 22)
        cls.saat_berbeda = metrik(at, METRIK_AIR)
        cls.at = geser_ipal(at, int(skenario.ACUAN_SUBSTITUSI_IPAL))

    def test_sempat_tidak_tersedia(self):
        self.assertIsNone(self.saat_berbeda)

    def test_air_tersimpan_kembali_tersedia(self):
        m = metrik(self.at, METRIK_AIR)
        self.assertIsNotNone(m)
        self.assertEqual(m.value, "20 m³")

    def test_tanpa_sisa_keadaan_kustom(self):
        self.assertIsNone(peringatan_air(self.at))
        self.assertNotIn(tab_dasbor.PESAN_AIR_TIDAK_TERSEDIA,
                         [c.value for c in self.at.caption])

    def test_co2_kembali_ke_nilai_acuan(self):
        self.assertAlmostEqual(angka_co2(self.at)["zeopave"],
                               neraca_acuan()["co2_zeopave_ton"], delta=0.01)


# ═══════════ E. skor kualitatif ═══════════

class SkorKualitatif(unittest.TestCase):
    """Radar dan SDG tetap penilaian tim, tidak pernah naik status."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_radar_dinyatakan_penilaian_tim(self):
        teks = "\n".join(w.value for w in self.at.warning)
        self.assertIn("penilaian kualitatif tim", teks)
        self.assertIn("bukan hasil pengukuran", teks)
        self.assertIn("tidak boleh dikutip sebagai temuan penelitian", teks)

    def test_judul_radar_membawa_kualifikasinya(self):
        self.assertIn("penilaian kualitatif tim", tab_dasbor.PERINGATAN_RADAR)

    def test_sdg_dinyatakan_penilaian_tim(self):
        self.assertIn("penilaian kualitatif tim", tab_co2.CATATAN_SDG)
        self.assertIn("bukan hasil pengukuran", tab_co2.CATATAN_SDG)
        self.assertIn(tab_co2.CATATAN_SDG, [c.value for c in self.at.caption])

    def test_skor_tidak_pernah_diklaim_terukur(self):
        """
        Kata "terukur" boleh muncul di dalam kalimat PENYANGKALANNYA; yang
        dilarang adalah skornya diberi status bukti terukur.
        """
        for teks in (tab_dasbor.PERINGATAN_RADAR, tab_co2.CATATAN_SDG):
            self.assertIn("bukan hasil pengukuran", teks)
            self.assertNotRegex(teks, r"skor[^.]*terukur")
        at = jalankan()
        for skor in tab_dasbor.SKOR_ZEOPAVE:
            self.assertNotIn(f"{skor}% · terukur", seluruh_teks(at))

    def test_skor_bukan_keluaran_ilmiah(self):
        """
        Nama kategori radar boleh sama dengan nama besaran ilmiah; yang tidak
        boleh adalah SKORNYA ikut dianggap nilai ilmiah.
        """
        nilai_kunci = {a["nilai"] for a in akses.angka_kunci()}
        for skor in tab_dasbor.SKOR_ZEOPAVE + tab_dasbor.SKOR_KONVENSIONAL:
            self.assertNotIn(float(skor), nilai_kunci)
        for n, skor in tab_co2.SKOR_SDG.items():
            self.assertNotIn(float(skor), nilai_kunci)

    def test_skor_tidak_berubah_menurut_skenario(self):
        """Penilaian tim bukan fungsi komposisi."""
        at = skenario_kustom(jalankan(), 22)
        self.assertEqual(tab_dasbor.SKOR_ZEOPAVE, (95, 80, 75, 85, 65, 90))
        self.assertIn("penilaian kualitatif tim",
                      "\n".join(w.value for w in at.warning))


# ═══════════ F. batas arsitektur ═══════════

class BatasArsitektur(unittest.TestCase):

    def _sumber(self, berkas: str) -> str:
        with open(berkas, encoding="utf8") as f:
            return f.read()

    def _impor(self, berkas: str) -> set:
        jalur = set()
        for simpul in ast.walk(ast.parse(self._sumber(berkas), filename=berkas)):
            if isinstance(simpul, ast.Import):
                jalur.update(a.name for a in simpul.names)
            elif isinstance(simpul, ast.ImportFrom) and simpul.module:
                jalur.add(simpul.module)
        return jalur

    def test_tidak_mengimpor_streamlit(self):
        for berkas in (BERKAS_CO2, BERKAS_DASBOR):
            self.assertNotIn("streamlit",
                             {j.split(".")[0] for j in self._impor(berkas)})

    def test_tidak_menyelesaikan_resolusi_sendiri(self):
        for berkas in (BERKAS_CO2, BERKAS_DASBOR):
            impor = self._impor(berkas)
            self.assertNotIn("scenario.resolusi", impor)
            self.assertNotIn("scenario.state", impor)

    def test_tidak_menduplikasi_aturan_identitas_konfigurasi(self):
        for berkas in (BERKAS_CO2, BERKAS_DASBOR):
            sumber = self._sumber(berkas)
            for terlarang in ("cocok_konfigurasi_uji", "substitusi_ipal_persen ==",
                              "alasan_berbeda", "PARAMETER_KONFIGURASI_UJI"):
                self.assertNotIn(terlarang, sumber, f"{berkas}: {terlarang}")

    def test_ringkasan_dampak_tidak_membaca_retensi_kanonik(self):
        """
        Inti koreksi S5-5, dipertajam pada S6-B.

        Ringkasan dampak adalah bagian yang MILIK skenario aktif; ia harus
        memakai keluaran resolusi dan tidak boleh menyentuh nilai terukur
        kanonik. Sejak S6-B tabel perbandingan memang membaca nilai kanonik —
        itu justru koreksinya — sehingga larangan ini dipersempit ke fungsi
        yang benar-benar melayani skenario aktif, bukan ke seluruh berkas.
        """
        for simpul in ast.walk(pohon_modul(BERKAS_DASBOR)):
            if (isinstance(simpul, ast.FunctionDef)
                    and simpul.name == "_ringkasan_dampak"):
                potongan = ast.get_source_segment(
                    self._sumber(BERKAS_DASBOR), simpul) or ""
                self.assertNotIn("RETENSI_RERATA", potongan)
                self.assertNotIn("akses.", potongan)
                self.assertNotIn("hidrologi", potongan)
                return
        self.fail("_ringkasan_dampak() tidak ditemukan")

    def test_dasbor_tidak_menghitung_hidrologi_sendiri(self):
        """Air tertahan tetap datang dari resolusi, bukan dihitung di dasbor."""
        self.assertNotIn("hidrologi", self._sumber(BERKAS_DASBOR))

    def test_kontrak_render_co2(self):
        self.assertEqual(self._argumen(BERKAS_CO2), ["st", "hasil_co2"])

    def test_kontrak_render_dasbor(self):
        """
        SD-06 mempersempit kontrak: `hasil_co2` dan `luas_area_m2` hanya
        memberi makan metrik yang dipensiunkan, jadi ikut dihapus.
        """
        self.assertEqual(
            self._argumen(BERKAS_DASBOR),
            ["st", "retensi_aktif", "air_tertahan_aktif"])

    def _argumen(self, berkas: str) -> list:
        for simpul in ast.walk(ast.parse(self._sumber(berkas), filename=berkas)):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                return [a.arg for a in simpul.args.args]
        self.fail(f"fungsi render() tidak ditemukan di {berkas}")

    def test_aquapave_hanya_mengorkestrasi(self):
        isi = self._sumber(BERKAS_APLIKASI)
        self.assertIn("tab_emisi_co2.render(st, HASIL_CO2)", isi)
        self.assertIn("tab_dasbor.render(", isi)
        self.assertIn("AIR_TERTAHAN_AKTIF = HASIL_SKENARIO_AKTIF[OutputID.RUNOFF]",
                      isi)
        for sisa in ("skor_zeopave", "Scatterpolar", "tren_substitusi",
                     "Lumpur IPAL Termanfaatkan", "RETENSI_RERATA"):
            self.assertNotIn(sisa, isi, f"sisa Tab 5/6 tertinggal: {sisa}")

    def test_hasil_co2_tetap_dihitung_sekali_sebelum_tab(self):
        isi = self._sumber(BERKAS_APLIKASI)
        self.assertEqual(isi.count("emisi.neraca("), 1)
        self.assertLess(isi.index("HASIL_CO2 = emisi.neraca("),
                        isi.index("tabs = st.tabs("))


# ═══════════ G. tabel perbandingan berbasis nilai kanonik (S6-B) ═══════════

class TabelPerbandinganKanonik(unittest.TestCase):
    """
    Setiap klaim ilmiah di tabel dasbor harus berasal dari sumber kanonik,
    bukan dari literal teks. Sebelum S6-B seluruh selnya literal, dan lewat
    pintu itulah empat nilai yang sudah dihapus ADR-001 kembali.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()
        cls.baris = {b["Parameter"]: b for b in tab_dasbor.baris_perbandingan()}

    def _tabel(self, at):
        for d in at.dataframe:
            if "Parameter" in d.value.columns:
                return d.value
        raise AssertionError("tabel perbandingan rinci tidak digambar")

    def test_tabel_digambar(self):
        self.assertEqual(len(self._tabel(self.at)), 9)

    def test_permeabilitas_memakai_nilai_terukur_kanonik(self):
        sel = self.baris["Permeabilitas"]["ZEOPAVE-AQUA"]
        b = akses.besaran("PERMEABILITAS")
        self.assertIn("1,667", sel)
        self.assertIn(b.satuan, sel)
        self.assertIn(b.status, sel)
        self.assertEqual(b.status, akses.TERUKUR)

    def test_permeabilitas_pembanding_dari_pustaka_yang_disitir(self):
        sel = self.baris["Permeabilitas"]["Perkerasan Konvensional"]
        b = akses.besaran("PERM_BETON_KONVENSIONAL")
        self.assertIn("0,01", sel)
        self.assertIn(akses.LITERATUR, sel)
        self.assertIn(b.sumber, self.baris["Permeabilitas"]["Sumber"])

    def test_kuat_tekan_memakai_hasil_utama_dan_umur_benar(self):
        nama = [p for p in self.baris if p.startswith("Kuat Tekan")][0]
        self.assertIn("7 hari", nama)
        sel = self.baris[nama]["ZEOPAVE-AQUA"]
        self.assertIn("13,19", sel)
        self.assertIn(akses.TERUKUR, sel)

    def test_15_mpa_tidak_muncul_sebagai_hasil_laboratorium(self):
        """Asumsi tidak boleh naik pangkat menjadi hasil uji."""
        seluruh = "\n".join(
            str(v) for b in tab_dasbor.baris_perbandingan() for v in b.values())
        self.assertNotIn("15,00 MPa", seluruh)
        self.assertNotIn("(lab)", seluruh)

    def test_ambang_kuat_tekan_dari_pustaka_bukan_sni(self):
        nama = [p for p in self.baris if p.startswith("Kuat Tekan")][0]
        sumber = self.baris[nama]["Sumber"]
        self.assertIn(akses.besaran("AMBANG_LALU_LINTAS_RINGAN").sumber, sumber)
        self.assertIn("5 MPa", sumber)
        self.assertNotIn("SNI", sumber)

    def test_porositas_tetap_target(self):
        sel = self.baris["Porositas"]["ZEOPAVE-AQUA"]
        self.assertIn(akses.TARGET, sel)
        self.assertIn("belum diukur", sel)
        self.assertEqual(akses.status("POROSITAS_TARGET_MAKS"), akses.TARGET)

    def test_retensi_mempertahankan_ketelitian(self):
        sel = self.baris["Retensi Air"]["ZEOPAVE-AQUA"]
        self.assertIn("40,0", sel)
        self.assertIn(akses.TERUKUR, sel)

    def test_kapasitas_banjir_berstatus_model(self):
        sel = self.baris["Kapasitas Mitigasi Banjir"]["ZEOPAVE-AQUA"]
        self.assertIn(akses.MODEL, sel)
        self.assertIn("20.000", sel)

    def test_co2_tidak_menyatakan_angka_yang_bergantung_skenario(self):
        """Faktor emisi dapat diubah pengguna; tabel acuan tidak boleh mematoknya."""
        sel = self.baris["CO₂ per ton semen"]["ZEOPAVE-AQUA"]
        self.assertIn("Tab 5", sel)
        self.assertNotIn("0,72", sel)

    def test_tanpa_tanda_centang(self):
        """Status bukti ditulis sebagai kata, bukan disandikan tanda grafis."""
        seluruh = "\n".join(
            str(v) for b in tab_dasbor.baris_perbandingan() for v in b.values())
        self.assertNotIn("✅", seluruh)

    def test_sel_tanpa_dasar_dinyatakan_eksplisit(self):
        """Bukan nol, bukan sel kosong, bukan tanda hubung."""
        for b in tab_dasbor.baris_perbandingan():
            for kolom, nilai in b.items():
                self.assertNotEqual(str(nilai).strip(), "")
                self.assertNotEqual(str(nilai).strip(), "-")
                self.assertNotEqual(str(nilai).strip(), "0")
        kosong = [b["Parameter"] for b in tab_dasbor.baris_perbandingan()
                  if tab_dasbor.TIDAK_BERSUMBER in b["Perkerasan Konvensional"]]
        self.assertTrue(kosong, "tidak satu pun sel tanpa dasar ditandai")

    def test_sitasi_tak_bersumber_tidak_dipakai(self):
        seluruh = "\n".join(
            str(v) for b in tab_dasbor.baris_perbandingan() for v in b.values())
        for palsu in ("Chen et al", "ACI 522: 15", "Prototipe lab"):
            self.assertNotIn(palsu, seluruh)

    def test_setiap_sumber_berasal_dari_besaran_kanonik(self):
        """Kolom Sumber hanya boleh berisi sumber kanonik atau pernyataan kosong."""
        sah = {b.sumber for _, b in
               __import__("konstanta").daftar_provenans()}
        for b in tab_dasbor.baris_perbandingan():
            s = b["Sumber"]
            if s == tab_dasbor.TIDAK_BERSUMBER:
                continue
            self.assertTrue(
                any(k in s for k in sah),
                f"sumber tidak kanonik pada baris {b['Parameter']!r}: {s!r}")

    def test_tabel_tidak_berubah_menurut_skenario(self):
        """Tabel menggambarkan konfigurasi acuan, bukan skenario aktif."""
        at = skenario_kustom(jalankan(), 22)
        self.assertEqual(
            self._tabel(at).to_csv(index=False),
            self._tabel(self.at).to_csv(index=False))

    def test_kepemilikan_dinyatakan(self):
        teks = "\n".join(c.value for c in self.at.caption)
        self.assertIn("konfigurasi acuan penelitian", teks)
        self.assertIn("bukan skenario yang sedang aktif", teks)

    def test_dasbor_bukan_sumber_konstanta_ilmiah_kedua(self):
        """
        Nilai ilmiah harus datang lewat akses, bukan didefinisikan di dasbor.
        Konstanta modul yang tersisa hanyalah penilaian kualitatif tim dan satu
        asumsi tonase yang memang sudah ditandai.
        """
        import ast
        with open(BERKAS_DASBOR, encoding="utf8") as f:
            pohon = ast.parse(f.read(), filename=BERKAS_DASBOR)
        angka = []
        for n in pohon.body:
            if isinstance(n, ast.Assign):
                for target in n.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        try:
                            v = ast.literal_eval(n.value)
                        except Exception:
                            continue
                        if isinstance(v, (int, float)):
                            angka.append(target.id)
        # SD-06: IPAL_TON_PER_100_M2 dipensiunkan. Dasbor kini tidak memuat
        # satu pun konstanta ilmiah numerik miliknya sendiri.
        self.assertEqual(sorted(angka), [])


# ═══════════ S7-I: transparansi asumsi tonase IPAL ═══════════

class MetrikIpalDanCo2Dipensiunkan(unittest.TestCase):
    """
    SD-06 ditutup (keputusan penulis): metrik "Lumpur IPAL Termanfaatkan" dan
    "CO₂ Terhindarkan" **dipensiunkan** dari dasbor.

    Sebabnya bukan angkanya kurang tepat, melainkan angkanya mewakili **bahan
    yang salah**: 0,8 t/100 m² tertelusur ke kalimat Abstrak naskah tentang
    kebutuhan SEMEN, bukan lumpur IPAL.

    Keduanya **tidak diganti** angka lain. Dua basis tersisa dan belum
    diputuskan: resep Tab 7 (~3,52 t/1.000 m²) dan campuran kanonik
    (~1,26 t/1.000 m²), keduanya bertumpu pada SD-16C.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_konstanta_tonase_tidak_ada_lagi(self):
        self.assertFalse(hasattr(tab_dasbor, "IPAL_TON_PER_100_M2"))

    def test_kedua_metrik_tidak_ada_lagi(self):
        label = [m.label for m in self.at.metric]
        self.assertNotIn(METRIK_IPAL, label)
        self.assertNotIn(METRIK_CO2, label)

    def test_tidak_ada_perhitungan_tonase_tersisa(self):
        """Termasuk lewat ekspresi lain: tidak boleh ada 0,8 di sumber dasbor."""
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.Constant) and simpul.value == 0.8:
                self.fail("literal 0,8 kembali ke dasbor")
            if isinstance(simpul, ast.Name) and simpul.id in (
                "IPAL_TON_PER_100_M2", "ipal_total_ton", "co2_manfaat"
            ):
                self.fail(f"sisa perhitungan dipensiunkan: {simpul.id}")

    def test_tidak_ada_nilai_pengganti_yang_diselundupkan(self):
        """
        Tidak boleh muncul 3,52 (resep Tab 7) maupun 1,26 (kanonik) sebagai
        pengganti diam-diam. Memilih di antaranya keputusan penulis.
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.Constant) and isinstance(
                simpul.value, float
            ):
                for terlarang in (3.52, 1.26, 0.352, 0.126):
                    self.assertNotAlmostEqual(
                        simpul.value, terlarang, delta=1e-9,
                        msg=f"nilai pengganti diselundupkan: {simpul.value}",
                    )

    def test_pemensiunan_dinyatakan_di_layar(self):
        teks = seluruh_teks(self.at)
        self.assertIn("dipensiunkan", teks)
        self.assertIn("kebutuhan **semen**", teks)

    def test_neraca_emisi_domain_tetap_hidup(self):
        """
        Pemensiunan keluaran dasbor BUKAN pembatalan model emisi.
        core/emisi.neraca() tetap dihitung dan tetap dibaca Tab 5.
        """
        from core import emisi

        h = emisi.neraca(10.0, 15.0, 0.85, 0.05)
        self.assertGreater(h["co2_dihemat_ton"], 0.0)
        with io.open(BERKAS_APLIKASI, encoding="utf8") as f:
            isi = f.read()
        self.assertIn("HASIL_CO2 = emisi.neraca(", isi)
        self.assertIn("tab_emisi_co2.render(st, HASIL_CO2)", isi)

    def test_dasbor_tidak_lagi_menerima_hasil_co2(self):
        """Kontrak dipersempit: parameter mati dihapus, bukan digantung."""
        import inspect

        param = list(inspect.signature(tab_dasbor.render).parameters)
        self.assertEqual(param, ["st", "retensi_aktif", "air_tertahan_aktif"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
