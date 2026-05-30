"""Veri kaynakları: TEFAS Excel export'u okuma + canlı fiyat çekimi.

İki giriş yolu:
  1) from_workbook(path)  -> TEFAS'tan indirilen Excel export'u (SKILL'deki
     akış). Birincil ve en güvenilir yol.
  2) from_live(asof)      -> tefas-crawler ile canlı fiyat çekimi. TEFAS
     erişilebilir olduğunda kullanılır; yeni TEFAS API'si yalnızca fiyat
     verir, AUM/kişi sayısı/portföy dağılımı artık public değildir.
"""

from __future__ import annotations

import datetime as _dt
import warnings
from typing import Dict, List, Optional

import pandas as pd

from . import config
from .compute import FundRecord, mevduat_esligi

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


# ---------------------------------------------------------------------------
# 1) Excel export okuma
# ---------------------------------------------------------------------------

_INFO_REQUIRED = {"Fon Kodu", "Fiyat"}
_PD_SHEET_NAMES = ("Portföy Dağılım", "Portföy Dağılım ", "Portfoy Dagilim")


def _read_info_sheets(xls: pd.ExcelFile) -> Dict[_dt.date, pd.DataFrame]:
    """Tarih bazlı fiyat/info sheet'lerini {tarih: df} olarak döndürür."""
    out = {}
    for name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=name, header=0)
        except Exception:
            continue
        cols = set(map(str, df.columns))
        if not _INFO_REQUIRED.issubset(cols):
            continue
        if "Tarih" not in cols or df.empty:
            continue
        try:
            d = pd.to_datetime(df["Tarih"].iloc[0]).date()
        except Exception:
            continue
        out[d] = df.set_index("Fon Kodu")
    return out


def _read_portfolio(xls: pd.ExcelFile) -> Optional[pd.DataFrame]:
    for name in xls.sheet_names:
        if str(name).strip() in (n.strip() for n in _PD_SHEET_NAMES):
            df = pd.read_excel(xls, sheet_name=name, header=0)
            if "Fon Kodu" in df.columns:
                return df.set_index("Fon Kodu")
    return None


def _read_ozet_detay_value(xls: pd.ExcelFile) -> Optional[Dict[str, Dict]]:
    """ÖZET DETAY VALUE sheet'inden 3 dönem ME + fon büyüklüğü çeker.

    Sheet'te 'No' başlıklı 3 tablo (1G/7G/15G) vardır. col1=kod, col2=ad,
    col8=Mevduat Eşleniği, (1G tablosunda) col9=Fon Toplam Değer.
    """
    target = None
    for name in xls.sheet_names:
        if "ÖZET DETAY VALUE" in str(name).upper().replace("I", "İ").upper() \
                or str(name).strip().upper() == "ÖZET DETAY VALUE":
            target = name
            break
    if target is None:
        return None

    raw = pd.read_excel(xls, sheet_name=target, header=None)
    # 'No' başlık satırlarını bul -> her tablo başlangıcı
    header_rows = [i for i in range(len(raw))
                   if str(raw.iat[i, 0]).strip() == "No"]
    if len(header_rows) < 3:
        return None
    periods = ["1G", "7G", "15G"]
    data: Dict[str, Dict] = {}
    for pi, hr in enumerate(header_rows[:3]):
        period = periods[pi]
        r = hr + 1
        while r < len(raw):
            code = raw.iat[r, 1]
            if pd.isna(code) or str(code).strip() == "":
                break
            code = str(code).strip()
            me = raw.iat[r, 8]
            rec = data.setdefault(code, {"name": str(raw.iat[r, 2]).strip(),
                                         "me": {}, "fund_size": None})
            try:
                rec["me"][period] = float(me)
            except (TypeError, ValueError):
                pass
            if period == "1G":
                try:
                    rec["fund_size"] = float(raw.iat[r, 9])
                except (TypeError, ValueError):
                    pass
            r += 1
    return data


