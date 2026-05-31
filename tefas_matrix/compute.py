"""Mevduat eşleniği hesabı ve ağırlıklı sıralama mantığı.

Saf hesaplama katmanı: girdi olarak fon bazında fiyat/ME verisi alır,
çıktı olarak sıralanmış DataFrame üretir. Ne dosya okur ne Excel yazar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import pandas as pd

from . import config


def mevduat_esligi(price_t: float, price_ref: float, days: int,
                   fon_stopaj: float = config.FON_STOPAJ,
                   mevduat_stopaj: float = config.MEVDUAT_STOPAJ) -> float:
    """Tek bir dönem için mevduat eşleniğini döndürür.

    Yıllık (basit) getiri = (P_t / P_ref - 1) * 365 / gün
    Mevduat eşleniği = yıllık_getiri * (1 - fon_stopaj) / (1 - mevduat_stopaj)
    """
    annualized = (price_t / price_ref - 1.0) * 365.0 / days
    return annualized * (1.0 - fon_stopaj) / (1.0 - mevduat_stopaj)


@dataclass
class FundRecord:
    """Bir fonun matrix için gereken tüm alanları."""

    code: str
    name: str
    me: Dict[str, float] = field(default_factory=dict)  # {"1G":.., "7G":.., "15G":..}
    fund_size: Optional[float] = None     # Fon Toplam Değer (TL)
    investors: Optional[int] = None       # Kişi Sayısı
    allocation: Dict[str, float] = field(default_factory=dict)  # ham PD sütunları
    tur: str = ""                          # fon türü (Para Piyasası/Serbest/Katılım)
    tefas: Optional[bool] = None           # TEFAS'ta işlem görüyor mu
    getiri1a: Optional[float] = None       # TEFAS yayımlı 1 aylık getiri (cross-check)


def build_matrix(records: Dict[str, FundRecord],
                 weights: Dict[str, float] = None,
                 exclude: set = None) -> pd.DataFrame:
    """Fon kayıtlarından sıralanmış matrix DataFrame'i üretir.

    Sütunlar: Fon Kodu, Fon Adı, {1G,7G,15G} ME, {1G,7G,15G} Sıra,
    AĞIRLIKLI ORT, Fon Tutar, Fon Kişi Sayısı + portföy dağılım sütunları.
    Hariç tutulan fonlar tamamen çıkarılır (sıralamayı etkilemez).
    """
    weights = weights or config.WEIGHTS
    exclude = config.EXCLUDE if exclude is None else exclude

    rows = []
    for code, rec in records.items():
        if code in exclude:
            continue
        if not all(p in rec.me for p in ("1G", "7G", "15G")):
            continue
        rows.append(rec)

    if not rows:
        raise ValueError("Hiç geçerli fon kaydı yok (ME verisi eksik olabilir).")

    df = pd.DataFrame([{
        "Fon Kodu": r.code,
        "Fon Adı": r.name,
        "1G ME": r.me["1G"],
        "7G ME": r.me["7G"],
        "15G ME": r.me["15G"],
        "Fon Tutar": r.fund_size,
        "Fon Kişi Sayısı": r.investors,
        "_alloc": r.allocation,
    } for r in rows])

    # Dönem bazlı sıralar (büyükten küçüğe, hariç fonlar zaten yok)
    for period in ("1G", "7G", "15G"):
        df[f"{period} Sıra"] = (
            df[f"{period} ME"].rank(ascending=False, method="min").astype(int)
        )

    df["AĞIRLIKLI ORT"] = (
        df["1G ME"] * weights["1G"]
        + df["7G ME"] * weights["7G"]
        + df["15G ME"] * weights["15G"]
    )

    df = df.sort_values("AĞIRLIKLI ORT", ascending=False).reset_index(drop=True)
    df.insert(0, "Sıra", range(1, len(df) + 1))
    return df


def portfolio_breakdown(alloc: Dict[str, float]) -> Dict[str, float]:
    """Ham TEFAS PD sütunlarını çıktı gruplarına toplar ve 'Diğer'i hesaplar.

    'Diğer' = listelenmeyen tüm varlık sınıflarının toplamı, böylece
    her satır ~%100'e tamamlanır. alloc boşsa boş sözlük döner (PD YOK).
    """
    if not alloc:
        return {}

    def num(v):
        try:
            f = float(v)
            return 0.0 if pd.isna(f) else f
        except (TypeError, ValueError):
            return 0.0

    out: Dict[str, float] = {}
    used = set()
    for label, sources in config.PD_OUTPUT_COLUMNS:
        out[label] = round(sum(num(alloc.get(s)) for s in sources), 4)
        used.update(sources)

    total_all = sum(num(v) for k, v in alloc.items())
    mapped = sum(out.values())
    out["Diğer (%)"] = round(total_all - mapped, 4)
    return out
