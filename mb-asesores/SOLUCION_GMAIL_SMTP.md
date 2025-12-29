# 🔐 Solución para Errores SMTP de Gmail

## ❌ Error Común
```
535 5.7.8 Username and Password not accepted. For more information, go to
5.7.8  https://support.google.com/mail/?p=BadCredentials
```

## 🎯 Problema
Google ya no permite usar contraseñas normales para aplicaciones externas. Requiere **contraseñas de aplicación** o **OAuth2**.

---

## ✅ Solución RECOMENDADA: OAuth2 Específico para Gmail

### **⚠️ IMPORTANTE: Gmail y Google Drive son INDEPENDIENTES**
- 📁 **Google Drive**: Para acceso a hojas de cálculo y archivos (ya configurado)
- 📧 **Gmail SMTP**: Para envío de correos (requiere configuración separada)
- 🔑 **Pueden usar cuentas diferentes**: No necesitas la misma cuenta para ambos

### **🆕 OAuth2 Específico (RECOMENDADO)**

#### **Ventajas:**
- 🎯 **Independiente**: No depende de Google Drive
- 🔒 **Más seguro**: Credenciales específicas solo para Gmail
- 📧 **Cualquier cuenta**: Usa cualquier email de Gmail
- 🔄 **Automático**: Tokens se renuevan solos

#### **Pasos:**
1. Ve a **Configuración** → **Email** → **� OAuth2 Gmail**
2. Clic en **"Crear"**
3. Completa tu **email de Gmail**: `tu-correo@gmail.com`
4. Sigue la **"Guía de Configuración"** en la pestaña para:
   - Crear proyecto en Google Cloud Console
   - Habilitar Gmail API
   - Descargar credenciales OAuth2
   - Pegar el archivo JSON en Odoo
5. Clic en **"🔐 Autenticar con Google"**
6. Autoriza en la ventana que se abre
7. ¡Listo! Ahora configura tu servidor SMTP con **OAuth2 Específico**

#### **Configurar Servidor SMTP:**
1. Ve a **Configuración** → **Email** → **Servidores de Correo Saliente**
2. Crea/edita servidor con estos datos:
   - **Servidor SMTP**: `smtp.gmail.com`
   - **Puerto**: `587`
   - **Usuario**: `tu-correo@gmail.com` 
   - **Autenticación**: Selecciona **"OAuth2 Específico"**
   - ✅ Marca **"Usar OAuth2 para Gmail"**
3. Clic en **"Probar Conexión"**

---

## 🚀 RESUMEN DE LA SOLUCIÓN

### **� Para Gmail:** 
1. **OAuth2 Específico** (recomendado): Configuración → 📧 OAuth2 Gmail
2. **OAuth2 desde Google Drive** (solo si es la misma cuenta)  
3. **Contraseña de Aplicación** (más fácil pero menos seguro)

### **📁 Para Google Drive:**
- Configuración independiente (ya está funcionando)
- Se usa solo para hojas de cálculo y archivos

### **🔑 IMPORTANTE:**
- **Gmail y Google Drive SON INDEPENDIENTES**
- **Pueden usar cuentas diferentes**
- **OAuth2 Específico es la solución recomendada**

---

## � Instrucciones Detalladas

### **📧 Método 1: OAuth2 Específico (RECOMENDADO)**

#### **🎯 Ventajas:**
- ✅ **Independiente**: No necesita Google Drive
- ✅ **Cualquier cuenta**: Funciona con cualquier Gmail
- ✅ **Más seguro**: Credenciales específicas para email
- ✅ **Fácil gestión**: Se maneja por separado

#### **📋 Pasos:**
1. **Configurar OAuth2:**
   - Ve a **Configuración** → **Email** → **📧 OAuth2 Gmail**
   - Clic **"Crear"** → Completa tu email Gmail
   - Sigue la **"Guía de Configuración"**
   - Descarga credenciales desde Google Cloud Console
   - Pega el JSON y autentica

2. **Configurar Servidor SMTP:**
   - Ve a **Configuración** → **Email** → **Servidores de Correo Saliente**
   - Crear/editar servidor:
     - **Servidor**: `smtp.gmail.com`
     - **Puerto**: `587`
     - **Usuario**: `tu-email@gmail.com`
     - **Autenticación**: **"OAuth2 Específico"**
   - **Probar Conexión**

### **🔄 Método 2: OAuth2 desde Google Drive**

#### **⚠️ Solo usar si:**
- El email de Gmail es **exactamente la misma cuenta** de Google Drive
- Google Drive ya está funcionando

#### **📋 Pasos:**
1. Identificar cuenta de Google Drive activa
2. Usar **"OAuth2 desde Google Drive"** en autenticación
3. Configurar con el mismo email

### **🔑 Método 3: Contraseña de Aplicación**

