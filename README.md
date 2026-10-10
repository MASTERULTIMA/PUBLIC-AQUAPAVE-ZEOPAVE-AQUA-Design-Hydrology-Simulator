# AQUAPAVE

Aplikasi Streamlit pendamping penelitian **ZEOPAVE-AQUA** — perkerasan berpori
dengan substitusi lumpur IPAL, dilengkapi lapisan retensi hebel AAC dan zeolit.

AQUAPAVE menyajikan hasil pengujian laboratorium penelitian ini, menghitung
neraca dan skenario di atasnya, dan **menyatakan status bukti setiap angka yang
ditampilkannya**.

---

## Yang dilakukan aplikasi ini

- Menyambut pengguna baru lewat tab **Mulai di Sini**: penjelasan berbahasa
  awam, **model 3D konseptual** lapisan sistem, dan **simulasi hidrologi
  terpandu** empat langkah.
- Menyajikan **empat hasil ukur** penelitian beserta provenansinya: kuat tekan
  13,19 MPa (7 hari), permeabilitas 1,667 cm/detik, retensi air 40,0%, dan
  komposisi campuran §3.3.
- Menghitung **neraca massa** rancangan campuran untuk volume adukan pilihan.
- Menghitung **kuat tekan** `f'c = P/A` dari beban dan geometri benda uji.
- Menghitung **permeabilitas** `k = Q·L/(A·h·t)` metode constant head.
- Mensimulasikan **hidrologi skala area**: air jatuh, air tertahan, limpasan.
- Menghitung **neraca emisi CO₂** dari parameter yang dipilih pengguna.
- Menyusun **estimasi biaya** dua lapisan sistem dari kuantitas campuran
  kanonik dan harga satuan historis proyek.
- Menandai setiap keluaran dengan **status buktinya**, dan menolak menampilkan
  angka untuk konfigurasi yang tidak pernah diuji.

## Yang **tidak** dilakukan aplikasi ini

Kemampuan berikut pernah ada dan **sudah dihapus** karena tidak berdasar.
Aplikasi ini tidak menyediakannya, dan tidak berencana menyediakannya tanpa
bukti baru:

| Dihapus | Sebab |
|---|---|
| Estimasi **porositas** dari komposisi | koefisiennya tidak bersumber; porositas tidak pernah diukur pada penelitian ini |
| Estimasi **permeabilitas** dari komposisi | relasi polinomialnya tidak bersumber |
| Estimasi **kuat tekan** dari komposisi | satu campuran dengan tiga benda uji tidak dapat menjadi dasar hubungan substitusi→kekuatan |
| Klaim **"85% optimasi material"** | tidak ada di naskah |
| Ambang lulus permeabilitas 0,45 / 0,60 cm/detik | tidak ada di naskah |
| Atribusi **"SNI min 10 MPa"** | ambang lalu lintas ringan 5 MPa berasal dari Govedarica et al. (2022), bukan SNI |
| **Kapasitas retensi** dari tebal lapisan | rumusnya tidak bersumber |
| Metrik Dasbor **tonase lumpur IPAL** dan **CO₂ terhindarkan** skala proyek | tonasenya ternyata mewakili kebutuhan semen, bukan lumpur IPAL |

Untuk konfigurasi yang tidak pernah dicetak dan diuji, aplikasi menampilkan
**"Belum tersedia — konfigurasi ini belum diuji"**, bukan angka taksiran.

---

## Model bukti

Setiap besaran membawa provenansinya sendiri. Angka tidak boleh muncul di layar
tanpa statusnya ikut tampil.

| Status | Arti | Contoh |
|---|---|---|
| **terukur** | diukur tim di laboratorium, ada di tabel naskah | kuat tekan 13,19 MPa · permeabilitas 1,667 cm/detik · retensi 40,0% |
| **literatur** | dari pustaka yang disitir naskah | faktor emisi semen · ambang lalu lintas ringan 5 MPa |
| **model** | keluaran perhitungan, bukan pengukuran | air tertahan · biaya per m² |
| **target** | rancangan yang belum pernah diukur | porositas 18–25% |
| **asumsi** | nilai kerja tanpa sumber, wajib ditandai | berat satuan 1.850 kg/m³ · faktor konversi umur |
| **masukan historis proyek** | dipakai proyek, tidak diverifikasi ke pasar | keenam harga satuan material |
| **penilaian kualitatif** | pendapat tim, bukan pengukuran | skor radar Dasbor |

Kategori-kategori ini **tidak boleh diratakan** menjadi "data tervalidasi".
Aplikasi ini memverifikasi bahwa perhitungannya mereproduksi naskah; ia **tidak**
memvalidasi kebenaran ilmiah naskahnya (ADR-004).

---

## Keterbatasan yang diketahui

