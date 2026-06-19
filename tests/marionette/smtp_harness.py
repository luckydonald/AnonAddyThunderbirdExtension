"""
Minimal SMTP capture server for Marionette tests.

Accepts TCP connections, speaks enough SMTP to satisfy Thunderbird
(EHLO/MAIL FROM/RCPT TO/DATA/QUIT), and records each delivered message.
"""

import email.parser
import queue
import socket
import threading


class SMTPCaptureServer:
    def __init__(self):
        self._sock = None
        self._accept_thread = None
        self._stop = threading.Event()
        self.messages = []
        self._queue = queue.Queue()
        self.port = None

    def start(self) -> int:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(5)
        self._sock.settimeout(1.0)
        self.port = self._sock.getsockname()[1]
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        return self.port

    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle, args=(conn,), daemon=True)
            t.start()

    def _handle(self, conn):
        conn.settimeout(30.0)
        buf = b""
        mail_from = ""
        rcpt_to = []

        try:
            conn.sendall(b"220 localhost SMTP ready\r\n")

            while True:
                # Read a line from the buffer
                while b"\r\n" not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    buf += chunk
                idx = buf.index(b"\r\n")
                raw_line = buf[:idx]
                buf = buf[idx + 2:]
                line = raw_line.decode("utf-8", errors="replace").strip()
                upper = line.upper()

                if upper.startswith("EHLO") or upper.startswith("HELO"):
                    # Two-line EHLO response — must NOT collapse into one sendall with
                    # a single trailing \r\n or Thunderbird's SMTP client will reject it.
                    conn.sendall(b"250-localhost\r\n250 SIZE 10485760\r\n")

                elif upper.startswith("MAIL FROM"):
                    mail_from = line[len("MAIL FROM:"):].strip().strip("<>")
                    conn.sendall(b"250 OK\r\n")

                elif upper.startswith("RCPT TO"):
                    addr = line[len("RCPT TO:"):].strip().strip("<>")
                    rcpt_to.append(addr)
                    conn.sendall(b"250 OK\r\n")

                elif upper == "DATA":
                    conn.sendall(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                    # Accumulate bytes until the end-of-DATA marker
                    while b"\r\n.\r\n" not in buf:
                        chunk = conn.recv(4096)
                        if not chunk:
                            return
                        buf += chunk
                    sep = buf.index(b"\r\n.\r\n")
                    raw_data = buf[:sep]
                    buf = buf[sep + 5:]  # advance past \r\n.\r\n
                    # Undo dot-stuffing (lines beginning with ".." → ".")
                    lines = raw_data.split(b"\r\n")
                    undotted = [ln[1:] if ln.startswith(b"..") else ln for ln in lines]
                    raw_data = b"\r\n".join(undotted)

                    msg = email.parser.BytesParser().parsebytes(raw_data)
                    record = {
                        "mail_from": mail_from,
                        "rcpt_to": list(rcpt_to),
                        "to_header": msg.get("To", "") or "",
                        "cc_header": msg.get("Cc", "") or "",
                        "subject": msg.get("Subject", "") or "",
                        "raw": raw_data.decode("utf-8", errors="replace"),
                    }
                    self.messages.append(record)
                    self._queue.put(record)
                    conn.sendall(b"250 OK\r\n")
                    mail_from = ""
                    rcpt_to = []

                elif upper == "QUIT":
                    conn.sendall(b"221 Bye\r\n")
                    return

                elif upper == "RSET":
                    mail_from = ""
                    rcpt_to = []
                    conn.sendall(b"250 OK\r\n")

                elif upper == "NOOP":
                    conn.sendall(b"250 OK\r\n")

                else:
                    conn.sendall(b"500 Unrecognized command\r\n")

        except Exception:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def wait_for_message(self, timeout: float = 20.0):
        """Block until a message arrives or timeout. Returns the message dict or None."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear(self):
        """Discard all captured messages and reset the queue."""
        self.messages.clear()
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def shutdown(self):
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
