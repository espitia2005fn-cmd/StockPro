# ADR - Architectural Decision Log

## ADR-001: Big Data como eje del proyecto
- **Contexto**: Proyecto universitario U. Cundinamarca, se necesita Big Data como valor agregado
- **Decisión**: Incorporar análisis predictivo y visualización de datos como funcionalidad principal
- **Implementación**: ECharts 5.5.0 para dashboards, módulo ml_predicciones.html para predicciones

## ADR-002: Persistencia híbrida SQLite + Supabase
- **Contexto**: Desarrollo local con SQLite, producción con Supabase/PostgreSQL
- **Decisión**: db_adapter.py como capa de abstracción entre ambos
- **Estado**: SQLite funcional, Supabase pendiente de credenciales

## ADR-003: Priorizar bugs críticos antes que features
- **Contexto**: Múltiples bugs heredados del template original
- **Decisión**: Auditoría completa primero, fixes críticos antes de nuevo diseño
- **Resultado**: 25+ bugs corregidos en una sesión

## ADR-004: Outfit como fuente única
- **Contexto**: El proyecto mezclaba Anton, Bebas Neue, Inter y Outfit
- **Decisión**: Unificar toda la app bajo Outfit (300-800 weight)
- **Motivo**: Coherencia visual, rendimiento (una sola carga de Google Fonts)

## ADR-005: Bootstrap Icons versión única
- **Contexto**: Mezcla de bootstrap-icons@1.11.0 y 1.11.1
- **Decisión**: Unificar a 1.11.1 en todos los templates
- **Motivo**: Consistencia, evitar conflictos de versión