def from_workbook(path: str) -> Dict[str, FundRecord]:
    """TEFAS export'undan fon kayıtlarını üretir.

    ME kaynağı: önce 'ÖZET DETAY VALUE', yoksa tarih bazlı fiyat
    sheet'lerinden hesaplanır. Fon büyüklüğü/kişi sayısı en güncel info
    sheet'inden, portföy dağılımı 'Portföy Dağılım' sheet'inden alınır.
    """
    xls = pd.ExcelFile(path)
    info = _read_info_sheets(xls)
    pd_sheet = _read_portfolio(xls)
    ozet = _read_ozet_detay_value(xls)

    if not info and not ozet:
        raise ValueError(
            "Kaynak dosyada ne fiyat sheet'i ne de 'ÖZET DETAY VALUE' bulundu."
        )

    latest = max(info) if info else None
    latest_df = info[latest] if latest is not None else None

    # ME kaynağı
    if ozet:
        me_by_code = {c: v["me"] for c, v in ozet.items()}
        name_by_code = {c: v["name"] for c, v in ozet.items()}
        size_by_code = {c: v.get("fund_size") for c, v in ozet.items()}
    else:
        me_by_code, name_by_code, size_by_code = _compute_me_from_prices(info)

    records: Dict[str, FundRecord] = {}
    for code, me in me_by_code.items():
        name = name_by_code.get(code, code)
        if latest_df is not None and code in latest_df.index:
            row = latest_df.loc[code]
            name = str(row.get("Fon Adı", name))
        rec = FundRecord(code=code, name=name, me=me)
        # Fon büyüklüğü
        rec.fund_size = size_by_code.get(code)
        if rec.fund_size is None and latest_df is not None and code in latest_df.index:
            v = latest_df.loc[code].get("Fon Toplam Değer")
            rec.fund_size = float(v) if pd.notna(v) else None
        # Kişi sayısı
        if latest_df is not None and code in latest_df.index:
            v = latest_df.loc[code].get("Kişi Sayısı")
            try:
                rec.investors = int(v) if pd.notna(v) else None
            except (TypeError, ValueError):
                rec.investors = None
        # Portföy dağılımı
        if pd_sheet is not None and code in pd_sheet.index:
            rec.allocation = pd_sheet.loc[code].to_dict()
        records[code] = rec
    return records


def _compute_me_from_prices(info: Dict[_dt.date, pd.DataFrame]):
    """Tarih bazlı fiyat sheet'lerinden 1G/7G/15G ME hesaplar.

    Hedef boşluklar (1,7,15 gün) için T tarihine en yakın sheet seçilir;
    yıllıklandırmada nominal gün (1/7/15) kullanılır (TEFAS konvansiyonu).
    """
    dates = sorted(info)
    T = dates[-1]
    price_T = info[T]["Fiyat"]
    name_col = info[T].get("Fon Adı")

    chosen = {}
    for period, gap in config.PERIOD_DAYS.items():
        target = T - _dt.timedelta(days=gap)
        ref_date = min(dates[:-1], key=lambda d: abs((d - target).days)) \
            if len(dates) > 1 else None
        chosen[period] = ref_date

    me_by_code: Dict[str, Dict[str, float]] = {}
    for code in price_T.index:
        me = {}
        ok = True
        for period, gap in config.PERIOD_DAYS.items():
            ref_date = chosen[period]
            if ref_date is None or code not in info[ref_date].index:
                ok = False
                break
            p_t = float(price_T[code])
            p_ref = float(info[ref_date]["Fiyat"][code])
            # Canlı veride bazı fonların belirli tarihte fiyatı 0/NaN
            # gelebilir (yeni kurulan fon vb.) -> ME hesaplanamaz, fonu atla.
            if not (p_t > 0 and p_ref > 0):
                ok = False
                break
            me[period] = mevduat_esligi(p_t, p_ref, gap)
        if ok:
            me_by_code[code] = me
    name_by_code = {c: (str(name_col[c]) if name_col is not None and c in name_col.index else c)
                    for c in me_by_code}
    size_by_code = {c: None for c in me_by_code}
    return me_by_code, name_by_code, size_by_code


def filter_ppf(records: Dict[str, FundRecord],
               name_filter: str = config.NAME_FILTER,
               min_size: Optional[float] = config.MIN_FUND_SIZE) -> Dict[str, FundRecord]:
    """Para piyasası fonu adı + minimum büyüklük filtresini uygular."""
    nf = name_filter.upper()
    out = {}
    for code, rec in records.items():
        if nf and nf not in rec.name.upper():
            continue
        if min_size is not None and rec.fund_size is not None and rec.fund_size < min_size:
            continue
        out[code] = rec
    return out


# ---------------------------------------------------------------------------
# 2) Canlı çekim (tefas-crawler)
# ---------------------------------------------------------------------------

# Liste endpoint'i PPF evrenini tek istekte (kod + ad + tür) döndürür;
# böylece yalnızca para piyasası fonları için fiyat çekilir. Yeni TEFAS
# API'si toplu (bulk-by-date) sorguyu artık desteklemiyor (boş döner) ve
# isimsiz `fetch` ~400 fon × her tarih için bir HTTP isteğine açılıp
# hız sınırına (503 -> 403) takılıyor. Bu yüzden önce evreni daraltıp
# fon başına zaman serisini throttle'lı çekiyoruz.
_LIST_PAYLOAD = {
    "dil": "TR", "fonTipi": "YAT", "kurucuKodu": None, "sfonTurKod": None,
    "fonTurAciklama": None, "islem": 1, "fonTurKod": None, "fonGrubu": None,
    "donemGetiri1a": "1", "donemGetiri3a": "1", "donemGetiri6a": "1",
    "donemGetiri1y": "1", "donemGetiriyb": "1", "donemGetiri3y": "1",
    "donemGetiri5y": "1", "basTarih": None, "bitTarih": None,
    "calismaTipi": 2, "getiriOrani": "1",
}


