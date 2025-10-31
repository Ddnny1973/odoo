Sub get_status()
    Dim objRequest As Object
    Dim strUrl As String
    Dim strResponse As String
    Dim uid As Integer
    Dim numberString As String
    
    Dim xmlDoc As Object
    Set xmlDoc = CreateObject("MSXML2.DOMDocument")
    
    ' Mostrar progreso
    Application.StatusBar = "Obteniendo estado actual de Odoo..."
    Application.ScreenUpdating = False
    
    On Error GoTo ErrorHandler
    
    ' Crear un nuevo objeto de solicitud
    Set objRequest = CreateObject("MSXML2.ServerXMLHTTP")
    
    ' Establecer el tiempo de espera en segundos
    objRequest.setTimeouts 30000, 30000, 30000, 120000
    
    ' Autenticar y obtener UID
    uid = AuthenticateOdoo(objRequest)
    If uid = 0 Then
        MsgBox "Error: No se pudo autenticar con Odoo", vbCritical, "Error de Autenticación"
        GoTo CleanExit
    End If

    ' Cambiar la URL para la llamada a la función
    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/object"

    ' sin parámetros
    Dim strPostData As String
    strPostData = "<?xml version=""1.0""?>" & _
              "<methodCall>" & _
              "<methodName>execute_kw</methodName>" & _
              "<params>" & _
              "<param><value><string>aserprem</string></value></param>" & _
              "<param><value><int>" & uid & "</int></value></param>" & _
              "<param><value><string>Api_2024</string></value></param>" & _
              "<param><value><string>mb_asesores.vencimientos</string></value></param>" & _
              "<param><value><string>get_status</string></value></param>" & _
              "<param><value><array><data/></array></value></param>" & _
              "</params>" & _
              "</methodCall>"
              
    ' Ejecutar llamada a método
    objRequest.Open "POST", strUrl, False
    objRequest.setRequestHeader "Content-Type", "text/xml"
    objRequest.send strPostData

    ' Manejar la respuesta
    strResponse = objRequest.responseText
    
    ' Verificar si hay errores en la respuesta
    If InStr(strResponse, "<fault>") > 0 Then
        MsgBox "Error en la respuesta de Odoo: " & strResponse, vbCritical, "Error del Servidor"
        GoTo CleanExit
    End If
    
    ' Cargar la respuesta XML
    xmlDoc.async = False
    If Not xmlDoc.LoadXML(strResponse) Then
        MsgBox "Error al procesar la respuesta XML", vbCritical, "Error de Procesamiento"
        GoTo CleanExit
    End If
    
    ' Extraer valores de la respuesta
    Dim status As String, hojas As String, mes As String
    Dim statusNode As Object, hojasNode As Object, mesNode As Object
    
    Set statusNode = xmlDoc.SelectSingleNode("//member[name='status']/value/string")
    Set hojasNode = xmlDoc.SelectSingleNode("//member[name='hojas']/value/string")
    Set mesNode = xmlDoc.SelectSingleNode("//member[name='mes']/value/string")
    
    If Not statusNode Is Nothing Then status = statusNode.Text
    If Not hojasNode Is Nothing Then hojas = hojasNode.Text
    If Not mesNode Is Nothing Then mes = mesNode.Text
    
    ' Actualizar celdas con validación
    If status <> "" Then Sheets("Hoja1").Range("I2").Value = status
    If mes <> "" Then Sheets("Hoja1").Range("B2").Value = mes
    
    ' Mostrar resultado mejorado que coincide con la estructura de vencimientos.py
    MsgBox "[ESTADO] Estado actual del sistema obtenido exitosamente" & vbCrLf & vbCrLf & _
           "Estado del sistema: " & status & vbCrLf & _
           "Mes configurado: " & mes & vbCrLf & _
           "Hojas disponibles: " & hojas & vbCrLf & vbCrLf & _
           "Los datos han sido sincronizados con la hoja de Excel" & vbCrLf & vbCrLf & _
           "[INFO] Estados posibles del sistema:" & vbCrLf & _
           "• idle/inactivo: Listo para nuevas operaciones" & vbCrLf & _
           "• running: Procesando descarga de vencimientos" & vbCrLf & _
           "• sending: Enviando notificaciones WhatsApp" & vbCrLf & _
           "• waiting: Esperando completar operaciones", vbInformation, "Estado del Sistema - Vencimientos"

