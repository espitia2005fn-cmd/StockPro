# Bug Memory — StockPro

## Sesión 28/06/2026 — Seguridad, Supabase, Imágenes

### B001: CSP `unsafe-inline` en script-src
- **Síntoma**: CSP permitía `unsafe-inline` en script-src, anulando protección XSS
- **Causa raíz**: `@app.after_request` no generaba nonces; templates no tenían `nonce=`
- **Solución**: `secrets.token_hex(16)` en `@app.before_request`, `g.csp_nonce` via context processor, `nonce="{{ csp_nonce }}"` en cada `<script>` tag de las 5 bases
- **Archivos tocados**: `app.py`, `base_admin.html`, `base_public.html`, `base_auth.html`, `base_cliente.html`, `base_categoria.html`

### B002: XSS via `innerHTML` sin sanitizar
- **Síntoma**: 7+ templates usaban `.innerHTML =` con datos potencialmente controlados por usuario
- **Causa raíz**: No había función de escape para template literals
- **Solución**: Agregar `escHtml(t)` (basado en `textContent`) a todas las bases, reemplazar `innerHTML` con `textContent` + `escHtml()`
- **Archivos**: `base_admin.html`, `base_public.html`, `base_auth.html`, `base_cliente.html`, `dashboard.html`, `admin_productos.html`, `admin_ordenes.html`, `admin_basedatos.html`, `cliente_dashboard.html`, `cliente_pedidos.html`

### B003: `except:` sin especificar tipo
- **Síntoma**: 8 bloques `except:` capturaban SystemExit, KeyboardInterrupt, errores internos
- **Causa raíz**: Uso de bare `except:` por conveniencia
- **Solución**: Cambiar a `except Exception:`, agregar `import logging` + `logger = logging.getLogger(__name__)`
- **Archivo**: `app.py`

### B004: Gunicorn ignora `.env`
- **Síntoma**: En Railway, `DATABASE_URL` y otras vars no se cargaban
- **Causa raíz**: `load_dotenv()` estaba solo en `run.py`, gunicorn ejecuta `app.py` directo
- **Solución**: Agregar `load_dotenv()` al inicio de `app.py` (nivel módulo, no dentro de función)
- **Archivo**: `app.py`

### B005: `init_db()` sin fallback — crash total si PostgreSQL falla
- **Síntoma**: Si PostgreSQL no conectaba, la app moría sin iniciar
- **Causa raíz**: No había try/except alrededor de la conexión PostgreSQL
- **Solución**: Envolver en try/except: si falla, setear `db_adapter.DATABASE_URL = ''` y usar SQLite
- **Archivo**: `app.py`, `db_adapter.py`

### B006: CAPTCHA vacío al deshabilitar
- **Síntoma**: Cuando `CAPTCHA_ENABLED=0`, `generar_captcha()` retornaba strings vacíos
- **Causa raíz**: Lógica condicional en `generar_captcha()` retornaba temprano
- **Solución**: Siempre generar números; `CAPTCHA_ENABLED` solo controla `validar_captcha()`
- **Archivo**: `app.py`

### B007: Sin bloqueo de cuenta por intentos fallidos
- **Síntoma**: Podían probar contraseñas infinitamente
- **Causa raíz**: Funcionalidad no implementada
- **Solución**: Agregar columnas `failed_attempts` + `locked_until` a `usuarios`, funciones `obtener_bloqueo_usuario()`, `incrementar_intentos_fallidos()`, `resetear_intentos_fallidos()`; login chequea y bloquea tras 5 intentos (15 min)
- **Archivos**: `database.py`, `database_supabase.py`, `app.py`

### B008: Cursor leak en db_adapter (INSERT OR IGNORE)
- **Síntoma**: En PostgreSQL, `INSERT ... RETURNING id` tras `INSERT OR IGNORE` daba error
- **Causa raíz**: `db_adapter.py` no convertía correctamente `INSERT OR IGNORE` a `INSERT ... ON CONFLICT DO NOTHING`, y `lastrowid` fallaba
- **Solución**: Usar `INSERT ... ON CONFLICT DO NOTHING RETURNING id`, ejecutar comando antes de consultar cursor
- **Archivo**: `db_adapter.py`

### B009: Columna `mensaje` faltante en `alertas` (PostgreSQL)
- **Síntoma**: `INSERT INTO alertas (mensaje, ...)` fallaba en PostgreSQL
- **Causa raíz**: Schema PostgreSQL no tenía `mensaje TEXT`
- **Solución**: Agregar `mensaje TEXT` a `CREATE TABLE alertas` en `database_supabase.py`
- **Archivo**: `database_supabase.py`

### B010: Railway + Supabase — IPv6 incompatible con Direct Connection
- **Síntoma**: Railway no podía conectar a Supabase puerto 5432
- **Causa raíz**: Supabase Direct Connection usa solo IPv6; Railway no resuelve IPv6
- **Solución**: Usar Transaction Pooler (puerto 6543) con `?pgbouncer=true`
- **Nota**: El usuario debe actualizar `DATABASE_URL` en Railway Dashboard

## Sesión 29/06/2026 — Escalabilidad, imágenes, hacking

### B011: carrito.html renderiza imagen sin prefijo /static/uploads/
- **Síntoma**: Productos agregados desde `producto_detalle.html` muestran imagen rota (404) cuando el campo `imagen` tiene ruta de subcarpeta (ej: `Lubricantes/prod_xxx.jpg`)
- **Causa raíz**: `carrito.html:230` usa `item.imagen` directo sin anteponer `/static/uploads/`. `index.html` y `categoria.html` envían la URL completa, pero `producto_detalle.html` envía el valor crudo de la DB
- **Solución**: Normalizar en `carrito.html`: si `item.imagen` no empieza con `/static/uploads/`, agregar el prefijo
- **Archivo**: `carrito.html`

### B012: encodeURIComponent rompe rutas con slash
- **Síntoma**: En `index.html:492` y `categoria.html:157` se usa `encodeURIComponent(p.imagen)` que convierte `/` en `%2F`. Funciona en servidores locales pero no es estándar
- **Causa raíz**: Codificar toda la ruta en vez de solo el nombre del archivo
- **Solución**: Usar `/static/uploads/` + `encodeURIComponent` solo para el nombre base, o concatenar directamente (las subcarpetas no necesitan encoding)
- **Archivo**: `index.html`, `categoria.html`

---

## Patrones de Fix Rápido
- **CSP nonces**: `g.csp_nonce = secrets.token_hex(16)` en before_request, context processor lo inyecta, templates usan `nonce="{{ csp_nonce }}"` en cada `<script>`
- **escHtml()**: `function escHtml(t){const d=document.createElement('div'); d.textContent=t; return d.innerHTML;}` — liviano, sin dependencias
- **Dual DB**: `DATABASE_URL` con 'postgres' → PostgreSQL, si falla → SQLite. No requiere config manual
- **CAPTCHA**: Siempre generar challenge; flag solo desactiva validación
