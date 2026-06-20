import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import bcrypt
import hashlib

DATABASE_URL = os.environ.get('SUPABASE_DATABASE_URL', '') or os.environ.get('DATABASE_URL', '')

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError('SUPABASE_DATABASE_URL no configurada')
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def obtener_conexion():
    return get_conn()

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def crear_tablas():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS repuestos (
        id SERIAL PRIMARY KEY,
        codigo TEXT UNIQUE,
        nombre TEXT NOT NULL,
        categoria TEXT NOT NULL,
        cantidad INTEGER DEFAULT 0,
        precio DOUBLE PRECISION DEFAULT 0,
        stock_minimo INTEGER DEFAULT 5,
        ubicacion TEXT,
        proveedor TEXT,
        imagen TEXT,
        descripcion TEXT,
        caracteristicas TEXT,
        especificaciones TEXT,
        garantia TEXT,
        peso TEXT,
        costo DOUBLE PRECISION DEFAULT 0,
        fecha_registro TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS movimientos (
        id SERIAL PRIMARY KEY,
        repuesto_id INTEGER REFERENCES repuestos(id),
        tipo_movimiento TEXT,
        cantidad INTEGER,
        precio_unitario DOUBLE PRECISION,
        motivo TEXT,
        usuario TEXT,
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS alertas (
        id SERIAL PRIMARY KEY,
        repuesto_id INTEGER REFERENCES repuestos(id),
        tipo TEXT,
        estado TEXT DEFAULT 'PENDIENTE',
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre TEXT,
        email TEXT,
        rol TEXT DEFAULT 'cliente',
        activo INTEGER DEFAULT 1,
        telefono TEXT DEFAULT '',
        direccion TEXT DEFAULT '',
        foto_perfil TEXT DEFAULT '',
        ultimo_acceso TIMESTAMP,
        reset_token TEXT,
        reset_token_expiry DOUBLE PRECISION,
        permisos TEXT DEFAULT '{}',
        fecha_registro TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id SERIAL PRIMARY KEY,
        factura TEXT UNIQUE NOT NULL,
        usuario_id INTEGER REFERENCES usuarios(id),
        cliente_nombre TEXT,
        cliente_cedula TEXT,
        subtotal DOUBLE PRECISION,
        iva DOUBLE PRECISION,
        total DOUBLE PRECISION,
        estado TEXT DEFAULT 'completada',
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS venta_detalle (
        id SERIAL PRIMARY KEY,
        venta_id INTEGER REFERENCES ventas(id),
        producto_id INTEGER REFERENCES repuestos(id),
        codigo TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio DOUBLE PRECISION,
        subtotal DOUBLE PRECISION
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (
        id SERIAL PRIMARY KEY,
        factura TEXT UNIQUE NOT NULL,
        usuario_id INTEGER REFERENCES usuarios(id),
        cliente_nombre TEXT NOT NULL,
        cliente_email TEXT,
        cliente_telefono TEXT,
        cliente_direccion TEXT,
        subtotal DOUBLE PRECISION,
        iva DOUBLE PRECISION,
        total DOUBLE PRECISION,
        metodo_pago TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS pedido_detalle (
        id SERIAL PRIMARY KEY,
        pedido_id INTEGER REFERENCES pedidos(id),
        producto_id INTEGER REFERENCES repuestos(id),
        codigo TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio DOUBLE PRECISION,
        subtotal DOUBLE PRECISION
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS pagos (
        id SERIAL PRIMARY KEY,
        pedido_id INTEGER REFERENCES pedidos(id),
        metodo_pago TEXT,
        monto DOUBLE PRECISION,
        referencia TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (
        id SERIAL PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        icono TEXT DEFAULT 'generic',
        descripcion TEXT DEFAULT '',
        imagen TEXT DEFAULT '',
        activo INTEGER DEFAULT 1,
        fecha_registro TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor TEXT DEFAULT '',
        tipo TEXT DEFAULT 'text'
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS actividad (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER,
        usuario_nombre TEXT,
        accion TEXT NOT NULL,
        detalle TEXT DEFAULT '',
        ip TEXT DEFAULT '',
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS webhooks (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        url TEXT NOT NULL,
        evento TEXT NOT NULL,
        activo INTEGER DEFAULT 1,
        ultima_respuesta INTEGER DEFAULT 0,
        ultimo_error TEXT DEFAULT '',
        fecha_creacion TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS webhook_logs (
        id SERIAL PRIMARY KEY,
        webhook_id INTEGER REFERENCES webhooks(id),
        evento TEXT,
        url TEXT,
        payload TEXT,
        respuesta INTEGER,
        error TEXT,
        fecha TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS sucursales (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        direccion TEXT,
        telefono TEXT,
        encargado TEXT,
        activo INTEGER DEFAULT 1,
        fecha_registro TIMESTAMP DEFAULT NOW()
    )''')

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_repuesto ON movimientos(repuesto_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pedidos_usuario ON pedidos(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repuestos_categoria ON repuestos(categoria)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repuestos_nombre ON repuestos(nombre)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pedido_detalle_producto ON pedido_detalle(producto_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actividad_fecha ON actividad(fecha DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_evento ON webhooks(evento)")

    cursor.execute("SELECT COUNT(*) as cnt FROM config")
    if cursor.fetchone()['cnt'] == 0:
        config_default = [
            ('whatsapp', '573000000000', 'text'),
            ('facebook', '', 'text'),
            ('instagram', '', 'text'),
            ('youtube', '', 'text'),
            ('tiktok', '', 'text'),
            ('empresa_nombre', 'Celeris Moto Express', 'text'),
            ('empresa_email', 'info@stockpro.com', 'text'),
            ('empresa_telefono', '+57 300 000 0000', 'text'),
            ('empresa_direccion', '', 'text'),
            ('empresa_horarios', 'Lun-Sab: 8:00 AM - 6:00 PM', 'text'),
            ('empresa_logo', '', 'text'),
            ('anio_copyright', '2026', 'text'),
        ]
        cursor.executemany("INSERT INTO config (clave, valor, tipo) VALUES (%s, %s, %s) ON CONFLICT (clave) DO NOTHING", config_default)

    cursor.execute("SELECT COUNT(*) as cnt FROM categorias")
    if cursor.fetchone()['cnt'] == 0:
        categorias_default = [
            ('motor', 'Motor', 'engine', 'Filtros, bujias y todo para el motor de tu moto'),
            ('frenos', 'Frenos', 'brake', 'Pastillas, discos y componentes de freno de alta calidad'),
            ('suspension', 'Suspension', 'suspension', 'Horquillas, amortiguadores y componentes para una conduccion suave'),
            ('electrico', 'Electrico', 'electric', 'Baterias, focos y sistema electrico para tu moto'),
            ('transmision', 'Transmision', 'transmission', 'Cadenas, pinones, coronas y embragues para tu moto'),
            ('lubricantes', 'Lubricantes', 'oil', 'Aceites de motor y lubricantes de primera calidad'),
            ('neumaticos', 'Neumaticos', 'tire', 'Llantas de alta calidad para tu moto'),
            ('carroceria', 'Carroceria', 'body', 'Espejos, manillares, guardabarros y accesorios esteticos'),
            ('herramientas', 'Herramientas', 'tools', 'Kit de herramientas y equipos para mantenimiento profesional'),
            ('escape', 'Escape', 'exhaust', 'Silenciadores, tubos y empaques para el sistema de escape'),
        ]
        cursor.executemany("INSERT INTO categorias (slug, nombre, icono, descripcion) VALUES (%s, %s, %s, %s) ON CONFLICT (slug) DO NOTHING", categorias_default)

    cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_hash = hash_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
        cursor.execute('''INSERT INTO usuarios (username, password, nombre, email, rol, activo)
                          VALUES (%s, %s, %s, %s, %s, %s)''',
                       ('admin', admin_hash, 'Administrador', 'admin@stockpro.com', 'administrador', 1))

    conn.commit()
    conn.close()
    print("[OK] Tablas Supabase creadas/verificadas correctamente")


def verificar_usuario(username, password):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, rol, password FROM usuarios WHERE username = %s AND activo = 1", (username,))
    usuario = cursor.fetchone()
    if not usuario:
        conn.close()
        return None
    stored_hash = usuario['password']
    try:
        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            conn.close()
            return (usuario['id'], usuario['username'], usuario['nombre'], usuario['rol'])
    except ValueError:
        pass
    if stored_hash == hashlib.sha256(password.encode()).hexdigest():
        new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (new_hash, usuario['id']))
        conn.commit()
        conn.close()
        return (usuario['id'], usuario['username'], usuario['nombre'], usuario['rol'])
    conn.close()
    return None


def obtener_usuario_por_id(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, rol, email, telefono, direccion FROM usuarios WHERE id = %s", (user_id,))
    u = cursor.fetchone()
    conn.close()
    return u


def obtener_usuario_por_email(email):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre FROM usuarios WHERE email = %s AND activo = 1", (email,))
    u = cursor.fetchone()
    conn.close()
    return u


def guardar_token_reset(user_id, token):
    conn = get_conn()
    cursor = conn.cursor()
    expiry = datetime.now().timestamp() + 3600
    cursor.execute("UPDATE usuarios SET reset_token = %s, reset_token_expiry = %s WHERE id = %s", (token, expiry, user_id))
    conn.commit()
    conn.close()


def verificar_token_reset(token):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE reset_token = %s AND reset_token_expiry > %s", (token, datetime.now().timestamp()))
    u = cursor.fetchone()
    conn.close()
    return u


def actualizar_password(user_id, nueva_password):
    conn = get_conn()
    cursor = conn.cursor()
    new_hash = hash_password(nueva_password)
    cursor.execute("UPDATE usuarios SET password = %s, reset_token = NULL, reset_token_expiry = NULL WHERE id = %s", (new_hash, user_id))
    conn.commit()
    conn.close()


def obtener_todos_usuarios():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, email, rol, activo, fecha_registro, foto_perfil FROM usuarios ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return rows


def actualizar_usuario(user_id, nombre, email, rol, activo, foto_perfil=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET nombre = %s, email = %s, rol = %s, activo = %s, foto_perfil = %s WHERE id = %s",
                   (nombre, email, rol, activo, foto_perfil, user_id))
    conn.commit()
    conn.close()


def eliminar_usuario(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s AND username != 'admin'", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def obtener_categorias():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nombre, icono, descripcion, imagen FROM categorias WHERE activo = 1 ORDER BY nombre")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'slug': r['slug'], 'nombre': r['nombre'], 'icono': r['icono'], 'descripcion': r['descripcion'], 'imagen': r['imagen'] or ''} for r in rows]


def obtener_todas_categorias():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nombre, icono, descripcion, imagen, activo FROM categorias ORDER BY activo DESC, nombre")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'slug': r['slug'], 'nombre': r['nombre'], 'icono': r['icono'], 'descripcion': r['descripcion'], 'imagen': r['imagen'] or '', 'activo': r['activo']} for r in rows]


def obtener_categoria_por_slug(slug):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nombre, icono, descripcion, imagen FROM categorias WHERE slug = %s AND activo = 1", (slug,))
    c = cursor.fetchone()
    conn.close()
    if c:
        return {'id': c['id'], 'slug': c['slug'], 'nombre': c['nombre'], 'icono': c['icono'], 'descripcion': c['descripcion'], 'imagen': c['imagen'] or ''}
    return None


def crear_categoria(slug, nombre, icono, descripcion, imagen=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO categorias (slug, nombre, icono, descripcion, imagen) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                   (slug, nombre, icono, descripcion, imagen))
    new_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    return new_id


def actualizar_categoria(id, slug, nombre, icono, descripcion, activo, imagen=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE categorias SET slug = %s, nombre = %s, icono = %s, descripcion = %s, activo = %s, imagen = %s WHERE id = %s",
                   (slug, nombre, icono, descripcion, activo, imagen, id))
    conn.commit()
    conn.close()


def eliminar_categoria(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE categorias SET activo = 0 WHERE id = %s", (id,))
    conn.commit()
    conn.close()


def reactivar_categoria(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE categorias SET activo = 1 WHERE id = %s", (id,))
    conn.commit()
    conn.close()


def borrar_categoria(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE repuestos SET categoria = 'Sin categoria' WHERE categoria = (SELECT nombre FROM categorias WHERE id = %s)", (id,))
    cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
    conn.commit()
    conn.close()


def get_config(clave, default=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE clave = %s", (clave,))
    row = cursor.fetchone()
    conn.close()
    return row['valor'] if row else default


def set_config(clave, valor):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO config (clave, valor, tipo)
        VALUES (%s, %s, COALESCE((SELECT tipo FROM config WHERE clave = %s), 'text'))
        ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor
    ''', (clave, valor, clave))
    conn.commit()
    conn.close()


def get_all_config():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM config")
    rows = cursor.fetchall()
    conn.close()
    return {r['clave']: r['valor'] for r in rows}


def obtener_foto_perfil(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT foto_perfil FROM usuarios WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['foto_perfil'] if row and row['foto_perfil'] else ''


def actualizar_ultimo_acceso(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET ultimo_acceso = NOW() WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()


def obtener_usuarios_activos(minutos=15):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, nombre, foto_perfil, ultimo_acceso, rol
        FROM usuarios
        WHERE activo = 1 AND ultimo_acceso IS NOT NULL
          AND ultimo_acceso > NOW() - INTERVAL '1 minute' * %s
        ORDER BY ultimo_acceso DESC
    ''', (minutos,))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'username': r['username'], 'nombre': r['nombre'], 'foto_perfil': r['foto_perfil'] or '', 'ultimo_acceso': r['ultimo_acceso'], 'rol': r['rol']} for r in rows]


def log_actividad(usuario_id, usuario_nombre, accion, detalle='', ip=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO actividad (usuario_id, usuario_nombre, accion, detalle, ip) VALUES (%s, %s, %s, %s, %s)",
                   (usuario_id, usuario_nombre, accion, detalle, ip))
    conn.commit()
    conn.close()


def obtener_actividad(limite=100, offset=0):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario_id, usuario_nombre, accion, detalle, ip, fecha FROM actividad ORDER BY fecha DESC LIMIT %s OFFSET %s", (limite, offset))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'usuario_id': r['usuario_id'], 'usuario_nombre': r['usuario_nombre'], 'accion': r['accion'], 'detalle': r['detalle'], 'ip': r['ip'], 'fecha': r['fecha']} for r in rows]


def contar_actividad():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM actividad")
    total = cursor.fetchone()['cnt']
    conn.close()
    return total


ROLES = {
    'administrador': ['ver_dashboard', 'gestionar_productos', 'gestionar_categorias', 'gestionar_usuarios',
                       'gestionar_pedidos', 'ver_analitica', 'gestionar_config', 'gestionar_respaldos',
                       'ver_logs', 'gestionar_webhooks'],
    'vendedor': ['ver_dashboard', 'gestionar_pedidos', 'ver_productos', 'ver_analitica'],
    'bodeguero': ['gestionar_productos', 'gestionar_categorias', 'ver_dashboard',
                   'ver_movimientos', 'ver_inventario'],
    'cliente': []
}

def get_rol_permisos(rol):
    return ROLES.get(rol, [])

def usuario_tiene_permiso(rol, permiso):
    return permiso in ROLES.get(rol, [])

def obtener_usuarios():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, email, rol, activo, telefono, fecha_registro FROM usuarios ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'username': r['username'], 'nombre': r['nombre'], 'email': r['email'], 'rol': r['rol'], 'activo': r['activo'], 'telefono': r['telefono'], 'fecha_registro': r['fecha_registro']} for r in rows]


def actualizar_usuario_rol(user_id, rol, activo=None):
    conn = get_conn()
    cursor = conn.cursor()
    if activo is not None:
        cursor.execute("UPDATE usuarios SET rol = %s, activo = %s WHERE id = %s", (rol, 1 if activo else 0, user_id))
    else:
        cursor.execute("UPDATE usuarios SET rol = %s WHERE id = %s", (rol, user_id))
    conn.commit()
    conn.close()


_cache = {}
_cache_ttl = {}

def cache_get(key):
    if key in _cache:
        if _cache_ttl.get(key, 0) > 0:
            if (datetime.now() - _cache[key]['ts']).total_seconds() > _cache_ttl[key]:
                del _cache[key]
                del _cache_ttl[key]
                return None
        return _cache[key]['data']
    return None

def cache_set(key, data, ttl=60):
    _cache[key] = {'data': data, 'ts': datetime.now()}
    _cache_ttl[key] = ttl

def cache_clear(pattern=None):
    global _cache, _cache_ttl
    if pattern:
        keys = [k for k in _cache if pattern in k]
        for k in keys:
            del _cache[k]
            if k in _cache_ttl:
                del _cache_ttl[k]
    else:
        _cache = {}
        _cache_ttl = {}


def crear_webhook(nombre, url, evento):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO webhooks (nombre, url, evento) VALUES (%s, %s, %s) RETURNING id", (nombre, url, evento))
    new_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    return new_id


def obtener_webhooks():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, url, evento, activo, ultima_respuesta, ultimo_error, fecha_creacion FROM webhooks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'nombre': r['nombre'], 'url': r['url'], 'evento': r['evento'], 'activo': r['activo'], 'ultima_respuesta': r['ultima_respuesta'], 'ultimo_error': r['ultimo_error'], 'fecha_creacion': r['fecha_creacion']} for r in rows]


def eliminar_webhook(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM webhooks WHERE id = %s", (id,))
    conn.commit()
    conn.close()


def webhook_log(webhook_id, evento, url, payload, respuesta, error=''):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO webhook_logs (webhook_id, evento, url, payload, respuesta, error) VALUES (%s, %s, %s, %s, %s, %s)",
                   (webhook_id, evento, url, payload, respuesta, error))
    cursor.execute("UPDATE webhooks SET ultima_respuesta = %s, ultimo_error = %s WHERE id = %s", (respuesta, error, webhook_id))
    conn.commit()
    conn.close()


def obtener_webhook_logs(limite=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, webhook_id, evento, url, respuesta, error, fecha FROM webhook_logs ORDER BY fecha DESC LIMIT %s", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'webhook_id': r['webhook_id'], 'evento': r['evento'], 'url': r['url'], 'respuesta': r['respuesta'], 'error': r['error'], 'fecha': r['fecha']} for r in rows]


def disparar_webhook(evento, payload):
    import json
    import urllib.request
    import urllib.error
    webhooks = obtener_webhooks()
    for wh in webhooks:
        if wh['evento'] == evento and wh['activo']:
            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(wh['url'], data=data, headers={'Content-Type': 'application/json'})
                resp = urllib.request.urlopen(req, timeout=10)
                webhook_log(wh['id'], evento, wh['url'], json.dumps(payload), resp.status)
            except Exception as e:
                webhook_log(wh['id'], evento, wh['url'], json.dumps(payload), 0, str(e))


def crear_pedido(usuario_id, cliente_nombre, cliente_email, cliente_telefono, cliente_direccion, carrito, subtotal, iva, total, metodo_pago):
    import random
    conn = get_conn()
    cursor = conn.cursor()
    factura = f"PED-{random.randint(10000, 99999)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cursor.execute('''INSERT INTO pedidos
        (factura, usuario_id, cliente_nombre, cliente_email, cliente_telefono, cliente_direccion,
         subtotal, iva, total, metodo_pago, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id''',
        (factura, usuario_id, cliente_nombre, cliente_email, cliente_telefono, cliente_direccion,
         subtotal, iva, total, metodo_pago, 'pendiente'))
    pedido_id = cursor.fetchone()['id']
    for item in carrito:
        cursor.execute('''INSERT INTO pedido_detalle
            (pedido_id, producto_id, codigo, nombre, cantidad, precio, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (pedido_id, item['id'], item.get('codigo', ''), item['nombre'],
             item['cantidad'], item['precio'], item['precio'] * item['cantidad']))
    cursor.execute('''INSERT INTO pagos (pedido_id, metodo_pago, monto, estado)
                      VALUES (%s, %s, %s, %s)''',
                   (pedido_id, metodo_pago, total, 'pendiente'))
    conn.commit()
    conn.close()
    return pedido_id, factura


def confirmar_pago(pedido_id, nombre_cliente=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT producto_id, cantidad, precio FROM pedido_detalle WHERE pedido_id = %s", (pedido_id,))
    detalles = cursor.fetchall()
    cliente_mov = nombre_cliente if nombre_cliente else 'Invitado'
    for d in detalles:
        pid = d['producto_id']
        cant = d['cantidad']
        precio = d['precio']
        cursor.execute("SELECT cantidad FROM repuestos WHERE id = %s", (pid,))
        stock = cursor.fetchone()
        if not stock:
            conn.rollback()
            conn.close()
            raise Exception(f'Producto ID {pid} no encontrado')
        if stock['cantidad'] < cant:
            conn.rollback()
            conn.close()
            raise Exception(f'Stock insuficiente ID {pid}. Disp: {stock["cantidad"]}, req: {cant}')
        cursor.execute("UPDATE repuestos SET cantidad = cantidad - %s WHERE id = %s", (cant, pid))
        cursor.execute('''INSERT INTO movimientos (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario)
                          VALUES (%s, 'SALIDA', %s, %s, %s, %s)''',
                       (pid, cant, precio, f'Venta pedido #{pedido_id}', cliente_mov))
    cursor.execute("UPDATE pagos SET estado = 'completado' WHERE pedido_id = %s", (pedido_id,))
    cursor.execute("UPDATE pedidos SET estado = 'pagado' WHERE id = %s", (pedido_id,))
    conn.commit()
    conn.close()


def obtener_pedidos_usuario(usuario_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE usuario_id = %s ORDER BY fecha DESC", (usuario_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_pedido_detalle(pedido_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedido_detalle WHERE pedido_id = %s", (pedido_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_resumen_dashboard():
    conn = get_conn()
    cursor = conn.cursor()
    hoy = datetime.now().strftime('%Y-%m-%d')
    inicio_mes = datetime.now().replace(day=1).strftime('%Y-%m-%d')

    cursor.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(total),0) as sum FROM pedidos WHERE fecha::date = %s AND estado IN ('pagado','entregado')", (hoy,))
    ventas_hoy = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(total),0) as sum FROM pedidos WHERE fecha::date >= %s AND estado IN ('pagado','entregado')", (inicio_mes,))
    ventas_mes = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as cnt FROM pedidos WHERE estado = 'pendiente'")
    pendientes = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE fecha_registro::date = %s AND rol = 'cliente'", (hoy,))
    clientes_hoy = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE rol = 'cliente'")
    total_clientes = cursor.fetchone()['cnt']

    cursor.execute('''SELECT p.id, p.factura, p.cliente_nombre, p.total, p.estado, p.metodo_pago, p.fecha
                      FROM pedidos p ORDER BY p.fecha DESC LIMIT 10''')
    pedidos = cursor.fetchall()
    cursor.execute('''SELECT id, nombre, codigo, cantidad, stock_minimo, precio
                      FROM repuestos WHERE cantidad <= stock_minimo ORDER BY cantidad ASC LIMIT 10''')
    stock_critico = cursor.fetchall()

    import calendar
    ahora = datetime.now()
    if ahora.month == 1:
        mes_ant = datetime(ahora.year - 1, 12, 1)
    else:
        mes_ant = datetime(ahora.year, ahora.month - 1, 1)
    fin_mes_ant = mes_ant.replace(day=calendar.monthrange(mes_ant.year, mes_ant.month)[1])
    cursor.execute("SELECT COALESCE(SUM(total),0) as sum FROM pedidos WHERE fecha >= %s AND fecha < %s AND estado IN ('pagado','entregado')",
                   (mes_ant.strftime('%Y-%m-%d'), fin_mes_ant.strftime('%Y-%m-%d') + ' 23:59:59'))
    ventas_mes_anterior_valor = cursor.fetchone()['sum']

    ventas_ant_valor = float(ventas_mes_anterior_valor or 0)
    ventas_mes_valor = float(ventas_mes['sum'] or 0)
    crecimiento = round(((ventas_mes_valor - ventas_ant_valor) / ventas_ant_valor * 100), 1) if ventas_ant_valor > 0 else 0

    cursor.execute("SELECT COUNT(*) as cnt FROM repuestos")
    total_productos = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM repuestos WHERE cantidad <= stock_minimo")
    stock_critico_count = cursor.fetchone()['cnt']
    cursor.execute("SELECT COALESCE(SUM(cantidad * precio),0) as sum FROM repuestos")
    valor_inventario = cursor.fetchone()['sum']
    salud = round(((total_productos - stock_critico_count) / total_productos * 100), 1) if total_productos > 0 else 100

    conn.close()
    return {
        'total_productos': total_productos,
        'stock_critico': stock_critico_count,
        'valor_inventario': valor_inventario,
        'salud_inventario': salud,
        'ventas_hoy_count': int(ventas_hoy['cnt'] or 0),
        'ventas_hoy_valor': float(ventas_hoy['sum'] or 0),
        'ventas_mes_count': int(ventas_mes['cnt'] or 0),
        'ventas_mes_valor': ventas_mes_valor,
        'ventas_mes_anterior_count': 0,
        'ventas_mes_anterior_valor': ventas_ant_valor,
        'crecimiento_ventas': crecimiento,
        'pedidos_pendientes': pendientes,
        'clientes_nuevos_hoy': clientes_hoy,
        'total_clientes': total_clientes,
        'ultimos_pedidos': [{
            'id': p['id'], 'factura': p['factura'], 'cliente': p['cliente_nombre'],
            'total': p['total'], 'estado': p['estado'], 'metodo_pago': p['metodo_pago'], 'fecha': p['fecha']
        } for p in pedidos],
        'stock_critico_lista': [{
            'id': p['id'], 'nombre': p['nombre'], 'codigo': p['codigo'],
            'cantidad': p['cantidad'], 'stock_minimo': p['stock_minimo'], 'precio': p['precio']
        } for p in stock_critico]
    }