CleanExit:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    Exit Sub
    
ErrorHandler:
    MsgBox "Error inesperado: " & Err.Description & vbCrLf & "Línea: " & Erl, vbCritical, "Error"
    GoTo CleanExit

End Sub

Sub CallOdooActualizarEstadoGeneral(Optional soloActualizar As Boolean = False)
    Dim objRequest As Object
    Dim strUrl As String
    Dim strResponse As String
    Dim uid As Integer
    
    Dim xmlDoc As Object
    Set xmlDoc = CreateObject("MSXML2.DOMDocument")
    
    ' Mostrar progreso
    If Not soloActualizar Then
        Application.StatusBar = "Actualizando estado general en Odoo..."
        Application.ScreenUpdating = False
    End If
    
    On Error GoTo ErrorHandler
    
    ' Leer datos de la hoja con validación
    Dim status_new As String, mes_new As String, year_new As String, hojas_new As String
    status_new = Trim(CStr(Sheets("Hoja1").Range("I1").Value))
    mes_new = UCase(Trim(CStr(Sheets("Hoja1").Range("B2").Value)))
    year_new = Trim(CStr(Sheets("Hoja1").Range("B1").Value))
    
    ' Validar datos requeridos
    If status_new = "" Or mes_new = "" Or year_new = "" Then
        MsgBox "Error: Faltan datos requeridos:" & vbCrLf & _
               "Status: " & status_new & vbCrLf & _
               "Mes: " & mes_new & vbCrLf & _
               "Año: " & year_new, vbCritical, "Datos Incompletos"
        GoTo CleanExit
    End If
    
    ' Obtener hojas seleccionadas de forma más eficiente
    hojas_new = ObtenerHojasSeleccionadas()
    
    ' Crear conexión con timeouts optimizados
    Set objRequest = CreateObject("MSXML2.ServerXMLHTTP")
    objRequest.setTimeouts 30000, 30000, 30000, 120000
    
    ' Autenticar
    uid = AuthenticateOdoo(objRequest)
    If uid = 0 Then
        MsgBox "Error: No se pudo autenticar con Odoo", vbCritical, "Error de Autenticación"
        GoTo CleanExit
    End If

    ' Cambiar la URL para la llamada a la función
    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/object"

    ' Construir parámetros con validación
    Dim strPostData As String
    strPostData = "<?xml version=""1.0""?>" & _
                  "<methodCall>" & _
                  "<methodName>execute_kw</methodName>" & _
                  "<params>" & _
                  "<param><value><string>aserprem</string></value></param>" & _
                  "<param><value><int>" & uid & "</int></value></param>" & _
                  "<param><value><string>Api_2024</string></value></param>" & _
                  "<param><value><string>mb_asesores.vencimientos</string></value></param>" & _
                  "<param><value><string>actualizar_estado_general</string></value></param>" & _
                  "<param><value><array><data>" & _
                  "<value><string>" & EscapeXML(status_new) & "</string></value>" & _
                  "<value><string>" & EscapeXML(mes_new) & "</string></value>" & _
                  "<value><string>" & EscapeXML(hojas_new) & "</string></value>" & _
                  "<value><string>" & EscapeXML(year_new) & "</string></value>" & _
                  "</data></array></value></param>" & _
                  "</params>" & _
                  "</methodCall>"
              
    ' Ejecutar llamada
    objRequest.Open "POST", strUrl, False
    objRequest.setRequestHeader "Content-Type", "text/xml"
    objRequest.send strPostData

    ' Procesar respuesta
    strResponse = objRequest.responseText
    
    ' Verificar errores
    If InStr(strResponse, "<fault>") > 0 Then
        MsgBox "Error en la respuesta de Odoo: " & strResponse, vbCritical, "Error del Servidor"
        GoTo CleanExit
    End If
    
    xmlDoc.async = False
    If Not xmlDoc.LoadXML(strResponse) Then
        MsgBox "Error al procesar la respuesta XML", vbCritical, "Error de Procesamiento"
        GoTo CleanExit
    End If
    
    ' Extraer valores de la respuesta con validación
    Dim status As String, observaciones As String, mes As String, year As String, hojas As String
    Dim statusNode As Object, obsNode As Object, mesNode As Object, yearNode As Object, hojasNode As Object
    
    Set statusNode = xmlDoc.SelectSingleNode("//member[name='status']/value/string")
    Set obsNode = xmlDoc.SelectSingleNode("//member[name='observaciones']/value/string")
    Set mesNode = xmlDoc.SelectSingleNode("//member[name='mes']/value/string")
    Set yearNode = xmlDoc.SelectSingleNode("//member[name='year']/value/string")
    Set hojasNode = xmlDoc.SelectSingleNode("//member[name='hojas']/value/string")
    
    If Not statusNode Is Nothing Then status = statusNode.Text
    If Not obsNode Is Nothing Then observaciones = obsNode.Text
    If Not mesNode Is Nothing Then mes = mesNode.Text
    If Not yearNode Is Nothing Then year = yearNode.Text
    If Not hojasNode Is Nothing Then hojas = hojasNode.Text
    
    ' Actualizar celda con el status
    If status <> "" Then Sheets("Hoja1").Range("I2").Value = status
          
    If Not soloActualizar Then
        ' Mostrar resultado detallado que coincide con la lógica de vencimientos.py
        Dim mensaje As String
        mensaje = "[ACTUALIZADO] Estado del sistema actualizado exitosamente" & vbCrLf & vbCrLf & _
                 "INFORMACION ACTUALIZADA EN ODOO:" & vbCrLf & _
                 "Estado del sistema: " & status & vbCrLf & _
                 "Año configurado: " & year & vbCrLf & _
                 "Mes configurado: " & mes & vbCrLf & _
                 "Hojas seleccionadas: " & hojas & vbCrLf & vbCrLf
        
        If observaciones <> "" Then
            mensaje = mensaje & "OBSERVACIONES DEL SISTEMA:" & vbCrLf & observaciones & vbCrLf & vbCrLf
        End If
        
        mensaje = mensaje & "El sistema está configurado y listo para:" & vbCrLf & _
                           "• Descarga de vencimientos desde Google Drive" & vbCrLf & _
                           "• Envío automático de correos" & vbCrLf & _
                           "• Notificaciones por WhatsApp" & vbCrLf & _
                           "• Actualización de archivos en la nube"
        
        MsgBox mensaje, vbInformation, "Configuración Actualizada - Sistema"
    End If

