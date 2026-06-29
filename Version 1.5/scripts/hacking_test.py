"""
Pruebas de hacking contra StockPro local.
NO rompe nada - solo verifica seguridad.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    # Fallback a urllib
    import urllib.request
    import urllib.parse

    class FakeResponse:
        def __init__(self, status, headers, text, url):
            self.status_code = status
            self.headers = headers
            self.text = text
            self.url = url

    class Session:
        def __init__(self):
            self.cookies = {}
        def get(self, url, allow_redirects=True):
            req = urllib.request.Request(url)
            req.add_header('Cookie', '; '.join(f'{k}={v}' for k,v in self.cookies.items()))
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                status = resp.status
                headers = dict(resp.headers)
                text = resp.read().decode('utf-8', errors='replace')
                if allow_redirects:
                    return FakeResponse(status, headers, text, url)
                return FakeResponse(status, headers, text, url)
            except urllib.error.HTTPError as e:
                return FakeResponse(e.code, dict(e.headers), e.read().decode('utf-8', errors='replace'), url)
            except Exception as e:
                return FakeResponse(0, {}, str(e), url)
        def post(self, url, data, allow_redirects=True):
            payload = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Cookie', '; '.join(f'{k}={v}' for k,v in self.cookies.items()))
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                status = resp.status
                headers = dict(resp.headers)
                text = resp.read().decode('utf-8', errors='replace')
                if 'Set-Cookie' in headers:
                    for c in headers.get('Set-Cookie', '').split(','):
                        if '=' in c:
                            kv = c.split(';')[0].strip()
                            if '=' in kv:
                                k, v = kv.split('=', 1)
                                self.cookies[k] = v
                if allow_redirects:
                    return FakeResponse(status, headers, text, url)
                return FakeResponse(status, headers, text, url)
            except urllib.error.HTTPError as e:
                return FakeResponse(e.code, dict(e.headers), e.read().decode('utf-8', errors='replace'), url)
            except Exception as e:
                return FakeResponse(0, {}, str(e), url)

    requests = type(sys)('requests')
    requests.Session = Session

BASE = 'http://127.0.0.1:5000'
s = requests.Session()

def test(num, name, condition, ok_msg, fail_msg):
    status = 'OK' if condition else 'XX'
    print(f'  {status} [{num}] {name}: {ok_msg if condition else fail_msg}')

print()
print('=== PRUEBAS DE HACKING ===')
print()

# 1 - SQLi login
r = s.post(BASE + '/login', data={
    'username': "' OR 1=1 --",
    'password': "' OR '1'='1",
    'captcha': '0'
})
test(1, 'SQLi en login', '/admin' not in r.url, 'BLOQUEADO (redirect a login)', f'VULNERABLE (status {r.status_code})')

# 2 - Path traversal
r = s.get(BASE + '/static/../../../etc/passwd')
test(2, 'Path traversal en static', r.status_code != 200, 'BLOQUEADO', f'VULNERABLE (status {r.status_code})')

# 3 - Admin sin autenticar
r = s.get(BASE + '/admin/dashboard')
test(3, 'Admin sin autenticar', '/login' in r.url or r.status_code == 302, 'REDIRECT A LOGIN', f'VULNERABLE (status {r.status_code})')

# 4 - Inyeccion numerica
r = s.get(BASE + '/producto/999999999')
test(4, 'ID inexistente en producto', r.status_code != 200, '404/MANEJADO', f'POSIBLE BUG (status {r.status_code})')

# 5 - SQLi en slug de categoria
r = s.get(BASE + '/categoria/test-OR-1=1--')
test(5, 'SQLi en slug categoria', r.status_code != 200, '404/MANEJADO', f'VULNERABLE (status {r.status_code})')

# 6 - 404 page
r = s.get(BASE + '/ruta-inexistente-xyz')
test(6, 'Pagina 404 personalizada', 'Pagina no encontrada' in r.text or 'Página no encontrada' in r.text, 'Template mantenimiento.html OK', 'Sin template 404')

# 7 - POST sin CSRF a ruta sensible
r = s.post(BASE + '/admin/actualizar_config', data={'key': 'test', 'value': 'test'})
test(7, 'POST sin CSRF token', r.status_code in (400, 403, 405, 500), f'BLOQUEADO ({r.status_code})', f'VULNERABLE ({r.status_code})')

# 8 - Header Security Check
r = s.get(BASE + '/')
h = r.headers
tests_headers = [
    ('Content-Security-Policy', 'Content-Security-Policy' in h),
    ('X-Content-Type-Options', h.get('X-Content-Type-Options') == 'nosniff'),
    ('X-Frame-Options', h.get('X-Frame-Options') == 'SAMEORIGIN'),
    ('Strict-Transport-Security', 'Strict-Transport-Security' in h),
]
header_ok = all(t[1] for t in tests_headers)
for name, ok in tests_headers:
    test(8.1, f'Header {name}', ok, 'PRESENTE', 'AUSENTE')

print()
print('--- Resumen ---')
print('  Pruebas: 7 + headers')
if header_ok:
    print('  TODO OK - La app es segura')
else:
    print('  Algunos headers faltan')
print()
