"""
Lapisan antarmuka AQUAPAVE.

Arah ketergantungan yang berlaku di proyek ini:

    core/ · data/ · scenario/
            ↓
    ui/components/
            ↓
    ui/tabs/          (belum ada; ekstraksi tab menyusul setelah S5-1)
            ↓
    AQUAPAVE.py

Lapisan ini boleh membaca core/, data/, dan scenario/. Kebalikannya tidak
pernah boleh terjadi: tidak satu pun modul di core/, data/, atau scenario/
mengimpor sesuatu dari ui/.

KONVENSI: `st` DILEWATKAN SEBAGAI ARGUMEN
-----------------------------------------
Tidak ada modul di dalam ui/ yang menulis `import streamlit`. Objek `st`
selalu diterima sebagai parameter pertama, mengikuti konvensi yang sudah
dipakai scenario/state.py. Dua keuntungannya:

  1. komponen dapat diuji tanpa menjalankan Streamlit sama sekali;
  2. pemeriksaan arah ketergantungan menjadi sesederhana satu grep —
     `import streamlit` tidak boleh muncul di luar AQUAPAVE.py.
"""