CleanExit:
    If Not soloActualizar Then
        Application.StatusBar = False
        Application.ScreenUpdating = True
    End If
    Exit Sub
    
ErrorHandler:
    MsgBox "Error inesperado: " & Err.Description & vbCrLf & "Línea: " & Erl, vbCritical, "Error"
    GoTo CleanExit

End Sub

Sub CallConsolaWithParameters()
    ' Mostrar progreso inicial
    Application.StatusBar = "Iniciando proceso de consola con parámetros..."
    Application.ScreenUpdating = False
    
    On Error GoTo ErrorHandler
    
    ' Primero actualizar parámetros del archivo
    Application.StatusBar = "Actualizando parámetros del archivo..."
    CallOdooActualizarEstadoGeneral (True)

    Dim objRequest As Object
    Dim strUrl As String
    Dim strResponse As String
    Dim uid As Integer
    
    Dim xmlDoc As Object
    Set xmlDoc = CreateObject("MSXML2.DOMDocument")
    
    ' Leer parámetros con validación
    Dim mes As String, anno As String, hojas As String
    Dim mensajes_whatsapp As String, control_mails As String, estado_provision As String
    Dim control_mensajes As String
    
    mes = Trim(CStr(Sheets("Hoja1").Range("B2").Value))
    anno = Trim(CStr(Sheets("Hoja1").Range("B1").Value))
    mensajes_whatsapp = Trim(CStr(Sheets("Hoja1").Range("B6").Value))
    control_mails = Trim(CStr(Sheets("Hoja1").Range("B7").Value))
    estado_provision = Trim(CStr(Sheets("Hoja1").Range("B8").Value))
    
    ' Validar datos críticos
    If mes = "" Or anno = "" Then
        MsgBox "Error: Faltan datos críticos (mes o año)", vbCritical, "Datos Incompletos"
        GoTo CleanExit
    End If
    
    control_mensajes = mensajes_whatsapp & "," & control_mails & "," & estado_provision
    
    ' Obtener hojas seleccionadas
    hojas = ObtenerHojasSeleccionadas()
    
    ' Crear conexión con timeouts optimizados
    Set objRequest = CreateObject("MSXML2.ServerXMLHTTP")
    objRequest.setTimeouts 30000, 30000, 30000, 300000
    
    Application.StatusBar = "Autenticando con Odoo..."
    
    ' Autenticar
    uid = AuthenticateOdoo(objRequest)
    If uid = 0 Then
        MsgBox "Error: No se pudo autenticar con Odoo", vbCritical, "Error de Autenticación"
        GoTo CleanExit
    End If
    
    ' Cambiar la URL para la llamada a la función
    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/object"
    
    Application.StatusBar = "Ejecutando proceso de consola... (esto puede tomar varios minutos)"

    ' Construir parámetros estructurados con validación XML
    Dim strPostData As String
    strPostData = "<?xml version=""1.0""?>" & _
              "<methodCall>" & _
              "<methodName>execute_kw</methodName>" & _
              "<params>" & _
              "<param><value><string>aserprem</string></value></param>" & _
              "<param><value><int>" & uid & "</int></value></param>" & _
              "<param><value><string>Api_2024</string></value></param>" & _
              "<param><value><string>mb_asesores.vencimientos</string></value></param>" & _
              "<param><value><string>consola</string></value></param>" & _
              "<param>" & _
              "<value><struct>" & _
              "<member><name>" & EscapeXML(mes) & "</name><value><string>" & EscapeXML(mes) & "</string></value></member>" & _
              "<member><name>" & EscapeXML(anno) & "</name><value><string>" & EscapeXML(anno) & "</string></value></member>" & _
              "<member><name>" & EscapeXML(hojas) & "</name><value><string>" & EscapeXML(hojas) & "</string></value></member>" & _
              "<member><name>" & EscapeXML(control_mensajes) & "</name><value><string>" & EscapeXML(control_mensajes) & "</string></value></member>" & _
              "</struct></value>" & _
              "</param>" & _
              "</params>" & _
              "</methodCall>"

    ' Ejecutar proceso de consola
    objRequest.Open "POST", strUrl, False
    objRequest.setRequestHeader "Content-Type", "text/xml"
    objRequest.send strPostData

    ' Procesar respuesta
    strResponse = objRequest.responseText
    
    Application.StatusBar = "Procesando respuesta del servidor..."
    
    ' Verificar errores en la respuesta
    If InStr(strResponse, "<fault>") > 0 Then
        MsgBox "Error en la respuesta de Odoo: " & strResponse, vbCritical, "Error del Servidor"
        GoTo CleanExit
    End If
    
    xmlDoc.async = False
    If Not xmlDoc.LoadXML(strResponse) Then
        MsgBox "Error al procesar la respuesta XML", vbCritical, "Error de Procesamiento"
        GoTo CleanExit
    End If
    
    ' Extraer resultados con validación mejorada
    Dim salida As String, errorMsg As String
    Dim salidaNode As Object, errorNode As Object
    
    Set salidaNode = xmlDoc.SelectSingleNode("//member[name='salida']/value/string")
    Set errorNode = xmlDoc.SelectSingleNode("//member[name='error']/value/string")
    
    If Not salidaNode Is Nothing Then salida = salidaNode.Text
    If Not errorNode Is Nothing Then errorMsg = errorNode.Text
    
    ' Mostrar resultados detallados que coinciden con vencimientos.py
    If errorMsg <> "" Then
        MsgBox "[ERROR] Error durante el proceso de consola:" & vbCrLf & vbCrLf & _
               "DETALLE DEL ERROR:" & vbCrLf & errorMsg & vbCrLf & vbCrLf & _
               "PARAMETROS UTILIZADOS EN EL PROCESO:" & vbCrLf & _
               "Mes: " & mes & vbCrLf & _
               "Año: " & anno & vbCrLf & _
               "Hojas seleccionadas: " & hojas & vbCrLf & _
               "Configuración de control: " & control_mensajes & vbCrLf & vbCrLf & _
               "ACCIONES SUGERIDAS:" & vbCrLf & _
               "• Verifique la conexión a Google Drive" & vbCrLf & _
               "• Valide que las hojas existan en el archivo" & vbCrLf & _
               "• Contacte al administrador si persiste", vbCritical, "Error en Proceso de Consola"
    Else
        Dim mensaje As String
        mensaje = "[COMPLETADO] Proceso de consola completado exitosamente" & vbCrLf & vbCrLf & _
                 "OPERACION EJECUTADA: Descargar desde Google Drive" & vbCrLf & _
                 "RESUMEN DEL PROCESO:" & vbCrLf & _
                 "Período procesado: " & mes & " " & anno & vbCrLf & _
                 "Hojas procesadas: " & hojas & vbCrLf & _
                 "Configuración aplicada: " & control_mensajes & vbCrLf & vbCrLf
        
        If salida <> "" Then
            mensaje = mensaje & "SALIDA DETALLADA DEL PROCESO:" & vbCrLf & _
                               "```" & vbCrLf & salida & vbCrLf & "```" & vbCrLf & vbCrLf
        End If
        
        mensaje = mensaje & "RESULTADOS OBTENIDOS:" & vbCrLf & _
                           "• Las URL del archivo Google Sheet han sido actualizadas" & vbCrLf & _
                           "• Los correos de vencimiento han sido enviados" & vbCrLf & _
                           "• Las notificaciones WhatsApp están en proceso" & vbCrLf & vbCrLf & _
                           "El sistema está listo para nuevas operaciones"
        
        MsgBox mensaje, vbInformation, "Proceso de Consola Completado"
    End If

