"""
Limpieza automatica de imagenes huerfanas en uploads/.
Borra imagenes que NO esten referenciadas en repuestos.imagen ni categorias.imagen.
Se ejecuta automaticamente al iniciar la app si pasaron 24h desde la ultima vez.
"""
import os, sys, time, logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def cleanup_orphan_images(app):
    uploads = os.path.join(app.root_path, 'Static', 'uploads')
    lockfile = os.path.join(app.root_path, '..', 'data', '.last_image_cleanup')
    lockfile = os.path.normpath(lockfile)

    # Chequear si pasaron 24h
    if os.path.exists(lockfile):
        try:
            with open(lockfile, 'r') as f:
                last = float(f.read().strip())
            if time.time() - last < 86400:
                last_dt = datetime.fromtimestamp(last).strftime('%Y-%m-%d %H:%M')
                logger.info(f"[CLEANUP] Ultima limpieza: {last_dt}. Faltan {24 - (time.time()-last)//3600:.0f}h. Saltando.")
                return
        except:
            pass

    logger.info("[CLEANUP] Iniciando limpieza de imagenes huerfanas...")

    if not os.path.isdir(uploads):
        logger.warning(f"[CLEANUP] No existe {uploads}")
        return

    # 1. Obtener imagenes referenciadas en DB
    from src import db_adapter as db
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
        if conn:
            conn.close()
        return

    logger.info(f"[CLEANUP] Imagenes referenciadas en DB: {len(refs)}")

    # 2. Escanear uploads/
    deleted = 0
    kept = 0
    errors = 0
    log_lines = []

    for root, dirs, files in os.walk(uploads):
        for f in files:
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                continue
            rel_path = os.path.relpath(os.path.join(root, f), uploads)
            rel_path = rel_path.replace('\\', '/')

            if rel_path in refs:
                kept += 1
                continue

            # Si la imagen esta en raiz PERO una copia con mismo nombre base esta en subcarpeta referenciada
            fname_lower = f.lower()
            is_duplicate = False
            for ref in refs:
                if '/' in ref and ref.split('/')[-1].lower() == fname_lower:
                    is_duplicate = True
                    break

            if is_duplicate:
                full_path = os.path.join(root, f)
                try:
                    os.remove(full_path)
                    deleted += 1
                    msg = f"BORRADO (duplicado en subcarpeta): {rel_path}"
                    log_lines.append(msg)
                    logger.info(f"[CLEANUP] {msg}")
                except Exception as e:
                    errors += 1
                    logger.warning(f"[CLEANUP] Error borrando {rel_path}: {e}")
                continue

            # La imagen no esta referenciada y no es duplicado
            full_path = os.path.join(root, f)
            try:
                os.remove(full_path)
                deleted += 1
                msg = f"BORRADO (huerfano): {rel_path}"
                log_lines.append(msg)
                logger.info(f"[CLEANUP] {msg}")
            except Exception as e:
                errors += 1
                logger.warning(f"[CLEANUP] Error borrando {rel_path}: {e}")

    # 3. Guardar timestamp
    try:
        os.makedirs(os.path.dirname(lockfile), exist_ok=True)
        with open(lockfile, 'w') as f:
            f.write(str(time.time()))
    except:
        pass

    logger.info(f"[CLEANUP] Completado: {deleted} borradas, {kept} conservadas, {errors} errores")

    # 4. Log file
    log_path = os.path.join(os.path.dirname(lockfile), 'image_cleanup.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Borradas: {deleted} | Conservadas: {kept} | Errores: {errors}\n")
            for line in log_lines:
                f.write(line + '\n')
    except:
        pass

    return deleted, kept, errors
