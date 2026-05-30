"""Tek dosyalık, interaktif HTML dashboard üreticisi.

Excel çıktısının yanında; tarayıcıda açılan, harici bağımlılığı (CDN/JS
kütüphanesi) olmayan bir özet panel üretir: KPI kartları, ilk N fonun
inline-SVG bar grafiği ve renk kodlu, sütundan sıralanabilir tam tablo.
Renk şeması Excel çıktısıyla (config.RANK_FILLS) aynıdır.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
from typing import Dict

import pandas as pd

from . import config


def _argb_to_css(argb: str) -> str:
    """'FFE2EFDA' (ARGB) -> '#E2EFDA' (CSS hex, alfa atılır)."""
    s = str(argb)
    return "#" + (s[2:] if len(s) == 8 else s)


def _rank_css(rank: int) -> str:
    for upto, color in config.RANK_FILLS:
        if rank <= upto:
            return _argb_to_css(color)
    return _argb_to_css(config.DEFAULT_FILL)


def _fmt_pct(v) -> str:
    return "—" if pd.isna(v) else f"{v * 100:.2f}%"


def _fmt_int(v) -> str:
    return "—" if v is None or pd.isna(v) else f"{int(v):,}".replace(",", ".")


def write_html_dashboard(df: pd.DataFrame, out_path: str, *,
                         weights: Dict[str, float] = None,
                         asof: str = "", top_n: int = 15) -> str:
    """Sıralanmış matrix DataFrame'inden tek dosyalık HTML dashboard yazar."""
    weights = weights or config.WEIGHTS
    asof = asof or _dt.date.today().isoformat()

    wavg = df["AĞIRLIKLI ORT"]
    best = df.iloc[0]
    worst = df.iloc[-1]
    kpis = [
        ("Fon Sayısı", str(len(df)), ""),
        ("Ortalama Mevd. Eşl.", _fmt_pct(wavg.mean()), ""),
        ("Medyan Mevd. Eşl.", _fmt_pct(wavg.median()), ""),
        ("En Yüksek", _fmt_pct(best["AĞIRLIKLI ORT"]), str(best["Fon Kodu"])),
        ("En Düşük", _fmt_pct(worst["AĞIRLIKLI ORT"]), str(worst["Fon Kodu"])),
        ("Aralık (maks–min)", _fmt_pct(best["AĞIRLIKLI ORT"] - worst["AĞIRLIKLI ORT"]), ""),
        ("Ağırlıklar (1G/7G/15G)",
         f"{weights['1G']:.0%} / {weights['7G']:.0%} / {weights['15G']:.0%}", ""),
    ]

    kpi_html = "\n".join(
        f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-sub">{html.escape(sub)}</div></div>'
        for label, value, sub in kpis
    )

    chart_html = _svg_bar_chart(df.head(top_n))

    # Tam tablo verisi (JS ile sıralanır)
    rows = []
    for _, r in df.iterrows():
        rank = int(r["Sıra"])
        rows.append({
            "rank": rank,
            "code": str(r["Fon Kodu"]),
            "name": str(r["Fon Adı"]),
            "g1": None if pd.isna(r["1G ME"]) else round(float(r["1G ME"]) * 100, 2),
            "g7": None if pd.isna(r["7G ME"]) else round(float(r["7G ME"]) * 100, 2),
            "g15": None if pd.isna(r["15G ME"]) else round(float(r["15G ME"]) * 100, 2),
            "wavg": None if pd.isna(r["AĞIRLIKLI ORT"]) else round(float(r["AĞIRLIKLI ORT"]) * 100, 2),
            "size": None if pd.isna(r["Fon Tutar"]) else float(r["Fon Tutar"]),
            "inv": None if pd.isna(r["Fon Kişi Sayısı"]) else int(r["Fon Kişi Sayısı"]),
            "color": _rank_css(rank),
        })
    data_json = json.dumps(rows, ensure_ascii=False)

    doc = _TEMPLATE.format(
        asof=html.escape(asof),
        kpis=kpi_html,
        chart=chart_html,
        data=data_json,
        generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def _svg_bar_chart(top: pd.DataFrame, width: int = 720, bar_h: int = 26,
                   gap: int = 8, pad_left: int = 70, pad_right: int = 90) -> str:
    """İlk N fonun ağırlıklı ME'sini yatay bar grafik (inline SVG) olarak çizer."""
    vals = top["AĞIRLIKLI ORT"].astype(float).tolist()
    codes = top["Fon Kodu"].astype(str).tolist()
    if not vals:
        return "<p>Veri yok.</p>"
    vmax = max(vals) or 1.0
    plot_w = width - pad_left - pad_right
    height = len(vals) * (bar_h + gap) + gap
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" '
             f'role="img" aria-label="İlk {len(vals)} fon">']
    for i, (code, v) in enumerate(zip(codes, vals)):
        y = gap + i * (bar_h + gap)
        bw = max(2, plot_w * (v / vmax))
        color = _rank_css(i + 1)
        parts.append(
            f'<text x="{pad_left - 8}" y="{y + bar_h * 0.7}" '
            f'class="bar-code" text-anchor="end">{html.escape(code)}</text>'
            f'<rect x="{pad_left}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
            f'rx="3" fill="{color}" stroke="#1F4E79" stroke-width="0.6"/>'
            f'<text x="{pad_left + bw + 6:.1f}" y="{y + bar_h * 0.7}" '
            f'class="bar-val">{v * 100:.2f}%</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TEFAS PPF Mevduat Eşleniği — {asof}</title>
<style>
  :root {{ --navy:#002060; --line:#1F4E79; --bg:#f4f6fa; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:'Segoe UI',system-ui,Arial,sans-serif;
         background:var(--bg); color:#1a1a1a; }}
  header {{ background:var(--navy); color:#fff; padding:20px 28px; }}
  header h1 {{ margin:0; font-size:20px; }}
  header .sub {{ opacity:.8; font-size:13px; margin-top:4px; }}
  main {{ max-width:1100px; margin:0 auto; padding:22px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
          gap:12px; margin-bottom:22px; }}
  .kpi {{ background:#fff; border:1px solid #e2e6ee; border-radius:10px;
         padding:14px 16px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
  .kpi-label {{ font-size:12px; color:#5b6472; text-transform:uppercase;
               letter-spacing:.03em; }}
  .kpi-value {{ font-size:22px; font-weight:700; color:var(--navy); margin-top:6px; }}
  .kpi-sub {{ font-size:12px; color:#8a93a3; min-height:14px; }}
  section {{ background:#fff; border:1px solid #e2e6ee; border-radius:10px;
            padding:18px; margin-bottom:22px; }}
  section h2 {{ margin:0 0 14px; font-size:15px; color:var(--navy); }}
  .chart {{ width:100%; height:auto; }}
  .bar-code {{ font-size:12px; font-weight:600; fill:#333; }}
  .bar-val {{ font-size:11px; fill:#444; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th, td {{ padding:7px 9px; text-align:right; border-bottom:1px solid #eef0f4; }}
  th:nth-child(2), td:nth-child(2),
  th:nth-child(3), td:nth-child(3) {{ text-align:left; }}
  th {{ background:var(--navy); color:#fff; cursor:pointer; user-select:none;
       position:sticky; top:0; white-space:nowrap; }}
  th:hover {{ background:#0a2f7a; }}
  th .arrow {{ font-size:10px; opacity:.7; }}
  td.code {{ font-weight:600; }}
  .tbl-wrap {{ max-height:620px; overflow:auto; border-radius:8px; }}
  footer {{ text-align:center; color:#8a93a3; font-size:12px; padding:10px 0 30px; }}
</style>
</head>
<body>
<header>
  <h1>TEFAS Para Piyasası Fonları — Mevduat Eşleniği Dashboard</h1>
  <div class="sub">As-of: {asof} · Üretim: {generated}</div>
</header>
<main>
  <div class="kpis">{kpis}</div>
  <section>
    <h2>İlk sıradaki fonlar — Ağırlıklı Mevduat Eşleniği</h2>
    {chart}
  </section>
  <section>
    <h2>Tüm Fonlar (başlığa tıklayarak sırala)</h2>
    <div class="tbl-wrap">
      <table id="t">
        <thead><tr>
          <th data-k="rank" data-t="n">Sıra<span class="arrow"></span></th>
          <th data-k="code" data-t="s">Kod<span class="arrow"></span></th>
          <th data-k="name" data-t="s">Fon Adı<span class="arrow"></span></th>
          <th data-k="g1" data-t="n">1G ME<span class="arrow"></span></th>
          <th data-k="g7" data-t="n">7G ME<span class="arrow"></span></th>
          <th data-k="g15" data-t="n">15G ME<span class="arrow"></span></th>
          <th data-k="wavg" data-t="n">AĞ. ORT<span class="arrow"></span></th>
          <th data-k="size" data-t="n">Fon Tutar<span class="arrow"></span></th>
          <th data-k="inv" data-t="n">Kişi<span class="arrow"></span></th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </section>
  <footer>tefas_matrix · mevduat eşleniği = yıllık getiri × (1 − fon stopaj) / (1 − mevduat stopaj)</footer>
</main>
<script>
const DATA = {data};
const pct = v => v==null ? "—" : v.toFixed(2)+"%";
const intf = v => v==null ? "—" : Math.round(v).toLocaleString("tr-TR");
function render(rows) {{
  const tb = document.querySelector("#t tbody");
  tb.innerHTML = rows.map(r => `<tr style="background:${{r.color}}">
    <td>${{r.rank}}</td><td class="code">${{r.code}}</td>
    <td>${{r.name}}</td><td>${{pct(r.g1)}}</td><td>${{pct(r.g7)}}</td>
    <td>${{pct(r.g15)}}</td><td><b>${{pct(r.wavg)}}</b></td>
    <td>${{intf(r.size)}}</td><td>${{intf(r.inv)}}</td></tr>`).join("");
}}
let sortKey="rank", sortDir=1;
function sortBy(k, t) {{
  if (k===sortKey) sortDir=-sortDir; else {{ sortKey=k; sortDir=1; }}
  const rows=[...DATA].sort((a,b)=>{{
    let x=a[k], y=b[k];
    if (x==null) return 1; if (y==null) return -1;
    if (t==="s") return sortDir*String(x).localeCompare(String(y),"tr");
    return sortDir*(x-y);
  }});
  document.querySelectorAll("#t th .arrow").forEach(s=>s.textContent="");
  const th=document.querySelector(`#t th[data-k="${{k}}"] .arrow`);
  if (th) th.textContent = sortDir>0 ? "▲" : "▼";
  render(rows);
}}
document.querySelectorAll("#t th").forEach(th=>
  th.addEventListener("click",()=>sortBy(th.dataset.k, th.dataset.t)));
render(DATA);
</script>
</body>
</html>
"""
