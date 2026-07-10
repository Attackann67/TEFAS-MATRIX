# Formul Kutuphanesi (openpyxl ile uretilen kaliplar)

Omurga: tum aylar tek "Hesap Detay" sayfasina yigilir (Ay kolonu ile). Ozet sayfalar SUMIFS ile buradan beslenir.
Araliklar: AY=$A, ENT=$B, KOD=$C(hesap kodu), PB=$E/F, TL=$H (yapiya gore uyarlarsin).

## Temel
- Istirak toplami: `=SUMIFS(TL, AY,"2026-05", ENT,$B5)`
- Kategori: `=SUMIFS(TL, AY,"2026-05", KOD,"10203")`
- Vadesiz: `=SUMIFS(...,KOD,"100")+SUMIFS(...,KOD,"10201")`
- Kategori x para birimi: `=SUMIFS(ORG, KOD,"10201", PB,"USD")` (orijinal tutar ayni PB icinde toplanir; TL ayri kolonda)
- Vadesiz %: `=IF(D5=0,0,E5/D5)`  | Likit/Overdue: `=IF(F5=0,"-",C5/F5)`
- EUR cevrim: TL hucre / EURTRY girdi hucresi (mavi, tek nokta; 31.05 icin 53,1224 TCMB) / 1e6 (mn)
- MoM delta: `=E5-D5` ; SORGULA bayragi: `=IF(G5>=$C$2,"SORGULA","")` (C2 = esik, mavi girdi %50)
- Mail kisisellestirme: ic ice `SUBSTITUTE($B$5,"{istirak}",K5)...` + gizli yardimci kolonlar; para birimi kirilimi onceden metin olarak M kolonuna yazilir.

## Kontrol kaliplari (her dosyada zorunlu)
- `=ROUND(SUMIF(ENT,"<>",TL) - <kaynak_toplam>, 2)` -> 0 beklenir
- Satir toplami = kategori toplami: Check kolonu `=ROUND(SUMIF(ENT,$B5,TL)-Total5,2)`
- PASS/FAIL: `=IF(ABS(D5)<0.5,"PASS","FAIL")` + kosullu bicim (PASS yesil E3F4E7, FAIL kirmizi F9D5D3)
- Toleranslar: TL 0,5; mn EUR 0,01; foto/gorsel kaynakli tam sayilar +-5 (yuvarlama notu ile)

## Bilinen sabitler / referans mutabakatlar
- 2026-05 grup: 55.630.216.243 TL (Arcelik 25.251.289.328 + Paz 1.635.371.035 + istirakler 28.743.555.881)
- Arcelik+Paz check: 26.886.660.362,39 | BE cash dosyasi = C746: 162.344.617 EUR
- Overdue 30.06: 536.795 bin | 31.05: 536.751 bin | BE 11 kayit toplami: 320.714 bin (Management tek basina 292.263)
- E251 Romania = 7.151.167 EUR (Catalina pivotu ile birebir - pivotlar EUR'dur)

## Renk/format
Baslik dolgu #002060 beyaz bold Arial; ara grup gri E8EAF0; dikkat sari FFF3C4.
Mavi 0033CC=girdi, siyah=ayni sayfa formul, yesil 0B6E2D=capraz sayfa. Sayi: '#,##0' (TL/EUR tam), '#,##0.0' (mn), '0.0%'.
recalc zorunlu: `python /mnt/skills/public/xlsx/scripts/recalc.py <dosya>` -> total_errors 0 olmadan teslim yok.
