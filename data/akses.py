"""
Lapisan akses data — satu-satunya jalan dari konstanta ke modul perhitungan.

Tujuan lapisan ini sempit dan disengaja:

  1. memberi modul perhitungan satu titik masuk yang stabil ke konstanta.py;
  2. menjaga agar nilai yang dihapus ADR-001 tidak diam-diam kembali;
  3. menyediakan provenansi siap tampil untuk antarmuka.

BUKAN tugas lapisan ini: melakukan perhitungan, menyentuh Streamlit, atau
membaca vault Obsidian. Runtime aplikasi TIDAK BOLEH bergantung pada berkas
Markdown mana pun. Vault adalah lapisan dokumentasi; hubungannya dengan kode
hanyalah string sitasi di dalam field `sumber`.
"""

from __future__ import annotations

import konstanta as _k

TERUKUR = _k.TERUKUR
LITERATUR = _k.LITERATUR
MODEL = _k.MODEL
TARGET = _k.TARGET
ASUMSI = _k.ASUMSI

#: Status yang boleh ditampilkan tanpa kualifikasi tambahan di antarmuka.
STATUS_TERPERCAYA = (TERUKUR, LITERATUR)


class NilaiDihapus(LookupError):
    """Dinaikkan bila kode mencoba memakai konstanta yang sudah dihapus ADR-001."""


def pastikan_tidak_dihapus(nama: str) -> None:
    """
    Penjaga. Panggil sebelum memperkenalkan kembali konstanta lama.

    >>> pastikan_tidak_dihapus("optimasi_material_85")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    data.akses.NilaiDihapus: 'optimasi_material_85' dihapus oleh ADR-001: ...
    """
    if nama in _k.DIHAPUS:
        raise NilaiDihapus(
            f"{nama!r} dihapus oleh ADR-001: {_k.DIHAPUS[nama].alasan}")


def besaran(nama: str) -> _k.Besaran:
    """Ambil satu Besaran berdasarkan nama konstantanya."""
    pastikan_tidak_dihapus(nama)
    obj = getattr(_k, nama, None)
    if not isinstance(obj, _k.Besaran):
        raise LookupError(f"{nama!r} bukan Besaran yang terdefinisi di konstanta.py")
    return obj


def nilai(nama: str) -> float:
    """Nilai numerik sebuah Besaran."""
    return besaran(nama).nilai


def provenans(nama: str) -> str:
    """Baris provenansi siap tempel di bawah angka pada antarmuka."""
    return besaran(nama).provenans()


def status(nama: str) -> str:
    """Status bukti sebuah Besaran."""
    return besaran(nama).status


def perlu_kualifikasi(nama: str) -> bool:
    """True bila nilai ini tidak boleh disajikan sebagai hasil tanpa penjelasan."""
    return besaran(nama).status not in STATUS_TERPERCAYA


# --------------------------------------------------------------------------
# Kumpulan data laboratorium
# --------------------------------------------------------------------------

def dataset_kuat_tekan() -> list[dict]:
    """Tiga benda uji tekan, OUTPUT3 Tabel 4.1."""
    return [dict(b) for b in _k.BENDA_UJI_TEKAN]


def dataset_retensi() -> list[dict]:
    """Tiga pengujian retensi, OUTPUT3 Tabel 4.3."""
    return [dict(u) for u in _k.UJI_RETENSI]


def lapisan_sistem() -> list[dict]:
    """Lima lapisan prototipe, OUTPUT3 Tabel 4.2."""
    return [dict(l) for l in _k.LAPISAN_SISTEM]


def sdg_didukung() -> tuple[int, ...]:
    """Set SDG final: 9, 11, 12, 13 (keputusan penulis 30 Agustus 2026)."""
    return _k.SDG_DIDUKUNG


def sdg_keterangan() -> dict[int, str]:
    return dict(_k.SDG_KETERANGAN)


# --------------------------------------------------------------------------
# Angka kunci yang boleh dipajang aplikasi
# --------------------------------------------------------------------------

def angka_kunci() -> list[dict]:
    """
    Nilai utama beserta status buktinya, untuk kartu ringkasan antarmuka.

    Hanya berisi nilai yang benar-benar didukung naskah. Klaim lama seperti
    "85% optimasi material" tidak ada di sini karena tidak ada di naskah mana pun.
    """
    daftar = [
        ("KUAT_TEKAN_7_HARI", "Kuat tekan (7 hari)", "MPa"),
        ("PERMEABILITAS", "Permeabilitas", "cm/dtk"),
        ("RETENSI_RERATA", "Retensi air", "%"),
        ("SUBSTITUSI_IPAL", "Substitusi lumpur IPAL", "%"),
    ]
    keluar = []
    for nama, label, satuan in daftar:
        b = besaran(nama)
        keluar.append(
            {
                "nama": nama,
                "label": label,
                "nilai": b.nilai,
                "satuan": satuan,
                "status": b.status,
                "provenans": b.provenans(),
                "perlu_kualifikasi": b.status not in STATUS_TERPERCAYA,
            }
        )
    return keluar


def daftar_dihapus() -> dict[str, _k.Dihapus]:
    """Konstanta yang dihapus ADR-001 beserta alasan dan pola pengenalnya."""
    return dict(_k.DIHAPUS)


def pola_dihapus() -> dict[str, tuple[str, ...]]:
    """
    Regex yang menandai nilai terhapus muncul kembali di keluaran terpuji.

    Dipakai penjaga keluaran: penjaga lama hanya menolak kode yang MEMINTA
    konstanta terhapus lewat lapisan ini, dan tidak dapat melihat nilai yang
    ditulis langsung sebagai teks tampilan.
    """
    return _k.pola_dihapus()
