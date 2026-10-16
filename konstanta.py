"""
Sumbu data AQUAPAVE — satu-satunya tempat angka boleh didefinisikan.

Setiap besaran membawa provenansinya sendiri: nilai, satuan, sumber, dan status.
Tidak ada literal angka yang boleh muncul lagi di AQUAPAVE.py.

Sumber kebenaran: OUTPUT3.docx — naskah DevICE 2026, dokumen kanonik
eksternal yang TIDAK disertakan di repositori ini. Naskah menang atas
kode (ADR-001); berkas ini menyalin angkanya, bukan menggantikannya.
Keputusan yang mendasari berkas ini:
  ADR-001 — naskah menang atas kode
  ADR-002 — tiap angka membawa status
  ADR-003 — tidak ada koefisien yang dipasang ke tiga titik data

Status:
  TERUKUR    diukur tim di laboratorium, ada di tabel naskah
  LITERATUR  dari pustaka yang disitir naskah
  MODEL      keluaran perhitungan, bukan pengukuran
  TARGET     rancangan yang belum pernah diukur
  ASUMSI     nilai kerja tanpa sumber — wajib ditandai di antarmuka
"""

from dataclasses import dataclass


TERUKUR = "terukur"
LITERATUR = "literatur"
MODEL = "model"
TARGET = "target"
ASUMSI = "asumsi"

_LABEL_STATUS = {
    TERUKUR: "Hasil uji laboratorium",
    LITERATUR: "Nilai dari pustaka",
    MODEL: "Keluaran model — bukan hasil uji",
    TARGET: "Target rancangan — belum diukur",
    ASUMSI: "Asumsi kerja — belum bersumber",
}


@dataclass(frozen=True)
class Besaran:
    """Satu angka beserta asal-usulnya."""

    nilai: float
    satuan: str
    sumber: str
    status: str
    catatan: str = ""

    @property
    def terpercaya(self) -> bool:
        """Boleh dipakai untuk klaim di hadapan juri tanpa kualifikasi."""
        return self.status in (TERUKUR, LITERATUR)

    @property
    def label_status(self) -> str:
        return _LABEL_STATUS[self.status]

    def provenans(self) -> str:
        """Baris pendek untuk ditempel di bawah angka di antarmuka."""
        dasar = f"{self.label_status} · {self.sumber}"
        return f"{dasar} · {self.catatan}" if self.catatan else dasar

    def __format__(self, spec: str) -> str:
        return format(self.nilai, spec or "")


# ═══════════════════════════════════════════════════════════════════════════
# RANCANGAN CAMPURAN — OUTPUT3 §3.3
# Pengikat : agregat = 1 : 3. Tanpa pasir.
# ═══════════════════════════════════════════════════════════════════════════

RASIO_PENGIKAT_AGREGAT = Besaran(
    3.0, "kg agregat per kg pengikat", "Hasil Uji", TERUKUR,
    "1 kg pengikat : 3 kg batu sirtu",
)

SUBSTITUSI_IPAL = Besaran(
    15.0, "%", "Hasil Uji", TERUKUR,
    "0,85 kg semen + 0,15 kg lumpur IPAL per kg pengikat",
)

FAKTOR_AIR_PENGIKAT = Besaran(
    0.40, "-", "Hasil Uji", TERUKUR,
    "±0,40 liter air per kg pengikat",
)

AGREGAT_UKURAN_MIN = Besaran(4.75, "mm", "Hasil Uji", TERUKUR)
AGREGAT_UKURAN_MAKS = Besaran(12.5, "mm", "Hasil Uji", TERUKUR)

# Naskah tidak menyebut berat satuan. Berat benda uji justru memberi ~1.279
# kg/m3 bila silinder benar-benar 150x300 mm — belum terkonfirmasi.
BERAT_SATUAN_BETON = Besaran(
    1850.0, "kg/m³", "tidak ada di Hasil Uji", ASUMSI,
    "berat benda uji justru menyiratkan ~1.279 kg/m³; tinggi silinder belum dikonfirmasi",
)


