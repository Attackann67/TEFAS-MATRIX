"""Komut satiri: kayit dogrula, iskele kur, ozet cikar, dashboard uret.

Ornekler:
    # Snapshot klasorunden dashboard uret (varsayilan yol skill data/snapshots)
    python -m beko_cash build --snapshots .claude/skills/beko-cash-dashboard/data/snapshots \
        --out Beko_Cash_Dashboard_2026-05.xlsx

    # Tek/tum snapshot dogrula (kontrol-listesi kurallari)
    python -m beko_cash validate --snapshots <klasor>

    # Yeni ay iskelesi (kayda baslamak icin)
    python -m beko_cash new --month 2026-06 --eurtry 53.50 \
        --snapshots <klasor>

    # Insana okunur ozet (SORGULA bayraklari, toplamlar)
    python -m beko_cash summary --snapshots <klasor>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import compute, dashboard, extract, snapshot, webdash

DEFAULT_SNAP = ".claude/skills/beko-cash-dashboard/data/snapshots"


def _load(folder: str):
    snaps = snapshot.load_all(folder)
    if not snaps:
        print(f"[!] {folder} altinda snapshot bulunamadi.", file=sys.stderr)
        sys.exit(2)
    return snaps


def cmd_build(args):
    snaps = _load(args.snapshots)
    problems, notes = [], []
    for s in snaps:
        problems += snapshot.validate(s)
        notes += snapshot.advisories(s)
    if problems and not args.force:
        print("[!] Dogrulama hatalari (--force ile yine de uret):", file=sys.stderr)
        for p in problems:
            print("    -", p, file=sys.stderr)
        sys.exit(1)
    for nt in notes:
        print("[uyari]", nt)
    out = dashboard.build(snaps, args.out)
    print(f"[ok] {len(snaps)} ay -> {out}")
    print(compute.summary(snaps))
    print("\nSonraki adim (zorunlu): recalc ile formulleri dogrula")
    print(f"    python /mnt/skills/public/xlsx/scripts/recalc.py {out}")


def cmd_validate(args):
    snaps = _load(args.snapshots)
    total = 0
    for s in snaps:
        issues = snapshot.validate(s)
        notes = snapshot.advisories(s)
        total += len(issues)
        tag = "PASS" if not issues else f"{len(issues)} hata"
        print(f"{s['month']}: {tag}")
        for i in issues:
            print("    [hata]", i)
        for n in notes:
            print("    [uyari]", n)
    print(f"\nToplam: {total} hata")
    sys.exit(0 if total == 0 else 1)


def cmd_new(args):
    folder = Path(args.snapshots)
    snap = snapshot.scaffold(args.month, args.eurtry)
    out = snapshot.save(snap, folder)
    print(f"[ok] iskele: {out}")
    print("    entities/pool/source_total_tl alanlarini kaynak dosyalardan doldur (mavi girdi).")


def cmd_summary(args):
    snaps = _load(args.snapshots)
    print(compute.summary(snaps))


def cmd_web(args):
    snaps = _load(args.snapshots)
    out = webdash.write(snaps, args.out)
    print(f"[ok] {len(snaps)} ay -> {out} (tarayicida ac)")


def cmd_extract(args):
    snaps_by_month = extract.extract_from_detail(args.detail, args.sheet)
    print(f"[ok] {len(snaps_by_month)} ay cikarildi: {', '.join(sorted(snaps_by_month))}")
    target = args.month or max(snaps_by_month)
    if args.overdue:
        n = extract.enrich_overdue(snaps_by_month[target], args.overdue)
        print(f"    overdue -> {target}: {n} istirak eslesti")
    if args.pool:
        pool = extract.enrich_pool(snaps_by_month[target], args.pool)
        print(f"    pool -> {target}: {len(pool['participants'])} katilimci, "
              f"grand {pool['grand_total_eur']:,.0f} EUR")
    if args.eurtry and target in snaps_by_month:
        snaps_by_month[target]["eurtry"] = args.eurtry
    if args.sheet2_gap and target in snaps_by_month:
        snaps_by_month[target].setdefault("checks", {})["sheet2_gap"] = args.sheet2_gap
    folder = Path(args.out_dir)
    for month, snap in sorted(snaps_by_month.items()):
        out = snapshot.save(snap, folder)
        print(f"    yazildi: {out}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="beko_cash", description="Beko cash-overdue kayit & dashboard")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="snapshot'lardan dashboard Excel uret")
    b.add_argument("--snapshots", default=DEFAULT_SNAP)
    b.add_argument("--out", required=True)
    b.add_argument("--force", action="store_true", help="dogrulama sorunlarini yoksay")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate", help="kontrol-listesi kurallariyla dogrula")
    v.add_argument("--snapshots", default=DEFAULT_SNAP)
    v.set_defaults(func=cmd_validate)

    n = sub.add_parser("new", help="yeni ay snapshot iskelesi olustur")
    n.add_argument("--month", required=True, help="YYYY-MM")
    n.add_argument("--eurtry", type=float, default=None)
    n.add_argument("--snapshots", default=DEFAULT_SNAP)
    n.set_defaults(func=cmd_new)

    s = sub.add_parser("summary", help="insana okunur ozet")
    s.add_argument("--snapshots", default=DEFAULT_SNAP)
    s.set_defaults(func=cmd_summary)

    w = sub.add_parser("web", help="tek dosyalik HTML dashboard uret")
    w.add_argument("--snapshots", default=DEFAULT_SNAP)
    w.add_argument("--out", default="beko_cash_dashboard.html")
    w.set_defaults(func=cmd_web)

    e = sub.add_parser("extract", help="kaynak Excel'lerden aylik snapshot uret")
    e.add_argument("--detail", required=True, help="Hesap Detay tarzi trend/detay dosyasi")
    e.add_argument("--sheet", default=None, help="detay sayfa adi (varsayilan ilk)")
    e.add_argument("--overdue", default=None, help="overdue dosyasi (bin EUR)")
    e.add_argument("--pool", default=None, help="Citi pool dosyasi")
    e.add_argument("--month", default=None, help="zenginlestirilecek ay (varsayilan son)")
    e.add_argument("--eurtry", type=float, default=None)
    e.add_argument("--sheet2-gap", type=float, default=None, help="bilinen Sheet2 farki (not)")
    e.add_argument("--out-dir", default=DEFAULT_SNAP)
    e.set_defaults(func=cmd_extract)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
