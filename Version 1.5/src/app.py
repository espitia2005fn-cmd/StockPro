from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, make_response, send_file, g
from werkzeug.utils import secure_filename, safe_join
from html import escape
import sqlite3
import os
from . import database as db
from . import db_adapter
from datetime import datetime, timedelta
from functools import wraps
import random
import secrets
import logging
logger = logging.getLogger(__name__)
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import shutil
import re

app = Flask(__name__, static_folder='Static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# CSRF protection
csrf = CSRFProtect(app)

# CORS configuration
from flask_cors import CORS
ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True,
     allow_headers=['Content-Type', 'X-CSRFToken'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://",
)

# Session security
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FORCE_HTTPS', '0') == '1'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Upload limits
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# Max length validations
MAX_LEN = {
    'username': 50, 'email': 100, 'nombre': 100, 'password': 128,
    'telefono': 20, 'direccion': 200, 'codigo': 50, 'producto_nombre': 100,
    'categoria': 50, 'ubicacion': 100, 'proveedor': 100,
    'descripcion': 500, 'caracteristicas': 500, 'especificaciones': 500,
    'garantia': 100, 'peso': 50, 'slug': 100, 'icono': 50,
    'webhook_url': 500, 'webhook_nombre': 100,
    'empresa_valor': 200, 'motivo': 200,
}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MIMES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}

# Configuración de correo para recuperación de contraseña
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get('MAIL_DEFAULT_SENDER', 'StockPro'), os.environ.get('MAIL_USERNAME', ''))

mail = Mail(app)

@app.template_filter('format_number')
def format_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)

@app.template_filter('nl2br')
def nl2br_filter(value):
    return escape(str(value)).replace('\n', '<br>')

ICONOS_SVG = {
    'engine': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/><path d="M8 12h8"/></svg>',
    'brake': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>',
    'suspension': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4v14a4 4 0 004 4h4a4 4 0 004-4V4"/><path d="M2 4h20"/><path d="M8 8h8"/><path d="M10 12h4"/></svg>',
    'electric': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/></svg>',
    'transmission': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><path d="M12 8v8M8 12h8"/><path d="M16 8l3-3M8 16l-3 3M8 8L5 5M16 16l3 3"/></svg>',
    'oil': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a8 8 0 00-8 8c0 5 4 10 8 12 4-2 8-7 8-12a8 8 0 00-8-8z"/><path d="M9 11a3 3 0 106 0c0-2-3-5-3-5s-3 3-3 5z"/></svg>',
    'tire': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><path d="M4 4l3 3M17 17l3 3M4 20l3-3M17 7l3-3"/></svg>',
    'body': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12H2l3-6h4l3 4h8v5h-4"/><circle cx="8" cy="17" r="2"/><circle cx="17" cy="17" r="2"/></svg>',
    'tools': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a5 5 0 00-7.07 7.07L4 17l3 3 3.63-3.63a5 5 0 007.07-7.07L17 9.3"/><path d="M17 9.3l3.03-3.03"/></svg>',
    'exhaust': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h4l2 3h4l2 4h5"/><path d="M18 14v3"/><circle cx="16" cy="18" r="2"/></svg>',
    'battery': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="12" rx="2"/><path d="M6 7V5h12v2"/><path d="M10 11h4M12 9v4"/></svg>',
    'filter': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>',
    'chain': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5h6a3 3 0 013 3v6a3 3 0 01-3 3h-6"/><path d="M12 19H6a3 3 0 01-3-3v-6a3 3 0 013-3h6"/><circle cx="12" cy="12" r="3"/></svg>',
    'lights': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19h6"/><path d="M10 23h4"/><path d="M12 2v2"/><path d="M12 6a7 7 0 00-7 7v2h14v-2a7 7 0 00-7-7z"/></svg>',
    'cooling': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v8M12 14v8"/><path d="M6 12H2M22 12h-4"/><path d="M7 7l4 4M13 13l4 4M7 17l4-4M13 11l4-4"/></svg>',
    'generic': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>',
}

@app.template_filter('cat_icon')
def cat_icon_filter(icon_name):
    if not icon_name:
        icon_name = 'generic'
    svg = ICONOS_SVG.get(icon_name.replace('bi-', ''), ICONOS_SVG.get('generic'))
    return svg

@app.context_processor
def inject_cart_count():
    carrito = session.get('carrito', [])
    return {'cart_count': len(carrito)}

@app.context_processor
def inject_categorias():
    try:
        cats = db.obtener_categorias()
    except Exception:
        cats = []
    return {'todas_categorias': cats}

@app.context_processor
def inject_config():
    try:
        cfg = db.get_all_config()
    except Exception:
        cfg = {}
    return {'config': cfg, 'ICONOS_SVG': ICONOS_SVG}

@app.before_request
def generar_nonce():
    g.csp_nonce = secrets.token_hex(16)

@app.context_processor
def inject_nonce():
    return {'csp_nonce': getattr(g, 'csp_nonce', secrets.token_hex(16))}



DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'stockpro.db')

def get_db():
    return db_adapter.get_connection()

def init_db():
    if db_adapter.USING_PG:
        from . import database_supabase as db_supabase
        db_supabase.crear_tablas()
    else:
        db.crear_tablas()

# ========== DECORADORES ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Inicia sesión para continuar', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Inicia sesión para continuar', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'administrador':
            flash('Acceso denegado', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ========== SEGURIDAD: CAPTCHA ==========
CAPTCHA_ENABLED = os.environ.get('CAPTCHA_ENABLED', '1') == '1'

def generar_captcha():
    if not CAPTCHA_ENABLED:
        session['_captcha'] = 0
        return ''
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(['+', '-'])
    if op == '+':
        rta = a + b
    else:
        a, b = max(a, b), min(a, b)
        rta = a - b
    session['_captcha'] = rta
    return f'{a} {op} {b}'

def validar_captcha(respuesta):
    if not CAPTCHA_ENABLED:
        return True
    try:
        expected = session.get('_captcha')
        if expected is None:
            return False
        result = int(respuesta) == expected
        session.pop('_captcha', None)
        return result
    except (ValueError, TypeError):
        session.pop('_captcha', None)
        return False

# ========== SEGURIDAD: INACTIVIDAD ==========
INACTIVIDAD_MAX_MINUTOS = 60

@app.before_request
def verificar_inactividad():
    user_id = session.get('user_id')
    if user_id and request.endpoint not in ('api_ping', 'api_logout_now', 'static', 'login'):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT ultimo_acceso FROM usuarios WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            try:
                ultimo = datetime.strptime(row[0][:19], '%Y-%m-%d %H:%M:%S')
                if datetime.now() - ultimo > timedelta(minutes=INACTIVIDAD_MAX_MINUTOS):
                    nombre = session.get('username', '')
                    db.log_actividad(user_id, nombre, 'Sesión expirada', f'Inactividad de más de {INACTIVIDAD_MAX_MINUTOS}min', request.remote_addr or '')
                    session.clear()
                    flash('Sesión expirada por inactividad', 'warning')
                    return redirect(url_for('login'))
            except ValueError:
                pass


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    nonce = getattr(g, 'csp_nonce', '')
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        f"script-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com 'nonce-{nonce}' 'strict-dynamic'; "
        "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response

# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found(e):
    return render_template('mantenimiento.html', error_code=404, error_msg='Página no encontrada'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('mantenimiento.html', error_code=500, error_msg='Error interno del servidor'), 500


# ========== RUTAS PÚBLICAS (sin login) ==========
@app.route('/')
def index():
    categorias = db.obtener_categorias()
    return render_template('index.html', categorias=categorias)

@app.route('/categoria/<slug>')
def categoria_dinamica(slug):
    cat = db.obtener_categoria_por_slug(slug)
    if not cat:
        return redirect(url_for('index'))
    return render_template('categoria.html', categoria=cat, slug=slug)

@app.route('/producto/<int:id>')
def ver_producto(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conn.close()
    if not producto:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('index'))
    return render_template('producto_detalle.html', producto=producto)

# ========== API PÚBLICAS ==========
@app.route('/api/inventario')
@limiter.limit("60 per minute", override_defaults=False)
def api_inventario():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos ORDER BY nombre")
    rows = cursor.fetchall()
    conn.close()
    inventario = []
    for row in rows:
        fecha_reg = row[15] if len(row) > 15 else None
        es_nuevo = False
        if fecha_reg:
            try:
                fecha_str = str(fecha_reg)
                fechan = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S') if ' ' in fecha_str else datetime.strptime(fecha_str, '%Y-%m-%d')
                es_nuevo = (datetime.now() - fechan).total_seconds() < 259200
            except Exception:
                import traceback; traceback.print_exc()
        inventario.append({
            'id': row[0], 'codigo': row[1], 'nombre': row[2],
            'categoria': row[3], 'cantidad': row[4], 'precio': row[5],
            'stock_minimo': row[6], 'ubicacion': row[7], 'proveedor': row[8],
            'imagen': row[9] if len(row) > 9 else None,
            'es_nuevo': es_nuevo
        })
    return jsonify(inventario)

@app.route('/api/inventario/categoria/<categoria>')
@limiter.limit("60 per minute", override_defaults=False)
def api_inventario_por_categoria(categoria):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos WHERE categoria = ? ORDER BY nombre", (categoria,))
    rows = cursor.fetchall()
    conn.close()
    inventario = []
    for row in rows:
        fecha_reg = row[15] if len(row) > 15 else None
        es_nuevo = False
        if fecha_reg:
            try:
                fecha_str = str(fecha_reg)
                fechan = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S') if ' ' in fecha_str else datetime.strptime(fecha_str, '%Y-%m-%d')
                es_nuevo = (datetime.now() - fechan).total_seconds() < 259200
            except Exception:
                import traceback; traceback.print_exc()
        inventario.append({
            'id': row[0], 'codigo': row[1], 'nombre': row[2],
            'categoria': row[3], 'cantidad': row[4], 'precio': row[5],
            'stock_minimo': row[6], 'ubicacion': row[7], 'proveedor': row[8],
            'imagen': row[9] if len(row) > 9 else None,
            'es_nuevo': es_nuevo
        })
    return jsonify(inventario)

@app.route('/api/estadisticas')
@limiter.limit("60 per minute", override_defaults=False)
def api_estadisticas():
    cached = db.cache_get('api_estadisticas')
    if cached: return jsonify(cached)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM repuestos")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM repuestos WHERE cantidad <= stock_minimo")
    critico = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(cantidad * precio) FROM repuestos")
    valor = cursor.fetchone()[0] or 0
    cursor.execute("SELECT categoria, SUM(cantidad) FROM repuestos GROUP BY categoria")
    categorias = cursor.fetchall()
    conn.close()
    salud = round(((total - critico) / total * 100), 1) if total > 0 else 100
    data = {
        'total_productos': total,
        'stock_critico': critico,
        'valor_total': valor,
        'salud_inventario': salud,
        'distribucion_categorias': {
            'categorias': [c[0] for c in categorias],
            'cantidades': [c[1] for c in categorias]
        }
    }
    db.cache_set('api_estadisticas', data, ttl=30)
    return jsonify(data)

# ========== CARRITO PÚBLICO ==========
@app.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', [])
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)

@app.route('/pago')
def pago():
    carrito = session.get('carrito', [])
    if not carrito:
        flash('Carrito vacío', 'warning')
        return redirect(url_for('ver_carrito'))
    return render_template('pago.html')

