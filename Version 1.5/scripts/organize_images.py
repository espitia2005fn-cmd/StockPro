"""
Copia imagenes de uploads/ a subdirectorios por categoria y actualiza DB.
Usa SQLite local o PostgreSQL via DATABASE_URL.
COPY no MOVE: originales quedan intactos.
"""
import os, sys, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --local flag fuerza SQLite aunque DATABASE_URL esté configurado
use_local = '--local' in sys.argv

from dotenv import load_dotenv
load_dotenv()
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

BASE = os.path.join(os.path.dirname(__file__), '..', 'src')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'stockpro.db')
UPLOADS = os.path.join(BASE, 'Static', 'uploads')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# ---- Detectar DB ----
if not use_local and DATABASE_URL and 'postgres' in DATABASE_URL:
    print("[DB] PostgreSQL (Supabase)")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    pg = True
else:
    print(f"[DB] SQLite local: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    pg = False

c = conn.cursor()

# ---- Categorias ----
if pg:
    c.execute("SELECT id, nombre, imagen FROM categorias ORDER BY id")
else:
    c.execute("SELECT id, nombre, imagen FROM categorias ORDER BY id")
cats = c.fetchall()

# Mapeo nombre_categoria -> nombre_carpeta (normalizado)
# Usamos nombres exactos de la DB como carpetas
cat_folder = {}
for cat in cats:
    name = cat['nombre'].strip()
    safe = name.replace('/', '-').replace('\\', '-')
    cat_folder[cat['id']] = safe
    folder_path = os.path.join(UPLOADS, safe)
    os.makedirs(folder_path, exist_ok=True)
    print(f"  Carpeta: {safe}/")

# ---- Recorrer productos ----
if pg:
    c.execute("SELECT id, codigo, nombre, imagen, categoria FROM repuestos ORDER BY id")
else:
    c.execute("SELECT id, codigo, nombre, imagen, categoria FROM repuestos ORDER BY id")
productos = c.fetchall()

copied = 0
skipped = 0
updated = 0

for p in productos:
    img = p['imagen']
    if not img:
        skipped += 1
        continue

    # Buscar el id de categoria por nombre
    cat_id = None
    for cat in cats:
        if cat['nombre'] == p['categoria']:
            cat_id = cat['id']
            break
    if cat_id is None:
        print(f"  [WARN] {p['codigo']}: categoria '{p['categoria']}' no encontrada")
        skipped += 1
        continue

    folder_name = cat_folder[cat_id]
    src = os.path.join(UPLOADS, img)
    if not os.path.isfile(src):
        print(f"  [WARN] {p['codigo']}: archivo no encontrado: {img}")
        skipped += 1
        continue

    dst = os.path.join(UPLOADS, folder_name, img)
    if os.path.isfile(dst):
        print(f"  [SKIP] {p['codigo']}: ya existe en {folder_name}/{img}")
        copied += 1  # ya existe, contamos como hecho
    else:
        shutil.copy2(src, dst)
        print(f"  [COPY] {p['codigo']}: {img} -> {folder_name}/")
        copied += 1

    new_path = f"{folder_name}/{img}"
    if pg:
        c.execute("UPDATE repuestos SET imagen = %s WHERE id = %s", (new_path, p['id']))
    else:
        c.execute("UPDATE repuestos SET imagen = ? WHERE id = ?", (new_path, p['id']))
    updated += 1

# ---- Tambien procesar imagenes de categorias ----
cat_copied = 0
cat_updated = 0
for cat in cats:
    img = cat['imagen']
    if not img:
        continue
    folder_name = cat_folder[cat['id']]
    src = os.path.join(UPLOADS, img)
    if not os.path.isfile(src):
        print(f"  [WARN] cat '{cat['nombre']}': archivo no encontrado: {img}")
        continue
    dst = os.path.join(UPLOADS, folder_name, img)
    if os.path.isfile(dst):
        print(f"  [SKIP] cat '{cat['nombre']}': ya existe en {folder_name}/{img}")
    else:
        shutil.copy2(src, dst)
        print(f"  [COPY] cat '{cat['nombre']}': {img} -> {folder_name}/")
    cat_copied += 1
    new_path = f"{folder_name}/{img}"
    if pg:
        c.execute("UPDATE categorias SET imagen = %s WHERE id = %s", (new_path, cat['id']))
    else:
        c.execute("UPDATE categorias SET imagen = ? WHERE id = ?", (new_path, cat['id']))
    cat_updated += 1

conn.commit()

# ---- Resumen ----
print(f"\n[OK] Imagenes copiadas (productos): {copied}")
print(f"[OK] DB actualizadas (productos):   {updated}")
print(f"[OK] Imagenes copiadas (categorias): {cat_copied}")
print(f"[OK] DB actualizadas (categorias):   {cat_updated}")
print(f"[OK] Sin cambios:                    {skipped}")

# Verificacion
if pg:
    c.execute("SELECT codigo, imagen FROM repuestos WHERE imagen != '' ORDER BY codigo")
    rows = c.fetchall()
else:
    c.execute("SELECT codigo, imagen FROM repuestos WHERE imagen != '' ORDER BY codigo")
    rows = c.fetchall()
for r in rows[:5]:
    print(f"  PROD {r['codigo']}: {r['imagen']}")
if len(rows) > 5:
    print(f"  ... y {len(rows)-5} mas")
if pg:
    c.execute("SELECT nombre, imagen FROM categorias WHERE imagen != '' ORDER BY nombre")
    cat_rows = c.fetchall()
else:
    c.execute("SELECT nombre, imagen FROM categorias WHERE imagen != '' ORDER BY nombre")
    cat_rows = c.fetchall()
for r in cat_rows:
    print(f"  CAT  {r['nombre']}: {r['imagen']}")

c.close()
conn.close()
print("\n[OK] ORGANIZACION COMPLETADA!")
