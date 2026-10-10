"""
Permeabilitas beton poros — metode CONSTANT HEAD.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

Metode fisik dikonfirmasi tim eksperimen pada 30 Agustus 2026 sebagai
constant head (ADR-006). Persamaan didokumentasikan dengan rujukan
SNI 2435:2008 pada OUTPUT3 Persamaan 3.4.

CATATAN KEPATUHAN — kesesuaian peralatan dan prosedur terhadap seluruh
ketentuan SNI 2435:2008 BELUM diverifikasi butir demi butir. Modul ini
menerapkan persamaannya, bukan menyatakan kepatuhan penuh terhadap standar.

DUA BENTUK YANG SETARA
----------------------
Perbedaannya hanya di mana waktu berada, dan keduanya identik secara aljabar.

  bentuk volume   : k = V * L / (A * h * t)     V dalam cm3, t dalam detik
  bentuk debit    : k = Q * L / (A * h)         Q dalam cm3/detik

Karena Q sudah mengandung waktu, faktor t TIDAK boleh dibagikan lagi pada
bentuk debit. Menuliskan k = Q*L/(A*h*t) dengan Q berupa debit menghasilkan
satuan cm/detik^2 dan itu keliru.
"""

from __future__ import annotations

import math
from typing import Sequence

# Konfigurasi laboratorium yang dikonfirmasi (OUTPUT3 §4.5). Dipakai sebagai
# acuan reproduksi pada validation/ DAN sebagai nilai bawaan widget pada
# ui/tabs/permeabilitas.py. Nilainya menyalin besaran kanonik di konstanta.py.
# Kesetaraannya terhadap konstanta.py dijaga validation/test_duplikasi_kanonik.py.
LAB_TEBAL_CM = 2.0
LAB_LUAS_CM2 = 225.0          # benda uji persegi 15 x 15 cm
LAB_TINGGI_TEKAN_CM = 6.0
LAB_KECEPATAN_CM_PER_DETIK = 5.0
LAB_K_CM_PER_DETIK = 1.667


def _positif(nama: str, nilai: float) -> float:
    if nilai is None:
        raise ValueError(f"{nama} wajib diisi")
    nilai = float(nilai)
    if not math.isfinite(nilai):
        raise ValueError(f"{nama} harus berupa bilangan berhingga")
    if nilai <= 0:
        raise ValueError(f"{nama} harus lebih besar dari nol, diterima {nilai}")
    return nilai


def debit_dari_kecepatan(kecepatan_cm_per_detik: float, luas_cm2: float) -> float:
    """Debit volumetrik Q = v * A, dalam cm3/detik."""
    v = _positif("kecepatan aliran", kecepatan_cm_per_detik)
    a = _positif("luas penampang", luas_cm2)
    return v * a


def gradien_hidraulik(tinggi_tekan_cm: float, tebal_cm: float) -> float:
    """Gradien hidraulik i = h / L, tanpa satuan."""
    h = _positif("tinggi tekan", tinggi_tekan_cm)
    L = _positif("tebal benda uji", tebal_cm)
    return h / L


def koefisien_dari_debit(
    debit_cm3_per_detik: float,
    tebal_cm: float,
    luas_cm2: float,
    tinggi_tekan_cm: float,
) -> float:
    """
    k = Q * L / (A * h), dalam cm/detik. Q adalah DEBIT (cm3/detik).

    Tidak ada pembagi waktu di sini: waktu sudah terkandung di dalam Q.

    >>> round(koefisien_dari_debit(1125.0, 2.0, 225.0, 6.0), 4)
    1.6667
    """
    Q = _positif("debit", debit_cm3_per_detik)
    L = _positif("tebal benda uji", tebal_cm)
    A = _positif("luas penampang", luas_cm2)
    h = _positif("tinggi tekan", tinggi_tekan_cm)
    return (Q * L) / (A * h)


def koefisien_dari_volume(
    volume_cm3: float,
    tebal_cm: float,
    luas_cm2: float,
    tinggi_tekan_cm: float,
    waktu_detik: float,
) -> float:
    """
    k = V * L / (A * h * t), dalam cm/detik. V adalah VOLUME terkumpul (cm3)
    selama t detik.

    Bentuk inilah yang dipakai antarmuka lama AQUAPAVE, dan hasilnya identik
    dengan bentuk debit untuk eksperimen yang sama.

    >>> round(koefisien_dari_volume(1125.0, 2.0, 225.0, 6.0, 1.0), 4)
    1.6667
    >>> round(koefisien_dari_volume(67500.0, 2.0, 225.0, 6.0, 60.0), 4)
    1.6667
    """
    V = _positif("volume air", volume_cm3)
    t = _positif("waktu pengujian", waktu_detik)
    return koefisien_dari_debit(V / t, tebal_cm, luas_cm2, tinggi_tekan_cm)


def koefisien_dari_kecepatan(
    kecepatan_cm_per_detik: float,
    tebal_cm: float,
    tinggi_tekan_cm: float,
) -> float:
    """
    Bentuk ringkas k = v * L / h, dalam cm/detik.

    Luas penampang tidak muncul karena v sudah merupakan fluks per satuan luas.
    Ini bukan kejanggalan melainkan hukum Darcy: v = k * i dengan i = h / L.

    >>> round(koefisien_dari_kecepatan(5.0, 2.0, 6.0), 4)
    1.6667
    """
    v = _positif("kecepatan aliran", kecepatan_cm_per_detik)
    L = _positif("tebal benda uji", tebal_cm)
    h = _positif("tinggi tekan", tinggi_tekan_cm)
    return (v * L) / h


def ringkasan(nilai_k: Sequence[float]) -> dict:
    """Rata-rata, simpangan baku populasi, dan koefisien variasi dari sederet k."""
    nilai = [float(x) for x in nilai_k]
    if not nilai:
        raise ValueError("daftar nilai k kosong")
    n = len(nilai)
    rerata = sum(nilai) / n
    if n == 1:
        simpangan = 0.0
    else:
        simpangan = math.sqrt(sum((x - rerata) ** 2 for x in nilai) / n)
    cv = (simpangan / rerata * 100.0) if rerata else 0.0
    return {"n": n, "rerata": rerata, "simpangan_baku": simpangan, "cv_persen": cv}


def pembanding_literatur() -> list[dict]:
    """
    Nilai pembanding yang BENAR-BENAR disitir naskah. Bukan ambang kelulusan.

    Ambang 0,45 cm/detik dan target 0,60 cm/detik yang dipakai aplikasi lama
    tidak ada di versi naskah mana pun dan telah dihapus (ADR-001).
    """
    return [
        {
            "nama": "Beton konvensional (impermeabel)",
            "nilai": 0.01,
            "satuan": "cm/detik",
            "sifat": "batas atas",
            "sumber": "ACI Committee 522 (2020) via OUTPUT3 §1.1",
        },
        {
            "nama": "Beton berpori agregat daur ulang berserat",
            "nilai": 0.574,
            "satuan": "cm/detik",
            "sifat": "batas bawah rentang",
            "sumber": "Zhu et al. (2020) via OUTPUT3 §2.2",
        },
        {
            "nama": "Beton berpori agregat daur ulang berserat",
            "nilai": 0.764,
            "satuan": "cm/detik",
            "sifat": "batas atas rentang",
            "sumber": "Zhu et al. (2020) via OUTPUT3 §2.2",
        },
    ]
