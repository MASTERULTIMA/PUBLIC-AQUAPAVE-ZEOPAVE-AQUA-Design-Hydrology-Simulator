"""
Uji antarmuka Tab 7 — Efisiensi Biaya (S5-6).

Tab ini berbeda dari tab lain: seluruh keluarannya **bukan temuan
penelitian**. Naskah DevICE tidak memuat bab biaya, sehingga tidak satu pun
angkanya bersumber di dalam penelitian.

Karena itu yang paling dijaga di sini bukan ketepatan angkanya, melainkan
bahwa klasifikasinya tidak pernah hilang: peringatan indikatif tetap tampil,
panel audit masukan tetap menyebut setiap asumsinya, dan tidak ada satu pun
keluaran yang naik status menjadi temuan.

Uji ini juga menjaga agar ekstraksi tidak diam-diam memperbaiki mesin biaya.
Nilai bawaannya dipatok apa adanya; bila suatu saat harga atau UNIT_PER_M2
diubah, uji ini gagal dan perubahannya harus disengaja.

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

from data import akses  # noqa: E402
from ui.tabs import biaya as tab_biaya  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_TAB = os.path.join(AKAR, "ui", "tabs", "biaya.py")
TENGGAT = 60

#: Nilai dasar yang dihasilkan MATERIAL_DEFAULT apa adanya.
#:
#: S7-E: "total per unit" tidak lagi bermakna sebagai satu angka — kedua
#: lapisan berbasis berbeda. Yang dipakai sekarang adalah subtotal per lapisan.
RETENSI_PER_M2_BAWAAN = 130_000.0        # 6 kg hebel + 1 kg zeolit, per 1 m²


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def widget(at, jenis: str, label: str):
    kel = getattr(at, jenis)
    cocok = [x for x in kel if getattr(x, "label", None) == label]
    if not cocok:
        raise AssertionError(f"{jenis} {label!r} tidak ada")
    return cocok[0]


def kartu_total(at) -> str:
    cocok = [m.value for m in at.markdown if "SISTEM LENGKAP" in m.value]
    if not cocok:
        raise AssertionError("kartu biaya lapisan tidak digambar")
    return cocok[0]


def _kartu_angka(at) -> list:
    return [float(x.replace(",", ""))
            for x in re.findall(r"Rp ([\d,.]+)<", kartu_total(at))]


def beton_per_m2(at) -> float:
    return _kartu_angka(at)[0]


def retensi_per_m2(at) -> float:
    return _kartu_angka(at)[1]


def sistem_per_m2(at) -> float:
    return _kartu_angka(at)[2]


def tabel_proyek(at):
    for d in at.dataframe:
        if "Komponen Biaya" in d.value.columns:
            return d.value
    raise AssertionError("tabel biaya proyek tidak digambar")


def total_proyek(at) -> float:
    df = tabel_proyek(at)
    baris = df[df["Komponen Biaya"].str.startswith("TOTAL")]
    teks = baris.iloc[0]["Jumlah (Rp)"]
    return float(teks.replace("Rp ", "").replace(",", ""))


def tabel_audit(at):
    for d in at.dataframe:
        if "Masukan" in d.value.columns:
            return d.value
    raise AssertionError("tabel audit masukan tidak digambar")


def seluruh_teks(at) -> str:
    bagian = []
    for kel in (at.markdown, at.caption, at.info, at.warning, at.success, at.error):
        bagian.extend(str(getattr(e, "value", "")) for e in kel)
    return "\n".join(bagian)


# ── st tiruan, untuk menggambar tab tanpa Streamlit ──

class WadahPalsu:
    """Kolom atau expander; dipakai sebagai konteks maupun langsung."""

    def __init__(self, induk):
        self.induk = induk

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def markdown(self, teks, **k):
        self.induk.markdown(teks, **k)


class StPalsu:
    """Perekam panggilan; cukup untuk modul biaya."""

    def __init__(self):
        self.dicatat: list[tuple] = []

    # tata letak
    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [WadahPalsu(self) for _ in range(n)]

    def expander(self, label, **_):
        self.dicatat.append(("expander", label))
        return WadahPalsu(self)

    def divider(self):
        self.dicatat.append(("divider",))

    # keluaran
    def markdown(self, teks, **_):
        self.dicatat.append(("markdown", teks))

    def caption(self, teks, **_):
        self.dicatat.append(("caption", teks))

    def error(self, teks, **_):
        self.dicatat.append(("error", teks))

    def warning(self, teks, **_):
        self.dicatat.append(("warning", teks))

    def metric(self, label, value, delta=None, **_):
        self.dicatat.append(("metric", label, value, delta))

    def dataframe(self, df, **_):
        self.dicatat.append(("dataframe", df.to_csv(index=False)))

    def plotly_chart(self, fig, **_):
        self.dicatat.append(("plotly", fig.layout.title.text))

    # masukan — mengembalikan nilai bawaannya
    def _bawaan(self, args, kw, kunci):
        if kunci in kw:
            return kw[kunci]
        if len(args) >= 3:
            return args[2]
        return args[0] if args else None

    def text_input(self, label, *args, **kw):
        nilai = self._bawaan(args, kw, "value")
        self.dicatat.append(("text_input", label, nilai))
        return nilai

    def number_input(self, label, *args, **kw):
        nilai = self._bawaan(args, kw, "value")
        self.dicatat.append(("number_input", label, nilai))
        return nilai

    def slider(self, label, *args, **kw):
        nilai = self._bawaan(args, kw, "value")
        self.dicatat.append(("slider", label, nilai))
        return nilai


# ═══════════ 1. aplikasi dan tab hidup ═══════════

class TabHidup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_aplikasi_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_sembilan_tab_masih_ada(self):
        """Tab pembuka Mulai di Sini ditambah delapan tab teknis."""
        self.assertEqual(len(self.at.tabs), 9)

    def test_tab_digambar(self):
        self.assertIn("Estimasi Biaya Pembuatan ZEOPAVE-AQUA", seluruh_teks(self.at))
        self.assertIsNotNone(kartu_total(self.at))
        self.assertIsNotNone(tabel_proyek(self.at))


# ═══════════ 2. klasifikasi indikatif tetap terlihat ═══════════

class KlasifikasiIndikatif(unittest.TestCase):
    """Yang paling penting di tab ini: statusnya tidak boleh hilang."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_peringatan_indikatif_tampil(self):
        self.assertIn(tab_biaya.PERINGATAN_INDIKATIF,
                      [e.value for e in self.at.error])

    def test_dinyatakan_bukan_temuan_penelitian(self):
        teks = tab_biaya.PERINGATAN_INDIKATIF
        self.assertIn("bukan temuan penelitian", teks)
        self.assertIn("tidak satu pun angka di tab ini", teks)
        self.assertIn("tidak boleh disajikan", teks)

    def test_tidak_diklaim_terukur_atau_tervalidasi(self):
        self.assertNotIn("tervalidasi secara eksperimental.\n\nHasil",
                         tab_biaya.PERINGATAN_INDIKATIF)
        for e in self.at.error:
            self.assertNotIn("terukur", e.value.lower())

    def test_panel_audit_menyebut_setiap_asumsi(self):
        audit = tabel_audit(self.at)
        self.assertEqual(len(audit), len(tab_biaya.AUDIT_MASUKAN))
        status = set(audit["Status"])
        self.assertTrue(any(s.startswith("ASUMSI") for s in status))
        # Keputusan penulis boleh muncul; klaim bersumber tidak boleh.
        for s in status:
            self.assertNotIn("terukur", s.lower())
            self.assertNotIn("literatur", s.lower())

    def test_kerapatan_ditandai_asumsi_operasional_sementara(self):
        audit = tabel_audit(self.at)
        baris = audit[audit["Masukan"].str.contains("Berat satuan beton poros")]
        self.assertEqual(len(baris), 1)
        self.assertEqual(baris.iloc[0]["Status"], "ASUMSI OPERASIONAL SEMENTARA")
        self.assertIn("SD-16C", baris.iloc[0]["Catatan"])

    def test_tidak_ada_masukan_bersumber(self):
        audit = tabel_audit(self.at)
        for s in audit["Status"]:
            self.assertNotIn("literatur", s.lower())
            self.assertNotIn("terukur", s.lower())
        self.assertIn("Tidak ada masukan yang berstatus nilai pasar bersumber",
                      seluruh_teks(self.at))

    def test_provenans_harga_dinyatakan_di_panel(self):
        """
        PRICE-01 menutup penantian pembangunan ulang: harga tidak lagi
        menunggu tabel bertanggal, melainkan dinyatakan asalnya.
        """
        teks = seluruh_teks(self.at)
        self.assertIn(tab_biaya.SUMBER_HARGA, teks)
        self.assertNotIn("dibangun ulang di atas tabel harga", teks)


