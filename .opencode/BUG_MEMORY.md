# Bug Memory

## Críticos (corregidos)
| ID | Bug | Archivo | Fix |
|----|-----|---------|-----|
| BUG-001 | Flash messages no se mostraban en base_public.html | base_public.html | Agregado get_flashed_messages() |
| BUG-002 | flash('...', 'error') (categoría inválida) | app.py (25+ ocurrencias) | Cambiado a 'danger' |
| BUG-003 | Flash alert categories no mapeaban danger en base_admin/cliente | base_admin.html, base_cliente.html | Mapeo correcto |
| BUG-004 | SAFOTAWARE en título de base_auth.html | base_auth.html | Cambiado a STOCKPRO |
| BUG-005 | style.css vs Style.css (case mismatch Windows) | base_public, base_auth, base_categoria | Unificado a Style.css |
| BUG-006 | Modal categorías estructura rota | admin_categorias.html | Footer dentro del modal, Reactivar separado |
| BUG-007 | Sin handlers 404/500 | app.py | Agregados con template mantenimiento.html |
| BUG-008 | &aacute; literal en lugar de á | app.py | Reemplazado con Unicode |
| BUG-009 | Fuente Anton en hero de categorías | base_categoria.html | Cambiado a Outfit |
| BUG-010 | Bootstrap Icons versión mezclada | Todos los templates | Unificado a 1.11.1 |
| BUG-016 | Sin favicon | Todos los base templates | Favicon inline SVG agregado |
| BUG-022 | Sin HSTS header | app.py | Strict-Transport-Security agregado |
| BUG-023 | admin123 como password fallback | database.py, database_supabase.py | Cambiado a admin |
| BUG-024 | FLASK_DEBUG default '1' | app.py | Cambiado a '0' |
| BUG-025 | except: pass ocultaba errores | app.py (3 lugares) | Cambiado a traceback.print_exc() |

## Auditoría 28/06/2026 — Hallazgos Nuevos
| ID | Bug | Severidad | Estado |
|----|-----|-----------|--------|
| AUDIT-001 | CSP con 'unsafe-inline' anula protección XSS | 🔴 Crítica | Pendiente |
| AUDIT-002 | +98 innerHTML sin sanitización (XSS almacenado) | 🔴 Crítica | Pendiente |
| AUDIT-003 | Conexiones BD sin try/finally (~90 ubicaciones) | 🔴 Crítica | Pendiente |
| AUDIT-004 | PRAGMA foreign_keys se ignora en PostgreSQL | 🔴 Crítica | Pendiente |
| AUDIT-005 | Sin bloqueo de cuenta por intentos fallidos | 🟠 Alta | Pendiente |
| AUDIT-006 | Rate limits en memoria (se reinician al reiniciar) | 🟠 Alta | Pendiente |
| AUDIT-007 | INSERT OR IGNORE/REPLACE convertido a INSERT plano | 🟠 Alta | Pendiente |
| AUDIT-008 | lastrowid con SELECT LASTVAL() no concurrente | 🟠 Alta | Pendiente |
| AUDIT-009 | Webhook SSRF sin validación de IP interna | 🟠 Alta | Pendiente |
| AUDIT-010 | except: pass en 6+ ubicaciones | 🟠 Alta | Pendiente |
| AUDIT-011 | Endpoint @csrf.exempt (/api/respaldos/crear) | 🟠 Alta | Pendiente |
| AUDIT-012 | Faltan índices (pedido_detalle, pedidos_estado, pedidos_fecha) | 🟠 Alta | Pendiente |

## Documentados (pendientes de priorizar)
| ID | Bug | Severidad |
|----|-----|-----------|
| BUG-011 | Sin límite de intentos login | Media |
| BUG-012 | Sin rate limiting API | Media |
| BUG-013 | Sin Content-Security-Policy | Media |
| BUG-014 | Sin validación tamaño uploads | Baja |
| BUG-015 | SQLi potencial (parámetros en reportes) | Alta (mitigado por parámetros) |
| BUG-017 | Sin nonce CSP en scripts inline | Media |
| BUG-018 | Sin protecciones XSS en templates | Baja (Jinja autoescapado) |
| BUG-019 | Sin logs auditoría | Baja |
| BUG-020 | Sin backup automático BD | Baja |
| BUG-021 | Sin X-Frame-Options | Media |
| BUG-026 | Sin Content-Type-Options | Baja |
| BUG-027 | Sin regeneración session ID en login | Media |
| BUG-028 | Cookies sin Secure flag (HTTP) | Baja |
| BUG-029 | Sin validación email en registro | Baja |
| BUG-030 | Sin tests de seguridad | Media |
| BUG-031 | Sin monitoreo de errores | Baja |
| BUG-032 | Sin logging centralizado | Baja |
| BUG-033 | Sin HTTPS redirect automático | Media |
| BUG-034 | Database connection leaks (sin try/finally) | Alta |
