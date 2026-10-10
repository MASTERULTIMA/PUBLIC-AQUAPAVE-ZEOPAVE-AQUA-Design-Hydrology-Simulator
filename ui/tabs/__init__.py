"""
Tab aplikasi, satu modul per tab.

Setiap modul mengekspor satu fungsi `render(st, ...)` dan MEMILIKI seluruh
penyajian tabnya. Perhitungan tetap di core/; nilai kanonik tetap di
data/akses.py; penyelesaian keluaran per skenario tetap di scenario/.

Kontrak sengaja dibuat sekecil mungkin dan berbeda-beda antartab: sebuah tab
hanya menerima apa yang benar-benar dibutuhkannya. Tidak ada objek konteks
umum yang dilewatkan demi keseragaman — justru kontrak yang sempit itulah yang
membuktikan tab tidak bergantung pada urutan eksekusi tab lain.

Seperti seluruh isi ui/, modul di sini tidak mengimpor Streamlit: `st`
dilewatkan sebagai argumen pertama.
"""
