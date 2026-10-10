"""
Model keluaran skenario — identitas stabil, bukti, dan ketersediaan.

Modul murni: tanpa Streamlit, tanpa I/O, tanpa state.

DUA HAL YANG SENGAJA DIPISAH
----------------------------
**Status bukti** menjawab: kalau nilai ini ada, seberapa kuat dukungannya?
    terukur · deterministik · literatur · target · asumsi

**Ketersediaan** menjawab: apakah nilai ini ada untuk skenario ini?
    tersedia · tidak_tersedia

Keduanya bukan hal yang sama. "Belum tersedia" **bukan** kategori ilmiah
sejajar dengan "terukur" atau "literatur" — ia menyatakan ketiadaan hasil,
bukan hasil dengan mutu tertentu. Karena itu keluaran yang tidak tersedia
memiliki `status_bukti = None`: tidak ada bukti untuk dinilai mutunya.

Pengenal keluaran (`OutputID`) bersifat internal dan stabil. Label tampilan
disimpan terpisah di `LABEL`, sehingga mengubah kata di layar tidak pernah
mematahkan logika.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OutputID(str, Enum):
    """Pengenal internal keluaran. Jangan dipakai sebagai teks tampilan."""

    MIX_TOTAL_MASS = "MIX_TOTAL_MASS"
    IPAL_MASS = "IPAL_MASS"
    CO2_TOTAL = "CO2_TOTAL"
    COMPRESSIVE_STRENGTH = "COMPRESSIVE_STRENGTH"
    PERMEABILITY = "PERMEABILITY"
    RETENTION = "RETENTION"
    POROSITY = "POROSITY"
    RUNOFF = "RUNOFF"


#: Label tampilan — terpisah dari pengenal internal.
LABEL: dict[OutputID, str] = {
    OutputID.MIX_TOTAL_MASS: "Massa total campuran",
    OutputID.IPAL_MASS: "Massa lumpur IPAL",
    OutputID.CO2_TOTAL: "Emisi CO₂ campuran",
    OutputID.COMPRESSIVE_STRENGTH: "Kuat tekan (7 hari)",
    OutputID.PERMEABILITY: "Koefisien permeabilitas",
    OutputID.RETENTION: "Retensi air",
    OutputID.POROSITY: "Porositas",
    OutputID.RUNOFF: "Air tertahan pada skala area",
}

#: Urutan tampilan pada tabel perbandingan.
URUTAN: tuple[OutputID, ...] = (
    OutputID.MIX_TOTAL_MASS,
    OutputID.IPAL_MASS,
    OutputID.CO2_TOTAL,
    OutputID.COMPRESSIVE_STRENGTH,
    OutputID.PERMEABILITY,
    OutputID.RETENTION,
    OutputID.POROSITY,
    OutputID.RUNOFF,
)


class StatusBukti(str, Enum):
    """Mutu dukungan sebuah nilai, bila nilainya ada."""

    TERUKUR = "terukur"
    DETERMINISTIK = "deterministik"
    LITERATUR = "literatur"
    TARGET = "target"
    ASUMSI = "asumsi"


class Ketersediaan(str, Enum):
    """Ada atau tidaknya nilai untuk skenario tertentu."""

    TERSEDIA = "tersedia"
    TIDAK_TERSEDIA = "tidak_tersedia"


#: Kalimat baku untuk keluaran yang tidak tersedia.
FRASA_TIDAK_TERSEDIA = "Belum tersedia — konfigurasi ini belum diuji"


@dataclass(frozen=True)
class Keluaran:
    """Satu keluaran skenario."""

    id: OutputID
    satuan: str
    ketersediaan: Ketersediaan
    nilai: float | None = None
    status_bukti: StatusBukti | None = None
    sumber: str = ""
    catatan: str = ""

    def __post_init__(self):
        if self.ketersediaan is Ketersediaan.TIDAK_TERSEDIA:
            if self.nilai is not None:
                raise ValueError(
                    f"{self.id.value}: keluaran tidak tersedia tidak boleh membawa nilai"
                )
            if self.status_bukti is not None:
                raise ValueError(
                    f"{self.id.value}: keluaran tidak tersedia tidak boleh membawa "
                    "status bukti — ketiadaan hasil bukan kategori bukti"
                )
        else:
            if self.nilai is None:
                raise ValueError(f"{self.id.value}: keluaran tersedia wajib punya nilai")
            if self.status_bukti is None:
                raise ValueError(
                    f"{self.id.value}: keluaran tersedia wajib punya status bukti"
                )

    @property
    def tersedia(self) -> bool:
        return self.ketersediaan is Ketersediaan.TERSEDIA

    @property
    def label(self) -> str:
        return LABEL[self.id]

    def teks_nilai(self, desimal: int = 2) -> str:
        """Nilai siap tampil, atau kalimat ketidaktersediaan."""
        if not self.tersedia:
            return FRASA_TIDAK_TERSEDIA
        return f"{self.nilai:,.{desimal}f} {self.satuan}".strip()


def tersedia(
    id: OutputID,
    nilai: float,
    satuan: str,
    status_bukti: StatusBukti,
    sumber: str = "",
    catatan: str = "",
) -> Keluaran:
    """Bentuk keluaran yang tersedia."""
    return Keluaran(
        id=id, nilai=float(nilai), satuan=satuan,
        ketersediaan=Ketersediaan.TERSEDIA,
        status_bukti=status_bukti, sumber=sumber, catatan=catatan,
    )


def tidak_tersedia(id: OutputID, satuan: str, catatan: str = "") -> Keluaran:
    """Bentuk keluaran yang tidak tersedia untuk skenario ini."""
    return Keluaran(
        id=id, nilai=None, satuan=satuan,
        ketersediaan=Ketersediaan.TIDAK_TERSEDIA,
        status_bukti=None, sumber="", catatan=catatan or FRASA_TIDAK_TERSEDIA,
    )


# ─────────────────────────── perbandingan ───────────────────────────

def dapat_dibandingkan(a: Keluaran, b: Keluaran) -> tuple[bool, str]:
    """
    Bolehkah selisih antara dua keluaran dihitung?

    Tiga syarat, semuanya wajib:
      1. keduanya tersedia;
      2. satuannya sama;
      3. status buktinya sama — membandingkan hasil terukur terhadap keluaran
         model menghasilkan angka yang tidak bermakna.
    """
    if a.id is not b.id:
        return False, "pengenal keluaran berbeda"
    if not (a.tersedia and b.tersedia):
        return False, "salah satu keluaran tidak tersedia"
    if a.satuan != b.satuan:
        return False, f"satuan berbeda: {a.satuan} vs {b.satuan}"
    if a.status_bukti is not b.status_bukti:
        return False, (
            f"status bukti berbeda: {a.status_bukti.value} vs {b.status_bukti.value}"
        )
    return True, ""


def selisih(acuan: Keluaran, lain: Keluaran) -> dict | None:
    """
    Selisih `lain` terhadap `acuan`, atau None bila tidak dapat dibandingkan.

    Mengembalikan None adalah jawaban yang benar untuk pasangan yang tidak
    sebanding — bukan nol, dan bukan angka apa pun.
    """
    boleh, alasan = dapat_dibandingkan(acuan, lain)
    if not boleh:
        return None
    delta = lain.nilai - acuan.nilai
    return {
        "delta": delta,
        "delta_persen": (delta / acuan.nilai * 100.0) if acuan.nilai else None,
        "satuan": acuan.satuan,
        "alasan": alasan,
    }
