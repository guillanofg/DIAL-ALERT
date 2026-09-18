"""Local demonstration interface. Run: python3 src/server.py"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from assistant import answer, GenerationError, QUESTIONS

HTML = (Path(__file__).with_name('index.html')).read_bytes()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, payload, mime='application/json'):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/':
            self.send(200, HTML, 'text/html; charset=utf-8')
        elif self.path == '/questions':
            self.send(200, QUESTIONS)
        else:
            self.send(404, {'error': 'Not found'})

    def do_POST(self):
        if self.path != '/ask':
            return self.send(404, {'error': 'Not found'})
        if self.headers.get('Origin') not in (None, 'http://127.0.0.1:8099'):
            return self.send(403, {'error': 'Origin rejected'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'JSON required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 256:
                return self.send(413, {'error': 'Invalid request size'})
            obj = json.loads(self.rfile.read(length))
            if not isinstance(obj, dict) or set(obj) != {'question_id', 'mode'}:
                raise ValueError('Only question_id and mode are accepted. No patient information.')
            if not isinstance(obj['question_id'], str) or not isinstance(obj['mode'], str):
                raise ValueError('Question and mode must be strings.')
            self.send(200, answer(obj['question_id'], obj['mode']))
        except (ValueError, TypeError) as exc:
            self.send(400, {'error': str(exc)})
        except GenerationError as exc:
            self.send(503, {'error': str(exc), 'status': 'no_generated_answer'})
        except Exception:
            self.send(503, {'error': 'Unable to complete request', 'status': 'no_generated_answer'})

if __name__ == '__main__':
    print('Open http://127.0.0.1:8099 ; stop with Control+C', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8099), Handler).serve_forever()