@app.route('/confirmar_pedido', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
def confirmar_pedido():
    carrito = session.get('carrito', [])
    if not carrito:
        flash('Carrito vacío', 'warning')
        return redirect(url_for('ver_carrito'))

    metodos_validos = {'mercadopago', 'nequi', 'pse', 'tarjeta', 'transferencia', 'contraentrega'}
    metodo_pago = request.form.get('metodo_pago', 'tarjeta')
    if metodo_pago not in metodos_validos:
        flash('Método de pago inválido', 'danger')
        return redirect(url_for('pago'))

    if session.get('user_id'):
        usuario_id = session.get('user_id')
        usuario = db.obtener_usuario_por_id(usuario_id)
        cliente_nombre = usuario[2] if usuario and len(usuario) > 2 else ''
        cliente_email = usuario[4] if usuario and len(usuario) > 4 else ''
        cliente_telefono = usuario[5] if usuario and len(usuario) > 5 else ''
        cliente_direccion = usuario[6] if usuario and len(usuario) > 6 else ''
    else:
        usuario_id = None
        cliente_nombre = request.form.get('cliente_nombre', '').strip()
        cliente_email = request.form.get('cliente_email', '').strip()
        cliente_telefono = request.form.get('cliente_telefono', '').strip()
        cliente_direccion = request.form.get('cliente_direccion', '').strip()

        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', cliente_email):
            flash('Correo electrónico inválido', 'danger')
            return redirect(url_for('pago'))

        if len(cliente_nombre) > MAX_LEN['nombre'] or \
           len(cliente_telefono) > MAX_LEN['telefono'] or \
           len(cliente_direccion) > MAX_LEN['direccion']:
            flash('Uno o más campos superan la longitud máxima permitida', 'danger')
            return redirect(url_for('pago'))

    if not cliente_nombre or not cliente_email:
        flash('Por favor complete sus datos de contacto', 'danger')
        return redirect(url_for('pago'))

    # Recalcular precios desde la BD
    conn = get_db()
    cursor = conn.cursor()
    subtotal = 0
    carrito_validado = []
    for item in carrito:
        cursor.execute("SELECT id, nombre, precio, cantidad, imagen, categoria FROM repuestos WHERE id = ?", (item['id'],))
        producto = cursor.fetchone()
        if not producto:
            conn.close()
            flash(f'Producto "{item.get("nombre", "Desconocido")}" no disponible', 'danger')
            return redirect(url_for('ver_carrito'))
        if producto[3] < item['cantidad']:
            conn.close()
            flash(f'Stock insuficiente para {producto[1]}. Disponible: {producto[3]}', 'danger')
            return redirect(url_for('ver_carrito'))
        precio_real = producto[2]
        cantidad = item['cantidad']
        subtotal += precio_real * cantidad
        carrito_validado.append({
            'id': producto[0], 'nombre': producto[1], 'precio': precio_real,
            'cantidad': cantidad, 'imagen': producto[4] or '', 'categoria': producto[5] or ''
        })
    conn.close()

    iva = subtotal * 0.19
    total = subtotal + iva

    pedido_id, factura = db.crear_pedido(
        usuario_id,
        cliente_nombre,
        cliente_email,
        cliente_telefono,
        cliente_direccion,
        carrito_validado,
        subtotal,
        iva,
        total,
        metodo_pago,
    )

    # Pasar el nombre del cliente logueado o None para invitado
    nombre_cliente = session.get('nombre') if session.get('user_id') else None
    db.confirmar_pago(pedido_id, nombre_cliente)

    # Log de actividad
    ip = request.remote_addr or ''
    if session.get('user_id'):
        db.log_actividad(session['user_id'], session.get('nombre'), 'Pedido realizado',
                         f'Pedido #{factura} por ${total:,.0f}', ip)
    else:
        db.log_actividad(0, 'Invitado', 'Pedido invitado',
                         f'Pedido #{factura} por ${total:,.0f} - {cliente_nombre}', ip)

    session['ultimo_pedido'] = {
        'factura': factura,
        'total': total,
        'metodo': metodo_pago,
    }
    session['ultima_compra'] = {
        'factura': factura,
        'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'productos': carrito_validado,
        'subtotal': subtotal,
        'iva': iva,
        'total': total,
        'cliente': cliente_nombre,
    }
    session['carrito'] = []

    flash(f'Pedido #{factura} confirmado exitosamente', 'success')

    return render_template('confirmacion_pedido.html', factura=factura, total=total, metodo=metodo_pago)

@app.route('/api/pedido_detalle/<int:id>')
@login_required
def api_pedido_detalle(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT usuario_id, subtotal, iva, total FROM pedidos WHERE id = ?''', (id,))
    pedido = cursor.fetchone()
    if not pedido:
        conn.close()
        return jsonify({'error': 'No encontrado'}), 404

    # Verificar que el pedido pertenece al usuario (o es admin)
    usuario_id_pedido = pedido[0]
    user_id = session.get('user_id')
    if session.get('rol') != 'administrador':
        if not usuario_id_pedido or usuario_id_pedido != user_id:
            conn.close()
            return jsonify({'error': 'No autorizado'}), 403

    cursor.execute('''SELECT codigo, nombre, cantidad, precio, subtotal FROM pedido_detalle WHERE pedido_id = ?''', (id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify({
        'detalles': [{'codigo': r[0], 'nombre': r[1], 'cantidad': r[2], 'precio': r[3], 'subtotal': r[4]} for r in rows],
        'subtotal': pedido[1],
        'iva': pedido[2],
        'total': pedido[3]
    })

@app.route('/recibo')
def recibo():
    compra = session.get('ultima_compra', None)
    if not compra:
        flash('No hay compra reciente', 'warning')
        return redirect(url_for('ver_carrito'))
    return render_template('recibo.html', compra=compra)

@app.route('/finalizar_compra')
def finalizar_compra():
    flash('Usa el formulario de pago para confirmar tu pedido', 'info')
    return redirect(url_for('pago'))

@app.route('/api/carrito/ver')
def carrito_ver():
    carrito = session.get('carrito', [])
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    total_items = sum(item['cantidad'] for item in carrito)
    return jsonify({'carrito': carrito, 'total': total, 'total_items': total_items})

@app.route('/api/carrito/agregar', methods=['POST'])
@limiter.limit("20 per minute", override_defaults=False)
def carrito_agregar():
    data = request.get_json()
    producto_id = data.get('id')
    cantidad = data.get('cantidad', 1)

    if not producto_id or not isinstance(cantidad, (int, float)) or cantidad < 1:
        return jsonify({'success': False, 'error': 'Datos inválidos'}), 400
    cantidad = int(cantidad)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, precio, imagen, categoria FROM repuestos WHERE id = ?", (producto_id,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404

    producto_id = producto[0]
    nombre = producto[1]
    precio = producto[2]
    imagen = producto[3] or ''
    categoria = producto[4] or ''

    carrito = session.get('carrito', [])
    for item in carrito:
        if item['id'] == producto_id:
            item['cantidad'] += cantidad
            session['carrito'] = carrito
            return jsonify({'success': True, 'mensaje': f'Cantidad actualizada: {nombre}'})
    carrito.append({'id': producto_id, 'nombre': nombre, 'precio': precio, 'cantidad': cantidad, 'imagen': imagen, 'categoria': categoria})
    session['carrito'] = carrito
    return jsonify({'success': True, 'mensaje': f'Agregado: {nombre}'})

@app.route('/api/carrito/actualizar', methods=['POST'])
@limiter.limit("20 per minute", override_defaults=False)
def carrito_actualizar():
    data = request.get_json()
    producto_id = data.get('id')
    if not isinstance(producto_id, (int, float)):
        return jsonify({'success': False, 'error': 'ID inválido'}), 400
    cantidad = int(data.get('cantidad', 1))
    if cantidad < 0:
        return jsonify({'success': False, 'error': 'Cantidad inválida'}), 400
    carrito = session.get('carrito', [])
    for i, item in enumerate(carrito):
        if item['id'] == producto_id:
            if cantidad <= 0:
                carrito.pop(i)
            else:
                item['cantidad'] = cantidad
            break
    session['carrito'] = carrito
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return jsonify({'success': True, 'total': total})

@app.route('/api/carrito/eliminar', methods=['POST'])
@limiter.limit("20 per minute", override_defaults=False)
def carrito_eliminar():
    data = request.get_json()
    producto_id = data.get('id')
    if not isinstance(producto_id, (int, float)):
        return jsonify({'success': False, 'error': 'ID inválido'}), 400
    carrito = session.get('carrito', [])
    carrito = [item for item in carrito if item['id'] != producto_id]
    session['carrito'] = carrito
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return jsonify({'success': True, 'total': total})

@app.route('/api/carrito/vaciar', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
def carrito_vaciar():
    session['carrito'] = []
    return jsonify({'success': True})

@app.route('/api/carrito/verificar_stock', methods=['POST'])
@limiter.limit("20 per minute", override_defaults=False)
def verificar_stock_carrito():
    """Verifica que todos los productos en el carrito tengan stock suficiente"""
    carrito = session.get('carrito', [])
    if not carrito:
        return jsonify({'success': True, 'stock_ok': True})
    
    conn = get_db()
    cursor = conn.cursor()
    problemas = []
    
    for item in carrito:
        cursor.execute("SELECT cantidad, nombre FROM repuestos WHERE id = ?", (item['id'],))
        producto = cursor.fetchone()
        if not producto:
            problemas.append({
                'nombre': item.get('nombre', 'Desconocido'),
                'solicitado': item.get('cantidad', 0),
                'disponible': 0,
                'error': 'Producto no encontrado'
            })
        elif producto[0] < item.get('cantidad', 0):
            problemas.append({
                'nombre': producto[1] or item.get('nombre', 'Desconocido'),
                'solicitado': item.get('cantidad', 0),
                'disponible': producto[0],
                'error': 'Stock insuficiente'
            })
    conn.close()
    
    if problemas:
        return jsonify({'success': False, 'stock_ok': False, 'problemas': problemas})
    return jsonify({'success': True, 'stock_ok': True})

# ========== DASHBOARD CLIENTE ==========
@app.route('/cliente/dashboard')
def cliente_dashboard():
    if 'user_id' not in session:
        flash('Inicia sesión para acceder', 'warning')
        return redirect(url_for('login'))
    if session.get('rol') != 'cliente' and session.get('rol') != 'administrador':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('index'))
    return render_template('cliente_dashboard.html', usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/cliente/pedidos')
def cliente_pedidos():
    if 'user_id' not in session:
        flash('Inicia sesión para acceder', 'warning')
        return redirect(url_for('login'))
    return render_template('cliente_pedidos.html', usuario=session.get('nombre'))

@app.route('/cliente/perfil')
def cliente_perfil():
    if 'user_id' not in session:
        flash('Inicia sesión para acceder', 'warning')
        return redirect(url_for('login'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT email, telefono, direccion FROM usuarios WHERE id = ?", (session['user_id'],))
        usuario = cursor.fetchone()
        conn.close()
        
        # Datos por defecto si no hay
        if usuario:
            datos = {
                'email': usuario[0] or '',
                'telefono': usuario[1] or '',
                'direccion': usuario[2] or ''
            }
        else:
            datos = {'email': '', 'telefono': '', 'direccion': ''}
        
        return render_template('cliente_perfil.html', usuario=datos)
    
    except Exception as e:
        print(f"ERROR en perfil: {e}")
        flash('Error al cargar el perfil', 'danger')
        return redirect(url_for('cliente_dashboard'))

@app.route('/cliente/actualizar_perfil', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
def actualizar_perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    email = request.form.get('email')
    telefono = request.form.get('telefono', '')
    direccion = request.form.get('direccion', '')
    nueva_password = request.form.get('nueva_password', '')

    if len(nombre or '') > MAX_LEN['nombre'] or len(email or '') > MAX_LEN['email'] or \
       len(telefono or '') > MAX_LEN['telefono'] or len(direccion or '') > MAX_LEN['direccion']:
        flash('Uno o más campos superan la longitud máxima permitida', 'danger')
        return redirect(url_for('cliente_perfil'))

    conn = get_db()
    cursor = conn.cursor()

    foto_perfil = session.get('foto_perfil', '')
    if 'foto_perfil' in request.files:
        file = request.files['foto_perfil']
        if file and file.filename:
            saved = guardar_imagen(file)
            if saved:
                foto_perfil = saved

    if nueva_password:
        password_hash = db.hash_password(nueva_password)
        cursor.execute("UPDATE usuarios SET nombre = ?, email = ?, telefono = ?, direccion = ?, foto_perfil = ?, password = ? WHERE id = ?",
                       (nombre, email, telefono, direccion, foto_perfil, password_hash, session['user_id']))
        flash('Perfil actualizado. Tu contraseña ha sido cambiada.', 'success')
    else:
        cursor.execute("UPDATE usuarios SET nombre = ?, email = ?, telefono = ?, direccion = ?, foto_perfil = ? WHERE id = ?",
                       (nombre, email, telefono, direccion, foto_perfil, session['user_id']))
        flash('Perfil actualizado correctamente', 'success')

    session['nombre'] = nombre
    session['foto_perfil'] = foto_perfil
    conn.commit()
    conn.close()

    return redirect(url_for('cliente_perfil'))

@app.route('/api/cliente/pedidos')
def api_cliente_pedidos():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''SELECT id, factura, fecha, subtotal, iva, total, metodo_pago, estado
                      FROM pedidos WHERE usuario_id = ? ORDER BY fecha DESC''', (session['user_id'],))
    pedidos = cursor.fetchall()

    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM pedidos WHERE usuario_id = ? AND estado = 'pagado'", (session['user_id'],))
    total_gastado = cursor.fetchone()[0] or 0

    cursor.execute("SELECT fecha_registro FROM usuarios WHERE id = ?", (session['user_id'],))
    fecha_registro = cursor.fetchone()

    conn.close()

    pedidos_list = []
    for p in pedidos:
        pedidos_list.append({
            'id': p[0],
            'factura': p[1],
            'fecha': p[2],
            'subtotal': p[3],
            'iva': p[4],
            'total': p[5],
            'metodo_pago': p[6],
            'estado': p[7]
        })

    fecha_desde = fecha_registro[0].split('-')[0] if fecha_registro else '2025'

    return jsonify({
        'pedidos': pedidos_list,
        'total_pedidos': len(pedidos_list),
        'total_gastado': total_gastado,
        'cliente_desde': fecha_desde
    })

# ========== LOGIN Y RECUPERACIÓN ==========
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", override_defaults=False)
def login():
    if request.method == 'POST':
        if not validar_captcha(request.form.get('_captcha', '')):
            flash(' Código de verificación incorrecto', 'danger')
            captcha_q = generar_captcha()
            return render_template('login.html', captcha_q=captcha_q)
        username = request.form.get('username')
        password = request.form.get('password')

        # Bloqueo de cuenta por intentos fallidos
        failed, locked_until = db.obtener_bloqueo_usuario(username)
        if locked_until is not None:
            try:
                if isinstance(locked_until, str):
                    lock_time = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S')
                else:
                    lock_time = locked_until
                if datetime.now() < lock_time:
                    flash(' Cuenta bloqueada por múltiples intentos. Intente nuevamente en 15 minutos.', 'danger')
                    captcha_q = generar_captcha()
                    return render_template('login.html', captcha_q=captcha_q)
            except Exception:
                pass

        usuario = db.verificar_usuario(username, password)
        if usuario:
            db.resetear_intentos_fallidos(username)
            session.clear()
            session['user_id'] = usuario[0]
            session['username'] = usuario[1]
            session['nombre'] = usuario[2]
            session['rol'] = usuario[3]
            foto = db.obtener_foto_perfil(usuario[0])
            if foto:
                session['foto_perfil'] = foto
            db.actualizar_ultimo_acceso(usuario[0])
            ip = request.remote_addr or ''
            db.log_actividad(usuario[0], usuario[1], 'Inicio de sesión', f'Usuario {usuario[1]} inició sesión', ip)
            flash(f'Bienvenido {usuario[2]}', 'success')
            if usuario[3] == 'administrador':
                return redirect(url_for('dashboard'))
            elif usuario[3] == 'cliente':
                return redirect(url_for('cliente_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash(' Usuario o contraseña incorrectos', 'danger')
            db.incrementar_intentos_fallidos(username)
    captcha_q = generar_captcha()
    return render_template('login.html', captcha_q=captcha_q)

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    username = session.get('username')
    if user_id:
        ip = request.remote_addr or ''
        db.log_actividad(user_id, username, 'Cierre de sesión', f'Usuario {username} cerró sesión', ip)
    session.clear()
    flash(' Sesión cerrada', 'success')
    return redirect(url_for('login'))

@app.route('/recuperar_password', methods=['GET', 'POST'])
@limiter.limit("5 per minute", override_defaults=False)
def recuperar_password():
    if request.method == 'POST':
        if not validar_captcha(request.form.get('_captcha', '')):
            flash(' Código de verificación incorrecto', 'danger')
            captcha_q = generar_captcha()
            return render_template('recuperar_pass.html', captcha_q=captcha_q)
        email = request.form.get('email')
        usuario = db.obtener_usuario_por_email(email)
        
        if usuario:
            token = secrets.token_urlsafe(32)
            db.guardar_token_reset(usuario[0], token)
            reset_url = url_for('reset_password', token=token, _external=True)
            
            try:
                msg = Message('Recuperación de contraseña - StockPro',
                              recipients=[email])
                msg.body = f'''
Haz clic en el siguiente enlace para restablecer tu contraseña:

{reset_url}

Si no solicitaste este cambio, ignora este mensaje.
El enlace expirará en 1 hora.
'''
                mail.send(msg)
                flash('Correo enviado. Revisa tu bandeja de entrada.', 'success')
            except Exception as e:
                print(f"Error al enviar email: {e}")
                print(f"[DEBUG] Enlace de recuperacion: {reset_url}")
                flash(' No se pudo enviar el correo. Revisa la consola del servidor.', 'danger')
        else:
            flash('Si el correo está registrado, recibirás un enlace de recuperación.', 'info')
        
        return redirect(url_for('login'))
    
    captcha_q = generar_captcha()
    return render_template('recuperar_pass.html', captcha_q=captcha_q)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per minute", override_defaults=False)
def reset_password(token):
    usuario = db.verificar_token_reset(token)
    if not usuario:
        flash(' Enlace inválido o expirado', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nueva = request.form.get('password')
        if nueva and len(nueva) >= 8:
            db.actualizar_password(usuario[0], nueva)
            flash(' Contraseña actualizada correctamente', 'success')
            return redirect(url_for('login'))
        flash(' La contraseña debe tener al menos 8 caracteres', 'danger')
    
    return render_template('cambiar_pass.html', token=token)

# ========== RUTAS PÚBLICAS DE REGISTRO ==========
@app.route('/registro', methods=['GET', 'POST'])
@limiter.limit("5 per minute", override_defaults=False)
def registro_cliente():
    """Registro público para clientes"""
    if request.method == 'POST':
        if not validar_captcha(request.form.get('_captcha', '')):
            flash(' Código de verificación incorrecto', 'danger')
            captcha_q = generar_captcha()
            return render_template('registro_cliente.html', captcha_q=captcha_q)
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        username = request.form.get('username')
        telefono = request.form.get('telefono', '')
        direccion = request.form.get('direccion', '')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not nombre or not email or not username or not password:
            flash('Los campos marcados con * son obligatorios', 'danger')
            return redirect(url_for('registro_cliente'))

        if len(nombre) > MAX_LEN['nombre'] or len(email) > MAX_LEN['email'] or \
           len(username) > MAX_LEN['username'] or len(password) > MAX_LEN['password'] or \
           len(telefono) > MAX_LEN['telefono'] or len(direccion) > MAX_LEN['direccion']:
            flash('Uno o más campos superan la longitud máxima permitida', 'danger')
            return redirect(url_for('registro_cliente'))

        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('registro_cliente'))

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'danger')
            return redirect(url_for('registro_cliente'))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            flash('El usuario o email ya está registrado', 'danger')
            conn.close()
            return redirect(url_for('registro_cliente'))

        password_hash = db.hash_password(password)

        cursor.execute('''INSERT INTO usuarios (username, password, nombre, email, rol, activo, telefono, direccion)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (username, password_hash, nombre, email, 'cliente', 1, telefono, direccion))

        conn.commit()
        conn.close()

        flash('Cuenta creada exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    captcha_q = generar_captcha()
    return render_template('registro_cliente.html', captcha_q=captcha_q)

# ========== RUTAS PRIVADAS (ADMIN) ==========
@app.route('/dashboard')
@admin_required
def dashboard():
    return render_template('dashboard.html', usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/registro')
@admin_required
def admin_registro():
    categorias = db.obtener_categorias()
    return render_template('registro.html', usuario=session.get('nombre'), rol=session.get('rol'), categorias=categorias)

@app.route('/movimientos')
@admin_required
def movimientos():
    categorias = db.obtener_categorias()
    return render_template('movimientos.html', categorias=categorias, usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/analisis')
@admin_required
def analisis():
    return render_template('analysis.html', usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    usuarios = db.obtener_todos_usuarios()
    return render_template('admin_usuarios.html', usuarios=usuarios, usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/usuario/editar/<int:id>', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_usuario_editar(id):
    try:
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        rol = request.form.get('rol')
        activo = 1 if request.form.get('activo') == 'on' else 0
        foto_perfil = ''
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename:
                saved = guardar_imagen(file)
                if saved:
                    foto_perfil = saved
        db.actualizar_usuario(id, nombre, email, rol, activo, foto_perfil)
        flash(' Usuario actualizado', 'success')
    except Exception as e:
        app.logger.error(f"Error al actualizar usuario: {e}")
        flash('Error al actualizar usuario', 'danger')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/eliminar/<int:id>', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_usuario_eliminar(id):
    if db.eliminar_usuario(id):
        flash(' Usuario eliminado', 'success')
    else:
        flash(' No se puede eliminar al admin', 'danger')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/cambiar_contrasena/<int:id>', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_usuario_cambiar_contrasena(id):
    nueva = request.form.get('nueva_contrasena')
    if nueva and len(nueva) >= 8:
        password_hash = db.hash_password(nueva)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (password_hash, id))
        conn.commit()
        conn.close()
        flash(' Contraseña actualizada', 'success')
    else:
        flash(' Mínimo 8 caracteres', 'danger')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/productos')
@admin_required
def admin_productos():
    categorias = db.obtener_categorias()
    return render_template('admin_productos.html', usuario=session.get('nombre'), rol=session.get('rol'), categorias=categorias)

@app.route('/admin/configuracion', methods=['GET', 'POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_configuracion():
    if request.method == 'POST':
        for key in ['whatsapp', 'facebook', 'instagram', 'youtube', 'tiktok',
                     'empresa_nombre', 'empresa_email', 'empresa_telefono',
                     'empresa_direccion', 'empresa_horarios', 'anio_copyright']:
            val = request.form.get(key, '')
            if len(val) > MAX_LEN['empresa_valor']:
                flash(f'El campo {key} supera la longitud máxima', 'danger')
                return redirect(url_for('admin_configuracion'))
            db.set_config(key, val)
        if 'empresa_logo' in request.files:
            file = request.files['empresa_logo']
            if file and file.filename:
                saved = guardar_imagen(file)
                if saved:
                    db.set_config('empresa_logo', saved)
        flash('Configuracion guardada', 'success')
        return redirect(url_for('admin_configuracion'))
    config = db.get_all_config()
    return render_template('admin_configuracion.html', config=config, usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/categorias')
@admin_required
def admin_categorias():
    categorias = db.obtener_todas_categorias()
    return render_template('admin_categorias.html', categorias=categorias, usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/categoria/crear', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_categoria_crear():
    slug = request.form.get('slug', '').strip().lower().replace(' ', '_')
    nombre = request.form.get('nombre', '').strip()
    icono = request.form.get('icono', 'generic').strip()
    descripcion = request.form.get('descripcion', '').strip()
    imagen = ''
    if 'imagen' in request.files:
        file = request.files['imagen']
        if file and file.filename:
            saved = guardar_imagen(file)
            if saved:
                imagen = saved
    if len(slug) > MAX_LEN['slug'] or len(nombre) > MAX_LEN['nombre'] or \
       len(icono) > MAX_LEN['icono'] or len(descripcion) > MAX_LEN['descripcion']:
        flash('Uno o más campos superan la longitud máxima permitida', 'danger')
        return redirect(url_for('admin_categorias'))
    if not slug or not nombre:
        flash('Slug y nombre son obligatorios', 'danger')
        return redirect(url_for('admin_categorias'))
    try:
        db.crear_categoria(slug, nombre, icono, descripcion, imagen)
        flash(f'Categoria "{nombre}" creada', 'success')
    except (sqlite3.IntegrityError, db_adapter.IntegrityError):
        flash(f'El slug "{slug}" ya existe', 'danger')
    return redirect(url_for('admin_categorias'))

@app.route('/admin/categoria/editar/<int:id>', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_categoria_editar(id):
    slug = request.form.get('slug', '').strip().lower().replace(' ', '_')
    nombre = request.form.get('nombre', '').strip()
    icono = request.form.get('icono', 'generic').strip()
    descripcion = request.form.get('descripcion', '').strip()
    activo = 1 if request.form.get('activo') else 0
    imagen = request.form.get('imagen_existente', '')
    if 'imagen' in request.files:
        file = request.files['imagen']
        if file and file.filename:
            saved = guardar_imagen(file)
            if saved:
                imagen = saved
    db.actualizar_categoria(id, slug, nombre, icono, descripcion, activo, imagen)
    flash('Categoria actualizada', 'success')
    return redirect(url_for('admin_categorias'))

@app.route('/admin/categoria/eliminar/<int:id>', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_categoria_eliminar(id):
    db.eliminar_categoria(id)
    flash('Categoria desactivada', 'success')
    return redirect(url_for('admin_categorias'))

@app.route('/admin/categoria/reactivar/<int:id>', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_categoria_reactivar(id):
    db.reactivar_categoria(id)
    return jsonify({'success': True})

@app.route('/admin/categoria/borrar/<int:id>', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_categoria_borrar(id):
    db.borrar_categoria(id)
    return jsonify({'success': True})

@app.route('/api/categorias')
def api_categorias():
    categorias = db.obtener_categorias()
    return jsonify(categorias)

@app.route('/admin/clientes')
@admin_required
def admin_clientes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, username, nombre, email, telefono, direccion, activo, fecha_registro, foto_perfil,
                      (SELECT COALESCE(SUM(total), 0) FROM pedidos WHERE usuario_id = usuarios.id AND estado = 'pagado') as total_gastado,
                      (SELECT COUNT(*) FROM pedidos WHERE usuario_id = usuarios.id) as total_pedidos
                      FROM usuarios WHERE rol = 'cliente' ORDER BY fecha_registro DESC''')
    clientes = cursor.fetchall()
    conn.close()
    return render_template('admin_clientes.html', clientes=clientes, usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/api/admin/cliente/pedidos/<int:id>')
@admin_required
def api_admin_cliente_pedidos(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, factura, fecha, total, metodo_pago, estado 
                      FROM pedidos WHERE usuario_id = ? ORDER BY fecha DESC''', (id,))
    pedidos = cursor.fetchall()
    conn.close()
    
    pedidos_list = []
    for p in pedidos:
        pedidos_list.append({
            'id': p[0],
            'factura': p[1],
            'fecha': p[2],
            'total': p[3],
            'metodo_pago': p[4],
            'estado': p[5]
        })
    
    return jsonify({'pedidos': pedidos_list})

@app.route('/admin/cliente/editar/<int:id>', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def admin_cliente_editar(id):
    try:
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono', '')
        direccion = request.form.get('direccion', '')
        activo = 1 if request.form.get('activo') == 'on' else 0
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''UPDATE usuarios 
                          SET nombre = ?, email = ?, telefono = ?, direccion = ?, activo = ?
                          WHERE id = ? AND rol = 'cliente' ''',
                       (nombre, email, telefono, direccion, activo, id))
        conn.commit()
        conn.close()
        
        flash('Cliente actualizado correctamente', 'success')
    except Exception as e:
        app.logger.error(f"Error al actualizar cliente: {e}")
        flash('Error al actualizar cliente', 'danger')
    
    return redirect(url_for('admin_clientes'))

@app.route('/admin/cliente/eliminar/<int:id>', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_cliente_eliminar(id):
    try:
        db.eliminar_usuario(id)
        flash('Cliente eliminado correctamente', 'success')
    except Exception as e:
        app.logger.error(f"Error al eliminar cliente: {e}")
        flash('Error al eliminar cliente', 'danger')
    return redirect(url_for('admin_clientes'))

@app.route('/admin/ordenes')
@admin_required
def admin_ordenes():
    conn = get_db()
    cursor = conn.cursor()
    cliente_id = request.args.get('cliente')
    if cliente_id:
        cursor.execute('''SELECT p.id, p.factura, p.cliente_nombre, p.total, p.metodo_pago, p.estado, p.fecha, p.usuario_id, u.nombre
                          FROM pedidos p LEFT JOIN usuarios u ON p.usuario_id = u.id
                          WHERE p.usuario_id = ? ORDER BY p.fecha DESC''', (cliente_id,))
    else:
        cursor.execute('''SELECT p.id, p.factura, p.cliente_nombre, p.total, p.metodo_pago, p.estado, p.fecha, p.usuario_id, u.nombre
                          FROM pedidos p LEFT JOIN usuarios u ON p.usuario_id = u.id
                          ORDER BY p.fecha DESC LIMIT 200''')
    pedidos = cursor.fetchall()
    conn.close()
    return render_template('admin_ordenes.html', pedidos=pedidos, usuario=session.get('nombre'), rol=session.get('rol'))

# ========== CRUD PRODUCTOS ==========
@app.route('/api/producto/<int:id>', methods=['GET'])
@admin_required
def api_obtener_producto(id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo, nombre, categoria, cantidad, precio, stock_minimo, ubicacion, proveedor, imagen, descripcion, caracteristicas, especificaciones, garantia, peso, costo FROM repuestos WHERE id = ?", (id,))
        producto = cursor.fetchone()
        conn.close()
        if producto:
            return jsonify({
                'id': producto[0],
                'codigo': producto[1],
                'nombre': producto[2],
                'categoria': producto[3],
                'cantidad': producto[4],
                'precio': producto[5],
                'stock_minimo': producto[6],
                'ubicacion': producto[7] or '',
                'proveedor': producto[8] or '',
                'imagen': producto[9] or '',
                'descripcion': producto[10] or '',
                'caracteristicas': producto[11] or '',
                'especificaciones': producto[12] or '',
                'garantia': producto[13] or '',
                'peso': producto[14] or '',
                'costo': producto[15] or 0
            })
        return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        app.logger.error(f"Error en /api/producto/<id> GET: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/producto/<int:id>', methods=['PUT'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_actualizar_producto(id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT cantidad, precio, nombre FROM repuestos WHERE id = ?", (id,))
        viejo = cursor.fetchone()
        if not viejo:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        cantidad_vieja = viejo[0]
        precio = viejo[1]
        nombre = viejo[2]
        cantidad_nueva = max(0, int(data.get('cantidad', cantidad_vieja)))
        data['precio'] = max(0, float(data.get('precio', precio)))
        data['stock_minimo'] = max(0, int(data.get('stock_minimo', 0)))
        
        cursor.execute('''UPDATE repuestos 
            SET codigo = ?, nombre = ?, categoria = ?, cantidad = ?, precio = ?, stock_minimo = ?, ubicacion = ?, proveedor = ?, imagen = ?,
            descripcion = ?, caracteristicas = ?, especificaciones = ?, garantia = ?, peso = ?, costo = ?
            WHERE id = ?''',
            (data['codigo'], data['nombre'], data['categoria'], cantidad_nueva,
             data['precio'], data['stock_minimo'], data['ubicacion'], data['proveedor'],
             data.get('imagen', ''), data.get('descripcion', ''), data.get('caracteristicas', ''),
             data.get('especificaciones', ''), data.get('garantia', ''), data.get('peso', ''),
             data.get('costo', 0), id))
        
        diferencia = cantidad_nueva - cantidad_vieja
        if diferencia != 0:
            tipo = 'ENTRADA' if diferencia > 0 else 'SALIDA'
            motivo = f'Edición manual: {nombre} - Stock {cantidad_vieja} → {cantidad_nueva}'
            cursor.execute('''INSERT INTO movimientos 
                (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (id, tipo, abs(diferencia), precio, motivo, session.get('username', 'admin')))
        
        conn.commit()
        conn.close()

        ip = request.remote_addr or ''
        db.log_actividad(session['user_id'], session.get('nombre'), 'Producto editado',
                         f'ID: {id} - {data.get("nombre", "")} - Stock: {cantidad_vieja}→{cantidad_nueva}', ip)

        return jsonify({'success': True, 'mensaje': 'Producto actualizado'})
    except Exception as e:
        app.logger.error(f"Error en /api/producto/<id> PUT: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ========== API ADMIN ==========
@app.route('/api/estadisticas/admin')
@admin_required
def api_estadisticas_admin():
    return api_estadisticas()

@app.route('/api/dashboard')
@app.route('/api/dashboard/resumen')
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_dashboard_resumen():
    """Resumen ejecutivo para el Panel General"""
    cached = db.cache_get('api_dashboard')
    if cached: return jsonify(cached)
    resumen = db.obtener_resumen_dashboard()

    # Ventas mensuales para el chart
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', fecha) as mes, COUNT(*), COALESCE(SUM(total),0)
        FROM pedidos WHERE estado IN ('pagado','entregado')
        AND fecha >= date('now', '-11 months')
        GROUP BY strftime('%Y-%m', fecha) ORDER BY mes
    """)
    ventas_mensuales = cursor.fetchall()
    meses = [r[0] for r in ventas_mensuales]
    ventas_data = [r[2] for r in ventas_mensuales]

    # Categorías para el doughnut chart (solo stock positivo)
    cursor.execute("SELECT categoria, SUM(cantidad) FROM repuestos GROUP BY categoria HAVING SUM(cantidad) > 0 ORDER BY SUM(cantidad) DESC")
    categorias = cursor.fetchall()
    categorias_nombres = [c[0] for c in categorias]
    categorias_count = [c[1] for c in categorias]

    # Movimientos recientes
    cursor.execute("""
        SELECT COALESCE(r.nombre, 'Producto eliminado'), m.tipo_movimiento, m.cantidad, m.fecha
        FROM movimientos m LEFT JOIN repuestos r ON m.repuesto_id = r.id
        ORDER BY m.fecha DESC LIMIT 5
    """)
    movimientos_raw = cursor.fetchall()
    conn.close()

    data = {
        'fecha_hoy': datetime.now().strftime('%d/%m/%Y'),
        'ventas_hoy_count': resumen['ventas_hoy_count'],
        'ventas_hoy_valor': resumen['ventas_hoy_valor'],
        'ventas_mes_count': resumen['ventas_mes_count'],
        'ventas_mes_valor': resumen['ventas_mes_valor'],
        'stock_critico': resumen['stock_critico'],
        'clientes_nuevos': resumen['clientes_nuevos_hoy'],
        'salud_stock': round(resumen['salud_inventario']),
        'salud_label': 'Saludable' if resumen['salud_inventario'] >= 70 else 'Crítico' if resumen['salud_inventario'] < 50 else 'Alerta',
        'stock_critico_data': [{'nombre': p['nombre'], 'cantidad': p['cantidad'], 'stock_minimo': p['stock_minimo']} for p in resumen['stock_critico_lista']],
        'movimientos': [{'producto': m[0], 'tipo': m[1], 'cantidad': m[2], 'fecha': m[3]} for m in movimientos_raw],
        'meses': meses,
        'ventas_mensuales': ventas_data,
        'categorias_nombres': categorias_nombres,
        'categorias_count': categorias_count,
    }
    db.cache_set('api_dashboard', data, ttl=30)
    return jsonify(data)

@app.route('/api/dashboard/detalle/ventas_hoy')
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_dashboard_ventas_hoy():
    cached = db.cache_get('api_detalle_ventas_hoy')
    if cached: return jsonify(cached)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT factura, cliente_nombre, total, metodo_pago, estado, time(fecha) as hora
                      FROM pedidos WHERE date(fecha) = date('now')
                      ORDER BY fecha DESC''')
    rows = cursor.fetchall()
    conn.close()
    data = [{
        'factura': r[0], 'cliente': r[1], 'total': r[2],
        'metodo_pago': r[3] or '-', 'estado': r[4], 'hora': r[5][:5] if r[5] else '-'
    } for r in rows]
    db.cache_set('api_detalle_ventas_hoy', data, ttl=30)
    return jsonify(data)

@app.route('/api/dashboard/detalle/ventas_mes')
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_dashboard_ventas_mes():
    cached = db.cache_get('api_detalle_ventas_mes')
    if cached: return jsonify(cached)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT date(fecha) as dia, COUNT(*), COALESCE(SUM(total),0)
                      FROM pedidos WHERE date(fecha) >= date('now', 'start of month')
                      AND estado IN ('pagado','entregado')
                      GROUP BY date(fecha) ORDER BY dia DESC''')
    rows = cursor.fetchall()
    cursor.execute('''SELECT COALESCE(SUM(total),0), COUNT(*)
                      FROM pedidos WHERE date(fecha) >= date('now', 'start of month')
                      AND estado IN ('pagado','entregado')''')
    total = cursor.fetchone()
    conn.close()
    data = {
        'dias': [{'fecha': r[0], 'cantidad': r[1], 'subtotal': r[2]} for r in rows],
        'total_ventas': total[0] or 0,
        'total_pedidos': total[1] or 0
    }
    db.cache_set('api_detalle_ventas_mes', data, ttl=30)
    return jsonify(data)

@app.route('/api/dashboard/detalle/stock_critico')
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_dashboard_stock_critico():
    cached = db.cache_get('api_detalle_stock_critico')
    if cached: return jsonify(cached)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, codigo, nombre, cantidad, stock_minimo, precio
                      FROM repuestos WHERE cantidad <= stock_minimo
                      ORDER BY cantidad ASC''')
    rows = cursor.fetchall()
    conn.close()
    data = [{
        'id': r[0], 'codigo': r[1] or '-', 'nombre': r[2],
        'cantidad': r[3], 'stock_minimo': r[4], 'precio': r[5],
        'faltan': max(0, r[4] - r[3])
    } for r in rows]
    db.cache_set('api_detalle_stock_critico', data, ttl=30)
    return jsonify(data)

@app.route('/api/dashboard/detalle/salud_stock')
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_dashboard_salud_stock():
    cached = db.cache_get('api_detalle_salud_stock')
    if cached: return jsonify(cached)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, codigo, nombre, cantidad, stock_minimo, precio,
                      CASE WHEN cantidad > stock_minimo * 2 THEN 'optimo'
                           WHEN cantidad > stock_minimo THEN 'bajo'
                           ELSE 'critico' END as nivel
                      FROM repuestos ORDER BY nivel, cantidad ASC''')
    rows = cursor.fetchall()
    conn.close()
    grupos = {'optimo': [], 'bajo': [], 'critico': []}
    for r in rows:
        grupos[r[6]].append({
            'id': r[0], 'codigo': r[1] or '-', 'nombre': r[2],
            'cantidad': r[3], 'stock_minimo': r[4], 'precio': r[5]
        })
    total = len(rows)
    data = {
        'grupos': grupos,
        'total': total,
        'pct_optimo': round(len(grupos['optimo'])/total*100,1) if total else 0,
        'pct_bajo': round(len(grupos['bajo'])/total*100,1) if total else 0,
        'pct_critico': round(len(grupos['critico'])/total*100,1) if total else 0
    }
    db.cache_set('api_detalle_salud_stock', data, ttl=30)
    return jsonify(data)

@app.route('/api/dashboard/detalle/clientes_nuevos')
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_dashboard_clientes_nuevos():
    cached = db.cache_get('api_detalle_clientes_nuevos')
    if cached: return jsonify(cached)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT username, nombre, email, telefono, time(fecha_registro) as hora
                      FROM usuarios WHERE date(fecha_registro) = date('now') AND rol = 'cliente'
                      ORDER BY fecha_registro DESC''')
    rows = cursor.fetchall()
    conn.close()
    data = [{
        'username': r[0], 'nombre': r[1], 'email': r[2] or '-',
        'telefono': r[3] or '-', 'hora': r[4][:5] if r[4] else '-'
    } for r in rows]
    db.cache_set('api_detalle_clientes_nuevos', data, ttl=30)
    return jsonify(data)

@app.route('/api/bigdata/analisis')
@admin_required
def api_bigdata_analisis():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos")
    productos = cursor.fetchall()
    cursor.execute("SELECT m.*, r.nombre FROM movimientos m LEFT JOIN repuestos r ON m.repuesto_id = r.id WHERE m.tipo_movimiento = 'SALIDA' ORDER BY m.fecha DESC LIMIT 500")
    movimientos = cursor.fetchall()
    conn.close()
    ventas = {}
    for m in movimientos:
        nombre = m[8] if len(m) > 8 else 'Producto'
        ventas[nombre] = ventas.get(nombre, 0) + m[3]
    top_vendidos = [{'nombre': k, 'movimientos': v} for k, v in sorted(ventas.items(), key=lambda x: x[1], reverse=True)[:10]]
    valor_total = sum(p[4] * p[5] for p in productos) if productos else 0
    predicciones = []
    for p in productos:
        if p[4] <= p[6]:
            necesidad = p[6] * 2 - p[4]
            predicciones.append({'producto': p[2], 'codigo': p[1], 'stock_actual': p[4], 'minimo_recomendado': p[6], 'cantidad_necesaria': max(0, necesidad)})
    return jsonify({
        'total_productos': len(productos),
        'valor_total_inventario': valor_total,
        'productos_mas_vendidos': top_vendidos,
        'predicciones_reposicion': predicciones
    })

@app.route('/api/movimientos')
@admin_required
def api_movimientos():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.id, m.tipo_movimiento, m.cantidad, m.precio_unitario, m.motivo, m.usuario, m.fecha, 
                   COALESCE(r.nombre, 'Producto eliminado') as producto, 
                   COALESCE(r.codigo, '') as codigo,
                   COALESCE(r.categoria, '') as categoria,
                   CASE 
                       WHEN m.motivo LIKE 'Venta%' AND m.usuario != 'sistema' AND m.usuario NOT IN ('admin', 'vendedor1', 'vendedor2')
                       THEN 'logueado'
                       WHEN m.motivo LIKE 'Venta%' AND m.usuario = 'sistema'
                       THEN 'invitado'
                       ELSE 'sistema'
                   END as cliente_tipo,
                   CASE 
                       WHEN m.motivo LIKE 'Venta%' AND m.usuario != 'sistema' AND m.usuario NOT IN ('admin', 'vendedor1', 'vendedor2')
                       THEN (SELECT nombre FROM usuarios WHERE username = m.usuario)
                       WHEN m.motivo LIKE 'Venta%' AND m.usuario = 'sistema'
                       THEN NULL
                       ELSE NULL
                   END as cliente_nombre
            FROM movimientos m 
            LEFT JOIN repuestos r ON m.repuesto_id = r.id 
            ORDER BY m.fecha DESC 
            LIMIT 500
        ''')
        rows = cursor.fetchall()
        conn.close()
        movimientos = []
        for row in rows:
            cliente_mostrar = None
            if row[9] == 'logueado' and row[10]:
                cliente_mostrar = row[10]
            elif row[9] == 'invitado':
                cliente_mostrar = 'Invitado'
            else:
                cliente_mostrar = 'Sistema'
            
            movimientos.append({
                'id': row[0], 'tipo_movimiento': row[1], 'cantidad': row[2],
                'precio_unitario': row[3], 'motivo': row[4], 'usuario': row[5],
                'fecha': row[6], 'producto': row[7], 'codigo': row[8],
                'categoria': row[9],
                'cliente_tipo': row[10], 
                'cliente_nombre': cliente_mostrar
            })
        return jsonify(movimientos)
    except Exception as e:
        app.logger.error(f"Error en /api/movimientos: {e}")
        return jsonify({'error': 'Error al cargar movimientos'}), 500

@app.route('/api/guardar', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_guardar():
    try:
        codigo = request.form.get('codigo')
        nombre = request.form.get('nombre')
        categoria = request.form.get('categoria')
        cantidad_str = request.form.get('cantidad', '0').strip()
        cantidad = max(0, int(cantidad_str) if cantidad_str else 0)
        precio_str = request.form.get('precio', '0').strip()
        precio = max(0, float(precio_str) if precio_str else 0)
        costo_str = request.form.get('costo', '0').strip()
        costo = max(0, float(costo_str) if costo_str else 0)
        stock_minimo_str = request.form.get('stock_minimo', '5').strip()
        stock_minimo = max(0, int(stock_minimo_str) if stock_minimo_str else 5)
        ubicacion = request.form.get('ubicacion', '')
        proveedor = request.form.get('proveedor', '')
        descripcion = request.form.get('descripcion', '')
        caracteristicas = request.form.get('caracteristicas', '')
        especificaciones = request.form.get('especificaciones', '')
        garantia = request.form.get('garantia', '')
        peso = request.form.get('peso', '')
        
        if len(codigo or '') > MAX_LEN['codigo'] or len(nombre or '') > MAX_LEN['producto_nombre'] or \
           len(categoria or '') > MAX_LEN['categoria'] or len(ubicacion or '') > MAX_LEN['ubicacion'] or \
           len(proveedor or '') > MAX_LEN['proveedor'] or len(descripcion or '') > MAX_LEN['descripcion'] or \
           len(caracteristicas or '') > MAX_LEN['caracteristicas'] or len(especificaciones or '') > MAX_LEN['especificaciones'] or \
           len(garantia or '') > MAX_LEN['garantia'] or len(peso or '') > MAX_LEN['peso']:
            flash('Uno o más campos superan la longitud máxima permitida', 'danger')
            return redirect(url_for('admin_registro'))
        
        imagen = ''
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename:
                extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                filename = f"prod_{int(datetime.now().timestamp())}.{extension}"
                uploads_dir = os.path.join(app.root_path, 'Static', 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                filepath = os.path.join(uploads_dir, filename)
                file.save(filepath)
                imagen = filename
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM repuestos WHERE codigo = ?", (codigo,))
        if cursor.fetchone():
            conn.close()
            flash('Ya existe producto con ese código', 'danger')
            return redirect(url_for('admin_registro'))
        
        cursor.execute("INSERT INTO repuestos (codigo, nombre, categoria, cantidad, precio, stock_minimo, ubicacion, proveedor, imagen, descripcion, caracteristicas, especificaciones, garantia, peso, costo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                       (codigo, nombre, categoria, cantidad, precio, stock_minimo, ubicacion, proveedor, imagen, descripcion, caracteristicas, especificaciones, garantia, peso, costo))
        
        repuesto_id = cursor.lastrowid
        
        if cantidad > 0:
            cursor.execute('''INSERT INTO movimientos 
                (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario)
                VALUES (?, 'ENTRADA', ?, ?, 'Registro inicial', ?)''',
                (repuesto_id, cantidad, precio, session.get('username', 'admin')))
        
        conn.commit()
        conn.close()

        ip = request.remote_addr or ''
        db.log_actividad(session['user_id'], session.get('nombre'), 'Producto creado',
                         f'Código: {codigo} - {nombre} - Stock: {cantidad} - ${precio:,.0f}', ip)
        
        flash(' Producto registrado exitosamente', 'success')
        return redirect(url_for('admin_productos'))
        
    except Exception as e:
        app.logger.error(f"Error al registrar producto: {e}")
        flash('Error al registrar producto', 'danger')
        return redirect(url_for('admin_registro'))

def guardar_imagen(file):
    """Guarda un archivo de imagen en Static/uploads y devuelve el nombre."""
    extension = os.path.splitext(file.filename)[1].lower().lstrip('.')
    if extension not in ALLOWED_EXTENSIONS:
        return None
    uploads_dir = os.path.join(app.root_path, 'Static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext == '':
        ext = '.jpg'
    saved_name = f"cat_{int(datetime.now().timestamp())}_{random.randint(100,999)}{ext}"
    filepath = os.path.join(uploads_dir, saved_name)
    file.save(filepath)
    return saved_name

# ========== SUBIR IMAGEN ==========
@app.route('/api/subir_imagen', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def api_subir_imagen():
    try:
        if 'imagen' not in request.files:
            return jsonify({'success': False, 'error': 'No hay imagen'})

        file = request.files['imagen']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'Nombre vacío'})

        extension = os.path.splitext(file.filename)[1].lower().lstrip('.')
        if extension not in ALLOWED_EXTENSIONS:
            return jsonify({'success': False, 'error': 'Formato no permitido (solo PNG, JPG, GIF, WebP)'})

        if file.mimetype not in ALLOWED_MIMES:
            return jsonify({'success': False, 'error': 'Tipo MIME no permitido'})

        filename = secure_filename(file.filename)
        if filename == '':
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'})

        uploads_dir = os.path.join(app.root_path, 'Static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        extension = os.path.splitext(filename)[1].lower()
        if extension == '':
            extension = '.jpg'
        saved_name = f"prod_{int(datetime.now().timestamp())}{extension}"
        filepath = os.path.join(uploads_dir, saved_name)
        file.save(filepath)

        return jsonify({'success': True, 'filename': saved_name})
    except Exception as e:
        app.logger.error(f"Error en /api/guardar imagen: {e}")
        return jsonify({'success': False, 'error': 'Error al guardar la imagen'}), 500

@app.route('/api/actualizar/<int:id>', methods=['PUT'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_actualizar(id):
    try:
        data = request.get_json()
        tipo = data.get('tipo')
        cantidad = max(0, int(data.get('cantidad', 0)))
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        motivo = (data.get('motivo', '') or '')[:200]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT cantidad, precio FROM repuestos WHERE id = ?", (id,))
        producto = cursor.fetchone()
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        if tipo == 'ENTRADA':
            nueva = producto[0] + cantidad
        elif tipo == 'SALIDA':
            if cantidad > producto[0]:
                return jsonify({'error': 'Stock insuficiente'}), 400
            nueva = producto[0] - cantidad
        else:
            return jsonify({'error': 'Tipo inválido'}), 400
        cursor.execute("UPDATE repuestos SET cantidad = ? WHERE id = ?", (nueva, id))
        cursor.execute("INSERT INTO movimientos (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario) VALUES (?,?,?,?,?,?)",
                       (id, tipo, cantidad, producto[1], motivo, session.get('username')))
        conn.commit()
        conn.close()

        ip = request.remote_addr or ''
        db.log_actividad(session['user_id'], session.get('nombre'), f'Stock {tipo}',
                         f'ID: {id} - Cant: {cantidad} - Motivo: {motivo}', ip)

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error en /api/actualizar stock: {e}")
        return jsonify({'error': 'Error al actualizar el stock'}), 500

@app.route('/api/eliminar/<int:id>', methods=['DELETE'])
@limiter.limit("30 per minute", override_defaults=False)
@admin_required
def api_eliminar(id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Obtener datos del producto antes de eliminar
        cursor.execute("SELECT nombre, cantidad, precio FROM repuestos WHERE id = ?", (id,))
        producto = cursor.fetchone()
        
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        nombre = producto[0]
        cantidad = producto[1]
        precio = producto[2]
        
        # REGISTRAR MOVIMIENTO DE SALIDA incluso si no hay stock
        motivo_mov = f'ELIMINACIÓN: {nombre} ({"stock 0" if cantidad == 0 else f"stock {cantidad} unidades"})'
        cursor.execute('''INSERT INTO movimientos 
            (repuesto_id, tipo_movimiento, cantidad, precio_unitario, motivo, usuario)
            VALUES (?, 'SALIDA', ?, ?, ?, ?)''',
            (id, cantidad, precio, motivo_mov, session.get('username', 'admin')))
        
        # Conservar el historial de movimientos (poner repuesto_id en NULL)
        cursor.execute("UPDATE movimientos SET repuesto_id = NULL WHERE repuesto_id = ?", (id,))
        cursor.execute("UPDATE pedido_detalle SET producto_id = NULL WHERE producto_id = ?", (id,))
        cursor.execute("DELETE FROM alertas WHERE repuesto_id = ?", (id,))
        cursor.execute("DELETE FROM repuestos WHERE id = ?", (id,))
        
        conn.commit()
        conn.close()

        ip = request.remote_addr or ''
        db.log_actividad(session['user_id'], session.get('nombre'), 'Producto eliminado',
                         f'ID: {id} - {nombre} - Stock: {cantidad}', ip)
        
        return jsonify({'success': True, 'mensaje': f'Producto {nombre} eliminado'})
        
    except Exception as e:
        app.logger.error(f"Error en /api/eliminar: {e}")
        return jsonify({'error': 'Error al eliminar el producto'}), 500

# ========== SUCURSALES ==========
# (Eliminado - no usado)

# ==================== BIG DATA AVANZADO ====================

@app.route('/api/ventas/evolucion')
@admin_required
def api_ventas_evolucion():
    dias = min(max(request.args.get('dias', 30, type=int) or 30, 1), 365)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DATE(m.fecha) as dia, SUM(m.cantidad) as total
        FROM movimientos m
        WHERE m.tipo_movimiento = 'SALIDA'
        AND m.fecha >= date('now', ?)
        GROUP BY DATE(m.fecha)
        ORDER BY dia
    ''', (f'-{dias} days',))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'fecha': row[0], 'ventas': row[1]} for row in rows])

