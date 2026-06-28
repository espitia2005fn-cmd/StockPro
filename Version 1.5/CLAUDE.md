# Ilia - Memoria del Proyecto StockPro

## Identidad
- Me llamo **ilia**
- Soy el agente de IA que mantiene y desarrolla StockPro
- Este archivo es mi memoria persistente del proyecto

## Proyecto: StockPro
**Proyecto de grado — Universidad de Cundinamarca**
Sistema de gestion de inventarios, ventas y analitica con ML para tienda de motopartes. Eje central: Big Data + analytics como valor agregado academico (ML predictivo, dashboards ECharts, clasificacion ABC).

### Stack
- Python Flask 3.1.3 (SQLite local / PostgreSQL opcional)
- Tailadmin template (panel admin)
- Frontend: HTML+CSS+JS con Bootstrap
- ML: scikit-learn para prediccion de ventas
- Seed: 63 productos reales, 19 pedidos, 6 clientes

### Estructura
```
Version 1.5/
  src/
    app.py              <-- API y rutas principales
    database.py         <-- SQLite
    database_supabase.py <-- PostgreSQL
    Static/
      css/ (Style.css, tailadmin.css)
      uploads/ (277 imagenes de productos)
    templates/ (public + admin HTML)
  scripts/
    seed_reales.py      <-- Seed con datos reales
  data/
    stockpro.db         <-- Base de datos
  tests/
```

### Estado Actual
- **Login**: Arreglado (se borro `session.regenerate()` que no existe en Flask 3.1.3)
- **Botones blancos**: Arreglado (se agregaron 12 vars CSS a Style.css)
- **Export CSV**: Links corregidos (`/api/exportar_csv_completo`)
- **ML Predicciones**: Threshold 7 dias minimo, lag adaptativo
- **NUEVO badge**: 3 dias de threshold, gradient pill
- **Badge carrito**: Arreglado (busca `.btn-nav .badge-nav`)
- **Reportes PDF**: Ruta `/admin/reportes` creada
- **CSP**: Content-Security-Policy agregada
- **Tipografia**: Unificada a Outfit

### Overhaul v2.0 — COMPLETADO (commit dba6608)
- **FASE 1 Seguridad**: safe_join, str(e)=0, CORS localhost, captcha fix, session secure
- **FASE 2 DB Adapter**: autocommit=False, rollback(), SQL conversions, set_config() fix
- **FASE 3 Validacion**: max(0,...), IDs numericos, email regex, MAX_LEN, dias<=365
- **FASE 4 Rate Limits**: 62 decoradores (antes 41), GETs criticos protegidos
- **FASE 5 Templates**: Bootstrap 5.3.3 unificado, flashes duplicados eliminados

### Issues Conocidos (post-Overhaul)
- `database.py` y `database_supabase.py` no unificados (~80% duplicacion)
- Dark theme no integrado (CSS listo, JS toggle no conectado)
- Bloqueo de cuenta por intentos fallidos NO implementado
- base_categoria.html NO hereda de base_public.html (requiere reestructura)
- mostrarNotificacion() duplicada en varios templates
- CSP con 'unsafe-inline' debilita proteccion XSS
- Connection pooling en PostgreSQL no implementado
- app.py sigue siendo monolito (3000+ lineas)

### Diagnostico 23/06/2026 — Auditoria Completa de Bugs

#### 🔴 CRITICOS (arreglar AHORA)

| # | Bug | Archivo | Solucion |
|---|-----|---------|----------|
| 1 | Flash messages INVISIBLES en paginas publicas | `base_public.html` — falta `{% with messages = get_flashed_messages() %}`. 7 flash() calls en app.py se pierden (carrito, pago, confirmacion, recibo) | Agregar bloque de flash en base_public.html |
| 2 | Categoria `'error'` NO es Bootstrap 5 | `app.py` usa `flash('...', 'error')` 26 veces. `base_admin.html:179` genera `alert-error` que NO existe en BS5 | Cambiar a `'danger'` o mapear correctamente |
| 3 | `danger`, `warning`, `info` se ven como `success` (verde) | `base_admin.html:179` y `base_cliente.html:86` solo distinguen `'error'` vs `else` → `success` | Hacer switch case para todas las categorias |
| 4 | "SAFOTAWARE" hardcodeado en auth | `base_auth.html:135` — `<h1>SAFOTAWARE</h1>` en vez de "STOCKPRO" | Cambiar a "STOCKPRO" |
| 5 | `style.css` vs `Style.css` (CASE MISMATCH) | `base_public.html:10`, `base_auth.html:10`, `base_categoria.html:8` referencian `css/style.css` pero el archivo es `css/Style.css`. Funciona en Windows, se rompe en Linux | Cambiar referencia a `Style.css` o renombrar archivo a `style.css` |
| 6 | Modal categorias con estructura rota | `admin_categorias.html:380-405` — modal-footer de "Nueva Categoria" queda fuera del modal-body, entre medio de otro modal | Reestructurar los divs del modal |
| 7 | Sin error handlers 404/500 | `app.py` — no hay NI UN `@app.errorhandler`. Usuario ve pagina blanca o traceback en errores | Agregar handlers con templates custom |
| 8 | HTML entities se duplican por autoescape | `app.py:706,911,1078,1611,2359,3056` — `&aacute;` dentro de strings Python se convierte en `&amp;aacute;` | Usar caracteres Unicode reales (`á`, `é`, etc.) |

