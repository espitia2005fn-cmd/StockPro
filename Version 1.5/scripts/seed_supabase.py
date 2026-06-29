"""
Seed para PostgreSQL (Supabase). Mismos datos que seed_reales.py.
Usa DATABASE_URL del entorno o del .env
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if not DATABASE_URL or 'postgres' not in DATABASE_URL:
    print("[ERROR] DATABASE_URL no contiene PostgreSQL. Usa: postgresql://user:pass@host:6543/db?pgbouncer=true")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
c = conn.cursor()

# Crear tablas
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src import database_supabase as db_sup
db_sup.crear_tablas()
print("[OK] Tablas creadas/verificadas")

# Imagenes
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'Static', 'uploads')
def get_all_images():
    images = []
    for root, dirs, files in os.walk(UPLOADS_DIR):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                rel = os.path.relpath(os.path.join(root, f), UPLOADS_DIR)
                images.append(rel)
    return images

all_images = get_all_images()
print(f"\n[+] Imagenes disponibles: {len(all_images)}")

def normalize(s):
    return (s.lower()
            .replace('\u00f1', 'n').replace('\u00d1', 'n')
            .replace('\u00e1', 'a').replace('\u00c1', 'a')
            .replace('\u00e9', 'e').replace('\u00c9', 'e')
            .replace('\u00ed', 'i').replace('\u00cd', 'i')
            .replace('\u00f3', 'o').replace('\u00d3', 'o')
            .replace('\u00fa', 'u').replace('\u00da', 'u'))

def find_img(keywords):
    for f in all_images:
        fl = normalize(f)
        if all(normalize(k) in fl for k in keywords):
            return f
    return ''

cat_name_map = {1:'Motor',2:'Frenos',3:'Suspension',4:'Electrico',5:'Transmision',
                6:'Lubricantes',7:'Neumaticos',8:'Carroceria',9:'Herramientas',10:'Escape'}

# Categorias
categoria_images = {
    1: 'Filtro_Aceite_Duke.jpg',
    2: 'Pastillas_de_Freno_Pulsar_200_Ns_Bajaj.jpg',
    3: 'Amortiguador_trasero_ns200.jpg',
    4: 'Bateria_Magna_YB5L-B__12V-5Ah_.jpg',
    5: 'Kit_arrastre_ns.jpg',
    6: 'Motul_5100_15W50_4T_.jpg',
    7: 'Llanta_Michelin_130-70-17_PILOT_STREET_2.jpg',
    8: 'Manillar_universal.jpg',
    9: '',
    10: '',
}
for cat_id, img in categoria_images.items():
    c.execute("UPDATE categorias SET imagen = %s WHERE id = %s", (img, cat_id))
    print(f"  Categoria ID={cat_id}: imagen -> {img or '(sin imagen)'}")

# Limpiar datos anteriores
for table in ['venta_detalle', 'ventas', 'pedido_detalle', 'pedidos', 'pagos',
              'movimientos', 'alertas', 'actividad', 'repuestos']:
    c.execute(f"DELETE FROM {table}")
    print(f"  {table}: limpiado")

# Productos
lub = [
    ('LUB-001', 'Aceite de Motor Liqui Moly 10W40 Semisintetico', 45, 45000, 32000, 5, 'A-01', 'Liqui Moly', ['liqui', 'moly', '10w40']),
    ('LUB-002', 'Aceite de Motor Liqui Moly 10W40 Sintetico Street Race', 30, 68000, 48000, 5, 'A-02', 'Liqui Moly', ['liqui', 'moly', 'street']),
    ('LUB-003', 'Aceite de Motor Mobil 10W30 Semisintetico Super Mx', 50, 38000, 26000, 5, 'A-03', 'Mobil', ['mobil', '10w30', 'super']),
    ('LUB-004', 'Aceite de Motor Mobil 10W30 Semisintetico Ultimate', 25, 42000, 30000, 5, 'A-04', 'Mobil', ['mobil', '10w30', 'ultimate']),
    ('LUB-005', 'Aceite de Motor Motul 10W40 Semisintetico Scooter', 35, 35000, 24000, 5, 'A-05', 'Motul', ['motul', '10w40', 'scooter']),
    ('LUB-006', 'ACEITE MOTUL 5100 15W50 4T LITRO', 60, 55000, 38000, 8, 'A-06', 'Motul', ['motul', '5100', '15w50']),
    ('LUB-007', 'ACEITE-BAJAJ-20W50-4T-1.2-LITROS', 40, 28000, 19000, 5, 'A-07', 'Bajaj', ['bajaj', '20w50']),
    ('LUB-008', 'Aceite Motul 20W50 Semisintetico 5000', 20, 32000, 22000, 5, 'A-08', 'Motul', ['motul', '20w50', '5000']),
    ('LUB-009', 'ACEITE MOTUL 7100 20W50 4T LITRO', 25, 75000, 52000, 5, 'A-09', 'Motul', ['7100', '20w50']),
    ('LUB-010', 'EMOB 20W50 M SUPER 4T', 30, 25000, 17000, 5, 'A-10', 'EMOB', ['emob', 'super4t']),
    ('LUB-011', 'EMOB 20W50 M ULTRA', 20, 30000, 21000, 5, 'A-11', 'EMOB', ['emob', 'ultra']),
    ('LUB-012', 'Motul 7100 4T 10W40 4 Litros', 15, 180000, 130000, 3, 'A-12', 'Motul', ['7100', '10w40', '4l']),
    ('LUB-013', 'Liqui Moly 10W40', 10, 120000, 85000, 2, 'A-13', 'Liqui Moly', ['liqui', 'moly', '10w40']),
    ('LUB-014', 'Mobil 10W30 Semisintetico', 12, 100000, 70000, 2, 'A-14', 'Mobil', ['mobil', '10w30']),
]

filtros_aceite = [
    ('FIL-001', 'Filtro Aceite Pulsar 135/NS160', 30, 12000, 7000, 5, 'B-01', 'Bajaj', ['filtro', 'aceite', 'pulsar135']),
    ('FIL-002', 'Filtro de Aceite PULSAR 200 NS / Dominar 400', 35, 15000, 9000, 5, 'B-02', 'Bajaj', ['filtro', 'aceite', 'pulsar', '200']),
    ('FIL-003', 'Filtro Aceite KN-155 Duke 200/390/690', 20, 25000, 16000, 3, 'B-03', 'KN', ['kn-155']),
    ('FIL-004', 'Filtro Aceite KN-401 Kawasaki EX-250R Ninja', 15, 28000, 18000, 3, 'B-04', 'KN', ['kn-401']),
    ('FIL-005', 'Filtro Aceite Bajaj Original (Universal)', 40, 8000, 4500, 5, 'B-05', 'Bajaj', ['bajaj', 'original', 'filtro', 'aceite']),
    ('FIL-006', 'Filtro Aceite Duke (Original)', 25, 18000, 11000, 5, 'B-06', 'KTM', ['filtro', 'aceite', 'duke']),
    ('FIL-007', 'Filtro Aceite Kawasaki (Original)', 18, 22000, 14000, 3, 'B-07', 'Kawasaki', ['filtro', 'aceite', 'kawasaki']),
]

filtros_aire = [
    ('FIA-001', 'Filtro de Aire PULSAR 200 NS FI', 28, 18000, 10000, 5, 'C-01', 'Bajaj', ['filtro', 'aire', 'pulsar', '200']),
    ('FIA-002', 'Filtro de Aire RTR 200 Fi TVS Original', 20, 22000, 13000, 3, 'C-02', 'TVS', ['filtro', 'aire', 'rtr', '200']),
    ('FIA-003', 'Filtro Aire Pulsar NS (Carburador)', 15, 15000, 8500, 5, 'C-03', 'Bajaj', ['filtro', 'aire', 'pulsar', 'ns']),
    ('FIA-004', 'Filtro Aire RTR 200 (Carburador)', 12, 16000, 9000, 3, 'C-04', 'TVS', ['filtro', 'aire', 'rtr']),
]

baterias = [
    ('BAT-001', 'Bateria Magna YB5L-B (12V-5Ah)', 18, 85000, 55000, 3, 'D-01', 'Magna', ['magna', 'yb5l']),
    ('BAT-002', 'Bateria Magna YTX7L-BS (12V-6Ah)', 15, 95000, 62000, 3, 'D-02', 'Magna', ['ytx7l']),
    ('BAT-003', 'Bateria YB10L-B2', 10, 110000, 72000, 2, 'D-03', 'Yuasa', ['yb10l']),
    ('BAT-004', 'Bateria YT12B-BS (12V-10Ah)', 8, 130000, 85000, 2, 'D-04', 'Yuasa', ['yt12b']),
    ('BAT-005', 'Bateria YTX20L-BS (12V-18Ah)', 6, 160000, 105000, 2, 'D-05', 'Yuasa', ['ytx20l']),
    ('BAT-006', 'Bateria Yuasa Ducati/FZ6/ZX-10R YT12-B4', 5, 180000, 120000, 1, 'D-06', 'Yuasa', ['yuasa', 'ducati']),
    ('BAT-007', 'Bateria Moto Magna GEL YB5LB', 12, 95000, 62000, 3, 'D-07', 'Magna', ['gel', 'yb5lb']),
]

bujias = [
    ('BUJ-001', 'Bujia Central PULSAR 200 NS BS4 Bajaj Original', 30, 15000, 8000, 5, 'E-01', 'Bajaj', ['bujia', 'pulsar', '200', 'central']),
    ('BUJ-002', 'Bujia CR8EIX Generico Japon Iridium', 40, 12000, 6500, 5, 'E-02', 'NGK', ['cr8eix']),
    ('BUJ-003', 'Bujia Dr 650 / XF Freewind 650 Suzuki', 15, 18000, 10000, 3, 'E-03', 'NGK', ['bujia', '650']),
    ('BUJ-004', 'Bujia Platino 100 / Boxer 100 / Pulsar 135 Bajaj Original', 35, 10000, 5500, 5, 'E-04', 'Bajaj', ['platino', '100']),
    ('BUJ-005', 'Bujia RG8YC Gixxer 155 Suzuki Original', 20, 14000, 7500, 3, 'E-05', 'Suzuki', ['rg8yc']),
    ('BUJ-006', 'Bujia Discover 135 / Pulsar 180 Platino 125 Original', 25, 11000, 6000, 5, 'E-06', 'Bajaj', ['discover', '135']),
]

llantas = [
    ('LLN-001', 'Llanta Dunlop 130/70-17 ARROWMAX GT 601 Trasera', 8, 250000, 170000, 2, 'F-01', 'Dunlop', ['dunlop', '130-70-17', 'arrowmax']),
    ('LLN-002', 'Llanta KONTROL 110/90-17 KNT1001 Trasera', 10, 180000, 120000, 2, 'F-02', 'Kontrol', ['kontrol', '110-90-17']),
    ('LLN-003', 'Llanta KONTROL 110/90-17 TTR Trasera', 8, 160000, 105000, 2, 'F-03', 'Kontrol', ['kontrol', 'ttr']),
    ('LLN-004', 'Llanta Michelin 100/80-17 PILOT STREET 2 Delantera', 6, 320000, 220000, 1, 'F-04', 'Michelin', ['michelin', '100-80-17', 'pilot']),
    ('LLN-005', 'Llanta Michelin 130/70-17 PILOT STREET 2', 5, 350000, 240000, 1, 'F-05', 'Michelin', ['michelin', '130-70-17', 'pilot']),
    ('LLN-006', 'Llanta Michelin 140/70R-17 PILOT STREET Radial Trasera', 4, 380000, 260000, 1, 'F-06', 'Michelin', ['michelin', '140-70r-17']),
    ('LLN-007', 'Llanta Pirelli 150/60R-17 DIABLO ROSSO 3 Trasera', 3, 450000, 310000, 1, 'F-07', 'Pirelli', ['pirelli', '150', 'diablo']),
    ('LLN-008', 'Llanta Pirelli 140/70R-17 DIABLO ROSSO 3 Trasera', 4, 420000, 290000, 1, 'F-08', 'Pirelli', ['pirelli', '140', 'diablo']),
    ('LLN-009', 'Llanta Dunlop 130/70-17 (Deportiva)', 7, 220000, 150000, 2, 'F-09', 'Dunlop', ['dunlop', '130-70-17']),
    ('LLN-010', 'Llanta Kontrol 110/90-17 (Urbana)', 12, 140000, 92000, 3, 'F-10', 'Kontrol', ['kontrol', '110-90-17']),
]

frenos = [
    ('FRN-001', 'Pastilla Kevlar Delantero XTZ', 20, 35000, 22000, 5, 'G-01', 'Kevlar', ['kevlar', 'delantero', 'xtz']),
    ('FRN-002', 'Pastilla Kevlar Trasero CB 150 Invicta New', 18, 32000, 20000, 5, 'G-02', 'Kevlar', ['kevlar', 'trasero', 'cb']),
    ('FRN-003', 'Pastillas de Freno Pulsar 200 NS Bajaj', 25, 28000, 17000, 5, 'G-03', 'Bajaj', ['pulsar', '200', 'ns', 'freno']),
    ('FRN-004', 'Pastillas de Freno Thriller / Glamour / Passion Hero', 22, 22000, 14000, 5, 'G-04', 'Hero', ['thriller', 'glamour']),
]

transmision = [
    ('TRN-001', 'Cadena 428 (Original)', 15, 45000, 30000, 3, 'H-01', 'RK', ['cadena', '428']),
    ('TRN-002', 'Kit Arrastre NS (Relacion original)', 10, 85000, 55000, 2, 'H-02', 'RK', ['kit', 'arrastre', 'ns']),
    ('TRN-003', 'Pinon Delantero (Universal)', 20, 15000, 8500, 5, 'H-03', 'RK', ['pinon', 'delantero']),
]

suspension = [
    ('SUS-001', 'Amortiguador Trasero NS200 (Original)', 6, 180000, 120000, 2, 'I-01', 'Bajaj', ['amortiguador', 'ns200']),
    ('SUS-002', 'Horquilla Delantera NS 200 (Kit)', 4, 250000, 170000, 1, 'I-02', 'Bajaj', ['horquilla', 'ns']),
]

carroceria = [
    ('CAR-001', 'Manillar Universal (Acero)', 12, 55000, 35000, 3, 'J-01', 'Universal', ['manillar']),
]

herramientas = [
    ('HER-001', 'Kit de Herramientas Basico (15 piezas)', 10, 45000, 28000, 2, 'K-01', 'Generic', []),
    ('HER-002', 'Gato Hidraulico de Piso 2 Ton', 5, 180000, 120000, 1, 'K-02', 'Generic', []),
    ('HER-003', 'Compresor de Aire Portatil', 8, 120000, 80000, 1, 'K-03', 'Generic', []),
]

escape = [
    ('ESC-001', 'Silenciador Universal Deportivo', 6, 95000, 62000, 2, 'L-01', 'Universal', []),
    ('ESC-002', 'Tubo de Escape Completo Pulsar NS200', 4, 150000, 100000, 1, 'L-02', 'Bajaj', []),
]

all_products = (
    [('Lubricantes', 6, lub)] +
    [('Motor - Filtros Aceite', 1, filtros_aceite)] +
    [('Motor - Filtros Aire', 1, filtros_aire)] +
    [('Electrico - Baterias', 4, baterias)] +
    [('Electrico - Bujias', 4, bujias)] +
    [('Neumaticos', 7, llantas)] +
    [('Frenos', 2, frenos)] +
    [('Transmision', 5, transmision)] +
    [('Suspension', 3, suspension)] +
    [('Carroceria', 8, carroceria)] +
    [('Herramientas', 9, herramientas)] +
    [('Escape', 10, escape)]
)

all_product_ids = []
for grupo, cat_id, prods in all_products:
    cat_nombre = cat_name_map[cat_id]
    print(f"\n  --- {grupo} (cat={cat_nombre}) ---")
    for codigo, nombre, stock, precio, costo, stock_min, ubicacion, proveedor, keywords in prods:
        imagen = find_img(keywords)
        desc = f"{nombre} - {proveedor}"
        c.execute("""
            INSERT INTO repuestos (codigo, nombre, categoria, cantidad, precio, costo, stock_minimo,
             ubicacion, proveedor, imagen, descripcion, garantia)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (codigo, nombre, cat_nombre, stock, precio, costo, stock_min, ubicacion, proveedor, imagen, desc, '6 meses'))
        pid = c.fetchone()['id']
        all_product_ids.append(pid)
        img_status = f"[OK] {imagen}" if imagen else "[WARN] Sin imagen"
        print(f"  ID={pid:3} | {codigo:15} | ${precio:>7} | stock={stock:3} | {nombre[:40]:40} | {img_status}")