# ═══════════════════════════════════════════════════════════════════════════
# KUAT TEKAN — OUTPUT3 Tabel 4.1
# Diuji umur 7 hari, dikonversi ke 14 hari. BUKAN 28 hari.
# ═══════════════════════════════════════════════════════════════════════════

UMUR_UJI_HARI = Besaran(7, "hari", "Hasil Uji", TERUKUR)
UMUR_KONVERSI_HARI = Besaran(14, "hari", "Hasil Uji", TERUKUR)

LUAS_SILINDER = Besaran(
    0.017671, "m²", "Hasil Uji", TERUKUR,
    "silinder Ø150 mm",
)

# Pembagi, bukan pengali: f'c(14) = f'c(7) / 0,879.
FAKTOR_KONVERSI_7_KE_14 = Besaran(
    0.879, "-", "Hasil Uji", ASUMSI,
    "TURUNAN MELINGKAR — Equation_Format_Reference.jpeg menuliskan "
    "FK = 15,00/13,19 ≈ 1,137 lalu memakainya untuk menghasilkan 15,00 MPa. "
    "Hasil Uji tidak menyitir sumber mana pun. Lihat ADR-005",
)

# Tabel faktor umur PBI 1971 (0,65 / 0,88 / 0,95 / 1,00) adalah rasio terhadap
# kuat tekan 28 hari, dan itulah yang diterapkan AQUAPAVE.py secara matematis
# benar. Namun naskah TIDAK menyitirnya, sehingga provenansi primer 0,879 tetap
# terbuka: implementasinya konsisten dengan model faktor-umur relatif-28-hari,
# tetapi sumber aslinya belum dapat ditelusuri. Lihat ADR-005.

# Tabel 4.1 — tiga benda uji, satu rancangan campuran.
# Ini REPLIKASI, bukan rancangan percobaan: tidak ada kurva yang bisa dipasang.
BENDA_UJI_TEKAN = (
    {"nama": "BU-1", "beban_kN": 235.2, "berat_kg": 6.45},
    {"nama": "BU-2", "beban_kN": 233.4, "berat_kg": 6.80},
    {"nama": "BU-3", "beban_kN": 230.4, "berat_kg": 7.10},
)

KUAT_TEKAN_7_HARI = Besaran(
    13.19, "MPa", "Hasil Uji", TERUKUR,
    "rerata tiga benda uji",
)

# HASIL UTAMA kuat tekan adalah KUAT_TEKAN_7_HARI (13,19 MPa, terukur langsung).
# Nilai 14 hari di bawah dipertahankan sebagai rekam jejak, TIDAK dipakai sebagai
# hasil utama, dan tidak boleh muncul di Abstrak atau kesimpulan (ADR-005).
KUAT_TEKAN_14_HARI = Besaran(
    15.00, "MPa", "Hasil Uji", ASUMSI,
    "TIDAK DIPAKAI sebagai hasil utama — turunan melingkar dari faktor yang "
    "justru diturunkan dari nilai ini. Diturunkan dari MODEL ke ASUMSI",
)


# ═══════════════════════════════════════════════════════════════════════════
# RETENSI AIR — OUTPUT3 Tabel 4.3
# Simulasi curah hujan, tiga pengulangan, masukan 1.000 ml.
# ═══════════════════════════════════════════════════════════════════════════

UJI_RETENSI = (
    {"nama": "Uji 1", "input_ml": 1000, "output_ml": 600},
    {"nama": "Uji 2", "input_ml": 1000, "output_ml": 590},
    {"nama": "Uji 3", "input_ml": 1000, "output_ml": 610},
)

RETENSI_RERATA = Besaran(
    40.0, "%", "Hasil Uji", TERUKUR,
    "nilai terkoreksi sesuai keputusan penulis 30 Agustus 2026 dan sudah "
    "diterapkan ke Hasil Uji. Rerata aritmetik ketiga uji (40,0 / 41,0 / 39,0) "
    "dan perbandingan 400 ml terhadap 1.000 ml keduanya memberi 40,0%. "
    "Nilai 39,7% pada pelaporan sebelumnya adalah ketidaksesuaian penyalinan",
)