#### 🟧 VISUALES Y TEMPLATES

| # | Bug | Archivo | Solucion |
|---|-----|---------|----------|
| 9 | `base_categoria.html` usa Anton/Bebas Neue/Inter (no Outfit) | `base_categoria.html:10` — fuente diferente al resto del proyecto | Cambiar a Outfit o eliminar archivo (es dead code) |
| 10 | Bootstrap Icons version inconsistente | `base_admin.html`, `base_cliente.html`: 1.11.1. `base_public.html`, `base_auth.html`: 1.11.0 | Unificar a 1.11.1 en todos |
| 11 | `btn-cart` class usada pero no definida en CSS | `categoria.html:171`, `index.html:435` | Agregar la clase al CSS o cambiar por clase existente |
| 12 | Cuenta bancaria placeholder hardcodeada | `pago.html:157` — `Cuenta: 123-456-789` | Poner en config o dejar vacio |
| 13 | NIT hardcodeado | `recibo.html:64` — `NIT 900.123.456-7` | Poner en config o dejar vacio |
| 14 | Newsletter sin funcionalidad | `base_public.html:132-135` — input + boton que no hacen nada | Quitar o implementar |
| 15 | Dark theme partido en dos sistemas | `Style.css` usa `[data-theme="dark"]`, `tailadmin.css` usa `.dark` class | El JS toggle debe setear AMBOS |
| 16 | No hay favicon | Ninguna template tiene `<link rel="icon">` | Agregar favicon.ico |
| 17 | `mostrarNotificacion()` duplicada 6 veces | `base_admin.html`, `index.html`, `categoria.html`, `producto_detalle.html`, `carrito.html`, `admin_productos.html` | Centralizar en bloque extra_js de cada base |
| 18 | `getCSRFToken()` duplicada 4 veces | `base_public.html`, `base_admin.html`, `base_cliente.html`, `base_categoria.html` | Centralizar |
| 19 | `base_categoria.html` es dead code (416 lineas) | No es extendida por nadie, no referenciada en app.py | Decidir: eliminar o convertir en layout heredable |

#### 🟨 SEGURIDAD

| # | Bug | Archivo | Solucion |
|---|-----|---------|----------|
| 21 | CORS default `'*'` | `app.py:31` — cualquier web puede llamar la API | Setear `CORS_ORIGINS` en produccion |
| 22 | Sin HSTS (`Strict-Transport-Security`) | `app.py:229-247` — falta entre security headers | Agregar header |
| 23 | Password admin `admin123` como fallback | `database.py:240` — `os.environ.get('ADMIN_PASSWORD', 'admin123')` | Quitar fallback, forzar env var |
| 24 | Debug mode default `'1'` en app.py | `app.py:3095` — `FLASK_DEBUG` default `'1'` | Cambiar default a `'0'` |
| 27 | Rate limits en memoria (`memory://`) | `app.py:41` — se resetean al reiniciar servidor | Usar Redis o similar en produccion |

**Pendientes a futuro:** Connection leaks (try/finally), unificar database.py y database_supabase.py, error handlers 404/500, HTST, CORS produccion.

#### 🟦 BASE DE DATOS

| # | Bug | Archivo | Solucion |
|---|-----|---------|----------|
| 28 | Connection leaks — sin try/finally | `database.py` — todas las funciones | Envolver en context managers |
| 29 | database.py y database_supabase.py 80% duplicados | Ambos archivos | Unificar en un solo adapter |
| 30 | db_adapter._convert() regex fragil | `db_adapter.py:60-94` — regex convierte SQLite a PostgreSQL | Refactorizar usando dialectos |
| 31 | `lastrowid` con `SELECT LASTVAL()` inseguro | `db_adapter.py:134-137` — concurrencia da IDs equivocados | Usar `RETURNING id` |
| 32 | Producto ID=55 sin imagen | BD — "Piñon Delantero (Universal)" sin campo imagen | Asignar imagen |
| 33 | Archivo imagen mal nombrado | `uploads/Llanta Pirelli... jpg` — falta punto antes de jpg | Renombrar a `.jpg` |
| 34 | 16 subdirectorios en uploads/ no referenciados | `uploads/Aceite/`, `uploads/Filtros/`, etc. | Limpiar o ignorar |

