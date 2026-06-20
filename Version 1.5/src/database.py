import sqlite3
from datetime import datetime
import hashlib
import bcrypt
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'stockpro.db')

def obtener_conexion():
    db_url = os.environ.get('DATABASE_URL', '')
    if 'postgres' in db_url:
        from .db_adapter import get_connection
        return get_connection()
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def crear_tablas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Tabla repuestos - CON TODAS LAS COLUMNAS
    cursor.execute('''CREATE TABLE IF NOT EXISTS repuestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        nombre TEXT NOT NULL,
        categoria TEXT NOT NULL,
        cantidad INTEGER DEFAULT 0,
        precio REAL DEFAULT 0,
        stock_minimo INTEGER DEFAULT 5,
        ubicacion TEXT,
        proveedor TEXT,
        imagen TEXT,
        descripcion TEXT,
        caracteristicas TEXT,
        especificaciones TEXT,
        garantia TEXT,
        peso TEXT,
        costo REAL DEFAULT 0,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabla movimientos
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repuesto_id INTEGER,
        tipo_movimiento TEXT,
        cantidad INTEGER,
        precio_unitario REAL,
        motivo TEXT,
        usuario TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (repuesto_id) REFERENCES repuestos(id)
    )''')
    
    # Tabla alertas
    cursor.execute('''CREATE TABLE IF NOT EXISTS alertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repuesto_id INTEGER,
        mensaje TEXT,
        tipo TEXT,
        estado TEXT DEFAULT 'PENDIENTE',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (repuesto_id) REFERENCES repuestos(id)
    )''')
    
    # Tabla usuarios
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre TEXT,
        email TEXT,
        rol TEXT DEFAULT 'cliente',
        activo INTEGER DEFAULT 1,
        telefono TEXT,
        direccion TEXT,
        reset_token TEXT,
        reset_token_expiry TIMESTAMP,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Migración segura para bases existentes
    for col, tipo in [('telefono', 'TEXT'), ('direccion', 'TEXT'),
                      ('foto_perfil', "TEXT DEFAULT ''"),
                      ('ultimo_acceso', 'TIMESTAMP')]:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")
        except Exception:
            pass
    try:
        cursor.execute("ALTER TABLE repuestos ADD COLUMN costo REAL DEFAULT 0")
    except Exception:
        pass
    
    # Tabla ventas (sistema anterior)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura TEXT UNIQUE NOT NULL,
        usuario_id INTEGER,
        cliente_nombre TEXT,
        cliente_cedula TEXT,
        subtotal REAL,
        iva REAL,
        total REAL,
        estado TEXT DEFAULT 'completada',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )''')
    
    # Tabla venta_detalle
    cursor.execute('''CREATE TABLE IF NOT EXISTS venta_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto_id INTEGER,
        codigo TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio REAL,
        subtotal REAL,
        FOREIGN KEY (venta_id) REFERENCES ventas(id),
        FOREIGN KEY (producto_id) REFERENCES repuestos(id)
    )''')
    
    # ========== NUEVAS TABLAS PARA SISTEMA DE PAGO ==========
    
    # Tabla de pedidos (ordenes de compra)
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura TEXT UNIQUE NOT NULL,
        usuario_id INTEGER,
        cliente_nombre TEXT NOT NULL,
        cliente_email TEXT,
        cliente_telefono TEXT,
        cliente_direccion TEXT,
        subtotal REAL,
        iva REAL,
        total REAL,
        metodo_pago TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )''')
    
    # Tabla de detalles del pedido
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedido_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        producto_id INTEGER,
        codigo TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio REAL,
        subtotal REAL,
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
        FOREIGN KEY (producto_id) REFERENCES repuestos(id)
    )''')
    
    # Tabla de pagos
    cursor.execute('''CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        metodo_pago TEXT,
        monto REAL,
        referencia TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
    )''')
    
    # Tabla categorias
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        icono TEXT DEFAULT 'generic',
        descripcion TEXT DEFAULT '',
        imagen TEXT DEFAULT '',
        activo INTEGER DEFAULT 1,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabla configuracion
    cursor.execute('''CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor TEXT DEFAULT '',
        tipo TEXT DEFAULT 'text'
    )''')
    
    # Insertar configuraciones por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM config")
    if cursor.fetchone()[0] == 0:
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
        cursor.executemany("INSERT OR IGNORE INTO config (clave, valor, tipo) VALUES (?, ?, ?)", config_default)
    
    # Poblar categorias por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
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
        cursor.executemany("INSERT INTO categorias (slug, nombre, icono, descripcion) VALUES (?, ?, ?, ?)", categorias_default)
    
    # Migración: agregar columna imagen si no existe
    try:
        cursor.execute("ALTER TABLE categorias ADD COLUMN imagen TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # ya existe
    
    # Crear usuario admin por defecto si no existe
    cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_password_hash = hash_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
        cursor.execute('''INSERT INTO usuarios (username, password, nombre, email, rol, activo) 
                          VALUES (?, ?, ?, ?, ?, ?)''', 
                          ('admin', admin_password_hash, 'Administrador', 'admin@stockpro.com', 'administrador', 1))
    
    conn.commit()

    # Indices para rendimiento
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_repuesto ON movimientos(repuesto_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pedidos_usuario ON pedidos(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repuestos_categoria ON repuestos(categoria)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repuestos_nombre ON repuestos(nombre)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pedido_detalle_producto ON pedido_detalle(producto_id)")

    # ========== TABLA DE ACTIVIDAD / LOGS ==========
    cursor.execute('''CREATE TABLE IF NOT EXISTS actividad (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        usuario_nombre TEXT,
        accion TEXT NOT NULL,
        detalle TEXT DEFAULT '',
        ip TEXT DEFAULT '',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actividad_fecha ON actividad(fecha DESC)")

    # ========== TABLA DE WEBHOOKS ==========
    cursor.execute('''CREATE TABLE IF NOT EXISTS webhooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        url TEXT NOT NULL,
        evento TEXT NOT NULL,
        activo INTEGER DEFAULT 1,
        ultima_respuesta INTEGER DEFAULT 0,
        ultimo_error TEXT DEFAULT '',
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_evento ON webhooks(evento)")

    # ========== TABLA DE LOGS DE WEBHOOKS ==========
    cursor.execute('''CREATE TABLE IF NOT EXISTS webhook_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        webhook_id INTEGER,
        evento TEXT,
        url TEXT,
        payload TEXT,
        respuesta INTEGER,
        error TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Agregar columna permisos a usuarios si no existe
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN permisos TEXT DEFAULT '{}'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("[OK] Tablas creadas/verificadas correctamente")

# ========== FUNCIONES DE PEDIDOS Y PAGOS ==========

def crear_pedido(usuario_id, cliente_nombre, cliente_email, cliente_telefono, cliente_direccion, carrito, subtotal, iva, total, metodo_pago):
    """Crea un nuevo pedido con estado pendiente"""
    import random
    from datetime import datetime
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    factura = f"PED-{random.randint(10000, 99999)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    cursor.execute('''INSERT INTO pedidos 
        (factura, usuario_id, cliente_nombre, cliente_email, cliente_telefono, cliente_direccion, 
         subtotal, iva, total, metodo_pago, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (factura, usuario_id, cliente_nombre, cliente_email, cliente_telefono, cliente_direccion,
         subtotal, iva, total, metodo_pago, 'pendiente'))
    
    pedido_id = cursor.lastrowid
    
    for item in carrito:
        cursor.execute('''INSERT INTO pedido_detalle 
            (pedido_id, producto_id, codigo, nombre, cantidad, precio, subtotal)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (pedido_id, item['id'], item.get('codigo', ''), item['nombre'], 
             item['cantidad'], item['precio'], item['precio'] * item['cantidad']))
    
    # Registrar pago pendiente
    cursor.execute('''INSERT INTO pagos 
        (pedido_id, metodo_pago, monto, estado)
        VALUES (?, ?, ?, ?)''',
        (pedido_id, metodo_pago, total, 'pendiente'))
    
    conn.commit()
    conn.close()
    
    return pedido_id, factura

def confirmar_pago(pedido_id, nombre_cliente=None):
    """Confirma un pago y actualiza stock. El nombre_cliente es el nombre del usuario logueado o 'Invitado'"""
    conn = obtener_conexion()
    conn.execute("BEGIN IMMEDIATE")
    cursor = conn.cursor()
    
    # Obtener detalles del pedido para verificar y actualizar stock
    cursor.execute("SELECT producto_id, cantidad, precio FROM pedido_detalle WHERE pedido_id = ?", (pedido_id,))
    detalles = cursor.fetchall()
    
    # Determinar quién hizo la compra
    cliente_movimiento = nombre_cliente if nombre_cliente else 'Invitado'
    
    for detalle in detalles:
        producto_id = detalle[0]
        cantidad = detalle[1]
        precio = detalle[2]
        
        # Verificar stock suficiente
        cursor.execute("SELECT cantidad FROM repuestos WHERE id = ?", (producto_id,))
        stock_actual = cursor.fetchone()
        if not stock_actual:
            conn.rollback()
            conn.close()
            raise Exception(f'Producto ID {producto_id} no encontrado')
        if stock_actual[0] < cantidad:
            conn.rollback()
            conn.close()
            raise Exception(f'Stock insuficiente para producto ID {producto_id}. Disponible: {stock_actual[0]}, solicitado: {cantidad}')
        
        cursor.execute("UPDATE repuestos SET cantidad = cantidad - ? WHERE id = ?", (cantidad, producto_id))
        
        # Registrar movimiento con el nombre del cliente
        cursor.execute('''INSERT INTO movimientos 
            (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario)
            VALUES (?, 'SALIDA', ?, ?, ?, ?)''',
            (producto_id, cantidad, precio, f'Venta pedido #{pedido_id}', cliente_movimiento))
    
    # Actualizar estado del pago
    cursor.execute("UPDATE pagos SET estado = 'completado' WHERE pedido_id = ?", (pedido_id,))
    
    # Actualizar estado del pedido
    cursor.execute("UPDATE pedidos SET estado = 'pagado' WHERE id = ?", (pedido_id,))
    
    conn.commit()
    conn.close()

def obtener_pedidos_usuario(usuario_id):
    """Obtiene todos los pedidos de un usuario"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM pedidos 
                      WHERE usuario_id = ? 
                      ORDER BY fecha DESC''', (usuario_id,))
    pedidos = cursor.fetchall()
    conn.close()
    return pedidos

def obtener_pedido_detalle(pedido_id):
    """Obtiene detalles de un pedido específico"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM pedido_detalle WHERE pedido_id = ?''', (pedido_id,))
    detalles = cursor.fetchall()
    conn.close()
    return detalles


# ========== RESTO DE FUNCIONES EXISTENTES ==========

def obtener_resumen_dashboard():
    """Resumen ejecutivo para el panel general"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    inicio_mes = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    
    # Ventas hoy
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM pedidos WHERE date(fecha) = ? AND estado IN ('pagado','entregado')", (hoy,))
    ventas_hoy = cursor.fetchone()
    
    # Ventas mes actual
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM pedidos WHERE date(fecha) >= ? AND estado IN ('pagado','entregado')", (inicio_mes,))
    ventas_mes = cursor.fetchone()
    
    # Pedidos pendientes
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE estado = 'pendiente'")
    pendientes = cursor.fetchone()[0]
    
    # Clientes nuevos hoy
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE date(fecha_registro) = ? AND rol = 'cliente'", (hoy,))
    clientes_hoy = cursor.fetchone()[0]
    
    # Total clientes
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'cliente'")
    total_clientes = cursor.fetchone()[0]
    
    # Últimos 10 pedidos
    cursor.execute('''SELECT p.id, p.factura, p.cliente_nombre, p.total, p.estado, p.metodo_pago, p.fecha 
                      FROM pedidos p ORDER BY p.fecha DESC LIMIT 10''')
    pedidos = cursor.fetchall()
    
    # Productos con stock crítico (top 10)
    cursor.execute('''SELECT id, nombre, codigo, cantidad, stock_minimo, precio 
                      FROM repuestos WHERE cantidad <= stock_minimo 
                      ORDER BY cantidad ASC LIMIT 10''')
    stock_critico = cursor.fetchall()
    
    # Comparativa mes anterior
    import calendar
    ahora = datetime.now()
    if ahora.month == 1:
        mes_anterior = datetime(ahora.year - 1, 12, 1)
    else:
        mes_anterior = datetime(ahora.year, ahora.month - 1, 1)
    inicio_mes_anterior = mes_anterior.strftime('%Y-%m-%d')
    fin_mes_anterior = datetime(ahora.year, ahora.month, 1).strftime('%Y-%m-%d')
    
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM pedidos WHERE date(fecha) >= ? AND date(fecha) < ? AND estado IN ('pagado','entregado')",
                   (inicio_mes_anterior, fin_mes_anterior))
    ventas_mes_anterior = cursor.fetchone()
    
    
    # Crecimiento
    ventas_mes_count = ventas_mes[0] or 0
    ventas_mes_valor = ventas_mes[1] or 0
    ventas_ant_count = ventas_mes_anterior[0] or 0
    ventas_ant_valor = ventas_mes_anterior[1] or 0
    crecimiento = round(((ventas_mes_valor - ventas_ant_valor) / ventas_ant_valor * 100), 1) if ventas_ant_valor > 0 else 0
    
    # Estadísticas generales
    cursor.execute("SELECT COUNT(*) FROM repuestos")
    total_productos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM repuestos WHERE cantidad <= stock_minimo")
    stock_critico_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(cantidad * precio) FROM repuestos")
    valor_inventario = cursor.fetchone()[0] or 0
    salud = round(((total_productos - stock_critico_count) / total_productos * 100), 1) if total_productos > 0 else 100
    
    conn.close()
    
    return {
        'total_productos': total_productos,
        'stock_critico': stock_critico_count,
        'valor_inventario': valor_inventario,
        'salud_inventario': salud,
        'ventas_hoy_count': ventas_hoy[0] or 0,
        'ventas_hoy_valor': ventas_hoy[1] or 0,
        'ventas_mes_count': ventas_mes_count,
        'ventas_mes_valor': ventas_mes_valor,
        'ventas_mes_anterior_count': ventas_ant_count,
        'ventas_mes_anterior_valor': ventas_ant_valor,
        'crecimiento_ventas': crecimiento,
        'pedidos_pendientes': pendientes,
        'clientes_nuevos_hoy': clientes_hoy,
        'total_clientes': total_clientes,
        'ultimos_pedidos': [{
            'id': p[0], 'factura': p[1], 'cliente': p[2],
            'total': p[3], 'estado': p[4], 'metodo_pago': p[5], 'fecha': p[6]
        } for p in pedidos],
        'stock_critico_lista': [{
            'id': p[0], 'nombre': p[1], 'codigo': p[2],
            'cantidad': p[3], 'stock_minimo': p[4], 'precio': p[5]
        } for p in stock_critico]
    }

def verificar_usuario(username, password):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, rol, password FROM usuarios WHERE username = ? AND activo = 1",
                   (username,))
    usuario = cursor.fetchone()
    if not usuario:
        conn.close()
        return None

    stored_hash = usuario[4]
    # Try bcrypt first
    try:
        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            conn.close()
            return (usuario[0], usuario[1], usuario[2], usuario[3])
    except ValueError:
        pass

    # Fallback: SHA256 (legacy) — migrate on success
    if stored_hash == hashlib.sha256(password.encode()).hexdigest():
        new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_hash, usuario[0]))
        conn.commit()
        conn.close()
        return (usuario[0], usuario[1], usuario[2], usuario[3])

    conn.close()
    return None