# ═══════════ 3. mesin biaya tidak berubah ═══════════

class MesinBiayaTidakBerubah(unittest.TestCase):
    """
    Nilai bawaan dipatok. Bila harga, volume, atau UNIT_PER_M2 bergeser, uji
    ini gagal — perubahan pada mesin biaya harus disengaja, bukan efek samping.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_unit_per_m2_tetap(self):
        self.assertAlmostEqual(tab_biaya.UNIT_PER_M2, 14.75, delta=1e-9)

    def test_harga_bawaan_tetap(self):
        """C-03 mengubah kuantitas, BUKAN harga. Keenam harga tidak bergeser."""
        diharapkan = [
            ("Air", 4_000), ("Semen", 1_500), ("Kerikil", 2_000),
            ("Limbah Lumpur IPAL", 0), ("Hebel", 20_000), ("Zeolit", 10_000),
        ]
        bahan = tab_biaya.material_bawaan()
        self.assertEqual(len(bahan), len(diharapkan))
        for m, (nama, harga) in zip(bahan, diharapkan):
            self.assertEqual(m["nama"], nama)
            self.assertAlmostEqual(m["harga"], harga, delta=1e-9)

    def test_kuantitas_retensi_tetap_keputusan_penulis(self):
        """Hebel 6 kg dan zeolit 1 kg per m² tidak diturunkan dari campuran."""
        bahan = {m["nama"]: m["vol"] for m in tab_biaya.material_bawaan()}
        self.assertAlmostEqual(bahan["Hebel"], 6.0, delta=1e-9)
        self.assertAlmostEqual(bahan["Zeolit"], 1.0, delta=1e-9)

    def test_subtotal_lapisan_bawaan(self):
        """
        Kedua lapisan per m². Beton diturunkan campuran kanonik §3.3; retensi
        dipakai apa adanya. Nilainya dihitung, tidak dibekukan sebagai literal.
        """
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        r = tab_biaya.rancangan_beton()
        harga = {b["nama"]: b["harga"] for b in tab_biaya.BAHAN_BETON}
        harapan = sum(r[b["kunci"]] * harga[b["nama"]]
                      for b in tab_biaya.BAHAN_BETON)
        self.assertAlmostEqual(h["retensi_per_m2"], RETENSI_PER_M2_BAWAAN, delta=0.01)
        self.assertAlmostEqual(h["beton_per_m2"], harapan, delta=0.01)
        self.assertAlmostEqual(retensi_per_m2(self.at), RETENSI_PER_M2_BAWAAN,
                               delta=0.01)
        self.assertAlmostEqual(beton_per_m2(self.at), h["beton_per_m2"], delta=0.01)

    def test_biaya_sistem_per_m2_adalah_jumlah_kedua_lapisan(self):
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        self.assertAlmostEqual(
            h["sistem_per_m2"], h["beton_per_m2"] + h["retensi_per_m2"], delta=1e-9)
        self.assertAlmostEqual(sistem_per_m2(self.at), h["sistem_per_m2"], delta=0.01)

    def test_proyek_memakai_sistem_lengkap(self):
        """1.000 m², overhead 20%, PPN 11% — kini sistem lengkap."""
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        diharapkan = h["sistem_per_m2"] * 1000.0 * 1.20 * 1.11
        self.assertAlmostEqual(total_proyek(self.at), diharapkan, delta=1.0)

    def test_representasi_ipal_kini_kanonik(self):
        """
        C-03: penyatuan yang dahulu dijaga agar tidak terjadi diam-diam kini
        dilakukan SECARA SADAR atas keputusan penulis. Kuantitas lumpur IPAL
        Tab 7 dibaca dari campuran kanonik, bukan literal 0,4 kg.
        """
        ipal = [m for m in tab_biaya.material_bawaan() if "IPAL" in m["nama"]][0]
        self.assertNotAlmostEqual(ipal["vol"], 0.4, delta=1e-6)
        self.assertAlmostEqual(
            ipal["vol"], tab_biaya.rancangan_beton()["massa_ipal_kg"], delta=1e-9)


# ═══════════ 4. luas proyek tetap menggerakkan keluaran yang sama ═══════════

class LuasProyek(unittest.TestCase):

    def test_luas_bawaan_mengikuti_bilah_sisi(self):
        at = jalankan()
        self.assertAlmostEqual(
            widget(at, "number_input", "Luas Area Proyek (m²)").value,
            1000.0, delta=1e-9)

    def test_mengubah_luas_menskalakan_biaya_proyek(self):
        at = jalankan()
        awal = total_proyek(at)
        widget(at, "number_input", "Luas Area Proyek (m²)").set_value(2500.0).run()
        self.assertAlmostEqual(total_proyek(at), awal * 2.5, delta=1.0)

    def test_luas_tidak_mengubah_biaya_per_m2(self):
        at = jalankan()
        widget(at, "number_input", "Luas Area Proyek (m²)").set_value(2500.0).run()
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        self.assertAlmostEqual(retensi_per_m2(at), RETENSI_PER_M2_BAWAAN, delta=0.01)
        self.assertAlmostEqual(beton_per_m2(at), h["beton_per_m2"], delta=0.01)

    def test_tonase_ipal_diturunkan_dari_geometri_bukan_1475(self):
        """
        Kuantitas IPAL = resep IPAL × faktor resep. Nilai lama 5,9 t/1.000 m²
        berasal dari pengali 14,75 dan tidak boleh kembali.
        """
        at = jalankan()
        widget(at, "number_input", "Luas Area Proyek (m²)").set_value(1000.0).run()
        diharapkan = tab_biaya.rancangan_beton()["massa_ipal_kg"] * 1000.0
        m = widget(at, "metric", "Lumpur IPAL terpakai")
        terbaca = float(m.value.replace(" kg", "").replace(",", ""))
        self.assertAlmostEqual(terbaca, diharapkan, delta=1.0)
        # Nilai era-lama yang tidak boleh kembali: 5.900 kg (pengali 14,75)
        # dan 3.520 kg (formulasi 40% yang sudah digantikan C-03).
        self.assertNotAlmostEqual(terbaca, 5_900.0, delta=100.0)
        self.assertNotAlmostEqual(terbaca, 3_520.0, delta=100.0)

    def test_luas_area_bilah_sisi_menjadi_nilai_awal(self):
        at = jalankan()
        at.sidebar.button[0].click().run()
        [n for n in at.sidebar.number_input
         if "Luas Area Perkerasan" in n.label][0].set_value(3000.0).run()
        self.assertAlmostEqual(
            widget(at, "number_input", "Luas Area Proyek (m²)").value,
            3000.0, delta=1e-9)


# ═══════════ 5. modul berdiri sendiri ═══════════

class ModulBerdiriSendiri(unittest.TestCase):
    """Digambar tanpa Streamlit, tanpa tab lain, tanpa urutan tertentu."""

    def test_dapat_digambar_tanpa_streamlit(self):
        st = StPalsu()
        tab_biaya.render(st, 1000.0)
        self.assertTrue(st.dicatat)
        self.assertIn(("error", tab_biaya.PERINGATAN_INDIKATIF), st.dicatat)

    def test_hasil_sama_tanpa_bergantung_urutan(self):
        """Menggambar dua kali berturut-turut memberi rekaman identik."""
        a, b = StPalsu(), StPalsu()
        tab_biaya.render(a, 1000.0)
        tab_biaya.render(b, 1000.0)
        self.assertEqual(a.dicatat, b.dicatat)

    def test_luas_berbeda_menghasilkan_rekaman_berbeda(self):
        a, b = StPalsu(), StPalsu()
        tab_biaya.render(a, 1000.0)
        tab_biaya.render(b, 2000.0)
        self.assertNotEqual(a.dicatat, b.dicatat)

    def test_tidak_memutasi_konstanta_modul(self):
        salinan = [dict(m) for m in tab_biaya.material_bawaan()]
        tab_biaya.render(StPalsu(), 1000.0)
        self.assertEqual(tab_biaya.material_bawaan(), salinan)

    def test_subtotal_lapisan_dari_st_tiruan_sesuai(self):
        st = StPalsu()
        tab_biaya.render(st, 1000.0)
        kartu = [t for jenis, t in
                 ((d[0], d[1]) for d in st.dicatat if d[0] == "markdown")
                 if "SISTEM LENGKAP" in t][0]
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        self.assertIn(f"Rp {RETENSI_PER_M2_BAWAAN:,.2f}", kartu)
        self.assertIn(f"Rp {h['sistem_per_m2']:,.2f}", kartu)


# ═══════════ 6. batas arsitektur ═══════════

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
        self.assertNotIn("streamlit",
                         {j.split(".")[0] for j in self._impor(BERKAS_TAB)})

    def test_tidak_mengimpor_tab_lain(self):
        sumber = self._sumber(BERKAS_TAB)
        for lain in ("permeabilitas", "kuat_tekan", "retensi_air",
                     "emisi_co2", "dasbor"):
            self.assertNotIn(f"import {lain}", sumber)

    def test_membaca_campuran_dari_core_bukan_menyalinnya(self):
        """
        DIBALIK PADA C-03. Uji ini dahulu melarang Tab 7 menyentuh core/,
        data/, dan scenario/, dengan alasan "seluruh angkanya asumsi dan
        masukan pengguna". Alasan itu tidak berlaku lagi: identitas campuran
        Tab 7 kini kanonik §3.3, sehingga ia WAJIB membacanya dari sumber
        ilmiah alih-alih menduplikasinya (ADR-011).

        Yang tetap dilarang: `scenario/` — Tab 7 tidak membaca skenario aktif
        dan tidak bergantung urutan tab (ADR-008).
        """
        impor = {j.split(".")[0] for j in self._impor(BERKAS_TAB)}
        self.assertIn("core", impor)
        self.assertNotIn("scenario", impor)

    def test_kontrak_render(self):
        for simpul in ast.walk(ast.parse(self._sumber(BERKAS_TAB),
                                         filename=BERKAS_TAB)):
            if isinstance(simpul, ast.FunctionDef) and simpul.name == "render":
                self.assertEqual([a.arg for a in simpul.args.args],
                                 ["st", "area_m2"])
                return
        self.fail("fungsi render() tidak ditemukan")

    def test_aquapave_hanya_mengorkestrasi(self):
        isi = self._sumber(BERKAS_APLIKASI)
        self.assertIn("tab_biaya.render(st, area_m2)", isi)
        for sisa in ("UNIT_PER_M2", "MATERIAL_DEFAULT", "Waterfall",
                     "Luas Area Proyek", "harga_konv_m2", "total_per_unit"):
            self.assertNotIn(sisa, isi, f"sisa Tab 7 tertinggal: {sisa}")

    def test_seluruh_tab_sudah_terekstraksi(self):
        """Setelah S5-6 tidak ada lagi badan tab di dalam berkas aplikasi."""
        isi = self._sumber(BERKAS_APLIKASI)
        for panggilan in ("tab_permeabilitas.render", "tab_kuat_tekan.render",
                          "tab_retensi_air.render", "tab_emisi_co2.render",
                          "tab_dasbor.render", "tab_biaya.render"):
            self.assertIn(panggilan, isi)


# ═══════════ 7. perbaikan S7-B: cacat bebas-bukti ═══════════

class KlaimLaboratoriumTidakBolehKembali(unittest.TestCase):
    """
    C-06 — tab pernah menyatakan harganya berasal dari "pengujian laboratorium
    2026", sementara panji dan panel auditnya sendiri menyatakan sebaliknya.
    Tidak ada satu pun besaran kanonik terkait harga di repositori.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tidak_mengklaim_sumber_laboratorium(self):
        teks = seluruh_teks(self.at).lower()
        for klaim in ("harga referensi aktual", "pengujian laboratorium 2026"):
            self.assertNotIn(klaim, teks, f"klaim tanpa dasar kembali: {klaim}")

    def test_ketiadaan_sumber_dinyatakan_eksplisit(self):
        """
        Bukan pencarian substring: kalimat penutup harus MENYANGKAL sumber,
        bukan sekadar tidak menyebutnya. Kata "kutipan pemasok" justru muncul
        di dalam penyangkalannya.
        """
        self.assertIn("Tidak ada satu pun harga yang berasal dari",
                      tab_biaya.CATATAN_PENUTUP)

    def test_menyatakan_lingkupnya_ilustratif(self):
        self.assertIn("ilustratif", tab_biaya.CATATAN_PENUTUP.lower())
        self.assertIn("diasumsikan", tab_biaya.CATATAN_PENUTUP.lower())


