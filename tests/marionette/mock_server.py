"""
Minimal HTTP server that mimics the addy.io API for Marionette tests.
Serves fixture JSON from tests/fixtures/ and records API requests.
"""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


class _Handler(BaseHTTPRequestHandler):
    recorded: list = []

    def do_GET(self):
        _Handler.recorded.append(("GET", self.path, {}))
        path = self.path.split("?")[0]
        if path == "/api/v1/domain-options":
            self._respond(200, _load("domain-options.json"))
        elif path == "/api/v1/aliases":
            aliases = _load("aliases.json")
            self._respond(
                200,
                {"data": aliases, "meta": {"current_page": 1, "last_page": 1}},
            )
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        body = self._read_body()
        _Handler.recorded.append(("POST", self.path, body))
        alias = {
            "id": "mock-created",
            "local_part": body.get("local_part", "random123"),
            "domain": body.get("domain", "anonaddy.me"),
            "email": f"{body.get('local_part', 'random123')}@{body.get('domain', 'anonaddy.me')}",
            "active": True,
            "description": body.get("description", ""),
        }
        self._respond(201, {"data": alias})

    def do_PATCH(self):
        body = self._read_body()
        _Handler.recorded.append(("PATCH", self.path, body))
        self._respond(200, {})

    def do_DELETE(self):
        _Handler.recorded.append(("DELETE", self.path, {}))
        self.send_response(204)
        self.end_headers()

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _respond(self, status: int, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # silence access logs during tests


def start() -> tuple[HTTPServer, int]:
    """Start the mock server on a random port. Returns (server, port)."""
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port
