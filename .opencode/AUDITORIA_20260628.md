# Auditoría Completa StockPro — 28/06/2026

## Resumen Ejecutivo

| Área | Estado | Hallazgos |
|------|--------|-----------|
| **Seguridad** | MODERADO | 4 CRÍTICOS, 8 ALTOS, 8 MEDIOS, 6 BAJOS |
| **Base de Datos** | MODERADO | 3 CRÍTICOS, 4 ALTOS, 3 MEDIOS, 1 BAJO |
| **Funcionalidad** | BUENO | 7/7 tests pasan, 13/13 bugs previstos siguen fijos |
| **Regresiones** | 2 corregidas | BUG-010 (bootstrap icons), BUG-016 (favicon) |

---

## 🔴 Hallazgos Críticos

### C-1: CSP con `'unsafe-inline'` anula protección XSS
- **Archivo**: `app.py:239-240`
- **Impacto**: Cualquier script inyectado se ejecuta. Combinado con +98 `.innerHTML` en templates, hay un chain de XSS almacenado viable.
- **Fix**: Implementar nonces, quitar `'unsafe-inline'`, mover scripts inline a archivos externos.

### C-2: +98 `.innerHTML` en templates sin sanitización
- **Archivo**: Múltiples templates (dashboard.html, analysis.html, admin_*.html, cliente_*.html)
- **Impacto**: Un producto con nombre `<script>...</script>` ejecuta JS en el admin que lo vea.
- **Fix**: Usar `escHtml()` o `textContent` en vez de `innerHTML`.

### C-3: Conexiones a BD sin `try/finally` en ~90 ubicaciones
- **Archivo**: `app.py`, `database.py`, `database_supabase.py`
- **Impacto**: Cualquier excepción entre `get_db()` y `conn.close()` fuga la conexión. Con SQLite: archivos bloqueados. Con PostgreSQL: agota conexiones.
- **Fix**: Envolver toda operación de BD en `try/finally`.

### C-4: `PRAGMA` en adapter se reemplaza por `SELECT 1`
- **Archivo**: `db_adapter.py:62-63`
- **Impacto**: En PostgreSQL, `PRAGMA foreign_keys = ON` se ignora. Integridad referencial desactivada.
- **Fix**: Implementar manejo correcto de PRAGMAs.

---

## 🟠 Hallazgos Altos

### H-1: Sin bloqueo de cuenta por intentos fallidos
- **Archivo**: `app.py:800-834`
- **Fix**: Agregar columna `failed_attempts` + `locked_until` en `usuarios`.

### H-2: Rate limits en memoria (`memory://`) — se reinician al reiniciar
- **Archivo**: `app.py:41`
- **Fix**: Usar Redis en producción.

### H-3: `INSERT OR IGNORE/REPLACE` convertido a `INSERT` plano en adapter
- **Archivo**: `db_adapter.py:64-67`
- **Fix**: Convertir a `ON CONFLICT DO NOTHING` / `ON CONFLICT DO UPDATE`.

### H-4: `lastrowid` usa `SELECT LASTVAL()` — no concurrente
- **Archivo**: `db_adapter.py:133-137`
- **Fix**: Usar `RETURNING id` directamente en INSERTs.

### H-5: Webhook SSRF — sin validación de URL contra IPs internas
- **Archivo**: `database.py:871-884`, `database_supabase.py:635-648`
- **Fix**: Bloquear rangos RFC1918, validar esquema HTTPS.

### H-6: `except: pass` en 6+ ubicaciones
- **Archivo**: `app.py:125,133,2832,2928,2966,3054`, `database.py:94,98`
- **Fix**: Reemplazar con `except Exception:` + logging.

### H-7: Un endpoint CSRF-exempt (`@csrf.exempt`)
- **Archivo**: `app.py:3004`
- **Fix**: Remover `@csrf.exempt`.

### H-8: Faltan índices clave (`pedido_detalle(pedido_id)`, `pedidos(estado)`, `pedidos(fecha)`)
- **Archivo**: `database.py:252-258`
- **Fix**: Agregar los 3 índices.

---

## 🟡 Hallazgos Medios

- Contraseñas SMTP con default vacío (`app.py:73-74`)
- `_convert()` regex frágil para fechas (`db_adapter.py:70-73`)
- Token de reset no se invalida tras uso (`database.py:567-582`)
- Validación de uploads solo por extensión/MIME, no por magic bytes (`app.py:1681-1694`)
- Off-by-one-second en query de dashboard PG (`database_supabase.py:756`)
- Datos de orden en cookie de sesión (lado cliente) (`app.py:483-497`)

---

## ✅ Bugs Regresados y Corregidos Hoy

| Bug | Descripción | Fix |
|-----|------------|-----|
| **BUG-010** | `base_auth.html` usaba bootstrap-icons@1.11.0 (debía ser 1.11.1) | ✅ Corregido |
| **BUG-016** | `base_auth.html` sin favicon | ✅ Corregido |

---

## ✅ 7/7 Tests Pasan

```
test_carrito_agregar_precio_validado ✅
test_carrito_agregar_producto_inexistente ✅
test_carrito_agregar_cantidad_invalida ✅
test_confirmar_pedido_sin_carrito ✅
test_login_admin ✅
test_api_eliminar_producto ✅
test_api_pedido_detalle_idor ✅
```

---

## Recomendaciones por Prioridad

### Semana 1 (IMPACTO INMEDIATO)
1. CSP nonces + quitar `'unsafe-inline'`
2. Función `escHtml()` global + reemplazar `innerHTML` críticos
3. Envolver conexiones BD en `try/finally`
4. Arreglar `PRAGMA` en adapter

### Semana 2 (SEGURIDAD)
5. Bloqueo de cuenta por intentos fallidos
6. Remover `@csrf.exempt`
7. Validación de webhook URLs (SSRF)
8. Reemplazar `except: pass` con logging

### Semana 3 (BD Y RENDIMIENTO)
9. Agregar índices faltantes
10. `INSERT OR IGNORE/REPLACE` → `ON CONFLICT`
11. `lastrowid` → `RETURNING id`
12. Validación de uploads por magic bytes

---

*Auditoría generada el 28/06/2026 — 3 skills usados: security-reviewer, code-explorer, bug-tracker-memory*
