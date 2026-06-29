"""
Probar login en Railway con CSRF token
"""
import urllib.request, urllib.parse, sys, re
import http.cookiejar
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://stockpro-production-e2ee.up.railway.app'
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookie_jar)
)

# 1. GET login page para CSRF + captcha
r = opener.open(BASE + '/login', timeout=10)
html = r.read().decode('utf-8', errors='replace')

csrf = ''
captcha = '0'
m = re.search(r'csrf-token" content="([^"]+)"', html)
if m:
    csrf = m.group(1)
    print('CSRF token: OK (' + csrf[:10] + '...)')

m = re.search(r'Cuanto es (\d+)\s*[-+]\s*(\d+)', html)
if m:
    a, b = int(m.group(1)), int(m.group(2))
    captcha = str(a - b)
    print('Captcha: ' + str(a) + ' - ' + str(b) + ' = ' + captcha)

# 2. Intentar login con credenciales erroneas
print()
print('--- Test 1: credenciales incorrectas ---')
data = urllib.parse.urlencode({
    'username': 'admin',
    'password': 'wrongpass123',
    'captcha': captcha,
    'csrf_token': csrf
}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
try:
    r = opener.open(req, timeout=10)
    print('Status: ' + str(r.status) + ' URL: ' + r.url)
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')
    print('Error: ' + str(e.code))
    if 'bloqueada' in body.lower() or 'bloqueado' in body.lower():
        print('-> CUENTA BLOQUEADA')
    elif 'incorrecto' in body.lower() or 'error' in body.lower():
        print('-> Rechazado (credenciales incorrectas) - OK')
    elif 'csrf' in body.lower():
        print('-> CSRF error')
    else:
        print('-> Body: ' + body[:200])

# 3. Probar la pagina principal
print()
print('--- Test 2: pagina principal ---')
r = opener.open(BASE + '/', timeout=10)
html = r.read().decode('utf-8', errors='replace')
if 'StockPro' in html and 'Categor' in html:
    print('OK - Pagina principal carga con categorias')
else:
    print('XX - Pagina principal no carga correctamente')

print()
print('=== COMPLETADO ===')
