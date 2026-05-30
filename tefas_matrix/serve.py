"""Dashboard'u yerelde (localhost) servis eden hafif sunucu.

Üretilen HTML dashboard'u tarayıcıda açmanın en kolay yolu: dosyayı çift
tıklamak yerine küçük bir yerel HTTP sunucusu başlatıp tarayıcıyı otomatik
açar. Yalnızca Python standart kütüphanesini kullanır (ek bağımlılık yok)
ve sadece 127.0.0.1'e bağlanır (dışarıya açık değildir).
"""

from __future__ import annotations

import os
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def serve_dashboard(html_path: str, port: int = 8000,
                    open_browser: bool = True) -> None:
    """`html_path` dosyasını 127.0.0.1:port üzerinden servis eder.

    Sunucu Ctrl+C'ye kadar çalışır. Port meşgulse sıradaki boş portu dener.
    """
    directory = os.path.dirname(os.path.abspath(html_path)) or "."
    fname = os.path.basename(html_path)

    handler = partial(_QuietHandler, directory=directory)
    httpd, bound_port = _bind(handler, port)
    url = f"http://127.0.0.1:{bound_port}/{fname}"

    print(f"▶ Dashboard yerelde yayında: {url}")
    print("  (durdurmak için Ctrl+C)")
    if open_browser:
        threading.Timer(0.6, lambda: _try_open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n■ Sunucu durduruldu.")
    finally:
        httpd.server_close()


def _bind(handler, port: int, tries: int = 20):
    """İlk boş portu bulup ThreadingHTTPServer döndürür."""
    last_err = None
    for p in range(port, port + tries):
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), handler), p
        except OSError as e:  # port meşgul
            last_err = e
            continue
    raise RuntimeError(f"{port}-{port + tries} aralığında boş port yok") from last_err


def _try_open(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        pass  # başsız ortam; kullanıcı URL'yi elle açar


class _QuietHandler(SimpleHTTPRequestHandler):
    """İstek loglarını bastıran statik dosya sunucusu."""

    def log_message(self, *args):  # noqa: D401
        pass
