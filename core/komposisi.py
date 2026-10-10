"""
Komposisi dan neraca massa rancangan campuran beton poros.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

Sumber: OUTPUT3 §3.3 — rasio pengikat : agregat = 1 : 3, dengan 15% semen
disubstitusi lumpur IPAL, dan air ±0,40 liter per kg pengikat. Campuran dibuat
TANPA PASIR.

SATU HAL YANG PERLU DIBACA SEBELUM MEMAKAI MODUL INI
----------------------------------------------------
Agregat pada rancangan campuran adalah **batu sirtu saja**.

Hebel dan zeolit BUKAN bahan campuran beton. Naskah §3.4.2 butir 1 menyatakan
keduanya sebagai *media retensi air*, dan Tabel 4.2 menempatkannya sebagai
**lapisan terpisah di bawah beton poros**. §4.1.3 menjelaskan alasannya: hebel
dipakai dalam bentuk aslinya justru karena fungsinya menyimpan air, bukan
memikul beban.

Modul ini karena itu TIDAK menyediakan pembagian fraksi agregat menjadi
sirtu/hebel/zeolit. Versi aplikasi sebelumnya melakukannya, dan itu memodelkan
sistem material yang berbeda dari yang diteliti.

ASUMSI YANG BELUM TERSELESAIKAN
-------------------------------
Berat satuan beton poros 1.850 kg/m3 **tidak disebut naskah**. Data benda uji
justru menyiratkan angka yang jauh lebih rendah: tiga silinder dengan massa
rata-rata 6,78 kg, bila benar berukuran Ø150 x 300 mm, memberi sekitar
1.279 kg/m3. Selisihnya besar dan belum terjelaskan.

Modul ini TIDAK memilih salah satu diam-diam. Berat satuan diserahkan sebagai
argumen, nilai bawaannya 1.850 kg/m3 agar perilaku lama tidak berubah, dan
setiap hasil membawa daftar asumsinya sendiri.
"""

from __future__ import annotations

import math

#: Berat satuan bawaan, kg/m3. ASUMSI — tidak ada di naskah.
BERAT_SATUAN_ASUMSI = 1850.0

#: Rasio agregat terhadap pengikat (OUTPUT3 §3.3): 1 kg pengikat : 3 kg sirtu.
RASIO_AGREGAT_ACUAN = 3.0

#: Substitusi lumpur IPAL yang diuji laboratorium, persen.
SUBSTITUSI_ACUAN = 15.0

#: Faktor air-pengikat acuan.
FAKTOR_AIR_PENGIKAT_ACUAN = 0.40

# Data benda uji tekan (OUTPUT3 Tabel 4.1), dipakai untuk menghitung berat
# satuan tersirat pada fungsi di bawah.
_MASSA_BENDA_UJI_KG = (6.45, 6.80, 7.10)
_DIAMETER_SILINDER_M = 0.150
_TINGGI_SILINDER_M = 0.300


def _positif(nama: str, nilai: float) -> float:
    nilai = float(nilai)
    if not math.isfinite(nilai) or nilai <= 0:
        raise ValueError(f"{nama} harus bilangan positif berhingga, diterima {nilai}")
    return nilai


def _persen(nama: str, nilai: float) -> float:
    nilai = float(nilai)
    if not math.isfinite(nilai) or not 0.0 <= nilai <= 100.0:
        raise ValueError(f"{nama} harus 0-100 persen, diterima {nilai}")
    return nilai


def massa_total_kg(berat_satuan_kg_m3: float, volume_m3: float) -> float:
    """Massa total adukan, kg. m = rho * V"""
    return _positif("berat satuan", berat_satuan_kg_m3) * _positif("volume adukan", volume_m3)


def berat_satuan_tersirat_benda_uji() -> dict:
    """
    Berat satuan yang tersirat dari massa benda uji tekan.

    Dipakai untuk menyatakan besarnya selisih terhadap asumsi 1.850 kg/m3,
    bukan untuk menggantikannya.

    PEMBULATAN DI SINI ARITMETIKA, BUKAN KONVENSI PELAPORAN
        Nilai persisnya 1.279,53 kg/m3. Contoh di bawah menyatakan apa yang
        dihasilkan Python, bukan angka mana yang seharusnya dikutip proyek.
        Naskah dan konstanta.py masih menyebut ~1.279; keselarasan angka yang
        dikutip menunggu keputusan penulis pada SD-16C, bersama pertanyaan
        yang lebih mendasar apakah 1.850 dan angka ini menggambarkan besaran
        fisik yang sama.

    >>> hasil = berat_satuan_tersirat_benda_uji()
    >>> round(hasil["berat_satuan_kg_m3"], 2)
    1279.53
    >>> round(hasil["berat_satuan_kg_m3"])
    1280
    """
    volume = math.pi * (_DIAMETER_SILINDER_M / 2.0) ** 2 * _TINGGI_SILINDER_M
    rerata = sum(_MASSA_BENDA_UJI_KG) / len(_MASSA_BENDA_UJI_KG)
    rho = rerata / volume
    return {
        "massa_rerata_kg": rerata,
        "volume_silinder_m3": volume,
        "berat_satuan_kg_m3": rho,
        "selisih_terhadap_asumsi_persen": (rho - BERAT_SATUAN_ASUMSI) / BERAT_SATUAN_ASUMSI * 100.0,
        "catatan": (
            "Mengandaikan silinder berukuran 150 x 300 mm. Tinggi silinder "
            "sebenarnya belum dikonfirmasi tim, sehingga angka ini indikatif."
        ),
    }


