"""TEFAS PPF Matrix yapılandırması.

Tüm politika parametreleri (ağırlıklar, hariç tutulan fonlar, stopaj,
renk kodları ve portföy dağılım sütun eşlemesi) burada toplanır; böylece
analiz mantığı sabit kalırken parametreler kolayca güncellenebilir.
"""

from __future__ import annotations

# --- Dönem ağırlıkları (Sheet 1, satır 3 sarı input hücreleri) ---------------
# Toplam %100 olmalıdır. Excel'de kullanıcı tarafından değiştirilebilir.
WEIGHTS = {"1G": 0.50, "7G": 0.35, "15G": 0.15}

# Dönem -> gün sayısı (yıllıklandırma için)
PERIOD_DAYS = {"1G": 1, "7G": 7, "15G": 15}

# --- Stopaj parametreleri ----------------------------------------------------
# Mevduat eşleniği = yıllık getiri x (1 - fon_stopaj) / (1 - mevduat_stopaj)
# Beko kurumsal yatırımcıdır (KVK 2/1): fon stopajı %0.
FON_STOPAJ = 0.00
MEVDUAT_STOPAJ = 0.175

# --- Hariç tutulan fonlar (politika kararı) ---------------------------------
# FIL = Fiba Portföy; DL2/DLY/DIP/DVS/DCB/DCN/DNP = Deniz Portföy.
# Bu liste değişebilir; her çalıştırmada kullanıcıya teyit ettirin.
EXCLUDE = {"FIL", "DL2", "DLY", "DIP", "DVS", "DCB", "DCN", "DNP"}

# --- TEFAS filtreleri (canlı çekimde uygulanır) ------------------------------
# Fon adında bu ifade geçenler PPF kabul edilir.
NAME_FILTER = "PARA PİYASASI"
# Fon Toplam Değer alt sınırı (TL). None ise filtre uygulanmaz.
MIN_FUND_SIZE = 2_000_000_000

# --- Sheet 2: Portföy Dağılım çıktı sütunları -------------------------------
# (Çıktı başlığı) -> ham TEFAS Portföy Dağılım sütun adları toplamı.
# Ham sheet'te alt kırılımlar (TL/Döviz/Altın, Alım/Satım) ayrı gelir;
# burada anlamlı gruplara toplanır. Listelenmeyen tüm varlık sınıfları
# "Diğer" altında toplanır, böylece TOPLAM her zaman ~%100'e tamamlanır.
PD_OUTPUT_COLUMNS = [
    ("Mevduat (TL) (%)", ["Mevduat (TL) (%)"]),
    ("Ters-Repo (%)", ["Ters-Repo (%)"]),
    ("Devlet Tahvili (%)", ["Devlet Tahvili (%)"]),
    ("Finansman Bonosu (%)", ["Finansman Bonosu (%)"]),
    ("Özel Sektör Tahvili (%)", ["Özel Sektör Tahvili (%)"]),
    ("Varlığa Dayalı MK (%)", ["Varlığa Dayalı Menkul Kıymetler (%)"]),
    ("Takasbank Para P. (%)", ["Takasbank Para Piyasası (%)"]),
    (
        "Kamu Kira Sert. (%)",
        ["Kamu Kira Sertifikaları (TL) (%)", "Kamu Kira Sertifikaları (Döviz) (%)"],
    ),
    ("Hazine Bonosu (%)", ["Hazine Bonosu (%)"]),
    ("Özel Sektör Kira Sert. (%)", ["Özel Sektör Kira Sertifikaları (%)"]),
    (
        "Katılma Hesabı (%)",
        [
            "Katılma Hesabı (TL) (%)",
            "Katılma Hesabı (Döviz) (%)",
            "Katılma Hesabı (Altın) (%)",
        ],
    ),
    (
        "BİST Taahhütlü İşlem (%)",
        [
            "BİST Taahhütlü İşlem Pazarı Alım (%)",
            "BİST Taahhütlü İşlem Pazarı Satım (%)",
        ],
    ),
    ("Borsa İstanbul Para P. (%)", ["Borsa İstanbul Para Piyasası (%)"]),
    # "Diğer (%)" otomatik hesaplanır (kalan tüm sınıflar) -> compute.py
]

# --- Renk kodlaması (ARGB hex) ----------------------------------------------
RANK_FILLS = [
    (5, "FFE2EFDA"),   # 1-5   koyu yeşil
    (10, "FFF2F7EB"),  # 6-10  açık yeşil
    (15, "FFF2F2F2"),  # 11-15 gri
    (20, "FFFAFAFA"),  # 16-20 açık gri
]
DEFAULT_FILL = "FFFFFFFF"   # 21+ beyaz
MISSING_FILL = "FFFDE8E8"   # PD/veri eksik kırmızı
HEADER_FILL = "FF002060"    # başlık koyu lacivert
INPUT_FILL = "FFFFFF00"     # ağırlık input sarı
SEPARATOR_ROWS = {5, 10, 15, 20}
SEPARATOR_COLOR = "FF1F4E79"