@app.route('/api/productos/tendencias')
@admin_required
def api_productos_tendencias():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, r.nombre, r.cantidad, r.stock_minimo,
               COALESCE(SUM(CASE WHEN m.fecha >= date('now', '-7 days') THEN m.cantidad ELSE 0 END), 0) as ventas_semana_actual,
               COALESCE(SUM(CASE WHEN m.fecha BETWEEN date('now', '-14 days') AND date('now', '-7 days') THEN m.cantidad ELSE 0 END), 0) as ventas_semana_anterior
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA'
        GROUP BY r.id
    ''')
    productos = cursor.fetchall()
    resultado = []
    for p in productos:
        ventas_actual = p[4]
        ventas_anterior = p[5]
        tendencia = 'estable'
        if ventas_anterior > 0:
            cambio = (ventas_actual - ventas_anterior) / ventas_anterior * 100
            if cambio > 20:
                tendencia = 'alza'
            elif cambio < -20:
                tendencia = 'baja'
        cursor2 = conn.cursor()
        cursor2.execute('''
            SELECT AVG(cantidad) FROM movimientos
            WHERE repuesto_id = ? AND tipo_movimiento = 'SALIDA' AND fecha >= date('now', '-30 days')
        ''', (p[0],))
        promedio_diario = cursor2.fetchone()[0] or 0
        dias_restantes = int(p[2] / promedio_diario) if promedio_diario > 0 else 999
        resultado.append({
            'nombre': p[1],
            'stock_actual': p[2],
            'stock_minimo': p[3],
            'ventas_actual': ventas_actual,
            'ventas_anterior': ventas_anterior,
            'tendencia': tendencia,
            'dias_restantes': dias_restantes
        })
    conn.close()
    return jsonify(resultado)

@app.route('/api/analytics/clasificacion_abc')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_clasificacion_abc():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, r.nombre, COALESCE(SUM(m.cantidad), 0) as ventas
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA' AND m.fecha >= date('now', '-30 days')
        GROUP BY r.id
        ORDER BY ventas DESC
    ''')
    productos = cursor.fetchall()
    conn.close()
    total_ventas = sum(p[2] for p in productos)
    resultado = []
    acum = 0
    for p in productos:
        acum += p[2]
        if total_ventas == 0:
            categoria = 'C'
        elif acum <= total_ventas * 0.7:
            categoria = 'A'
        elif acum <= total_ventas * 0.9:
            categoria = 'B'
        else:
            categoria = 'C'
        resultado.append({'nombre': p[1], 'ventas': p[2], 'categoria': categoria})
    return jsonify(resultado)