#### 🟢 LO QUE SI FUNCIONA
- 7/7 tests pasan ✅
- 63 productos con datos reales, 62 con imagenes ✅
- 15 tablas con indices ✅
- CSRF activo en todos los forms ✅
- Rate limiting en 62 endpoints ✅
- Session seguro (HttpOnly + SameSite=Strict + 8h) ✅
- Bcrypt para passwords ✅
- CAPTCHA en login/registro ✅
- Todas las rutas renderizan templates existentes ✅
- Style.css 1310 lineas sin errores sintacticos ✅
- tailadmin.css 1178 lineas sin errores ✅
- Dockerfile + .dockerignore ✅
- safe_join + html.escape() implementados ✅
- CSP nonces en todas las templates (5 bases) + unsafe-inline quitado de script-src ✅
- escHtml() global para prevenir XSS en innerHTML ✅
- Bloqueo de cuenta tras 5 intentos fallidos (15 min de lockout) ✅
- logging.getLogger(__name__) en vez de bare except ✅

### Test de Integracion 23/06/2026 (build mode)

**FLUJO COMPLETO VERIFICADO (todo OK ✅):**

| Paso | Resultado | Detalle |
|------|-----------|---------|
| Login admin | ✅ | captcha +- random resuelto correctamente |
| Dashboard + 16 admin pages | ✅ | todas cargan 200 |
| 3 cliente pages | ✅ | dashboard, pedidos, perfil |
| Agregar al carrito | ✅ | precio real $90,000 desde BD (no el del cliente) |
| Ver carrito | ✅ | 1 item, total correcto |
| Checkout completo | ✅ | crea pedido en DB con factura |
| Pedido en base de datos | ✅ | `PED-41781-20260623190825`, total $107,100 (IVA incluido) |
| Registrar usuario nuevo | ✅ | redirect a login |
| Logout + proteccion | ✅ | admin pages redirigen a login |
| 404 page | ✅ | devuelve 404 sin romper |

**API endpoints verificados:** dashboard/resumen, categorias, movimientos, clasificacion_abc, prediccion_demanda, ml/ventas, notificaciones, usuarios_activos — todos 200 ✅

**Issues menores detectados durante test:**
- El CSRF token del login se invalida despues del login, hay que obtener uno fresco del dashboard para POSTs posteriores (comportamiento normal de Flask-WTF)
- Rate limits (429) se disparan con ~15+ requests rapidas en admin pages. Normal en testing, no en uso real.

### Servidor
- `http://192.168.0.5:5000` (local: `http://localhost:5000`)
- `--reload` activo

### Configuracion
- `C:\Users\Juan Espi\.config\opencode\opencode.json` - config principal
- `C:\Users\Juan Espi\.config\opencode\commands\mobile.md` - comando /mobile
- Node.js v24.16.0 / npm 11.13.0
- opencode-mobile plugin instalado para conectar iPhone via OpenLens

### Plugins OpenCode Instalados (25/06/2026)
- `opencode-mobile` - QR para conectar iPhone via OpenLens
- `opencode-firecrawl` - Web scraping de docs (Flask, Bootstrap, etc.)
- `opencode-supermemory` - Memoria persistente entre sesiones
- `opencode-notificator` - Notificaciones de escritorio en tareas largas
- `opencode-worktree` - Git worktrees para versiones paralelas
- `opencode-wakatime` - Trackeo de tiempo de coding

### Mobile QR - Conexion iPhone
- **Conexion local (WiFi directa)**: NO funciono (probable client isolation del router)
- **localtunnel**: Funciona pero da 502/503 con Flask (no recomendado)
- **cloudflared**: FUNCIONA. Comando: `npx cloudflared tunnel --url http://localhost:5000`
- Regla Firewall creada: `StockPro 5000 TCP` (puerto 5000 abierto)
- Red WiFi cambiada a **Privada** para mejor conectividad
- **PENDIENTE**: Probar QR con cloudflared:
  - `npx opencode-mobile qr <path-to-tunnel.json>` o `mobile` tool con URL
  - iOS OpenLens escanea URL publica de cloudflared
- Archivo temporal: `Version 1.5/mobile-qr.png` (QR de IP local - NO funciona)
- QR funcional guardado: `Version 1.5/mobile-qr-cloudflare.png` (usar con cloudflared activo)
- URL cloudflared ultima: `https://corporation-euro-medications-mono.trycloudflare.com` (cambia cada vez)

### Comandos Importantes
- `/mobile` - Genera QR para conectar iPhone con OpenLens
- `npx opencode-mobile qr <file>` - QR desde terminal
- Server: `cd "Version 1.5"; flask run --host=0.0.0.0 --port=5000 --reload`
- Seed: `cd "Version 1.5"; python scripts/seed_reales.py`
- Tests: `cd "Version 1.5"; pytest`
- Cloudflared tunnel: `npx cloudflared tunnel --url http://localhost:5000`
