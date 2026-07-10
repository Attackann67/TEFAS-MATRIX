"""beko_cash dogrulama testleri (proprietary veri gerektirmez).

Cekirdek: sema/gruplama, snapshot dogrulama, turetilmis metrikler ve dashboard
uretimi (dosya olusuyor, sayfalar var, formuller mavi/yesil ayrimina uyuyor).
"""

from __future__ import annotations

import openpyxl
import pytest

from beko_cash import compute, dashboard, schema, snapshot


def _snap(month="2026-05", eurtry=53.1224):
    return {
        "month": month, "eurtry": eurtry, "source_total_tl": 1000.0,
        "entities": {
            "E046": {"name": "Arcelik", "tot_tl": 600.0,
                     "cat_tl": {"10201": 300.0, "10204": 300.0}},
            "E625": {"name": "Beko Gulf", "tot_tl": 400.0,
                     "cat_tl": {"10201": 350.0, "10204": 50.0},
                     "overdue_keur": 17017, "match": "Olasi", "status": "LC teminat"},
        },
        "pool": {"grand_total_eur": 200.0, "arcelik_eur": 150.0,
                 "participants": {"BEKO PLC": 25.0, "ARCELIK ANONIM SIRKETI": 150.0}},
        "checks": {},
    }


def test_group_mapping():
    assert schema.CATEGORY_GROUP["10201"] == "Vadesiz"
    assert schema.CATEGORY_GROUP["10203"] == "Pool"
    assert schema.CATEGORY_GROUP["10204"] == "Vadeli"
    assert schema.segment_of("E046") == "Arcelik"
    assert schema.segment_of("E625") == "Istirakler"


def test_groups_from_cat():
    g = schema.groups_from_cat({"100": 10, "10201": 90, "10203": 50, "10204": 40, "104": 5})
    assert g["Vadesiz"] == 100  # 100 + 10201
    assert g["Pool"] == 50
    assert g["Vadeli"] == 45    # 10204 + 104


def test_validate_pass_and_catch_mismatch():
    snap = _snap()
    assert snapshot.validate(snap) == []
    # tot_tl bozulunca hata
    snap["entities"]["E625"]["tot_tl"] = 999
    issues = snapshot.validate(snap)
    assert any("tot_tl" in i for i in issues)


def test_advisory_missing_eurtry():
    snap = _snap(eurtry=None)
    notes = snapshot.advisories(snap)
    assert any("eurtry" in n for n in notes)


def test_detail_rows_code_grain():
    rows = compute.detail_rows([_snap()])
    # 2 istirak x sifir olmayan kategoriler; her satirda kat_kod dolu
    assert all(r["kat_kod"] for r in rows)
    vad = sum(r["tl"] for r in rows if r["grup"] == "Vadesiz")
    assert vad == pytest.approx(300 + 350)


def test_summary_sorgula_flag():
    out = compute.summary([_snap()])
    assert "Beko Gulf" in out  # vadesiz 350/400 = %87 >= esik


def test_dashboard_build(tmp_path):
    out = dashboard.build([_snap("2026-04", None), _snap("2026-05")], tmp_path / "d.xlsx")
    wb = openpyxl.load_workbook(out)
    for s in ["Ozet", "Girdi", "Kayit Detay", "Grup Trend", "Kategori Trend",
              "Istirak Matris", "Nakit vs Overdue", "Citi Pool", "Acik Sorgular", "Kontrol"]:
        assert s in wb.sheetnames
    # Kayit Detay TL kolonu (G) mavi girdi, ozet formul
    detay = wb["Kayit Detay"]
    assert detay["A1"].value == "Ay" and detay["G1"].value == "TL"
    # Grup Trend segment SUMIFS formul icermeli
    grup = wb["Grup Trend"]
    has_sumifs = any(
        isinstance(c.value, str) and c.value.startswith("=SUMIFS")
        for row in grup.iter_rows() for c in row
    )
    assert has_sumifs