@app.route('/api/analytics/sin_movimiento')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_sin_movimiento():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, r.nombre, r.cantidad, r.precio, MAX(m.fecha) as ultima_venta
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA'
        GROUP BY r.id
        HAVING ultima_venta < date('now', '-60 days') OR ultima_venta IS NULL
    ''')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'nombre': r[1], 'stock': r[2], 'precio': r[3], 'ultima_venta': r[4] or 'Nunca'} for r in rows])

@app.route('/api/analytics/prediccion_demanda')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_prediccion_demanda():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, r.nombre, r.cantidad, r.stock_minimo,
               COALESCE(SUM(m.cantidad), 0) as ventas_30d
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA' AND m.fecha >= date('now', '-30 days')
        GROUP BY r.id
    ''')
    productos = cursor.fetchall()
    conn.close()
    resultado = []
    for p in productos:
        ventas = p[4]
        if ventas == 0:
            prediccion_7 = prediccion_15 = prediccion_30 = 0
        else:
            promedio_diario = ventas / 30.0
            prediccion_7 = round(promedio_diario * 7)
            prediccion_15 = round(promedio_diario * 15)
            prediccion_30 = round(promedio_diario * 30)
        resultado.append({
            'nombre': p[1],
            'stock_actual': p[2],
            'stock_minimo': p[3],
            'prediccion_7d': prediccion_7,
            'prediccion_15d': prediccion_15,
            'prediccion_30d': prediccion_30
        })
    return jsonify(resultado)

