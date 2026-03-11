import xmlrpclib

db = "consultorio"
username = "usuario1"
password = "usuario1"
url = "http://159.69.28.121:8009"

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

#uid trae el id del modelo res.users
print uid