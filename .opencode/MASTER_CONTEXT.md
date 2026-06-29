# MASTER_CONTEXT.md

## Contexto Académico — Proyecto de Grado
**Universidad de Cundinamarca** — Facultad de Ingeniería
**StockPro** es un proyecto de grado que integra **Big Data** como valor agregado académico, combinando análisis predictivo con machine learning (scikit-learn) y visualización de datos (ECharts 5.5.0) en un sistema de gestión de inventarios y ventas para motopartes.

> **Eje central**: Big Data + analytics como pilar del proyecto de grado. No es solo un sistema de inventarios — es la demostración práctica de cómo el análisis de datos y ML resuelven problemas reales en una PYME.

## Project Purpose
**StockPro** — Sistema de gestión de inventarios, ventas y analítica con ML para una tienda de motopartes (*Celeris Moto Express*). Permite administrar productos (repuestos de moto), controlar stock, gestionar ventas/pedidos con carrito de compras, generar reportes PDF y CSV, y predecir demanda mediante machine learning (scikit-learn). Atiende tres roles: administrador (gestión completa), cliente (ver pedidos/perfil) y público (navegar catálogo, comprar).

## Enfoque de Desarrollo (prioridades del proyecto de grado)
1. **Big Data & Analytics** — Módulo de predicciones ML, dashboards ECharts, clasificación ABC, reportes exportables (PDF/CSV). Es el diferenciador académico.
2. **Sistema funcional completo** — Carrito de compras, pedidos, pagos, roles (admin/cliente/público).
3. **Estabilidad y seguridad** — Overhaul v2.0 completado (seguridad, rate limits, templates).
4. **Calidad de código** — Tests (7/7 pasan), bugs documentados, código limpio.

