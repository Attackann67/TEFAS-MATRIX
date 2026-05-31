"""Tek dosyalık, interaktif, detaylı HTML dashboard üreticisi.

Excel çıktısının yanında; tarayıcıda açılan, harici bağımlılığı (CDN/JS
kütüphanesi) olmayan bir özet panel üretir. İki sekme:
  1) Sıralama  — KPI kartları, ilk N fon bar grafiği, sütundan sıralanabilir
     tam tablo (Tür + Büyüklük + 1G/7G/15G ME + AĞ.ORT).
  2) Portföy Dağılımı — ortalama varlık sınıfı bar grafiği + fon×sınıf
     ısı haritası (heatmap) tablosu.
Renk şeması Excel çıktısıyla (config.RANK_FILLS) aynıdır.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
from typing import Dict

import pandas as pd

from . import config
from .compute import portfolio_breakdown


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


def _fmt_tl(v) -> str:
    """TL büyüklüğü kısa biçim (mr/mn)."""
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    if v >= 1e9:
        return f"{v / 1e9:.1f} mr"
    if v >= 1e6:
        return f"{v / 1e6:.0f} mn"
    return f"{v:,.0f}"


def write_html_dashboard(df: pd.DataFrame, out_path: str, *,
                         weights: Dict[str, float] = None,
                         asof: str = "", top_n: int = 15) -> str:
    """Sıralanmış matrix DataFrame'inden tek dosyalık detaylı HTML dashboard yazar."""
    weights = weights or config.WEIGHTS
    asof = asof or _dt.date.today().isoformat()

    wavg = df["AĞIRLIKLI ORT"]
    best = df.iloc[0]
    worst = df.iloc[-1]
    has_size = df["Fon Tutar"].notna().any()
    total_aum = df["Fon Tutar"].sum(skipna=True) if has_size else None

    # Tür kırılımı
    tur_counts = {}
    if "Tür" in df.columns:
        for t in df["Tür"].fillna(""):
            t = t or "—"
            tur_counts[t] = tur_counts.get(t, 0) + 1
    tur_str = " · ".join(f"{k}: {v}" for k, v in sorted(tur_counts.items(),
                                                        key=lambda x: -x[1])) or "—"

    kpis = [
        ("Fon Sayısı", str(len(df)), ""),
        ("Toplam Büyüklük", _fmt_tl(total_aum) + (" TL" if has_size else ""),
         "" if has_size else "büyüklük yok"),
        ("Ortalama Mevd. Eşl.", _fmt_pct(wavg.mean()), ""),
        ("Medyan Mevd. Eşl.", _fmt_pct(wavg.median()), ""),
        ("En Yüksek", _fmt_pct(best["AĞIRLIKLI ORT"]), str(best["Fon Kodu"])),
        ("En Düşük", _fmt_pct(worst["AĞIRLIKLI ORT"]), str(worst["Fon Kodu"])),
        ("Ağırlıklar (1G/7G/15G)",
         f"{weights['1G']:.0%} / {weights['7G']:.0%} / {weights['15G']:.0%}", ""),
        ("Tür Kırılımı", tur_str, ""),
    ]
    kpi_html = "\n".join(
        f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-sub">{html.escape(sub)}</div></div>'
        for label, value, sub in kpis
    )

    chart_html = _svg_bar_chart(df.head(top_n))

    # Portföy dağılımı: her fon için breakdown
    asset_labels = [lbl for lbl, _ in config.PD_OUTPUT_COLUMNS] + ["Diğer (%)"]
    breakdowns = {}
    for _, r in df.iterrows():
        bd = portfolio_breakdown(r["_alloc"]) if r["_alloc"] else {}
        if bd:
            breakdowns[str(r["Fon Kodu"])] = bd
    has_dist = bool(breakdowns)

    # Yalnızca kullanılan (toplamı >0) varlık sınıflarını göster
    used_labels = [lbl for lbl in asset_labels
                   if any(abs(bd.get(lbl, 0.0)) > 1e-9 for bd in breakdowns.values())]
    avg_alloc = {lbl: (sum(bd.get(lbl, 0.0) for bd in breakdowns.values())
                       / max(1, len(breakdowns))) for lbl in used_labels}
    dist_chart_html = _svg_alloc_chart(avg_alloc) if has_dist else \
        "<p>Portföy dağılımı verisi yok (canlı API vermemiş olabilir).</p>"

    # Tablo verisi
    rows = []
    for _, r in df.iterrows():
        rank = int(r["Sıra"])
        code = str(r["Fon Kodu"])
        bd = breakdowns.get(code, {})
        rows.append({
            "rank": rank,
            "code": code,
            "name": str(r["Fon Adı"]),
            "tur": str(r.get("Tür", "") or ""),
            "g1": None if pd.isna(r["1G ME"]) else round(float(r["1G ME"]) * 100, 2),
            "g7": None if pd.isna(r["7G ME"]) else round(float(r["7G ME"]) * 100, 2),
            "g15": None if pd.isna(r["15G ME"]) else round(float(r["15G ME"]) * 100, 2),
            "wavg": None if pd.isna(r["AĞIRLIKLI ORT"]) else round(float(r["AĞIRLIKLI ORT"]) * 100, 2),
            "size": None if pd.isna(r["Fon Tutar"]) else float(r["Fon Tutar"]),
            "color": _rank_css(rank),
            "dist": {lbl: round(bd.get(lbl, 0.0), 2) for lbl in used_labels} if bd else None,
        })

    doc = _TEMPLATE.format(
        asof=html.escape(asof),
        kpis=kpi_html,
        chart=chart_html,
        dist_chart=dist_chart_html,
        data=json.dumps(rows, ensure_ascii=False),
        asset_labels=json.dumps(used_labels, ensure_ascii=False),
        has_dist=json.dumps(has_dist),
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


# Varlık sınıfı renk paleti (heatmap + ortalama grafik için)
_ASSET_COLORS = [
    "#1F4E79", "#2E75B6", "#5B9BD5", "#9DC3E6", "#70AD47", "#A9D18E",
    "#FFC000", "#ED7D31", "#C55A11", "#7030A0", "#A6A6A6", "#264478",
    "#636363", "#997300",
]


def _svg_alloc_chart(avg_alloc: Dict[str, float], width: int = 720,
                     bar_h: int = 22, gap: int = 7, pad_left: int = 170,
                     pad_right: int = 60) -> str:
    """Ortalama varlık sınıfı dağılımını yatay bar grafik olarak çizer."""
    items = sorted(avg_alloc.items(), key=lambda x: -x[1])
    items = [(k, v) for k, v in items if abs(v) > 1e-9]
    if not items:
        return "<p>Veri yok.</p>"
    vmax = max(v for _, v in items) or 1.0
    plot_w = width - pad_left - pad_right
    height = len(items) * (bar_h + gap) + gap
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" '
             f'role="img" aria-label="Ortalama varlık dağılımı">']
    for i, (label, v) in enumerate(items):
        y = gap + i * (bar_h + gap)
        bw = max(1.5, plot_w * (v / vmax))
        color = _ASSET_COLORS[i % len(_ASSET_COLORS)]
        lbl = label.replace(" (%)", "")
        parts.append(
            f'<text x="{pad_left - 8}" y="{y + bar_h * 0.7}" '
            f'class="bar-code" text-anchor="end">{html.escape(lbl)}</text>'
            f'<rect x="{pad_left}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
            f'rx="3" fill="{color}"/>'
            f'<text x="{pad_left + bw + 6:.1f}" y="{y + bar_h * 0.7}" '
            f'class="bar-val">{v:.1f}%</text>'
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
  main {{ max-width:1180px; margin:0 auto; padding:22px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
          gap:12px; margin-bottom:22px; }}
  .kpi {{ background:#fff; border:1px solid #e2e6ee; border-radius:10px;
         padding:14px 16px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
  .kpi-label {{ font-size:12px; color:#5b6472; text-transform:uppercase;
               letter-spacing:.03em; }}
  .kpi-value {{ font-size:20px; font-weight:700; color:var(--navy); margin-top:6px; }}
  .kpi-sub {{ font-size:12px; color:#8a93a3; min-height:14px; }}
  .tabs {{ display:flex; gap:6px; margin-bottom:14px; }}
  .tab {{ padding:9px 18px; border:1px solid #d6dbe6; background:#fff;
         border-radius:8px 8px 0 0; cursor:pointer; font-weight:600;
         color:#5b6472; }}
  .tab.active {{ background:var(--navy); color:#fff; border-color:var(--navy); }}
  .panel {{ display:none; }}
  .panel.active {{ display:block; }}
  section {{ background:#fff; border:1px solid #e2e6ee; border-radius:10px;
            padding:18px; margin-bottom:22px; }}
  section h2 {{ margin:0 0 14px; font-size:15px; color:var(--navy); }}
  .chart {{ width:100%; height:auto; }}
  .bar-code {{ font-size:12px; font-weight:600; fill:#333; }}
  .bar-val {{ font-size:11px; fill:#444; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th, td {{ padding:7px 9px; text-align:right; border-bottom:1px solid #eef0f4;
           white-space:nowrap; }}
  th.l, td.l {{ text-align:left; }}
  th {{ background:var(--navy); color:#fff; cursor:pointer; user-select:none;
       position:sticky; top:0; }}
  th:hover {{ background:#0a2f7a; }}
  th .arrow {{ font-size:10px; opacity:.7; }}
  td.code {{ font-weight:600; }}
  .tbl-wrap {{ max-height:640px; overflow:auto; border-radius:8px; }}
  .hm td.n {{ font-size:12px; }}
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

  <div class="tabs">
    <div class="tab active" data-tab="rank">Sıralama</div>
    <div class="tab" data-tab="dist">Portföy Dağılımı</div>
  </div>

  <div class="panel active" id="panel-rank">
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
            <th class="l" data-k="code" data-t="s">Kod<span class="arrow"></span></th>
            <th class="l" data-k="name" data-t="s">Fon Adı<span class="arrow"></span></th>
            <th class="l" data-k="tur" data-t="s">Tür<span class="arrow"></span></th>
            <th data-k="size" data-t="n">Büyüklük<span class="arrow"></span></th>
            <th data-k="g1" data-t="n">1G ME<span class="arrow"></span></th>
            <th data-k="g7" data-t="n">7G ME<span class="arrow"></span></th>
            <th data-k="g15" data-t="n">15G ME<span class="arrow"></span></th>
            <th data-k="wavg" data-t="n">AĞ. ORT<span class="arrow"></span></th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
  </div>

  <div class="panel" id="panel-dist">
    <section>
      <h2>Ortalama Varlık Sınıfı Dağılımı</h2>
      {dist_chart}
    </section>
    <section>
      <h2>Fon × Varlık Sınıfı (%) — ısı haritası</h2>
      <div class="tbl-wrap">
        <table id="hm" class="hm"><thead></thead><tbody></tbody></table>
      </div>
    </section>
  </div>

  <footer>tefas_matrix · mevduat eşleniği = yıllık getiri × (1 − fon stopaj) / (1 − mevduat stopaj)</footer>
</main>
<script>
const DATA = {data};
const ASSETS = {asset_labels};
const HAS_DIST = {has_dist};
const pct = v => v==null ? "—" : v.toFixed(2)+"%";
const tl = v => {{
  if (v==null) return "—";
  if (v>=1e9) return (v/1e9).toFixed(1)+" mr";
  if (v>=1e6) return (v/1e6).toFixed(0)+" mn";
  return Math.round(v).toLocaleString("tr-TR");
}};
function render(rows) {{
  document.querySelector("#t tbody").innerHTML = rows.map(r => `<tr style="background:${{r.color}}">
    <td>${{r.rank}}</td><td class="l code">${{r.code}}</td>
    <td class="l">${{r.name}}</td><td class="l">${{r.tur}}</td>
    <td>${{tl(r.size)}}</td><td>${{pct(r.g1)}}</td><td>${{pct(r.g7)}}</td>
    <td>${{pct(r.g15)}}</td><td><b>${{pct(r.wavg)}}</b></td></tr>`).join("");
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

// Heatmap (Portföy Dağılımı)
function heatColor(v) {{
  if (!v) return "#ffffff";
  const a = Math.min(1, v/60);   // %60+ tam doygun
  return `rgba(31,78,121,${{0.08 + a*0.72}})`;
}}
function buildHeatmap() {{
  if (!HAS_DIST) {{
    document.querySelector("#hm thead").innerHTML =
      "<tr><th class='l'>Bilgi</th></tr>";
    document.querySelector("#hm tbody").innerHTML =
      "<tr><td class='l'>Portföy dağılımı verisi yok.</td></tr>";
    return;
  }}
  const head = "<tr><th>Sıra</th><th class='l'>Kod</th>" +
    ASSETS.map(a=>`<th>${{a.replace(' (%)','')}}</th>`).join("") + "</tr>";
  document.querySelector("#hm thead").innerHTML = head;
  document.querySelector("#hm tbody").innerHTML = DATA.map(r=>{{
    if (!r.dist) return `<tr><td>${{r.rank}}</td><td class="l code">${{r.code}}</td>`+
      `<td class="l" colspan="${{ASSETS.length}}" style="color:#c0392b">PD YOK</td></tr>`;
    const cells = ASSETS.map(a=>{{
      const v = r.dist[a] || 0;
      return `<td class="n" style="background:${{heatColor(v)}};${{v>40?'color:#fff':''}}">`+
             `${{v? v.toFixed(1):'·'}}</td>`;
    }}).join("");
    return `<tr><td>${{r.rank}}</td><td class="l code">${{r.code}}</td>${{cells}}</tr>`;
  }}).join("");
}}
buildHeatmap();

// Sekmeler
document.querySelectorAll(".tab").forEach(t=>t.addEventListener("click",()=>{{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(x=>x.classList.remove("active"));
  t.classList.add("active");
  document.getElementById("panel-"+t.dataset.tab).classList.add("active");
}}));
</script>
</body>
</html>
"""
