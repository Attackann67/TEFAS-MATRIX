"""Sabitler ve sema: kategori kodlari, gruplama, segment haritasi, renkler.

Kaynak: .claude/skills/beko-cash-dashboard/references/veri-modeli.md (bolum 2)
ve SKILL.md kayit semasi. Tek dogruluk noktasi burasidir; hesap ve dashboard
katmanlari bu tanimlari kullanir.
"""

from __future__ import annotations

# --- Kategori kodlari ve 4 grup (veri-modeli.md bolum 2) ---------------------
# Vadesiz = 100 + 10201 | Vadeli = 10204 + 104 + 10205 | Pool = 10203 | Diger = kalan
CATEGORY_GROUP = {
    "100": "Vadesiz",
    "10201": "Vadesiz",
    "10202": "Diger",   # bloke vadesiz
    "10203": "Pool",
    "10204": "Vadeli",
    "10205": "Vadeli",  # bloke vadeli
    "104": "Vadeli",    # faiz tahakkuku
    "101": "Diger",
    "105": "Diger",
    "109": "Diger",
}

# Snapshot'ta kaydedilen 4 grup alani -> gorunen ad
GROUPS = ["Vadesiz", "Vadeli", "Pool", "Diger"]
GROUP_FIELD = {"Vadesiz": "vad_tl", "Vadeli": "vdl_tl", "Pool": "pool_tl", "Diger": "dig_tl"}

# 10 kategori kodu - gorunum sirasi ve TR etiket (gercek Kategori Analizi ile ayni)
CATEGORY_ORDER = ["100", "10201", "10202", "10203", "10204", "10205", "104", "101", "105", "109"]
CATEGORY_LABEL = {
    "100": "Kasa",
    "10201": "Vadesiz mevduat",
    "10202": "Bloke vadesiz",
    "10203": "Nakit havuzu (pool)",
    "10204": "Vadeli mevduat",
    "10205": "Bloke vadeli",
    "104": "Faiz tahakkuku",
    "101": "Alinan cekler",
    "105": "KK alacaklari",
    "109": "Diger likit",
}


def groups_from_cat(cat_tl: dict) -> dict:
    """10-kod cat_tl haritasindan 4 grup toplami turetir (vad/vdl/pool/dig)."""
    out = {g: 0.0 for g in GROUPS}
    for code, tl in (cat_tl or {}).items():
        grp = CATEGORY_GROUP.get(str(code), "Diger")
        out[grp] += float(tl or 0)
    return out

# --- Segment haritasi (SKILL: grup + segment) --------------------------------
# Arcelik ve Pazarlama ayri segment; kalan hepsi Istirakler.
ARCELIK = "E046"
PAZARLAMA = "E601"
BEKO_EUROPE = "C746"  # konsolide tek satir


def segment_of(code: str) -> str:
    if code == ARCELIK:
        return "Arcelik"
    if code == PAZARLAMA:
        return "Pazarlama"
    return "Istirakler"


SEGMENTS = ["Istirakler", "Arcelik", "Pazarlama"]

# --- Renk paleti (SKILL kirmizi cizgiler + formuller.md) ---------------------
C_HEADER = "FF002060"      # baslik dolgu (lacivert)
C_HEADER_TXT = "FFFFFFFF"  # baslik yazi (beyaz)
C_INPUT = "FF0033CC"       # mavi = dis kaynak girdi
C_SAME = "FF000000"        # siyah = ayni sayfa formul
C_CROSS = "FF0B6E2D"       # yesil = capraz sayfa formul
C_GROUP = "FFE8EAF0"       # ara grup gri
C_WARN = "FFFFF3C4"        # dikkat sari
C_PASS = "FFE3F4E7"        # PASS yesil dolgu
C_FAIL = "FFF9D5D3"        # FAIL kirmizi dolgu

# Sayi bicimleri
FMT_TL = "#,##0"
FMT_MN = "#,##0.0"
FMT_PCT = "0.0%"
FMT_RATIO = '0.00;-0.00;"-"'

# --- Toleranslar (formuller.md) ----------------------------------------------
TOL_TL = 0.5
TOL_MN_EUR = 0.01

# SORGULA esigi: vadesiz orani bu degeri asarsa bayrak (SKILL varsayilan %50)
SORGULA_ESIK = 0.50