# Nilai lama dipertahankan sebagai rekam jejak, BUKAN untuk dipakai menghitung.
RETENSI_RERATA_PELAPORAN_LAMA = 39.7

RETENSI_SIMPANGAN_BAKU = Besaran(1.0, "%", "Hasil Uji", TERUKUR)
RETENSI_KOEF_VARIASI = Besaran(2.5, "%", "Hasil Uji", TERUKUR)

TARGET_REDUKSI_LIMPASAN_MIN = Besaran(
    35.0, "%", "Hasil Uji", ASUMSI,
    "dasar target belum dirujuk — [AUTHOR INPUT REQUIRED] di Hasil Uji",
)
TARGET_REDUKSI_LIMPASAN_MAKS = Besaran(
    55.0, "%", "Hasil Uji", ASUMSI,
    "dasar target belum dirujuk — [AUTHOR INPUT REQUIRED] di Hasil Uji",
)


# ═══════════════════════════════════════════════════════════════════════════
# PERMEABILITAS — OUTPUT3 §4.5 · metode CONSTANT HEAD (dikonfirmasi tim, 2026-08-30)
#
# Riwayat penilaian — jangan dihapus, lihat ADR-006:
#   1. Draf naskah (§3.5, Abstrak) menyebut falling head. Di bawah anggapan itu
#      persamaan tampak keliru dan nilai k sempat dinilai "sirkular".
#   2. Tim eksperimen mengonfirmasi metode sebenarnya CONSTANT HEAD.
#   3. Di bawah constant head, persamaannya benar dan nilainya reproducible.
#      Penilaian "sirkular" DIBATALKAN — pembatalan A hanyalah hukum Darcy,
#      karena v sudah merupakan fluks per satuan luas.
#
# Notasi (koreksi 2026-08-30): Q adalah DEBIT VOLUMETRIK (cm³/detik), sehingga
# waktu sudah terkandung di dalam Q dan TIDAK boleh dibagikan lagi:
#       benar  : k = Q·L / (A·h)        dengan Q debit  (cm³/detik)
#       benar  : k = V·L / (A·h·t)      dengan V volume (cm³) selama t detik
#       keliru : k = Q·L / (A·h·t)      dengan Q debit  -> satuan jadi cm/detik²
# Kedua bentuk yang benar identik secara aljabar; AQUAPAVE.py memakai bentuk
# volume dan sudah benar (diaudit 2026-08-30, tanpa perubahan kode).
# ═══════════════════════════════════════════════════════════════════════════

PERM_METODE = "Constant head (tinggi tekan tetap)"
PERM_METODE_SUMBER = "konfirmasi tim eksperimen, 2026-08-30"

PERM_TEBAL_SAMPEL = Besaran(2.0, "cm", "Hasil Uji", TERUKUR)
PERM_LUAS_PENAMPANG = Besaran(
    225.0, "cm²", "Hasil Uji", TERUKUR,
    "benda uji persegi 15 × 15 cm — bukan silinder",
)
PERM_TINGGI_TEKANAN = Besaran(6.0, "cm", "Hasil Uji", TERUKUR)

# Gradien hidraulik i = h/L = 3,0 (turunan, bukan masukan terpisah).
PERM_GRADIEN_HIDRAULIK = Besaran(
    3.0, "-", "turunan dari h/L", MODEL,
    "i = 6/2; dipakai pada hubungan Darcy v = k·i",
)

