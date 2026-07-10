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

## Çıktı

**Sheet 1 — PPF Mevduat Eşleniği:** Sıra, Fon Kodu/Adı, 1G/7G/15G ME ve dönem
sıraları, formüllü `AĞIRLIKLI ORT.` (sarı ağırlık input hücrelerine bağlı),
`Fark (2.ye)`, Fon Tutar, Kişi Sayısı + alt cross-check bloğu.

**Sheet 2 — Portföy Dağılım:** Aynı sırada varlık sınıfı yüzdeleri, otomatik
`Diğer` ile %100'e tamamlanan `TOPLAM` ve `Kontrol` sütunu.

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

---

# Beko Cash Dashboard (`beko_cash`)

Beko Corporate Treasury **nakit-overdue kayit + analiz + dashboard** motoru.
Aylik liquid assets formu, overdue listesi ve Citi pool raporunu isler; istirak
bazli trend, atil nakit (SORGULA) analizi, nakit-overdue karsilastirmasi ve Citi
pool takibini tek dosyada, **canli SUMIFS formullu** Excel olarak uretir.

Claude Code uzerinden `beko-cash-dashboard` skill'i ile tetiklenir; komut
satirindan da bagimsiz calisir.

## Uc katman

| Katman | Modul | Is |
|---|---|---|
| **Kayit** | `snapshot` | aylik `data/snapshots/YYYY-MM.json` oku/yaz/dogrula/iskele |
| **Analiz** | `compute` | 4 grup + 10 kod turetimi, vadesiz %, SORGULA, MoM delta, trend |
| **Cikarim** | `extract` | kaynak Excel'lerden (Hesap Detay / overdue / pool) snapshot uret |
| **Dashboard** | `dashboard` | 10 sayfali, canli formullu, renk-kodlu Excel |

## Kullanim

```bash
# Kaynak Excel'lerden aylik kayit uret (kolonlar baslik adindan bulunur)
python -m beko_cash extract \
    --detail <trend/Hesap_Detay>.xlsx --sheet "Hesap Detay" \
    --overdue <Nakit_vs_Overdue>.xlsx --pool <Citi_Pool>.xlsx \
    --month 2026-05 --eurtry 53.1224 --sheet2-gap 11386549.99

python -m beko_cash validate              # kontrol-listesi kurallari
python -m beko_cash build --out Beko_Cash_Dashboard_2026-05.xlsx
python /mnt/skills/public/xlsx/scripts/recalc.py Beko_Cash_Dashboard_2026-05.xlsx  # zorunlu
python -m beko_cash summary                # insana okunur ozet
python -m beko_cash web --out dash.html    # tek dosyalik HTML dashboard (tarayici)
python -m beko_cash new --month 2026-06 --eurtry 53.50   # bos ay iskelesi
```

## Kayit (snapshot) semasi

Istirak basina 10 kategori kodu (`cat_tl`) birincil; 4 grup (Vadesiz/Vadeli/
Pool/Diger) buradan turetilir. Overdue (bin EUR), Citi pool, eslesme guveni
(Kesin/Olasi/Eslesmedi), statu ve sorgu takibi ayni kayitta tutulur. Detay
sayfa `data/snapshots/`; dashboard tamamen bu kayitlardan uretilir (kaynak
Excel'ler ucsa bile yeniden uretilebilir).

## Dashboard sayfalari

Ozet · Girdi (mavi tek nokta) · Kayit Detay (SUMIFS omurgasi) · Kayit Entity ·
Grup Trend (TL + mn EUR) · Kategori Trend (10 kod) · Istirak Matris (SORGULA
bayragi) · Nakit vs Overdue (kesit farki etikette) · Citi Pool · Acik Sorgular
· Kontrol (PASS/FAIL).

Renk kurali: baslik #002060 · **mavi** dis kaynak girdi · siyah ayni sayfa
formul · **yesil** capraz sayfa · **sari** dikkat. Kaynaksiz rakam yazilmaz.

## Veri notu

`data/snapshots/` altinda **gercek aylik kayitlar** tutulur (kullanici karari;
depo ozel). Kaynak/cikti xlsx dosyalari `.gitignore` ile haric tutulur; kayitlar
kaynak dosyalardan `extract` ile yeniden uretilebilir. Depo gorunurlugu
degisecekse snapshot'lar cikarilmalidir.

Citi pool katilimcilari `schema.POOL_PARTICIPANT_MAP` ile istirak koduna
baglanir (13 LE -> C746; HARIC olanlar C746'ya katilmaz; eslesmeyen isim
uyari uretir ve kullaniciya sorulur).

## Dogrulama

```bash
python -m pytest tests/test_beko_cash.py -q
```
