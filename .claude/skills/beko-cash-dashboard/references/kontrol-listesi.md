# Kontrol Listesi ve Bilinen Tuzaklar

## Her teslim oncesi
1. recalc: total_errors = 0.
2. Detay toplami = kaynak dosya toplami (kurus).
3. Her ozet gorunum (kategori, istirak, pivot, EUR) ayni grup toplamina baglanir.
4. Satir bazli Check kolonlari 0.
5. Renk kurali: hardcode edilen her deger MAVI mi? Yeni gelen dis rakam formul gibi siyah yazilmis mi kontrol et.

## Tuzaklar (yasanmis)
- **Birim**: overdue bin EUR; pivotlardaki "Entity Currency Amount" Beko Europe icin EUR. Emin degilsen once dogrula (Romania 7.151.167 vakasi).
- **Kesit farki**: nakit 31.05 / overdue 30.06 / pool gunluk. Ayni tabloda uc tarih olabilir - kolon basligina tarih, nota uyari. Oranlar "gosterge".
- **INF para birimi bos** (bazi aylar): kurdan para birimi cikarma; "(bos)" yaz.
- **Iki Original Amount kolonu** (INF): 9 dolu degilse 10'a bak.
- **Cift isim** (E801 "Beko AE LLCBeko AE LLC"): gosterimde temizle, detayda kaynak haliyle birak.
- **Sifir kur girilen satirlar** (istirak flash): esdeger eksik; orijinal pb'de karsilastir.
- **Turetilmis toplam != resmi rakam**: 320,7 (11 kayit) vs 292,3 (Management, resmi liste). Ust yonetime giden metinde resmi rakam ana, turetilmis toplam etiketli ikinci planda.
- **Bloke nakit**: LC/teminat rehni serbest vadesiz gorunebilir (Gulf 30,5 mn USD). Atil nakit sorgusundan once bloke durumu sor; raporda 10202/10205'e reclass talep et.
- **Faiz tahakkuku = anapara** (Singer 10.216.928 = 10.216.928): kayit hatasi isareti, sorgula.
- **Container reset**: /tmp'deki json/scriptler ucar; kaynak dosyadan yeniden uretilebilir tut (build scriptlerini repoya koy).

## Aylik dongu kontrolu
Ayin 10'u liquid report -> snapshot + analiz | 3. hafta Mali Isler gozden gecirme (takvim 22'si) | oncesinde Morocco/Gulf/Defy sorgu maili | cevaplar snapshot'a islenir.