@app.route('/api/analytics/estacionalidad')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_estacionalidad():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            strftime('%Y-%m', fecha) as mes,
            SUM(cantidad) as total_ventas
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha >= date('now', '-60 days')
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT 2
    ''')
    rows = cursor.fetchall()
    conn.close()
    if len(rows) == 2:
        variacion = round((rows[0][1] - rows[1][1]) / rows[1][1] * 100, 1) if rows[1][1] > 0 else 0
        return jsonify({
            'mes_actual': rows[0][0],
            'ventas_actual': rows[0][1],
            'mes_anterior': rows[1][0],
            'ventas_anterior': rows[1][1],
            'variacion': variacion
        })
    else:
        return jsonify({'error': 'No hay suficientes datos'})

# ==================== NUEVOS ENDPOINTS PARA ANALÍTICA AVANZADA ====================

@app.route('/api/analytics/rotacion_stock')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_rotacion_stock():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COALESCE(SUM(cantidad), 0) as total_ventas
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha >= date('now', '-30 days')
    ''')
    total_ventas = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT COALESCE(SUM(cantidad * precio), 0) as valor_inventario
        FROM repuestos
    ''')
    valor_inventario = cursor.fetchone()[0] or 0
    
    conn.close()
    
    ventas_diarias = total_ventas / 30
    if ventas_diarias > 0:
        dias_rotacion = round(valor_inventario / ventas_diarias)
    else:
        dias_rotacion = 999
    
    return jsonify({'dias_promedio': dias_rotacion})

@app.route('/api/analytics/resumen_ventas')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_resumen_ventas():
    dias = request.args.get('dias', 30, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COALESCE(SUM(cantidad), 0) as total_unidades,
            COALESCE(SUM(cantidad * precio_unitario), 0) as ingreso_total
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha >= date('now', ?)
    ''', (f'-{dias} days',))
    actual = cursor.fetchone()
    
    cursor.execute('''
        SELECT COALESCE(SUM(cantidad), 0) as total_unidades
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha BETWEEN date('now', ?) AND date('now', ?)
    ''', (f'-{dias*2} days', f'-{dias} days'))
    anterior = cursor.fetchone()
    
    cursor.execute('''
        SELECT COUNT(DISTINCT id) as num_transacciones
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha >= date('now', ?)
    ''', (f'-{dias} days',))
    transacciones = cursor.fetchone()[0] or 1
    
    conn.close()
    
    total_unidades = actual[0]
    ingreso_total = actual[1] or 0
    ticket_promedio = round(ingreso_total / transacciones) if transacciones > 0 else 0
    
    ventas_anterior = anterior[0] or 0
    if ventas_anterior > 0:
        crecimiento = round((total_unidades - ventas_anterior) / ventas_anterior * 100, 1)
    else:
        crecimiento = 100 if total_unidades > 0 else 0
    
    return jsonify({
        'ticket_promedio': ticket_promedio,
        'total_unidades': total_unidades,
        'ingreso_total': ingreso_total,
        'crecimiento': crecimiento
    })