PERM_KECEPATAN_ALIRAN = Besaran(
    5.0, "cm/detik",
    "Hasil Uji; konfirmasi tim eksperimen 2026-08-30 — "
    "catatan pengukuran mentah tidak tersedia",
    TERUKUR,
    "diukur sebagai v = s/t — jarak tempuh air menembus benda uji dibagi waktu "
    "yang dicatat dengan stopwatch. Status TERUKUR tetap berlaku karena besaran "
    "ini memang diukur tim di laboratorium; ketiadaan catatan mentah s dan t "
    "adalah celah dokumentasi, bukan alasan menurunkan status metodenya",
)

PERM_DEBIT = Besaran(
    1125.0, "cm³/detik", "Hasil Uji", MODEL,
    "debit volumetrik Q = v × A; turunan dari kecepatan terukur",
)

PERMEABILITAS = Besaran(
    1.667, "cm/detik", "Hasil Uji", TERUKUR,
    "hasil uji constant head; dihitung dari kecepatan terukur dan geometri "
    "benda uji melalui k = Q·L/(A·h), setara k = v·L/h. Nilai tidak diubah",
)

# Satu-satunya pembanding permeabilitas yang benar-benar disitir naskah.
PERM_BETON_KONVENSIONAL = Besaran(
    0.01, "cm/detik", "ACI Committee 522 (2020)", LITERATUR,
    "batas atas; perkerasan konvensional bersifat impermeabel",
)

PERM_ZHU_MIN = Besaran(
    0.574, "cm/detik", "Zhu et al. (2020)", LITERATUR,
    "beton berpori agregat daur ulang berserat, porositas rancangan 15%",
)
PERM_ZHU_MAKS = Besaran(
    0.764, "cm/detik", "Zhu et al. (2020)", LITERATUR,
)


# ═══════════════════════════════════════════════════════════════════════════
# POROSITAS — target rancangan, TIDAK PERNAH DIUKUR (OUTPUT3 §4.3)
# ═══════════════════════════════════════════════════════════════════════════

POROSITAS_TARGET_MIN = Besaran(18.0, "%", "Hasil Uji", TARGET)
POROSITAS_TARGET_MAKS = Besaran(25.0, "%", "Hasil Uji", TARGET)

# Naskah §4.3: "Draf belum memuat hasil pengukuran porositas benda uji."
POROSITAS_TERUKUR = None


# ═══════════════════════════════════════════════════════════════════════════
# SISTEM LAPISAN — OUTPUT3 Tabel 4.2
# Hebel dan zeolit adalah LAPISAN, bukan komponen campuran beton.
# ═══════════════════════════════════════════════════════════════════════════

LAPISAN_SISTEM = (
    {
        "nama": "Beton poros",
        "fungsi": "Menerima air hujan dan mengalirkannya melalui rongga beton. "
                  "Substitusi lumpur IPAL 15%, porositas rancangan 18–25%.",
    },
    {
        "nama": "Batu sirtu 4–12 mm",
        "fungsi": "Filtrasi sekaligus pendistribusi aliran menuju media retensi.",
    },
    {
        "nama": "Hebel AAC",
        "fungsi": "Media retensi; menyimpan air sementara melalui struktur berongga.",
    },
    {
        "nama": "Zeolit",
        "fungsi": "Menambah kapasitas retensi; menahan air pada mikropori "
                  "sehingga pelepasan berlangsung lebih lambat.",
    },
    {
        "nama": "Pipa overflow",
        "fungsi": "Mengalirkan kelebihan air ke drainase saat kapasitas retensi penuh.",
    },
)


# ═══════════════════════════════════════════════════════════════════════════
# EMISI CO2 — OUTPUT3 §1.1
# ═══════════════════════════════════════════════════════════════════════════

CO2_PER_TON_SEMEN_MIN = Besaran(
    0.8, "ton CO₂/ton semen",
    "Scrivener et al. (2018); Habert et al. (2020)", LITERATUR,
)
CO2_PER_TON_SEMEN_MAKS = Besaran(
    0.9, "ton CO₂/ton semen",
    "Scrivener et al. (2018); Habert et al. (2020)", LITERATUR,
)

