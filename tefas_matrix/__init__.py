"""TEFAS PPF Mevduat Eşleniği Matrix üreticisi.

Para piyasası fonlarının mevduat eşleniği bazlı ağırlıklı performans
sıralamasını oluşturur ve formüllü, cross-check'li iki sheet'li Excel
çıktısı üretir.
"""

from .compute import FundRecord, build_matrix, mevduat_esligi  # noqa: F401
from .sources import from_live, from_workbook, filter_ppf  # noqa: F401
from .workbook import write_workbook  # noqa: F401

__version__ = "1.0.0"
