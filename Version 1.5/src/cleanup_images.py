"""
Limpieza automatica de imagenes huerfanas en uploads/.
Borra imagenes que NO esten referenciadas en repuestos.imagen ni categorias.imagen.
Se ejecuta al iniciar la app si pasaron 24h desde la ultima vez.
"""
import os, time, logging
from datetime import datetime

logger = logging.getLogger(__name__)

def cleanup_orphan_images(app):
    uploads = os.path.join(app.root_path, 'Static', 'uploads')
    data_dir = os.path.join(app.root_path, '..', 'data')
    lockfile = os.path.join(data_dir, '.last_image_cleanup')

    if not os.path.isdir(uploads):
        logger.warning(f"[CLEANUP] No existe {uploads}")
        return

    # Chequear si pasaron 24h
    if os.path.exists(lockfile):
        try:
            with open(lockfile) as f:
                last = float(f.read().strip())
            if time.time() - last < 86400:
                last_dt = datetime.fromtimestamp(last).strftime('%Y-%m-%d %H:%M')
                h = 24 - (time.time() - last) / 3600
                logger.info(f"[CLEANUP] Ultima: {last_dt}. Faltan {h:.0f}h. Saltando.")
                return
        except:
            pass

    logger.info("[CLEANUP] Iniciando limpieza de imagenes huerfanas...")

    # 1. Obtener imagenes referenciadas en DB
    from . import db_adapter as db
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT imagen FROM repuestos WHERE imagen != '' AND imagen IS NOT NULL")
        refs = set()
        for row in cur.fetchall():
            refs.add(row['imagen'].replace('\\', '/'))
        cur.execute("SELECT imagen FROM categorias WHERE imagen != '' AND imagen IS NOT NULL")
        for row in cur.fetchall():
            refs.add(row['imagen'].replace('\\', '/'))
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"[CLEANUP] Error leyendo DB: {e}")
        if conn: conn.close()
        return

    logger.info(f"[CLEANUP] Referenciadas en DB: {len(refs)}")

    # 2. Escanear uploads/
    deleted = 0
    kept = 0
    errors = 0
    log_lines = []

    for root, dirs, files in os.walk(uploads):
        dirs[:] = [d for d in dirs if not d.startswith('_')]
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                continue
            rel = os.path.relpath(os.path.join(root, f), uploads).replace('\\', '/')

            if rel in refs:
                kept += 1
                continue

            # Duplicado: mismo nombre de archivo en subcarpeta referenciada
            f_lower = f.lower()
            dup_ref = None
            for r in refs:
                if '/' in r and r.split('/')[-1].lower() == f_lower:
                    dup_ref = r
                    break
            if dup_ref:
                sub_path = os.path.join(uploads, dup_ref.replace('/', os.sep))
                if not os.path.exists(sub_path):
                    logger.info(f"[CLEANUP] SKIP (subdir copy missing): {rel} — ref {dup_ref} no existe en disco")
                    kept += 1
                    continue
                try:
                    os.remove(os.path.join(root, f))
                    deleted += 1
                    msg = f"BORRADO (duplicado en subcarpeta): {rel}"
                    log_lines.append(msg)
                    logger.info(f"[CLEANUP] {msg}")
                except Exception as e:
                    errors += 1
                    logger.warning(f"[CLEANUP] Error: {rel} - {e}")
                continue

            # Huerfano
            try:
                os.remove(os.path.join(root, f))
                deleted += 1
                msg = f"BORRADO (huerfano): {rel}"
                log_lines.append(msg)
                logger.info(f"[CLEANUP] {msg}")
            except Exception as e:
                errors += 1
                logger.warning(f"[CLEANUP] Error: {rel} - {e}")

    # 3. Guardar timestamp
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(lockfile, 'w') as f:
            f.write(str(time.time()))
    except:
        pass

    # 4. Log file
    log_path = os.path.join(data_dir, 'image_cleanup.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Borradas: {deleted} | Conservadas: {kept} | Errores: {errors}\n")
            for line in log_lines:
                f.write(line + '\n')
    except:
        pass

    logger.info(f"[CLEANUP] Completo: {deleted} borradas, {kept} conservadas, {errors} errores")
    return deleted, kept, errors


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default=None)
    parser.add_argument('--db', default=None)
    args = parser.parse_args()

    class MockApp:
        root_path = os.path.join(os.path.dirname(__file__))
    app = MockApp()
    if args.path:
        app.root_path = os.path.dirname(args.path.rstrip('/').rstrip('\\'))
    if args.db:
        global DB_PATH
        DB_PATH = args.db

    from . import db_adapter
    db_adapter.DB_PATH = os.path.abspath(args.db) if args.db else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'stockpro.db'))

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    d, k, e = cleanup_orphan_images(app)
    print(f"\nBorradas: {d} | Conservadas: {k} | Errores: {e}")
