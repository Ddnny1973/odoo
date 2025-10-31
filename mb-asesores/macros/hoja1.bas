Sub CallOdooFunction()
    Dim objRequest As Object
    Dim strUrl As String
    Dim strResponse As String
    Dim uid As Integer
    
    Dim registros_actualizados As String
    Dim duracion As String
    
    Dim xmlDoc As Object
    Set xmlDoc = CreateObject("MSXML2.DOMDocument")
    
    ' Mostrar progreso
    Application.StatusBar = "Iniciando descarga de vencimientos..."
    Application.ScreenUpdating = False
    
    On Error GoTo ErrorHandler
    
    ' Limpiar respuestas anteriores
    Sheets("Hoja1").Range("A4:A5").ClearContents
    
    ' Leer parámetros básicos (sin validación ya que esta función no los usa)
    Dim mes As String, anno As String, hojas As String
    mes = Trim(CStr(Sheets("Hoja1").Range("B1").Value))
    anno = Trim(CStr(Sheets("Hoja1").Range("B2").Value))
    hojas = Trim(CStr(Sheets("Hoja1").Range("B3").Value))
    
    ' Crear conexión con timeouts optimizados
    Set objRequest = CreateObject("MSXML2.ServerXMLHTTP")
    objRequest.setTimeouts 30000, 30000, 30000, 120000
    
    ' Autenticar con Odoo
    uid = AuthenticateOdoo(objRequest)
    If uid = 0 Then
        MsgBox "Error: No se pudo autenticar con Odoo", vbCritical, "Error de Autenticación"
        GoTo CleanExit
    End If

    ' Cambiar la URL para la llamada a la función
    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/object"
    
    Application.StatusBar = "Ejecutando descarga de vencimientos..."

    ' Preparar llamada sin parámetros
    Dim strPostData As String
    strPostData = "<?xml version=""1.0""?>" & _
              "<methodCall>" & _
              "<methodName>execute_kw</methodName>" & _
              "<params>" & _
              "<param><value><string>aserprem</string></value></param>" & _
              "<param><value><int>" & uid & "</int></value></param>" & _
              "<param><value><string>Api_2024</string></value></param>" & _
              "<param><value><string>mb_asesores.vencimientos</string></value></param>" & _
              "<param><value><string>descarga_vencimientos</string></value></param>" & _
              "<param><value><array><data/></array></value></param>" & _
              "</params>" & _
              "</methodCall>"
    
    ' Debug: Guardar request en celda para diagnóstico
    Sheets("Hoja1").Range("A15").Value = strPostData
    
    ' Ejecutar llamada
    objRequest.Open "POST", strUrl, False
    objRequest.setRequestHeader "Content-Type", "text/xml"
    objRequest.send strPostData

    ' Procesar respuesta
    strResponse = objRequest.responseText
    
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
    
    ' Extraer valores de la respuesta con validación
    Dim regNode As Object, durNode As Object
    
    Set regNode = xmlDoc.SelectSingleNode("//member[name='registros_actualizados']/value/int")
    Set durNode = xmlDoc.SelectSingleNode("//member[name='duracion']/value/string")
    
    If Not regNode Is Nothing Then registros_actualizados = regNode.Text
    If Not durNode Is Nothing Then duracion = durNode.Text

    ' Actualizar celdas con resultados
    Sheets("Hoja1").Range("A4").Value = "Registros actualizados: " & registros_actualizados
    Sheets("Hoja1").Range("A5").Value = "Duración: " & duracion

    ' Mostrar resultado mejorado
    MsgBox "[EXITO] Descarga de vencimientos completada:" & vbCrLf & vbCrLf & _
           "RESUMEN:" & vbCrLf & _
           "Registros actualizados: " & registros_actualizados & vbCrLf & _
           "Duración: " & duracion & vbCrLf & vbCrLf & _
           "Proceso completado exitosamente", vbInformation, "Descarga de Vencimientos"

CleanExit:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    Exit Sub
    
ErrorHandler:
    MsgBox "Error inesperado: " & Err.Description & vbCrLf & "Línea: " & Erl, vbCritical, "Error"
    GoTo CleanExit

End Sub



Sub CallOdooFunctionWithParameters()
    Dim objRequest As Object
    Dim strUrl As String
    Dim strResponse As String
    Dim uid As Integer
    
    Dim registros_actualizados As String
    Dim duracion As String
    Dim registros_enviados As String
    Dim registros_no_enviados As String
    Dim status As String
    
    Dim xmlDoc As Object
    Set xmlDoc = CreateObject("MSXML2.DOMDocument")
    
    ' Mostrar progreso
    Application.StatusBar = "Iniciando descarga de vencimientos con parámetros..."
    Application.ScreenUpdating = False
    
    On Error GoTo ErrorHandler
    
    ' Limpiar respuestas anteriores
    Sheets("Hoja1").Range("A4:A5").ClearContents
    
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
    
    ' Obtener hojas seleccionadas de forma optimizada
    hojas = ObtenerHojasSeleccionadas()
    
    ' Crear conexión con timeouts optimizados
    Set objRequest = CreateObject("MSXML2.ServerXMLHTTP")
    objRequest.setTimeouts 30000, 30000, 30000, 300000  ' Timeout más largo para procesos con WhatsApp
    
    Application.StatusBar = "Autenticando con Odoo..."
    
    ' Autenticar con Odoo
    uid = AuthenticateOdoo(objRequest)
    If uid = 0 Then
        MsgBox "Error: No se pudo autenticar con Odoo", vbCritical, "Error de Autenticación"
        GoTo CleanExit
    End If

    ' Cambiar la URL para la llamada a la función
    strUrl = "https://aserprem.gestorconsultoria.com.co/xmlrpc/2/object"
    
    Application.StatusBar = "Ejecutando descarga de vencimientos con parámetros... (esto puede tomar varios minutos)"

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
              "<param><value><string>descarga_vencimientos</string></value></param>" & _
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

    ' Ejecutar proceso
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
    
    ' Extraer solo el estado para mostrar mensaje y terminar
    Dim statusNode As Object
    Set statusNode = xmlDoc.SelectSingleNode("//member[name='status']/value/string")
    If Not statusNode Is Nothing Then status = statusNode.Text
    
    ' Mostrar mensaje de proceso en ejecución y terminar
    If LCase(Trim(status)) = "running" Or LCase(Trim(status)) = "enviando whatsapp" Then
        MsgBox "La descarga de vencimientos ha sido iniciada en el servidor." & vbCrLf & vbCrLf & _
               "El proceso continuará en segundo plano y recibirá un correo al finalizar." & vbCrLf & vbCrLf & _
               "Puede cerrar esta ventana y continuar trabajando normalmente.", vbInformation, "Proceso iniciado en servidor"
    ElseIf LCase(Trim(status)) = "waiting" Then
        MsgBox "El sistema está esperando operaciones previas. Intente nuevamente más tarde.", vbInformation, "Sistema en espera"
    ElseIf LCase(Trim(status)) = "stop" Then
        MsgBox "El proceso ha sido detenido por el sistema. Contacte al administrador si persiste el problema.", vbExclamation, "Proceso detenido"
    Else
        MsgBox "La solicitud ha sido enviada. Estado recibido: " & status, vbInformation, "Solicitud enviada"
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
' FUNCIONES AUXILIARES COMPARTIDAS
' ===============================================
' Nota: Si estas funciones ya existen en modulo1.bas, 
' puedes eliminar estas duplicadas y referenciar las del otro módulo

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