print(f"\n[OK] Total productos: {len(all_product_ids)}")

# Movimientos de entrada (stock inicial)
for pid in all_product_ids:
    c.execute("SELECT codigo, cantidad, precio FROM repuestos WHERE id = %s", (pid,))
    r = c.fetchone()
    c.execute("""
        INSERT INTO movimientos (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario, fecha)
        VALUES (%s, 'ENTRADA', %s, %s, 'Stock inicial primera semana', 'admin', NOW() - INTERVAL '7 days')
    """, (pid, r['cantidad'], r['precio']))

# Clientes
clientes = [
    ('Carlos Mendoza', 'carlos.mendoza@email.com', '3001234567', 'Calle 50 #20-30, Medellin'),
    ('Maria Garcia', 'maria.garcia@email.com', '3107654321', 'Carrera 80 #45-12, Medellin'),
    ('Pedro Ramirez', 'pedro.ramirez@email.com', '3209876543', 'Av. Las Palmas #15-40, Medellin'),
    ('Ana Lopez', 'ana.lopez@email.com', '3001112233', 'Calle 10 #5-60, Envigado'),
    ('Luis Torres', 'luis.torres@email.com', '3154445566', 'Carrera 43 #30-15, Sabaneta'),
    ('Sofia Rendon', 'sofia.rendon@email.com', '3017778899', 'Calle 30 #25-10, Bello'),
]
for nom, email, tel, direccion in clientes:
    c.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO usuarios (username, password, nombre, email, rol, activo, telefono, direccion)
            VALUES (%s, 'seed_client', %s, %s, 'cliente', 1, %s, %s)
        """, (email.split('@')[0], nom, email, tel, direccion))
        print(f"  Cliente creado: {nom}")

conn.commit()

# Pedidos
clientes_db = c.execute(
    "SELECT id, nombre, email, telefono, direccion FROM usuarios WHERE rol='cliente' AND activo=1"
).fetchall()

productos_db = c.execute(
    "SELECT id, codigo, nombre, precio FROM repuestos ORDER BY id"
).fetchall()

ventas_data = [
    (6, 0, [(0, 2), (6, 1)]),
    (6, 1, [(25, 1), (26, 1)]),
    (5, 2, [(40, 2)]),
    (5, 3, [(12, 1)]),
    (5, 4, [(49, 1)]),
    (4, 0, [(3, 3)]),
    (4, 5, [(33, 1), (34, 1)]),
    (4, 1, [(57, 1)]),
    (3, 2, [(20, 2)]),
    (3, 4, [(59, 1), (60, 1)]),
    (2, 3, [(6, 4)]),
    (2, 5, [(61, 1)]),
    (2, 0, [(44, 2)]),
    (1, 1, [(0, 1), (1, 1), (2, 1)]),
    (1, 4, [(52, 1)]),
    (1, 2, [(47, 1)]),
    (0, 5, [(10, 2)]),
    (0, 3, [(53, 1), (54, 1)]),
    (0, 0, [(36, 1), (37, 1)]),
]

factura_num = 1001
for dia_offset, cli_idx, items in ventas_data:
    cli = clientes_db[cli_idx]
    fecha = datetime.now() - timedelta(days=dia_offset)
    subtotal = 0
    detalle = []
    for prod_idx, cant in items:
        prod = productos_db[prod_idx]
        subtotal += prod['precio'] * cant
        detalle.append((prod, cant, prod['precio']))
    iva = round(subtotal * 0.19, 2)
    total = round(subtotal + iva, 2)
    factura = f"FAC-{factura_num}"

    c.execute("""
        INSERT INTO pedidos (factura, usuario_id, cliente_nombre, cliente_email, cliente_telefono,
         cliente_direccion, subtotal, iva, total, metodo_pago, estado, fecha)
        VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, 'Efectivo', 'completado', %s)
        RETURNING id
    """, (factura, cli['nombre'], cli['email'], cli['telefono'], cli['direccion'],
          subtotal, iva, total, fecha))
    pedido_id = c.fetchone()['id']

    for prod, cant, precio in detalle:
        sub = round(precio * cant, 2)
        c.execute("""
            INSERT INTO pedido_detalle (pedido_id, producto_id, codigo, nombre, cantidad, precio, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (pedido_id, prod['id'], prod['codigo'], prod['nombre'], cant, precio, sub))
        c.execute("""
            INSERT INTO movimientos (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario, fecha)
            VALUES (%s, 'SALIDA', %s, %s, %s, 'admin', %s)
        """, (prod['id'], cant, precio, f'Venta #{factura} - {cli["nombre"]}', fecha))
        c.execute("UPDATE repuestos SET cantidad = cantidad - %s WHERE id = %s", (cant, prod['id']))

    c.execute("""
        INSERT INTO actividad (usuario_id, usuario_nombre, accion, detalle, fecha)
        VALUES (1, 'admin', 'Venta realizada', %s, %s)
    """, (f'Venta #{factura} - ${total:,.0f} - {cli["nombre"]}', fecha))

    factura_num += 1
    print(f"  Pedido {factura}: {cli['nombre']} - ${total:,.0f} ({len(items)} productos) - {fecha.strftime('%d/%m/%Y')}")

conn.commit()

# Alertas stock bajo
bajos = c.execute("""
    SELECT id, codigo, nombre, cantidad, stock_minimo
    FROM repuestos WHERE cantidad <= stock_minimo ORDER BY cantidad
""").fetchall()
for p in bajos:
    c.execute("""
        INSERT INTO alertas (repuesto_id, mensaje, tipo, estado)
        VALUES (%s, %s, 'stock_bajo', 'PENDIENTE')
    """, (p['id'], f'Stock bajo: {p["nombre"]} ({p["cantidad"]} und, minimo {p["stock_minimo"]})'))
    print(f"  [ ! ] Stock bajo: {p['nombre'][:35]} ({p['cantidad']}/{p['stock_minimo']})")

conn.commit()

# Verificacion
for tbl in ['categorias', 'repuestos', 'pedidos', 'movimientos', 'alertas']:
    cnt = c.execute(f"SELECT COUNT(*) as cnt FROM {tbl}").fetchone()['cnt']
    print(f"  {tbl}: {cnt}")

c.close()
conn.close()
print("\n[OK] SEED SUPABASE COMPLETADO!")
