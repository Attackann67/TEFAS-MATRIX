# Veri Modeli - Kaynak Dosyalar

## 1. Liquid Assets formu (aylik, "Liquid_Assets_MMYY_value.xlsx")
- Istirakler: sheet **Form25a-Assets-YD**, baslik satir 11, veri 12+.
  Kolonlar (1-index): 5=Subsidaries ("E625 - Beko Gulf"), 6=Account ("10201 - Demand deposits..."),
  8=Item/Banka, 9=Original Amount, 10=Currency Rate, 11=Entity Currency Amount (TL),
  12=Interest Rate, 14=Maturity, 16=Original Currency.
- Arcelik + Pazarlama: sheet **Form25a-Assets INF** (enflasyon duzeltmeli), ayni satir yapisi,
  kolonlar: 9=Orig1, 10=Orig2 (ikisi de dolu olabilir; 9'u kullan), 11=Rate, 12=TL, 13=IR, 15=Mat, 17=Ccy.
  Sadece "E046 - Arçelik A.Ş." ve "E601 - Pazarlama A.Ş." satirlarini al.
  DIKKAT: bazi aylarda INF para birimi kolonu BOS (Sub/Nis 2026 ornegi) - para birimi analizi o ay icin kurulamaz, "(bos)" etiketle, kurdan cikarim YAPMA.
- Bilinen fark: Sheet2 konsolide ozeti ile satir detayi arasinda 11.386.549,99 TL fark (2026-05). Detayi esas al, farki notla.

## 2. Kategori kodlari ve gruplama
| Kod | EN | TR | Grup |
|---|---|---|---|
| 100 | Cash on Hand | Kasa | Vadesiz |
| 10201 | Demand deposits | Vadesiz mevduat | Vadesiz |
| 10202 | Blocked demand | Bloke vadesiz | Diger |
| 10203 | Cash pool deposit | Nakit havuzu | Pool |
| 10204 | Time deposits | Vadeli mevduat | Vadeli |
| 10205 | Blocked time | Bloke vadeli | Vadeli |
| 104 | Interest accrual | Faiz tahakkuku | Vadeli |
| 101 | Cheques received | Alinan cekler | Diger |
| 105 | Credit card receiv. | KK alacaklari | Diger |
| 109 | Other liquid | Diger likit | Diger |
Vadesiz = 100+10201. Vadeli = 10204+104+10205. Pool = 10203. Diger = kalan.

## 3. Overdue listesi ("Istirak alacak ve overdue", Hakan Deveci)
- Sheet2, baslik r2 (bir kolon kaymis olabilir - degerden dogrula), veri r3+.
- Kolonlar: 5=Bolge, 6=Istirak adi (kod YOK), 9=Toplam Alacak, 10=Net Overdue (guncel ay), 17=Net Overdue (onceki ay).
- BIRIM: bin EUR ("000 silinmis"; 323.220 = 323,22 mn EUR).
- Yapi: ana blok -> "EUR Toplam" satiri -> "Diger" detay blogu -> negatif blok. SADECE ana blogu kullan; toplami dosyanin kendi EUR Toplam satirina bagla.

## 4. Beko Europe Cash Report (LE bazli, EUR)
- Sheet "Cash", veri r3+: 2=LE adi ("E251 - Beko Romania S.A."), 3=Account, 5=Item, 6=Orig, 7=Rate, 8=Ccy, 9=EUR, 10=IR.
- 24 tuzel kisilik; toplam = grup formundaki C746 EUR karsiligi (dogrulama kancasi).
- Beko Europe Management S.R.L. (kod ~779) BU DOSYADA YOK - nakit verisi hicbir kaynakta yok.

## 5. Citi pool raporu (gunluk, EUR)
- Katilimci bazli SUM EURO BALANCE, iki gun yan yana.
- "Istiraklerin Pool Bakiyesi" = Grand Total - Arcelik Anonim Sirketi.
- BEKO INTERNATIONAL SA = eski Indesit Co Int. Businesssa = overdue'daki "Beko S.A.".
- BEKO EUROPE BV = JV holding; C746 konsolidasyon dugumu DEGIL, E746 LE DEGIL.

## 6. Istirak flash raporlari (orn. IHP/Beko LLC daily)
- Yapi serbest; oku, kalem bazinda onceki resmi kesitle ORIJINAL para biriminde karsilastir.
- Kur 0 girilmis satirlar olabilir - esdegerler eksik, isaretle.
