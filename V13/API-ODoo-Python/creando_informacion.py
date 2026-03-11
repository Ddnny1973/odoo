import xmlrpclib

db = "consultorio"
username = "usuario1"
password = "usuario1"
url = "http://159.69.28.121:8009"

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
#Autenticandose en la base de datos
uid = common.authenticate(db, username, password, {})

models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

id = models.execute_kw(db, uid, password, 'hr.employee', 'create',
    [
        {
            'name' : 'Prueba de creacion',
            'identification_id' : '987654321'
        }
    ])

print id
