import xmlrpclib

db = "consultorio"
username = "usuario1"
password = "usuario1"
url = "http://159.69.28.121:8009"

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
#Autenticandose en la base de datos
uid = common.authenticate(db, username, password, {})

models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

#Buscamos que registros se van a actualiar (empleados cuyo puesto sea Gestor Documental):
ids = models.execute_kw(db, uid, password,'hr.employee','search',
    [[['job_id', '=', 'Gestor Documental']]])

#Revisamos la informacion previa a la actualizacion
contact_cells = models.execute_kw(db, uid, password,'hr.employee','read', [ids],
    {'fields':['name', 'type_ident_id', 'identification_id', 'mobile_phone', 'work_location']})

print 'Antes de actualizar'
print contact_cells
print ''
print ''
#Actualizaremos los campos Direccion de trabajo y ubicacion del trabajo
filas_actualizadas = models.execute_kw(db, uid, password, 'hr.employee', 'write', [ids, {
    'mobile_phone': "999999999",
    'work_location': 'Despues de actualizar'

}])

#Revisamos la informacion despues de actualizar a la actualizacion
contact_cells = models.execute_kw(db, uid, password,'hr.employee','read',[ids],
    {'fields':['name', 'type_ident_id', 'identification_id', 'mobile_phone', 'work_location']})

print 'Despues de actualizar'
print contact_cells

print filas_actualizadas
