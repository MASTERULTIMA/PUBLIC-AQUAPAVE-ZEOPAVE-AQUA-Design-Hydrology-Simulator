"""
Keadaan skenario — koleksi skenario untuk satu sesi.

Modul ini boleh mengimpor Streamlit karena berada DI ATAS core/ dalam hierarki
lapisan; core/ sendiri tetap murni. Seluruh fungsi menerima `st` sebagai
argumen, sehingga dapat diuji tanpa menjalankan Streamlit sama sekali.

SESI SAJA. Tidak ada penyimpanan ke berkas maupun basis data. Menutup peramban
berarti kehilangan skenario kustom, dan itu memang perilaku yang diinginkan
pada tahap ini.

IDENTITAS KONFIGURASI PENELITIAN
--------------------------------
Hasil pengukuran laboratorium melekat pada **konfigurasi yang diuji secara
utuh**, bukan pada satu angka saja. Karena itu kecocokan terhadap acuan
ditentukan oleh perbandingan terstruktur atas seluruh parameter yang
mendefinisikan komposisi uji — bukan oleh satu bendera boolean yang hanya
melihat persentase substitusi.

Perbandingan dilakukan parameter demi parameter dan dapat ditampilkan apa
adanya kepada pengguna, sehingga alasan sebuah skenario dianggap kustom selalu
terlihat. Tidak ada hashing: yang dibutuhkan adalah penjelasan, bukan sidik jari.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

import konstanta as _k

#: Satu kunci di st.session_state untuk seluruh koleksi.
KUNCI = "aquapave_koleksi"

#: Nama skenario acuan.
ACUAN = "ACUAN"

#: Nama skenario kustom yang tersedia, berurutan.
NAMA_KUSTOM = ("A", "B", "C")

# Nilai acuan penelitian (OUTPUT3 §3.3).
ACUAN_SUBSTITUSI_IPAL = float(_k.SUBSTITUSI_IPAL.nilai)
ACUAN_FAKTOR_AIR_PENGIKAT = float(_k.FAKTOR_AIR_PENGIKAT.nilai)
ACUAN_RASIO_AGREGAT = float(_k.RASIO_PENGIKAT_AGREGAT.nilai)

#: Parameter yang MENDEFINISIKAN konfigurasi uji laboratorium.
#: Hanya perbedaan pada parameter inilah yang memutus pewarisan hasil ukur.
#: Luas area, intensitas hujan, dan faktor emisi TIDAK termasuk: mengubahnya
#: tidak mengubah komposisi yang dicetak dan diuji.
PARAMETER_KONFIGURASI_UJI: tuple[tuple[str, str, float], ...] = (
    ("substitusi_ipal_persen", "Substitusi lumpur IPAL (%)", 1e-9),
    ("faktor_air_pengikat", "Faktor air-pengikat", 1e-9),
    ("rasio_agregat", "Rasio agregat terhadap pengikat", 1e-9),
)


@dataclass
class Skenario:
    """Parameter rancangan satu skenario."""

    # --- komposisi: mendefinisikan konfigurasi uji ---
    substitusi_ipal_persen: float = ACUAN_SUBSTITUSI_IPAL
    faktor_air_pengikat: float = ACUAN_FAKTOR_AIR_PENGIKAT
    rasio_agregat: float = ACUAN_RASIO_AGREGAT

    # --- lokasi: tidak mendefinisikan konfigurasi uji ---
    luas_area_m2: float = 1000.0
    intensitas_hujan_mm_per_jam: float = 50.0
    durasi_hujan_jam: float = 1.0

    # --- faktor emisi dan volume: tidak mendefinisikan konfigurasi uji ---
    co2_per_ton_semen: float = 0.85
    co2_per_ton_ipal: float = float(_k.CO2_PER_TON_IPAL.nilai)
    total_pengikat_ton: float = 10.0
    volume_adukan_m3: float = 1.0
    berat_satuan_kg_m3: float = 1850.0

    def sebagai_dict(self) -> dict:
        return asdict(self)


def acuan_penelitian() -> Skenario:
    """Skenario yang persis mengikuti komposisi yang diuji laboratorium."""
    return Skenario()


# ─────────────────────── identitas konfigurasi ───────────────────────

def bandingkan_konfigurasi(sk: Skenario, acuan: Skenario | None = None) -> list[dict]:
    """
    Perbandingan terstruktur parameter demi parameter terhadap acuan.

    Mengembalikan satu baris per parameter, sehingga antarmuka dapat
    menjelaskan **mengapa** sebuah skenario dianggap kustom.

    >>> [b["cocok"] for b in bandingkan_konfigurasi(acuan_penelitian())]
    [True, True, True]
    """
    ref = acuan or acuan_penelitian()
    baris = []
    for nama, label, toleransi in PARAMETER_KONFIGURASI_UJI:
        nilai = getattr(sk, nama)
        nilai_acuan = getattr(ref, nama)
        baris.append({
            "parameter": nama,
            "label": label,
            "nilai": nilai,
            "nilai_acuan": nilai_acuan,
            "cocok": abs(float(nilai) - float(nilai_acuan)) <= toleransi,
        })
    return baris


def cocok_konfigurasi_uji(sk: Skenario, acuan: Skenario | None = None) -> bool:
    """True bila SELURUH parameter komposisi sama dengan konfigurasi yang diuji."""
    return all(b["cocok"] for b in bandingkan_konfigurasi(sk, acuan))


def alasan_berbeda(sk: Skenario, acuan: Skenario | None = None) -> list[str]:
    """Daftar parameter yang membuat skenario ini berbeda dari acuan."""
    return [
        f"{b['label']}: {b['nilai']:g} (acuan {b['nilai_acuan']:g})"
        for b in bandingkan_konfigurasi(sk, acuan)
        if not b["cocok"]
    ]


# ─────────────────────────── koleksi ───────────────────────────

@dataclass
class Koleksi:
    """Kumpulan skenario satu sesi. Acuan selalu ada dan tidak dapat diubah."""

    kustom: dict[str, Skenario] = field(default_factory=dict)
    aktif: str = ACUAN

    @property
    def acuan(self) -> Skenario:
        """Acuan dibentuk ulang setiap kali diakses, sehingga mustahil termutasi."""
        return acuan_penelitian()

    def nama_terpakai(self) -> list[str]:
        return [ACUAN] + [n for n in NAMA_KUSTOM if n in self.kustom]

    def ambil(self, nama: str) -> Skenario:
        if nama == ACUAN:
            return self.acuan
        if nama not in self.kustom:
            raise KeyError(f"skenario {nama!r} tidak ada")
        return self.kustom[nama]

    def nama_berikutnya(self) -> str | None:
        for n in NAMA_KUSTOM:
            if n not in self.kustom:
                return n
        return None

    def penuh(self) -> bool:
        return self.nama_berikutnya() is None


# ─────────────────────── operasi session_state ───────────────────────

def muat(st) -> Koleksi:
    """Ambil koleksi dari session_state, buat bila belum ada."""
    if KUNCI not in st.session_state:
        st.session_state[KUNCI] = Koleksi()
    return st.session_state[KUNCI]


def skenario_aktif(st) -> Skenario:
    """Skenario yang sedang dipilih."""
    k = muat(st)
    return k.ambil(k.aktif)


def pilih(st, nama: str) -> Koleksi:
    k = muat(st)
    if nama != ACUAN and nama not in k.kustom:
        raise KeyError(f"skenario {nama!r} tidak ada")
    k.aktif = nama
    st.session_state[KUNCI] = k
    return k


def tambah_kustom(st, dari: str | None = None) -> str:
    """
    Tambahkan skenario kustom baru, disalin dari `dari` (bawaan: acuan).

    Mengembalikan nama skenario baru. Menaikkan RuntimeError bila slot penuh.
    """
    k = muat(st)
    nama = k.nama_berikutnya()
    if nama is None:
        raise RuntimeError(
            f"slot skenario kustom penuh (maksimum {len(NAMA_KUSTOM)})"
        )
    sumber = k.ambil(dari) if dari else k.acuan
    k.kustom[nama] = replace(sumber)
    k.aktif = nama
    st.session_state[KUNCI] = k
    return nama


def hapus_kustom(st, nama: str) -> Koleksi:
    """Hapus satu skenario kustom. Acuan tidak dapat dihapus."""
    if nama == ACUAN:
        raise ValueError("konfigurasi acuan penelitian tidak dapat dihapus")
    k = muat(st)
    if nama not in k.kustom:
        raise KeyError(f"skenario {nama!r} tidak ada")
    del k.kustom[nama]
    if k.aktif == nama:
        k.aktif = ACUAN
    st.session_state[KUNCI] = k
    return k


def perbarui_aktif(st, **bidang) -> Skenario:
    """
    Perbarui skenario yang sedang aktif.

    Menaikkan ValueError bila yang aktif adalah acuan penelitian: hasil
    pengukuran melekat pada konfigurasi itu, sehingga ia tidak boleh berubah.
    """
    k = muat(st)
    if k.aktif == ACUAN:
        raise ValueError(
            "konfigurasi acuan penelitian tidak dapat diubah — "
            "buat skenario kustom terlebih dahulu"
        )
    s = k.kustom[k.aktif]
    for nama, nilai in bidang.items():
        if not hasattr(s, nama):
            raise AttributeError(f"Skenario tidak memiliki bidang {nama!r}")
        setattr(s, nama, nilai)
    st.session_state[KUNCI] = k
    return s


def pulihkan_acuan(st) -> Koleksi:
    """Kembali ke konfigurasi acuan penelitian sebagai skenario aktif."""
    k = muat(st)
    k.aktif = ACUAN
    st.session_state[KUNCI] = k
    return k