CO2_PER_TON_IPAL = Besaran(
    0.05, "ton CO₂/ton", "tidak ada di Hasil Uji", ASUMSI,
    "karbon tertanam lumpur IPAL diperkirakan sangat kecil, belum bersumber",
)

PANGSA_EMISI_SEMEN_GLOBAL = Besaran(
    7.5, "%", "Scrivener et al. (2018)", LITERATUR,
    "rentang 7–8% emisi CO₂ global",
)


# ═══════════════════════════════════════════════════════════════════════════
# AMBANG PUSTAKA — pengganti ambang karangan yang dihapus
# ═══════════════════════════════════════════════════════════════════════════

AMBANG_LALU_LINTAS_RINGAN = Besaran(
    5.0, "MPa", "Govedarica et al. (2022)", LITERATUR,
    "ambang minimum kuat tekan untuk aplikasi lalu lintas ringan",
)

NATARAJA_KUAT_TEKAN_MIN = Besaran(
    16.0, "MPa", "Nataraja et al. (2023)", LITERATUR,
    "beton berpori tanpa substitusi, umur 7 hari",
)
NATARAJA_KUAT_TEKAN_MAKS = Besaran(
    35.5, "MPa", "Nataraja et al. (2023)", LITERATUR,
)


# ═══════════════════════════════════════════════════════════════════════════
# SKALA HIDROLOGI — OUTPUT3 §4.6
# ═══════════════════════════════════════════════════════════════════════════

SKALA_LUAS_ACUAN = Besaran(1000.0, "m²", "Hasil Uji", TERUKUR)
SKALA_INTENSITAS_ACUAN = Besaran(50.0, "mm/jam", "Hasil Uji", TERUKUR)

# 1.000 m2 x 50 mm/jam = 50.000 L/jam yang JATUH; 40% darinya = 20.000 L
# yang TERTAHAN. Naskah menandai perlunya kejelasan ini.
SKALA_AIR_JATUH = Besaran(50000.0, "liter/jam", "Hasil Uji", MODEL,
                          "turunan: luas × intensitas")
SKALA_AIR_TERTAHAN = Besaran(20000.0, "liter/jam", "Hasil Uji", MODEL,
                             "turunan: 40% dari air yang jatuh, bukan total curah hujan")


# ═══════════════════════════════════════════════════════════════════════════
# SDG — Abstrak OUTPUT3 menyebut 3, 9, 11, 12; §1.1 menyebut 9, 11, 12, 13.
# Abstrak adalah revisi terakhir, jadi itu yang dipakai.
# ═══════════════════════════════════════════════════════════════════════════

SDG_DIDUKUNG = (9, 11, 12, 13)
SDG_KETERANGAN = {
    9: "Industri, Inovasi, dan Infrastruktur — infrastruktur inovatif dan berkelanjutan",
    11: "Kota dan Permukiman Berkelanjutan — ketahanan kota terhadap banjir",
    12: "Konsumsi dan Produksi yang Bertanggung Jawab — pemanfaatan limbah",
    13: "Penanganan Perubahan Iklim — adaptasi terhadap dampak terkait banjir",
}
SDG_CATATAN = (
    "Keputusan penulis 2026-08-30: set final adalah SDG 9, 11, 12, 13. "
    "SDG 3 dihapus sebagai keselarasan utama karena penelitian tidak mengukur "
    "paparan silika, silikosis, maupun luaran kesehatan secara langsung. "
    "Konteks kesehatan kerja boleh dibahas bila disitir dengan benar, tetapi "
    "bukan sebagai luaran penelitian yang ditunjukkan."
)