def obtener_usuario_por_id(user_id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, rol, email, telefono, direccion FROM usuarios WHERE id = ?", (user_id,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def obtener_usuario_por_email(email):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre FROM usuarios WHERE email = ? AND activo = 1", (email,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def guardar_token_reset(user_id, token):
    conn = obtener_conexion()
    cursor = conn.cursor()
    expiry = datetime.now().timestamp() + 3600
    cursor.execute("UPDATE usuarios SET reset_token = ?, reset_token_expiry = ? WHERE id = ?", (token, expiry, user_id))
    conn.commit()
    conn.close()

def verificar_token_reset(token):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE reset_token = ? AND reset_token_expiry > ?", (token, datetime.now().timestamp()))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def actualizar_password(user_id, nueva_password):
    conn = obtener_conexion()
    cursor = conn.cursor()
    nueva_password_hash = hash_password(nueva_password)
    cursor.execute("UPDATE usuarios SET password = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?", 
                   (nueva_password_hash, user_id))
    conn.commit()
    conn.close()

def obtener_todos_usuarios():
    conn = obtener_conexion()
    cursor = conn.cursor()
    # Incluir TODOS los usuarios (incluyendo admin)
    cursor.execute("SELECT id, username, nombre, email, rol, activo, fecha_registro, foto_perfil FROM usuarios ORDER BY id")
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios

def actualizar_usuario(user_id, nombre, email, rol, activo, foto_perfil=''):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''UPDATE usuarios 
        SET nombre = ?, email = ?, rol = ?, activo = ?, foto_perfil = ?
        WHERE id = ?''', (nombre, email, rol, activo, foto_perfil, user_id))
    conn.commit()
    conn.close()

def eliminar_usuario(user_id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ? AND username != 'admin'", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def obtener_categorias():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nombre, icono, descripcion, imagen FROM categorias WHERE activo = 1 ORDER BY nombre")
    cats = cursor.fetchall()
    conn.close()
    return [{'id': c[0], 'slug': c[1], 'nombre': c[2], 'icono': c[3], 'descripcion': c[4], 'imagen': c[5] or ''} for c in cats]

def obtener_todas_categorias():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nombre, icono, descripcion, imagen, activo FROM categorias ORDER BY activo DESC, nombre")
    cats = cursor.fetchall()
    conn.close()
    return [{'id': c[0], 'slug': c[1], 'nombre': c[2], 'icono': c[3], 'descripcion': c[4], 'imagen': c[5] or '', 'activo': c[6]} for c in cats]

def obtener_categoria_por_slug(slug):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nombre, icono, descripcion, imagen FROM categorias WHERE slug = ? AND activo = 1", (slug,))
    c = cursor.fetchone()
    conn.close()
    if c:
        return {'id': c[0], 'slug': c[1], 'nombre': c[2], 'icono': c[3], 'descripcion': c[4], 'imagen': c[5] or ''}
    return None

def crear_categoria(slug, nombre, icono, descripcion, imagen=''):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO categorias (slug, nombre, icono, descripcion, imagen) VALUES (?, ?, ?, ?, ?)",
                   (slug, nombre, icono, descripcion, imagen))
    conn.commit()
    conn.close()
    return cursor.lastrowid

def actualizar_categoria(id, slug, nombre, icono, descripcion, activo, imagen=''):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("UPDATE categorias SET slug = ?, nombre = ?, icono = ?, descripcion = ?, activo = ?, imagen = ? WHERE id = ?",
                   (slug, nombre, icono, descripcion, activo, imagen, id))
    conn.commit()
    conn.close()

def eliminar_categoria(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("UPDATE categorias SET activo = 0 WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def reactivar_categoria(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("UPDATE categorias SET activo = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def borrar_categoria(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("UPDATE repuestos SET categoria = 'Sin categoría' WHERE categoria = (SELECT nombre FROM categorias WHERE id = ?)", (id,))
    cursor.execute("DELETE FROM categorias WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def get_config(clave, default=''):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE clave = ?", (clave,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_config(clave, valor):
    conn = obtener_conexion()
    cursor = conn.cursor()
    # Guardar tipo actual antes de modificar
    cursor.execute("SELECT tipo FROM config WHERE clave = ?", (clave,))
    row = cursor.fetchone()
    tipo_actual = row[0] if row else 'text'
    cursor.execute("DELETE FROM config WHERE clave = ?", (clave,))
    cursor.execute("INSERT INTO config (clave, valor, tipo) VALUES (?, ?, ?)",
                   (clave, valor, tipo_actual))
    conn.commit()
    conn.close()

def obtener_foto_perfil(user_id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT foto_perfil FROM usuarios WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else ''

def actualizar_ultimo_acceso(user_id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def obtener_usuarios_activos(minutos=15):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, nombre, foto_perfil, ultimo_acceso, rol
        FROM usuarios
        WHERE activo = 1
          AND ultimo_acceso IS NOT NULL
          AND ultimo_acceso > datetime('now', '-' || ? || ' minutes')
        ORDER BY ultimo_acceso DESC
    """, (minutos,))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'username': r[1], 'nombre': r[2], 'foto_perfil': r[3] or '', 'ultimo_acceso': r[4], 'rol': r[5]} for r in rows]

def get_all_config():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM config")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

# ========== LOGS / ACTIVIDAD ==========

def log_actividad(usuario_id, usuario_nombre, accion, detalle='', ip=''):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO actividad (usuario_id, usuario_nombre, accion, detalle, ip) VALUES (?, ?, ?, ?, ?)",
                   (usuario_id, usuario_nombre, accion, detalle, ip))
    conn.commit()
    conn.close()

def obtener_actividad(limite=100, offset=0):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario_id, usuario_nombre, accion, detalle, ip, fecha FROM actividad ORDER BY fecha DESC LIMIT ? OFFSET ?",
                   (limite, offset))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'usuario_id': r[1], 'usuario_nombre': r[2], 'accion': r[3], 'detalle': r[4], 'ip': r[5], 'fecha': r[6]} for r in rows]

def contar_actividad():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM actividad")
    total = cursor.fetchone()[0]
    conn.close()
    return total

# ========== ROLES Y PERMISOS ==========

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
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, email, rol, activo, telefono, fecha_registro FROM usuarios ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'username': r[1], 'nombre': r[2], 'email': r[3], 'rol': r[4], 'activo': r[5], 'telefono': r[6], 'fecha_registro': r[7]} for r in rows]

def actualizar_usuario_rol(user_id, rol, activo=None):
    conn = obtener_conexion()
    cursor = conn.cursor()
    if activo is not None:
        cursor.execute("UPDATE usuarios SET rol = ?, activo = ? WHERE id = ?", (rol, 1 if activo else 0, user_id))
    else:
        cursor.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (rol, user_id))
    conn.commit()
    conn.close()

# ========== CACHE ==========

_cache = {}
_cache_ttl = {}

def cache_get(key):
    if key in _cache:
        if _cache_ttl.get(key, 0) > 0:
            from datetime import datetime as dt
            if (dt.now() - _cache[key]['ts']).total_seconds() > _cache_ttl[key]:
                del _cache[key]
                del _cache_ttl[key]
                return None
        return _cache[key]['data']
    return None

def cache_set(key, data, ttl=60):
    from datetime import datetime as dt
    _cache[key] = {'data': data, 'ts': dt.now()}
    _cache_ttl[key] = ttl

def cache_clear(pattern=None):
    global _cache, _cache_ttl
    if pattern:
        keys = [k for k in _cache if pattern in k]
        for k in keys:
            del _cache[k]
            if k in _cache_ttl: del _cache_ttl[k]
    else:
        _cache = {}
        _cache_ttl = {}

# ========== WEBHOOKS ==========

def crear_webhook(nombre, url, evento):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO webhooks (nombre, url, evento) VALUES (?, ?, ?)", (nombre, url, evento))
    conn.commit()
    conn.close()
    return cursor.lastrowid

def obtener_webhooks():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, url, evento, activo, ultima_respuesta, ultimo_error, fecha_creacion FROM webhooks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'nombre': r[1], 'url': r[2], 'evento': r[3], 'activo': r[4], 'ultima_respuesta': r[5], 'ultimo_error': r[6], 'fecha_creacion': r[7]} for r in rows]

def eliminar_webhook(id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM webhooks WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def webhook_log(webhook_id, evento, url, payload, respuesta, error=''):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO webhook_logs (webhook_id, evento, url, payload, respuesta, error) VALUES (?, ?, ?, ?, ?, ?)",
                   (webhook_id, evento, url, payload, respuesta, error))
    cursor.execute("UPDATE webhooks SET ultima_respuesta = ?, ultimo_error = ? WHERE id = ?", (respuesta, error, webhook_id))
    conn.commit()
    conn.close()

def obtener_webhook_logs(limite=50):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, webhook_id, evento, url, respuesta, error, fecha FROM webhook_logs ORDER BY fecha DESC LIMIT ?", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'webhook_id': r[1], 'evento': r[2], 'url': r[3], 'respuesta': r[4], 'error': r[5], 'fecha': r[6]} for r in rows]

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

