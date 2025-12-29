# Guía Visual: Solucionar Error 403 access_denied

## 🎯 Problema Actual
**Error 403: access_denied** - Google rechaza el acceso después de seleccionar la cuenta

## 📍 Ubicación del Problema
✅ **redirect_uri** está correcto (HTTPS)  
❌ **Acceso denegado** por configuración de Google Console

## 🔧 Solución Principal: Agregar Test Users

### Paso 1: Navegar a Google Cloud Console
```
https://console.cloud.google.com
→ Seleccionar tu proyecto
→ Menú lateral: "APIs y servicios"
→ "Pantalla de consentimiento OAuth"
```

### Paso 2: Verificar Estado de la App
Buscar en la página:
```
Publishing status: [Testing/In production]
```

### Paso 3: Agregar Test Users (Si está en "Testing")
En la misma página, buscar:
```
┌─────────────────────────────────────┐
│ Test users                          │
│ ┌─────────────────┐                 │
│ │   ADD USERS     │ ← Hacer clic    │
│ └─────────────────┘                 │
└─────────────────────────────────────┘
```

### Paso 4: Agregar Email
En el campo que aparece, escribir:
```
┌──────────────────────────────────────┐
│ usuario@gmail.com                    │ ← Email EXACTO del formulario Odoo
└──────────────────────────────────────┘
[ADD] ← Clic
```

### Paso 5: Verificar Gmail API
```
APIs y servicios → Biblioteca → Buscar "Gmail API"
```
Debe mostrar: **"API habilitada" ✅**

## 🔄 Después de la Configuración

1. **Esperar 5-10 minutos** para propagación
2. **Actualizar módulo** mb-asesores en Odoo
3. **Intentar autenticación** nuevamente
4. **Verificar** que usas el mismo email en ambos lugares

## ⚡ Cambios en el Código

**Reducidos los scopes OAuth2:**
- ❌ Antes: `gmail.send` + `mail.google.com` (más restrictivo)
- ✅ Ahora: solo `gmail.send` (menos restrictivo)

## 🎯 Checklist Final

- [ ] App en modo "Testing" 
- [ ] Email agregado como "Test User"
- [ ] Gmail API habilitada
- [ ] URI redirección: `https://aserprem.gestorconsultoria.com.co/gmail/oauth2/callback`
- [ ] Mismo email en Odoo y Google
- [ ] Esperado 10 minutos después de cambios

## 🚨 Si Persiste el Error

1. **Probar con cuenta Gmail personal** (no empresarial)
2. **Crear nuevo proyecto** en Google Cloud Console
3. **Navegador incógnito** para evitar cache
4. **Verificar restricciones** de organización G Suite

---

**Estado actual:** redirect_uri ✅ → access_denied ❌ → Test Users 🔧