def rancangan_campuran(
    volume_m3: float,
    substitusi_ipal_persen: float = SUBSTITUSI_ACUAN,
    faktor_air_pengikat: float = FAKTOR_AIR_PENGIKAT_ACUAN,
    berat_satuan_kg_m3: float = BERAT_SATUAN_ASUMSI,
    rasio_agregat: float = RASIO_AGREGAT_ACUAN,
) -> dict:
    """
    Neraca massa rancangan campuran beton poros.

    Pembagian massa mengikuti rasio 1 : rasio_agregat : faktor_air_pengikat
    terhadap massa pengikat, sehingga

        massa_total = pengikat * (1 + rasio_agregat + f.a.b)

    Agregat adalah **batu sirtu saja**; hebel dan zeolit adalah lapisan retensi
    terpisah dan tidak muncul di sini.

    >>> h = rancangan_campuran(1.0)
    >>> round(h["massa_total_kg"], 1)
    1850.0
    >>> round(h["massa_pengikat_kg"], 2), round(h["massa_agregat_kg"], 2)
    (420.45, 1261.36)
    >>> round(h["massa_semen_kg"], 2), round(h["massa_ipal_kg"], 2)
    (357.39, 63.07)
    >>> h["neraca_tertutup"]
    True
    """
    V = _positif("volume adukan", volume_m3)
    rho = _positif("berat satuan", berat_satuan_kg_m3)
    sub = _persen("substitusi IPAL", substitusi_ipal_persen)
    fab = _positif("faktor air-pengikat", faktor_air_pengikat)
    ragg = _positif("rasio agregat", rasio_agregat)

    total = massa_total_kg(rho, V)

    pengikat = total / (1.0 + ragg + fab)
    agregat = ragg * pengikat
    air = fab * pengikat

    semen = pengikat * (1.0 - sub / 100.0)
    ipal = pengikat * (sub / 100.0)

    jumlah = pengikat + agregat + air
    tertutup = math.isclose(jumlah, total, rel_tol=1e-9, abs_tol=1e-9)

    asumsi = []
    if math.isclose(rho, BERAT_SATUAN_ASUMSI, rel_tol=1e-9):
        tersirat = berat_satuan_tersirat_benda_uji()
        asumsi.append(
            f"Berat satuan {BERAT_SATUAN_ASUMSI:.0f} kg/m³ adalah ASUMSI — tidak "
            f"disebut naskah. Massa benda uji justru menyiratkan sekitar "
            f"{tersirat['berat_satuan_kg_m3']:.0f} kg/m³."
        )
    if abs(sub - SUBSTITUSI_ACUAN) > 1e-9:
        asumsi.append(
            f"Substitusi {sub:.0f}% berada di luar komposisi yang diuji "
            f"({SUBSTITUSI_ACUAN:.0f}%). Proporsi massa tetap deterministik, "
            "tetapi kinerja campuran ini TIDAK diketahui."
        )
    if abs(fab - FAKTOR_AIR_PENGIKAT_ACUAN) > 1e-9:
        asumsi.append(
            f"Faktor air-pengikat {fab:.2f} berbeda dari acuan penelitian "
            f"({FAKTOR_AIR_PENGIKAT_ACUAN:.2f})."
        )

    def _pct(x: float) -> float:
        return x / total * 100.0 if total else 0.0

    return {
        "status_bukti": "model",
        "sesuai_acuan_penelitian": (
            abs(sub - SUBSTITUSI_ACUAN) < 1e-9
            and abs(fab - FAKTOR_AIR_PENGIKAT_ACUAN) < 1e-9
            and abs(ragg - RASIO_AGREGAT_ACUAN) < 1e-9
        ),
        # masukan
        "volume_m3": V,
        "berat_satuan_kg_m3": rho,
        "substitusi_ipal_persen": sub,
        "faktor_air_pengikat": fab,
        "rasio_agregat": ragg,
        # massa acuan total
        "massa_total_kg": total,
        # massa komponen
        "massa_pengikat_kg": pengikat,
        "massa_semen_kg": semen,
        "massa_ipal_kg": ipal,
        "massa_agregat_kg": agregat,
        "massa_air_kg": air,
        # proporsi terhadap massa total
        "proporsi_semen_persen": _pct(semen),
        "proporsi_ipal_persen": _pct(ipal),
        "proporsi_agregat_persen": _pct(agregat),
        "proporsi_air_persen": _pct(air),
        # pemeriksaan
        "jumlah_komponen_kg": jumlah,
        "selisih_neraca_kg": jumlah - total,
        "neraca_tertutup": tertutup,
        # keterbukaan
        "asumsi": asumsi,
        "catatan_agregat": (
            "Agregat adalah batu sirtu 4,75–12,5 mm. Hebel dan zeolit adalah "
            "media retensi pada lapisan terpisah (OUTPUT3 Tabel 4.2), bukan "
            "bagian campuran beton."
        ),
    }


def komponen(hasil: dict) -> list[dict]:
    """Daftar komponen siap tampil, dari hasil rancangan_campuran()."""
    return [
        {"Material": "Semen OPC", "Massa (kg)": hasil["massa_semen_kg"],
         "Proporsi (%)": hasil["proporsi_semen_persen"]},
        {"Material": "Lumpur IPAL", "Massa (kg)": hasil["massa_ipal_kg"],
         "Proporsi (%)": hasil["proporsi_ipal_persen"]},
        {"Material": "Batu Sirtu", "Massa (kg)": hasil["massa_agregat_kg"],
         "Proporsi (%)": hasil["proporsi_agregat_persen"]},
        {"Material": "Air", "Massa (kg)": hasil["massa_air_kg"],
         "Proporsi (%)": hasil["proporsi_air_persen"]},
    ]
