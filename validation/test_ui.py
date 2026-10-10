"""
Jaring pengaman antarmuka (S5-0).

Uji di berkas lain memeriksa mesin perhitungan. Berkas ini memeriksa hal yang
tidak dijangkau uji mana pun sebelumnya: apakah pengaman ilmiahnya benar-benar
sampai ke LAYAR.

Perbedaannya bukan main-main. Sebuah bug pada S3 — nama `_sk` tertimpa di
Tab 4 sehingga Tab 5 ikut rusak — lolos dari seluruh uji core/ dan hanya
tertangkap karena aplikasinya dijalankan headless. Berkas ini menjadikan
pemeriksaan itu otomatis, sehingga ekstraksi tab pada tahap berikutnya
berlangsung di atas jaring, bukan di atas ingatan.

Yang diuji di sini adalah PERILAKU ILMIAH dan integrasi, bukan tata letak.
Tidak ada pernyataan terhadap warna, urutan elemen, atau jumlah kolom — hal
semacam itu berubah setiap kali tampilan disentuh dan akan membuat uji ini
rapuh tanpa menambah keamanan apa pun.

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

import ast
import os
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

from streamlit.testing.v1 import AppTest  # noqa: E402

from data import akses  # noqa: E402
from scenario import state as skenario  # noqa: E402
from scenario.keluaran import FRASA_TIDAK_TERSEDIA  # noqa: E402
from ui.components import scenario as komp_skenario  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")

#: Streamlit membangun ulang seluruh pohon setiap kali; 60 detik memberi
#: kelonggaran pada mesin lambat tanpa membuat uji menggantung.
TENGGAT = 60


def jalankan() -> AppTest:
    """
    Jalankan aplikasi headless dari keadaan awal.

    Direktori kerja disetel ke akar proyek karena aplikasi memuat aset relatif
    (`Asset/AQUAPAVELOGO.png`).
    """
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


# ─────────────────────────── pembantu ───────────────────────────

def koleksi(at) -> skenario.Koleksi:
    return at.session_state[skenario.KUNCI]


def penggeser(at, potongan_label: str):
    """Penggeser bilah sisi menurut potongan labelnya."""
    cocok = [s for s in at.sidebar.slider if potongan_label in s.label]
    if not cocok:
        raise AssertionError(
            f"penggeser {potongan_label!r} tidak ada di bilah sisi; "
            f"yang ada: {[s.label for s in at.sidebar.slider]}"
        )
    return cocok[0]


def tombol(at, potongan_label: str):
    cocok = [b for b in at.sidebar.button if potongan_label in b.label]
    if not cocok:
        raise AssertionError(f"tombol {potongan_label!r} tidak ada di bilah sisi")
    return cocok[0]


def tabel_perbandingan(at):
    """Tabel perbandingan adalah tabel pertama pada halaman."""
    return at.dataframe[0].value


def sel(at, baris_keluaran: str, kolom_skenario: str) -> str:
    """Isi satu sel tabel perbandingan."""
    df = tabel_perbandingan(at)
    cocok = df[df["Keluaran"] == baris_keluaran]
    if cocok.empty:
        raise AssertionError(
            f"baris {baris_keluaran!r} tidak ada; yang ada: {list(df['Keluaran'])}"
        )
    if kolom_skenario not in df.columns:
        raise AssertionError(
            f"kolom {kolom_skenario!r} tidak ada; yang ada: {list(df.columns)}"
        )
    return cocok.iloc[0][kolom_skenario]


def impor_modul(berkas: str) -> set:
    """
    Nama paket tingkat atas yang benar-benar DIIMPOR sebuah berkas.

    Dibaca dari pohon sintaks, bukan dicari sebagai teks: dokumentasi yang
    menyebut sebuah modul tidak sama dengan mengimpornya.
    """
    with open(berkas, encoding="utf8") as f:
        pohon = ast.parse(f.read(), filename=berkas)
    paket = set()
    for simpul in ast.walk(pohon):
        if isinstance(simpul, ast.Import):
            paket.update(a.name.split(".")[0] for a in simpul.names)
        elif isinstance(simpul, ast.ImportFrom) and simpul.module:
            paket.add(simpul.module.split(".")[0])
    return paket


def seluruh_teks(at) -> str:
    """Gabungan teks tampilan, untuk memeriksa integrasi nilai ke layar."""
    bagian = []
    for kelompok in (at.markdown, at.caption, at.info, at.warning,
                     at.success, at.error, at.metric):
        for e in kelompok:
            bagian.append(str(getattr(e, "value", "")))
    return "\n".join(bagian)


ACUAN = "Acuan Penelitian"
KUSTOM_A = "Skenario A"

KUAT_TEKAN = "Kuat tekan (7 hari)"
PERMEABILITAS = "Koefisien permeabilitas"
RETENSI = "Retensi air"
POROSITAS = "Porositas"
MASSA_TOTAL = "Massa total campuran"
MASSA_IPAL = "Massa lumpur IPAL"
CO2 = "Emisi CO₂ campuran"
AIR_TERTAHAN = "Air tertahan pada skala area"


# ═══════════════════════════ 1. muat aplikasi ═══════════════════════════

class MuatAplikasi(unittest.TestCase):
    """Aplikasi harus hidup sebelum apa pun yang lain berarti."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(
            list(self.at.exception), [],
            "AQUAPAVE.py menaikkan kekecualian saat dimuat: "
            + "; ".join(str(e.value) for e in self.at.exception),
        )

    def test_delapan_tab_ada(self):
        """Tab pembuka Mulai di Sini ditambah tujuh tab teknis."""
        self.assertEqual(len(self.at.tabs), 8)

    def test_acuan_penelitian_yang_aktif_di_awal(self):
        k = koleksi(self.at)
        self.assertEqual(k.aktif, skenario.ACUAN)
        self.assertEqual(k.kustom, {})
        self.assertTrue(skenario.cocok_konfigurasi_uji(k.ambil(skenario.ACUAN)))

    def test_acuan_memakai_parameter_penelitian(self):
        s = koleksi(self.at).ambil(skenario.ACUAN)
        self.assertAlmostEqual(
            s.substitusi_ipal_persen, akses.nilai("SUBSTITUSI_IPAL"), delta=1e-9)
        self.assertAlmostEqual(
            s.faktor_air_pengikat, akses.nilai("FAKTOR_AIR_PENGIKAT"), delta=1e-9)

    def test_tabel_perbandingan_digambar(self):
        df = tabel_perbandingan(self.at)
        self.assertIn("Keluaran", df.columns)
        self.assertIn(ACUAN, df.columns)