# ═══════════════════════════════════════════════════════════════════════════
# DIHAPUS PADA FASE 01 — jangan dihidupkan kembali tanpa sumber
#
# Setiap entri membawa dua hal:
#
#   alasan  mengapa nilai itu dihapus (ADR-001)
#   pola    regex yang menandai nilainya HIDUP KEMBALI di keluaran terpuji
#
# `pola` ada karena penjaga lama hanya menutup satu pintu. Ia menolak kode yang
# MEMINTA konstanta terhapus lewat data/akses.py, tetapi tidak dapat melihat
# nilai yang ditulis langsung sebagai teks tampilan. Persis lewat pintu itulah
# empat nilai kembali ke tabel dasbor (temuan S6-A).
#
# Pola dipakai uji untuk memeriksa keluaran yang benar-benar dirender, bukan
# kode sumbernya: dokumentasi, komentar, dan kalimat yang MENJELASKAN sebuah
# penghapusan tetap boleh menyebut angkanya.
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Dihapus:
    """Satu nilai yang dihapus, beserta cara mengenalinya bila kembali."""

    alasan: str
    pola: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.alasan


DIHAPUS = {
    "ambang_permeabilitas_045": Dihapus(
        "Tidak ada di Hasil Uji. Satu-satunya nilai ACI 522 yang disitir adalah "
        "<0,01 cm/dtk untuk beton konvensional.",
        (r"0[,.]45\s*cm",),
    ),
    "target_permeabilitas_060": Dihapus(
        "Tidak ada di Hasil Uji.",
        (r"0[,.]60\s*cm", r"0[,.]75\s*cm"),
    ),
    "aci_522_014": Dihapus(
        "Sitasi keliru — angka ini tidak ada di Hasil Uji.",
        (r"0[,.]14\s*cm", r"ACI[^\n]{0,24}0[,.]14"),
    ),
    "sni_min_10_mpa": Dihapus(
        "Ambang lalu lintas ringan adalah 5 MPa (Govedarica et al., 2022), dan "
        "sumbernya bukan SNI.",
        (r"SNI[^\n]{0,40}10\s*MPa", r"min\.?\s*10\s*MPa"),
    ),
    "porositas_dasar_215": Dihapus(
        "Porositas tidak pernah diukur (§4.3) — tidak ada yang bisa dikalibrasi.",
        (r"21[,.]5\s*%",),
    ),
    "koef_porositas_ipal_hebel_fab": Dihapus("Tiga koefisien tanpa sumber."),
    "koef_permeabilitas_polinom": Dihapus(
        "Skala salah dan ambangnya sendiri tidak ada."),
    "kuat_tekan_205_035": Dihapus(
        "Tiga ulangan satu campuran tidak bisa menghasilkan kurva.",
        (r"20[,.]5\s*MPa", r"0[,.]35\s*MPa"),
    ),
    "hukuman_ipal_di_atas_15": Dihapus(
        "Hasil Uji hanya menguji satu tingkat substitusi."),
    "porositas_lapisan_zeolit_025": Dihapus(
        "Tanpa sumber; diganti neraca massa antar lapisan.",
        (r"porositas lapisan[^\n]{0,20}0[,.]25",),
    ),
    "optimasi_material_85": Dihapus(
        "Tidak ada di versi Hasil Uji. Hasil Uji menyebut 25% (§1.1) dan "
        "SUBJECT3 menyebut 35%, keduanya juga belum terbukti.",
        (r"optimasi material[^\n]{0,16}85", r"85\s*%[^\n]{0,16}optimasi"),
    ),
    "uji_manual_20_dan_005_m3": Dihapus("Rantai perhitungan di balik klaim 85%."),
}


def pola_dihapus() -> dict[str, tuple[str, ...]]:
    """Nama -> regex yang menandai nilai terhapus muncul lagi di layar."""
    return {n: d.pola for n, d in DIHAPUS.items() if d.pola}


def daftar_provenans() -> list[tuple[str, Besaran]]:
    """Semua besaran beserta namanya — untuk lampiran dan halaman provenansi."""
    return [
        (nama, obj) for nama, obj in sorted(globals().items())
        if isinstance(obj, Besaran)
    ]


def besaran_bermasalah() -> list[tuple[str, Besaran]]:
    """Besaran yang belum boleh dipakai sebagai klaim tanpa kualifikasi."""
    return [(n, b) for n, b in daftar_provenans() if not b.terpercaya]
