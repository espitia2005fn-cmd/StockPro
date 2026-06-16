"""
Migracion: SQLite -> Supabase (PostgreSQL)
Uso: SUPABASE_DATABASE_URL="postgresql://..." python migrate_to_supabase.py

Lee todos los datos del SQLite local y los inserta en Supabase.
"""
import os
import sys
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'stockpro.db')

def get_sqlite():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def get_pg():
    from src.database_supabase import get_conn
    return get_conn()


def has_id_column(cursor, table):
    try:
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'id'")
        return cursor.fetchone() is not None
    except:
        try:
            cursor.execute(f"SELECT id FROM {table} LIMIT 0")
            return True
        except:
            return False

def copy_table(conn_sqlite, conn_pg, table, columns, order_by='id'):
    cur_s = conn_sqlite.cursor()
    cur_p = conn_pg.cursor()

    has_id = has_id_column(cur_p, table)

    if has_id:
        cur_p.execute(f"SELECT COALESCE(MAX(id), 0) as max_id FROM {table}")
        max_id = cur_p.fetchone()['max_id']
        cur_s.execute(f"SELECT * FROM {table} WHERE id > ? ORDER BY {order_by}", (max_id,))
    else:
        cur_s.execute(f"SELECT * FROM {table}")
        cur_p.execute(f"DELETE FROM {table}")
        conn_pg.commit()

    rows = cur_s.fetchall()

    if not rows:
        print(f"  {table}: sin datos nuevos")
        return 0

    cols = columns
    placeholders = ', '.join(['%s'] * len(cols))
    col_names = ', '.join(cols)

    if has_id:
        updates = ', '.join([f"{c} = EXCLUDED.{c}" for c in cols if c != 'id'])
        conflict = f"ON CONFLICT (id) DO UPDATE SET {updates}"
    else:
        conflict = ""

    inserted = 0
    for row in rows:
        values = [row[c] if row[c] is not None else None for c in cols]
        try:
            cur_p.execute(
                f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) {conflict}",
                values
            )
            conn_pg.commit()
            inserted += 1
        except Exception as e:
            conn_pg.rollback()
            pk = row['id'] if has_id else row.get(cols[0], '?')
            print(f"  SKIP {table} pk={pk}: FK constraint (orphan record)")

    print(f"  {table}: {inserted} registros migrados")
    return inserted


def main():
    print("=" * 60)
    print("Migracion SQLite -> Supabase")
    print("=" * 60)

    conn_sqlite = get_sqlite()
    try:
        conn_pg = get_pg()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        print("\nConfigura SUPABASE_DATABASE_URL en el entorno:")
        print('  $env:SUPABASE_DATABASE_URL="postgresql://..."')
        sys.exit(1)

    total = 0

    print("\nCreando tablas en Supabase...")
    from src.database_supabase import crear_tablas
    crear_tablas()

    print("\nMigrando datos...")

    tables = [
        ('categorias', ['id', 'slug', 'nombre', 'icono', 'descripcion', 'imagen', 'activo', 'fecha_registro']),
        ('usuarios', ['id', 'username', 'password', 'nombre', 'email', 'rol', 'activo', 'telefono', 'direccion', 'foto_perfil', 'ultimo_acceso', 'reset_token', 'reset_token_expiry', 'permisos', 'fecha_registro']),
        ('repuestos', ['id', 'codigo', 'nombre', 'categoria', 'cantidad', 'precio', 'stock_minimo', 'ubicacion', 'proveedor', 'imagen', 'descripcion', 'caracteristicas', 'especificaciones', 'garantia', 'peso', 'costo', 'fecha_registro']),
        ('config', ['clave', 'valor', 'tipo']),
        ('movimientos', ['id', 'repuesto_id', 'tipo_movimiento', 'cantidad', 'precio_unitario', 'motivo', 'usuario', 'fecha']),
        ('alertas', ['id', 'repuesto_id', 'tipo', 'estado', 'fecha']),
        ('ventas', ['id', 'factura', 'usuario_id', 'cliente_nombre', 'cliente_cedula', 'subtotal', 'iva', 'total', 'estado', 'fecha']),
        ('venta_detalle', ['id', 'venta_id', 'producto_id', 'codigo', 'nombre', 'cantidad', 'precio', 'subtotal']),
        ('pedidos', ['id', 'factura', 'usuario_id', 'cliente_nombre', 'cliente_email', 'cliente_telefono', 'cliente_direccion', 'subtotal', 'iva', 'total', 'metodo_pago', 'estado', 'fecha']),
        ('pedido_detalle', ['id', 'pedido_id', 'producto_id', 'codigo', 'nombre', 'cantidad', 'precio', 'subtotal']),
        ('pagos', ['id', 'pedido_id', 'metodo_pago', 'monto', 'referencia', 'estado', 'fecha']),
        ('actividad', ['id', 'usuario_id', 'usuario_nombre', 'accion', 'detalle', 'ip', 'fecha']),
        ('webhooks', ['id', 'nombre', 'url', 'evento', 'activo', 'ultima_respuesta', 'ultimo_error', 'fecha_creacion']),
        ('webhook_logs', ['id', 'webhook_id', 'evento', 'url', 'payload', 'respuesta', 'error', 'fecha']),
        ('sucursales', ['id', 'nombre', 'direccion', 'telefono', 'encargado', 'activo', 'fecha_registro']),
    ]

    for table, cols in tables:
        n = copy_table(conn_sqlite, conn_pg, table, cols)
        total += n

    print(f"\nTotal registros migrados: {total}")
    print("Migracion completada.")

    conn_sqlite.close()
    conn_pg.close()


if __name__ == '__main__':
    main()
