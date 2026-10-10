"""
Uji antarmuka tab Mulai di Sini dan model 3D konseptualnya.

Tab ini pintu masuk bagi pengguna yang baru mengenal aplikasi. Karena ia
menyederhanakan, justru di sinilah klaim paling mudah melebar tanpa disadari.
Yang dijaga berkas ini:

1. **Simulasi terpandu tidak punya angkanya sendiri.** Hasilnya harus persis
   keluaran `core/hidrologi.skenario()` — fungsi yang juga dipakai tab Retensi
   Air — untuk masukan yang sama.

2. **Retensi tidak dipinjamkan.** Bila komposisi skenario aktif belum pernah
   diuji, tab ini tidak menjalankan simulasi dengan 40,0% milik konfigurasi
   acuan, dan model 3D tidak menggambar pembagian tetesnya (ADR-009).

3. **Model 3D tidak membawa angka teknik.** Ia konseptual dan menyatakannya:
   tidak berskala, bukan simulasi aliran fluida, tanpa sumbu berukuran, dan
   setiap lapisannya berasal dari daftar kanonik `data/akses.py`.

4. **Antarmuka tanpa emoji.** Judul, label, tombol, dan pesan berupa kata.

Seperti berkas uji lain di folder ini, ini adalah VERIFIKASI perangkat lunak,
bukan validasi eksperimental (ADR-004).

    python -m unittest discover -s validation -v
"""

from __future__ import annotations

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
from ui.components import model3d  # noqa: E402
from ui.tabs import mulai  # noqa: E402

BERKAS_APLIKASI = os.path.join(AKAR, "AQUAPAVE.py")
BERKAS_MODEL = os.path.join(AKAR, "ui", "components", "model3d.py")
TENGGAT = 60

RETENSI_TERUKUR = 40.0

#: Piktograf, simbol aneka, dingbat, dan pemilih variasi. Panah dan garis
#: tipografi (→, —, ·) berada di luar rentang ini dan tetap diizinkan.
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")


def jalankan() -> AppTest:
    os.chdir(AKAR)
    at = AppTest.from_file(BERKAS_APLIKASI, default_timeout=TENGGAT)
    at.run()
    return at


def tab_mulai(at):
    return at.tabs[0]


def tombol(at, label: str):
    cocok = [b for b in at.button if b.label == label]
    return cocok[0] if cocok else None


def widget(wadah, jenis: str, label: str):
    cocok = [x for x in getattr(wadah, jenis) if x.label == label]
    if not cocok:
        raise AssertionError(
            f"{jenis} {label!r} tidak ada; yang ada: "
            f"{[x.label for x in getattr(wadah, jenis)]}")
    return cocok[0]


def metrik(at) -> dict[str, str]:
    return {m.label: m.value for m in tab_mulai(at).metric}


def teks_tab(at) -> str:
    """Seluruh prosa tab Mulai di Sini yang terbaca pengguna."""
    t = tab_mulai(at)
    bagian = []
    for jenis in ("markdown", "caption", "info", "warning", "success", "error"):
        bagian += [x.value for x in getattr(t, jenis)]
    return "\n".join(bagian)


def pilih_percobaan(at, kunci: str) -> AppTest:
    at.radio(key=mulai.KUNCI_PERCOBAAN).set_value(kunci).run()
    return at


def jalankan_simulasi(at) -> AppTest:
    tombol(at, "Jalankan simulasi").click().run()
    return at


def skenario_kustom(at, persen_ipal: float | None = None) -> AppTest:
    """Tambah skenario kustom; bila diminta, geser substitusi lumpur IPAL-nya."""
    at.sidebar.button[0].click().run()
    if persen_ipal is not None:
        [s for s in at.sidebar.slider if "IPAL" in s.label][0] \
            .set_value(persen_ipal).run()
    return at


# ═══════════ 1. tab pembuka ═══════════