class InvarianKurvaSensitivitas(unittest.TestCase):
    """
    C-05 dan C-03. Tiap titik kurva dihitung ulang lewat campuran kanonik,
    sehingga kekekalan massa pengikat dijamin model domain, bukan aritmetika
    yang diulang di antarmuka.
    """

    HARGA = {"Air": 4_000.0, "Semen": 1_500.0, "Kerikil": 2_000.0,
             "Limbah Lumpur IPAL": 0.0}

    def test_penanda_komposisi_berada_di_dalam_sumbu(self):
        """C-05A: grafik wajib dapat menampilkan penandanya sendiri."""
        pct, _, kini, batas = tab_biaya.kurva_sensitivitas(self.HARGA)
        self.assertGreaterEqual(kini, float(pct[0]))
        self.assertLessEqual(kini, float(pct[-1]))
        self.assertLessEqual(kini, batas)

    def test_penanda_pada_substitusi_kanonik(self):
        """C-03: komposisi sekarang adalah 15%, bukan 40%."""
        _, _, kini, _ = tab_biaya.kurva_sensitivitas(self.HARGA)
        self.assertAlmostEqual(
            kini, float(akses.nilai("SUBSTITUSI_IPAL")), delta=1e-9)

    def test_massa_pengikat_kekal_di_titik_batas(self):
        """C-05B: dijamin core/komposisi, diperiksa ulang di sini."""
        acuan = None
        for p in (0, 15, 40, 100):
            r = tab_biaya.rancangan_beton(substitusi_ipal_persen=float(p))
            pengikat = r["massa_semen_kg"] + r["massa_ipal_kg"]
            if acuan is None:
                acuan = pengikat
            with self.subTest(persen=p):
                self.assertAlmostEqual(pengikat, acuan, delta=1e-9)
                self.assertAlmostEqual(
                    r["massa_total_kg"], 37.0, delta=1e-6)

    def test_kurva_melewati_biaya_sekarang_pada_komposisi_sekarang(self):
        pct, biaya, kini, _ = tab_biaya.kurva_sensitivitas(
            self.HARGA, retensi_per_m2=RETENSI_PER_M2_BAWAAN)
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        cocok = [b for x, b in zip(pct, biaya) if abs(float(x) - kini) < 1e-9]
        self.assertEqual(len(cocok), 1)
        self.assertAlmostEqual(cocok[0], h["sistem_per_m2"], delta=0.01)

    def test_harga_ipal_mempengaruhi_kurva(self):
        _, murah, _, _ = tab_biaya.kurva_sensitivitas(self.HARGA)
        mahal_harga = dict(self.HARGA, **{"Limbah Lumpur IPAL": 500.0})
        _, mahal, _, _ = tab_biaya.kurva_sensitivitas(mahal_harga)
        self.assertAlmostEqual(murah[0], mahal[0], delta=1e-6)
        self.assertNotAlmostEqual(murah[-1], mahal[-1], delta=1.0)

    def test_kurva_tidak_memakai_pengali_unit(self):
        """Bila 14,75 kembali menyusup, biayanya melompat ~15 kali."""
        _, biaya, _, _ = tab_biaya.kurva_sensitivitas(self.HARGA)
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        self.assertLess(max(biaya), h["beton_per_m2"] * 2)

    def test_kurva_tidak_diklaim_teruji(self):
        teks = seluruh_teks(jalankan()).lower()
        self.assertIn("aritmetika skenario", teks)
        self.assertIn("pernah dicetak maupun diuji", teks)


