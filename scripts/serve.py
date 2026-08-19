#!/usr/bin/env python3
"""Serve player/ with HTTP range support.

`python3 -m http.server` does not implement Range. Without it a browser cannot
seek inside a media file: setting audio.currentTime silently fails and the
element snaps back to 0. In the player that dragged the whole clock with it, so
clicking anywhere on the timeline restarted the song.

    ./scripts/serve.py [port]
"""
import os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'player')


class RangeHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def send_head(self):
        rng = self.headers.get('Range')
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404)
            return None
        size = os.fstat(f.fileno()).st_size
        m = re.match(r'bytes=(\d*)-(\d*)$', rng.strip())
        if not m:
            f.close()
            self.send_error(400, 'bad range')
            return None
        first, last = m.group(1), m.group(2)
        if first == '':                       # suffix form: last N bytes
            start, end = max(0, size - int(last)), size - 1
        else:
            start = int(first)
            end = int(last) if last else size - 1
        end = min(end, size - 1)
        if start > end:
            f.close()
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return None
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        return _Slice(f, end - start + 1)

    def end_headers(self):
        if 'Accept-Ranges' not in self._headers_buffer_names():
            self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def _headers_buffer_names(self):
        return b''.join(getattr(self, '_headers_buffer', [])).decode('latin-1', 'replace')

    def log_message(self, *a):
        pass


class _Slice:
    """A file that stops after n bytes, so copyfile sends only the range."""
    def __init__(self, f, n): self.f, self.n = f, n
    def read(self, k=-1):
        if self.n <= 0: return b''
        if k is None or k < 0: k = self.n
        d = self.f.read(min(k, self.n)); self.n -= len(d); return d
    def close(self): self.f.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    print(f"serving {ROOT} on http://127.0.0.1:{port}/  (range requests supported)")
    ThreadingHTTPServer(('127.0.0.1', port), RangeHandler).serve_forever()
