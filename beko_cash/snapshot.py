"""Kayit katmani: aylik snapshot JSON'lari oku / yaz / dogrula / iskele kur.

Snapshot semasi (SKILL.md):
    {
      "month": "2026-05",
      "eurtry": 53.1224,
      "source_total_tl": 55630216243,     # dis kaynak grup toplami (dogrulama kancasi)
      "entities": {
        "E625": {"name": "Beko Gulf", "tot_tl": ..., "vad_tl": ..., "vdl_tl": ...,
                  "pool_tl": ..., "dig_tl": ..., "vad_ccy": {"USD": 23179814},
                  "overdue_keur": 17017, "citi_pool_eur": null,
                  "status": "...", "match": "Kesin",
                  "sorgu": {"gonderildi": "...", "cevap": "...", "ozet": "..."}}
      },
      "pool": {"grand_total_eur": ..., "arcelik_eur": ..., "participants": {...}},
      "checks": {"detail_vs_source": 0, "sheet2_gap": 11386549.99}
    }

Kirmizi cizgi: kaynaksiz rakam yazma. Kaydedilen her tutar dis kaynaktan gelir
(mavi girdi). Turetilmis toplamlar burada saklanmaz; dashboard formulle uretir.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from . import schema

ENTITY_NUM_FIELDS = ("tot_tl", "vad_tl", "vdl_tl", "pool_tl", "dig_tl")


def load(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_all(folder: str | Path) -> List[dict]:
    """Klasordeki tum YYYY-MM.json snapshot'larini ay sirasina gore dondurur."""
    folder = Path(folder)
    snaps = [load(p) for p in folder.glob("*.json")]
    snaps.sort(key=lambda s: s.get("month", ""))
    return snaps


def save(snap: dict, folder: str | Path) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{snap['month']}.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=2)
    return out


def scaffold(month: str, eurtry: float | None = None) -> dict:
    """Bos aylik snapshot iskelesi (kayda baslamak icin)."""
    return {
        "month": month,
        "eurtry": eurtry,
        "source_total_tl": None,
        "entities": {},
        "pool": {"grand_total_eur": None, "arcelik_eur": None, "participants": {}},
        "checks": {"detail_vs_source": None, "sheet2_gap": None},
    }


def entity_groups(ent: dict) -> dict:
    """Istirakin 4 grup toplamini dondurur.

    cat_tl (10-kod) varsa ondan turetir (birincil); yoksa vad/vdl/pool/dig
    alanlarini kullanir. Boylece hem detayli hem ozet kayit desteklenir.
    """
    if ent.get("cat_tl"):
        return schema.groups_from_cat(ent["cat_tl"])
    return {g: float(ent.get(schema.GROUP_FIELD[g], 0) or 0) for g in schema.GROUPS}


def _entity_group_sum(ent: dict) -> float:
    return sum(entity_groups(ent).values())


def validate(snap: dict) -> List[str]:
    """Kontrol-listesi.md kurallari. Sorun listesi dondurur (bos = temiz).

    Sadece dogrular; duzeltme YAPMAZ. Eslesme/statu bosluklarini isaretler.
    """
    issues: List[str] = []
    month = snap.get("month")
    if not month:
        issues.append("month alani eksik")

    ents = snap.get("entities", {})
    if not ents:
        issues.append(f"{month}: hic istirak kaydi yok")

    detail_total = 0.0
    for code, ent in ents.items():
        name = ent.get("name", code)
        gsum = _entity_group_sum(ent)
        tot = float(ent.get("tot_tl", 0) or 0)
        # Satir bazli check: grup/kategori toplami = tot_tl (tolerans TL 0,5)
        if abs(gsum - tot) > schema.TOL_TL:
            kaynak = "cat_tl" if ent.get("cat_tl") else "grup alanlari"
            issues.append(
                f"{month}/{code} {name}: {kaynak} toplami {gsum:,.2f} != tot_tl {tot:,.2f} "
                f"(fark {gsum - tot:,.2f})"
            )
        detail_total += tot
        # Eslesme guveni bos ise isaretle (SORMADAN eslestirme kirmizi cizgisi)
        if ent.get("overdue_keur") not in (None,) and not ent.get("match"):
            issues.append(f"{month}/{code} {name}: overdue var ama eslesme guveni (match) bos")

    # Detay toplami = kaynak toplam (dis kancadan)
    src = snap.get("source_total_tl")
    if src not in (None, 0):
        diff = round(detail_total - float(src), 2)
        if abs(diff) > schema.TOL_TL:
            issues.append(
                f"{month}: detay toplami {detail_total:,.2f} - kaynak {float(src):,.2f} "
                f"= {diff:,.2f} (Sheet2 farki ise checks.sheet2_gap'e notla)"
            )
    return issues


def advisories(snap: dict) -> List[str]:
    """Bloklamayan uyarilar (dashboard yine uretilir): eksik kur, bloke, faiz=anapara."""
    notes: List[str] = []
    month = snap.get("month")
    if snap.get("eurtry") in (None, 0):
        notes.append(f"{month}: eurtry yok - bu ay EUR sutunlari bos kalir (TL trend etkilenmez)")
    for code, ent in snap.get("entities", {}).items():
        name = ent.get("name", code)
        cat = ent.get("cat_tl") or {}
        # Faiz tahakkuku (104) = vadeli anapara (10204) birebir esitse kayit hatasi isareti
        if cat.get("104") and cat.get("10204") and abs(float(cat["104"]) - float(cat["10204"])) < 0.5:
            notes.append(f"{month}/{code} {name}: faiz tahakkuku (104) = vadeli anapara (10204); sorgula")
        # Bloke: status LC/teminat/bloke der ama Diger grup 0 ise reclass (10202/10205) sor
        st = (ent.get("status") or "").lower()
        if ("lc" in st or "teminat" in st or "bloke" in st) and entity_groups(ent)["Diger"] == 0:
            notes.append(f"{month}/{code} {name}: status blokeye isaret ediyor ama bloke kalem yok; "
                         f"10202/10205 reclass gerekebilir")
    return notes


def compute_checks(snap: dict) -> dict:
    """checks blogunu detaydan yeniden hesaplar (kayittan sonra cagir)."""
    detail_total = sum(float(e.get("tot_tl", 0) or 0) for e in snap.get("entities", {}).values())
    src = snap.get("source_total_tl")
    snap.setdefault("checks", {})
    snap["checks"]["detail_total_tl"] = round(detail_total, 2)
    if src not in (None, 0):
        snap["checks"]["detail_vs_source"] = round(detail_total - float(src), 2)
    return snap["checks"]


def upsert_entity(snap: dict, code: str, **fields) -> dict:
    """Kayda istirak ekle/guncelle (kayit araci). Bilinmeyen alanlar da saklanir."""
    ent = snap.setdefault("entities", {}).setdefault(code, {})
    ent.update(fields)
    compute_checks(snap)
    return ent