class LencanaTidakMelebihiBukti(unittest.TestCase):
    """C-08 — perbandingan sah di dalam skenario, bukan keunggulan ekonomi."""

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tidak_memakai_penanda_kelulusan(self):
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        self.assertNotIn("komp_bukti.LULUS", sumber,
                         "lencana biaya tidak boleh memakai penanda kelulusan")

    def test_perbandingan_menyebut_kedua_ketergantungannya(self):
        """
        S7-H memulihkan perbandingan, tetapi ia bergantung pada DUA asumsi:
        harga yang diasumsikan dan berat satuan yang berstatus sementara.
        Keduanya harus disebut di lencana yang sama.
        """
        teks = seluruh_teks(self.at)
        self.assertIn("dalam skenario harga yang diasumsikan", teks)
        self.assertIn(tab_biaya.KERAPATAN_BETON_POROS.status, teks)

    def test_tidak_mengklaim_keunggulan_ekonomi_nyata(self):
        teks = seluruh_teks(self.at).lower()
        for klaim in ("terbukti lebih murah", "lebih ekonomis secara terbukti",
                      "keunggulan biaya tervalidasi"):
            self.assertNotIn(klaim, teks)


class PenghematanMemakaiSelisihHarga(unittest.TestCase):
    """C-09 — penghematan adalah selisih harga pengikat, bukan harga semen."""

    def test_andaian_penggantian_massa_dinyatakan(self):
        teks = seluruh_teks(jalankan()).lower()
        self.assertIn("menggantikan semen menurut massa", teks)
        self.assertIn("tidak pernah diuji secara terpisah", teks)

    def test_sumber_memakai_selisih_bukan_harga_semen_saja(self):
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        self.assertIn("ipal_per_m2 * (harga_semen - harga_ipal)", sumber)


class SelisihTonaseSudahDitutup(unittest.TestCase):
    """
    C-07 ditutup oleh dua keputusan penulis. SD-06 mempensiunkan tonase
    Dasbor; C-03 memindahkan Tab 7 ke campuran kanonik. Tidak ada lagi dua
    basis yang bersaing, dan panel audit tidak boleh lagi menyatakan ada.
    """

    def test_panel_audit_menyatakan_basis_kanonik(self):
        audit = tabel_audit(jalankan())
        baris = audit[audit["Masukan"].str.contains("Basis tonase IPAL")]
        self.assertEqual(len(baris), 1)
        self.assertEqual(baris.iloc[0]["Status"], "MENGIKUTI CAMPURAN KANONIK")
        self.assertIn("dipensiunkan", baris.iloc[0]["Catatan"])

    def test_panel_audit_tidak_lagi_menyatakan_belum_diputuskan(self):
        """Klaim yang sudah tidak benar tidak boleh tertinggal di layar."""
        audit = tabel_audit(jalankan())
        self.assertNotIn("BELUM DIPUTUSKAN", set(audit["Status"]))

    def test_dasbor_tidak_lagi_menawarkan_tonase_tandingan(self):
        """
        SD-06: metrik tonase Dasbor dipensiunkan, jadi tidak ada lagi angka
        tandingan di sana. Yang tersisa terbuka adalah basis Tab 7 sendiri.
        """
        from ui.tabs import dasbor as tab_dasbor
        self.assertFalse(hasattr(tab_dasbor, "IPAL_TON_PER_100_M2"))

    def test_basis_tonase_tab7_kini_kanonik(self):
        """
        C-03 ditutup: Tab 7 memakai campuran kanonik, sehingga tonasenya kini
        SAMA dengan yang diberikan core/komposisi — tidak lagi dua basis.
        """
        from core import komposisi

        ipal = next(m for m in tab_biaya.material_bawaan() if "IPAL" in m["nama"])
        kanonik = komposisi.rancangan_campuran(
            1.0 * tab_biaya.TEBAL_BETON_M,
            berat_satuan_kg_m3=tab_biaya.KERAPATAN_BETON_POROS.nilai,
        )["massa_ipal_kg"]
        self.assertAlmostEqual(ipal["vol"], kanonik, delta=1e-9)


