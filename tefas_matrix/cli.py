"""Komut satırı arayüzü.

Örnekler:
  # TEFAS Excel export'undan üret (birincil yol)
  python -m tefas_matrix --source TEFAS_ARGE.xlsx --out Matrix.xlsx

  # Canlı çek (TEFAS erişimi gerektirir)
  python -m tefas_matrix --live --asof 2026-05-29 --out Matrix.xlsx

  # Ağırlıkları değiştir
  python -m tefas_matrix --source in.xlsx --out out.xlsx --w1 0.5 --w7 0.35 --w15 0.15
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys

from . import config
from .compute import build_matrix
from .dashboard import write_html_dashboard
from .sources import filter_ppf, from_live, from_workbook
from .workbook import write_workbook


def main(argv=None):
    p = argparse.ArgumentParser(prog="tefas_matrix",
                                description="TEFAS PPF Mevduat Eşleniği Matrix üreticisi")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", help="TEFAS Excel export dosya yolu")
    g.add_argument("--live", action="store_true", help="TEFAS'tan canlı fiyat çek")
    p.add_argument("--asof", help="Canlı çekim için T günü (YYYY-MM-DD)")
    p.add_argument("--out", required=True, help="Çıktı .xlsx yolu")
    p.add_argument("--dashboard", nargs="?", const="__auto__",
                   help="İnteraktif HTML dashboard da üret. Yol verilmezse "
                        "--out ile aynı isimde .html yazılır.")
    p.add_argument("--serve", nargs="?", const=8000, type=int, metavar="PORT",
                   help="Dashboard'u yerelde (localhost) servis et ve tarayıcıda "
                        "aç. Varsayılan port 8000. --dashboard verilmese de çalışır.")
    p.add_argument("--w1", type=float, default=config.WEIGHTS["1G"])
    p.add_argument("--w7", type=float, default=config.WEIGHTS["7G"])
    p.add_argument("--w15", type=float, default=config.WEIGHTS["15G"])
    p.add_argument("--no-filter", action="store_true",
                   help="Para piyasası adı/büyüklük filtresini uygulama")
    p.add_argument("--keep-excluded", action="store_true",
                   help="Hariç tutulan fon listesini uygulama")
    args = p.parse_args(argv)

    weights = {"1G": args.w1, "7G": args.w7, "15G": args.w15}
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        print(f"UYARI: ağırlık toplamı %100 değil ({sum(weights.values()):.0%}).",
              file=sys.stderr)

    if args.live:
        print("TEFAS'tan canlı fiyat çekiliyor...", file=sys.stderr)
        records = from_live(asof=args.asof)
        records = filter_ppf(records) if not args.no_filter else records
        print("NOT: Canlı API portföy dağılımı/kişi sayısı vermez; bu alanlar boş.",
              file=sys.stderr)
    else:
        records = from_workbook(args.source)
        if not args.no_filter:
            records = filter_ppf(records)

    exclude = set() if args.keep_excluded else config.EXCLUDE
    df = build_matrix(records, weights=weights, exclude=exclude)

    asof = args.asof or _dt.date.today().isoformat()
    write_workbook(df, args.out, weights=weights, asof=asof)
    print(f"✓ {len(df)} fon yazıldı -> {args.out}")

    # --serve, --dashboard verilmese de HTML'e ihtiyaç duyar.
    html_path = None
    if args.dashboard is not None or args.serve is not None:
        html_path = args.dashboard if args.dashboard not in (None, "__auto__") else \
            (args.out[:-5] if args.out.lower().endswith(".xlsx") else args.out) + ".html"
        write_html_dashboard(df, html_path, weights=weights, asof=asof)
        print(f"✓ HTML dashboard -> {html_path}")

    print("İlk 5:")
    for _, r in df.head(5).iterrows():
        print(f"  {int(r['Sıra'])}. {r['Fon Kodu']:<4} "
              f"AĞ.ORT={r['AĞIRLIKLI ORT']:.4%}  {r['Fon Adı'][:45]}")

    if args.serve is not None:
        from .serve import serve_dashboard
        serve_dashboard(html_path, port=args.serve)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