class TabPembuka(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.at = jalankan()

    def test_tanpa_kegagalan(self):
        self.assertEqual(list(self.at.exception), [])

    def test_menjadi_tab_pertama(self):
        self.assertEqual(tab_mulai(self.at).label, "Mulai di Sini")

    def test_empat_langkah_berurutan(self):
        teks = teks_tab(self.at)
        letak = [teks.find(f"Langkah {n} dari 4") for n in (1, 2, 3, 4)]
        self.assertNotIn(-1, letak, "ada langkah yang tidak digambar")
        self.assertEqual(letak, sorted(letak), "langkah tidak berurutan")

    def test_belum_ada_hasil_sebelum_dijalankan(self):
        self.assertEqual(metrik(self.at), {})
        self.assertIn(mulai.PESAN_BELUM_DIJALANKAN,
                      [i.value for i in tab_mulai(self.at).info])

    def test_daftar_istilah_tersedia(self):
        label = [e.label for e in tab_mulai(self.at).expander]
        self.assertIn("Istilah yang sering muncul", label)
        self.assertIn("Cara membaca label status bukti", label)

    def test_menunjuk_ke_setiap_tab_teknis(self):
        """Penunjuk arah harus menyebut tab yang benar-benar ada."""
        ada = {t.label for t in self.at.tabs}
        for nama, _ in mulai.PENUNJUK_TAB:
            with self.subTest(tab=nama):
                self.assertIn(nama, ada)
        self.assertEqual(
            {n for n, _ in mulai.PENUNJUK_TAB} | {"Mulai di Sini"}, ada,
            "ada tab teknis yang tidak ditunjuk dari tab pembuka")

    def test_model_3d_digambar_beserta_versi_teksnya(self):
        t = tab_mulai(self.at)
        self.assertTrue(len(t.get("plotly_chart")) >= 1, "model 3D tidak digambar")
        self.assertIn("Versi teks model ini (tanpa tampilan 3D)",
                      [e.label for e in t.expander])
        self.assertIn(model3d.KETERANGAN_KONSEPTUAL,
                      [c.value for c in t.caption])


# ═══════════ 2. simulasi terpandu memakai perhitungan yang sama ═══════════

class SimulasiTerpandu(unittest.TestCase):

    def test_hasil_acuan_sama_dengan_core_hidrologi(self):
        at = jalankan_simulasi(jalankan())
        h = hidrologi.skenario(
            hidrologi.ACUAN_INTENSITAS_MM_PER_JAM, hidrologi.ACUAN_LUAS_M2,
            hidrologi.ACUAN_DURASI_JAM, RETENSI_TERUKUR)
        self.assertEqual(metrik(at), {
            "Air hujan yang jatuh": f"{mulai.angka(h['volume_hujan_m3'])} m³",
            "Air yang tertahan sistem": f"{mulai.angka(h['air_tertahan_m3'])} m³",
            "Limpasan dengan ZEOPAVE-AQUA":
                f"{mulai.angka(h['limpasan_zeopave_m3'])} m³",
            "Pengurangan limpasan":
                f"{mulai.angka(h['reduksi_limpasan_persen'])}%",
        })

    def test_hasil_acuan_mereproduksi_skala_naskah(self):
        """OUTPUT3 §4.6: 20.000 liter tertahan dari 50.000 liter yang jatuh."""
        at = jalankan_simulasi(jalankan())
        teks = teks_tab(at)
        self.assertIn(
            f"{mulai.angka(akses.nilai('SKALA_AIR_TERTAHAN'), 0)} liter", teks)
        self.assertIn(
            f"{mulai.angka(akses.nilai('SKALA_AIR_JATUH'), 0)} liter", teks)

    def test_hasil_berlabel_keluaran_model(self):
        at = jalankan_simulasi(jalankan())
        self.assertIn("KELUARAN MODEL", teks_tab(at))
        self.assertTrue(
            any("bukan hasil pengukuran lapangan" in w.value
                for w in tab_mulai(at).warning),
            "catatan batas penafsiran hidrologi tidak ikut tampil")

    def test_setiap_percobaan_dihitung_dari_masukannya(self):
        for p in mulai.daftar_percobaan(
                hidrologi.ACUAN_LUAS_M2, hidrologi.ACUAN_INTENSITAS_MM_PER_JAM):
            with self.subTest(percobaan=p.kunci):
                at = jalankan_simulasi(pilih_percobaan(jalankan(), p.kunci))
                h = hidrologi.skenario(
                    p.intensitas_mm_per_jam, p.luas_m2, p.durasi_jam,
                    RETENSI_TERUKUR)
                self.assertEqual(
                    metrik(at)["Air yang tertahan sistem"],
                    f"{mulai.angka(h['air_tertahan_m3'])} m³")

    def test_masukan_yang_diubah_menandai_hasil_usang(self):
        at = jalankan_simulasi(jalankan())
        sebelum = metrik(at)
        widget(tab_mulai(at), "number_input", "Luas area (m²)") \
            .set_value(2000.0).run()
        self.assertIn(mulai.PESAN_MASUKAN_BERUBAH,
                      [i.value for i in tab_mulai(at).info])
        self.assertEqual(metrik(at), sebelum,
                         "hasil berubah tanpa simulasi dijalankan ulang")
        jalankan_simulasi(at)
        self.assertNotIn(mulai.PESAN_MASUKAN_BERUBAH,
                         [i.value for i in tab_mulai(at).info])
        self.assertNotEqual(metrik(at), sebelum)

    def test_tidak_menulis_ke_skenario(self):
        """Masukan percobaan milik tab ini saja; skenario acuan tidak tersentuh."""
        at = jalankan()
        pilih_percobaan(at, "hujan_deras")
        jalankan_simulasi(at)
        aktif = [s for s in at.sidebar.slider if "Intensitas" in s.label][0]
        self.assertEqual(aktif.value, int(hidrologi.ACUAN_INTENSITAS_MM_PER_JAM))
        self.assertEqual(at.sidebar.radio[0].value, skenario.ACUAN)

    def test_tab_tidak_menyediakan_kendali_retensi(self):
        """Asumsi retensi hanya boleh dinyatakan di tab Retensi Air."""
        t = tab_mulai(jalankan())
        for jenis in ("slider", "number_input"):
            for w in getattr(t, jenis):
                with self.subTest(kendali=w.label):
                    self.assertNotIn("etensi", w.label)
                    self.assertNotIn("impasan", w.label)


# ═══════════ 3. komposisi yang belum diuji ═══════════

class KomposisiBelumDiuji(unittest.TestCase):

    def test_simulasi_tidak_ditawarkan(self):
        at = skenario_kustom(jalankan(), 20)
        t = tab_mulai(at)
        self.assertIsNone(tombol(at, "Jalankan simulasi"))
        self.assertEqual(list(t.number_input), [])
        self.assertEqual(metrik(at), {})
        self.assertTrue(
            any(FRASA_TIDAK_TERSEDIA in w.value for w in t.warning))
        self.assertIn(mulai.PESAN_PERLU_ACUAN, [i.value for i in t.info])

    def test_retensi_acuan_tidak_dipinjamkan(self):
        at = skenario_kustom(jalankan(), 20)
        teks = teks_tab(at)
        self.assertNotIn(mulai.angka(RETENSI_TERUKUR) + "%", teks)
        self.assertNotIn("4 dari 10 tetes", teks)
        self.assertIn(model3d.keterangan_tetes(None), teks)

    def test_hasil_lama_tidak_ikut_ke_skenario_lain(self):
        """Hasil yang dihitung untuk acuan bukan milik komposisi lain."""
        at = jalankan_simulasi(jalankan())
        self.assertNotEqual(metrik(at), {})
        skenario_kustom(at, 20)
        self.assertEqual(metrik(at), {})

    def test_satu_tombol_kembali_ke_acuan(self):
        at = skenario_kustom(jalankan(), 20)
        tombol(at, "Kembali ke Konfigurasi Acuan Penelitian").click().run()
        self.assertEqual(list(at.exception), [])
        self.assertIsNotNone(tombol(at, "Jalankan simulasi"))
        pemilih = at.sidebar.radio[0]
        self.assertEqual(pemilih.value, skenario.ACUAN)
        self.assertEqual(len(pemilih.options), 2,
                      "skenario kustom ikut terhapus saat kembali ke acuan")

    def test_kustom_identik_dengan_acuan_tetap_dapat_disimulasikan(self):
        """Komposisi yang sama persis dengan acuan memang sudah diuji."""
        at = skenario_kustom(jalankan())
        self.assertIsNotNone(tombol(at, "Jalankan simulasi"))


# ═══════════ 4. percobaan siap pakai ═══════════

class PercobaanSiapPakai(unittest.TestCase):

    def setUp(self):
        self.daftar = mulai.daftar_percobaan(750.0, 30.0)

    def test_titik_awal_adalah_skenario_naskah(self):
        p = self.daftar[0]
        self.assertEqual(p.luas_m2, akses.nilai("SKALA_LUAS_ACUAN"))
        self.assertEqual(p.intensitas_mm_per_jam,
                         akses.nilai("SKALA_INTENSITAS_ACUAN"))
        self.assertEqual(p.durasi_jam, hidrologi.ACUAN_DURASI_JAM)

    def test_kunci_unik(self):
        kunci = [p.kunci for p in self.daftar]
        self.assertEqual(len(kunci), len(set(kunci)))

    def test_semua_di_dalam_rentang_kendali(self):
        for p in self.daftar:
            with self.subTest(percobaan=p.kunci):
                self.assertTrue(
                    mulai.RENTANG_LUAS_M2[0] <= p.luas_m2
                    <= mulai.RENTANG_LUAS_M2[1])
                self.assertTrue(
                    mulai.RENTANG_INTENSITAS_MM_PER_JAM[0]
                    <= p.intensitas_mm_per_jam
                    <= mulai.RENTANG_INTENSITAS_MM_PER_JAM[1])
                self.assertTrue(
                    mulai.RENTANG_DURASI_JAM[0] <= p.durasi_jam
                    <= mulai.RENTANG_DURASI_JAM[1])

    def test_atur_sendiri_berangkat_dari_skenario_aktif(self):
        p = [x for x in self.daftar if x.kunci == mulai.PERCOBAAN_SENDIRI][0]
        self.assertEqual((p.luas_m2, p.intensitas_mm_per_jam), (750.0, 30.0))

    def test_percobaan_tidak_mengaku_sebagai_standar(self):
        """Tidak ada golongan hujan atau jenis lahan yang dikarang."""
        for p in self.daftar:
            teks = (p.judul + " " + p.uraian).lower()
            for kata in ("sni", "ringan", "sedang", "lebat", "ekstrem",
                         "kala ulang", "parkir", "perumahan"):
                with self.subTest(percobaan=p.kunci, kata=kata):
                    self.assertNotIn(kata, teks)

    def test_rentang_sama_dengan_kendali_yang_sudah_ada(self):
        """
        Rentang tab pembuka tidak boleh lebih longgar daripada kendali asal:
        luas dan intensitas di bilah sisi, durasi di tab Retensi Air.
        """
        at = jalankan()
        luas = [n for n in at.sidebar.number_input if "Luas Area" in n.label][0]
        hujan = [s for s in at.sidebar.slider if "Intensitas" in s.label][0]
        durasi = widget(at, "number_input", "Durasi Hujan (jam)")
        self.assertEqual((luas.min, luas.max), mulai.RENTANG_LUAS_M2)
        self.assertEqual((hujan.min, hujan.max),
                         mulai.RENTANG_INTENSITAS_MM_PER_JAM)
        self.assertEqual((durasi.min, durasi.max), mulai.RENTANG_DURASI_JAM)


# ═══════════ 5. model 3D konseptual ═══════════

class Model3D(unittest.TestCase):

    def setUp(self):
        self.lapisan = akses.lapisan_sistem()

    def test_setiap_lapisan_kanonik_digambar(self):
        nama = {j.name for j in model3d.gambar(self.lapisan).data}
        for lap in self.lapisan:
            with self.subTest(lapisan=lap["nama"]):
                self.assertIn(lap["nama"], nama)

    def test_urutan_mengikuti_daftar_kanonik(self):
        tata = model3d.tata_letak(self.lapisan)
        atas = [b["z_atas"] for b in tata["lempeng"]]
        self.assertEqual(atas, sorted(atas, reverse=True))
        digambar = [b["nama"] for b in tata["lempeng"]] \
            + [p["nama"] for p in tata["pipa"]]
        self.assertEqual(sorted(digambar),
                         sorted(lap["nama"] for lap in self.lapisan))

    def test_setiap_lapisan_punya_penjelasan_awam(self):
        for lap in self.lapisan:
            with self.subTest(lapisan=lap["nama"]):
                self.assertIsNot(model3d.rupa(lap["nama"]),
                                 model3d.RUPA_CADANGAN)
                self.assertTrue(model3d.rupa(lap["nama"]).sederhana)

    def test_penjelasan_awam_tanpa_angka_teknik(self):
        """
        Model tidak boleh menjadi sumber angka: tidak ada tebal, persen, atau
        sifat material di dalam kalimat penjelasannya.
        """
        for kunci, r in model3d.RUPA.items():
            with self.subTest(lapisan=kunci):
                self.assertIsNone(re.search(r"\d", r.sederhana))
        self.assertIsNone(re.search(r"\d", model3d.TANAH_DASAR["sederhana"]))

    def test_menyatakan_diri_konseptual(self):
        teks = model3d.KETERANGAN_KONSEPTUAL.lower()
        self.assertIn("tidak berskala", teks)
        self.assertIn("bukan simulasi aliran fluida", teks)

    def test_tanpa_sumbu_berukuran(self):
        adegan = model3d.gambar(self.lapisan).layout.scene
        for sumbu in (adegan.xaxis, adegan.yaxis, adegan.zaxis):
            self.assertFalse(sumbu.visible)

    def test_tanah_dasar_ditandai_konteks(self):
        self.assertNotIn(model3d.TANAH_DASAR["nama"],
                         [lap["nama"] for lap in self.lapisan])
        label = [a.text for a in
                 model3d.gambar(self.lapisan).layout.scene.annotations]
        self.assertTrue(any("Tanah dasar" in t and "konteks" in t for t in label))

    def test_tetes_mengikuti_retensi(self):
        self.assertEqual(model3d.jumlah_tetes_tertahan(RETENSI_TERUKUR), 4)
        fig = model3d.gambar(self.lapisan, retensi_persen=RETENSI_TERUKUR)
        self.assertTrue(len(fig.frames) > 0)

    def test_tanpa_retensi_tetes_tidak_digambar(self):
        fig = model3d.gambar(self.lapisan, retensi_persen=None)
        self.assertEqual(len(fig.frames), 0)
        self.assertNotIn("tetes air", [j.name for j in fig.data])
        label = [a.text for a in fig.layout.scene.annotations]
        self.assertTrue(any("belum diketahui" in t for t in label))

    def test_angka_hanya_yang_diserahkan_pemanggil(self):
        angka = {"jatuh": "JATUH-X", "tertahan": "TAHAN-Y", "lolos": "LOLOS-Z"}
        label = [a.text for a in model3d.gambar(
            self.lapisan, retensi_persen=RETENSI_TERUKUR,
            angka=angka).layout.scene.annotations]
        for teks in angka.values():
            self.assertIn(teks, label)
        tanpa = [a.text for a in model3d.gambar(
            self.lapisan, retensi_persen=RETENSI_TERUKUR
        ).layout.scene.annotations]
        self.assertFalse(any(re.search(r"m³|liter", t) for t in tanpa),
                         "model menampilkan volume tanpa simulasi")

    def test_sorot_meredupkan_lapisan_lain(self):
        fig = model3d.gambar(self.lapisan, sorot="Zeolit")
        badan = {j.name: j.opacity for j in fig.data
                 if j.type == "mesh3d" and j.name in
                 {lap["nama"] for lap in self.lapisan}}
        self.assertGreater(badan["Zeolit"], badan["Beton poros"])

    def test_tampilan_terurai_memberi_jarak(self):
        rapat = model3d.tata_letak(self.lapisan)["lempeng"]
        urai = model3d.tata_letak(self.lapisan, terurai=True)["lempeng"]
        self.assertEqual(rapat[0]["z_bawah"], rapat[1]["z_atas"])
        self.assertGreater(urai[0]["z_bawah"], urai[1]["z_atas"])

    def test_versi_teks_memuat_fungsi_dari_naskah(self):
        teks = model3d.uraian_teks(self.lapisan, RETENSI_TERUKUR)
        for lap in self.lapisan:
            with self.subTest(lapisan=lap["nama"]):
                self.assertIn(lap["nama"], teks)
                self.assertIn(lap["fungsi"], teks)

    def test_tanpa_aset_dari_luar(self):
        """Model dibangun di tempat; tidak ada berkas atau alamat yang diunduh."""
        with io.open(BERKAS_MODEL, encoding="utf8") as f:
            isi = f.read()
        self.assertNotIn("http://", isi)
        self.assertNotIn("https://", isi)


# ═══════════ 6. antarmuka tanpa emoji ═══════════

class TanpaEmoji(unittest.TestCase):

    def test_sumber_antarmuka(self):
        berkas = [BERKAS_APLIKASI]
        for akar, _, nama in os.walk(os.path.join(AKAR, "ui")):
            if "__pycache__" in akar:
                continue
            berkas += [os.path.join(akar, n) for n in nama if n.endswith(".py")]
        for b in berkas:
            with io.open(b, encoding="utf8") as f:
                for nomor, baris in enumerate(f, start=1):
                    with self.subTest(berkas=os.path.relpath(b, AKAR), baris=nomor):
                        self.assertIsNone(EMOJI.search(baris))

    def test_layar_yang_digambar(self):
        at = jalankan_simulasi(jalankan())
        teks = [t.label for t in at.tabs]
        for jenis in ("markdown", "caption", "info", "warning", "success",
                      "error"):
            teks += [x.value for x in getattr(at, jenis)]
        for jenis in ("button", "radio", "slider", "number_input", "selectbox",
                      "checkbox", "toggle", "expander", "metric"):
            teks += [x.label for x in getattr(at, jenis)]
        for t in teks:
            self.assertIsNone(EMOJI.search(t or ""), f"emoji pada layar: {t!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