# ═══════════ 8. S7-C: keanggotaan campuran vs komposisi ═══════════

class KeanggotaanSistem(unittest.TestCase):
    """
    Penulis menyatakan hebel dan zeolit bagian dari SISTEM ZEOPAVE-AQUA, tetapi
    **bukan** bahan campuran beton poros (keputusan penulis, S7-D butir D-3 dan
    D-4). Keduanya berada di lapisan media retensi.

    Penegasan itu mengoreksi rumusan S7-C di berkas ini, yang menyebut keduanya
    "bagian campuran", dan mengembalikan kesesuaian dengan naskah §3.4.2 serta
    Tabel 4.2 — yang memang sudah diterapkan Tab 1 dan core/komposisi.py.

    Uji ini menjaga keanggotaan SISTEM dan pemisahan LAPISAN. Ia sengaja tidak
    menyatakan keduanya agregat, pengikat, pengisi, maupun aditif, dan tidak
    menyatakan tebal maupun basis kuantitas apa pun.
    """

    def test_hebel_dan_zeolit_ada_di_daftar_material(self):
        nama = [m["nama"].lower() for m in tab_biaya.material_bawaan()]
        self.assertTrue(any("hebel" in n for n in nama))
        self.assertTrue(any("zeolit" in n for n in nama))

    def test_keduanya_masuk_biaya_per_unit(self):
        """Keanggotaan sistem berarti biayanya ikut total; lapisannya terpisah."""
        total = sum(m["vol"] * m["harga"] for m in tab_biaya.material_bawaan())
        tanpa = sum(
            m["vol"] * m["harga"] for m in tab_biaya.material_bawaan()
            if "hebel" not in m["nama"].lower() and "zeolit" not in m["nama"].lower()
        )
        self.assertGreater(total, tanpa)

    def test_tidak_mengklaim_klasifikasi_ilmiah(self):
        """
        Sumber Tab 7 tidak boleh menyebut hebel atau zeolit sebagai agregat.
        Keanggotaan sudah dijawab penulis; klasifikasinya belum.
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read().lower()
        for klaim in ("hebel adalah agregat", "zeolit adalah agregat",
                      "hebel sebagai agregat", "zeolit sebagai agregat"):
            self.assertNotIn(klaim, sumber)


class PemisahanLapisan(unittest.TestCase):
    """
    S7-D: setiap bahan ditandai lapisannya. Penandaan ini menyatakan
    KEANGGOTAAN saja — bukan tebal, volume, atau basis kuantitas.
    """

    def test_setiap_material_punya_lapisan(self):
        for m in tab_biaya.material_bawaan():
            with self.subTest(material=m["nama"]):
                self.assertIn(m["lapisan"],
                              (tab_biaya.LAPISAN_BETON, tab_biaya.LAPISAN_RETENSI))

    def test_beton_poros_berisi_empat_bahan_sesuai_keputusan_penulis(self):
        """D-3: air, kerikil, semen, lumpur IPAL — tanpa hebel dan zeolit."""
        beton = {m["nama"] for m in tab_biaya.material_bawaan()
                 if m["lapisan"] == tab_biaya.LAPISAN_BETON}
        self.assertEqual(
            beton, {"Air", "Semen", "Kerikil", "Limbah Lumpur IPAL"})

    def test_hebel_dan_zeolit_bukan_bahan_beton(self):
        """D-4: keduanya media retensi, bukan campuran beton (naskah §3.4.2)."""
        retensi = {m["nama"] for m in tab_biaya.material_bawaan()
                   if m["lapisan"] == tab_biaya.LAPISAN_RETENSI}
        self.assertEqual(retensi, {"Hebel", "Zeolit"})

    def test_penandaan_meliputi_seluruh_bahan(self):
        """Setiap bahan punya lapisan; jumlah biayanya sama dengan sistem."""
        h = tab_biaya.biaya_lapisan(tab_biaya.material_bawaan())
        self.assertAlmostEqual(
            sum(m["vol"] * m["harga"] for m in tab_biaya.material_bawaan()),
            h["sistem_per_m2"], delta=0.01)

    def test_hanya_tebal_dari_penulis_yang_ada(self):
        """
        S7-E: penulis menetapkan beton poros 2 cm dan lapisan retensi 7,5 cm.
        Keduanya boleh ada. Tebal LAIN — termasuk pembagian 7,5 cm menjadi
        hebel dan zeolit — belum ditetapkan dan tidak boleh dikarang.
        """
        DIIZINKAN = {"TEBAL_BETON_M", "TEBAL_RETENSI_M"}
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        for simpul in pohon.body:
            if not isinstance(simpul, ast.Assign):
                continue
            for sasaran in simpul.targets:
                if not isinstance(sasaran, ast.Name):
                    continue
                if sasaran.id in DIIZINKAN:
                    continue
                if ("TEBAL" in sasaran.id or "KEDALAMAN" in sasaran.id
                        or "TINGGI_LAPISAN" in sasaran.id):
                    self.fail(f"tebal lapisan dikarang: {sasaran.id}")

    def test_tebal_sesuai_keputusan_penulis(self):
        self.assertAlmostEqual(tab_biaya.TEBAL_BETON_M, 0.02, delta=1e-12)
        self.assertAlmostEqual(tab_biaya.TEBAL_RETENSI_M, 0.075, delta=1e-12)

    def test_pembagian_hebel_zeolit_tidak_dikarang(self):
        """7,5 cm belum dibagi antara hebel dan zeolit; jangan mengarangnya."""
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        for pola in ("TEBAL_HEBEL", "TEBAL_ZEOLIT", "FRAKSI_HEBEL",
                     "FRAKSI_ZEOLIT", "PEMBAGIAN_RETENSI"):
            self.assertNotIn(pola, sumber)

    def test_tebal_ditandai_keputusan_penulis(self):
        audit = tabel_audit(jalankan())
        baris = audit[audit["Masukan"].str.contains("Tebal lapisan")]
        self.assertEqual(len(baris), 1)
        self.assertEqual(baris.iloc[0]["Status"], "KEPUTUSAN PENULIS")
        # Pembagian 7,5 cm tetap terbuka dan harus dinyatakan.
        self.assertIn("BELUM ditetapkan", baris.iloc[0]["Catatan"])

    def test_basis_retensi_ditandai_keputusan_penulis(self):
        audit = tabel_audit(jalankan())
        baris = audit[audit["Masukan"].str.contains("Hebel 6 kg")]
        self.assertEqual(len(baris), 1)
        self.assertEqual(baris.iloc[0]["Status"], "KEPUTUSAN PENULIS")
        self.assertIn("tidak diskalakan lagi", baris.iloc[0]["Catatan"])


class KerapatanAsumsiTerpusat(unittest.TestCase):
    """
    S7-F melarang kerapatan apa pun masuk Tab 7, karena belum diizinkan.
    S7-H mengizinkannya sebagai **asumsi operasional sementara**, sehingga
    aturannya berubah: kerapatan boleh ada, tetapi hanya di SATU tempat
    bernama, membawa statusnya, dan tidak pernah sebagai angka telanjang.

    SD-16C tetap terbuka. Yang berubah adalah izin memakainya, bukan buktinya.
    """

    def test_kerapatan_hanya_hidup_di_satu_tempat(self):
        """Angka 1850 hanya boleh muncul sekali: di dalam asumsi terpusat."""
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        self.assertEqual(
            sumber.count("1850"), 1,
            "kerapatan harus hidup di satu tempat saja, bukan tersebar",
        )
        self.assertIn("KERAPATAN_BETON_POROS = AsumsiOperasional(", sumber)

    def test_perhitungan_membaca_asumsi_bukan_literal(self):
        """
        Tidak ada fungsi yang boleh menuliskan ulang angkanya; semuanya wajib
        lewat KERAPATAN_BETON_POROS.
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.FunctionDef):
                for n in ast.walk(simpul):
                    if isinstance(n, ast.Constant) and n.value == 1850.0:
                        self.fail(f"literal kerapatan di dalam {simpul.name}()")

    def test_status_asumsi_melekat_pada_nilainya(self):
        k = tab_biaya.KERAPATAN_BETON_POROS
        self.assertAlmostEqual(k.nilai, 1850.0, delta=1e-9)
        self.assertEqual(k.satuan, "kg/m³")
        self.assertIn("asumsi", k.status.lower())
        self.assertIn("sementara", k.status.lower())
        self.assertIn("bukan hasil pengukuran", k.catatan.lower())

    def test_tidak_diklaim_terukur_di_layar(self):
        teks = seluruh_teks(jalankan()).lower()
        self.assertIn(tab_biaya.KERAPATAN_BETON_POROS.status.lower(), teks)
        for klaim in ("berat satuan terukur", "kerapatan terukur",
                      "berat satuan hasil uji"):
            self.assertNotIn(klaim, teks)

    def test_kerapatan_tetap_lokal_meski_campuran_kanonik(self):
        """
        C-03 membuat Tab 7 membaca CAMPURAN dari `core/`. Kerapatannya tetap
        asumsi lokal: ia belum terukur, dan mengambilnya dari `konstanta.py`
        akan menyiratkan kewenangan yang belum dimilikinya (SD-16C terbuka).
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        self.assertIn("KERAPATAN_BETON_POROS = AsumsiOperasional(", sumber)
        pohon = ast.parse(sumber)
        impor = set()
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.Import):
                impor.update(a.name.split(".")[0] for a in simpul.names)
            elif isinstance(simpul, ast.ImportFrom) and simpul.module:
                impor.add(simpul.module.split(".")[0])
        # Campuran boleh dari core; kewenangan kanonik langsung tidak.
        self.assertIn("core", impor)
        self.assertNotIn("konstanta", impor)

    def test_geometri_diturunkan(self):
        g = tab_biaya.geometri_beton()
        self.assertAlmostEqual(g["volume_m3"], 1.0 * 0.02, delta=1e-12)
        self.assertAlmostEqual(
            g["massa_kg"], g["volume_m3"] * tab_biaya.KERAPATAN_BETON_POROS.nilai,
            delta=1e-9)
        self.assertAlmostEqual(g["massa_kg"], 37.0, delta=1e-9)

    def test_neraca_massa_beton_tertutup(self):
        """Jumlah bahan wajib sama dengan massa geometri."""
        r = tab_biaya.rancangan_beton()
        self.assertTrue(r["neraca_tertutup"])
        self.assertAlmostEqual(
            r["massa_total_kg"], tab_biaya.geometri_beton()["massa_kg"],
            delta=1e-9)


class IdentitasCampuranKanonik(unittest.TestCase):
    """
    C-03 DITUTUP (keputusan penulis): Tab 7 mewakili campuran eksperimen §3.3.

    Sebelumnya kuantitasnya menyiratkan substitusi 40% dan f.a.b 0,20 —
    campuran yang **tidak pernah dicetak**. Kini kuantitas beton poros
    diturunkan `core/komposisi.rancangan_campuran()`, satu-satunya sumber
    ilmiah campuran itu.

    Yang TIDAK ikut terselesaikan: kerapatan 1.850 kg/m³ tetap asumsi
    operasional sementara, dan **SD-16C tetap terbuka**.
    """

    def test_substitusi_kanonik_15_persen(self):
        r = tab_biaya.rancangan_beton()
        self.assertAlmostEqual(
            r["substitusi_ipal_persen"], float(akses.nilai("SUBSTITUSI_IPAL")),
            delta=1e-9)

    def test_faktor_air_pengikat_kanonik(self):
        r = tab_biaya.rancangan_beton()
        self.assertAlmostEqual(
            r["faktor_air_pengikat"], float(akses.nilai("FAKTOR_AIR_PENGIKAT")),
            delta=1e-9)

    def test_formulasi_lama_tidak_aktif(self):
        """Substitusi 40% dan f.a.b 0,20 tidak boleh hidup di jalur hitung."""
        bahan = {m["nama"]: m["vol"] for m in tab_biaya.material_bawaan()}
        pengikat = bahan["Semen"] + bahan["Limbah Lumpur IPAL"]
        self.assertNotAlmostEqual(
            bahan["Limbah Lumpur IPAL"] / pengikat * 100, 40.0, delta=0.5)
        self.assertNotAlmostEqual(bahan["Air"] / pengikat, 0.20, delta=0.01)

    #: Satu-satunya pengecualian penjaga literal, dan ia harus disebut namanya.
    #:
    #: `KUANTITAS_TABEL_HISTORIS` memuat 0,4 — kuantitas lumpur IPAL pada tabel
    #: biaya proyek historis, yang KEBETULAN senilai f.a.b kanonik 0,40. Dua
    #: besaran berbeda dengan angka yang sama. Ia catatan provenans mati:
    #: `test_kuantitas_historis_tidak_dibaca_perhitungan` membuktikan tidak
    #: ada jalur hitung yang membacanya.
    HISTORIS_DIKECUALIKAN = ("KUANTITAS_TABEL_HISTORIS",)

    def test_tidak_ada_literal_campuran_di_antarmuka(self):
        """
        Tab 7 tidak boleh menjadi sumber kebenaran ilmiah kedua: 15, 0,40, dan
        rasio 3 tidak boleh ditulis sebagai literal di modul ini.
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        # Hanya konstanta modul-level: itulah yang berpotensi menjadi sumber
        # kebenaran kedua. Angka di dalam widget (mis. batas penggeser PPN)
        # bukan definisi campuran.
        for simpul in pohon.body:
            if not isinstance(simpul, ast.Assign):
                continue
            nama = [s.id for s in simpul.targets if isinstance(s, ast.Name)]
            if any(n in self.HISTORIS_DIKECUALIKAN for n in nama):
                continue
            for n in ast.walk(simpul.value):
                if isinstance(n, ast.Constant) and n.value in (15.0, 0.40, 0.15):
                    self.fail(f"literal campuran di antarmuka: {n.value}")

    def test_kuantitas_dari_domain_bukan_disalin(self):
        """Nilainya wajib sama dengan keluaran core/komposisi, bukan salinan."""
        from core import komposisi

        r = komposisi.rancangan_campuran(
            tab_biaya.LUAS_SATUAN_M2 * tab_biaya.TEBAL_BETON_M,
            berat_satuan_kg_m3=tab_biaya.KERAPATAN_BETON_POROS.nilai)
        bahan = {m["nama"]: m["vol"] for m in tab_biaya.material_bawaan()}
        for nama, kunci in (("Air", "massa_air_kg"), ("Semen", "massa_semen_kg"),
                            ("Kerikil", "massa_agregat_kg"),
                            ("Limbah Lumpur IPAL", "massa_ipal_kg")):
            self.assertAlmostEqual(bahan[nama], r[kunci], delta=1e-9)

    def test_sd16c_tetap_terbuka(self):
        """Identitas campuran terselesaikan; kerapatan TIDAK."""
        k = tab_biaya.KERAPATAN_BETON_POROS
        self.assertIn("asumsi", k.status.lower())
        self.assertIn("sementara", k.status.lower())
        self.assertAlmostEqual(k.nilai, 1850.0, delta=1e-9)
        self.assertEqual(akses.status("BERAT_SATUAN_BETON"), akses.ASUMSI)

    def test_kerapatan_benda_uji_tidak_diselundupkan(self):
        """1.279,53 tidak boleh muncul sebagai pengganti diam-diam."""
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        for pola in ("1279", "1_279", "1279.53"):
            self.assertNotIn(pola, sumber)


