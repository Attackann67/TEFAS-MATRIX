# TEFAS PPF Mevduat Eşleniği Matrix Agent

Para piyasası fonlarının (PPF) **mevduat eşleniği** bazlı ağırlıklı performans
sıralamasını üretir ve formüllü, cross-check'li, iki sheet'li Excel çıktısı
oluşturur. Hem komut satırından çalışan bir Python pipeline'ı hem de Claude Code
üzerinden tetiklenen bir **skill + subagent** olarak kullanılabilir.

## Mevduat eşleniği nedir?

Bir fonun yıllıklandırılmış getirisini, mevduat stopajı kadar brütleştirerek
"bu fonun getirisine ulaşmak için kaç % brüt mevduat faizi gerekir?" sorusunu
yanıtlar:

```
yıllık getiri  = (Fiyat_T / Fiyat_T-n − 1) × 365 / n
mevduat eşleniği = yıllık getiri × (1 − fon_stopaj) / (1 − mevduat_stopaj)
```

Beko kurumsal yatırımcıdır (KVK 2/1) → `fon_stopaj = 0`, `mevduat_stopaj = 0.175`,
yani çarpan `1 / (1 − 0.175) = 1.2121`. Üç dönem (1G/7G/15G) ağırlıklı
ortalanır (varsayılan **%50 / %35 / %15**).

## Kurulum

```bash
pip install -r requirements.txt
```

## Kullanım

### 1) TEFAS Excel export'undan (birincil, en güvenilir yol)

TEFAS [Fon Verileri](https://www.tefas.gov.tr/tr/fon-verileri?fundType=YAT)
ekranından "para piyasası" filtreli, T / T-1 / T-7 / T-15 tarihli export'u
indirin ve:

```bash
python -m tefas_matrix --source TEFAS_ARGE.xlsx --out Matrix_TEFAS_PPF.xlsx
```

Kaynak dosyada `ÖZET DETAY VALUE` sheet'i varsa ME doğrudan oradan okunur;
yoksa tarih bazlı fiyat sheet'lerinden hesaplanır. Fon büyüklüğü, kişi sayısı
ve portföy dağılımı sırasıyla en güncel info sheet'inden ve `Portföy Dağılım`
sheet'inden alınır.

### 2) Canlı çekim (TEFAS erişimi gerektirir)

```bash
python -m tefas_matrix --live --asof 2026-05-29 --out Matrix.xlsx
```

`tefas-crawler` kullanır. ⚠ Yeni TEFAS API'si **yalnızca fiyat** döndürür;
AUM, kişi sayısı ve portföy dağılımı public değildir → bu alanlar boş kalır ve
Sheet 2 "PD YOK" olarak işaretlenir. Tam çıktı için (1) numaralı yolu kullanın.

### Ağırlıkları değiştirme

```bash
python -m tefas_matrix --source in.xlsx --out out.xlsx --w1 0.5 --w7 0.35 --w15 0.15
```

### İnteraktif HTML dashboard

`--dashboard` ile Excel'in yanında tek dosyalık, tarayıcıda açılan interaktif
bir dashboard da üretilir (harici bağımlılık/CDN yok):

```bash
python -m tefas_matrix --source in.xlsx --out out.xlsx --dashboard
# -> out.html  (yol da verilebilir: --dashboard panel.html)
```

### Yerel dashboard (localhost'ta aç)

Dosyayı çift tıklamak yerine `--serve` ile dashboard'u yerel bir sunucuda
açabilirsin; tarayıcı otomatik açılır (yalnızca `127.0.0.1`, dışarı kapalı,
ek bağımlılık yok). `--dashboard` vermesen de çalışır:

```bash
python -m tefas_matrix --source in.xlsx --out out.xlsx --serve
# ▶ Dashboard yerelde yayında: http://127.0.0.1:8000/out.html  (Ctrl+C ile durur)

python -m tefas_matrix --live --asof 2026-05-29 --out out/Matrix.xlsx --serve 8080
```

## Çıktı

**Sheet 1 — Dashboard:** Özet panel — KPI kartları (fon sayısı, ortalama/medyan
ME, en yüksek/en düşük, aralık, ağırlıklar), ilk 10 fon mini-tablosu ve gömülü
bar grafik. Dosya açıldığında ilk gelen sheet budur.

**Sheet 2 — PPF Mevduat Eşleniği:** Sıra, Fon Kodu/Adı, 1G/7G/15G ME ve dönem
sıraları, formüllü `AĞIRLIKLI ORT.` (sarı ağırlık input hücrelerine bağlı),
`Fark (2.ye)`, Fon Tutar, Kişi Sayısı + alt cross-check bloğu.

**Sheet 3 — Portföy Dağılım:** Aynı sırada varlık sınıfı yüzdeleri, otomatik
`Diğer` ile %100'e tamamlanan `TOPLAM` ve `Kontrol` sütunu.

**HTML dashboard (`--dashboard`):** KPI kartları, ilk 15 fonun inline-SVG bar
grafiği ve sütundan sıralanabilir, renk kodlu tam tablo. Excel ile aynı renk
şeması.

Renk kodu: 1-5 koyu yeşil · 6-10 açık yeşil · 11-15 gri · 16-20 açık gri ·
21+ beyaz · veri eksik kırmızı. 5/10/15/20. sıralarda ayraç çizgisi.

## Yapılandırma

Tüm politika parametreleri `tefas_matrix/config.py`:
ağırlıklar, hariç tutulan fonlar (`FIL`, Deniz Portföy fonları), stopaj,
filtreler, portföy dağılım sütun eşlemesi, renkler.

## Doğrulama

`tests/test_matrix.py` örnek TEFAS export'undan üretilen çıktının, referans
matrix dosyasıyla birebir eşleştiğini doğrular (ME makine hassasiyetinde,
portföy dağılımı tam, TOPLAM ≈ %100).

```bash
python -m pytest tests/ -v          # fixture mevcutsa
```
