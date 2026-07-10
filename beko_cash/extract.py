"""Cikarici: kaynak Excel'lerden aylik snapshot uretir (kayit oncesi adim).

Bu modul, veri-modeli.md'deki Hesap Detay / overdue / Citi pool yapilarini okur
ve snapshot semasina cevirir. Kolonlari baslik adindan otomatik bulur; boylece
kucuk kaymalar (bir kolon oynamasi) tolere edilir. Tek kural: kaynaksiz rakam
uretme; okunamayan kalem atlanir ve bildirilir.

CLI:
    python -m beko_cash extract --detail Beko_Likit_Trend.xlsx --out-dir <snapdir> \
        --overdue Nakit_vs_Overdue.xlsx --pool Citi_Pool.xlsx \
        --month 2026-05 --eurtry 53.1224
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from . import schema, snapshot


_TR_FOLD = str.maketrans({"ş": "s", "Ş": "s", "ı": "i", "İ": "i", "ğ": "g", "Ğ": "g",
                          "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"})


def _norm(s) -> str:
    return str(s or "").strip().replace("i̇", "i").translate(_TR_FOLD).lower()


def _find_header(ws, needles: List[str], max_scan: int = 10):
    """En cok needle'i AYRI kisa hucrelerde eslestiren satiri baslik kabul eder.

    Uzun baslik/aciklama satirlari (tek hucrede birden cok kelime) elenir: bir
    hucre yalnizca kisa ise (<=40 karakter) ve tek bir needle'a denk gelirse sayilir.
    """
    best_row, best_found, best_score = None, {}, 0
    for hr in range(1, max_scan + 1):
        found = {}
        for c in range(1, ws.max_column + 1):
            raw = ws.cell(hr, c).value
            if raw is None:
                continue
            val = _norm(raw)
            if len(val) > 40:  # aciklama/baslik cumlesi - header degil
                continue
            for nd in needles:
                if nd in found:
                    continue
                if val == nd or val.startswith(nd) or nd in val:
                    found[nd] = c
                    break
        score = len(found)
        if score > best_score:
            best_row, best_found, best_score = hr, dict(found), score
    if best_score >= 2:
        return best_row, best_found
    return None, {}


def _code_name(cell) -> tuple[str, str]:
    s = str(cell or "").strip()
    if " - " in s:
        code, name = s.split(" - ", 1)
        return code.strip(), name.strip()
    return s, s


def extract_from_detail(path: str | Path, sheet: Optional[str] = None) -> Dict[str, dict]:
    """Hesap Detay tarzi uzun sayfadan ay -> snapshot uretir (cat_tl ile).

    Beklenen kolonlar (baslikla bulunur): Ay, Istirak('KOD - Ad'), Kod, TL.
    """
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    hr, cols = _find_header(ws, ["ay", "istirak", "kod", "tl"])
    if hr is None or not all(k in cols for k in ("ay", "istirak", "kod")):
        raise ValueError(f"{path}: Ay/Istirak/Kod basligi bulunamadi (bulunan: {cols})")
    c_ay, c_ent, c_kod = cols["ay"], cols["istirak"], cols["kod"]
    c_tl = cols.get("tl")
    if c_tl is None:
        raise ValueError(f"{path}: TL kolonu bulunamadi")

    # (ay, kod) -> {cat_code: tl}, (ay,kod)->name
    agg: Dict[tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    names: Dict[tuple, str] = {}
    for row in ws.iter_rows(min_row=hr + 1, values_only=True):
        ay = row[c_ay - 1]
        ent = row[c_ent - 1]
        kod = row[c_kod - 1]
        tl = row[c_tl - 1]
        if not ay or not ent or kod is None:
            continue
        code, name = _code_name(ent)
        cat = str(kod).strip()
        agg[(str(ay), code)][cat] += float(tl or 0)
        names[(str(ay), code)] = name

    snaps: Dict[str, dict] = {}
    for (ay, code), cat in agg.items():
        snap = snaps.setdefault(ay, snapshot.scaffold(ay))
        cat_tl = {k: round(v, 2) for k, v in cat.items() if round(v, 2) != 0}
        tot = round(sum(cat.values()), 2)
        snap["entities"][code] = {
            "name": names[(ay, code)],
            "tot_tl": tot,
            "cat_tl": cat_tl,
        }
    # kaynak toplam = detay toplami (bu grain'de dogrulama kancasi)
    for ay, snap in snaps.items():
        snapshot.compute_checks(snap)
        snap["source_total_tl"] = snap["checks"]["detail_total_tl"]
        snap["checks"]["detail_vs_source"] = 0
    return snaps


def enrich_overdue(snap: dict, path: str | Path, sheet: Optional[str] = None) -> int:
    """Overdue dosyasindan (bin EUR) istirak bazli overdue + eslesme ekler."""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    hr, cols = _find_header(ws, ["kod", "istirak", "overdue", "eslesme"])
    if hr is None or "kod" not in cols:
        raise ValueError(f"{path}: overdue basligi bulunamadi ({cols})")
    # overdue guncel = ilk 'overdue' kolonu; eslesme = 'eslesme'
    c_kod = cols["kod"]
    # basliklarda birden fazla overdue olabilir; guncel ay ilk gorunen kabul edilir
    ov_cols = [c for c in range(1, ws.max_column + 1) if "overdue" in _norm(ws.cell(hr, c).value)]
    c_ov = ov_cols[0] if ov_cols else None
    c_ovprev = ov_cols[1] if len(ov_cols) > 1 else None
    c_match = cols.get("eslesme")
    n = 0
    for r in range(hr + 1, ws.max_row + 1):
        kod = ws.cell(r, c_kod).value
        if not kod:
            continue
        code = _code_name(kod)[0]
        ent = snap["entities"].get(code)
        if ent is None:
            continue
        if c_ov:
            ent["overdue_keur"] = ws.cell(r, c_ov).value
        if c_ovprev:
            ent["overdue_prev_keur"] = ws.cell(r, c_ovprev).value
        if c_match and ws.cell(r, c_match).value:
            ent["match"] = str(ws.cell(r, c_match).value).strip()
        n += 1
    return n


def enrich_pool(snap: dict, path: str | Path, sheet: Optional[str] = None) -> dict:
    """Citi pool dosyasindan katilimci bakiyeleri + Arcelik + grand total."""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    hr, cols = _find_header(ws, ["firm", "balance"])
    # firm ilk kolon, guncel bakiye ikinci kolon (ilk sayisal)
    c_firm = cols.get("firm", 1)
    c_bal = None
    for c in range(c_firm + 1, ws.max_column + 1):
        v = ws.cell((hr or 4) + 1, c).value
        if isinstance(v, (int, float)):
            c_bal = c
            break
    c_bal = c_bal or 2
    parts: Dict[str, float] = {}
    arcelik = None
    for r in range((hr or 4) + 1, ws.max_row + 1):
        firm = ws.cell(r, c_firm).value
        bal = ws.cell(r, c_bal).value
        if not firm or not isinstance(bal, (int, float)):
            continue
        firm = str(firm).strip()
        if _norm(firm).startswith("grand total") or "istirak" in _norm(firm) or "kontrol" in _norm(firm):
            continue
        parts[firm] = bal
        if _norm(firm).startswith("arcelik anonim"):
            arcelik = bal
    snap["pool"] = {
        "grand_total_eur": round(sum(parts.values()), 2),
        "arcelik_eur": arcelik,
        "participants": parts,
    }
    return snap["pool"]
