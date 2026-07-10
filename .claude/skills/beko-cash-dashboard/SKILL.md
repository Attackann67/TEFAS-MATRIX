---
name: beko-cash-dashboard
description: Beko Corporate Treasury nakit-overdue dashboard ve kayit sistemi. Aylik liquid assets formu, overdue listesi, Citi pool raporu ve istirak flash raporlarini isler; istirak bazli atil nakit analizi, nakit-overdue karsilastirmasi, trend takibi ve sorgu yazismalari uretir. Kullanici "liquid report analiz", "overdue karsilastir", "atil nakit", "cash dashboard", "aylik kapanis", "istirak sorgusu", "pool bakiyeleri" dediginde veya Form25a / overdue / Citi pool dosyasi yuklediginde devreye al.
---

# Beko Cash Dashboard

Aylik dongu: liquid report gelir (ayin ~10'u) -> analiz + kayit -> overdue listesi gelir -> karsilastirma -> Mali Isler gozden gecirmesi (3. hafta) -> istirak sorgulari -> cevaplar kayda islenir.

Bu depodaki `beko_cash` paketi kayit + analiz + dashboard uretimini yapar.
**Elle hucre hesaplama yok**; ozet sayfalar canli SUMIFS ile detaya baglidir.

## Hizli yol (her zaman bunu kullan)

```bash
# 1) Kaynak Excel'lerden aylik kayit (snapshot) uret - Hesap Detay omurgasi + overdue + pool
python -m beko_cash extract \
    --detail <trend_veya_hesap_detay>.xlsx --sheet "Hesap Detay" \
    --overdue <Nakit_vs_Overdue>.xlsx --pool <Citi_Pool>.xlsx \
    --month 2026-05 --eurtry 53.1224 --sheet2-gap 11386549.99

# 2) Kayitlari dogrula (kontrol-listesi kurallari)
python -m beko_cash validate

# 3) Dashboard Excel uret (10 sayfa, canli formullu)
python -m beko_cash build --out Beko_Cash_Dashboard_<ay>.xlsx

# 4) ZORUNLU: formulleri dogrula (total_errors 0 olmadan teslim yok)
python /mnt/skills/public/xlsx/scripts/recalc.py Beko_Cash_Dashboard_<ay>.xlsx

# Ek: yeni ay iskelesi / insana okunur ozet
python -m beko_cash new --month 2026-06 --eurtry 53.50
python -m beko_cash summary
```

Kayitlar `data/snapshots/YYYY-MM.json` altinda tutulur (kayit sistemi = tek
gercek). Dashboard bu dosyalardan uretilir; kaynak Excel'ler ucsa bile kayittan
yeniden uretilebilir.

## Calisma sirasi
1. `references/veri-modeli.md` oku: kaynak dosya yapilari, kolon haritalari, kategori kodlari.
2. `beko_cash extract` ile veriyi cikar, HER AY ayni kurallarla. Kolonlar baslik adindan bulunur; kaymayi tolere eder. Cikarim sonrasi `validate` ile kontrol toplamlarini dogrula (`references/kontrol-listesi.md`).
3. Kayit sistemine yazilir: `data/snapshots/YYYY-MM.json`. Onceki aylar varsa trend otomatik guncellenir.
4. `beko_cash build` Excel ciktisini `references/formuller.md` kurallariyla uretir. Tum ozet sayfalar canli SUMIFS ile detaya bagli; hardcode sadece dis kaynak girdilerde (mavi): Kayit Detay TL, Girdi sayfasi eurtry/kaynak/esik.
5. Overdue geldiginde extract `--overdue` ile eslestirir; `references/eslesme-tablosu.md` guven etiketini (Kesin/Olasi/Eslesmedi) kaynaktan tasir. Yeni/eslesmeyen isim cikarsa SORMADAN eslestirme, kullaniciya sor.
6. Sorgu maili/Teams mesaji gerekiyorsa `references/yazismalar.md` sablonlarini kullan; rakamlari orijinal para biriminde ver.

## Kayit semasi (data/snapshots/YYYY-MM.json)
```json
{
  "month": "2026-05",
  "eurtry": 53.1224,
  "source_total_tl": 55630216242.99,
  "entities": {
    "E625": {"name": "Beko Gulf", "tot_tl": 2123915923.31,
              "cat_tl": {"10201": 1749597738.0, "10204": 374318185.31},
              "overdue_keur": 17017.10825, "overdue_prev_keur": 13378.33436,
              "citi_pool_eur": null, "match": "Olasi",
              "status": "LC teminat - netting",
              "sorgu": {"gonderildi": "2026-07-03", "cevap": null, "ozet": "..."}}
  },
  "pool": {"grand_total_eur": 79877427, "arcelik_eur": 149938904, "participants": {...}},
  "checks": {"detail_vs_source": 0, "sheet2_gap": 11386549.99}
}
```
`cat_tl` = 10 kategori kodu bazinda TL (birincil). 4 grup (Vadesiz/Vadeli/Pool/Diger)
buradan turetilir. `cat_tl` yoksa vad_tl/vdl_tl/pool_tl/dig_tl alanlari da desteklenir.
Her analiz sonrasi snapshot guncellenir; dashboard bu dosyalardan beslenir.

## Dashboard sayfalari (beko_cash build)
- **Ozet**: son kesit, segment dagilimi, sayfa rehberi
- **Girdi**: mavi tek nokta - ay x (eurtry, kaynak toplam), SORGULA esigi
- **Kayit Detay**: tum aylar tek uzun sayfa (Ay/Kod/Istirak/Segment/Grup/Kat Kod/TL) - SUMIFS omurgasi
- **Kayit Entity**: ay-istirak skalerler (toplam, overdue, pool, statu, eslesme)
- **Grup Trend**: segment (istirakler/Arcelik/Pazarlama) x ay, TL ve mn EUR
- **Kategori Trend**: 10 kod x ay; vadesiz MoM sicramasi sari
- **Istirak Matris**: istirak x ay + vadesiz orani + SORGULA bayragi (esik hucresi)
- **Nakit vs Overdue**: likit mn EUR / overdue mn EUR orani; kesit farki her zaman etikette
- **Citi Pool**: katilimci bakiyeleri + "Istiraklerin Pool = Grand Total - Arcelik"
- **Acik Sorgular**: kim, ne zaman soruldu, cevap durumu
- **Kontrol**: detay vs kaynak, Sheet2 gap, PASS/FAIL

## Kirmizi cizgiler
- Kaynaksiz rakam yazma. Turetilmis toplam (orn. Beko Europe 320,7) her zaman "X kaydin toplami" etiketiyle; resmi listedeki rakamla (292,3) karistirma.
- Kesit farkli verileri tek oranda birlestirme; birlestirirsen not zorunlu (nakit 31.05 / overdue 30.06 / pool gunluk).
- LC/teminat bloke nakdi "atil" sayma (Gulf ornegi). Bloke sinifi (10202/10205) dogru mu kontrol et; extract sonrasi `validate` uyari verir.
- Renk: basliklar #002060; mavi=girdi, siyah=ayni sayfa formul, yesil=capraz sayfa, sari=dikkat. Em-dash yasak; "lazim" yasak.