CleanExit:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    Exit Sub
    
ErrorHandler:
    MsgBox "Error inesperado: " & Err.Description & vbCrLf & "Línea: " & Erl, vbCritical, "Error"
    GoTo CleanExit

End Sub

' ===============================================
' FUNCIONES AUXILIARES MEJORADAS
' ===============================================

' Función para autenticar con Odoo y obtener UID
Function AuthenticateOdoo(objRequest As Object) As Integer
    Dim strUrl As String
    Dim strPostData As String
    Dim strResponse As String
    Dim startPos As Integer, endPos As Integer
    Dim numberString As String
    
    On Error GoTo AuthError
    
    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/common"
    
    strPostData = "<?xml version=""1.0""?>" & _
                  "<methodCall>" & _
                  "<methodName>authenticate</methodName>" & _
                  "<params>" & _
                  "<param><value><string>aserprem</string></value></param>" & _
                  "<param><value><string>api@gestorconsultoria.com.co</string></value></param>" & _
                  "<param><value><string>Api_2024</string></value></param>" & _
                  "<param><value><array><data></data></array></value></param>" & _
                  "</params>" & _
                  "</methodCall>"
    
    objRequest.Open "POST", strUrl, False
    objRequest.setRequestHeader "Content-Type", "text/xml"
    objRequest.send strPostData
    
    strResponse = objRequest.responseText
    
    ' Verificar errores comunes
    If InStr(strResponse, "502 Bad Gateway") > 0 Then
        MsgBox "Error: 502 Bad Gateway. Servidor no disponible.", vbCritical, "Error de Conexión"
        AuthenticateOdoo = 0
        Exit Function
    End If
    
    If InStr(strResponse, "<fault>") > 0 Then
        MsgBox "Error de autenticación: " & strResponse, vbCritical, "Error de Autenticación"
        AuthenticateOdoo = 0
        Exit Function
    End If
    
    ' Extraer UID
    startPos = InStr(strResponse, "<int>") + Len("<int>")
    endPos = InStr(strResponse, "</int>")
    
    If startPos > Len("<int>") And endPos > startPos Then
        numberString = Mid(strResponse, startPos, endPos - startPos)
        AuthenticateOdoo = CInt(numberString)
    Else
        AuthenticateOdoo = 0
    End If
    
    Exit Function
    
