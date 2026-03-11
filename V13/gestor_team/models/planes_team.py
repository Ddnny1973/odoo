# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class planesTEAM(models.Model):
    _name = 'gestor.planes.team'
    _description = 'Planes TEAM'

    name = fields.Char('Plan')
    codigo = fields.Char('Código')
    codigo_id = fields.Integer('Codigo ID', help='ID del plan - Externo')
    descripcion = fields.Text('Descripción')
    tipo_plan = fields.Many2one('gestor.tipo.plan.team')
    clasificacion = fields.Char('Clasificación', help='Tipología de línea, ej. Abierta, Mixta')
    activo = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")
    nombre_equivalente_ids = fields.Many2many('gestor.nombre.equivalente.plan.team')

    _sql_constraints = [('unq_planes_team_name', 'UNIQUE (name, tipo_plan)',
                         'El nombre del producto ya existe!')]


class tipologialineasplanesTEAM(models.Model):
    _name = 'gestor.tipologia.lineas.planes.team'
    _description = 'Tipología líneas Planes TEAM'

    name = fields.Char('Tipología', help='Tipología de línea, ej. Abierta, Mixta')
    active = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")

    _sql_constraints = [('unq_tipologia_linea_planes_team_name', 'UNIQUE (name)',
                         'La tipología de línea ya existe!')]


class lineasplanesTEAM(models.Model):
    _name = 'gestor.lineas.planes.team'
    _description = 'Líneas de planes RP CLARO'

    name = fields.Char('Línea', help='Línea de planes RP CLARO ej. LINEA NUEVA, UPGRADE, PORTABILIDAD')
    active = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")
    tipo_ids = fields.Many2one('gestor.tipo.plan.team')
    tipo_linea_id = fields.Many2one('gestor.tipo.lineas.planes.team')

    _sql_constraints = [('unq_linea_planes_team_name', 'UNIQUE (name)',
                         'La línea del plan ya existe!')]


class TipolineasplanesTEAM(models.Model):
    _name = 'gestor.tipo.lineas.planes.team'
    _description = 'Tipo de Líneas de planes RP CLARO'

    name = fields.Char('Tipo de Línea')
    id_tips = fields.Integer('ID Tips')
    active = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")
    lineas_planes_ids = fields.One2many('gestor.lineas.planes.team', 'tipo_linea_id', string='Producto1 en RP')

    _sql_constraints = [('unq_tipo_linea_planes_team_name', 'UNIQUE (name)',
                         'La línea del plan ya existe!')]


class CategoriaTipoPlanesTEAM(models.Model):
    _name = 'gestor.categoria.tipo.planes.team'
    _description = 'Categoría tipo planes CLARO'

    name = fields.Char('Categoría', help='Categoría del tipo de plan para control presupuestal ej. Postpago, Postpago PYME, Hogar...')
    active = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")
    informe = fields.Boolean(default=True, string='Informe', help="Mostrar en el informe Comercial.\nNota: Se excluyen las ventas asociadas a esta categoría.")

    _sql_constraints = [('unq_categoria_tipo_planes_team_name', 'UNIQUE (name)',
                         'La línea del plan ya existe!')]


class tipoplanTEAM(models.Model):
    _name = 'gestor.tipo.plan.team'
    _description = 'Valor CFM Planes TEAM'

    name = fields.Char('Tipo', help='Tipo de plan en TIPS ej. Postpago, Especial, Sinergia')
    linea_ids = fields.Many2many('gestor.lineas.planes.team')
    codigo_id = fields.Integer('Codigo ID', help='ID del plan - Externo')
    tipo_producto = fields.Char('Tipo Producto', help='Tipo de producto TIPS')
    activo = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")
    comisiones_ids = fields.Many2many('gestor.comisiones.team')
    categoria_id = fields.Many2one('gestor.categoria.tipo.planes.team')
    plan_id_wz = fields.Integer('Codigo ID', help='ID del plan - Externo')

    _sql_constraints = [('unq_tipo_planes_team_name', 'UNIQUE (name, linea_id)',
                         'El tipo de plan ya existe!')]


class precioplanesTEAM(models.Model):
    _name = 'gestor.precio.planes.team'
    _description = 'Valor CFM Planes TEAM'

    name = fields.Many2one('gestor.planes.team')
    tipologia = fields.Many2one('gestor.tipologia.lineas.planes.team')
    active = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.")
    detalle_precios_planes_ids = fields.One2many('gestor.detalle.precios.planes.team', 'precio_detalle_id')

    _sql_constraints = [('unq_precio_planes_team_name', 'UNIQUE (name, linea, tipologia, fecha)',
                         'El precio del plan para esa fecha ya existe!')]


class DetallePreciosPlanes(models.Model):
    _name = 'gestor.detalle.precios.planes.team'
    _description = 'CFM del Plan'

    precio_detalle_id = fields.Integer('CFM del Plan')
    cfm_con_iva = fields.Float('CFM', help='Cargo fijo mensual CON IVA')
    cfm_sin_iva = fields.Float('CFM sin IVA', help='Cargo fijo mensual SIN IVA')
    fecha_inicio = fields.Date('Fecha Inicio', help='Fecha Inicio de vigencia')
    fecha_fin = fields.Date('Fecha Final', help='Fecha Final de vigencia')


class NombresEquivalentesPlanesTEAM(models.Model):
    _name = 'gestor.nombre.equivalente.plan.team'
    _description = 'Nombres equivalentes planes entre RP, TIPS y CLARO'

    plan_id = fields.Many2many('gestor.planes.team')
    name = fields.Char('Nombre equivalente')
    plan_id_2 = fields.Many2one('gestor.planes.team', string='Nombre equivalente')

    _sql_constraints = [('unq_nombre_equivalente_team_name', 'UNIQUE (name)',
                         'El plan ya tiene una equivalencia!')]

    @api.onchange('plan_id_2')
    def cambiar_nombre(self):
        self.name = self.plan_id_2.name
