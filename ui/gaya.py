"""
Lembar gaya bersama.

Dipisahkan dari AQUAPAVE.py karena komponen di ui/components/ memancarkan
kelas CSS yang didefinisikan di sini (`result-box`, `kpi-card`, `badge-*`,
`section-head`). Bila lembar gaya tetap tertinggal di berkas aplikasi,
komponen akan tampak benar di satu tempat dan diam-diam kehilangan gayanya di
tempat lain.

TAHAN TERHADAP TEMA DAN LEBAR LAYAR
-----------------------------------
Setiap kotak yang memasang latar sendiri juga memasang warna teksnya sendiri,
sehingga isinya tetap terbaca pada tema terang maupun gelap. Judul bagian
mewarisi warna teks tema. Petak kartu angka kunci melipat sendiri pada layar
sempit (tablet), bukan memaksakan empat kolom.
"""

LEMBAR_GAYA = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .hero-banner {
    background: linear-gradient(135deg, #0a3d6b 0%, #1565C0 50%, #0288d1 100%);
    border-radius: 16px;
    padding: 40px 36px 32px;
    margin-bottom: 24px;
    color: white;
    position: relative;
    overflow: hidden;
  }
  @media (max-width: 900px) {
    .hero-banner { padding: 26px 22px 22px; }
    .hero-title  { font-size: 2rem; }
  }
  .hero-title { font-size: 2.6rem; font-weight: 700; margin: 0; letter-spacing: -1px; }
  .hero-sub   { font-size: 1.05rem; margin: 6px 0 0; opacity: 0.85; }
  .hero-ajak  { font-size: 0.95rem; margin: 14px 0 0; max-width: 62ch; line-height: 1.5; }
  .hero-badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.78rem;
    margin-top: 14px;
    letter-spacing: 0.5px;
  }

  .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr);
              gap: 14px; margin-bottom: 24px; }
  @media (max-width: 1150px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  }
  .kpi-card {
    background: white;
    border-radius: 12px;
    padding: 20px 18px 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-top: 4px solid;
    text-align: center;
  }
  .kpi-card.biru   { border-color: #1565C0; }
  .kpi-card.teal   { border-color: #00897B; }
  .kpi-card.hijau  { border-color: #388E3C; }
  .kpi-card.oranye { border-color: #E65100; }
  .kpi-value { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; line-height: 1;
               font-variant-numeric: tabular-nums; }
  .kpi-label { font-size: 0.78rem; color: #666; margin-top: 6px; }
  .kpi-status{ font-size: 0.62rem; letter-spacing: 0.08em; color: #8a8a8a;
               margin-top: 8px; font-family: ui-monospace, monospace; }
  .kpi-icon  { font-size: 1.4rem; margin-bottom: 6px; }

  .section-head {
    font-size: 1.1rem; font-weight: 700;
    color: inherit;
    border-left: 4px solid #1565C0;
    padding-left: 12px;
    margin: 18px 0 14px;
  }
  .result-box2 {
    background: #141414;
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid #141414;
    margin: 10px 0;
    color: #ecf0f1;
    overflow-x: auto;
  }
  .result-box {
    background: linear-gradient(135deg,#E3F2FD,#E8F5E9);
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid #BBDEFB;
    margin: 10px 0;
    color: #1a1a2e;
  }
  .result-box-dark {
    background: #1e2a3a;
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid #2c3e50;
    margin: 10px 0;
    color: #ecf0f1;
  }
  .result-value { font-size: 2rem; font-weight: 700; color: #1565C0; }
  .result-label { font-size: 0.82rem; color: #555; }

  .badge-lulus { background:#E8F5E9; color:#2E7D32; border-radius:8px; padding:6px 14px; font-weight:600; font-size:0.9rem; }
  .badge-gagal { background:#FFEBEE; color:#C62828; border-radius:8px; padding:6px 14px; font-weight:600; font-size:0.9rem; }
  .badge-warn  { background:#FFF3E0; color:#E65100; border-radius:8px; padding:6px 14px; font-weight:600; font-size:0.9rem; }

  div[data-baseweb="tab-list"] { gap: 6px; }
  div[data-baseweb="tab"] { border-radius: 8px 8px 0 0; }

  .footer {
    text-align:center; color:#999; font-size:0.78rem;
    border-top:1px solid #eee; margin-top:40px; padding-top:16px;
  }
</style>
"""


def pasang(st) -> None:
    """Pasang lembar gaya. Dipanggil sekali, sebelum komponen mana pun digambar."""
    st.markdown(LEMBAR_GAYA, unsafe_allow_html=True)


def pengantar(st, teks: str) -> None:
    """
    Satu-dua kalimat berbahasa awam tentang kegunaan sebuah tab.

    Diletakkan tepat di bawah judul tab, sebelum keterangan teknisnya, supaya
    pembaca yang baru mengenal bidang ini tahu pertanyaan apa yang dijawab tab
    itu sebelum bertemu istilah dan rujukannya.
    """
    st.markdown(f"**Untuk apa tab ini?** {teks}")


def judul_bagian(st, teks: str) -> None:
    """Judul bagian bergaris tepi — idiom yang berulang di setiap tab."""
    st.markdown(f'<div class="section-head">{teks}</div>', unsafe_allow_html=True)