# ═══════════════════════ 2. nilai kanonik sampai ke layar ═══════════════════════

class NilaiPenelitianDiAntarmuka(unittest.TestCase):
    """
    Ketiga hasil utama harus terlihat di antarmuka DAN membawa status
    buktinya.

    Memeriksa konstanta di Python saja tidak cukup: S1 justru menemukan bahwa
    nilai yang benar di konstanta.py bisa tidak pernah sampai ke layar.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_kuat_tekan_13_19_terukur(self):
        s = sel(self.at, KUAT_TEKAN, ACUAN)
        self.assertIn("13.19", s)
        self.assertIn("MPa", s)
        self.assertIn("terukur", s)

    def test_permeabilitas_1_667_terukur(self):
        s = sel(self.at, PERMEABILITAS, ACUAN)
        self.assertIn("1.67", s)
        self.assertIn("cm/detik", s)
        self.assertIn("terukur", s)

    def test_retensi_40_0_terukur(self):
        s = sel(self.at, RETENSI, ACUAN)
        self.assertIn("40.00", s)
        self.assertIn("terukur", s)

    def test_retensi_bukan_lagi_39_7(self):
        """Pelaporan lama 39,7% tidak boleh muncul sebagai hasil."""
        self.assertNotIn("39.7", sel(self.at, RETENSI, ACUAN))

    def test_porositas_berstatus_target_bukan_terukur(self):
        """Porositas tidak pernah diukur; ia target rancangan."""
        s = sel(self.at, POROSITAS, ACUAN)
        self.assertIn("target", s)
        self.assertNotIn("terukur", s)

    def test_kartu_angka_kunci_membawa_status(self):
        teks = seluruh_teks(self.at)
        for a in akses.angka_kunci():
            self.assertIn(a["status"].upper(), teks)

    def test_provenansi_setiap_angka_kunci_tersedia(self):
        teks = seluruh_teks(self.at)
        for a in akses.angka_kunci():
            self.assertIn(a["label"], teks)
            self.assertIn(a["provenans"], teks)

    def test_estimasi_15_mpa_bukan_hasil_utama(self):
        """15,00 MPa berstatus asumsi dan tidak boleh jadi kuat tekan acuan."""
        self.assertNotIn("15.00 MPa", sel(self.at, KUAT_TEKAN, ACUAN))


# ═══════════════ 3. pengaman ilmiah pada skenario kustom ═══════════════

class PengamanSkenarioKustom(unittest.TestCase):
    """
    Jalur regresi paling penting di seluruh berkas ini.

    Acuan → tambah Skenario A → geser satu parameter komposisi → hasil ukur
    HARUS lenyap dari kolom A, sementara besaran deterministik tetap dihitung
    ulang. Bila jalur ini rusak, aplikasi menampilkan hasil laboratorium untuk
    komposisi yang tidak pernah dicetak.
    """

    @classmethod
    def setUpClass(cls):
        at = jalankan()
        tombol(at, "Tambah skenario").click().run()
        penggeser(at, "Substitusi Lumpur IPAL").set_value(22).run()
        cls.at = at

    def test_menjadi_skenario_kustom(self):
        k = koleksi(self.at)
        self.assertIn("A", k.kustom)
        self.assertEqual(k.aktif, "A")
        self.assertAlmostEqual(k.ambil("A").substitusi_ipal_persen, 22.0, delta=1e-9)
        self.assertFalse(skenario.cocok_konfigurasi_uji(k.ambil("A")))

    def test_kolom_skenario_a_muncul(self):
        self.assertIn(KUSTOM_A, tabel_perbandingan(self.at).columns)

    def test_alasan_berbeda_dijelaskan_di_layar(self):
        """Pengguna harus tahu MENGAPA skenarionya dianggap kustom."""
        peringatan = "\n".join(w.value for w in self.at.sidebar.warning)
        self.assertIn("Substitusi lumpur IPAL", peringatan)
        self.assertIn("22", peringatan)

    # ── yang TERSEDIA: deterministik, dihitung ulang ──

    def test_massa_total_tersedia_dan_deterministik(self):
        s = sel(self.at, MASSA_TOTAL, KUSTOM_A)
        self.assertNotIn(FRASA_TIDAK_TERSEDIA, s)
        self.assertIn("deterministik", s)

    def test_massa_ipal_dihitung_ulang(self):
        s = sel(self.at, MASSA_IPAL, KUSTOM_A)
        self.assertNotIn(FRASA_TIDAK_TERSEDIA, s)
        self.assertIn("deterministik", s)
        self.assertNotEqual(s, sel(self.at, MASSA_IPAL, ACUAN))

    def test_neraca_co2_dihitung_ulang(self):
        s = sel(self.at, CO2, KUSTOM_A)
        self.assertNotIn(FRASA_TIDAK_TERSEDIA, s)
        self.assertIn("deterministik", s)
        self.assertNotEqual(s, sel(self.at, CO2, ACUAN))

    # ── yang TIDAK TERSEDIA: hasil ukur ──

    def test_kuat_tekan_terukur_tidak_tersedia(self):
        self.assertEqual(sel(self.at, KUAT_TEKAN, KUSTOM_A), FRASA_TIDAK_TERSEDIA)

    def test_permeabilitas_terukur_tidak_tersedia(self):
        self.assertEqual(sel(self.at, PERMEABILITAS, KUSTOM_A), FRASA_TIDAK_TERSEDIA)

    def test_retensi_terukur_tidak_tersedia(self):
        self.assertEqual(sel(self.at, RETENSI, KUSTOM_A), FRASA_TIDAK_TERSEDIA)

    def test_porositas_tidak_tersedia(self):
        self.assertEqual(sel(self.at, POROSITAS, KUSTOM_A), FRASA_TIDAK_TERSEDIA)

    def test_ketidaktersediaan_merambat_ke_air_tertahan(self):
        """Air tertahan diturunkan dari retensi; ketidaktahuan ikut merambat."""
        self.assertEqual(sel(self.at, AIR_TERTAHAN, KUSTOM_A), FRASA_TIDAK_TERSEDIA)

    # ── bentuk ketidaktersediaannya ──

    def test_tidak_ada_nol_menggantikan_hasil_ukur(self):
        """Sel kosong tidak boleh berubah menjadi nol, tanda hubung, atau kosong."""
        for baris in (KUAT_TEKAN, PERMEABILITAS, RETENSI, POROSITAS, AIR_TERTAHAN):
            s = sel(self.at, baris, KUSTOM_A)
            self.assertNotIn("0.00", s, f"{baris}: nol menggantikan ketiadaan hasil")
            self.assertNotEqual(s.strip(), "")
            self.assertNotIn("-", s.replace(FRASA_TIDAK_TERSEDIA, ""))

    def test_tidak_ada_status_bukti_pada_yang_tidak_tersedia(self):
        """'Belum tersedia' bukan kategori bukti sejajar 'terukur' (ADR-009)."""
        for baris in (KUAT_TEKAN, PERMEABILITAS, RETENSI, POROSITAS, AIR_TERTAHAN):
            s = sel(self.at, baris, KUSTOM_A)
            for status in ("terukur", "deterministik", "literatur", "target", "asumsi"):
                self.assertNotIn(status, s, f"{baris}: membawa status bukti {status}")

    def test_nilai_terukur_tidak_bocor_ke_kolom_kustom(self):
        """Angka hasil laboratorium tidak boleh muncul di kolom yang belum diuji."""
        df = tabel_perbandingan(self.at)
        kolom_a = "\n".join(str(v) for v in df[KUSTOM_A])
        for angka in ("13.19", "1.67", "40.00"):
            self.assertNotIn(angka, kolom_a)

    def test_acuan_tidak_ikut_berubah(self):
        """Menyunting skenario kustom tidak boleh menyentuh acuan penelitian."""
        self.assertIn("13.19", sel(self.at, KUAT_TEKAN, ACUAN))
        self.assertIn("terukur", sel(self.at, RETENSI, ACUAN))


# ═════════════════════ 4. daur hidup skenario ═════════════════════

class DaurHidupSkenario(unittest.TestCase):
    """Tambah, berpindah, hapus — dengan acuan yang selalu bertahan."""

    def setUp(self):
        self.at = jalankan()

    def test_tambah_skenario(self):
        tombol(self.at, "Tambah skenario").click().run()
        k = koleksi(self.at)
        self.assertEqual(list(k.kustom), ["A"])
        self.assertEqual(k.aktif, "A")
        self.assertIn(KUSTOM_A, tabel_perbandingan(self.at).columns)

    def test_tambah_beberapa_lalu_penuh(self):
        for diharapkan in ("A", "B", "C"):
            tombol(self.at, "Tambah skenario").click().run()
            self.assertIn(diharapkan, koleksi(self.at).kustom)
        self.assertTrue(koleksi(self.at).penuh())
        self.assertTrue(tombol(self.at, "Tambah skenario").disabled)

    def test_berpindah_skenario_aktif(self):
        tombol(self.at, "Tambah skenario").click().run()
        penggeser(self.at, "Substitusi Lumpur IPAL").set_value(20).run()

        self.at.sidebar.radio[0].set_value(skenario.ACUAN).run()
        self.assertEqual(koleksi(self.at).aktif, skenario.ACUAN)
        self.assertEqual(
            penggeser(self.at, "Substitusi Lumpur IPAL").value, 15,
            "berpindah ke acuan harus memuat ulang kendali dari nilai acuan",
        )

        self.at.sidebar.radio[0].set_value("A").run()
        self.assertEqual(koleksi(self.at).aktif, "A")
        self.assertEqual(
            penggeser(self.at, "Substitusi Lumpur IPAL").value, 20,
            "kembali ke skenario kustom harus memulihkan nilainya sendiri",
        )

    def test_hapus_skenario_kustom(self):
        tombol(self.at, "Tambah skenario").click().run()
        tombol(self.at, "Hapus skenario").click().run()
        k = koleksi(self.at)
        self.assertEqual(k.kustom, {})
        self.assertEqual(k.aktif, skenario.ACUAN)
        self.assertNotIn(KUSTOM_A, tabel_perbandingan(self.at).columns)

    def test_skenario_baru_tidak_mewarisi_kendali_yang_dihapus(self):
        """
        Menghapus A lalu menambah A lagi harus dimulai dari acuan, bukan dari
        nilai kendali milik A yang lama.
        """
        tombol(self.at, "Tambah skenario").click().run()
        penggeser(self.at, "Substitusi Lumpur IPAL").set_value(24).run()
        tombol(self.at, "Hapus skenario").click().run()
        tombol(self.at, "Tambah skenario").click().run()
        self.assertAlmostEqual(
            koleksi(self.at).ambil("A").substitusi_ipal_persen,
            skenario.ACUAN_SUBSTITUSI_IPAL, delta=1e-9,
        )

    def test_acuan_selalu_ada_dan_tidak_dapat_dihapus(self):
        self.assertIn(skenario.ACUAN, koleksi(self.at).nama_terpakai())
        self.assertTrue(
            tombol(self.at, "Hapus skenario").disabled,
            "tombol hapus harus mati saat acuan penelitian yang aktif",
        )
        self.assertIn(ACUAN, tabel_perbandingan(self.at).columns)

    def test_kendali_acuan_terkunci(self):
        """Acuan tidak dapat disunting; parameternya tetap nilai penelitian."""
        for label in ("Substitusi Lumpur IPAL", "Faktor Air-Pengikat",
                      "Intensitas Hujan"):
            self.assertTrue(
                penggeser(self.at, label).disabled,
                f"kendali {label!r} harus mati saat acuan aktif",
            )
        self.assertTrue(skenario.cocok_konfigurasi_uji(
            koleksi(self.at).ambil(skenario.ACUAN)))


# ═══════════════════ 5. identitas konfigurasi ═══════════════════

class IdentitasKonfigurasi(unittest.TestCase):
    """
    Memulihkan skenario kustom ke konfigurasi penelitian yang PERSIS harus
    memulihkan pula ketersediaan hasil ukurnya.

    Identitas ditentukan perbandingan parameter demi parameter (ADR-009), jadi
    hasil ukur kembali berlaku begitu komposisinya sama — bukan karena
    skenarionya bernama acuan, melainkan karena komposisinya memang komposisi
    yang diuji.
    """

    @classmethod
    def setUpClass(cls):
        at = jalankan()
        tombol(at, "Tambah skenario").click().run()
        penggeser(at, "Substitusi Lumpur IPAL").set_value(22).run()
        cls.saat_berbeda = sel(at, KUAT_TEKAN, KUSTOM_A)
        penggeser(at, "Substitusi Lumpur IPAL").set_value(
            int(skenario.ACUAN_SUBSTITUSI_IPAL)).run()
        cls.at = at

    def test_sempat_tidak_tersedia(self):
        self.assertEqual(self.saat_berbeda, FRASA_TIDAK_TERSEDIA)

    def test_kendali_tidak_kehilangan_masukan(self):
        """
        Regresi: identitas widget dahulu ikut bergeser bersama nilainya,
        sehingga masukan tepat setelah sebuah perubahan hilang diam-diam.
        """
        self.assertAlmostEqual(
            koleksi(self.at).ambil("A").substitusi_ipal_persen,
            skenario.ACUAN_SUBSTITUSI_IPAL, delta=1e-9,
        )

    def test_identitas_pulih(self):
        self.assertTrue(skenario.cocok_konfigurasi_uji(koleksi(self.at).ambil("A")))
        self.assertEqual(skenario.alasan_berbeda(koleksi(self.at).ambil("A")), [])

    def test_hasil_ukur_kembali_tersedia(self):
        self.assertIn("13.19", sel(self.at, KUAT_TEKAN, KUSTOM_A))
        self.assertIn("1.67", sel(self.at, PERMEABILITAS, KUSTOM_A))
        self.assertIn("40.00", sel(self.at, RETENSI, KUSTOM_A))

    def test_status_bukti_pulih_sebagai_terukur(self):
        for baris in (KUAT_TEKAN, PERMEABILITAS, RETENSI):
            self.assertIn("terukur", sel(self.at, baris, KUSTOM_A))

    def test_sama_persis_dengan_kolom_acuan(self):
        """Komposisi yang sama harus menghasilkan keluaran yang sama."""
        for baris in (KUAT_TEKAN, PERMEABILITAS, RETENSI, POROSITAS,
                      MASSA_TOTAL, MASSA_IPAL, CO2, AIR_TERTAHAN):
            self.assertEqual(
                sel(self.at, baris, KUSTOM_A), sel(self.at, baris, ACUAN),
                f"{baris}: kolom kustom berbeda padahal komposisinya identik",
            )

    def test_disebut_identik_dengan_acuan(self):
        pemberitahuan = "\n".join(m.value for m in self.at.sidebar.info)
        self.assertIn("identik dengan acuan", pemberitahuan)


# ═══════════════════ arah ketergantungan ═══════════════════

class ArahKetergantungan(unittest.TestCase):
    """
    core/, data/, dan scenario/ tidak boleh bergantung pada Streamlit maupun
    pada lapisan antarmuka. Diperiksa otomatis agar tidak tergantung pada
    kedisiplinan siapa pun.
    """

    LAPISAN_MURNI = ("core", "data", "scenario")

    def _berkas(self, paket):
        d = os.path.join(AKAR, paket)
        return [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".py")]

    def test_lapisan_murni_tidak_mengimpor_streamlit(self):
        for paket in self.LAPISAN_MURNI:
            for berkas in self._berkas(paket):
                self.assertNotIn(
                    "streamlit", impor_modul(berkas),
                    f"{berkas} mengimpor Streamlit; lapisan ini harus murni",
                )

    def test_lapisan_murni_tidak_mengimpor_ui(self):
        for paket in self.LAPISAN_MURNI:
            for berkas in self._berkas(paket):
                self.assertNotIn(
                    "ui", impor_modul(berkas),
                    f"{berkas} bergantung pada lapisan tampilan",
                )

    def test_core_tidak_mengimpor_scenario(self):
        """core/ adalah lapisan terdalam; ia tidak mengenal skenario."""
        for berkas in self._berkas("core"):
            self.assertNotIn("scenario", impor_modul(berkas))

    def test_ui_menerima_st_sebagai_argumen(self):
        """
        Tidak ada modul ui/ yang mengimpor Streamlit: `st` selalu dilewatkan.
        Konvensi ini yang membuat komponen dapat diuji tanpa Streamlit.
        """
        for akar, _, berkas in os.walk(os.path.join(AKAR, "ui")):
            if "__pycache__" in akar:
                continue
            for f in berkas:
                if f.endswith(".py"):
                    p = os.path.join(akar, f)
                    self.assertNotIn(
                        "streamlit", impor_modul(p),
                        f"{p} mengimpor Streamlit; lewatkan `st` sebagai argumen",
                    )

    def test_konstanta_dihapus_tetap_terkunci(self):
        """Nilai yang dihapus ADR-001 tidak boleh diakses lewat pintu mana pun."""
        for nama in akses.daftar_dihapus():
            with self.assertRaises(akses.NilaiDihapus):
                akses.besaran(nama)


# ═══════════════════ komponen bersama ═══════════════════

class KomponenBersama(unittest.TestCase):
    """
    Komponen ui/ diuji tanpa menjalankan Streamlit, memanfaatkan konvensi
    `st` sebagai argumen.
    """

    class StPalsu:
        def __init__(self):
            self.session_state = {}
            self.dicatat = []

        def warning(self, teks): self.dicatat.append(("warning", teks))
        def caption(self, teks): self.dicatat.append(("caption", teks))
        def markdown(self, teks, **_): self.dicatat.append(("markdown", teks))

    def test_kunci_kendali_diikat_ke_nama_skenario(self):
        a = komp_skenario.kunci("A", "substitusi_ipal_persen")
        b = komp_skenario.kunci("B", "substitusi_ipal_persen")
        self.assertNotEqual(a, b)
        self.assertIn("A", a)

    def test_bersihkan_kendali_hanya_menyentuh_skenario_itu(self):
        st = self.StPalsu()
        st.session_state[komp_skenario.kunci("A", "x")] = 1
        st.session_state[komp_skenario.kunci("B", "x")] = 2
        st.session_state["lain"] = 3
        komp_skenario.bersihkan_kendali(st, "A")
        self.assertNotIn(komp_skenario.kunci("A", "x"), st.session_state)
        self.assertIn(komp_skenario.kunci("B", "x"), st.session_state)
        self.assertIn("lain", st.session_state)

    def test_tidak_tersedia_menolak_keluaran_yang_tersedia(self):
        """Pengaman: komponen ini tidak boleh dipakai pada hasil yang ada."""
        from scenario.keluaran import OutputID, StatusBukti, tersedia
        from ui.components import warnings as komp_catatan

        k = tersedia(OutputID.RETENTION, 40.0, "%", StatusBukti.TERUKUR)
        with self.assertRaises(ValueError):
            komp_catatan.tidak_tersedia(self.StPalsu(), k)

    def test_tidak_tersedia_memakai_frasa_baku(self):
        from scenario.keluaran import OutputID
        from scenario.keluaran import tidak_tersedia as buat
        from ui.components import warnings as komp_catatan

        st = self.StPalsu()
        komp_catatan.tidak_tersedia(st, buat(OutputID.RETENTION, "%"))
        self.assertIn(FRASA_TIDAK_TERSEDIA, st.dicatat[0][1])

    def test_teks_bukti_tidak_memberi_status_pada_yang_kosong(self):
        from scenario.keluaran import OutputID
        from scenario.keluaran import tidak_tersedia as buat
        from ui.components import evidence as komp_bukti

        self.assertEqual(
            komp_bukti.teks_bukti(buat(OutputID.PERMEABILITY, "cm/detik")),
            FRASA_TIDAK_TERSEDIA,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
