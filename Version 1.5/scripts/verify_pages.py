"""
Verificacion de paginas clave del sistema.
Sin f-strings complejas para evitar problemas de shell.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import urllib.request, urllib.parse

BASE = 'http://127.0.0.1:5000'

def get(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return r.status, r.read().decode('utf-8', errors='replace'), r.url
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace'), url
    except Exception as e:
        return 0, str(e), url

def post(url, data):
    payload = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=payload, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, r.read().decode('utf-8', errors='replace'), r.url
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace'), url
    except Exception as e:
        return 0, str(e), url

print()
print('=== VERIFICACION DE PAGINAS ===')
print()

paginas = {
    '/': 'Inicio',
    '/login': 'Login',
    '/admin/': 'Admin Login',
    '/categoria/Motor': 'Categoria Motor',
    '/categoria/Lubricantes': 'Categoria Lubricantes',
    '/producto/1': 'Producto ID=1',
}

for path, nombre in paginas.items():
    status, text, url = get(BASE + path)
    if status == 200:
        ok = True
    elif status in (301, 302) and '/login' in url:
        ok = True
    else:
        ok = False
    marca = 'OK' if ok else 'XX'
    print('  ' + marca + ' [' + str(status) + '] ' + nombre.ljust(25) + ' ' + path)

# API
print()
print('--- API ---')
status, text, _ = get(BASE + '/api/inventario')
try:
    data = json.loads(text)
    print('  OK [200] Productos en API: ' + str(len(data)))
except:
    print('  XX [' + str(status) + '] API inventario fallo')

status, text, _ = get(BASE + '/api/categorias')
try:
    data = json.loads(text)
    print('  OK [200] Categorias en API: ' + str(len(data)))
except:
    print('  XX [' + str(status) + '] API categorias fallo')

# SQLi a login
print()
print('--- SQLi Test ---')
status, _, url = post(BASE + '/login', {
    'username': "' OR 1=1 --",
    'password': "' OR '1'='1",
    'captcha': '0'
})
if '/admin' in url:
    print('  XX VULNERABLE - SQLi bypasso el login!')
else:
    print('  OK BLOQUEADO - SQLi no funciono')

# Admin sin auth
print()
print('--- Admin sin autenticar ---')
for path in ['/admin/', '/admin/dashboard', '/admin/productos']:
    status, _, url = get(BASE + path)
    if 'login' in url.lower() or status in (301, 302, 401, 403):
        print('  OK Redirige a login: ' + path)
    else:
        print('  XX [' + str(status) + '] Posible acceso: ' + path)

# 404
print()
print('--- 404 ---')
status, text, _ = get(BASE + '/ruta-inexistente-xyz')
if 'Pagina no encontrada' in text or 'Página no encontrada' in text:
    print('  OK [' + str(status) + '] Template 404 personalizada')
else:
    print('  XX [' + str(status) + '] Sin template 404')

print()
print('=== VERIFICACION COMPLETADA ===')
