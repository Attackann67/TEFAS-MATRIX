---
name: tefas-ppf-matrix
description: TEFAS para piyasası fonlarının mevduat eşleniği bazlı ağırlıklı performans matrixini oluşturur. Kullanıcı TEFAS Excel dosyası yüklediğinde, "fon sıralaması yap", "matrix oluştur", "mevduat eşleniği analizi", "PPF ranking", "fon karşılaştırma", "hangi fonlar iyi", "TEFAS analiz", "para piyasası fonu değerlendir", "güncel TEFAS dosyası oluştur", "portföy dağılım sırala" dediğinde mutlaka devreye al. TEFAS fon verisi içeren herhangi bir Excel dosyası yüklendiğinde de bu skill'i kullan.
---

# TEFAS PPF Matrix Oluşturucu

Para piyasası fonlarının mevduat eşleniği bazlı ağırlıklı performans
sıralamasını oluşturur. İki sheet'li formüllü, cross-check'li Excel çıktısı
üretir. Bu depodaki `tefas_matrix` paketi tüm hesaplama ve biçimlendirmeyi yapar.

## Hızlı yol (her zaman bunu kullan)

```bash
# 1) TEFAS Excel export'u (birincil)
python -m tefas_matrix --source <indirilen.xlsx> --out Matrix_TEFAS_PPF_<tarih>.xlsx

# 2) Canlı çekim (TEFAS erişilebilirse)
python -m tefas_matrix --live --asof <YYYY-MM-DD> --out Matrix_TEFAS_PPF_<tarih>.xlsx
```

Pipeline; ME hesabı, hariç tutma, ağırlıklı sıralama, formüller, renk kodları,
cross-check ve portföy dağılımını otomatik yapar. **Elle hücre hesaplama!**

## Veri Kaynağı

TEFAS'tan (https://www.tefas.gov.tr/tr/fon-verileri?fundType=YAT) çekilen veri.
TEFAS doğrudan erişilebilir değilse `tefas-crawler` (`--live`) kullanılabilir;
ancak yeni API yalnızca **fiyat** verir (AUM/kişi/portföy dağılımı gelmez).
Tam çıktı için web export'u (`--source`) tercih et.

### TEFAS filtreleri (kullanıcı tarafında):
- Fon adında **"para piyasası"** geçen fonlar
- **Fon Toplam Değer > 2.000.000.000 TL** (config: `MIN_FUND_SIZE`)
- Tarih aralığı: T, T-1, T-7, T-15

### Kaynak dosyadaki sheet hiyerarşisi:
| Sheet | İçerik | Öncelik |
|---|---|---|
| ÖZET DETAY VALUE | Tüm fonların 1G/7G/15G ME'si | BİRİNCİL |
| (tarih) fiyat sheet'leri | Ham fiyat → ME hesaplanır | ÖZET yoksa otomatik yedek |
| Portföy Dağılım | Varlık sınıfı dağılımı (%) | Sheet 2 için |

Pipeline bu sheet'leri otomatik bulur (`tefas_matrix/sources.py`).

## Metodoloji (tefas_matrix/compute.py)

```
yıllık getiri  = (Fiyat_T / Fiyat_T-n − 1) × 365 / n
mevduat eşleniği = yıllık getiri × (1 − fon_stopaj) / (1 − mevduat_stopaj)
```
Beko kurumsal: `fon_stopaj = 0`, `mevduat_stopaj = 0.175` → çarpan 1.2121.
Ağırlıklı ort. = 1G×%50 + 7G×%35 + 15G×%15 (config'de değiştirilebilir).

## Hariç tutulan fonlar (config.EXCLUDE)

`FIL` (Fiba) ve `DL2, DLY, DIP, DVS, DCB, DCN, DNP` (Deniz Portföy) — politika
kararı. **Her çalıştırmada kullanıcıya teyit ettir**, liste değişmiş olabilir.
Hariç tutmamak için `--keep-excluded`.

## Çıktı yapısı

**Sheet 1 – PPF Mevduat Eşleniği:** Sıra · Fon Kodu · Fon Adı · 1G/7G/15G ME +
dönem sıraları · formüllü `AĞIRLIKLI ORT.` (sarı E3/G3/I3 ağırlık hücrelerine
bağlı) · `Fark (2.ye)` · Fon Tutar · Kişi Sayısı · alt CROSS-CHECK bloğu.

**Sheet 2 – Portföy Dağılım:** aynı sırada varlık sınıfı %'leri, otomatik
`Diğer` ile %100'e tamamlanan `TOPLAM` + `Kontrol`. PD'si olmayan fon kırmızı
"PD YOK".

Renk: 1-5 koyu yeşil · 6-10 açık yeşil · 11-15 gri · 16-20 açık gri · 21+ beyaz
· eksik kırmızı. ME `0.00%`, PD `0.00`, ağırlık `0%`.

## Doğrulama ("emin misin" dendiğinde)

1. ME değeri kaynaktaki ham veriyle eşleşmeli (makine hassasiyeti)
2. `AĞIRLIKLI ORT.` hardcoded değil **formül** olmalı
3. Her satır bir üsttekinden ≤ olmalı (azalan)
4. İki sheet'te aynı sırada aynı fon kodu
5. Her fonun PD toplamı ≈ %100
`python -m pytest tests/` bunları otomatik kontrol eder.

## Kurumsal Stopaj Parametresi

Beko KVK 2/1 kapsamında %0 fon stopaj muafiyetine sahiptir; TEFAS ME değerleri
bunu yansıtır. Bireysel karşılaştırmada çarpan: kurumsal 1.2121, bireysel 1.0.

## E-mail Çıktısı

"e-mail yaz" / "Mine Hanım'a gönder" dendiğinde: ilk 5 sıralama (kod + tam ad +
ME%), mevcut pozisyonlar (ILH, YIK) sırası/tutarı, peer karşılaştırma (UCP
referans), piyasa değerlendirmesi (dönem trendi + portföy yapısı). Anti-AI
style kurallarını uygula.
