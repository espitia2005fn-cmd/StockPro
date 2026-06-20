# Ilia - Memoria del Proyecto StockPro

## Identidad
- Me llamo **ilia**
- Soy el agente de IA que mantiene y desarrolla StockPro
- Este archivo es mi memoria persistente del proyecto

## Proyecto: StockPro
Sistema de gestion de inventarios, ventas y analitica con ML para tienda de motopartes.

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

### Issues Conocidos
- Test ID 501 falla (producto no existe en seed nuevo)
- ~8 endpoints filtran `str(e)` en vez de mensaje generico
- `database.py` y `database_supabase.py` no unificados
- Dark theme no integrado (disponible en escritorio)

### Servidor
- `http://192.168.0.5:5000` (local: `http://localhost:5000`)
- `--reload` activo

### Configuracion
- `C:\Users\Juan Espi\.config\opencode\opencode.json` - config principal
- `C:\Users\Juan Espi\.config\opencode\commands\mobile.md` - comando /mobile
- Node.js v24.16.0 / npm 11.13.0
- opencode-mobile plugin instalado para conectar iPhone via OpenLens

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