## Tech Stack
| Capa | Tecnología |
|------|-----------|
| **Backend** | Python 3.12+ / Flask 3.x |
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5.3.3, Bootstrap Icons 1.11.1 |
| **Admin Template** | Tailadmin (sidebar + dashboard layout) |
| **Database** | SQLite (local/dev) / PostgreSQL (producción, vía Supabase) |
| **ML** | scikit-learn (LinearRegression, StandardScaler), numpy, pandas |
| **Auth** | bcrypt, Flask-WTF (CSRF), CAPTCHA matemático |
| **Rate Limiting** | Flask-Limiter (memory://, 1000/día, 200/hora) |
| **PDF** | fpdf2 |
| **Production WSGI** | Gunicorn |
| **Deployment** | Docker, Heroku (Procfile) |
| **Email** | Flask-Mail (recuperación de contraseña) |
| **Testing** | pytest |

## Project Structure
```
Repositorio/                          # Git root
├── .opencode/                        # OpenCode configuration
│   ├── ADR.md
│   ├── BUG_MEMORY.md
│   ├── MASTER_CONTEXT.md             # ← this file
│   ├── node_modules/
│   ├── package.json / package-lock.json
│   └── session_state.json
├── check_login.py                    # Utility: verify admin login against DB
├── check_pass.py                     # Utility: test password hashes
└── Version 1.5/                      # Main application
    ├── run.py                        # Entry point (loads dotenv, starts Flask)
    ├── requirements.txt              # Python dependencies (13 packages)
    ├── Dockerfile                    # Python 3.12-slim container
    ├── Procfile                      # Gunicorn production command
    ├── .env.example                  # Environment variable template
    ├── .gitignore
    ├── CLAUDE.md                     # Agent project memory (ilia)
    ├── migrate_to_supabase.py        # SQLite → PostgreSQL migration script
    ├── src/
    │   ├── __init__.py               # Empty package init
    │   ├── app.py                    # ≡ MAIN APPLICATION (3111 lines, monolithic)
    │   ├── database.py               # SQLite data access layer (881 lines)
    │   ├── database_supabase.py      # PostgreSQL/Supabase data access (792 lines)
    │   ├── db_adapter.py             # SQLite↔PostgreSQL adapter (175 lines)
    │   ├── Static/
    │   │   ├── css/
    │   │   │   ├── Style.css         # Custom styles (1310 lines)
    │   │   │   └── tailadmin.css     # Admin template styles (1178 lines)
    │   │   └── uploads/              # 277+ product images (flat + subdirs)
    │   └── templates/                # 38 Jinja2 templates
    │       ├── base_public.html       # Public layout (navbar, footer)
    │       ├── base_admin.html        # Admin layout (sidebar, header)
    │       ├── base_auth.html         # Auth layout (login/register)
    │       ├── base_cliente.html      # Client layout
    │       ├── base_categoria.html    # Dead code (416 lines, unused)
    │       ├── index.html             # Home page
    │       ├── login.html
    │       ├── registro.html / registrar_usuario.html / registro_cliente.html
    │       ├── recuperar_pass.html / reset_password
    │       ├── categoria.html
    │       ├── producto_detalle.html
    │       ├── carrito.html / pago.html / confirmacion_pedido.html / recibo.html
    │       ├── dashboard.html / analysis.html / movimientos.html
    │       ├── ml_predicciones.html   # ML predictions page
    │       ├── reportes.html / mantenimiento.html
    │       ├── admin_productos.html / admin_categorias.html / admin_usuarios.html
    │       ├── admin_clientes.html / admin_ordenes.html
    │       ├── admin_configuracion.html / admin_basedatos.html
    │       ├── admin_mantenimiento.html / admin_respaldos.html
    │       ├── admin_logs.html / admin_webhooks.html
    │       ├── cliente_dashboard.html / cliente_pedidos.html / cliente_perfil.html
    │       └── cambiar_pass.html
    ├── scripts/
    │   ├── seed_reales.py             # Seed: 63 real products, 19 orders, 6 clients
    │   └── generar_datos.py           # Random data generator
    ├── tests/
    │   └── test_checkout.py           # 7 integration tests (checkout, cart, auth)
    ├── data/
    │   ├── stockpro.db                # SQLite database
    │   ├── stockpro.db.backup         # Auto-backup
    │   └── ultimo_backup.txt          # Backup timestamp
    ├── backups/
    │   └── stockpro_20260620_155148.db
    └── node_modules/                  # (for any npm dependencies)
```

## Architecture
**Monolithic Flask MVC** — todo en `app.py` (3111 líneas) sin blueprints:
- **Model**: `database.py` / `database_supabase.py` — funciones directas SQL (sin ORM)
- **View**: Jinja2 templates con herencia (base_public → index/categoria/carrito, base_admin → admin_*, base_auth → login/registro)
- **Controller**: Rutas Flask decoradas con `@app.route()` (~62 rutas)
- **DB Adapter Pattern**: `db_adapter.py` detecta `DATABASE_URL` y elige SQLite o PostgreSQL automáticamente
- **Auth**: Sesión Flask con decoradores `login_required` / `admin_required` + inactividad (60 min)
- **Seguridad**: CSP headers, X-Frame-Options, HSTS, CSRF en todos los forms, CAPTCHA en login/registro, validación de entrada con `MAX_LEN`, `safe_join`, `escape()`
- **ML**: Predicción de demanda con regresión lineal dentro de `app.py`, cacheada en tabla `config`

## Database Tables (15)
| Table | Purpose |
|-------|---------|
| `repuestos` | Motorcycle parts inventory (63 productos reales) |
| `movimientos` | Stock movements (IN/OUT) |
| `alertas` | Low-stock alerts |
| `usuarios` | Users (admin + clientes) |
| `ventas` | Legacy sales |
| `venta_detalle` | Legacy sale items |
| `pedidos` | Orders (current system) |
| `pedido_detalle` | Order line items |
| `pagos` | Payment records |
| `categorias` | Product categories (10: motor, frenos, suspension, etc.) |
| `config` | Key-value configuration (WhatsApp, social, company info) |
| `actividad` | Activity logs |
| `webhooks` | Webhook endpoints |
| `webhook_logs` | Webhook delivery logs |
| `password_resets` | Password reset tokens |

## Entry Points
- **Development**: `cd "Version 1.5" && flask run --host=0.0.0.0 --port=5000 --reload`
- **Production**: `cd "Version 1.5" && python run.py`
- **Docker**: `docker build -t stockpro . && docker run -p 5000:5000 stockpro`
- **Heroku**: `web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.app:app`
- **Seed**: `cd "Version 1.5" && python scripts/seed_reales.py`
- **Tests**: `cd "Version 1.5" && pytest`
- **Admin default**: `admin` / `admin123` (cambiar en producción con env var `ADMIN_PASSWORD`)

## Key Conventions
- **Language**: Spanish (código, templates, comentarios, UI)
- **Naming**: snake_case para funciones/variables Python, PascalCase para clases
- **Templates**: Jinja2 con herencia de `base_*.html`, bloques `{% block titulo %}` / `{% block contenido %}`
- **CSS**: `Style.css` para público, `tailadmin.css` para panel admin (sin Bootstrap por defecto en admin)
- **Font**: Outfit (Google Fonts) unificada en todo el proyecto
- **API**: Rutas `/api/*` retornan JSON, rutas sin `/api/` renderizan templates
- **Cart**: Session-based (`session['carrito']`), precios validados desde BD
- **ML Models**: Entrenados inline en cada request (no persistidos), cacheados con TTL
- **Testing**: pytest, fixture restaura BD, CSRF deshabilitado en tests
- **Git**: Commits descriptivos en español, convención `fix:` / prefijos descriptivos

## Estado Actual (post-Overhaul v2.0)
- **Login**: Arreglado (se borró `session.regenerate()` que no existe en Flask 3.1.3)
- **Botones blancos**: Arreglado (se agregaron 12 vars CSS a Style.css)
- **Export CSV**: Links corregidos (`/api/exportar_csv_completo`)
- **ML Predicciones**: Threshold 7 días mínimo, lag adaptativo
- **NUEVO badge**: 3 días de threshold, gradient pill
- **Badge carrito**: Arreglado (busca `.btn-nav .badge-nav`)
- **Reportes PDF**: Ruta `/admin/reportes` creada
- **CSP**: Content-Security-Policy agregada
- **Tipografía**: Unificada a Outfit

## Overhaul v2.0 — COMPLETADO (commit dba6608)
- **FASE 1 Seguridad**: safe_join, str(e)=0, CORS localhost, captcha fix, session secure
- **FASE 2 DB Adapter**: autocommit=False, rollback(), SQL conversions, set_config() fix
- **FASE 3 Validación**: max(0,...), IDs numéricos, email regex, MAX_LEN, días<=365
- **FASE 4 Rate Limits**: 62 decoradores (antes 41), GETs críticos protegidos
- **FASE 5 Templates**: Bootstrap 5.3.3 unificado, flashes duplicados eliminados

## Issues Conocidos (post-Overhaul)
- `database.py` y `database_supabase.py` no unificados (~80% duplicación)
- Dark theme no integrado (CSS listo, JS toggle no conectado)
- Bloqueo de cuenta por intentos fallidos NO implementado
- `base_categoria.html` NO hereda de `base_public.html` (requiere reestructura)
- `mostrarNotificacion()` duplicada en varios templates
- CSP con `'unsafe-inline'` debilita protección XSS
- Connection pooling en PostgreSQL no implementado
- `app.py` sigue siendo monolito (3000+ líneas)

Para lista completa de bugs (34 documentados), ver `BUG_MEMORY.md`.

## Test de Integración 23/06/2026 (build mode)
| Paso | Resultado |
|------|-----------|
| Login admin | ✅ captcha resuelto |
| Dashboard + 16 admin pages | ✅ todas 200 |
| 3 cliente pages | ✅ |
| Agregar al carrito | ✅ precio real desde BD |
| Checkout completo | ✅ crea pedido + factura |
| Pedido en BD | ✅ IVA incluido correcto |
| Registrar usuario | ✅ redirect a login |
| Logout + protección | ✅ admin pages redirigen |
| 7/7 tests pytest | ✅ pasan |
| 62 endpoints rate-limited | ✅ |
| CSRF activo en todos los forms | ✅ |
| Bcrypt + CAPTCHA | ✅ |

## OpenCode Plugins Instalados
- `opencode-mobile` — QR para conectar iPhone vía OpenLens
- `opencode-firecrawl` — Web scraping de docs
- `opencode-supermemory` — Memoria persistente entre sesiones
- `opencode-notificator` — Notificaciones de escritorio
- `opencode-worktree` — Git worktrees para versiones paralelas
- `opencode-wakatime` — Trackeo de tiempo de coding

## Mobile — Conexión iPhone
- **cloudflared**: Funciona. Comando: `npx cloudflared tunnel --url http://localhost:5000`
- Regla Firewall: `StockPro 5000 TCP`
- QR guardado: `Version 1.5/mobile-qr-cloudflare.png`
- `/mobile` — genera QR para conectar iPhone con OpenLens

## Comandos Importantes
| Acción | Comando |
|--------|---------|
| **Servidor dev** | `cd "Version 1.5" && flask run --host=0.0.0.0 --port=5000 --reload` |
| **Servidor prod** | `cd "Version 1.5" && python run.py` |
| **Seed datos** | `cd "Version 1.5" && python scripts/seed_reales.py` |
| **Tests** | `cd "Version 1.5" && pytest` |
| **Docker** | `cd "Version 1.5" && docker build -t stockpro . && docker run -p 5000:5000 stockpro` |
| **Cloudflared** | `npx cloudflared tunnel --url http://localhost:5000` |
| **QR mobile** | `/mobile` (comando OpenCode) |
