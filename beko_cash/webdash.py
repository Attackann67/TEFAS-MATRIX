"""Web dashboard uretici: snapshot'lardan tek dosyalik, kendi kendine yeten HTML.

Excel'e alternatif goruntuleme katmani. Veri sayfaya JSON olarak gomulur;
grafikler inline SVG ile cizilir (dis kaynak yok, CSP uyumlu). Renk kurali
korunur: Beko lacivert #002060 marka, seri renkleri dogrulanmis palet
(mavi/su yesili/amber), durum renkleri ayri (PASS yesil, SORGULA kirmizi).

CLI: python -m beko_cash web --out dashboard.html
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from . import compute, schema, snapshot as snap_mod

_AY_TR = {"01": "Oca", "02": "Sub", "03": "Mar", "04": "Nis", "05": "May", "06": "Haz",
          "07": "Tem", "08": "Agu", "09": "Eyl", "10": "Eki", "11": "Kas", "12": "Ara"}


def _ay_label(m: str) -> str:
    y, mm = m.split("-")
    return f"{_AY_TR.get(mm, mm)} {y[2:]}"


def build_data(snaps: List[dict]) -> dict:
    """Snapshot'lardan sayfaya gomulecek kompakt JSON verisini uretir."""
    months = compute.months(snaps)
    segments = {}
    categories = {}
    checks = {}
    eurtry = {}
    for snap in snaps:
        m = snap["month"]
        eurtry[m] = snap.get("eurtry")
        seg_tot = {s: 0.0 for s in schema.SEGMENTS}
        cat_tot = {}
        for code, ent in snap.get("entities", {}).items():
            seg_tot[schema.segment_of(code)] += float(ent.get("tot_tl", 0) or 0)
            for kk, tl in (ent.get("cat_tl") or {}).items():
                cat_tot[kk] = cat_tot.get(kk, 0.0) + float(tl or 0)
        segments[m] = {k: round(v, 2) for k, v in seg_tot.items()}
        categories[m] = {k: round(v, 2) for k, v in cat_tot.items()}
        checks[m] = {
            "detail_vs_source": snap.get("checks", {}).get("detail_vs_source"),
            "sheet2_gap": snap.get("checks", {}).get("sheet2_gap"),
            "source_total": snap.get("source_total_tl"),
        }

    last = snaps[-1]
    entities = []
    universe = compute.entity_universe(snaps)
    per_month = {s["month"]: s.get("entities", {}) for s in snaps}
    for code, name in universe:
        tot = {}
        vad = {}
        for m in months:
            ent = per_month[m].get(code)
            if ent is None:
                continue
            tot[m] = round(float(ent.get("tot_tl", 0) or 0), 2)
            vad[m] = round(snap_mod.entity_groups(ent)["Vadesiz"], 2)
        ent_last = per_month[last["month"]].get(code, {})
        entities.append({
            "kod": code, "ad": name, "seg": schema.segment_of(code),
            "tot": tot, "vad": vad,
            "ovd": ent_last.get("overdue_keur"),
            "ovd_prev": ent_last.get("overdue_prev_keur"),
            "pool": ent_last.get("citi_pool_eur"),
            "match": ent_last.get("match"),
            "status": ent_last.get("status"),
            "sorgu": ent_last.get("sorgu"),
        })

    pool = last.get("pool", {}) or {}
    participants = []
    for firm, bal in (pool.get("participants") or {}).items():
        code, le = schema.pool_participant_entity(firm)
        participants.append({"ad": firm, "bal": bal, "kod": code or "Eslesmedi", "le": le})
    participants.sort(key=lambda p: -p["bal"])

    return {
        "months": months,
        "ay_labels": {m: _ay_label(m) for m in months},
        "eurtry": eurtry,
        "segments": segments,
        "categories": categories,
        "cat_labels": schema.CATEGORY_LABEL,
        "cat_order": schema.CATEGORY_ORDER,
        "checks": checks,
        "entities": entities,
        "pool": {"grand": pool.get("grand_total_eur"), "arcelik": pool.get("arcelik_eur"),
                 "participants": participants},
        "esik": schema.SORGULA_ESIK,
        "last": last["month"],
    }


