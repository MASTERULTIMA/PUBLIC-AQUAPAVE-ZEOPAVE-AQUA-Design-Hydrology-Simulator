"""
Uji antarmuka Tab 1 — Kalkulator Mix Design (S6-C).

Tab ini menampilkan dua hal yang berbeda pada satu layar:

  1. **Rancangan campuran skenario aktif** — deterministik, dihitung ulang
     setiap kali komposisi berubah;
  2. **Acuan kinerja konfigurasi acuan** — tiga angka yang selamanya milik
     campuran yang benar-benar dicetak dan diuji.

Keduanya sah berdampingan. Yang tidak sah adalah kepemilikannya kabur: begitu
pengguna menggeser substitusi ke 22%, ketiga angka acuan berdiri tepat di
bawah komposisi yang tidak pernah dicetak, dan tanpa pernyataan kepemilikan
yang jelas keduanya mudah terbaca sebagai satu hal.

Berkas ini menjaga pernyataan kepemilikan itu tetap ada — pada judul bagian,
label tiap kartu, dan keterangannya sekaligus — dan menjaga agar Tab 1 tetap
TIDAK memutuskan ketersediaan apa pun sendiri (ADR-009, ADR-010).

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import ast
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from streamlit.testing.v1 import AppTest  # noqa: E402

from data import akses  # noqa: E402
from scenario import state as skenario  # noqa: E402
from scenario.keluaran import FRASA_TIDAK_TERSEDIA  # noqa: E402
from ui.tabs import mix_design as tab_mix  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_TAB = os.path.join(AKAR, "ui", "tabs", "mix_design.py")
TENGGAT = 60

PENANDA_MILIK = "konfigurasi acuan"


def jalankan(kustom: float | None = None) -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    if kustom is not None:
        at.sidebar.button[0].click().run()
        [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(kustom).run()
    return at


def sel_perbandingan(at, baris: str, kolom: str) -> str:
    df = at.dataframe[0].value
    return df[df["Keluaran"] == baris].iloc[0][kolom]


# ── st tiruan: menggambar Tab 1 saja, terlepas dari tab lain ──

class WadahPalsu:
    def __init__(self, induk):
        self.induk = induk

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def markdown(self, teks, **k):
        self.induk.markdown(teks, **k)


class StPalsu:
    """Perekam panggilan; cukup untuk modul mix_design."""

    def __init__(self):
        self.dicatat: list[tuple] = []

    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [WadahPalsu(self) for _ in range(n)]

    def expander(self, label, **_):
        self.dicatat.append(("expander", label))
        return WadahPalsu(self)

    def divider(self):
        self.dicatat.append(("divider",))

    def markdown(self, teks, **_):
        self.dicatat.append(("markdown", teks))

    def caption(self, teks, **_):
        self.dicatat.append(("caption", teks))

    def info(self, teks, **_):
        self.dicatat.append(("info", teks))

    def error(self, teks, **_):
        self.dicatat.append(("error", teks))

    def metric(self, label, value, delta=None, **_):
        self.dicatat.append(("metric", label, value, delta))

    def dataframe(self, df, **_):
        self.dicatat.append(("dataframe", df.to_csv(index=False)))

    def plotly_chart(self, fig, **_):
        self.dicatat.append(("plotly", fig.layout.title.text))

    def number_input(self, label, *args, **kw):
        if "value" in kw:
            nilai = kw["value"]
        elif len(args) >= 3:
            nilai = args[2]
        else:
            nilai = args[0] if args else 0.0
        self.dicatat.append(("number_input", label, nilai))
        return nilai

    # ── pembantu ──
    def kartu(self) -> list[str]:
        """Kotak hasil yang digambar tab ini."""
        return [t for jenis, *sisa in self.dicatat if jenis == "markdown"
                for t in [sisa[0]] if "result-box" in t]

    def teks(self) -> str:
        return "\n".join(
            str(x) for baris in self.dicatat for x in baris[1:] if x)


def gambar(substitusi: float = 15.0, fab: float = 0.40) -> StPalsu:
    st = StPalsu()
    tab_mix.render(st, substitusi, fab)
    return st


# ═══════════ 1. kepemilikan acuan dinyatakan ═══════════

class KepemilikanAcuan(unittest.TestCase):
    """
    Ketiga kartu acuan wajib menyatakan miliknya siapa — pada judul, label,
    dan keterangan sekaligus, bukan hanya satu catatan kaki.
    """

    @classmethod
    def setUpClass(cls):
        cls.st = gambar()

    def test_judul_bagian_menyebut_konfigurasi_acuan(self):
        judul = [t for j, *s in self.st.dicatat if j == "markdown"
                 for t in [s[0]] if "Acuan Kinerja" in t]
        self.assertEqual(len(judul), 1)
        self.assertIn("Konfigurasi Acuan Penelitian", judul[0])

    def test_setiap_kartu_membawa_penanda_kepemilikan(self):
        kartu = self.st.kartu()
        self.assertEqual(len(kartu), 3, "jumlah kartu acuan berubah")
        for k in kartu:
            self.assertIn(
                PENANDA_MILIK, k,
                f"kartu tanpa penanda kepemilikan: {re.sub(r'<[^>]+>', ' ', k)[:120]}")

    def test_keterangan_kepemilikan_eksplisit(self):
        teks = self.st.teks()
        self.assertIn(tab_mix.KEPEMILIKAN_ACUAN_KINERJA, teks)
        self.assertIn("bukan milik", tab_mix.KEPEMILIKAN_ACUAN_KINERJA)
        self.assertIn("skenario yang sedang aktif",
                      tab_mix.KEPEMILIKAN_ACUAN_KINERJA)

    def test_menunjuk_ke_tempat_ketersediaan_dijawab(self):
        """Kepemilikan tanpa arah membuat pengguna buntu."""
        self.assertIn("tabel perbandingan", tab_mix.KEPEMILIKAN_ACUAN_KINERJA)

    def test_status_bukti_tetap_melekat(self):
        """Kepemilikan tidak boleh menggantikan status bukti."""
        kartu = "\n".join(self.st.kartu())
        self.assertIn(akses.status("PERMEABILITAS"), kartu)
        self.assertIn(akses.status("KUAT_TEKAN_7_HARI"), kartu)
        self.assertIn(akses.status("POROSITAS_TARGET_MAKS").upper(), kartu)

    def test_penyangkalan_prediksi_tetap_ada(self):
        """Kalimat lama tidak dibuang, hanya dilengkapi."""
        self.assertIn(tab_mix.CATATAN_ACUAN_KINERJA, self.st.teks())
        self.assertIn("bukan prediksi", tab_mix.CATATAN_ACUAN_KINERJA)


# ═══════════ 2. pemisahan pada komposisi kustom ═══════════

class PemisahanPadaKomposisiKustom(unittest.TestCase):
    """
    Inti S6-C. Angka acuan BOLEH tetap terlihat; yang dilarang adalah
    mengklaimnya sebagai hasil ukur komposisi yang sedang disusun.
    """

    @classmethod
    def setUpClass(cls):
        cls.acuan = gambar(substitusi=15.0)
        cls.kustom = gambar(substitusi=22.0)

    def test_kartu_acuan_tetap_terlihat(self):
        """Data penelitian tidak disembunyikan — ia tetap perlu diperiksa."""
        self.assertEqual(len(self.kustom.kartu()), 3)
        self.assertIn("13.19", "\n".join(self.kustom.kartu()))
        self.assertIn("1.667", "\n".join(self.kustom.kartu()))

    def test_tidak_ada_kartu_terukur_tanpa_kepemilikan(self):
        """
        Bukan larangan menyeluruh atas 13,19 atau 1,667 — keduanya sah sebagai
        informasi acuan. Yang dijaga: setiap kartu yang memuatnya harus
        menyatakan miliknya konfigurasi acuan.
        """
        for k in self.kustom.kartu():
            if "13.19" in k or "1.667" in k:
                self.assertIn(
                    PENANDA_MILIK, k,
                    "nilai terukur tampil tanpa menyatakan konfigurasi pemiliknya")

    def test_komposisi_kustom_tidak_mengubah_kartu_acuan(self):
        """Angka acuan tidak bergerak mengikuti komposisi — ia bukan prediksi."""
        self.assertEqual(self.acuan.kartu(), self.kustom.kartu())

    def test_tidak_ada_klaim_hasil_utama_skenario_aktif(self):
        """
        Tab 1 tidak menyajikan keluaran kinerja skenario aktif sama sekali,
        sehingga tidak boleh ada kalimat yang menyatakannya.
        """
        teks = self.kustom.teks()
        self.assertNotIn("HASIL UTAMA", teks)
        self.assertNotIn("skenario aktif —", teks)

    def test_parameter_aktif_dan_acuan_terpisah_jelas(self):
        """Parameter di atas milik skenario aktif; kartu di bawah milik acuan."""
        metrik = {label: nilai for j, label, nilai, _ in
                  (d for d in self.kustom.dicatat if d[0] == "metric")}
        self.assertEqual(metrik["Substitusi Lumpur IPAL"], "22%")
        self.assertNotIn(PENANDA_MILIK, "Substitusi Lumpur IPAL")
        for k in self.kustom.kartu():
            self.assertIn(PENANDA_MILIK, k)


# ═══════════ 3. tidak ada prediksi dari komposisi ═══════════

class TanpaPrediksi(unittest.TestCase):

    def test_kartu_acuan_tidak_bergerak_mengikuti_komposisi(self):
        for sub in (0.0, 15.0, 22.0, 25.0):
            self.assertEqual(
                gambar(substitusi=sub).kartu(), gambar(substitusi=15.0).kartu(),
                f"kartu acuan berubah pada substitusi {sub}% — ada prediksi")

    def test_kartu_acuan_tidak_bergerak_mengikuti_fab(self):
        for fab in (0.30, 0.40, 0.55):
            self.assertEqual(
                gambar(fab=fab).kartu(), gambar(fab=0.40).kartu(),
                f"kartu acuan berubah pada f.a.b {fab} — ada prediksi")

    def test_neraca_massa_memang_dihitung_ulang(self):
        """Yang deterministik harus tetap bergerak; hanya acuan yang diam."""
        a = [d for d in gambar(substitusi=15.0).dicatat if d[0] == "dataframe"]
        b = [d for d in gambar(substitusi=22.0).dicatat if d[0] == "dataframe"]
        self.assertNotEqual(a, b)

    def test_core_tidak_menyediakan_prediksi(self):
        from core import komposisi as kmp
        for nama in dir(kmp):
            for terlarang in ("prediksi", "predict", "taksir", "regresi"):
                self.assertNotIn(terlarang, nama.lower())


# ═══════════ 4. batas arsitektur ═══════════

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

    def test_tidak_menyelesaikan_resolusi_sendiri(self):
        impor = self._impor()
        self.assertNotIn("scenario.resolusi", impor)
        self.assertNotIn("scenario.state", impor)

    def test_tidak_menduplikasi_aturan_identitas_konfigurasi(self):
        sumber = self._sumber()
        for terlarang in ("cocok_konfigurasi_uji", "alasan_berbeda",
                          "PARAMETER_KONFIGURASI_UJI", "acuan_penelitian(",
                          "ACUAN_SUBSTITUSI_IPAL"):
            self.assertNotIn(
                terlarang, sumber,
                f"aturan identitas konfigurasi tergandakan di Tab 1: {terlarang}")

    def test_kontrak_render_tetap_minimal(self):
        """Kepemilikan dinyatakan lewat kata, bukan lewat argumen tambahan."""
        for simpul in ast.walk(ast.parse(self._sumber(), filename=BERKAS_TAB)):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                self.assertEqual(
                    [a.arg for a in simpul.args.args],
                    ["st", "substitusi_ipal_persen", "faktor_air_pengikat"])
                return
        self.fail("fungsi render() tidak ditemukan")

    def test_nilai_acuan_lewat_jalur_kanonik(self):
        """ADR-011: tidak ada literal ilmiah baru; semuanya lewat akses."""
        sumber = self._sumber()
        for nama in ("KUAT_TEKAN_7_HARI", "PERMEABILITAS",
                     "POROSITAS_TARGET_MIN", "POROSITAS_TARGET_MAKS",
                     "UMUR_UJI_HARI"):
            self.assertIn(f'akses.besaran("{nama}")', sumber)
        for literal in ("13.19", "1.667", "13,19", "1,667"):
            self.assertNotIn(literal, sumber,
                             f"nilai ilmiah ditulis sebagai literal: {literal}")


# ═══════════ 5. perilaku skenario tetap utuh ═══════════

class PerilakuSkenarioUtuh(unittest.TestCase):
    """Pengaman ADR-009 tidak boleh bergeser akibat perubahan penyajian."""

    def test_acuan_hasil_ukur_tersedia(self):
        at = jalankan()
        sel = sel_perbandingan(at, "Kuat tekan (7 hari)", "Acuan Penelitian")
        self.assertIn("13.19", sel)
        self.assertIn("terukur", sel)

    def test_kustom_22_hasil_ukur_tidak_tersedia(self):
        at = jalankan(kustom=22)
        for baris in ("Kuat tekan (7 hari)", "Koefisien permeabilitas",
                      "Retensi air"):
            self.assertEqual(
                sel_perbandingan(at, baris, "Skenario A"), FRASA_TIDAK_TERSEDIA)

    def test_dipulihkan_hasil_ukur_kembali(self):
        at = jalankan(kustom=22)
        [s for s in at.sidebar.slider if "IPAL" in s.label][0].set_value(
            int(skenario.ACUAN_SUBSTITUSI_IPAL)).run()
        self.assertTrue(skenario.cocok_konfigurasi_uji(
            at.session_state[skenario.KUNCI].ambil("A")))
        sel = sel_perbandingan(at, "Kuat tekan (7 hari)", "Skenario A")
        self.assertIn("13.19", sel)
        self.assertIn("terukur", sel)

    def test_kepemilikan_tampil_di_aplikasi_sungguhan(self):
        at = jalankan(kustom=22)
        self.assertEqual(list(at.exception), [])
        self.assertIn(tab_mix.KEPEMILIKAN_ACUAN_KINERJA,
                      [c.value for c in at.caption])
        judul = [m.value for m in at.markdown if "Acuan Kinerja" in m.value]
        self.assertEqual(len(judul), 1)
        self.assertIn("Konfigurasi Acuan Penelitian", judul[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
