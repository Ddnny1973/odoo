# 🔐 Solución para Errores SMTP de Gmail

## ❌ Error Común
```
535 5.7.8 Username and Password not accepted. For more information, go to
5.7.8  https://support.google.com/mail/?p=BadCredentials
```

## 🎯 Problema
Google ya no permite usar contraseñas normales para aplicaciones externas. Requiere **contraseñas de aplicación** o **OAuth2**.

---

## ✅ Solución 1: Contraseñas de Aplicación (RECOMENDADO)

### **Paso 1: Habilitar Verificación en 2 Pasos**
1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. **Seguridad** → **Verificación en 2 pasos**
3. Actívala si no está habilitada

### **Paso 2: Generar Contraseña de Aplicación**
1. En la misma página, busca **"Contraseñas de aplicación"**
2. O ve directamente a: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Selecciona:
   - **Aplicación**: Correo
   - **Dispositivo**: Otro (nombre personalizado)
   - **Nombre**: "Odoo MB-Asesores"
4. Clic en **"Generar"**
5. **¡IMPORTANTE!** Copia la contraseña de 16 caracteres (ej: `abcd efgh ijkl mnop`)

### **Paso 3: Configurar en Odoo**
1. Ve a **Configuración** → **Técnico** → **Servidores de correo saliente**
2. Edita tu servidor Gmail
3. **Contraseña**: Usa la contraseña de aplicación (NO tu contraseña normal)
4. **Usuario**: tu-email@gmail.com
5. **Servidor SMTP**: smtp.gmail.com
6. **Puerto**: 587
7. **Seguridad**: STARTTLS

---

## ✅ Solución 2: Servidor SMTP Alternativo

### **Outlook/Hotmail (Más Fácil)**
```
Servidor SMTP: smtp-mail.outlook.com
Puerto: 587
Seguridad: STARTTLS
Usuario: tu-email@outlook.com
Contraseña: tu contraseña normal
```

### **SendGrid (Profesional)**
```
Servidor SMTP: smtp.sendgrid.net
Puerto: 587
Usuario: apikey
Contraseña: tu-api-key-de-sendgrid
```

---

## 🔍 Verificar Configuración

### **Probar Envío Manual**
1. Ve a **Configuración** → **Técnico** → **Servidores de correo saliente**
2. Selecciona tu servidor
3. Clic en **"Probar Conexión"**

### **Revisar Logs de Odoo**
```bash
# Linux/WSL
./monitor_envio_correos.sh

# Windows
monitor_envio_correos.bat
```

### **Logs a Buscar**
- ✅ `Estado del correo ID X: sent`
- ❌ `Username and Password not accepted`
- ❌ `BadCredentials`
- 🔐 `SOLUCIÓN GMAIL:`

---

## 🚨 Errores Comunes y Soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `Username and Password not accepted` | Usando contraseña normal | Usar contraseña de aplicación |
| `BadCredentials` | Contraseña incorrecta | Regenerar contraseña de aplicación |
| `530 5.7.0 Authentication Required` | Configuración SMTP incorrecta | Verificar servidor y puerto |
| `Connection refused` | Puerto bloqueado | Usar puerto 587 con STARTTLS |

---

## 💡 Consejos

1. **Contraseña de aplicación es única**: Cada aplicación debe tener su propia contraseña
2. **Guarda la contraseña**: No se puede ver después, solo regenerar
3. **Si no aparece la opción**: Verifica que la verificación en 2 pasos esté activa
4. **Reinicia Odoo**: Después de cambiar la configuración SMTP

---

## 📞 Soporte

Si el problema persiste:
1. Revisa los logs con el script de monitoreo
2. Verifica que la verificación en 2 pasos esté activa
3. Considera usar Outlook en lugar de Gmail
4. Contacta al administrador del sistema
