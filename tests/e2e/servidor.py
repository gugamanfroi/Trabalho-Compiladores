"""Ambiente local para testes de interface sem Docker.

Reproduz o desenho do docker-compose: um servidor estático (papel do Nginx)
que encaminha /api/* e /health ao backend Flask real, na mesma origem.
"""
import logging
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from werkzeug.serving import make_server

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND = os.path.join(RAIZ, "frontend")
BACKEND = os.path.join(RAIZ, "backend")
sys.path.insert(0, BACKEND)

from app import create_app  # noqa: E402

logging.getLogger("werkzeug").setLevel(logging.ERROR)


class _Proxy(SimpleHTTPRequestHandler):
    backend_url = ""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONTEND, **kw)

    def log_message(self, *args):  # silencia o log
        pass

    def _encaminhar(self):
        corpo = None
        tam = int(self.headers.get("Content-Length") or 0)
        if tam:
            corpo = self.rfile.read(tam)
        req = urllib.request.Request(
            self.backend_url + self.path, data=corpo, method=self.command,
            headers={"Content-Type": self.headers.get("Content-Type", "")},
        )
        try:
            r = urllib.request.urlopen(req, timeout=10)
            status, dados, tipo = r.status, r.read(), r.headers.get("Content-Type")
        except urllib.error.HTTPError as e:
            status, dados, tipo = e.code, e.read(), e.headers.get("Content-Type")
        except Exception:
            status, dados, tipo = 502, b"<html>Bad Gateway</html>", "text/html"
        self.send_response(status)
        self.send_header("Content-Type", tipo or "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        try:
            self.wfile.write(dados)
        except (BrokenPipeError, ConnectionResetError):
            pass  # o navegador fechou a página antes da resposta

    def _rota_api(self):
        return self.path.startswith("/api/") or self.path == "/health"

    def do_GET(self):
        self._encaminhar() if self._rota_api() else super().do_GET()

    def do_POST(self):
        self._encaminhar()


class Ambiente:
    """Sobe backend + frontend em portas livres; use como context manager."""

    def __init__(self, backend_no_ar=True):
        self.backend_no_ar = backend_no_ar

    def __enter__(self):
        self._srv_back = make_server("127.0.0.1", 0, create_app(), threaded=True)
        back_url = "http://127.0.0.1:%d" % self._srv_back.server_port
        if self.backend_no_ar:
            threading.Thread(target=self._srv_back.serve_forever, daemon=True).start()
        handler = type("H", (_Proxy,), {"backend_url": back_url})
        self._srv_front = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self._srv_front.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self._srv_front.server_port
        return self

    def __exit__(self, *exc):
        self._srv_front.shutdown()
        self._srv_front.server_close()
        if self.backend_no_ar:
            self._srv_back.shutdown()
        self._srv_back.server_close()


if __name__ == "__main__":
    with Ambiente() as amb:
        print("Frontend em", amb.url)
        threading.Event().wait()
