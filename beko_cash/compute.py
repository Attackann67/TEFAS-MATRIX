"""Analiz katmani: snapshot'lardan turetilmis metrikler ve uzun-format satirlar.

Dashboard formulle uretir; bu modul (1) dogrulama/ozet ciktisi ve (2) dashboard'un
'Kayit Detay' sayfasini besleyen uzun-format satirlari saglar. Hicbir turetilmis
toplam snapshot'a geri yazilmaz (kirmizi cizgi).
"""

from __future__ import annotations

from typing import Dict, List

from . import schema


def _groups(ent: dict) -> dict:
    if ent.get("cat_tl"):
        return schema.groups_from_cat(ent["cat_tl"])
    return {g: float(ent.get(schema.GROUP_FIELD[g], 0) or 0) for g in schema.GROUPS}


def detail_rows(snaps: List[dict]) -> List[dict]:
    """Tum aylar tek listeye yigilir; her satir bir (ay, istirak, kategori).

    Bu, formuller.md'deki 'tum aylar tek Hesap Detay sayfasina yigilir' omurgasidir.
    Dashboard ozet sayfalari bu satirlara SUMIFS ile baglanir. cat_tl (10-kod)
    varsa kategori kodu bazinda; yoksa 4 grup bazinda satir uretir. Her iki
    durumda da 'grup' (Vadesiz/Vadeli/Pool/Diger) ve 'kat_kod' doldurulur, boylece
    hem 4-grup hem 10-kod SUMIFS calisir.
    """
    rows: List[dict] = []
    for snap in snaps:
        month = snap["month"]
        for code, ent in snap.get("entities", {}).items():
            seg = schema.segment_of(code)
            name = ent.get("name", code)
            cat = ent.get("cat_tl")
            if cat:
                for kk in schema.CATEGORY_ORDER:
                    tl = float(cat.get(kk, 0) or 0)
                    if tl == 0:
                        continue
                    rows.append({"ay": month, "kod": code, "istirak": name, "segment": seg,
                                 "grup": schema.CATEGORY_GROUP.get(kk, "Diger"),
                                 "kat_kod": kk, "tl": tl})
            else:
                for grp in schema.GROUPS:
                    tl = float(ent.get(schema.GROUP_FIELD[grp], 0) or 0)
                    if tl == 0:
                        continue
                    rows.append({"ay": month, "kod": code, "istirak": name, "segment": seg,
                                 "grup": grp, "kat_kod": grp, "tl": tl})
    return rows


def entity_rows(snaps: List[dict]) -> List[dict]:
    """Her (ay, istirak) bir satir: tot, overdue, pool, vad_ccy ozeti, statu, eslesme."""
    rows: List[dict] = []
    for snap in snaps:
        month = snap["month"]
        for code, ent in snap.get("entities", {}).items():
            ccy = ent.get("vad_ccy") or {}
            ccy_txt = ", ".join(f"{v:,.0f} {k}" for k, v in ccy.items()) if ccy else ""
            rows.append({
                "ay": month, "kod": code, "istirak": ent.get("name", code),
                "segment": schema.segment_of(code),
                "tot_tl": float(ent.get("tot_tl", 0) or 0),
                "vad_tl": _groups(ent)["Vadesiz"],
                "overdue_keur": ent.get("overdue_keur"),
                "citi_pool_eur": ent.get("citi_pool_eur"),
                "vad_ccy": ccy_txt,
                "status": ent.get("status", ""),
                "match": ent.get("match", ""),
            })
    return rows


def months(snaps: List[dict]) -> List[str]:
    return [s["month"] for s in snaps]


def entity_universe(snaps: List[dict]) -> List[tuple[str, str]]:
    """Tum aylardaki benzersiz (kod, ad) istirakler; segment sonra kod sirasiyla."""
    seen: Dict[str, str] = {}
    for snap in snaps:
        for code, ent in snap.get("entities", {}).items():
            seen[code] = ent.get("name", code)
    order = {"Istirakler": 0, "Arcelik": 1, "Pazarlama": 2}
    return sorted(seen.items(), key=lambda kv: (order[schema.segment_of(kv[0])], kv[0]))


def summary(snaps: List[dict]) -> str:
    """Insana okunur ozet (CLI ciktisi / hizli kontrol)."""
    lines: List[str] = []
    for snap in snaps:
        m = snap["month"]
        ents = snap.get("entities", {})
        tot = sum(float(e.get("tot_tl", 0) or 0) for e in ents.values())
        eur = snap.get("eurtry")
        eur_txt = f"{tot / eur / 1e6:,.1f} mn EUR" if eur else "(eurtry yok)"
        flags = []
        for code, e in ents.items():
            t = float(e.get("tot_tl", 0) or 0)
            v = _groups(e)["Vadesiz"]
            if t > 0 and v / t >= schema.SORGULA_ESIK:
                flags.append(e.get("name", code))
        lines.append(f"{m}: {len(ents)} istirak | {tot:,.0f} TL ({eur_txt})")
        if flags:
            lines.append(f"    SORGULA (vadesiz>={schema.SORGULA_ESIK:.0%}): {', '.join(flags)}")
        issues_note = snap.get("checks", {}).get("detail_vs_source")
        if issues_note not in (None, 0):
            lines.append(f"    checks.detail_vs_source = {issues_note:,.2f}")
    return "\n".join(lines)