def render(snaps: List[dict]) -> str:
    data = build_data(snaps)
    return _TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))


def write(snaps: List[dict], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.write_text(render(snaps), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Sablon: tek dosya, dis kaynak yok. Tokens :root uzerinde; koyu tema hem
# prefers-color-scheme hem data-theme ile secilir (ikisi de iki yonlu).
# ---------------------------------------------------------------------------

_TEMPLATE = r"""<title>Beko Cash Dashboard</title>
<style>
:root{
  --brand:#002060; --brand-ink:#ffffff; --accent:#2a78d6;
  --plane:#f4f6f9; --card:#ffffff; --card2:#eef1f6;
  --ink:#101418; --ink2:#4d5560; --muted:#8a919c;
  --grid:#e3e7ee; --axis:#c2c9d4; --ring:rgba(16,20,24,.09);
  --s1:#2a78d6; --s2:#1baf7a; --s3:#eda100;
  --good:#0ca30c; --good-ink:#006300; --warn:#fab219; --crit:#d03b3b;
  --pos:#2a78d6; --neg:#e34948;
  --chip:#e8edf5; --chip-ink:#26436e;
}
@media (prefers-color-scheme: dark){
  :root{
    --brand:#0c1c42; --brand-ink:#e8eefb; --accent:#3987e5;
    --plane:#0e1013; --card:#171a1f; --card2:#1e222a;
    --ink:#eceff3; --ink2:#aab2be; --muted:#7d8590;
    --grid:#262b33; --axis:#3a414c; --ring:rgba(255,255,255,.08);
    --s1:#3987e5; --s2:#199e70; --s3:#c98500;
    --good:#0ca30c; --good-ink:#3ec53e; --warn:#fab219; --crit:#e66767;
    --pos:#3987e5; --neg:#e66767;
    --chip:#233046; --chip-ink:#b9cdf1;
  }
}
:root[data-theme="light"]{
  --brand:#002060; --brand-ink:#ffffff; --accent:#2a78d6;
  --plane:#f4f6f9; --card:#ffffff; --card2:#eef1f6;
  --ink:#101418; --ink2:#4d5560; --muted:#8a919c;
  --grid:#e3e7ee; --axis:#c2c9d4; --ring:rgba(16,20,24,.09);
  --s1:#2a78d6; --s2:#1baf7a; --s3:#eda100;
  --good:#0ca30c; --good-ink:#006300; --warn:#fab219; --crit:#d03b3b;
  --pos:#2a78d6; --neg:#e34948;
  --chip:#e8edf5; --chip-ink:#26436e;
}
:root[data-theme="dark"]{
  --brand:#0c1c42; --brand-ink:#e8eefb; --accent:#3987e5;
  --plane:#0e1013; --card:#171a1f; --card2:#1e222a;
  --ink:#eceff3; --ink2:#aab2be; --muted:#7d8590;
  --grid:#262b33; --axis:#3a414c; --ring:rgba(255,255,255,.08);
  --s1:#3987e5; --s2:#199e70; --s3:#c98500;
  --good:#0ca30c; --good-ink:#3ec53e; --warn:#fab219; --crit:#e66767;
  --pos:#3987e5; --neg:#e66767;
  --chip:#233046; --chip-ink:#b9cdf1;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
  font:13px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;}
.mast{background:var(--brand);color:var(--brand-ink);padding:18px 28px 16px;}
.mast h1{margin:0;font-size:19px;font-weight:650;letter-spacing:.01em}
.mast .sub{margin-top:6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.kchip{font-size:11px;padding:3px 9px;border-radius:999px;
  background:rgba(255,255,255,.13);color:var(--brand-ink);letter-spacing:.02em}
.wrap{max-width:1280px;margin:0 auto;padding:20px 24px 48px;
  display:grid;grid-template-columns:repeat(12,1fr);gap:14px;}
.card{background:var(--card);border:1px solid var(--ring);border-radius:10px;
  padding:14px 16px;min-width:0;}
.card h2{margin:0 0 2px;font-size:13.5px;font-weight:650}
.card .note{font-size:11px;color:var(--muted);margin:0 0 10px}
.eyebrow{font-size:10.5px;font-weight:600;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted)}
.kpis{grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.kpi{background:var(--card);border:1px solid var(--ring);border-radius:10px;padding:12px 14px}
.kpi .v{font-size:27px;font-weight:650;letter-spacing:-.01em;margin:4px 0 1px}
.kpi .d{font-size:11.5px;color:var(--ink2)}
.kpi .up{color:var(--good-ink)} .kpi .dn{color:var(--crit)}
.span8{grid-column:span 8}.span6{grid-column:span 6}
.span4{grid-column:span 4}.span12{grid-column:1/-1}
@media(max-width:900px){.span8,.span6,.span4{grid-column:1/-1}}
svg{display:block;width:100%;height:auto}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:2px 0 8px;font-size:11.5px;color:var(--ink2)}
.legend .sw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  text-align:right;padding:7px 8px;border-bottom:1px solid var(--grid);white-space:nowrap}
th:first-child,th.l,td.l{text-align:left}
td{padding:6px 8px;border-bottom:1px solid var(--grid);text-align:right;white-space:nowrap;font-size:12.3px}
tbody tr:hover{background:var(--card2)}
.pill{display:inline-block;font-size:10.3px;font-weight:650;padding:2px 8px;border-radius:999px}
.pill.sorgula{background:color-mix(in srgb,var(--crit) 14%,transparent);color:var(--crit)}
.pill.pass{background:color-mix(in srgb,var(--good) 14%,transparent);color:var(--good-ink)}
.pill.kesin{background:var(--chip);color:var(--chip-ink)}
.pill.olasi{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--ink2)}
.vbar{display:inline-block;height:7px;border-radius:4px;background:var(--s1);vertical-align:middle}
.vtrack{display:inline-block;width:64px;height:7px;border-radius:4px;background:var(--card2);
  vertical-align:middle;margin-right:6px;position:relative;overflow:hidden}
.vtrack .vbar{position:absolute;left:0;top:0}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px;align-items:center}
.filters input{background:var(--card2);border:1px solid var(--ring);color:var(--ink);
  border-radius:7px;padding:6px 10px;font-size:12.5px;min-width:190px;outline:none}
.filters input:focus{border-color:var(--accent)}
.fchip{border:1px solid var(--ring);background:var(--card2);color:var(--ink2);
  font-size:11.5px;padding:5px 11px;border-radius:999px;cursor:pointer;user-select:none}
.fchip.on{background:var(--chip);color:var(--chip-ink);border-color:transparent;font-weight:650}
.fchip:focus-visible,.mrow:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--plane);
  padding:6px 9px;border-radius:7px;font-size:11.5px;line-height:1.4;z-index:9;
  opacity:0;transition:opacity .08s;max-width:260px;white-space:nowrap}
@media (prefers-reduced-motion: reduce){#tip{transition:none}}
.scroll{overflow-x:auto}
.checkrow{display:flex;gap:8px;align-items:baseline;justify-content:space-between;
  padding:7px 0;border-bottom:1px solid var(--grid);font-size:12.3px}
.checkrow:last-child{border-bottom:0}
.mono{font-variant-numeric:tabular-nums}
.small{font-size:11px;color:var(--muted)}
</style>
<div class="mast">
  <h1>Beko Cash Dashboard</h1>
  <div class="sub" id="mastchips"></div>
</div>
<div class="wrap">
  <div class="kpis" id="kpis"></div>

  <div class="card span8">
    <h2>Segment trendi</h2>
    <p class="note">Aylik likit varlik, milyar TL. Kaynak: liquid report Hesap Detay.</p>
    <div class="legend" id="lg-trend"></div>
    <div id="ch-trend"></div>
  </div>

  <div class="card span4">
    <h2>Kontrol</h2>
    <p class="note">Detay toplami = kaynak dosya toplami.</p>
    <div id="checks"></div>
    <p class="small" style="margin:10px 0 0" id="kesitnote"></p>
  </div>

  <div class="card span6">
    <h2>Kategori kirilimi</h2>
    <p class="note" id="cat-note"></p>
    <div id="ch-cat"></div>
  </div>

  <div class="card span6">
    <h2>Citi pool katilimci bakiyeleri</h2>
    <p class="note" id="pool-note"></p>
    <div id="ch-pool"></div>
  </div>

  <div class="card span12">
    <h2>Nakit ve overdue</h2>
    <p class="note">Bin EUR. Nakit 31.05 kesiti, overdue 30.06 kesiti; oranlar gostergedir. C746 konsolide tek satirdir.</p>
    <div class="legend" id="lg-no"></div>
    <div id="ch-no"></div>
  </div>

  <div class="card span12">
    <h2>Istirak matrisi</h2>
    <p class="note">Tum istirakler, aylik toplam TL. SORGULA: son ay vadesiz orani esigi asiyor.</p>
    <div class="filters">
      <input id="q" type="search" placeholder="Istirak ara..." aria-label="Istirak ara">
      <span class="fchip on" data-seg="*">Tumu</span>
      <span class="fchip" data-seg="Istirakler">Istirakler</span>
      <span class="fchip" data-seg="Arcelik">Arcelik</span>
      <span class="fchip" data-seg="Pazarlama">Pazarlama</span>
    </div>
    <div class="scroll"><table id="mtx"></table></div>
  </div>
</div>
<div id="tip" role="status"></div>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const M = D.months, L = D.last, AL = D.ay_labels;
const fmt = new Intl.NumberFormat('tr-TR');
const f1 = new Intl.NumberFormat('tr-TR',{minimumFractionDigits:1,maximumFractionDigits:1});
const f2 = new Intl.NumberFormat('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});
const bn = v => f2.format(v/1e9);
const fmtTL = v => Math.abs(v)>=1e9 ? f2.format(v/1e9)+' mlr' :
                 Math.abs(v)>=1e6 ? f1.format(v/1e6)+' mn' : fmt.format(Math.round(v));
const pct = v => f1.format(v*100)+'%';
const esc = s => String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---- tooltip ---- */
const tip = document.getElementById('tip');
function showTip(html,x,y){tip.innerHTML=html;tip.style.opacity=1;
  const w=tip.offsetWidth,h=tip.offsetHeight;
  tip.style.left=Math.min(x+14,innerWidth-w-8)+'px';
  tip.style.top=Math.max(8,y-h-10)+'px';}
function hideTip(){tip.style.opacity=0}

/* ---- masthead chips ---- */
(function(){
  const el=document.getElementById('mastchips');
  const eur=D.eurtry[L];
  el.innerHTML =
    `<span class="kchip">Kesit: ${AL[L]} (nakit)</span>`+
    `<span class="kchip">Overdue: 30.06 kesiti</span>`+
    `<span class="kchip">Pool: 09.07 gunluk</span>`+
    (eur?`<span class="kchip">EURTRY ${f2.format(eur)} TCMB</span>`:'')+
    `<span class="kchip">${M.length} ay kayitli</span>`;
})();

/* ---- KPIs ---- */
(function(){
  const segL=D.segments[L], segP=D.segments[M[M.length-2]]||null;
  const tot=Object.values(segL).reduce((a,b)=>a+b,0);
  const totP=segP?Object.values(segP).reduce((a,b)=>a+b,0):null;
  const mom=totP?(tot/totP-1):null;
  const eur=D.eurtry[L];
  const ist=segL['Istirakler'];
  let sorgu=0, ovdSum=0, likitIst=0;
  for(const e of D.entities){
    const t=e.tot[L]||0, v=e.vad[L]||0;
    if(t>0 && v/t>=D.esik) sorgu++;
    if(e.ovd!=null){ovdSum+=e.ovd; if(eur) likitIst+=t/eur/1000;}
  }
  const poolIst = (D.pool.grand!=null&&D.pool.arcelik!=null)?D.pool.grand-D.pool.arcelik:null;
  const k=[
    {t:'Grup toplam ('+AL[L]+')', v:bn(tot)+' mlr TL',
     d: eur? f1.format(tot/eur/1e6)+' mn EUR' : 'EURTRY girilmedi',
     x: mom!=null? `<span class="${mom>=0?'up':'dn'}">${mom>=0?'+':''}${pct(mom)} MoM</span>`:''},
    {t:'Istirakler', v:bn(ist)+' mlr TL', d: pct(ist/tot)+' pay'},
    {t:'SORGULA bayragi', v:String(sorgu)+' istirak', d:'vadesiz orani >= '+pct(D.esik)},
    {t:'Likit / Overdue (istirakler)', v: ovdSum? f2.format(likitIst/ovdSum):'-',
     d:'gosterge; kesitler farkli', x:''},
    {t:'Istiraklerin pool bakiyesi', v: poolIst!=null? f1.format(poolIst/1e6)+' mn EUR':'-',
     d:'Grand Total eksi Arcelik'}
  ];
  document.getElementById('kpis').innerHTML=k.map(o=>
    `<div class="kpi"><div class="eyebrow">${o.t}</div><div class="v">${o.v}</div>
     <div class="d">${o.d}${o.x?' &middot; '+o.x:''}</div></div>`).join('');
})();

/* ---- trend line chart ---- */
(function(){
  const segs=['Istirakler','Arcelik','Pazarlama'], cols=['--s1','--s2','--s3'];
  document.getElementById('lg-trend').innerHTML=segs.map((s,i)=>
    `<span><span class="sw" style="background:var(${cols[i]})"></span>${s}</span>`).join('');
  const W=720,H=240,P={l:46,r:118,t:12,b:26};
  const vals=segs.map(s=>M.map(m=>D.segments[m][s]/1e9));
  const ymax=Math.max(...vals.flat())*1.12;
  const x=i=>P.l+(W-P.l-P.r)*(M.length===1?.5:i/(M.length-1));
  const y=v=>H-P.b-(H-P.t-P.b)*(v/ymax);
  let g='';
  const ticks=4;
  for(let t=0;t<=ticks;t++){const v=ymax*t/ticks, yy=y(v);
    g+=`<line x1="${P.l}" x2="${W-P.r}" y1="${yy}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`+
       `<text x="${P.l-7}" y="${yy+3.5}" text-anchor="end" font-size="10" fill="var(--muted)">${f1.format(v)}</text>`;}
  M.forEach((m,i)=>{g+=`<text x="${x(i)}" y="${H-8}" text-anchor="middle" font-size="10.5" fill="var(--ink2)">${AL[m]}</text>`;});
  // uc etiketleri: cakismayi onlemek icin y'leri ayristir (min 13px)
  const ends=segs.map((s,si)=>({si, y:y(vals[si][vals[si].length-1]),
    txt:`${s} ${f1.format(vals[si][vals[si].length-1])}`}));
  ends.sort((a,b)=>a.y-b.y);
  for(let i=1;i<ends.length;i++)
    if(ends[i].y-ends[i-1].y<13) ends[i].y=ends[i-1].y+13;
  const endY={}; ends.forEach(e=>endY[e.si]=e.y);
  segs.forEach((s,si)=>{
    const c=`var(${cols[si]})`;
    const pts=vals[si].map((v,i)=>[x(i),y(v)]);
    g+=`<path d="M${pts.map(p=>p.join(',')).join('L')}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"/>`;
    pts.forEach((p,i)=>{g+=`<circle cx="${p[0]}" cy="${p[1]}" r="${i===M.length-1?4:3}" fill="${c}" stroke="var(--card)" stroke-width="2"/>`;});
    const lp=pts[pts.length-1];
    g+=`<text x="${lp[0]+9}" y="${endY[si]+3.5}" font-size="10.5" font-weight="600" fill="var(--ink2)">${segs[si]} ${f1.format(vals[si][vals[si].length-1])}</text>`;
  });
  g+=`<line x1="${P.l}" x2="${W-P.r}" y1="${H-P.b}" y2="${H-P.b}" stroke="var(--axis)" stroke-width="1"/>`;
  // hover kolonlari
  M.forEach((m,i)=>{
    const cw=(W-P.l-P.r)/Math.max(1,M.length-1);
    g+=`<rect x="${x(i)-cw/2}" y="${P.t}" width="${cw}" height="${H-P.t-P.b}" fill="transparent"
        data-i="${i}" class="hcol"/>`;
  });
  const el=document.getElementById('ch-trend');
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Segment trendi, milyar TL">${g}</svg>`;
  el.querySelectorAll('.hcol').forEach(r=>{
    r.addEventListener('mousemove',ev=>{
      const i=+r.dataset.i, m=M[i];
      const rows=segs.map((s,si)=>`${s}: <b>${f2.format(vals[si][i])} mlr</b>`).join('<br>');
      const tot=vals.reduce((a,v)=>a+v[i],0);
      showTip(`<b>${AL[m]}</b><br>${rows}<br>Toplam: <b>${f2.format(tot)} mlr TL</b>`,ev.clientX,ev.clientY);
    });
    r.addEventListener('mouseleave',hideTip);
  });
})();

/* ---- checks ---- */
(function(){
  const el=document.getElementById('checks');
  el.innerHTML=M.map(m=>{
    const c=D.checks[m], ok=c.detail_vs_source!=null&&Math.abs(c.detail_vs_source)<0.5;
    return `<div class="checkrow"><span>${AL[m]} <span class="small mono">${c.source_total?bn(c.source_total)+' mlr':''}</span></span>
      <span class="pill ${ok?'pass':'sorgula'}">${ok?'PASS':'FARK'}</span></div>`;
  }).join('');
  const gap=D.checks[L].sheet2_gap;
  document.getElementById('kesitnote').textContent=
    (gap? 'Bilinen Sheet2 farki: '+fmt.format(Math.round(gap))+' TL (detay esas alinir). ':'')+
    'Kesitler: nakit ay sonu, overdue sonraki ay sonu, pool gunluk. Oranlar gostergedir.';
})();

/* ---- kategori hbar ---- */
(function(){
  const cats=D.cat_order.filter(k=>(D.categories[L][k]||0)>0)
    .map(k=>({k, v:D.categories[L][k], lbl:D.cat_labels[k]||k}))
    .sort((a,b)=>b.v-a.v);
  const tot=cats.reduce((a,c)=>a+c.v,0);
  document.getElementById('cat-note').textContent=
    AL[L]+' kesiti, hesap kodu bazinda. Toplam '+bn(tot)+' mlr TL.';
  const W=560,rowH=27,P={l:150,r:86,t:4,b:4};
  const H=P.t+P.b+cats.length*rowH;
  const vmax=cats[0].v;
  let g='';
  cats.forEach((c,i)=>{
    const y=P.t+i*rowH, bw=Math.max(2,(W-P.l-P.r)*(c.v/vmax));
    g+=`<text x="${P.l-8}" y="${y+rowH/2+3.5}" text-anchor="end" font-size="11" fill="var(--ink2)">${esc(c.lbl)}</text>`+
       `<rect x="${P.l}" y="${y+5}" width="${bw}" height="${rowH-11}" rx="4" fill="var(--s1)"
          data-t="<b>${esc(c.lbl)}</b> (${c.k})<br>${fmtTL(c.v)} TL &middot; ${pct(c.v/tot)}" class="hv"/>`+
       `<text x="${P.l+bw+7}" y="${y+rowH/2+3.5}" font-size="10.5" fill="var(--ink2)" class="mono">${fmtTL(c.v)}</text>`;
  });
  g+=`<line x1="${P.l}" x2="${P.l}" y1="0" y2="${H}" stroke="var(--axis)" stroke-width="1"/>`;
  document.getElementById('ch-cat').innerHTML=
    `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Kategori kirilimi">${g}</svg>`;
})();

/* ---- Citi pool diverging bars ---- */
(function(){
  const ps=D.pool.participants;
  if(!ps.length){document.getElementById('ch-pool').innerHTML='<p class="small">Pool verisi yok.</p>';return;}
  const ist=(D.pool.grand!=null&&D.pool.arcelik!=null)?D.pool.grand-D.pool.arcelik:null;
  document.getElementById('pool-note').textContent=
    'EUR, gunluk kesit. Grand Total '+f1.format(D.pool.grand/1e6)+' mn; istirakler '+
    (ist!=null? f1.format(ist/1e6)+' mn':'-')+'. HARIC sinifi C746 toplamina katilmaz.';
  const W=560,rowH=19,P={l:196,r:60,t:4,b:4};
  const H=P.t+P.b+ps.length*rowH;
  const vmax=Math.max(...ps.map(p=>Math.abs(p.bal)));
  const x0=P.l+(W-P.l-P.r)/2, half=(W-P.l-P.r)/2;
  let g=`<line x1="${x0}" x2="${x0}" y1="0" y2="${H}" stroke="var(--axis)" stroke-width="1"/>`;
  ps.forEach((p,i)=>{
    const y=P.t+i*rowH, w=Math.max(1.5,half*Math.abs(p.bal)/vmax);
    const pos=p.bal>=0;
    const short=p.ad.length>26?p.ad.slice(0,25)+'…':p.ad;
    g+=`<text x="${P.l-8}" y="${y+rowH/2+3.5}" text-anchor="end" font-size="10" fill="var(--ink2)">${esc(short)}</text>`+
       `<rect x="${pos?x0:x0-w}" y="${y+4}" width="${w}" height="${rowH-8}" rx="3"
          fill="var(${pos?'--pos':'--neg'})"
          data-t="<b>${esc(p.ad)}</b><br>${fmt.format(Math.round(p.bal))} EUR<br>Kod: ${p.kod}${p.le?' (LE '+p.le+')':''}" class="hv"/>`;
    if(i<7||i>=ps.length-3){
      g+=`<text x="${pos?x0+w+5:x0-w-5}" y="${y+rowH/2+3.5}" font-size="9.5"
          text-anchor="${pos?'start':'end'}" fill="var(--muted)" class="mono">${f1.format(p.bal/1e6)}</text>`;}
  });
  document.getElementById('ch-pool').innerHTML=
    `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Citi pool bakiyeleri">${g}</svg>`;
})();

/* ---- nakit vs overdue grouped bars ---- */
(function(){
  const eur=D.eurtry[L];
  const rows=D.entities.filter(e=>e.ovd!=null&&e.ovd>0)
    .map(e=>({kod:e.kod,ad:e.ad,ovd:e.ovd,likit:eur?(e.tot[L]||0)/eur/1000:null,match:e.match}))
    .sort((a,b)=>b.ovd-a.ovd);
  document.getElementById('lg-no').innerHTML=
    `<span><span class="sw" style="background:var(--s1)"></span>Likit (31.05)</span>`+
    `<span><span class="sw" style="background:var(--s3)"></span>Overdue (30.06)</span>`;
  const W=1180,rowH=34,P={l:236,r:96,t:4,b:4};
  const H=P.t+P.b+rows.length*rowH;
  const vmax=Math.max(...rows.map(r=>Math.max(r.ovd,r.likit||0)));
  let g='';
  rows.forEach((r,i)=>{
    const y=P.t+i*rowH;
    const short=r.ad.length>30?r.ad.slice(0,29)+'…':r.ad;
    g+=`<text x="${P.l-8}" y="${y+rowH/2+3.5}" text-anchor="end" font-size="11" fill="var(--ink2)">${r.kod} ${esc(short)}</text>`;
    const bw=v=>Math.max(1.5,(W-P.l-P.r)*(v/vmax));
    if(r.likit!=null){
      g+=`<rect x="${P.l}" y="${y+5}" width="${bw(r.likit)}" height="10" rx="3" fill="var(--s1)"
        data-t="<b>${esc(r.ad)}</b><br>Likit: ${f1.format(r.likit)} bin EUR (31.05)" class="hv"/>`;}
    g+=`<rect x="${P.l}" y="${y+18}" width="${bw(r.ovd)}" height="10" rx="3" fill="var(--s3)"
        data-t="<b>${esc(r.ad)}</b><br>Overdue: ${f1.format(r.ovd)} bin EUR (30.06)" class="hv"/>`;
    const ratio=(r.likit!=null&&r.ovd)? r.likit/r.ovd : null;
    g+=`<text x="${W-P.r+8}" y="${y+rowH/2+3.5}" font-size="10.5" fill="${ratio!=null&&ratio<1?'var(--crit)':'var(--ink2)'}" class="mono">${ratio!=null?f2.format(ratio)+'x':'-'}</text>`;
  });
  g+=`<line x1="${P.l}" x2="${P.l}" y1="0" y2="${H}" stroke="var(--axis)" stroke-width="1"/>`+
     `<text x="${W-P.r+8}" y="-2" font-size="9" fill="var(--muted)">L/O</text>`;
  document.getElementById('ch-no').innerHTML=
    `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Nakit ve overdue karsilastirmasi">${g}</svg>`;
})();

/* ---- istirak matrisi ---- */
let segFilter='*';
function renderTable(){
  const q=(document.getElementById('q').value||'').toLocaleLowerCase('tr');
  const rows=D.entities
    .filter(e=>segFilter==='*'||e.seg===segFilter)
    .filter(e=>!q||(e.kod+' '+e.ad).toLocaleLowerCase('tr').includes(q))
    .sort((a,b)=>(b.tot[L]||0)-(a.tot[L]||0));
  const eur=D.eurtry[L];
  let h='<thead><tr><th class="l">Kod</th><th class="l">Istirak</th>';
  for(const m of M) h+=`<th>${AL[m]}</th>`;
  h+='<th>Vadesiz % ('+AL[L]+')</th><th>Overdue bin EUR</th><th>Pool EUR</th><th class="l">Eslesme</th><th class="l">Bayrak</th></tr></thead><tbody>';
  for(const e of rows){
    const t=e.tot[L]||0, v=e.vad[L]||0, vp=t>0?v/t:null;
    const sorgula=vp!=null&&vp>=D.esik&&t>0;
    h+=`<tr tabindex="0" class="mrow"><td class="l mono">${e.kod}</td><td class="l" title="${esc(e.status||'')}">${esc(e.ad)}</td>`;
    for(const m of M){
      const val=e.tot[m];
      h+=`<td class="mono">${val!=null?fmtTL(val):'<span class="small">-</span>'}</td>`;
    }
    h+= vp==null ? '<td>-</td>' :
      `<td><span class="vtrack"><span class="vbar" style="width:${Math.min(100,vp*100)}%;${sorgula?'background:var(--crit)':''}"></span></span><span class="mono">${pct(vp)}</span></td>`;
    h+=`<td class="mono">${e.ovd!=null?f1.format(e.ovd):'-'}</td>`;
    h+=`<td class="mono">${e.pool!=null?fmt.format(Math.round(e.pool)):'-'}</td>`;
    const mc=(e.match||'').toLocaleLowerCase('tr');
    h+=`<td class="l">${e.match?`<span class="pill ${mc.startsWith('kesin')?'kesin':'olasi'}">${esc(e.match)}</span>`:''}</td>`;
    h+=`<td class="l">${sorgula?'<span class="pill sorgula">SORGULA</span>':''}</td></tr>`;
  }
  h+='</tbody>';
  document.getElementById('mtx').innerHTML=h;
}
document.getElementById('q').addEventListener('input',renderTable);
document.querySelectorAll('.fchip').forEach(c=>{
  c.setAttribute('tabindex','0');
  const act=()=>{document.querySelectorAll('.fchip').forEach(x=>x.classList.remove('on'));
    c.classList.add('on'); segFilter=c.dataset.seg; renderTable();};
  c.addEventListener('click',act);
  c.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();act();}});
});
renderTable();

/* ---- ortak hover ---- */
document.querySelectorAll('svg .hv').forEach(el=>{
  el.addEventListener('mousemove',ev=>showTip(el.dataset.t,ev.clientX,ev.clientY));
  el.addEventListener('mouseleave',hideTip);
});
</script>
"""
