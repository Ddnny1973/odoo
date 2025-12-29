# Gmail OAuth2 Integration - MB Asesores (Docker/Proxy Reverso)

## Configuración para Entorno Docker con Nginx Proxy Reverso

### Descripción del Entorno
Este módulo está diseñado para funcionar en un entorno Docker detrás de un servidor bastión con nginx como proxy reverso, totalmente independiente de sistemas locales.

### Configuración Paso a Paso

#### 1. Instalar Dependencias en el Contenedor Docker
Las dependencias deben instalarse en el contenedor de Odoo:

```bash
# Desde el host (fuera del contenedor)
docker exec -it nombre_contenedor_odoo pip install -r /mnt/extra-addons/mb-asesores/requirements.txt

# O agregarlo al Dockerfile:
RUN pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

#### 2. Verificar Configuración de Odoo
Asegúrate de que la URL base esté configurada correctamente:

1. Ve a **Configuración → Parámetros del sistema**
2. Busca el parámetro `web.base.url`
3. Debe estar configurado como: `https://aserprem.gestorconsultoria.com.co`

#### 3. Configurar Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Selecciona tu proyecto o crea uno nuevo
3. Habilita **Gmail API**:
   - Ve a "APIs y servicios" → "Biblioteca"
   - Busca "Gmail API" y habilítala

4. Crear credenciales OAuth2:
   - Ve a "APIs y servicios" → "Credenciales"
   - Clic en "Crear credenciales" → "ID de cliente OAuth 2.0"
   - **Tipo de aplicación: "Aplicación web"** (obligatorio para Docker)
   - Nombre: "Odoo Gmail Integration Docker"
   
5. **Configurar URIs de redirección autorizados:**
   ```
   https://aserprem.gestorconsultoria.com.co/gmail/oauth2/callback
   http://localhost:8069/gmail/oauth2/callback
   ```

6. Descarga el archivo JSON de credenciales

#### 4. Configurar en Odoo

1. Ve a **Configuración → Técnico → OAuth2 Gmail**
2. Crea un nuevo registro
3. Completa el email de Gmail
4. Pega el contenido completo del archivo JSON descargado
5. Haz clic en **"🔐 Autenticar con Google"**
6. Se abrirá una nueva pestaña con Google OAuth2
7. Autoriza la aplicación
8. Serás redirigido automáticamente de vuelta a una página de confirmación
9. ¡Listo! La configuración estará autenticada

### Arquitectura del Flujo OAuth2

```
[Navegador] → [nginx Proxy] → [Docker Odoo] → [Google OAuth2]
     ↓                                              ↓
[Callback] ← [nginx Proxy] ← [Docker Odoo] ← [Authorization Code]
```

### Características para Docker

- ✅ **Sin dependencias locales**: Todo funciona a través del navegador web
- ✅ **Compatible con proxy reverso**: Usa las URLs públicas correctas
- ✅ **Callback automático**: Maneja la redirección a través del proxy
- ✅ **Páginas de confirmación**: Muestra éxito/error sin templates adicionales
- ✅ **Logging completo**: Para debugging en contenedores

### Configuración de Nginx (Referencia)

Asegúrate de que tu nginx tenga configurado el proxy para las rutas OAuth2:

```nginx
location /gmail/oauth2/callback {
    proxy_pass http://odoo_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Troubleshooting Docker

**Error: "redirect_uri_mismatch"**
- ✅ Verifica que `web.base.url` esté configurado correctamente
- ✅ Asegúrate de usar "Aplicación web" en Google Console
- ✅ Verifica que la URI exacta esté en Google Console: `https://aserprem.gestorconsultoria.com.co/gmail/oauth2/callback`

**Error: "Dependencias no encontradas"**
```bash
# Instalar en el contenedor
docker exec -it contenedor_odoo pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

**Error: "Configuración no encontrada"**
- Verifica que el callback llegue al contenedor correcto
- Revisa los logs del contenedor: `docker logs contenedor_odoo`

**Error: "access_denied"**
- Asegúrate de autorizar la aplicación en Google
- Verifica que Gmail API esté habilitada

### Logs y Debugging

Para revisar logs en el entorno Docker:
```bash
# Logs de Odoo
docker logs -f contenedor_odoo

# Logs específicos del OAuth2
docker exec -it contenedor_odoo tail -f /var/log/odoo/odoo.log | grep OAuth2
```

### Verificación de Funcionamiento

1. ✅ Dependencias instaladas en el contenedor
2. ✅ `web.base.url` configurado correctamente
3. ✅ Gmail API habilitada en Google Console
4. ✅ Credenciales "Aplicación web" creadas
5. ✅ URI de redirección agregada en Google Console
6. ✅ Archivo JSON configurado en Odoo
7. ✅ Autenticación completada exitosamente