1. **Berat satuan 1.850 kg/m³** berstatus asumsi operasional. Tidak ada
   pengukuran kerapatan adukan segar maupun beton keras pada formulasi ZEOPAVE.
   Seluruh kuantitas dan biaya beton poros per m² bergantung padanya (SD-16C).
2. **Satuan harga hebel belum terselesaikan.** Tabel biaya proyek mengenakan
   Rp 20.000 per kilogram; keterangan pembelian penulis menyebut sekitar
   Rp 20.000 per batang. Tidak ada catatan konversi, dan massa satu batang
   tidak diketahui. Hebel menyumbang bagian terbesar biaya sistem.
3. **Keenam harga material** adalah masukan perhitungan proyek historis. Tidak
   ada kuitansi, penawaran, tanggal, maupun pemasok di belakangnya, dan tidak
   satu pun diverifikasi terhadap harga pasar.
4. **Pembagian tebal 7,5 cm** antara hebel dan zeolit belum ditetapkan penulis.
5. **Provenansi tabel faktor konversi umur** belum tertelusuri.
6. **Porositas tidak pernah diukur** pada penelitian ini; 18–25% adalah target.
7. **Skor radar Dasbor** penilaian kualitatif tim tanpa metodologi penskoran
   terdokumentasi.

---

## Tab aplikasi

| Tab | Isi | Sumber perhitungan |
|---|---|---|
| **Mulai di Sini** | pintu masuk pengguna baru: pengantar, model 3D konseptual, simulasi terpandu empat langkah, daftar istilah | `core/hidrologi.py` (fungsi yang sama dengan tab Retensi Air) |
| **Kalkulator Mix Design** | neraca massa campuran; agregat batu sirtu saja | `core/komposisi.py` |
| **Permeabilitas** | `k = Q·L/(A·h·t)`, constant head, multi-pengujian | `core/permeabilitas.py`, `core/geometri.py` |
| **Kuat Tekan** | `f'c = P/A`; estimasi konversi umur terpisah dan berlabel | `core/kuat_tekan.py` |
| **Retensi Air** | hidrologi skala area, diagram Sankey | `core/hidrologi.py` |
| **Emisi CO₂** | neraca emisi skenario aktif | `core/emisi.py` |
| **Dasbor Perbandingan** | radar kualitatif + tabel perbandingan berstatus | penyajian saja |
| **Efisiensi Biaya** | biaya dua lapisan per m², sensitivitas substitusi | `core/komposisi.py` + harga historis |

Hebel dan zeolit adalah **media retensi pada lapisan terpisah**, bukan bahan
campuran beton (OUTPUT3 Tabel 4.2, §3.4.2).

### Tab Mulai di Sini dan model 3D

Tab pertama ditujukan bagi pembaca yang belum mengenal teknik sipil. Isinya
tidak menambah kemampuan ilmiah apa pun; ia menyajikan kemampuan yang sudah ada
dengan urutan dan bahasa yang lebih mudah diikuti.

- **Simulasi terpandu** memanggil `core/hidrologi.skenario()` — fungsi yang
  sama dengan tab Retensi Air — dengan tiga masukan: luas area, intensitas
  hujan, dan lama hujan. Percobaan siap pakainya dinyatakan sebagai kelipatan
  skenario naskah (§4.6), bukan sebagai golongan hujan atau standar perencanaan.
- **Tingkat retensi tidak dipilih di tab ini.** Ia datang dari resolusi
  skenario aktif. Bila komposisinya belum pernah diuji, simulasi terpandu tidak
  dijalankan dan tidak ada angka yang dipinjam dari konfigurasi acuan.
- **Model 3D bersifat konseptual.** Lima lapisannya dibaca dari daftar kanonik
  (`data/akses.lapisan_sistem()`, OUTPUT3 Tabel 4.2) dan disusun mengikuti
  ilustrasi naskah (Gambar 4.7). Tebal lapisan, ukuran pipa, dan warnanya
  **ilustratif dan tidak berskala**; gerak tetes air adalah isyarat jalur
  aliran, **bukan simulasi aliran fluida**. Pembagian tetes mengikuti tingkat
  retensi skenario aktif, dan angka volume yang ditempel pada model adalah
  hasil simulasi terakhir — model itu sendiri tidak menghitung apa pun.
- Model dibangun dengan Plotly yang sudah menjadi dependensi aplikasi
  (`ui/components/model3d.py`). Tidak ada paket baru, tidak ada berkas model
  eksternal, dan tidak ada yang diunduh saat aplikasi berjalan. Versi teksnya
  tersedia di bawah gambar bagi peramban tanpa WebGL atau pembaca layar.

---

## Arsitektur

Aliran satu arah, tanpa siklus:

```
konstanta.py      sumbu data — satu-satunya tempat angka didefinisikan
      ↓
data/akses.py     gerbang baca; menolak nilai yang sudah dihapus
      ↓
core/             perhitungan murni, tanpa Streamlit
      ↓
scenario/         keadaan skenario dan resolusi ketersediaan
      ↓
ui/components/    komponen tampilan bersama, termasuk model 3D konseptual
ui/tabs/          satu modul per tab; menerima `st` sebagai argumen
      ↓
AQUAPAVE.py       satu-satunya modul yang mengimpor Streamlit
```

Aturan yang dijaga uji: hanya `AQUAPAVE.py` mengimpor Streamlit · tab tidak
saling mengimpor · tidak ada rumus sains di lapisan `ui/` · setiap klaim ilmiah
melewati `data/akses.py` · keluaran yang tidak tersedia digambar sebagai
ketidaktersediaan, bukan nol.

Keputusan arsitektur terekam sebagai ADR di `AQUAPAVE-Vault/90-Keputusan/`.

## Struktur repositori

```
AQUAPAVE.py           titik masuk aplikasi
konstanta.py          40 besaran kanonik + daftar nilai yang dihapus permanen
core/                 komposisi, kuat tekan, permeabilitas, retensi, hidrologi,
                      emisi, geometri
scenario/             keadaan, resolusi ketersediaan, kontrak keluaran
data/akses.py         gerbang baca besaran kanonik
ui/                   gaya, bilah sisi, beranda, components/, tabs/
validation/           uji otomatis
AQUAPAVE-Vault/       dokumentasi terbit: ADR, konsep, standar, data,
                      dokumentasi aplikasi, register keterbatasan
```

---

## Batas publikasi dokumentasi

Repositori ini menerbitkan **himpunan minimum** dokumentasi yang diperlukan untuk
memahami, menjalankan, memvalidasi, dan mereproduksi aplikasi: seluruh **ADR**,
catatan konsep dan standar, data acuan, dokumentasi tiap tab, **register
keterbatasan**, lembar sinkronisasi bukti, dan rencana demonstrasi.

Ruang kerja penelitian internal **tidak diterbitkan**: log kerja harian, catatan
investigasi forensik, pertanyaan yang masih menunggu jawaban penulis, draf naskah
yang belum terbit, dan catatan perencanaan. Semuanya tetap ada pada salinan kerja
penulis. Pengecualian ini menyangkut **proses**, bukan bukti: setiap keterbatasan
ilmiah yang diketahui tetap dinyatakan — di aplikasi, di README ini, dan di
register keterbatasan.

---

## Menjalankan

**Butuh Python 3.10–3.12.**

Batas atasnya nyata, bukan kehati-hatian berlebih: `requirements.txt` menyematkan
`numpy==1.26.0` (mendukung Python <3.13) dan `pandas==2.2.3`, dan tidak satu pun
dari keduanya menyediakan wheel untuk Python 3.13 ke atas. Versi itu disematkan
karena **di lingkungan itulah seluruh 678 uji dijalankan dan lulus**; menaikkannya
berarti memvalidasi ulang, bukan sekadar memutakhirkan.

```bash
pip install -r requirements.txt
```

```bash
streamlit run AQUAPAVE.py
```

### Penerapan di Streamlit Community Cloud

Community Cloud **tidak membaca** `runtime.txt` maupun `.python-version`. Versi
Python hanya dapat dipilih di **Advanced settings saat aplikasi pertama kali
diterapkan**, dan tidak dapat diubah sesudahnya — mengubahnya menuntut aplikasi
dihapus lalu diterapkan ulang.

Karena itu, saat menerapkan aplikasi ini:

| Pengaturan | Nilai |
|---|---|
| Repository | `MASTERULTIMA/PUBLIC-AQUAPAVE-ZEOPAVE-AQUA-Design-Hydrology-Simulator` |
| Branch | `main` |
| Main file path | `AQUAPAVE.py` |
| **Python version** (Advanced settings) | **3.12** |

Bila versi Python dibiarkan pada bawaan Community Cloud yang sedang berlaku,
pemasangan gagal pada `numpy==1.26.0`.

## Menjalankan uji

```bash
python -m unittest discover -s validation
```

Doctest ikut terkumpul lewat `validation/test_doctest.py`.

Status pada komit terakhir dokumentasi ini, dijalankan pada repositori ini:
**678 uji lulus**, **26 unit doctest / 65 contoh**.

Uji di sini bukan sekadar pengaman regresi. Sebagian besar menjaga **klaim
ilmiah**: bahwa nilai yang dihapus tidak kembali, bahwa asumsi tidak naik
pangkat menjadi pengukuran, dan bahwa status bukti ikut tampil sampai ke layar.