def _list_ppf_funds(crawler, name_filter: str = config.NAME_FILTER):
    """Liste endpoint'inden para piyasası fonlarını (kod, ad) döndürür.

    Tek HTTP isteği; adında `name_filter` (varsayılan 'PARA PİYASASI')
    geçen YAT fonlarını süzer.
    """
    rows = crawler._do_post(crawler.list_endpoint, _LIST_PAYLOAD)
    nf = name_filter.upper()
    out = []
    for r in rows:
        name = str(r.get("fonUnvan", "")).strip()
        code = r.get("fonKodu")
        if code and nf in name.upper():
            out.append((str(code).strip(), name))
    return out


def _fetch_series_throttled(crawler, code, start, end,
                            delay=0.25, retries=4):
    """Tek fonun fiyat zaman serisini hız sınırına dayanıklı çeker.

    503/403 (rate-limit) durumunda üstel backoff (2s,4s,8s,16s) ile yeniden
    dener. Her çağrı arasında `delay` saniye bekleyerek flood'u önler.
    """
    import time
    from requests.exceptions import HTTPError

    for attempt in range(retries + 1):
        try:
            df = crawler.fetch(start=start.isoformat(), end=end.isoformat(),
                               name=code, columns=["code", "date", "title", "price"])
            time.sleep(delay)
            return df
        except HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status in (403, 503) and attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            raise


def from_live(asof: Optional[str] = None,
              delay: float = 0.25) -> Dict[str, FundRecord]:
    """tefas-crawler ile canlı fiyat çekip ME hesaplar (throttle'lı).

    Önce liste endpoint'inden para piyasası fonu evrenini (tek istek) alır,
    sonra yalnızca bu fonlar için fiyat zaman serisini fon başına bir istekle,
    hız sınırına dayanıklı (gecikme + backoff) çeker. Eski toplu fan-out
    (~400 fon × her tarih) TEFAS tarafından 503/403 ile sınırlandığından
    kullanılmaz.

    asof: 'YYYY-MM-DD' (T günü). None ise bugün denenir.
    NOT: Yeni TEFAS API'si yalnızca fiyat döndürür; fon büyüklüğü, kişi
    sayısı ve portföy dağılımı public olarak gelmez -> bu alanlar None
    kalır ve Sheet 2 'PD YOK' olarak işaretlenir. Bu veriler için TEFAS
    web export'unu kullanın (from_workbook).
    """
    try:
        from tefas import Crawler
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("tefas-crawler kurulu değil: pip install tefas-crawler") from e

    T = _dt.date.fromisoformat(asof) if asof else _dt.date.today()
    # Hafta sonu ise en son cuma'ya çek
    while T.weekday() >= 5:
        T -= _dt.timedelta(days=1)

    # En uzun dönem (15G) + tatil/hafta sonu payı kadar geriye git.
    max_gap = max(config.PERIOD_DAYS.values())
    window_start = T - _dt.timedelta(days=max_gap + 12)

    crawler = Crawler()
    ppf = _list_ppf_funds(crawler)
    if not ppf:
        raise RuntimeError("Liste endpoint'inden hiç para piyasası fonu gelmedi.")

    # (code, date, price, title) uzun tablosu -> tarih bazlı panel
    rows: List[dict] = []
    for code, _name in ppf:
        df = _fetch_series_throttled(crawler, code, window_start, T, delay=delay)
        if df is None or df.empty:
            continue
        for rec in df.to_dict("records"):
            rows.append(rec)

    if not rows:
        raise RuntimeError(f"{T} civarı için hiç PPF fiyatı alınamadı.")

    panel = pd.DataFrame(rows)
    panel = panel[panel["date"] <= T]
    info_like: Dict[_dt.date, pd.DataFrame] = {}
    for d, grp in panel.groupby("date"):
        df_d = grp.rename(columns={"price": "Fiyat", "title": "Fon Adı"})
        df_d = df_d.drop_duplicates(subset="code", keep="last").set_index("code")
        info_like[d] = df_d[["Fiyat", "Fon Adı"]]

    me_by_code, name_by_code, _ = _compute_me_from_prices(info_like)
    return {c: FundRecord(code=c, name=name_by_code.get(c, c), me=me)
            for c, me in me_by_code.items()}
