# models/vencimientos.py
from odoo import models, fields

class Vencimientos(models.Model):
    _name = 'mb_asesores.vencimientos'
    _description = 'Vencimientos'

    ramo = fields.Char(string='Ramo')
    poliza = fields.Char(string='Poliza')
    id_poliza = fields.Char(string='ID Poliza')
    tomador = fields.Char(string='Tomador')
    nombrecorto = fields.Char(string='Nombre Corto')
    iniciovigencia = fields.Date(string='Inicio Vigencia')
    movil = fields.Char(string='Movil')
    correo = fields.Char(string='Correo')
    mensaje = fields.Char(string='Mensaje')