@app.route('/api/analytics/margen_promedio')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_margen_promedio():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COALESCE(AVG(CASE WHEN precio > 0 AND costo > 0 THEN (precio - costo) / precio * 100 END), 0) as margen
        FROM repuestos
        WHERE precio > 0
    ''')
    resultado = cursor.fetchone()
    margen_promedio = round(resultado[0], 1) if resultado and resultado[0] else 0
    
    cursor.execute('''
        SELECT categoria,
               COALESCE(AVG(CASE WHEN precio > 0 AND costo > 0 THEN (precio - costo) / precio * 100 END), 0) as margen_cat
        FROM repuestos
        WHERE precio > 0
        GROUP BY categoria
    ''')
    categorias = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'promedio': margen_promedio,
        'por_categoria': [{'categoria': c[0], 'margen': round(c[1], 1)} for c in categorias]
    })

@app.route('/api/analytics/rotacion_por_categoria')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_rotacion_por_categoria():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            r.categoria,
            COALESCE(SUM(m.cantidad), 0) as ventas_totales,
            COALESCE(SUM(r.cantidad * r.precio), 0) as valor_inventario
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA' AND m.fecha >= date('now', '-30 days')
        GROUP BY r.categoria
    ''')
    categorias = cursor.fetchall()
    conn.close()
    
    resultado = []
    for cat in categorias:
        nombre = cat[0]
        ventas = cat[1]
        valor_inv = cat[2]
        
        if ventas > 0 and valor_inv > 0:
            ventas_diarias = ventas / 30
            dias = round(valor_inv / ventas_diarias) if ventas_diarias > 0 else 999
        else:
            dias = 999
        
        resultado.append({'categoria': nombre, 'dias': min(dias, 365)})
    
    return jsonify(resultado)