#### **📋 Pasos:**
1. Ve a tu **cuenta Gmail** → **Seguridad**
2. Habilita **"Verificación en 2 pasos"**
3. Genera **"Contraseña de aplicación"**
4. Usa esa contraseña de 16 caracteres en Odoo
5. Autenticación: **"Login"**

---

## 🛠️ Resolución de Problemas

### **❌ Error: "Username and Password not accepted"**
- ✅ **Solución**: Usar OAuth2 Específico o Contraseña de Aplicación
- ❌ **No funciona**: Contraseñas normales de Gmail

### **❌ Error: "No se encontró configuración OAuth2"**
- ✅ **Solución**: Configurar OAuth2 Específico primero
- 📍 **Ubicación**: Configuración → 📧 OAuth2 Gmail

### **❌ Error: "Las credenciales están configuradas para otra cuenta"**
- ✅ **Solución 1**: Usar OAuth2 Específico para tu cuenta
- ✅ **Solución 2**: Cambiar email a la cuenta de Google Drive
- ✅ **Solución 3**: Usar Contraseña de Aplicación

### **❌ Error: "Google Drive no está configurado"**
- ✅ **Solución**: Cambiar a OAuth2 Específico (independiente de Google Drive)

---

## 📞 Soporte

Si sigues teniendo problemas:
1. Revisa los logs de Odoo para errores específicos
2. Verifica que tengas los permisos correctos en Google Cloud Console
3. Asegúrate de que Gmail API esté habilitada
4. Contacta al administrador del sistema

**💡 Recomendación**: Siempre usar **OAuth2 Específico** para máxima flexibilidad y seguridad.

---

## ✅ Método Alternativo: Contraseñas de Aplicación

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
| `no configuró un campo obligatorio` | Campo requerido vacío en wizard | Completa todos los campos según el tipo elegido |

### 🔧 Problemas con el Asistente de Configuración

**Error: "no configuró un campo obligatorio"**
- **SOLUCIÓN**: Asegúrate de completar el campo de email antes de hacer clic en "Siguiente"
- **OAuth2**: Ingresa tu email de Gmail completo (ej: `usuario@gmail.com`)
- **Contraseña de Aplicación**: Ingresa tanto el email como la contraseña de 16 caracteres
- **Servidor Alternativo**: Completa usuario, contraseña y servidor SMTP

**Error: "Google Drive no está configurado"**
- Ve a **Configuración** → **Google Drive** y configúralo primero
- Luego regresa al asistente Gmail y selecciona OAuth2

**Error: "Wrong value for smtp_authentication: gmail_oauth2"**
- Este error indica que el módulo necesita ser actualizado
- Ve a **Aplicaciones** → busca "MB Asesores" → **Actualizar**
- O reinicia el servicio Odoo para cargar los cambios

**Error: "Compute method failed to assign smtp_authentication_info"**
- Error de caché en campos computados
- **SOLUCIÓN**: Actualiza el módulo "MB Asesores" 
- O reinicia Odoo completamente

**Error: "El email de Gmail es obligatorio" (pero el campo está lleno)**
- Problema de sincronización entre UI y servidor
- **SOLUCIÓN**: 
  1. Limpia el campo email completamente
  2. Vuelve a escribir el email completo
  3. Espera 2 segundos antes de hacer clic en "Siguiente"
  4. Si persiste, cierra el wizard y ábrelo nuevamente

**Error: "Las credenciales de Google Drive están configuradas para 'cuenta1' pero intentas configurar Gmail para 'cuenta2'"**
- **CAUSA**: Intentas usar OAuth2 con una cuenta diferente a la de Google Drive
- **SOLUCIONES**:
  1. **Cambiar el email en el wizard**: Usa la misma cuenta que aparece en el error
  2. **Reconfigurar Google Drive**: Ve a Configuración → Google Drive y configura la cuenta deseada
  3. **Usar contraseña de aplicación**: Cambia a "Contraseña de Aplicación" en el wizard

**Conexión exitosa pero credenciales misteriosas**
- Si el test dice "conexión establecida" pero no sabes de dónde vienen las credenciales
- **Explicación**: OAuth2 usa tokens de Google Drive ya configurados
- **Verificar**: Ve a logs de Odoo para ver detalles de autenticación
- **Verificar cuenta**: Ve a Configuración → Google Drive para ver qué cuenta está configurada

### 📋 Diferencias entre los Menús

**🔐 Configurar Gmail** (Asistente - Recomendado)
- Interfaz guiada paso a paso
- Validación automática de requisitos
- Configuración automática de OAuth2
- Ideal para usuarios nuevos

**⚙️ Configuración Avanzada Gmail**
- Formulario directo sin asistente
- Para usuarios que conocen todos los parámetros
- Acceso a todas las opciones de servidor SMTP
- Para configuraciones personalizadas

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
