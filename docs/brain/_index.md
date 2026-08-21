---
title: "Cerebro — Proyecto Odoo"
type: project-brain
repo: odoo
tags: [odoo, docker, conexion, mb-asesores, consola]
related:
  - "[[../../../Conocimiento/docs/brain/_index.md]]"
updated: 2026-08-21
owner: EQUIPO
---

# Cerebro Digital — Proyecto Odoo

Repo personal con múltiples módulos Odoo custom para distintos clientes y casos de uso.

## Estructura general

- **mb-asesores/** — Módulo de gestión de asesorías (Google Drive + Sheets + Odoo)
  - `consola/notebook.py` — Script de sincronización de pólizas y envío de correos
- **gc_apartamentos/** — Gestión de apartamentos y reconciliación
- **condominium/** — Funcionalidades de condominio
- **V13/** — Módulos legacy Odoo v13
- **Ai-Mindnovation-*** — Proyectos de análisis estratégico

## Conocimiento operativo

### mb-asesores/consola — Conexión a Odoo en Docker

**Problema recurrente:** El script `notebook.py` fallaba al conectarse a Odoo en contenedor.

**Causa raíz:** 
- Puerto mapeado (8029 externo) ≠ Puerto interno (8069)
- Cuando el script corre DENTRO del contenedor, debe usar puerto interno

**Solución (2026-08-21):**
```python
# ANTES (incorrecto para contenedor):
odoo = ODOO('localhost', port=8029)  # ❌ 8029 es el puerto externo

# DESPUÉS (correcto para contenedor):
odoo = ODOO('localhost', port=8069)  # ✅ 8069 es el puerto interno de Odoo
```

**Configuración docker-compose:**
```
web:
  image: odoo:16
  ports:
    - "8029:8069"  # 8029 (externo) → 8069 (interno)
```

**Regla:** Cuando ejecutas scripts desde dentro de un contenedor Docker:
- Usa puertos internos (los que el servicio define en su contenedor)
- No uses los puertos mapeados (los que mapeas en docker-compose)

### Deuda técnica — Refactor de notebook.py

El módulo `consola/notebook.py` sigue teniendo hardcoded:
- Credenciales de Odoo (usuario, contraseña)
- Credenciales de Google Drive
- Rutas de Google Drive
- Parámetros de conexión

**Siguiente paso:** Refactorizar a variables de entorno o `.env` file (usuario comentó: "ese módulo de consola no me gusta").

## Links útiles

- [Cerebro global — ReposPersonal/Conocimiento](../../../Conocimiento/docs/brain/_index.md)