@app.route('/api/analytics/estacionalidad_avanzada')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_estacionalidad_avanzada():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            strftime('%m', fecha) as mes_num,
            strftime('%Y', fecha) as anio,
            strftime('%B', fecha) as mes_nombre,
            COALESCE(SUM(cantidad), 0) as ventas
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha >= date('now', '-30 days')
    ''')
    actual = cursor.fetchone()
    
    cursor.execute('''
        SELECT 
            strftime('%B', fecha) as mes_nombre,
            COALESCE(SUM(cantidad), 0) as ventas
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha BETWEEN date('now', '-60 days') AND date('now', '-30 days')
    ''')
    anterior = cursor.fetchone()
    
    cursor.execute('''
        SELECT 
            strftime('%Y', fecha) as anio,
            COALESCE(SUM(cantidad), 0) as ventas
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND strftime('%m', fecha) = strftime('%m', 'now')
        AND strftime('%Y', fecha) = strftime('%Y', date('now', '-1 year'))
    ''')
    anio_anterior = cursor.fetchone()
    
    conn.close()
    
    ventas_actual = actual[3] if actual else 0
    ventas_anterior = anterior[1] if anterior else 0
    ventas_anio_anterior = anio_anterior[1] if anio_anterior else 0
    
    variacion_mensual = round((ventas_actual - ventas_anterior) / ventas_anterior * 100, 1) if ventas_anterior > 0 else 0
    variacion_anual = round((ventas_actual - ventas_anio_anterior) / ventas_anio_anterior * 100, 1) if ventas_anio_anterior > 0 else 0
    
    return jsonify({
        'mes_actual': actual[2] if actual else 'N/A',
        'ventas_actual': ventas_actual,
        'mes_anterior': anterior[0] if anterior else 'N/A',
        'ventas_anterior': ventas_anterior,
        'variacion_mensual': variacion_mensual,
        'anio_actual': actual[1] if actual else datetime.now().year,
        'anio_anterior': anio_anterior[0] if anio_anterior else datetime.now().year - 1,
        'ventas_anio_anterior': ventas_anio_anterior,
        'variacion_anual': variacion_anual
    })

@app.route('/api/analytics/alertas_inteligentes')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_alertas_inteligentes():
    conn = get_db()
    cursor = conn.cursor()
    
    alertas = []
    
    cursor.execute('''
        SELECT nombre, cantidad, stock_minimo
        FROM repuestos
        WHERE cantidad <= stock_minimo
        ORDER BY (cantidad * 1.0 / stock_minimo) ASC
        LIMIT 5
    ''')
    criticos = cursor.fetchall()
    for c in criticos:
        alertas.append({
            'nivel': 'critica',
            'titulo': ' Stock crítico',
            'mensaje': f'{c[0]} tiene {c[1]} unidades. Mínimo requerido: {c[2]}',
            'icono': 'bi-exclamation-triangle-fill'
        })
    
    cursor.execute('''
        SELECT nombre, cantidad, stock_minimo
        FROM repuestos
        WHERE cantidad <= stock_minimo * 1.5 AND cantidad > stock_minimo
        LIMIT 5
    ''')
    reposicion = cursor.fetchall()
    for r in reposicion:
        alertas.append({
            'nivel': 'alta',
            'titulo': ' Reposición necesaria',
            'mensaje': f'{r[0]} tiene {r[1]} unidades. Considere reponer (mínimo: {r[2]})',
            'icono': 'bi-truck'
        })
    
    cursor.execute('''
        SELECT r.nombre, MAX(m.fecha) as ultima_venta
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA'
        GROUP BY r.id
        HAVING ultima_venta < date('now', '-60 days') OR ultima_venta IS NULL
        LIMIT 3
    ''')
    sinmov = cursor.fetchall()
    for s in sinmov:
        alertas.append({
            'nivel': 'media',
            'titulo': ' Producto lento',
            'mensaje': f'{s[0]} no ha tenido ventas en más de 60 días',
            'icono': 'bi-hourglass-split'
        })
    
    cursor.execute('''
        SELECT r.nombre, COALESCE(SUM(m.cantidad), 0) as ventas
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA' AND m.fecha >= date('now', '-30 days')
        GROUP BY r.id
        HAVING ventas > 20
        ORDER BY ventas DESC
        LIMIT 3
    ''')
    alta_rotacion = cursor.fetchall()
    for a in alta_rotacion:
        alertas.append({
            'nivel': 'baja',
            'titulo': ' Alta demanda',
            'mensaje': f'{a[0]} tuvo {a[1]} ventas en el último mes. Asegure stock suficiente',
            'icono': 'bi-fire'
        })
    
    conn.close()
    
    return jsonify(alertas)

# ========== BASE DE DATOS (VISOR GENERAL) ==========

@app.route('/admin/reportes')
@admin_required
def admin_reportes():
    return render_template('reportes.html', usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/basedatos')
@admin_required
def admin_basedatos():
    return render_template('admin_basedatos.html', usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/api/basedatos')
@limiter.limit("15 per minute", override_defaults=False)
@admin_required
def api_basedatos():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Productos
        cursor.execute("SELECT id, codigo, nombre, categoria, cantidad, precio, stock_minimo, ubicacion, proveedor, fecha_registro FROM repuestos ORDER BY nombre")
        productos = cursor.fetchall()
        
        # Movimientos (últimos 200)
        cursor.execute('''
            SELECT m.id, COALESCE(r.nombre, 'Eliminado') as producto, m.tipo_movimiento, m.cantidad, m.precio_unitario, m.motivo, m.usuario, m.fecha
            FROM movimientos m LEFT JOIN repuestos r ON m.repuesto_id = r.id
            ORDER BY m.fecha DESC LIMIT 200
        ''')
        movimientos = cursor.fetchall()
        
        # Usuarios
        cursor.execute("SELECT id, username, nombre, email, rol, activo, fecha_registro FROM usuarios ORDER BY id")
        usuarios = cursor.fetchall()
        
        # Pedidos
        cursor.execute("SELECT id, factura, cliente_nombre, total, metodo_pago, estado, fecha FROM pedidos ORDER BY fecha DESC LIMIT 100")
        pedidos = cursor.fetchall()
        
        # Categorías
        cursor.execute("SELECT id, slug, nombre, activo FROM categorias ORDER BY nombre")
        categorias = cursor.fetchall()
        
        conn.close()
        
        def row_to_dict(row, keys):
            return {keys[i]: row[i] for i in range(len(keys))}
        
        return jsonify({
            'productos': [row_to_dict(r, ['id','codigo','nombre','categoria','cantidad','precio','stock_minimo','ubicacion','proveedor','fecha_registro']) for r in productos],
            'movimientos': [row_to_dict(r, ['id','producto','tipo','cantidad','precio','motivo','usuario','fecha']) for r in movimientos],
            'usuarios': [row_to_dict(r, ['id','username','nombre','email','rol','activo','fecha_registro']) for r in usuarios],
            'pedidos': [row_to_dict(r, ['id','factura','cliente','total','metodo_pago','estado','fecha']) for r in pedidos],
            'categorias': [row_to_dict(r, ['id','slug','nombre','activo']) for r in categorias],
            'stats': {
                'total_productos': len(productos),
                'total_movimientos': len(movimientos),
                'total_usuarios': len(usuarios),
                'total_pedidos': len(pedidos),
                'total_categorias': len(categorias),
            }
        })
    except Exception as e:
        app.logger.error(f"Error en /api/basedatos: {e}")
        return jsonify({'error': 'Error al obtener datos de la base de datos'}), 500

# ========== REGISTRO DE NUEVOS USUARIOS ==========
@app.route('/registrar_usuario', methods=['GET', 'POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def registrar_usuario():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        rol = request.form.get('rol', 'usuario').strip() or 'usuario'

        if not username or not password or not nombre:
            flash(' Todos los campos son obligatorios', 'danger')
            return redirect(url_for('registrar_usuario'))

        if len(username) > MAX_LEN['username'] or len(nombre) > MAX_LEN['nombre'] or \
           len(email) > MAX_LEN['email'] or len(password) > MAX_LEN['password']:
            flash('Uno o más campos superan la longitud máxima permitida', 'danger')
            return redirect(url_for('registrar_usuario'))

        if len(password) < 8:
            flash(' La contraseña debe tener al menos 8 caracteres', 'danger')
            return redirect(url_for('registrar_usuario'))

        if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash(' Correo electrónico inválido', 'danger')
            return redirect(url_for('registrar_usuario'))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        if cursor.fetchone():
            flash(' El nombre de usuario ya existe', 'danger')
            conn.close()
            return redirect(url_for('registrar_usuario'))

        password_hash = db.hash_password(password)

        cursor.execute('''INSERT INTO usuarios (username, password, nombre, email, rol, activo)
            VALUES (?, ?, ?, ?, ?, ?)''', (username, password_hash, nombre, email, rol, 1))
        conn.commit()
        conn.close()
        flash(' Usuario registrado exitosamente', 'success')
        return redirect(url_for('admin_usuarios'))

    return render_template('registrar_usuario.html')

# ========== EXPORTAR CSV COMPLETO ==========
@app.route('/api/exportar_csv_completo')
@limiter.limit("3 per minute", override_defaults=False)
@admin_required
def exportar_csv_completo():
    import csv
    from io import StringIO
    from datetime import datetime
    
    conn = get_db()
    cursor = conn.cursor()
    
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # 1. PRODUCTOS
    writer.writerow(['===== 1. PRODUCTOS ====='])
    writer.writerow(['ID', 'Código', 'Nombre', 'Categoría', 'Stock Actual', 'Stock Mínimo', 
                     'Precio', 'Valor Total', 'Ubicación', 'Proveedor', 'Fecha Registro'])
    
    cursor.execute('''
        SELECT id, codigo, nombre, categoria, cantidad, stock_minimo, 
               precio, (cantidad * precio) as valor_total, ubicacion, proveedor, fecha_registro
        FROM repuestos ORDER BY nombre
    ''')
    productos = cursor.fetchall()
    
    for p in productos:
        writer.writerow([p[0], p[1], p[2], p[3], p[4], p[5], f"{p[6]:,.0f}", 
                        f"{p[7]:,.0f}", p[8] or '', p[9] or '', p[10] or ''])
    
    writer.writerow([])
    writer.writerow(['===== RESUMEN PRODUCTOS ====='])
    writer.writerow(['Total Productos', len(productos)])
    writer.writerow(['Valor Total Inventario', f"{sum((p[6] * p[4]) for p in productos):,.0f}"])
    
    # 2. MOVIMIENTOS
    writer.writerow([])
    writer.writerow(['===== 2. MOVIMIENTOS (Últimos 500) ====='])
    writer.writerow(['ID', 'Producto', 'Tipo', 'Cantidad', 'Precio Unitario', 'Valor Total', 'Motivo', 'Usuario', 'Fecha'])
    
    cursor.execute('''
        SELECT m.id, r.nombre, m.tipo_movimiento, m.cantidad, m.precio_unitario,
               (m.cantidad * m.precio_unitario) as valor_total, m.motivo, m.usuario, m.fecha
        FROM movimientos m LEFT JOIN repuestos r ON m.repuesto_id = r.id
        ORDER BY m.fecha DESC LIMIT 500
    ''')
    movimientos = cursor.fetchall()
    
    for m in movimientos:
        writer.writerow([m[0], m[1], m[2], m[3], f"{m[4]:,.0f}", f"{m[5]:,.0f}", 
                        m[6] or '', m[7] or '', m[8]])
    
    # 3. CLASIFICACIÓN ABC
    writer.writerow([])
    writer.writerow(['===== 3. CLASIFICACIÓN ABC (Top 50) ====='])
    writer.writerow(['Producto', 'Ventas (30 días)', 'Categoría ABC'])
    
    cursor.execute('''
        SELECT r.nombre, COALESCE(SUM(m.cantidad), 0) as ventas
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id 
            AND m.tipo_movimiento = 'SALIDA' AND m.fecha >= date('now', '-30 days')
        GROUP BY r.id ORDER BY ventas DESC LIMIT 50
    ''')
    abc = cursor.fetchall()
    
    total_ventas = sum(a[1] for a in abc)
    acum = 0
    for item in abc:
        acum += item[1]
        if total_ventas == 0:
            categoria = 'C'
        elif acum <= total_ventas * 0.7:
            categoria = 'A'
        elif acum <= total_ventas * 0.9:
            categoria = 'B'
        else:
            categoria = 'C'
        writer.writerow([item[0], item[1], categoria])
    
    # 4. PRODUCTOS SIN MOVIMIENTO
    writer.writerow([])
    writer.writerow(['===== 4. PRODUCTOS SIN MOVIMIENTO (60+ días) ====='])
    writer.writerow(['Producto', 'Stock Actual', 'Precio', 'Última Venta'])
    
    cursor.execute('''
        SELECT r.nombre, r.cantidad, r.precio, MAX(m.fecha) as ultima_venta
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA'
        GROUP BY r.id
        HAVING ultima_venta < date('now', '-60 days') OR ultima_venta IS NULL
    ''')
    sin_mov = cursor.fetchall()
    
    for s in sin_mov:
        writer.writerow([s[0], s[1], f"{s[2]:,.0f}", s[3] or 'Nunca'])
    
    # 5. STOCK CRÍTICO
    writer.writerow([])
    writer.writerow(['===== 5. STOCK CRÍTICO ====='])
    writer.writerow(['Producto', 'Stock Actual', 'Stock Mínimo', 'Diferencia', 'Urgencia'])
    
    cursor.execute('''
        SELECT nombre, cantidad, stock_minimo
        FROM repuestos WHERE cantidad <= stock_minimo
        ORDER BY (cantidad * 1.0 / stock_minimo) ASC
    ''')
    criticos = cursor.fetchall()
    
    for c in criticos:
        diferencia = c[2] - c[1]
        urgencia = 'CRÍTICA' if c[1] == 0 else 'ALTA'
        writer.writerow([c[0], c[1], c[2], diferencia, urgencia])
    
    # 6. PREDICCIONES
    writer.writerow([])
    writer.writerow(['===== 6. PREDICCIONES DE DEMANDA ====='])
    writer.writerow(['Producto', 'Stock Actual', 'Stock Mínimo', 'Predicción 7d', 'Predicción 15d', 'Predicción 30d'])
    
    cursor.execute('''
        SELECT r.nombre, r.cantidad, r.stock_minimo,
               COALESCE(SUM(m.cantidad), 0) as ventas_30d
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id 
            AND m.tipo_movimiento = 'SALIDA' AND m.fecha >= date('now', '-30 days')
        GROUP BY r.id HAVING ventas_30d > 0
        ORDER BY ventas_30d DESC LIMIT 30
    ''')
    predicciones = cursor.fetchall()
    
    for p in predicciones:
        ventas_diarias = p[3] / 30
        pred_7d = round(ventas_diarias * 7)
        pred_15d = round(ventas_diarias * 15)
        pred_30d = round(ventas_diarias * 30)
        writer.writerow([p[0], p[1], p[2], pred_7d, pred_15d, pred_30d])
    
    # 7. USUARIOS
    writer.writerow([])
    writer.writerow(['===== 7. USUARIOS ====='])
    writer.writerow(['ID', 'Usuario', 'Nombre', 'Email', 'Rol', 'Activo', 'Fecha Registro'])
    
    cursor.execute('SELECT id, username, nombre, email, rol, activo, fecha_registro FROM usuarios')
    usuarios = cursor.fetchall()
    
    for u in usuarios:
        writer.writerow([u[0], u[1], u[2] or '', u[3] or '', u[4], 'Sí' if u[5] else 'No', u[6] or ''])
    
    conn.close()
    
    writer.writerow([])
    writer.writerow(['===== REPORTE GENERADO ====='])
    writer.writerow(['Fecha Exportación', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['Sistema', 'StockPro - Celeris Moto Express'])
    
    response = make_response(output.getvalue().encode('utf-8-sig'))
    response.headers['Content-Disposition'] = f'attachment; filename=stockpro_exportacion_completa_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    
    return response

# ========== MACHINE LEARNING - PREDICCIÓN DE VENTAS ==========

@app.route('/api/ml/prediccion_ventas')
@limiter.limit("5 per minute", override_defaults=False)
@admin_required
def ml_prediccion_ventas():
    """Predice ventas para los próximos 30 días usando Regresión Lineal (cache 1h)"""
    ahora = datetime.now()
    cache = getattr(ml_prediccion_ventas, 'cache', None)
    if cache and cache['ts'] > ahora - timedelta(hours=1):
        return jsonify(cache['data'])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DATE(fecha) as dia, SUM(cantidad) as ventas
        FROM movimientos
        WHERE tipo_movimiento = 'SALIDA'
        AND fecha >= date('now', '-180 days')
        GROUP BY DATE(fecha)
        ORDER BY dia
    ''')
    datos = cursor.fetchall()
    conn.close()

    if len(datos) < 7:
        return jsonify({'error': 'Se necesitan al menos 7 días de datos para generar predicciones'})

    df = pd.DataFrame(datos, columns=['fecha', 'ventas'])
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['dia_semana'] = df['fecha'].dt.dayofweek
    df['dia_mes'] = df['fecha'].dt.day
    df['mes'] = df['fecha'].dt.month
    df['semana'] = df['fecha'].dt.isocalendar().week

    lag_dias = min(7, max(1, len(datos) // 2))
    for i in range(1, lag_dias + 1):
        df[f'ventas_dia_{i}'] = df['ventas'].shift(i)

    df = df.dropna()

    feature_cols = ['dia_semana', 'dia_mes', 'mes', 'semana'] + [f'ventas_dia_{i}' for i in range(1, lag_dias + 1)]
    X = df[feature_cols].values
    y = df['ventas'].values

    model = LinearRegression()
    model.fit(X, y)
    r2 = model.score(X, y)

    ultimos_valores = df.iloc[-1:][feature_cols].values[0].tolist()
    predicciones = []

    for i in range(30):
        pred = model.predict([ultimos_valores])[0]
        predicciones.append(max(0, round(pred)))
        nuevos_valores = ultimos_valores[:4] + [pred] + ultimos_valores[4:-1]
        ultimos_valores = nuevos_valores

    fechas_prediccion = [(datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(30)]
    tendencia = 'alza' if predicciones[-1] > predicciones[0] else 'baja' if predicciones[-1] < predicciones[0] else 'estable'

    result = {
        'predicciones': predicciones,
        'fechas': fechas_prediccion,
        'precision': round(r2 * 100, 1),
        'tendencia': tendencia,
        'total_siguiente_mes': sum(predicciones)
    }
    ml_prediccion_ventas.cache = {'ts': datetime.now(), 'data': result}
    return jsonify(result)

@app.route('/api/ml/tendencias_productos')
@limiter.limit("5 per minute", override_defaults=False)
@admin_required
def ml_tendencias_productos():
    cache = getattr(ml_tendencias_productos, 'cache', None)
    if cache and cache['ts'] > datetime.now() - timedelta(hours=1):
        return jsonify(cache['data'])
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.id, r.nombre, r.precio,
               SUM(CASE WHEN m.fecha >= date('now', '-30 days') THEN m.cantidad ELSE 0 END) as ventas_30d,
               SUM(CASE WHEN m.fecha BETWEEN date('now', '-60 days') AND date('now', '-30 days') THEN m.cantidad ELSE 0 END) as ventas_60d
        FROM repuestos r
        LEFT JOIN movimientos m ON r.id = m.repuesto_id AND m.tipo_movimiento = 'SALIDA'
        GROUP BY r.id
        HAVING ventas_30d > 0 OR ventas_60d > 0
        ORDER BY ventas_30d DESC
        LIMIT 20
    ''')
    productos = cursor.fetchall()
    conn.close()

    resultados = []
    for p in productos:
        ventas_30 = p[3] or 0
        ventas_60 = p[4] or 0
        cambio = ((ventas_30 - ventas_60) / ventas_60 * 100) if ventas_60 > 0 else (100 if ventas_30 > 0 else 0)

        if cambio > 20:
            tendencia, color = 'alta', 'success'
        elif cambio < -20:
            tendencia, color = 'baja', 'danger'
        else:
            tendencia, color = 'estable', 'secondary'

        resultados.append({
            'nombre': p[1],
            'ventas_30d': ventas_30,
            'ventas_60d': ventas_60,
            'cambio': round(cambio, 1),
            'tendencia': tendencia,
            'color': color
        })

    ml_tendencias_productos.cache = {'ts': datetime.now(), 'data': resultados}
    return jsonify(resultados)

@app.route('/ml/predicciones')
@admin_required
def ml_predicciones():
    return render_template('ml_predicciones.html', usuario=session.get('nombre'), rol=session.get('rol'))

# ========== REPORTES PDF ==========

@app.route('/api/reporte/inventario/pdf')
@limiter.limit("3 per minute", override_defaults=False)
@admin_required
def reporte_inventario_pdf():
    from fpdf import FPDF
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, categoria, cantidad, precio, stock_minimo, ubicacion, proveedor FROM repuestos ORDER BY nombre")
    productos = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(cantidad * precio) FROM repuestos")
    total_prod, valor_total = cursor.fetchone()
    conn.close()

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(230, 57, 70)
    pdf.cell(0, 12, 'STOCKPRO - Reporte de Inventario', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")} | Total productos: {total_prod} | Valor inventario: ${valor_total:,.0f}', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(26, 26, 46)
    pdf.set_text_color(255, 255, 255)
    col_w = [22, 55, 30, 18, 22, 18, 30, 40]
    headers = ['Codigo', 'Nombre', 'Categoria', 'Stock', 'Precio', 'Min', 'Ubicacion', 'Proveedor']
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(33, 37, 41)
    fill = False
    for p in productos:
        if pdf.get_y() > 185:
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_fill_color(26, 26, 46)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 8, h, border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_font('Helvetica', '', 7)
            pdf.set_text_color(33, 37, 41)
        if fill:
            pdf.set_fill_color(240, 242, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        data = [str(p[0] or ''), p[1] or '', p[2] or '', str(p[3]), f'${p[4]:,.0f}', str(p[5] or 5), p[6] or '', p[7] or '']
        for i, d in enumerate(data):
            pdf.cell(col_w[i], 6, d, border=1, align='C' if i < 4 else 'R' if i == 4 else 'C', fill=True)
        pdf.ln()
        fill = not fill

    response = make_response(bytes(pdf.output(dest='S')))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=inventario_{datetime.now().strftime("%Y%m%d")}.pdf'
    return response


@app.route('/api/reporte/ventas/pdf')
@limiter.limit("3 per minute", override_defaults=False)
@admin_required
def reporte_ventas_pdf():
    from fpdf import FPDF
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT p.factura, p.cliente_nombre, p.total, p.metodo_pago, p.estado, p.fecha
                      FROM pedidos p ORDER BY p.fecha DESC LIMIT 100''')
    pedidos = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM pedidos WHERE estado IN ('pagado','entregado')")
    total_ventas, total_valor = cursor.fetchone()
    conn.close()

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(230, 57, 70)
    pdf.cell(0, 12, 'STOCKPRO - Reporte de Ventas', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")} | Total ventas: {total_ventas} | Valor total: ${total_valor:,.0f}', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(26, 26, 46)
    pdf.set_text_color(255, 255, 255)
    col_w = [55, 50, 30, 30, 25, 40]
    headers = ['Factura', 'Cliente', 'Total', 'Metodo Pago', 'Estado', 'Fecha']
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(33, 37, 41)
    fill = False
    for p in pedidos:
        if pdf.get_y() > 185:
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(26, 26, 46)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 8, h, border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(33, 37, 41)
        if fill:
            pdf.set_fill_color(240, 242, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        data = [p[0], p[1] or '', f'${p[2]:,.0f}', p[3] or '-', p[4], p[5][:10] if p[5] else '']
        for i, d in enumerate(data):
            pdf.cell(col_w[i], 6, d, border=1, align='C', fill=True)
        pdf.ln()
        fill = not fill

    response = make_response(bytes(pdf.output(dest='S')))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=ventas_{datetime.now().strftime("%Y%m%d")}.pdf'
    return response


# ========== MODO MANTENIMIENTO ==========

MANTENIMIENTO_FILE = os.path.join(os.path.dirname(DB_PATH), 'mantenimiento.txt')

def get_mantenimiento():
    try:
        with open(MANTENIMIENTO_FILE, 'r') as f:
            return f.read().strip() == '1'
    except Exception:
        return False

def set_mantenimiento(activo):
    os.makedirs(os.path.dirname(MANTENIMIENTO_FILE), exist_ok=True)
    with open(MANTENIMIENTO_FILE, 'w') as f:
        f.write('1' if activo else '0')

@app.before_request
def check_mantenimiento():
    if not get_mantenimiento():
        return
    if session.get('rol') == 'administrador':
        return
    if request.path.startswith(('/static', '/login', '/logout', '/mantenimiento')):
        return
    return render_template('mantenimiento.html'), 503

@app.route('/mantenimiento')
def pagina_mantenimiento():
    if get_mantenimiento():
        return render_template('mantenimiento.html'), 503
    return redirect(url_for('index'))

@app.route('/admin/mantenimiento', methods=['GET', 'POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_mantenimiento():
    if request.method == 'POST':
        activo = request.form.get('activo') == 'on'
        set_mantenimiento(activo)
        flash(f'Modo mantenimiento {"activado" if activo else "desactivado"}', 'success')
        return redirect(url_for('admin_mantenimiento'))
    return render_template('admin_mantenimiento.html', mantenimiento=get_mantenimiento(), usuario=session.get('nombre'), rol=session.get('rol'))

# ========== NOTIFICACIONES EN VIVO ==========

@app.route('/api/notificaciones')
@limiter.limit("20 per minute", override_defaults=False)
@admin_required
def api_notificaciones():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, codigo, cantidad, stock_minimo FROM repuestos WHERE cantidad = 0 ORDER BY nombre")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{
            'id': r[0], 'nombre': r[1], 'codigo': r[2],
            'cantidad': r[3], 'stock_minimo': r[4]
        } for r in rows])
    except Exception as e:
        app.logger.error(f"Error en /api/notificaciones: {e}")
        return jsonify({'error': 'Error al cargar notificaciones'}), 500

@app.route('/api/ping', methods=['POST'])
@limiter.limit("30 per minute", override_defaults=False)
@login_required
def api_ping():
    user_id = session.get('user_id')
    if user_id:
        db.actualizar_ultimo_acceso(user_id)
    return jsonify({'ok': True})

@app.route('/api/logout/now', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@login_required
def api_logout_now():
    user_id = session.get('user_id')
    username = session.get('username', '')
    if user_id:
        db.log_actividad(user_id, username, 'Cierre de sesión', f'Usuario cerró la página', request.remote_addr or '')
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/usuarios_activos')
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def api_usuarios_activos():
    try:
        activos = db.obtener_usuarios_activos(15)
        return jsonify(activos)
    except Exception as e:
        app.logger.error(f"Error en /api/usuarios_activos: {e}")
        return jsonify({'error': 'Error al cargar usuarios activos'}), 500

# ========== RESPALDOS AUTOMÁTICOS ==========

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
ULTIMO_BACKUP_FILE = os.path.join(os.path.dirname(DB_PATH), 'ultimo_backup.txt')
BACKUP_INTERVAL = 7 * 24 * 3600  # Semanal (cada sábado)

def leer_ultimo_backup():
    try:
        with open(ULTIMO_BACKUP_FILE, 'r') as f:
            return float(f.read().strip())
    except Exception:
        return 0

def escribir_ultimo_backup():
    os.makedirs(os.path.dirname(ULTIMO_BACKUP_FILE), exist_ok=True)
    with open(ULTIMO_BACKUP_FILE, 'w') as f:
        f.write(str(datetime.now().timestamp()))

def crear_respaldo():
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(BACKUP_DIR, f'stockpro_{timestamp}.db')
        shutil.copy2(DB_PATH, backup_path)
        escribir_ultimo_backup()
        # Limpiar backups viejos (>30 días)
        for f in os.listdir(BACKUP_DIR):
            fpath = os.path.join(BACKUP_DIR, f)
            if os.path.isfile(fpath) and f.endswith('.db'):
                file_time = os.path.getmtime(fpath)
                if datetime.now().timestamp() - file_time > 30 * 86400:
                    os.remove(fpath)
        return True, backup_path
    except Exception as e:
        app.logger.error(f"[BACKUP] Error al crear respaldo: {e}")
        return False, "Error al crear el respaldo"

def backup_thread():
    while True:
        try:
            hoy = datetime.now()
            if hoy.weekday() == 5:  # Sábado
                ultimo = leer_ultimo_backup()
                ahora = hoy.timestamp()
                if ahora - ultimo >= BACKUP_INTERVAL:
                    print(f"[BACKUP] Respaldo semanal (sábado)...")
                    crear_respaldo()
            threading.Event().wait(3600)  # Revisar cada hora
        except Exception:
            threading.Event().wait(3600)

@app.route('/admin/respaldos')
@admin_required
def admin_respaldos():
    return render_template('admin_respaldos.html', usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/api/respaldos')
@admin_required
def api_respaldos():
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        archivos = []
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            fpath = os.path.join(BACKUP_DIR, f)
            if os.path.isfile(fpath) and f.endswith('.db'):
                tamano = os.path.getsize(fpath)
                fecha = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S')
                archivos.append({'nombre': f, 'tamano': tamano, 'fecha': fecha})
        
        ultimo = leer_ultimo_backup()
        ahora = datetime.now().timestamp()
        horas_desde_ultimo = round((ahora - ultimo) / 3600, 1) if ultimo > 0 else 0
        
        return jsonify({
            'respaldos': archivos,
            'ultimo_backup': datetime.fromtimestamp(ultimo).strftime('%Y-%m-%d %H:%M:%S') if ultimo > 0 else 'Nunca',
            'horas_desde_ultimo': horas_desde_ultimo,
            'proximo_backup': 'Sábado (semanal)',
            'total_respaldos': len(archivos)
        })
    except Exception as e:
        app.logger.error(f"Error en /api/respaldos: {e}")
        return jsonify({'error': 'Error al listar respaldos'}), 500

@app.route('/api/respaldos/crear', methods=['POST'])
@limiter.limit("3 per minute", override_defaults=False)
@csrf.exempt
@admin_required
def api_respaldos_crear():
    exito, resultado = crear_respaldo()
    if exito:
        return jsonify({'success': True, 'archivo': os.path.basename(resultado)})
    return jsonify({'success': False, 'error': resultado}), 500

@app.route('/api/respaldos/descargar/<filename>')
@admin_required
def api_respaldos_descargar(filename):
    try:
        fpath = safe_join(BACKUP_DIR, filename)
        if not fpath or not os.path.exists(fpath):
            flash('Archivo no encontrado', 'danger')
            return redirect(url_for('admin_respaldos'))
        return send_file(fpath, as_attachment=True, download_name=filename)
    except (ValueError, FileNotFoundError):
        flash('Archivo no encontrado', 'danger')
        return redirect(url_for('admin_respaldos'))
    except Exception:
        flash('Error al descargar el archivo', 'danger')
        return redirect(url_for('admin_respaldos'))

# ========== LOGS / ACTIVIDAD ==========

import json as _json

@app.route('/admin/logs')
@admin_required
def admin_logs():
    registros = db.obtener_actividad(200)
    total = db.contar_actividad()
    return render_template('admin_logs.html', registros=registros, total=total,
                           usuario=session.get('nombre'), rol=session.get('rol'))

# ========== LOG ALL REQUESTS ==========

@app.after_request
def log_request(response):
    if request.path.startswith('/api/') or request.path in ['/login', '/logout']:
        return response
    if 'user_id' in session:
        try:
            ip = request.remote_addr or ''
            user = session.get('nombre', 'Desconocido')
            method = request.method
            path = request.path
            if method != 'GET':
                db.log_actividad(session['user_id'], user, f'{method} {path}', '', ip)
        except Exception:
            pass
    return response

# ========== WEBHOOKS ==========

@app.route('/admin/webhooks')
@admin_required
def admin_webhooks():
    webhooks = db.obtener_webhooks()
    logs = db.obtener_webhook_logs(30)
    return render_template('admin_webhooks.html', webhooks=webhooks, logs=logs,
                           usuario=session.get('nombre'), rol=session.get('rol'))

@app.route('/admin/webhooks/crear', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_webhooks_crear():
    nombre = request.form.get('nombre', '').strip()
    url = request.form.get('url', '').strip()
    evento = request.form.get('evento', '')
    if len(nombre) > MAX_LEN['webhook_nombre'] or len(url) > MAX_LEN['webhook_url']:
        flash('Uno o más campos superan la longitud máxima permitida', 'danger')
        return redirect(url_for('admin_webhooks'))
    if nombre and url and evento:
        db.crear_webhook(nombre, url, evento)
        db.log_actividad(session['user_id'], session.get('nombre'), 'Crear webhook', f'{nombre} -> {evento}', request.remote_addr)
        flash('Webhook creado', 'success')
    else:
        flash('Completa todos los campos', 'danger')
    return redirect(url_for('admin_webhooks'))

@app.route('/admin/webhooks/eliminar/<int:id>', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_webhooks_eliminar(id):
    db.eliminar_webhook(id)
    return jsonify({'success': True})

# ========== CACHE CLEAR ==========

@app.route('/admin/cache/limpiar', methods=['POST'])
@limiter.limit("10 per minute", override_defaults=False)
@admin_required
def admin_cache_limpiar():
    db.cache_clear()
    db.log_actividad(session['user_id'], session.get('nombre'), 'Limpiar cache', '', request.remote_addr)
    return jsonify({'success': True})

# ========== INICIALIZAR DB AL CARGAR ==========
init_db()

# Crear directorio de backups al iniciar
os.makedirs(BACKUP_DIR, exist_ok=True)

# Iniciar hilo de respaldos automaticos
hilo_backup = threading.Thread(target=backup_thread, daemon=True)
hilo_backup.start()

# ========== INICIO ==========
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, port=5000)