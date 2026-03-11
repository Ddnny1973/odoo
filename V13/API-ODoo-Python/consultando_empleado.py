import xmlrpclib

db = "consultorio"
username = "usuario1"
password = "usuario1"
url = "http://159.69.28.121:8009"

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
#Autenticandose en la base de datos
uid = common.authenticate(db, username, password, {})

models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

#Cosnsultando ID del puesto de trabajo
print 'consultando el ID del puesto de trabajo'
job_ids = models.execute_kw(db, uid, password,'hr.job','search',
    [[['name', '=', 'Gestor Documental']]])
print job_ids
print ''
print 'Consultando los ids de los empleados que cumplen con el puesto de trabajo'
print 'Metodo 1: usando el ID del puesto de trabajo'

ids = models.execute_kw(db, uid, password,'hr.employee','search',
    [[['job_id', '=', job_ids]]])
print ids
print ''
print 'Metodo 2: usando el framewor de odoo preguntando directamente por el name del puesto de trabajo'

ids = models.execute_kw(db, uid, password,'hr.employee','search',
    [[['job_id', '=', 'Gestor Documental']]])
print ids    
