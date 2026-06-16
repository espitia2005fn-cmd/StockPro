# generar_datos.py
import sqlite3
import random
import os
from datetime import datetime, timedelta
import bcrypt

def hash_password(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def generar_datos_prueba():
    print(" Generando datos de prueba...")
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'stockpro.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Verificar cuántos productos existen
    cursor.execute("SELECT COUNT(*) FROM repuestos")
    total_productos = cursor.fetchone()[0]
    print(f" Productos actuales: {total_productos}")
    
    # 2. Generar 1000 productos nuevos si hay menos de 200
    if total_productos < 200:
        print(" Generando 500 productos nuevos...")
        categorias = ['Motor', 'Frenos', 'Suspension', 'Electrico', 'Transmision', 
                      'Lubricantes', 'Neumaticos', 'Carroceria', 'Herramientas', 'Escape']
        proveedores = ['Ducati', 'Honda', 'Yamaha', 'Suzuki', 'Kawasaki', 'BMW', 'KTM']
        
        for i in range(500):
            categoria = random.choice(categorias)
            proveedor = random.choice(proveedores)
            precio = random.randint(5000, 500000)
            stock = random.randint(0, 200)
            stock_minimo = random.randint(5, 30)
            
            costo = int(precio * random.uniform(0.5, 0.8))
            cursor.execute('''INSERT INTO repuestos 
                (codigo, nombre, categoria, cantidad, precio, stock_minimo, proveedor, costo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (f'BD-{i+1000}', f'Producto Big Data {i+1}', categoria, 
                 stock, precio, stock_minimo, proveedor, costo))
        
        conn.commit()
        print("✅ 500 productos nuevos creados")
    
    # 3. Generar movimientos históricos (50,000)
    cursor.execute("SELECT id FROM repuestos")
    productos_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) FROM movimientos")
    total_movimientos = cursor.fetchone()[0]
    print(f" Movimientos actuales: {total_movimientos}")
    
    if total_movimientos < 10000:
        print(" Generando 50,000 movimientos históricos...")
        fecha_inicio = datetime.now() - timedelta(days=365)
        
        for i in range(50000):
            producto_id = random.choice(productos_ids)
            tipo = random.choice(['ENTRADA', 'SALIDA'])
            cantidad = random.randint(1, 20)
            precio = random.randint(5000, 500000)
            dias_atras = random.randint(0, 365)
            fecha = fecha_inicio + timedelta(days=dias_atras)
            usuario = random.choice(['admin', 'vendedor1', 'vendedor2', 'sistema'])
            
            cursor.execute('''INSERT INTO movimientos 
                (repuesto_id, tipo_movimiento, cantidad, precio_unitario, usuario, fecha)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (producto_id, tipo, cantidad, precio, usuario, fecha.strftime('%Y-%m-%d %H:%M:%S')))
            
            # Actualizar stock para movimientos de salida
            if tipo == 'SALIDA':
                cursor.execute("UPDATE repuestos SET cantidad = cantidad - ? WHERE id = ? AND cantidad >= ?", 
                              (cantidad, producto_id, cantidad))
            
            if i % 5000 == 0:
                print(f"   Progreso: {i}/50000 movimientos")
                conn.commit()
        
        conn.commit()
        print("✅ 50,000 movimientos generados")
    
    # 4. Crear usuario de prueba si no existe
    cursor.execute("SELECT id FROM usuarios WHERE username = 'cliente_prueba'")
    if not cursor.fetchone():
        print(" Creando usuario de prueba...")
        password_hash = hash_password('123456')
        cursor.execute('''INSERT INTO usuarios (username, password, nombre, email, rol, activo)
            VALUES (?, ?, ?, ?, ?, ?)''',
            ('cliente_prueba', password_hash, 'Cliente Prueba', 'cliente@prueba.com', 'cliente', 1))
        conn.commit()
        print("✅ Usuario cliente_prueba / 123456 creado")
    
    conn.close()
    print("\n DATOS DE PRUEBA GENERADOS CON ÉXITO!")
    print("======================================")
    print(" Admin: admin / admin123")
    print(" Cliente: cliente_prueba / 123456")
    print("======================================")

if __name__ == '__main__':
    generar_datos_prueba()