AuthError:
    MsgBox "Error durante autenticación: " & Err.Description, vbCritical, "Error de Autenticación"
    AuthenticateOdoo = 0
End Function

' Función para obtener hojas seleccionadas de forma optimizada
Function ObtenerHojasSeleccionadas() As String
    Dim lastRow As Integer
    Dim hojas As String
    Dim i As Integer
    Dim siEncontrado As Boolean
    Dim valorCelda As String
    
    On Error GoTo HojasError
    
    ' Encontrar la última fila con datos
    lastRow = Sheets("Hoja1").Cells(Rows.Count, "A").End(xlUp).Row
    
    ' Asegurar que no vayamos más allá de la fila 1000 por seguridad
    If lastRow > 1000 Then lastRow = 1000
    
    hojas = ""
    siEncontrado = False
    
    ' Procesar desde la fila 11 hasta la última fila
    For i = 11 To lastRow
        valorCelda = Trim(LCase(CStr(Sheets("Hoja1").Cells(i, 2).Value)))
        
        If valorCelda = "si" Then
            If siEncontrado Then
                hojas = hojas & ","
            End If
            hojas = hojas & Trim(CStr(Sheets("Hoja1").Cells(i, 1).Value))
            siEncontrado = True
        End If
    Next i
    
    ObtenerHojasSeleccionadas = hojas
    Exit Function
    
