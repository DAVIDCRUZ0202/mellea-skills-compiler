import http.client
import http.server
import json
import ssl


class ContextMgmtStrippingProxy(http.server.BaseHTTPRequestHandler):
    """Local proxy that strips context_management from Anthropic API requests.

    The IBM LiteLLM proxy rejects context_management as an unknown parameter.
    Claude Code sends it automatically. This proxy intercepts requests from the
    claude subprocess, strips the field, and forwards to the real upstream.
    """

    def log_message(self, fmt, *args):
        pass

    def handle_error(self, request, client_address):
        pass  # suppress BrokenPipeError tracebacks when subprocess closes mid-stream

    def _make_conn(self, timeout):
        host = self.server.upstream_host
        if self.server.upstream_scheme == "https":
            return http.client.HTTPSConnection(
                host, context=ssl.create_default_context(), timeout=timeout
            )
        return http.client.HTTPConnection(host, timeout=timeout)

    def _forward_post(self, body):
        path = self.server.upstream_path_prefix + self.path
        h = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in {"host", "content-length"}
        }
        h["Content-Length"] = str(len(body))
        conn = self._make_conn(300)
        conn.request("POST", path, body=body, headers=h)
        r = conn.getresponse()
        self.send_response(r.status, r.reason)
        for hk, hv in r.getheaders():
            if hk.lower() not in {"transfer-encoding", "connection"}:
                self.send_header(hk, hv)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            while True:
                chunk = r.read(4096)
                if not chunk:
                    break
                self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except BrokenPipeError:
            pass  # subprocess closed the connection (e.g. on timeout/kill)
        finally:
            conn.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            payload.pop("context_management", None)
            body = json.dumps(payload).encode()
        except Exception:
            pass
        self._forward_post(body)

    def do_GET(self):
        path = self.server.upstream_path_prefix + self.path
        h = {k: v for k, v in self.headers.items() if k.lower() != "host"}
        conn = self._make_conn(60)
        conn.request("GET", path, headers=h)
        r = conn.getresponse()
        body = r.read()
        self.send_response(r.status, r.reason)
        for hk, hv in r.getheaders():
            if hk.lower() not in {"transfer-encoding", "connection", "content-length"}:
                self.send_header(hk, hv)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        conn.close()
