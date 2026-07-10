"""Dashboard uretici: snapshot'lardan cok sayfali, canli-formullu Excel.

Omurga (formuller.md): tum aylar tek 'Kayit Detay' sayfasina yigilir; tum ozet
sayfalar SUMIFS ile buradan beslenir. Hardcode SADECE dis kaynak girdilerinde
(mavi): Kayit Detay/Entity TL'leri, Girdi sayfasindaki eurtry/kaynak/esik.
Diger her hucre formuldur (siyah ayni sayfa, yesil capraz sayfa).
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from . import compute, schema

# Sayfa adlari (formullerde ' ! ' ile referanslanir)
S_OZET = "Ozet"
S_GIRDI = "Girdi"
S_DETAY = "Kayit Detay"
S_ENTITY = "Kayit Entity"
S_GRUP = "Grup Trend"
S_KAT = "Kategori Trend"
S_MATRIS = "Istirak Matris"
S_NAKIT = "Nakit vs Overdue"
S_POOL = "Citi Pool"
S_SORGU = "Acik Sorgular"
S_KONTROL = "Kontrol"

_THIN = Side(style="thin", color="FFD9D9D9")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _hdr(cell):
    cell.font = Font(name="Arial", bold=True, color=schema.C_HEADER_TXT)
    cell.fill = PatternFill("solid", fgColor=schema.C_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = _BORDER


def _title(ws: Worksheet, text: str, span: int, row: int = 1):
    ws.cell(row=row, column=1, value=text)
    c = ws.cell(row=row, column=1)
    c.font = Font(name="Arial", bold=True, size=13, color=schema.C_HEADER)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)


def _color(cell, color=schema.C_SAME, fmt=None, bold=False, fill=None):
    cell.font = Font(name="Arial", color=color, bold=bold)
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    cell.border = _BORDER


def _ref(sheet: str, col: str, r1: int, r2: int) -> str:
    return f"'{sheet}'!${col}${r1}:${col}${r2}"


def _widths(ws: Worksheet, widths: dict):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


# --- Girdi sayfasi (mavi input tek nokta) ------------------------------------

def _build_girdi(ws: Worksheet, snaps: List[dict]):
    _title(ws, "Girdi Parametreleri (mavi = dis kaynak, tek nokta)", 3)
    ws.cell(row=3, column=1, value="SORGULA esigi (vadesiz orani)")
    ws.cell(row=3, column=2, value=schema.SORGULA_ESIK)
    _color(ws["B3"], schema.C_INPUT, schema.FMT_PCT, bold=True)
    esik_cell = f"'{S_GIRDI}'!$B$3"

    hr = 5
    for j, h in enumerate(["Ay", "EURTRY (TCMB)", "Kaynak Toplam TL"], start=1):
        c = ws.cell(row=hr, column=j, value=h)
        _hdr(c)
    r = hr + 1
    month_row = {}
    for snap in snaps:
        ws.cell(row=r, column=1, value=snap["month"])
        _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=snap.get("eurtry"))
        _color(ws.cell(row=r, column=2), schema.C_INPUT, "#,##0.0000")
        ws.cell(row=r, column=3, value=snap.get("source_total_tl"))
        _color(ws.cell(row=r, column=3), schema.C_INPUT, schema.FMT_TL)
        month_row[snap["month"]] = r
        r += 1
    _widths(ws, {"A": 12, "B": 16, "C": 20})
    eur_first, eur_last = hr + 1, r - 1
    return {
        "esik": esik_cell,
        "eur_range": f"'{S_GIRDI}'!$A${eur_first}:$C${eur_last}",
        "src_range": f"'{S_GIRDI}'!$A${eur_first}:$C${eur_last}",
    }


# --- Kayit Detay (uzun format, SUMIFS omurgasi) ------------------------------

def _build_detay(ws: Worksheet, snaps: List[dict]):
    heads = ["Ay", "Kod", "Istirak", "Segment", "Grup", "Kat Kod", "TL"]
    for j, h in enumerate(heads, start=1):
        _hdr(ws.cell(row=1, column=j, value=h))
    rows = compute.detail_rows(snaps)
    r = 2
    for row in rows:
        ws.cell(row=r, column=1, value=row["ay"])
        ws.cell(row=r, column=2, value=row["kod"])
        ws.cell(row=r, column=3, value=row["istirak"])
        ws.cell(row=r, column=4, value=row["segment"])
        ws.cell(row=r, column=5, value=row["grup"])
        ws.cell(row=r, column=6, value=row["kat_kod"])
        ws.cell(row=r, column=7, value=row["tl"])
        for j in range(1, 7):
            _color(ws.cell(row=r, column=j), schema.C_SAME)
        _color(ws.cell(row=r, column=7), schema.C_INPUT, schema.FMT_TL)  # mavi girdi
        r += 1
    _widths(ws, {"A": 10, "B": 8, "C": 28, "D": 12, "E": 10, "F": 10, "G": 18})
    ws.freeze_panes = "A2"
    return {"first": 2, "last": r - 1}


# --- Kayit Entity (per ay-istirak skalerler) ---------------------------------

def _build_entity(ws: Worksheet, snaps: List[dict]):
    heads = ["Ay", "Kod", "Istirak", "Segment", "Toplam TL", "Vadesiz TL",
             "Overdue (bin EUR)", "Citi Pool EUR", "Vadesiz PB", "Statu", "Eslesme"]
    for j, h in enumerate(heads, start=1):
        _hdr(ws.cell(row=1, column=j, value=h))
    rows = compute.entity_rows(snaps)
    r = 2
    for row in rows:
        vals = [row["ay"], row["kod"], row["istirak"], row["segment"],
                row["tot_tl"], row["vad_tl"], row["overdue_keur"],
                row["citi_pool_eur"], row["vad_ccy"], row["status"], row["match"]]
        for j, v in enumerate(vals, start=1):
            ws.cell(row=r, column=j, value=v)
        for j in (5, 6, 7, 8):
            ws.cell(row=r, column=j).number_format = schema.FMT_TL
        # mavi = girdi olan skalerler
        for j in (5, 6, 7, 8):
            _color(ws.cell(row=r, column=j), schema.C_INPUT, schema.FMT_TL)
        for j in (1, 2, 3, 4, 9, 10, 11):
            _color(ws.cell(row=r, column=j))
        # eslesme guveni renk uyarisi
        if str(row["match"]).lower().startswith(("olasi", "eslesme")):
            ws.cell(row=r, column=11).fill = PatternFill("solid", fgColor=schema.C_WARN)
        r += 1
    _widths(ws, {"A": 10, "B": 8, "C": 26, "D": 12, "E": 18, "F": 16,
                 "G": 16, "H": 16, "I": 22, "J": 24, "K": 12})
    ws.freeze_panes = "A2"
    return {"first": 2, "last": r - 1}


# --- Grup Trend (segment x ay, TL & EUR) -------------------------------------

def _build_grup(ws: Worksheet, snaps, det, girdi):
    _title(ws, "Grup Trend - segment bazli (TL ve mn EUR); yesil = capraz sayfa", 8)
    mlist = compute.months(snaps)
    tl = _ref(S_DETAY, "G", det["first"], det["last"])
    ay = _ref(S_DETAY, "A", det["first"], det["last"])
    seg = _ref(S_DETAY, "D", det["first"], det["last"])

    r = 3
    _hdr(ws.cell(row=r, column=1, value="Segment / Ay"))
    for j, m in enumerate(mlist, start=2):
        _hdr(ws.cell(row=r, column=j, value=m))
    r += 1
    # TL blok
    ws.cell(row=r, column=1, value="--- TL ---"); _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
    r += 1
    for segn in schema.SEGMENTS:
        ws.cell(row=r, column=1, value=segn); _color(ws.cell(row=r, column=1), bold=True)
        for j, m in enumerate(mlist, start=2):
            f = f'=SUMIFS({tl},{ay},"{m}",{seg},"{segn}")'
            ws.cell(row=r, column=j, value=f); _color(ws.cell(row=r, column=j), schema.C_CROSS, schema.FMT_TL)
        r += 1
    # Grup toplam TL
    ws.cell(row=r, column=1, value="GRUP TOPLAM"); _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
    top_row = r
    for j, m in enumerate(mlist, start=2):
        col = get_column_letter(j)
        f = f"=SUM({col}{top_row - 3}:{col}{top_row - 1})"
        ws.cell(row=r, column=j, value=f); _color(ws.cell(row=r, column=j), schema.C_SAME, schema.FMT_TL, bold=True, fill=schema.C_GROUP)
    r += 2
    # EUR blok (mn) = TL / eurtry / 1e6
    ws.cell(row=r, column=1, value="--- mn EUR ---"); _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
    tl_top = top_row  # GRUP TOPLAM TL satiri
    r += 1
    seg_tl_start = top_row - 3
    for i, segn in enumerate(schema.SEGMENTS):
        ws.cell(row=r, column=1, value=segn); _color(ws.cell(row=r, column=1), bold=True)
        for j, m in enumerate(mlist, start=2):
            col = get_column_letter(j)
            f = (f'=IF(VLOOKUP("{m}",{girdi["eur_range"]},2,0)=0,"",'
                 f'{col}{seg_tl_start + i}/VLOOKUP("{m}",{girdi["eur_range"]},2,0)/1000000)')
            ws.cell(row=r, column=j, value=f); _color(ws.cell(row=r, column=j), schema.C_CROSS, schema.FMT_MN)
        r += 1
    _widths(ws, {"A": 18})
    for j in range(2, len(mlist) + 2):
        ws.column_dimensions[get_column_letter(j)].width = 16
    return {"tl_toplam_row": top_row, "mlist": mlist}


# --- Kategori Trend (4 grup x ay) --------------------------------------------

def _build_kategori(ws: Worksheet, snaps, det):
    _title(ws, "Kategori Trend (10 kod x ay); vadesiz MoM sicramasi sari isaretlenir", 8)
    mlist = compute.months(snaps)
    tl = _ref(S_DETAY, "G", det["first"], det["last"])
    ay = _ref(S_DETAY, "A", det["first"], det["last"])
    kk = _ref(S_DETAY, "F", det["first"], det["last"])
    grp = _ref(S_DETAY, "E", det["first"], det["last"])

    # Veride gorunen kategori kodlari (10-kod grain yoksa 4 grup adi gelir)
    present = {row["kat_kod"] for row in compute.detail_rows(snaps)}
    codes = [c for c in schema.CATEGORY_ORDER if c in present]
    if not codes:  # sadece 4-grup kaydi
        codes = [g for g in schema.GROUPS if g in present]

    r = 3
    _hdr(ws.cell(row=r, column=1, value="Kod"))
    _hdr(ws.cell(row=r, column=2, value="Kategori"))
    for j, m in enumerate(mlist, start=3):
        _hdr(ws.cell(row=r, column=j, value=m))
    r += 1
    for code in codes:
        label = schema.CATEGORY_LABEL.get(code, code)
        ws.cell(row=r, column=1, value=code); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=label); _color(ws.cell(row=r, column=2))
        for j, m in enumerate(mlist, start=3):
            f = f'=SUMIFS({tl},{ay},"{m}",{kk},"{code}")'
            _color(ws.cell(row=r, column=j, value=f), schema.C_CROSS, schema.FMT_TL)
        r += 1
    # GRUP TOPLAM satiri (dogrulama)
    ws.cell(row=r, column=1, value=""); ws.cell(row=r, column=2, value="GRUP TOPLAM")
    _color(ws.cell(row=r, column=2), bold=True, fill=schema.C_GROUP)
    for j, m in enumerate(mlist, start=3):
        col = get_column_letter(j)
        _color(ws.cell(row=r, column=j, value=f"=SUM({col}4:{col}{r-1})"),
               schema.C_SAME, schema.FMT_TL, bold=True, fill=schema.C_GROUP)
    r += 2
    # Vadesiz (100+10201) MoM % - sicrama izleme
    ws.cell(row=r, column=2, value="Vadesiz (100+10201)"); _color(ws.cell(row=r, column=2), bold=True)
    vr = r
    for j, m in enumerate(mlist, start=3):
        f = f'=SUMIFS({tl},{ay},"{m}",{grp},"Vadesiz")'
        _color(ws.cell(row=r, column=j, value=f), schema.C_CROSS, schema.FMT_TL)
    r += 1
    ws.cell(row=r, column=2, value="Vadesiz MoM %"); _color(ws.cell(row=r, column=2), bold=True, fill=schema.C_WARN)
    for j, m in enumerate(mlist, start=3):
        if j == 3:
            _color(ws.cell(row=r, column=j, value="-")); continue
        prev, cur = get_column_letter(j - 1), get_column_letter(j)
        _color(ws.cell(row=r, column=j, value=f'=IF({prev}{vr}=0,"",{cur}{vr}/{prev}{vr}-1)'),
               schema.C_SAME, schema.FMT_PCT)
    from openpyxl.formatting.rule import CellIsRule
    last_col = get_column_letter(len(mlist) + 2)
    ws.conditional_formatting.add(
        f"D{r}:{last_col}{r}",
        CellIsRule(operator="greaterThanOrEqual", formula=["0.2"],
                   fill=PatternFill("solid", fgColor=schema.C_WARN)))
    _widths(ws, {"A": 8, "B": 22})
    for j in range(3, len(mlist) + 3):
        ws.column_dimensions[get_column_letter(j)].width = 16


# --- Istirak Matris (istirak x ay + SORGULA) ---------------------------------

def _build_matris(ws: Worksheet, snaps, det, girdi):
    _title(ws, "Istirak Matris - toplam TL (ay), vadesiz orani ve SORGULA bayragi", 10)
    ws.cell(row=2, column=1, value="SORGULA esigi:")
    ws.cell(row=2, column=2, value=f"={girdi['esik']}")
    _color(ws["B2"], schema.C_CROSS, schema.FMT_PCT, bold=True)

    mlist = compute.months(snaps)
    universe = compute.entity_universe(snaps)
    tl = _ref(S_DETAY, "G", det["first"], det["last"])
    ay = _ref(S_DETAY, "A", det["first"], det["last"])
    kod = _ref(S_DETAY, "B", det["first"], det["last"])
    grp = _ref(S_DETAY, "E", det["first"], det["last"])

    r = 4
    _hdr(ws.cell(row=r, column=1, value="Kod"))
    _hdr(ws.cell(row=r, column=2, value="Istirak"))
    _hdr(ws.cell(row=r, column=3, value="Segment"))
    col = 4
    for m in mlist:
        _hdr(ws.cell(row=r, column=col, value=f"{m} TL")); col += 1
    last_m = mlist[-1]
    _hdr(ws.cell(row=r, column=col, value=f"Vadesiz% ({last_m})")); vp_col = col; col += 1
    _hdr(ws.cell(row=r, column=col, value="SORGULA")); sg_col = col
    r += 1
    for code, name in universe:
        ws.cell(row=r, column=1, value=code); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=name); _color(ws.cell(row=r, column=2))
        ws.cell(row=r, column=3, value=schema.segment_of(code)); _color(ws.cell(row=r, column=3))
        c = 4
        for m in mlist:
            f = f'=SUMIFS({tl},{ay},"{m}",{kod},"{code}")'
            ws.cell(row=r, column=c, value=f); _color(ws.cell(row=r, column=c), schema.C_CROSS, schema.FMT_TL); c += 1
        # vadesiz% son ay
        tot_f = f'SUMIFS({tl},{ay},"{last_m}",{kod},"{code}")'
        vad_f = f'SUMIFS({tl},{ay},"{last_m}",{kod},"{code}",{grp},"Vadesiz")'
        vp = get_column_letter(vp_col)
        ws.cell(row=r, column=vp_col, value=f'=IF({tot_f}=0,"",{vad_f}/{tot_f})')
        _color(ws.cell(row=r, column=vp_col), schema.C_CROSS, schema.FMT_PCT)
        ws.cell(row=r, column=sg_col,
                value=f'=IF(AND({tot_f}>0,{vp}{r}<>"",{vp}{r}>=$B$2),"SORGULA","")')
        _color(ws.cell(row=r, column=sg_col), schema.C_SAME, bold=True)
        r += 1
    # SORGULA hucrelerini kirmizi vurgula
    from openpyxl.formatting.rule import CellIsRule
    sg = get_column_letter(sg_col)
    ws.conditional_formatting.add(
        f"{sg}5:{sg}{r-1}",
        CellIsRule(operator="equal", formula=['"SORGULA"'],
                   fill=PatternFill("solid", fgColor=schema.C_FAIL)))
    _widths(ws, {"A": 8, "B": 28, "C": 12})
    for j in range(4, sg_col + 1):
        ws.column_dimensions[get_column_letter(j)].width = 16
    ws.freeze_panes = "D5"


# --- Nakit vs Overdue --------------------------------------------------------

def _build_nakit(ws: Worksheet, snaps, det, ent, girdi):
    last = snaps[-1]
    m = last["month"]
    _title(ws, f"Nakit vs Overdue ({m}) - oranlar GOSTERGEDIR; kesit farki etikette", 8)
    ws.cell(row=2, column=1,
            value="UYARI: nakit kesiti ay sonu, overdue farkli kesit olabilir (kontrol-listesi). "
                  "Oran = likit mn EUR / overdue mn EUR.")
    _color(ws["A2"], schema.C_SAME, bold=True, fill=schema.C_WARN)
    ws.merge_cells("A2:H2")

    tl = _ref(S_DETAY, "G", det["first"], det["last"])
    ay = _ref(S_DETAY, "A", det["first"], det["last"])
    kod = _ref(S_DETAY, "B", det["first"], det["last"])
    e_ay = _ref(S_ENTITY, "A", ent["first"], ent["last"])
    e_kod = _ref(S_ENTITY, "B", ent["first"], ent["last"])
    e_ovd = _ref(S_ENTITY, "G", ent["first"], ent["last"])

    heads = ["Kod", "Istirak", "Likit mn EUR", "Overdue mn EUR", "Likit/Overdue",
             "Eslesme", "Statu"]
    r = 4
    for j, h in enumerate(heads, start=1):
        _hdr(ws.cell(row=r, column=j, value=h))
    r += 1
    eur = girdi["eur_range"]
    codes = [(c, e.get("name", c)) for c, e in last.get("entities", {}).items()
             if e.get("overdue_keur") not in (None,)]
    for code, name in codes:
        ws.cell(row=r, column=1, value=code); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=name); _color(ws.cell(row=r, column=2))
        # likit mn EUR
        tot_f = f'SUMIFS({tl},{ay},"{m}",{kod},"{code}")'
        ws.cell(row=r, column=3,
                value=f'=IF(VLOOKUP("{m}",{eur},2,0)=0,"",{tot_f}/VLOOKUP("{m}",{eur},2,0)/1000000)')
        _color(ws.cell(row=r, column=3), schema.C_CROSS, schema.FMT_MN)
        # overdue mn EUR = bin EUR / 1000
        ovd_f = f'SUMIFS({e_ovd},{e_ay},"{m}",{e_kod},"{code}")'
        ws.cell(row=r, column=4, value=f"={ovd_f}/1000")
        _color(ws.cell(row=r, column=4), schema.C_CROSS, schema.FMT_MN)
        # ratio
        ws.cell(row=r, column=5, value=f'=IF(D{r}=0,"-",C{r}/D{r})')
        _color(ws.cell(row=r, column=5), schema.C_SAME, schema.FMT_RATIO)
        e = last["entities"][code]
        ws.cell(row=r, column=6, value=e.get("match", "")); _color(ws.cell(row=r, column=6))
        ws.cell(row=r, column=7, value=e.get("status", "")); _color(ws.cell(row=r, column=7))
        r += 1
    _widths(ws, {"A": 8, "B": 28, "C": 16, "D": 16, "E": 16, "F": 12, "G": 28})


# --- Citi Pool ---------------------------------------------------------------

def _build_pool(ws: Worksheet, snaps):
    last = snaps[-1]
    pool = last.get("pool", {}) or {}
    _title(ws, f"Citi Pool ({last['month']}) - katilimci bakiyeleri (EUR); "
               f"HARIC = cash dosyasi disi, C746'ya katilmaz", 4)
    heads = ["Katilimci", "SUM EURO BALANCE", "Eslesen Kod", "LE Notu"]
    r = 3
    for j, h in enumerate(heads, start=1):
        _hdr(ws.cell(row=r, column=j, value=h))
    r += 1
    parts = pool.get("participants", {}) or {}
    first_p = r
    for name, bal in parts.items():
        code, le = schema.pool_participant_entity(name)
        ws.cell(row=r, column=1, value=name); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=bal); _color(ws.cell(row=r, column=2), schema.C_INPUT, schema.FMT_TL)
        ws.cell(row=r, column=3, value=code or "Eslesmedi"); _color(ws.cell(row=r, column=3))
        ws.cell(row=r, column=4, value=le); _color(ws.cell(row=r, column=4))
        if code is None:
            ws.cell(row=r, column=3).fill = PatternFill("solid", fgColor=schema.C_WARN)
        r += 1
    last_p = r - 1
    kod_rng = f"$C${first_p}:$C${last_p}"
    bal_rng = f"$B${first_p}:$B${last_p}"
    # Grand Total (girdi), Arcelik (girdi), Istiraklerin Pool = GT - Arcelik (formul)
    ws.cell(row=r, column=1, value="Grand Total (girdi)"); _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
    ws.cell(row=r, column=2, value=pool.get("grand_total_eur")); _color(ws.cell(row=r, column=2), schema.C_INPUT, schema.FMT_TL, bold=True)
    gt_row = r; r += 1
    ws.cell(row=r, column=1, value="Arcelik Anonim Sirketi (girdi)"); _color(ws.cell(row=r, column=1))
    ws.cell(row=r, column=2, value=pool.get("arcelik_eur")); _color(ws.cell(row=r, column=2), schema.C_INPUT, schema.FMT_TL)
    ar_row = r; r += 1
    ws.cell(row=r, column=1, value="Istiraklerin Pool Bakiyesi = Grand Total - Arcelik")
    _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
    ws.cell(row=r, column=2, value=f"=B{gt_row}-B{ar_row}")
    _color(ws.cell(row=r, column=2), schema.C_SAME, schema.FMT_TL, bold=True, fill=schema.C_GROUP)
    r += 1
    if first_p <= last_p:
        ws.cell(row=r, column=1, value="Katilimci toplami (kontrol)"); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=f"=SUM({bal_rng})")
        _color(ws.cell(row=r, column=2), schema.C_SAME, schema.FMT_TL)
        r += 2
        # Kod bazli ara toplamlar (canli SUMIF)
        ws.cell(row=r, column=1, value="Kod bazli ara toplam"); _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
        r += 1
        seen_codes = []
        for name in parts:
            code, _ = schema.pool_participant_entity(name)
            code = code or "Eslesmedi"
            if code not in seen_codes:
                seen_codes.append(code)
        for code in seen_codes:
            label = {"C746": "C746 Beko Europe (eslesen LE'ler)",
                     "HARIC": "HARIC (cash dosyasi disi - C746'ya katilmaz)",
                     "Eslesmedi": "Eslesmedi (kullaniciya sor)"}.get(code, code)
            ws.cell(row=r, column=1, value=label); _color(ws.cell(row=r, column=1))
            ws.cell(row=r, column=2, value=f'=SUMIF({kod_rng},"{code}",{bal_rng})')
            _color(ws.cell(row=r, column=2), schema.C_SAME, schema.FMT_TL)
            if code in ("HARIC", "Eslesmedi"):
                ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=schema.C_WARN)
            r += 1
    _widths(ws, {"A": 46, "B": 22, "C": 12, "D": 10})


# --- Acik Sorgular -----------------------------------------------------------

def _build_sorgular(ws: Worksheet, snaps):
    _title(ws, "Acik Sorgular - kim, ne zaman soruldu, cevap durumu", 6)
    heads = ["Ay", "Kod", "Istirak", "Gonderildi", "Cevap", "Durum", "Ozet"]
    r = 3
    for j, h in enumerate(heads, start=1):
        _hdr(ws.cell(row=r, column=j, value=h))
    r += 1
    for snap in snaps:
        for code, e in snap.get("entities", {}).items():
            sq = e.get("sorgu")
            if not sq:
                continue
            gon, cev = sq.get("gonderildi"), sq.get("cevap")
            durum = "Cevaplandi" if cev else ("Beklemede" if gon else "Acilmadi")
            vals = [snap["month"], code, e.get("name", code), gon, cev, durum, sq.get("ozet", "")]
            for j, v in enumerate(vals, start=1):
                ws.cell(row=r, column=j, value=v)
                _color(ws.cell(row=r, column=j))
            if not cev and gon:
                ws.cell(row=r, column=6).fill = PatternFill("solid", fgColor=schema.C_WARN)
            r += 1
    _widths(ws, {"A": 10, "B": 8, "C": 24, "D": 12, "E": 12, "F": 12, "G": 50})


# --- Kontrol -----------------------------------------------------------------

def _build_kontrol(ws: Worksheet, snaps, det, girdi):
    _title(ws, "Kontrol - detay vs kaynak, Sheet2 farki, PASS/FAIL", 6)
    mlist = compute.months(snaps)
    tl = _ref(S_DETAY, "G", det["first"], det["last"])
    ay = _ref(S_DETAY, "A", det["first"], det["last"])
    heads = ["Ay", "Detay Toplam TL", "Kaynak TL (girdi)", "Fark", "Sheet2 Gap (not)", "Sonuc"]
    r = 3
    for j, h in enumerate(heads, start=1):
        _hdr(ws.cell(row=r, column=j, value=h))
    r += 1
    eur = girdi["eur_range"]
    for snap in snaps:
        m = snap["month"]
        ws.cell(row=r, column=1, value=m); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=f'=SUMIFS({tl},{ay},"{m}")')
        _color(ws.cell(row=r, column=2), schema.C_CROSS, schema.FMT_TL)
        ws.cell(row=r, column=3, value=f'=VLOOKUP("{m}",{eur},3,0)')
        _color(ws.cell(row=r, column=3), schema.C_CROSS, schema.FMT_TL)
        ws.cell(row=r, column=4, value=f"=ROUND(B{r}-C{r},2)")
        _color(ws.cell(row=r, column=4), schema.C_SAME, schema.FMT_TL)
        gap = snap.get("checks", {}).get("sheet2_gap")
        ws.cell(row=r, column=5, value=gap); _color(ws.cell(row=r, column=5), schema.C_INPUT, schema.FMT_TL)
        ws.cell(row=r, column=6, value=f'=IF(ABS(D{r})<0.5,"PASS","FAIL")')
        _color(ws.cell(row=r, column=6), schema.C_SAME, bold=True)
        r += 1
    from openpyxl.formatting.rule import CellIsRule
    ws.conditional_formatting.add(
        f"F4:F{r-1}",
        CellIsRule(operator="equal", formula=['"PASS"'], fill=PatternFill("solid", fgColor=schema.C_PASS)))
    ws.conditional_formatting.add(
        f"F4:F{r-1}",
        CellIsRule(operator="equal", formula=['"FAIL"'], fill=PatternFill("solid", fgColor=schema.C_FAIL)))
    _widths(ws, {"A": 10, "B": 20, "C": 20, "D": 16, "E": 18, "F": 10})


# --- Ozet (kapak) ------------------------------------------------------------

def _build_ozet(ws: Worksheet, snaps, grup):
    last = snaps[-1]["month"]
    _title(ws, "Beko Cash Dashboard", 6)
    ws.cell(row=2, column=1, value=f"Son kesit: {last} | {len(snaps)} ay kayitli | "
                                   f"kaynak: liquid report + overdue + Citi pool")
    _color(ws["A2"], schema.C_SAME, bold=True)
    # Segment split (son ay) - Grup Trend'den capraz cek
    mlist = grup["mlist"]
    col = mlist.index(last) + 2
    colL = get_column_letter(col)
    tl_top = grup["tl_toplam_row"]
    r = 4
    _hdr(ws.cell(row=r, column=1, value="Segment (son ay)"))
    _hdr(ws.cell(row=r, column=2, value="TL"))
    r += 1
    for i, segn in enumerate(schema.SEGMENTS):
        ws.cell(row=r, column=1, value=segn); _color(ws.cell(row=r, column=1))
        ws.cell(row=r, column=2, value=f"='{S_GRUP}'!{colL}{tl_top - 3 + i}")
        _color(ws.cell(row=r, column=2), schema.C_CROSS, schema.FMT_TL)
        r += 1
    ws.cell(row=r, column=1, value="GRUP TOPLAM"); _color(ws.cell(row=r, column=1), bold=True, fill=schema.C_GROUP)
    ws.cell(row=r, column=2, value=f"='{S_GRUP}'!{colL}{tl_top}")
    _color(ws.cell(row=r, column=2), schema.C_CROSS, schema.FMT_TL, bold=True, fill=schema.C_GROUP)
    r += 2
    ws.cell(row=r, column=1, value="Sayfalar: Kontrol (PASS/FAIL), Istirak Matris (SORGULA), "
                                   "Nakit vs Overdue, Citi Pool, Acik Sorgular")
    _color(ws.cell(row=r, column=1))
    _widths(ws, {"A": 40, "B": 22})


# --- Orkestrasyon ------------------------------------------------------------

def build(snaps: List[dict], out_path: str | Path) -> Path:
    if not snaps:
        raise ValueError("En az bir snapshot gerekli")
    wb = Workbook()
    ws_ozet = wb.active
    ws_ozet.title = S_OZET
    ws_girdi = wb.create_sheet(S_GIRDI)
    ws_detay = wb.create_sheet(S_DETAY)
    ws_entity = wb.create_sheet(S_ENTITY)
    ws_grup = wb.create_sheet(S_GRUP)
    ws_kat = wb.create_sheet(S_KAT)
    ws_matris = wb.create_sheet(S_MATRIS)
    ws_nakit = wb.create_sheet(S_NAKIT)
    ws_pool = wb.create_sheet(S_POOL)
    ws_sorgu = wb.create_sheet(S_SORGU)
    ws_kontrol = wb.create_sheet(S_KONTROL)

    girdi = _build_girdi(ws_girdi, snaps)
    det = _build_detay(ws_detay, snaps)
    ent = _build_entity(ws_entity, snaps)
    grup = _build_grup(ws_grup, snaps, det, girdi)
    _build_kategori(ws_kat, snaps, det)
    _build_matris(ws_matris, snaps, det, girdi)
    _build_nakit(ws_nakit, snaps, det, ent, girdi)
    _build_pool(ws_pool, snaps)
    _build_sorgular(ws_sorgu, snaps)
    _build_kontrol(ws_kontrol, snaps, det, girdi)
    _build_ozet(ws_ozet, snaps, grup)

    out_path = Path(out_path)
    wb.save(out_path)
    return out_path
