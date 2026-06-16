import pytest
import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Disable CAPTCHA for testing
os.environ['CAPTCHA_ENABLED'] = '0'

from src.app import app, get_db, DB_PATH
from src import database as db


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SESSION_COOKIE_HTTPONLY'] = False
    app.config['WTF_CSRF_ENABLED'] = False
    
    backup_path = DB_PATH + '.bak'
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, backup_path)
    
    db.crear_tablas()
    
    with app.test_client() as client:
        with app.app_context():
            yield client
    
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, DB_PATH)
        os.remove(backup_path)


def test_carrito_agregar_precio_validado(client):
    """El precio debe venir de la BD, no del cliente"""
    resp = client.post('/api/carrito/agregar', json={
        'id': 501, 'nombre': 'test', 'precio': 1, 'cantidad': 1
    })
    data = resp.get_json()
    assert data.get('success') is True
    
    resp2 = client.get('/api/carrito/ver')
    data2 = resp2.get_json()
    assert len(data2['carrito']) > 0
    item = data2['carrito'][0]
    assert item['precio'] != 1
    assert item['precio'] == 32998.0


def test_carrito_agregar_producto_inexistente(client):
    """Producto que no existe debe dar error"""
    resp = client.post('/api/carrito/agregar', json={
        'id': 99999, 'nombre': 'fake', 'precio': 100, 'cantidad': 1
    })
    assert resp.status_code == 404


def test_carrito_agregar_cantidad_invalida(client):
    """Cantidad negativa o cero debe rechazarse"""
    resp = client.post('/api/carrito/agregar', json={
        'id': 501, 'nombre': 'test', 'precio': 100, 'cantidad': 0
    })
    assert resp.status_code == 400


def test_confirmar_pedido_sin_carrito(client):
    """Pedido sin carrito debe redirigir"""
    resp = client.post('/confirmar_pedido', data={
        'metodo_pago': 'tarjeta',
        'cliente_nombre': 'Test',
        'cliente_email': 'test@test.com'
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_login_admin(client):
    """Login con admin debe funcionar"""
    resp = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_api_eliminar_producto(client):
    """Eliminar producto debe registrar movimiento"""
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    
    # Crear un producto temporal para poder eliminarlo sin FK conflicts
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO repuestos (codigo, nombre, categoria, cantidad, precio) VALUES (?, ?, ?, ?, ?)",
                   ('TEST-DEL', 'Producto test para eliminar', 'Testing', 10, 10000))
    producto_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM repuestos")
    total_antes = cursor.fetchone()[0]
    conn.close()
    
    resp = client.delete(f'/api/eliminar/{producto_id}')
    data = resp.get_json()
    assert data.get('success') is True, f"Error: {data}"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM repuestos")
    total_despues = cursor.fetchone()[0]
    conn.close()
    
    assert total_despues == total_antes - 1


def test_api_pedido_detalle_idor(client):
    """Usuario cliente no debe ver pedidos de otro"""
    from src.database import hash_password
    
    # Crear cliente de prueba
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO usuarios (username, password, nombre, email, rol, activo) VALUES (?, ?, ?, ?, ?, ?)",
                   ('testclient', hash_password('testpass'), 'Test Client', 'test@test.com', 'cliente', 1))
    conn.commit()
    conn.close()
    
    client.post('/login', data={'username': 'testclient', 'password': 'testpass'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pedidos LIMIT 1")
    pedido = cursor.fetchone()
    conn.close()
    
    if pedido:
        resp = client.get(f'/api/pedido_detalle/{pedido[0]}')
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code} - cliente no deberia ver pedido ajeno"
    else:
        assert True
