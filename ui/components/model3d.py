"""
Model 3D konseptual sistem lapisan ZEOPAVE-AQUA.

APA INI
-------
Gambar tiga dimensi yang dapat diputar dan diperbesar, dibangun dari daftar
lapisan kanonik (`data/akses.lapisan_sistem()`, OUTPUT3 Tabel 4.2). Tujuannya
satu: membantu orang yang belum mengenal perkerasan berpori memahami lapisan
apa saja yang ada dan ke mana air hujan mengalir.

Susunannya mengikuti ilustrasi naskah (OUTPUT3 Gambar 4.7): permukaan beton
poros, lapisan penyaring batu sirtu, media retensi hebel dan zeolit, pipa
pembuang, dan tanah dasar sebagai alas.

TIGA HAL YANG BUKAN
-------------------
1. **Bukan gambar berskala.** Penelitian hanya menetapkan dua tebal (2 cm
   beton poros dan 7,5 cm media retensi; keduanya hidup di Tab Efisiensi
   Biaya), tidak menetapkan pembagian tebal hebel dan zeolit, dan tidak
   menetapkan tebal batu sirtu maupun ukuran pipa. Karena itu SELURUH ukuran
   di modul ini adalah satuan gambar, dipilih agar lapisan mudah dibedakan.
   Tidak satu pun boleh dibaca sebagai sentimeter.

2. **Bukan simulasi aliran fluida.** Tetes air bergerak di sepanjang lintasan
   yang digambar tangan. Yang mengikuti perhitungan hanyalah PERBANDINGANNYA:
   dari sepuluh tetes, jumlah yang berhenti di media retensi mengikuti tingkat
   retensi yang diserahkan pemanggil. Bila tingkat retensi tidak tersedia,
   tetes tidak digambar sama sekali — tidak ada pembagian yang dikarang.

3. **Bukan sumber angka.** Modul ini tidak menghitung apa pun. Angka yang
   ditempel pada model diterima sebagai teks yang sudah jadi dari pemanggil,
   yang memperolehnya dari `core/hidrologi.py`.

TANAH DASAR ADALAH KONTEKS
--------------------------
Tanah dasar tampil pada ilustrasi naskah tetapi BUKAN salah satu dari lima
lapisan Tabel 4.2, dan model hidrologi aplikasi tidak menghitung air yang
meresap ke dalamnya. Ia digambar pucat, diberi label konteks, dan tidak
dilewati tetes air.

TANPA DEPENDENSI BARU
---------------------
Plotly sudah dipakai seluruh tab, dan pustaka JavaScript-nya dibundel
Streamlit. Tidak ada aset yang diambil dari luar saat aplikasi berjalan.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import plotly.graph_objects as go

# ─────────────────────────── ukuran gambar ───────────────────────────
#: Ukuran balok, dalam SATUAN GAMBAR — bukan meter, bukan sentimeter.
PANJANG = 4.0
LEBAR = 2.6

#: Jarak antarlapisan pada tampilan terurai, dalam satuan gambar.
CELAH_TERURAI = 0.42

#: Jumlah tetes pada animasi. Sepuluh, agar pembagiannya terbaca sebagai
#: "sekian dari sepuluh" tanpa perlu menghitung persen.
JUMLAH_TETES = 10

#: Banyak bingkai per satu putaran lintasan, dan jumlah putaran per pemutaran.
BINGKAI_PER_PUTARAN = 48
JUMLAH_PUTARAN = 3

WARNA_AIR = "#1E88E5"
WARNA_AIR_TERSIMPAN = "#0D47A1"

#: Pilihan "tidak menyorot lapisan mana pun".
SEMUA = "Semua lapisan"

KETERANGAN_KONSEPTUAL = (
    "Model konseptual, **tidak berskala**. Tebal lapisan dan ukuran pipa "
    "dipilih agar mudah dibedakan, bukan diambil dari pengukuran. Gerak tetes "
    "air adalah ilustrasi jalur aliran, **bukan simulasi aliran fluida**."
)


@dataclass(frozen=True)
class Rupa:
    """Tampilan satu lapisan pada model. Seluruh nilainya ilustratif."""

    warna: str
    tebal: float = 0.45          # satuan gambar
    bentuk: str = "lempeng"      # "lempeng" atau "pipa"
    tekstur: str = ""            # "pori", "kerikil", "bata", "butir", atau ""
    menahan_air: bool = False    # True untuk media retensi
    singkat: str = ""            # label pendek pada model
    sederhana: str = ""          # penjelasan bahasa sehari-hari


#: Rupa tiap lapisan, dikunci pada AWALAN nama kanoniknya (huruf kecil).
#: Nama dan fungsi resminya TIDAK ditulis ulang di sini: keduanya dibaca dari
#: `data/akses.lapisan_sistem()`. Yang hidup di sini hanya rupa dan kalimat
#: penjelasan bahasa sehari-hari.
RUPA: dict[str, Rupa] = {
    "beton poros": Rupa(
        warna="#7C8894", tebal=0.42, tekstur="pori", singkat="Beton poros",
        sederhana=(
            "Permukaan yang diinjak dan dilewati. Betonnya sengaja dibuat "
            "berongga, sehingga air hujan meresap turun lewat celah-celahnya "
            "alih-alih menggenang di atas."
        ),
    ),
    "batu sirtu": Rupa(
        warna="#A88B6E", tebal=0.42, tekstur="kerikil", singkat="Batu sirtu",
        sederhana=(
            "Lapisan kerikil di bawah beton. Tugasnya menyaring air dan "
            "menyebarkannya secara merata sebelum air sampai ke media "
            "penyimpan."
        ),
    ),
    "hebel": Rupa(
        warna="#E4E8EB", tebal=0.52, tekstur="bata", menahan_air=True,
        singkat="Hebel AAC",
        sederhana=(
            "Bata ringan yang penuh rongga kecil. Bekerja seperti spons: "
            "menahan air untuk sementara."
        ),
    ),
    "zeolit": Rupa(
        warna="#8DB88A", tebal=0.52, tekstur="butir", menahan_air=True,
        singkat="Zeolit",
        sederhana=(
            "Butiran mineral dengan pori yang sangat halus. Menahan air "
            "lebih lama, lalu melepaskannya perlahan."
        ),
    ),
    "pipa": Rupa(
        warna="#2F6FB5", tebal=0.0, bentuk="pipa", singkat="Pipa overflow",
        sederhana=(
            "Saluran pembuang. Saat media penyimpan sudah penuh, kelebihan "
            "air dialirkan lewat pipa ini menuju drainase."
        ),
    ),
}

#: Dipakai bila daftar kanonik kelak memuat lapisan yang belum dikenal modul
#: ini. Lapisannya tetap digambar — tidak ada lapisan yang hilang diam-diam.
RUPA_CADANGAN = Rupa(warna="#B0BEC5", tebal=0.45)

#: Tanah dasar: konteks dari ilustrasi naskah, bukan lapisan Tabel 4.2.
TANAH_DASAR = {
    "nama": "Tanah dasar",
    "fungsi": (
        "Konteks dari Hasil Uji. Bukan salah satu "
        "dari lima lapisan sistem pada Tabel 4.2."
    ),
    "sederhana": (
        "Tanah asli yang menjadi alas sistem. Aplikasi ini tidak menghitung "
        "air yang meresap ke tanah, sehingga tetes air pada model tidak "
        "digambar sampai ke sini."
    ),
    "warna": "#6D5847",
    "tebal": 0.40,
}

JALUR_AIR_TEKS = (
    "Hujan jatuh ke permukaan beton poros.",
    "Air meresap turun lewat rongga beton.",
    "Lapisan batu sirtu menyaring air dan menyebarkannya.",
    "Hebel dan zeolit menahan sebagian air untuk sementara.",
    "Bila media retensi sudah penuh, kelebihan air keluar lewat pipa "
    "overflow menuju drainase.",
)


def rupa(nama: str) -> Rupa:
    """Rupa untuk satu nama lapisan kanonik, atau rupa cadangan."""
    kecil = nama.strip().lower()
    for awalan, r in RUPA.items():
        if kecil.startswith(awalan):
            return r
    return RUPA_CADANGAN


def label_singkat(nama: str) -> str:
    return rupa(nama).singkat or nama


# ─────────────────────────── tata letak ───────────────────────────

def tata_letak(lapisan: list[dict], terurai: bool = False) -> dict:
    """
    Posisi setiap lapisan pada model, dari atas ke bawah.

    Mengembalikan `lempeng` (daftar balok), `pipa` (daftar pipa, masing-masing
    menumpang pada lempeng tepat di atasnya dalam urutan kanonik), dan `tanah`
    (balok konteks). Permukaan atas berada pada z = 0; ke bawah bernilai
    negatif.

    >>> t = tata_letak([{"nama": "Beton poros", "fungsi": ""},
    ...                 {"nama": "Zeolit", "fungsi": ""},
    ...                 {"nama": "Pipa overflow", "fungsi": ""}])
    >>> [b["nama"] for b in t["lempeng"]], [p["nama"] for p in t["pipa"]]
    (['Beton poros', 'Zeolit'], ['Pipa overflow'])
    >>> t["lempeng"][0]["z_atas"]
    0.0
    """
    celah = CELAH_TERURAI if terurai else 0.0
    lempeng: list[dict] = []
    pipa: list[dict] = []
    z = 0.0
    for nomor, lap in enumerate(lapisan, start=1):
        r = rupa(lap["nama"])
        if r.bentuk == "pipa":
            if not lempeng:
                continue  # pipa tanpa lapisan penumpu tidak dapat digambar
            induk = lempeng[-1]
            jari = min(0.17, (induk["z_atas"] - induk["z_bawah"]) * 0.36)
            pipa.append({
                "nomor": nomor, "nama": lap["nama"], "fungsi": lap["fungsi"],
                "rupa": r, "jari": jari,
                "z": induk["z_bawah"] + jari + 0.03,
                "y": 0.45,
                "x_luar": -1.25, "x_dalam": PANJANG * 0.55,
            })
            continue
        lempeng.append({
            "nomor": nomor, "nama": lap["nama"], "fungsi": lap["fungsi"],
            "rupa": r, "z_atas": z, "z_bawah": z - r.tebal,
        })
        z -= r.tebal + celah
    z_tanah = z if terurai else (lempeng[-1]["z_bawah"] if lempeng else 0.0)
    tanah = {
        "z_atas": z_tanah, "z_bawah": z_tanah - TANAH_DASAR["tebal"],
    }
    return {"lempeng": lempeng, "pipa": pipa, "tanah": tanah}


def jumlah_tetes_tertahan(retensi_persen: float | None) -> int | None:
    """
    Berapa dari `JUMLAH_TETES` tetes yang digambar berhenti di media retensi.

    Pembulatan untuk keperluan GAMBAR saja; angka retensinya sendiri tidak
    diubah dan tetap ditampilkan apa adanya oleh pemanggil.

    >>> jumlah_tetes_tertahan(40.0)
    4
    >>> jumlah_tetes_tertahan(None) is None
    True
    """
    if retensi_persen is None:
        return None
    bagian = max(0.0, min(100.0, float(retensi_persen))) / 100.0
    return int(round(bagian * JUMLAH_TETES))


# ─────────────────────────── geometri ───────────────────────────

def _balok(x0, x1, y0, y1, z0, z1) -> dict:
    """Delapan titik sudut dan dua belas segitiga sebuah balok."""
    return {
        "x": [x0, x1, x1, x0, x0, x1, x1, x0],
        "y": [y0, y0, y1, y1, y0, y0, y1, y1],
        "z": [z0, z0, z0, z0, z1, z1, z1, z1],
        "i": [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3],
        "j": [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4],
        "k": [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7],
    }


def _bungkus(teks: str, lebar: int = 44) -> str:
    """Pecah kalimat panjang menjadi beberapa baris untuk kotak petunjuk."""
    baris, kini = [], ""
    for kata in teks.split():
        if len(kini) + len(kata) + 1 > lebar and kini:
            baris.append(kini)
            kini = kata
        else:
            kini = f"{kini} {kata}".strip()
    if kini:
        baris.append(kini)
    return "<br>".join(baris)


def _petunjuk(nama: str, fungsi: str, sederhana: str) -> str:
    isi = f"<b>{nama}</b>"
    if sederhana:
        isi += f"<br>{_bungkus(sederhana)}"
    if fungsi:
        isi += f"<br><i>{_bungkus('Hasil Uji: ' + fungsi)}</i>"
    return isi + "<extra></extra>"


def _titik_tekstur(b: dict, acak: random.Random) -> tuple[list, list, list]:
    """Titik-titik isyarat material pada muka depan dan muka kanan lempeng."""
    r: Rupa = b["rupa"]
    jumlah = {"pori": 46, "kerikil": 54, "butir": 70}.get(r.tekstur, 0)
    xs, ys, zs = [], [], []
    tinggi = b["z_atas"] - b["z_bawah"]
    for n in range(jumlah):
        z = b["z_bawah"] + tinggi * (0.12 + 0.76 * acak.random())
        if n % 3 == 2:      # muka kanan
            xs.append(PANJANG + 0.012)
            ys.append(LEBAR * (0.05 + 0.90 * acak.random()))
        else:               # muka depan
            xs.append(PANJANG * (0.03 + 0.94 * acak.random()))
            ys.append(-0.012)
        zs.append(z)
    if r.tekstur == "pori":  # pori juga terlihat dari atas
        for _ in range(60):
            xs.append(PANJANG * (0.04 + 0.92 * acak.random()))
            ys.append(LEBAR * (0.05 + 0.90 * acak.random()))
            zs.append(b["z_atas"] + 0.012)
    return xs, ys, zs


def _garis_bata(b: dict) -> tuple[list, list, list]:
    """Sambungan bata pada muka depan dan kanan lempeng hebel."""
    xs, ys, zs = [], [], []
    tengah = (b["z_atas"] + b["z_bawah"]) / 2.0

    def ruas(p, q):
        xs.extend([p[0], q[0], None])
        ys.extend([p[1], q[1], None])
        zs.extend([p[2], q[2], None])

    d = -0.012
    ruas((0, d, tengah), (PANJANG, d, tengah))
    for n in range(1, 6):
        x = PANJANG * n / 6.0
        ruas((x, d, b["z_atas"]), (x, d, tengah))
        ruas((x - PANJANG / 12.0, d, tengah), (x - PANJANG / 12.0, d, b["z_bawah"]))
    k = PANJANG + 0.012
    ruas((k, 0, tengah), (k, LEBAR, tengah))
    for n in range(1, 4):
        y = LEBAR * n / 4.0
        ruas((k, y, b["z_atas"]), (k, y, tengah))
        ruas((k, y - LEBAR / 8.0, tengah), (k, y - LEBAR / 8.0, b["z_bawah"]))
    return xs, ys, zs


WARNA_TEKSTUR = {
    "pori": "#3F4A54",
    "kerikil": "#5E4A3A",
    "butir": "#4F7F4C",
}


def _jejak_lempeng(b: dict, redup: bool, acak: random.Random) -> list:
    r: Rupa = b["rupa"]
    kabur = 0.14 if redup else 1.0
    jejak = [go.Mesh3d(
        **_balok(0, PANJANG, 0, LEBAR, b["z_bawah"], b["z_atas"]),
        color=r.warna, opacity=kabur, flatshading=True,
        lighting=dict(ambient=0.72, diffuse=0.55, specular=0.04, roughness=0.95),
        name=b["nama"], showlegend=False,
        hovertemplate=_petunjuk(b["nama"], b["fungsi"], r.sederhana),
    )]
    if r.tekstur in WARNA_TEKSTUR:
        xs, ys, zs = _titik_tekstur(b, acak)
        jejak.append(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="markers",
            marker=dict(size=3.2 if r.tekstur != "kerikil" else 4.6,
                        color=WARNA_TEKSTUR[r.tekstur],
                        opacity=0.10 if redup else 0.85),
            hoverinfo="skip", showlegend=False, name=f"tekstur {b['nama']}",
        ))
    elif r.tekstur == "bata":
        xs, ys, zs = _garis_bata(b)
        jejak.append(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="lines",
            line=dict(color="#9AA5AD", width=3),
            opacity=0.12 if redup else 0.9,
            hoverinfo="skip", showlegend=False, name=f"tekstur {b['nama']}",
        ))
    return jejak


def _jejak_pipa(p: dict, redup: bool) -> go.Surface:
    r: Rupa = p["rupa"]
    sudut = [2 * math.pi * n / 24 for n in range(25)]
    ys = [p["y"] + p["jari"] * math.cos(s) for s in sudut]
    zs = [p["z"] + p["jari"] * math.sin(s) for s in sudut]
    return go.Surface(
        x=[[p["x_luar"]] * len(sudut), [p["x_dalam"]] * len(sudut)],
        y=[ys, ys], z=[zs, zs],
        surfacecolor=[[0] * len(sudut), [0] * len(sudut)],
        colorscale=[[0, r.warna], [1, r.warna]], showscale=False,
        opacity=0.16 if redup else 1.0,
        name=p["nama"], showlegend=False,
        hovertemplate=_petunjuk(p["nama"], p["fungsi"], r.sederhana),
    )


def _jejak_tanah(t: dict, redup: bool) -> go.Mesh3d:
    return go.Mesh3d(
        **_balok(-0.25, PANJANG + 0.25, -0.25, LEBAR + 0.25,
                 t["z_bawah"], t["z_atas"]),
        color=TANAH_DASAR["warna"], opacity=0.10 if redup else 0.55,
        flatshading=True, name=TANAH_DASAR["nama"], showlegend=False,
        hovertemplate=_petunjuk(
            TANAH_DASAR["nama"] + " (konteks)", TANAH_DASAR["fungsi"],
            TANAH_DASAR["sederhana"]),
    )


# ─────────────────────────── jalur air ───────────────────────────

Z_LANGIT = 0.95

#: Letak label pada muka depan, sebagai bagian dari PANJANG: nama lapisan di
#: sisi kiri, angka simulasi di sisi kanan, sehingga keduanya tidak bertumpuk.
X_LABEL = 0.21
X_ANGKA = 0.74
Y_JALUR = -0.07   # sedikit di depan muka potongan, agar tetes tetap terlihat


def _lintasan_tetes(tata: dict, tertahan: int) -> list[dict]:
    """
    Lintasan tiap tetes: daftar titik yang dilalui dan apakah ia tertahan.

    Tetes yang tertahan berhenti di dalam lempeng media retensi. Tetes lain
    turun sampai setinggi pipa, lalu keluar lewat pipa. Tanpa pipa atau tanpa
    media retensi, tidak ada lintasan yang digambar.
    """
    penahan = [b for b in tata["lempeng"] if b["rupa"].menahan_air]
    if not penahan or not tata["pipa"]:
        return []
    pipa = tata["pipa"][0]
    # Urutan tetes yang tertahan disebar, supaya tidak mengelompok di satu sisi.
    sebaran = [1, 4, 7, 9, 2, 5, 0, 3, 6, 8]
    pilih = set(sebaran[:tertahan])
    lintasan = []
    for n in range(JUMLAH_TETES):
        x = 0.30 + (PANJANG - 0.60) * (n + 0.5) / JUMLAH_TETES
        mulai = (x, Y_JALUR, Z_LANGIT)
        if n in pilih:
            b = penahan[n % len(penahan)]
            dalam = 0.35 + 0.30 * ((n * 7) % 5) / 4.0
            z_henti = b["z_atas"] - (b["z_atas"] - b["z_bawah"]) * dalam
            lintasan.append({"titik": [mulai, (x, Y_JALUR, z_henti)],
                             "tertahan": True})
        else:
            lintasan.append({
                "titik": [mulai, (x, Y_JALUR, pipa["z"]),
                          (pipa["x_luar"], Y_JALUR, pipa["z"]),
                          (pipa["x_luar"] - 0.12, Y_JALUR, pipa["z"] - 0.45)],
                "tertahan": False,
            })
    return lintasan


def _di_lintasan(titik: list[tuple], bagian: float) -> tuple:
    """Titik pada lintasan patah-patah, `bagian` dari 0 (awal) sampai 1 (akhir)."""
    panjang = []
    for a, b in zip(titik, titik[1:]):
        panjang.append(sum((q - p) ** 2 for p, q in zip(a, b)) ** 0.5)
    total = sum(panjang) or 1.0
    sisa = max(0.0, min(1.0, bagian)) * total
    for (a, b), ruas in zip(zip(titik, titik[1:]), panjang):
        if sisa <= ruas or ruas == 0:
            f = 0.0 if ruas == 0 else sisa / ruas
            return tuple(p + (q - p) * f for p, q in zip(a, b))
        sisa -= ruas
    return titik[-1]


def _posisi_tetes(lintasan: list[dict], fase: float) -> tuple[list, list, list, list]:
    """Posisi dan warna seluruh tetes pada satu saat (`fase` dari 0 sampai 1)."""
    xs, ys, zs, warna = [], [], [], []
    for n, lin in enumerate(lintasan):
        s = (fase + (n * 0.37) % 1.0) % 1.0
        if lin["tertahan"]:
            # jatuh pada 55% pertama, lalu diam: "tersimpan"
            x, y, z = _di_lintasan(lin["titik"], min(1.0, s / 0.55))
            warna.append(WARNA_AIR_TERSIMPAN if s >= 0.55 else WARNA_AIR)
        else:
            x, y, z = _di_lintasan(lin["titik"], s)
            warna.append(WARNA_AIR)
        xs.append(x)
        ys.append(y)
        zs.append(z)
    return xs, ys, zs, warna


def _jejak_jalur_statis(tata: dict) -> list:
    """Garis dan panah jalur air — tetap terbaca walau animasi tidak diputar."""
    penahan = [b for b in tata["lempeng"] if b["rupa"].menahan_air]
    if not tata["lempeng"] or not tata["pipa"]:
        return []
    pipa = tata["pipa"][0]
    x = PANJANG * 0.5
    y = Y_JALUR - 0.02
    z_simpan = ((penahan[0]["z_atas"] + penahan[-1]["z_bawah"]) / 2.0
                if penahan else tata["lempeng"][-1]["z_bawah"])
    garis = go.Scatter3d(
        x=[x, x, x, pipa["x_luar"] - 0.05],
        y=[y, y, y, y],
        z=[Z_LANGIT + 0.1, z_simpan, pipa["z"], pipa["z"]],
        mode="lines", line=dict(color=WARNA_AIR, width=7), opacity=0.55,
        hoverinfo="skip", showlegend=False, name="jalur air",
    )
    panah = go.Cone(
        x=[x, x, pipa["x_luar"] - 0.05],
        y=[y, y, y],
        z=[0.12, z_simpan + 0.02, pipa["z"]],
        u=[0, 0, -1], v=[0, 0, 0], w=[-1, -1, 0],
        sizemode="absolute", sizeref=0.26, anchor="tip",
        colorscale=[[0, WARNA_AIR], [1, WARNA_AIR]], showscale=False,
        opacity=0.75, hoverinfo="skip", name="arah air",
    )
    return [garis, panah]


# ─────────────────────────── gambar ───────────────────────────

def _label_adegan(tata: dict, sorot: str | None, angka: dict | None,
                  retensi_tersedia: bool) -> list[dict]:
    # Label lapisan ditempel PADA muka depan lapisannya, bukan ditarik keluar
    # dengan garis penunjuk: label yang menjorok ke samping terpotong begitu
    # kolom gambar menyempit (tablet), sedangkan label pada muka lapisan ikut
    # mengecil dan membesar bersama modelnya.
    gaya_label = dict(
        showarrow=False, xanchor="center", yanchor="middle",
        font=dict(size=12, color="#102A43"),
        bgcolor="rgba(255,255,255,0.90)", bordercolor="#B0BEC5",
        borderwidth=1, borderpad=2,
    )
    label = []
    for b in tata["lempeng"]:
        if sorot and sorot != b["nama"]:
            continue
        label.append(dict(
            x=PANJANG * X_LABEL, y=-0.02, z=(b["z_atas"] + b["z_bawah"]) / 2.0,
            text=f"{b['nomor']}. {label_singkat(b['nama'])}", **gaya_label))
    for p in tata["pipa"]:
        if sorot and sorot != p["nama"]:
            continue
        label.append(dict(
            x=p["x_luar"], y=p["y"], z=p["z"] + p["jari"],
            text=f"{p['nomor']}. {label_singkat(p['nama'])}",
            **{**gaya_label, "showarrow": True, "arrowhead": 0,
               "arrowwidth": 1.2, "arrowcolor": "#607D8B",
               "ax": -14, "ay": -34, "xanchor": "left",
               "yanchor": "bottom"}))
    if not sorot or sorot == TANAH_DASAR["nama"]:
        t = tata["tanah"]
        label.append(dict(
            x=PANJANG * 0.58, y=-0.27, z=(t["z_atas"] + t["z_bawah"]) / 2.0,
            text="Tanah dasar (konteks)",
            **{**gaya_label, "font": dict(size=11, color="#5D4037")}))

    gaya_angka = dict(
        showarrow=False, font=dict(size=12, color="#0D47A1"),
        bgcolor="rgba(227,242,253,0.95)", bordercolor="#90CAF9",
        borderwidth=1, borderpad=4,
    )
    if angka:
        penahan = [b for b in tata["lempeng"] if b["rupa"].menahan_air]
        if angka.get("jatuh"):
            label.append(dict(x=PANJANG * 0.5, y=Y_JALUR, z=Z_LANGIT + 0.28,
                              text=angka["jatuh"], **gaya_angka))
        if angka.get("tertahan") and penahan:
            label.append(dict(
                x=PANJANG * X_ANGKA, y=Y_JALUR - 0.05,
                z=(penahan[0]["z_atas"] + penahan[-1]["z_bawah"]) / 2.0,
                text=angka["tertahan"], **gaya_angka))
        if angka.get("lolos") and tata["pipa"]:
            p = tata["pipa"][0]
            label.append(dict(x=p["x_luar"] - 0.1, y=Y_JALUR, z=p["z"] - 0.62,
                              text=angka["lolos"],
                              **{**gaya_angka, "xanchor": "left"}))
    elif not retensi_tersedia:
        penahan = [b for b in tata["lempeng"] if b["rupa"].menahan_air]
        if penahan:
            label.append(dict(
                x=PANJANG * 0.5, y=Y_JALUR - 0.05,
                z=Z_LANGIT + 0.28,
                text="Bagian yang tertahan: belum diketahui",
                **{**gaya_angka, "font": dict(size=12, color="#8D4E00"),
                   "bgcolor": "rgba(255,243,224,0.96)",
                   "bordercolor": "#FFB74D"}))
    return label


def gambar(
    lapisan: list[dict],
    *,
    sorot: str | None = None,
    terurai: bool = False,
    jalur_air: bool = True,
    retensi_persen: float | None = None,
    angka: dict | None = None,
    revisi: int = 0,
) -> go.Figure:
    """
    Bangun gambar 3D sistem lapisan.

    `lapisan`         daftar kanonik `{"nama", "fungsi"}`, dari atas ke bawah.
    `sorot`           nama lapisan yang ditonjolkan; lapisan lain diredupkan.
    `terurai`         True memisahkan lapisan agar tiap lapisan terlihat utuh.
    `jalur_air`       True menggambar jalur air dan tetesnya.
    `retensi_persen`  tingkat retensi untuk membagi tetes; None berarti tidak
                      tersedia, dan tetes tidak digambar.
    `angka`           teks siap tampil untuk ditempel pada model, berkunci
                      "jatuh", "tertahan", "lolos". Modul ini tidak
                      menghitungnya.
    `revisi`          dinaikkan pemanggil untuk mengembalikan sudut pandang.

    >>> lap = [{"nama": "Beton poros", "fungsi": "f"},
    ...        {"nama": "Zeolit", "fungsi": "f"},
    ...        {"nama": "Pipa overflow", "fungsi": "f"}]
    >>> fig = gambar(lap, retensi_persen=40.0)
    >>> sorted({j.name for j in fig.data} & {"Beton poros", "Zeolit", "Pipa overflow"})
    ['Beton poros', 'Pipa overflow', 'Zeolit']
    >>> len(fig.frames) == BINGKAI_PER_PUTARAN * JUMLAH_PUTARAN
    True
    >>> gambar(lap, retensi_persen=None).frames
    ()
    """
    tata = tata_letak(lapisan, terurai)
    acak = random.Random(20260910)   # benih tetap: gambar selalu sama
    fig = go.Figure()

    for b in tata["lempeng"]:
        for j in _jejak_lempeng(b, bool(sorot) and sorot != b["nama"], acak):
            fig.add_trace(j)
    for p in tata["pipa"]:
        fig.add_trace(_jejak_pipa(p, bool(sorot) and sorot != p["nama"]))
    fig.add_trace(_jejak_tanah(
        tata["tanah"], bool(sorot) and sorot != TANAH_DASAR["nama"]))

    tertahan = jumlah_tetes_tertahan(retensi_persen)
    tombol = []
    if jalur_air:
        for j in _jejak_jalur_statis(tata):
            fig.add_trace(j)
        lintasan = _lintasan_tetes(tata, tertahan) if tertahan is not None else []
        if lintasan:
            xs, ys, zs, warna = _posisi_tetes(lintasan, 0.0)
            fig.add_trace(go.Scatter3d(
                x=xs, y=ys, z=zs, mode="markers",
                marker=dict(size=7, color=warna, symbol="circle",
                            line=dict(color="#FFFFFF", width=1)),
                hoverinfo="skip", showlegend=False, name="tetes air",
            ))
            indeks = len(fig.data) - 1
            bingkai = []
            for n in range(BINGKAI_PER_PUTARAN * JUMLAH_PUTARAN):
                xs, ys, zs, warna = _posisi_tetes(
                    lintasan, (n % BINGKAI_PER_PUTARAN) / BINGKAI_PER_PUTARAN)
                bingkai.append(go.Frame(
                    name=str(n), traces=[indeks],
                    data=[go.Scatter3d(x=xs, y=ys, z=zs,
                                       marker=dict(color=warna))],
                ))
            fig.frames = bingkai
            tombol = [dict(
                type="buttons", direction="left", showactive=False,
                x=0.0, y=1.0, xanchor="left", yanchor="top",
                pad=dict(t=4, l=4), bgcolor="#FFFFFF", bordercolor="#90A4AE",
                font=dict(color="#102A43", size=12),
                buttons=[
                    dict(label="Putar aliran air", method="animate",
                         args=[None, dict(
                             frame=dict(duration=75, redraw=True),
                             transition=dict(duration=0),
                             fromcurrent=True, mode="immediate")]),
                    dict(label="Jeda", method="animate",
                         args=[[None], dict(
                             frame=dict(duration=0, redraw=False),
                             transition=dict(duration=0), mode="immediate")]),
                ],
            )]

    sumbu = dict(visible=False, showbackground=False)
    fig.update_layout(
        height=480, margin=dict(t=6, b=6, l=0, r=0),
        showlegend=False, updatemenus=tombol,
        uirevision=f"model3d-{revisi}",
        scene=dict(
            xaxis=sumbu, yaxis=sumbu, zaxis=sumbu,
            aspectmode="data", dragmode="turntable",
            uirevision=f"model3d-{revisi}",
            camera=dict(eye=dict(x=-1.12, y=-1.7, z=0.76),
                        up=dict(x=0, y=0, z=1),
                        center=dict(x=0.02, y=0, z=-0.08)),
            annotations=_label_adegan(
                tata, sorot, angka if jalur_air else None,
                retensi_tersedia=tertahan is not None or not jalur_air),
        ),
    )
    return fig


# ─────────────────────────── versi teks ───────────────────────────

def uraian_teks(lapisan: list[dict], retensi_persen: float | None,
                angka: dict | None = None) -> str:
    """
    Model yang sama dalam bentuk teks, untuk pembaca yang tidak dapat memakai
    tampilan 3D (pembaca layar, peramban tanpa WebGL, atau cetakan).
    """
    baris = ["**Lapisan dari atas ke bawah**", ""]
    for nomor, lap in enumerate(lapisan, start=1):
        r = rupa(lap["nama"])
        baris.append(
            f"{nomor}. **{lap['nama']}** — {r.sederhana or lap['fungsi']} "
            f"*Hasil Uji: {lap['fungsi']}*")
    baris += [
        "",
        f"Di bawahnya: **{TANAH_DASAR['nama']}** (konteks, bukan bagian dari "
        f"lima lapisan sistem). {TANAH_DASAR['sederhana']}",
        "",
        "**Jalur air**",
        "",
    ]
    baris += [f"{n}. {t}" for n, t in enumerate(JALUR_AIR_TEKS, start=1)]
    baris.append("")
    tertahan = jumlah_tetes_tertahan(retensi_persen)
    if tertahan is None:
        baris.append(
            "Pembagian air yang tertahan dan yang keluar **tidak digambar**: "
            "tingkat retensi belum tersedia untuk komposisi skenario aktif.")
    else:
        baris.append(
            f"Pada gambar, {tertahan} dari {JUMLAH_TETES} tetes berhenti di "
            f"media retensi dan {JUMLAH_TETES - tertahan} keluar lewat pipa, "
            "mengikuti tingkat retensi skenario aktif.")
    if angka:
        isi = [angka[k] for k in ("jatuh", "tertahan", "lolos") if angka.get(k)]
        if isi:
            baris += ["", "**Angka simulasi terakhir**", ""]
            baris += [f"- {teks.replace('<br>', ' ')}" for teks in isi]
    return "\n".join(baris)


def keterangan_tetes(retensi_persen: float | None) -> str:
    """
    Kalimat yang menjelaskan arti pembagian tetes pada gambar.

    Menyatakan terang-terangan batas hubungan gambar dengan perhitungan:
    model hidrologi aplikasi menghitung BERAPA air yang tertahan, bukan lewat
    jalur mana sisanya keluar.

    >>> keterangan_tetes(40.0).startswith("Pada gambar, 4 dari 10 tetes")
    True
    >>> "tidak digambar" in keterangan_tetes(None)
    True
    """
    tertahan = jumlah_tetes_tertahan(retensi_persen)
    if tertahan is None:
        return (
            "Pembagian air yang tertahan dan yang keluar tidak digambar: "
            "tingkat retensi belum tersedia untuk komposisi skenario aktif, "
            "dan aplikasi tidak menaksirnya."
        )
    return (
        f"Pada gambar, {tertahan} dari {JUMLAH_TETES} tetes berhenti di media "
        "retensi, mengikuti tingkat retensi skenario aktif. Perhitungan "
        "aplikasi hanya menentukan berapa banyak air yang tertahan; lewat "
        "jalur mana sisanya keluar tidak dihitung. Pipa digambar sebagai "
        "jalur keluar karena itulah fungsinya menurut Hasil Uji."
    )


# ─────────────────────────── penyajian ───────────────────────────

KUNCI_SOROT = "model3d_sorot"
KUNCI_TERURAI = "model3d_terurai"
KUNCI_JALUR = "model3d_jalur_air"
KUNCI_REVISI = "model3d_revisi"


def render(st, lapisan: list[dict], *, retensi_persen: float | None,
           angka: dict | None = None) -> None:
    """
    Gambar model 3D beserta kendalinya dan versi teksnya.

    Setiap kendali di sini mengubah gambar. Tidak ada kendali yang hanya
    hiasan, dan tidak ada yang menyentuh perhitungan.
    """
    nama = [lap["nama"] for lap in lapisan] + [TANAH_DASAR["nama"]]
    kol_gambar, kol_kendali = st.columns([2.1, 1])

    with kol_kendali:
        pilih = st.radio(
            "Sorot lapisan", [SEMUA] + nama, key=KUNCI_SOROT,
            format_func=lambda n: n if n == SEMUA else label_singkat(n),
            help=(
                "Pilih satu lapisan untuk menonjolkannya pada model dan "
                "membaca kegunaannya. Lapisan lain diredupkan."
            ),
        )
        terurai = st.toggle(
            "Pisahkan lapisan", key=KUNCI_TERURAI,
            help="Memberi jarak antarlapisan agar tiap lapisan terlihat utuh.",
        )
        jalur = st.toggle(
            "Tampilkan jalur air", value=True, key=KUNCI_JALUR,
            help=(
                "Menampilkan garis, panah, dan tetes air yang menunjukkan ke "
                "mana air hujan mengalir. Tekan Putar aliran air pada gambar "
                "untuk menggerakkan tetesnya."
            ),
        )
        if st.button("Atur ulang tampilan",
                     help="Mengembalikan sudut pandang ke posisi awal."):
            st.session_state[KUNCI_REVISI] = (
                st.session_state.get(KUNCI_REVISI, 0) + 1)
        _kartu_lapisan(st, lapisan, pilih)

    sorot = None if pilih == SEMUA else pilih
    revisi = st.session_state.get(KUNCI_REVISI, 0)
    with kol_gambar:
        st.plotly_chart(
            gambar(lapisan, sorot=sorot, terurai=terurai, jalur_air=jalur,
                   retensi_persen=retensi_persen, angka=angka, revisi=revisi),
            width="stretch", key=f"model3d_gambar_{revisi}",
            config={"displaylogo": False, "scrollZoom": True},
        )
        st.caption(
            "Seret untuk memutar, gulir atau cubit untuk memperbesar, dan "
            "arahkan penunjuk ke sebuah lapisan untuk membaca kegunaannya."
        )
        st.caption(KETERANGAN_KONSEPTUAL)
        if jalur:
            st.caption(keterangan_tetes(retensi_persen))

    with st.expander("Versi teks model ini (tanpa tampilan 3D)"):
        st.markdown(uraian_teks(lapisan, retensi_persen, angka))


def _kartu_lapisan(st, lapisan: list[dict], pilih: str) -> None:
    """Nama dan kegunaan lapisan yang sedang disorot."""
    if pilih == SEMUA:
        st.caption(
            "Lima lapisan sistem mengikuti Hasil Uji. Pilih salah "
            "satu di atas untuk membaca kegunaannya."
        )
        return
    if pilih == TANAH_DASAR["nama"]:
        st.markdown(f"**{TANAH_DASAR['nama']} (konteks)**")
        st.markdown(TANAH_DASAR["sederhana"])
        st.caption(TANAH_DASAR["fungsi"])
        return
    lap = next(x for x in lapisan if x["nama"] == pilih)
    r = rupa(pilih)
    st.markdown(f"**{lap['nama']}**")
    if r.sederhana:
        st.markdown(r.sederhana)
    st.caption(f"Menurut Hasil Uji: {lap['fungsi']}")
