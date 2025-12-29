# Script de Verificación y Corrección - Sistema de Envío de Correos
# Versión: 1.0 - PowerShell
# Fecha: $(Get-Date)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🔍 VERIFICACIÓN SISTEMA ENVÍO CORREOS" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

# Función para verificar Docker
function Check-Docker {
    Write-Host "`n📦 Verificando Docker..." -ForegroundColor Yellow
    
    try {
        $dockerInfo = docker ps 2>$null
        if ($dockerInfo -match "odoo") {
            Write-Host "✅ Contenedor Odoo está ejecutándose" -ForegroundColor Green
            $containerId = (docker ps | Select-String "odoo").Line.Split()[0]
            Write-Host "🆔 Container ID: $containerId" -ForegroundColor Cyan
            return $true
        } else {
            Write-Host "❌ Contenedor Odoo no está ejecutándose" -ForegroundColor Red
            Write-Host "💡 Ejecuta: docker-compose up -d" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "❌ Docker no está disponible o no está corriendo" -ForegroundColor Red
        Write-Host "💡 Asegúrate de que Docker Desktop esté iniciado" -ForegroundColor Yellow
        return $false
    }
}

# Función para verificar archivos del módulo
function Check-Module {
    Write-Host "`n🔧 Verificando módulo mb-asesores..." -ForegroundColor Yellow
    
    $basePath = ".\mb-asesores"
    $vencimientosPath = "$basePath\models\vencimientos.py"
    $manifestPath = "$basePath\__manifest__.py"
    
    if (Test-Path $vencimientosPath) {
        Write-Host "✅ vencimientos.py encontrado" -ForegroundColor Green
        
        # Verificar método corregido
        $content = Get-Content $vencimientosPath -Raw
        if ($content -match "_get_mail_server_for_email") {
            Write-Host "✅ Método _get_mail_server_for_email encontrado" -ForegroundColor Green
        } else {
            Write-Host "❌ Método _get_mail_server_for_email NO encontrado" -ForegroundColor Red
        }
        
        # Verificar corrección de typo
        if ($content -match 'subject = fields\.Char') {
            Write-Host "✅ Campo 'subject' corregido (typo arreglado)" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Campo 'subject' podría tener errores tipográficos" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ vencimientos.py NO encontrado en $vencimientosPath" -ForegroundColor Red
    }
    
    if (Test-Path $manifestPath) {
        Write-Host "✅ __manifest__.py encontrado" -ForegroundColor Green
    } else {
        Write-Host "❌ __manifest__.py NO encontrado" -ForegroundColor Red
    }
}

# Función para verificar archivos de macros VBA
function Check-VBAMacros {
    Write-Host "`n📊 Verificando macros VBA..." -ForegroundColor Yellow
    
    $macrosPath = ".\mb-asesores\macros"
    $hoja1Path = "$macrosPath\hoja1.bas"
    $modulo1Path = "$macrosPath\modulo1.bas"
    
    if (Test-Path $hoja1Path) {
        Write-Host "✅ hoja1.bas encontrado" -ForegroundColor Green
        
        # Verificar que no haya emojis
        $content = Get-Content $hoja1Path -Raw
        if ($content -match '[😀-🙏🚀-🛿⚀-⛿✀-⟿➰-➿⤀-⬿⭀-⯿]') {
            Write-Host "⚠️ Posibles emojis encontrados en hoja1.bas" -ForegroundColor Yellow
        } else {
            Write-Host "✅ Sin emojis en hoja1.bas (corregido)" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ hoja1.bas NO encontrado" -ForegroundColor Red
    }
    
    if (Test-Path $modulo1Path) {
        Write-Host "✅ modulo1.bas encontrado" -ForegroundColor Green
        
        # Verificar que no haya emojis
        $content = Get-Content $modulo1Path -Raw
        if ($content -match '[😀-🙏🚀-🛿⚀-⛿✀-⟿➰-➿⤀-⬿⭀-⯿]') {
            Write-Host "⚠️ Posibles emojis encontrados en modulo1.bas" -ForegroundColor Yellow
        } else {
            Write-Host "✅ Sin emojis en modulo1.bas (corregido)" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ modulo1.bas NO encontrado" -ForegroundColor Red
    }
}

# Función para verificar documentación
function Check-Documentation {
    Write-Host "`n📚 Verificando documentación..." -ForegroundColor Yellow
    
    $docsPath = ".\mb-asesores\macros"
    $docs = @(
        "CAMBIOS_EMOJIS_CORREGIDOS.md",
        "SOLUCION_ERROR_VBA.md", 
        "SOLUCION_BUG_CORREOS_VACIO.md",
        "RESUMEN_FINAL_PROYECTO.md",
        "SOLUCION_OAUTH2_SMTP_ERROR.md",
        "CORRECCION_METODO_MAIL_SERVER.md",
        "DIAGNOSTICO_OAUTH2_COMPLETO.md"
    )
    
    foreach ($doc in $docs) {
        $docPath = "$docsPath\$doc"
        if (Test-Path $docPath) {
            Write-Host "✅ $doc" -ForegroundColor Green
        } else {
            Write-Host "❌ $doc NO encontrado" -ForegroundColor Red
        }
    }
}

# Función para mostrar diagnóstico OAuth2
function Show-OAuth2Diagnosis {
    Write-Host "`n🔐 Diagnóstico OAuth2 - Error 535" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "📋 Cuentas configuradas:" -ForegroundColor Yellow
    Write-Host "   ✅ ddnny73@gmail.com (FUNCIONA)" -ForegroundColor Green
    Write-Host "   ❌ administracion@mbasesoresenseguros.com (ERROR 535)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔍 Pasos para solucionar:" -ForegroundColor Yellow
    Write-Host "   1. Regenerar token OAuth2 para administracion@" -ForegroundColor Cyan
    Write-Host "   2. Verificar usuarios autorizados en Google Cloud Console" -ForegroundColor Cyan
    Write-Host "   3. Confirmar scopes de Gmail API" -ForegroundColor Cyan
    Write-Host "   4. Revisar restricciones de dominio empresarial" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📄 Ver archivo: DIAGNOSTICO_OAUTH2_COMPLETO.md" -ForegroundColor Yellow
}

# Función para mostrar logs de Docker
function Show-DockerLogs {
    Write-Host "`n📋 ¿Deseas ver los logs de Odoo? (y/N): " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    
    if ($response -match '^[Yy]$') {
        Write-Host "📋 Últimas 20 líneas de logs de Odoo:" -ForegroundColor Cyan
        try {
            $containerId = (docker ps | Select-String "odoo").Line.Split()[0]
            docker logs --tail 20 $containerId
        } catch {
            Write-Host "❌ No se pudieron obtener los logs" -ForegroundColor Red
        }
    }
}

# Función para reiniciar servicios
function Restart-Services {
    Write-Host "`n🔄 ¿Deseas reiniciar el contenedor Odoo? (y/N): " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    
    if ($response -match '^[Yy]$') {
        Write-Host "🔄 Reiniciando contenedor Odoo..." -ForegroundColor Cyan
        try {
            docker-compose restart odoo
            Write-Host "⏳ Esperando que el servicio esté listo..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
            Check-Docker | Out-Null
        } catch {
            Write-Host "❌ Error al reiniciar el contenedor" -ForegroundColor Red
        }
    }
}

# Función principal
function Main {
    Write-Host "🚀 Iniciando verificación del sistema..." -ForegroundColor Green
    
    # Verificaciones básicas
    $dockerOk = Check-Docker
    Check-Module
    Check-VBAMacros
    Check-Documentation
    
    # Mostrar diagnóstico OAuth2
    Show-OAuth2Diagnosis
    
    Write-Host "`n============================================" -ForegroundColor Cyan
    Write-Host "✅ Verificación completada" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Cyan
    
    # Opciones adicionales
    if ($dockerOk) {
        Show-DockerLogs
        Restart-Services
    }
    
    Write-Host "`n📚 Archivos de documentación disponibles:" -ForegroundColor Yellow
    Write-Host "   - DIAGNOSTICO_OAUTH2_COMPLETO.md" -ForegroundColor Cyan
    Write-Host "   - RESUMEN_FINAL_PROYECTO.md" -ForegroundColor Cyan
    Write-Host "   - SOLUCION_OAUTH2_SMTP_ERROR.md" -ForegroundColor Cyan
    Write-Host "   - CORRECCION_METODO_MAIL_SERVER.md" -ForegroundColor Cyan
    
    Write-Host "`n🎯 Próximos pasos:" -ForegroundColor Yellow
    Write-Host "   1. Regenerar OAuth2 para administracion@mbasesoresenseguros.com" -ForegroundColor Cyan
    Write-Host "   2. Probar envío de correos desde Odoo" -ForegroundColor Cyan
    Write-Host "   3. Verificar que funcionen ambas cuentas Gmail" -ForegroundColor Cyan
    Write-Host "   4. Probar las macros VBA actualizadas" -ForegroundColor Cyan
    
    Write-Host "`n💡 Para ejecutar una prueba completa:" -ForegroundColor Yellow
    Write-Host "   1. Abre Odoo en el navegador" -ForegroundColor Cyan
    Write-Host "   2. Ve a Configuración > Parámetros técnicos > Servidores de correo" -ForegroundColor Cyan
    Write-Host "   3. Regenera OAuth2 para administracion@" -ForegroundColor Cyan
    Write-Host "   4. Prueba el envío de correos" -ForegroundColor Cyan
}

# Ejecutar función principal
Main

# Pausar para que el usuario pueda leer los resultados
Write-Host "`nPresiona cualquier tecla para continuar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