class PengaliLamaTidakKembali(unittest.TestCase):
    """
    S7-E: `UNIT_PER_M2 = 14,75` dipertahankan agar riwayatnya tertelusur,
    tetapi tidak boleh dipakai satu perhitungan pun.
    """

    def test_unit_per_m2_tidak_ikut_perhitungan_apa_pun(self):
        """
        14,75 dipertahankan agar riwayatnya tertelusur, tetapi tidak boleh
        muncul di dalam fungsi mana pun. Bila ia kembali, biaya melompat ~15×.
        """
        self.assertAlmostEqual(tab_biaya.UNIT_PER_M2, 14.75, delta=1e-9)
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        for simpul in ast.walk(pohon):
            if isinstance(simpul, ast.FunctionDef):
                for n in ast.walk(simpul):
                    if isinstance(n, ast.Name) and n.id == "UNIT_PER_M2":
                        self.fail(f"UNIT_PER_M2 dipakai di dalam {simpul.name}()")
                    if isinstance(n, ast.Constant) and n.value == 14.75:
                        self.fail(f"literal 14,75 di dalam {simpul.name}()")


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ═══════════ PRICE-01: provenans harga dan satuan hebel ═══════════

class ProvenansHargaHistoris(unittest.TestCase):
    """
    PRICE-01. Keenam harga berasal dari tabel perhitungan biaya proyek
    ZEOPAVE-AQUA. Tabel itu membuktikan angka mana yang dipakai proyek; ia
    TIDAK membuktikan angkanya benar.

    Uji di kelas ini menjaga jarak antara kedua pernyataan itu. Yang dijaga
    bukan besaran angkanya — angkanya memang tidak diubah PRICE-01 — melainkan
    sekuat apa antarmuka boleh mengklaimnya.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    #: Harga tabel historis, dipatok. PRICE-01 tidak menggeser satu pun.
    HARGA_HISTORIS = {
        "Air": 4_000, "Semen": 1_500, "Kerikil": 2_000,
        "Limbah Lumpur IPAL": 0, "Hebel": 20_000, "Zeolit": 10_000,
    }

    def test_keenam_harga_tidak_bergeser(self):
        self.assertEqual(tab_biaya.harga_satuan(), self.HARGA_HISTORIS)

    def test_total_tabel_historis_terekonstruksi(self):
        """
        Bukti provenans yang dapat dieksekusi: kuantitas tabel lama dikalikan
        harga yang dipakai hari ini harus kembali ke total yang tercatat.
        Bila seseorang menggeser sebuah harga, kesamaan ini gugur.
        """
        self.assertAlmostEqual(
            tab_biaya.total_tabel_historis(), 137_700.0, delta=0.01)
        self.assertAlmostEqual(
            tab_biaya.total_tabel_historis(),
            tab_biaya.TOTAL_TABEL_HISTORIS, delta=0.01)

    def test_setiap_baris_tabel_historis_terekonstruksi(self):
        """Bukan hanya totalnya: tiap baris tabel harus cocok satu per satu."""
        diharapkan = {"Air": 800.0, "Semen": 900.0, "Kerikil": 6_000.0,
                      "Limbah Lumpur IPAL": 0.0, "Hebel": 120_000.0,
                      "Zeolit": 10_000.0}
        harga = tab_biaya.harga_satuan()
        for nama, kuantitas in tab_biaya.KUANTITAS_TABEL_HISTORIS.items():
            with self.subTest(bahan=nama):
                self.assertAlmostEqual(
                    kuantitas * harga[nama], diharapkan[nama], delta=0.01)

    def test_status_tidak_mengklaim_verifikasi(self):
        """Statusnya menyebut asal, bukan pembenaran."""
        s = tab_biaya.STATUS_HARGA.lower()
        self.assertIn("historis", s)
        for klaim in ("pasar", "pemasok", "survei", "terverifikasi", "terukur"):
            self.assertNotIn(klaim, s)

    def test_antarmuka_menyebut_asal_harga(self):
        self.assertIn(tab_biaya.SUMBER_HARGA, seluruh_teks(self.at))

    def test_antarmuka_tidak_mengklaim_harga_pasar(self):
        """
        Penyangkalan, bukan pencarian substring: kata "survei pasar" memang
        muncul — di dalam kalimat yang menyangkalnya. Yang dilarang adalah
        klaim positifnya.
        """
        teks = seluruh_teks(self.at).lower()
        for klaim in ("harga pasar terkini", "survei harga", "kutipan pemasok dari",
                      "harga pasar aktual", "harga terverifikasi"):
            self.assertNotIn(klaim, teks, f"klaim tanpa dasar: {klaim}")
        self.assertIn("tidak ada satu pun harga yang berasal dari", teks)

    def test_panel_audit_menandai_keenam_harga_historis(self):
        audit = tabel_audit(self.at)
        baris = audit[audit["Status"].str.startswith(tab_biaya.STATUS_HARGA)]
        self.assertEqual(len(baris), 6)

    def test_tabel_historis_tercatat_sebagai_catatan_proyek(self):
        """Tabelnya sendiri masuk audit, dengan batas kekuatannya disebut."""
        audit = tabel_audit(self.at)
        baris = audit[audit["Masukan"].str.contains("Tabel perhitungan biaya")]
        self.assertEqual(len(baris), 1)
        catatan = baris.iloc[0]["Catatan"].lower()
        self.assertIn("tidak membuktikan harganya benar", catatan)


class KuantitasHistorisTidakAktif(unittest.TestCase):
    """
    PRICE-01 memasukkan kuantitas tabel lama ke dalam modul sebagai catatan
    provenans. Kelas ini membuktikan catatan itu MATI: ia tidak menyentuh satu
    pun angka biaya, dan formulasi 40% / f.a.b 0,20 tidak kembali hidup.
    """

    def test_kuantitas_historis_tidak_dibaca_perhitungan(self):
        """
        Penelusuran AST: satu-satunya pembaca `KUANTITAS_TABEL_HISTORIS`
        adalah `total_tabel_historis`, yang bukan bagian model biaya.
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        pembaca = set()
        for simpul in ast.walk(pohon):
            if not isinstance(simpul, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for n in ast.walk(simpul):
                if isinstance(n, ast.Name) and n.id == "KUANTITAS_TABEL_HISTORIS":
                    pembaca.add(simpul.name)
        self.assertEqual(pembaca, {"total_tabel_historis"})

    def test_total_historis_tidak_dipanggil_model_biaya(self):
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            pohon = ast.parse(f.read())
        pemanggil = set()
        for simpul in ast.walk(pohon):
            if not isinstance(simpul, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for n in ast.walk(simpul):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "total_tabel_historis"):
                    pemanggil.add(simpul.name)
        self.assertEqual(pemanggil, set())

    def test_kuantitas_aktif_bukan_kuantitas_historis(self):
        """Beton poros memakai campuran kanonik; angkanya harus berbeda."""
        aktif = {m["nama"]: m["vol"] for m in tab_biaya.material_bawaan()}
        for nama in ("Air", "Semen", "Kerikil", "Limbah Lumpur IPAL"):
            with self.subTest(bahan=nama):
                self.assertNotAlmostEqual(
                    aktif[nama], tab_biaya.KUANTITAS_TABEL_HISTORIS[nama],
                    delta=0.01)

    def test_kuantitas_retensi_memang_bertahan(self):
        """
        Hebel 6 kg dan zeolit 1 kg per m² sama dengan tabel lama — dan itu
        benar: keputusan penulis mempertahankannya. Kesamaan ini dinyatakan
        agar tidak disalahartikan sebagai formulasi lama yang kembali.
        """
        aktif = {m["nama"]: m["vol"] for m in tab_biaya.material_bawaan()}
        for nama in ("Hebel", "Zeolit"):
            with self.subTest(bahan=nama):
                self.assertAlmostEqual(
                    aktif[nama], tab_biaya.KUANTITAS_TABEL_HISTORIS[nama],
                    delta=1e-9)

    def test_formulasi_lama_tetap_mati(self):
        r = tab_biaya.rancangan_beton()
        self.assertNotAlmostEqual(r["substitusi_ipal_persen"], 40.0, delta=0.5)
        self.assertNotAlmostEqual(r["faktor_air_pengikat"], 0.20, delta=0.01)
        self.assertAlmostEqual(
            r["substitusi_ipal_persen"], float(akses.nilai("SUBSTITUSI_IPAL")),
            delta=1e-9)


class BatasanSatuanHebel(unittest.TestCase):
    """
    PRICE-01. Tabel historis mengenakan Rp 20.000 per KILOGRAM; keterangan
    pembelian penulis menyebut Rp 20.000 per BATANG. Massa satu batang tidak
    diketahui.

    Dua hal sama-sama dilarang, dan keduanya dijaga di sini: mengarang
    konversinya, dan mengubah angkanya diam-diam. Yang boleh dilakukan hanya
    menyatakan keduanya.
    """

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_harga_hebel_tidak_diubah(self):
        self.assertAlmostEqual(
            tab_biaya.harga_satuan()["Hebel"], 20_000, delta=1e-9)

    def test_biaya_hebel_tanpa_faktor_konversi(self):
        """6 kg × Rp 20.000 = Rp 120.000, tanpa pengali apa pun di antaranya."""
        baris = [m for m in tab_biaya.material_bawaan() if m["nama"] == "Hebel"]
        self.assertEqual(len(baris), 1)
        self.assertAlmostEqual(
            baris[0]["vol"] * baris[0]["harga"], 120_000.0, delta=0.01)

    def test_tidak_ada_konstanta_massa_atau_dimensi_batang(self):
        """
        Tidak ada massa batang, tidak ada dimensi, tidak ada jumlah batang.
        Bila salah satunya muncul, seseorang telah mengarang angka.
        """
        with io.open(BERKAS_TAB, encoding="utf8") as f:
            sumber = f.read()
        pohon = ast.parse(sumber)
        terlarang = ("BATANG", "BATA_", "MASSA_BATA", "KG_PER_BATANG",
                     "DIMENSI", "JUMLAH_BATANG", "VOLUME_BATANG")
        for simpul in pohon.body:
            if not isinstance(simpul, ast.Assign):
                continue
            for s in simpul.targets:
                if isinstance(s, ast.Name):
                    for kata in terlarang:
                        self.assertNotIn(
                            kata, s.id.upper(),
                            f"konstanta konversi hebel muncul: {s.id}")

    def test_batasan_menyatakan_kedua_satuan(self):
        b = tab_biaya.BATASAN_HEBEL.lower()
        self.assertIn("kilogram", b)
        self.assertIn("batang", b)
        self.assertIn("tidak ada catatan konversi", b)
        self.assertIn("massa satu batang tidak diketahui", b)

    def test_batasan_menyatakan_konversi_tidak_dihitung(self):
        """Bukan sekadar menyebut konflik: menyatakan apa yang TIDAK dilakukan."""
        b = tab_biaya.BATASAN_HEBEL.lower()
        self.assertIn("tidak dihitung di sini", b)
        self.assertIn("dibiarkan apa adanya", b)

    def test_batasan_tampil_terbuka_di_antarmuka(self):
        """
        Wajib tampil, bukan hanya ada di dokumentasi — dan bukan pula
        tersembunyi di dalam panel audit yang terlipat.
        """
        st = StPalsu()
        tab_biaya.render(st, 1000.0)
        peringatan = [d[1] for d in st.dicatat if d[0] == "warning"]
        self.assertIn(tab_biaya.BATASAN_HEBEL, peringatan)

    def test_batasan_terbaca_pada_aplikasi_sungguhan(self):
        self.assertIn("Satuan harga hebel belum terselesaikan",
                      seluruh_teks(self.at))

    def test_panel_audit_menandai_satuan_bermasalah(self):
        audit = tabel_audit(self.at)
        baris = audit[audit["Masukan"].str.contains("hebel")]
        self.assertEqual(len(baris), 1)
        self.assertIn("SATUAN BERMASALAH", baris.iloc[0]["Status"])
        self.assertIn("tidak dihitung", baris.iloc[0]["Catatan"])
