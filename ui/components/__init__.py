"""
Komponen presentasi bersama.

Isinya HANYA penyajian. Tidak ada perhitungan ilmiah di lapisan ini: angka
dihitung di core/, nilainya berasal dari data/akses.py, dan penyelesaian
keluaran per skenario dilakukan scenario/resolusi.py. Komponen di sini
menerima hasilnya lalu menggambarnya.

Seluruh fungsi menerima `st` sebagai argumen pertama; tidak ada modul di sini
yang mengimpor Streamlit (lihat ui/__init__.py).
"""

from . import comparison, evidence, provenance, scenario, warnings  # noqa: F401

__all__ = ["comparison", "evidence", "provenance", "scenario", "warnings"]
