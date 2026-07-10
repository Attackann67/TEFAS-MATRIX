"""beko_cash - Beko Corporate Treasury nakit-overdue kayit ve dashboard motoru.

Katmanlar:
  schema    - kategori kodlari, gruplama, segment, renk paleti (tek dogruluk noktasi)
  snapshot  - aylik JSON kaydi oku/yaz/dogrula/iskele (kayit)
  compute   - turetilmis metrikler ve uzun-format satirlar (analiz)
  dashboard - cok sayfali, canli SUMIFS'li Excel uretici (dashboard)

CLI: python -m beko_cash <build|validate|new|summary>
"""

from . import compute, dashboard, extract, schema, snapshot  # noqa: F401

__all__ = ["schema", "snapshot", "compute", "dashboard", "extract"]