HojasError:
    MsgBox "Error al obtener hojas seleccionadas: " & Err.Description, vbCritical, "Error"
    ObtenerHojasSeleccionadas = ""
End Function

' Función para escapar caracteres especiales en XML
Function EscapeXML(text As String) As String
    Dim result As String
    result = text
    result = Replace(result, "&", "&amp;")
    result = Replace(result, "<", "&lt;")
    result = Replace(result, ">", "&gt;")
    result = Replace(result, """", "&quot;")
    result = Replace(result, "'", "&apos;")
    EscapeXML = result
End Function

' Función para mostrar progreso detallado
Sub MostrarProgreso(mensaje As String)
    Application.StatusBar = mensaje
    DoEvents  ' Permite que Excel actualice la interfaz
End Sub

Sub CallOdooSendMailReport()
    Dim objRequest As Object
    Dim strUrl As String
    Dim strResponse As String
    Dim uid As Integer
    Dim xmlDoc As Object
    Set xmlDoc = CreateObject("MSXML2.DOMDocument")

    Application.StatusBar = "Ejecutando reporte de correos en Odoo..."
    Application.ScreenUpdating = False

    On Error GoTo ErrorHandler

    ' Leer el mes desde la hoja
    Dim mes As String
    mes = Trim(CStr(Sheets("Hoja1").Range("B2").Value))
    If mes = "" Then
        MsgBox "Error: El mes no está definido.", vbCritical, "Datos Incompletos"
        GoTo CleanExit
    End If

    Set objRequest = CreateObject("MSXML2.ServerXMLHTTP")
    objRequest.setTimeouts 30000, 30000, 30000, 120000

    uid = AuthenticateOdoo(objRequest)
    If uid = 0 Then
        MsgBox "Error: No se pudo autenticar con Odoo", vbCritical, "Error de Autenticación"
        GoTo CleanExit
    End If

    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/object"

    ' Construir la llamada XML-RPC para send_mail_report
    Dim strPostData As String
    strPostData = "<?xml version=""1.0""?>" & _
                  "<methodCall>" & _
                  "<methodName>execute_kw</methodName>" & _
                  "<params>" & _
                  "<param><value><string>aserprem</string></value></param>" & _
                  "<param><value><int>" & uid & "</int></value></param>" & _
                  "<param><value><string>Api_2024</string></value></param>" & _
                  "<param><value><string>mb_asesores.vencimientos</string></value></param>" & _
                  "<param><value><string>send_mail_report</string></value></param>" & _
                  "<param><value><array><data>" & _
                  "<value><string>" & EscapeXML(mes) & "</string></value>" & _
                  "</data></array></value></param>" & _
                  "</params>" & _
                  "</methodCall>"

    objRequest.Open "POST", strUrl, False
    objRequest.setRequestHeader "Content-Type", "text/xml"
    objRequest.send strPostData

    strResponse = objRequest.responseText

    If InStr(strResponse, "<fault>") > 0 Then
        MsgBox "Error en la respuesta de Odoo: " & strResponse, vbCritical, "Error del Servidor"
        GoTo CleanExit
    End If

    xmlDoc.async = False
    If Not xmlDoc.LoadXML(strResponse) Then
        MsgBox "Error al procesar la respuesta XML", vbCritical, "Error de Procesamiento"
        GoTo CleanExit
    End If

    ' Extraer el resultado del reporte
    Dim resultNode As Object
    Set resultNode = xmlDoc.SelectSingleNode("//string")
    If Not resultNode Is Nothing Then
        MsgBox "Resultado del reporte: " & resultNode.Text, vbInformation, "Reporte de Correos"
    Else
        MsgBox "No se pudo obtener el resultado del reporte.", vbExclamation, "Reporte de Correos"
    End If

CleanExit:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    Exit Sub

ErrorHandler:
    MsgBox "Error inesperado: " & Err.Description & vbCrLf & "Línea: " & Erl, vbCritical, "Error"
    GoTo CleanExit
End Sub
