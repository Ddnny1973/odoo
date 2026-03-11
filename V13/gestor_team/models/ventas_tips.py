# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Ventas(models.Model):
    _name = 'gestor.consulta.ventas.tips'
    _description = 'Ventas registradas en TIPS'

    def _get_categoria_plan(self):
        for registros in self:
            categoria = registros.env['gestor.tipo.plan.team'].search([('name', '=', registros.tipo_plan)])
            registros.categoria_tipo_plan = categoria.categoria_id.name

    def _get_year(self):
        for registros in self:
            registros.year = registros.fecha.strftime("%Y")

    def _get_month(self):
        for registros in self:
            registros.mes = registros.fecha.strftime("%m")

    def _get_presupuesto(self):
        for registros in self:
            categoria_id = registros.env['gestor.categoria.tipo.planes.team'].search([('name', '=', registros.categoria_tipo_plan)])
            presupuesto_id = registros.env['gestor.presupuestos.team'].search([('identificacion_empleado', '=', registros.vendedor_id),
                                                                            ('year', '=', registros.year),
                                                                            ('mes', '=', registros.mes)])
            if presupuesto_id:
                for i in presupuesto_id.presupuesto_detalle_ids.search([('categorias_planes_id.id', '=', categoria_id.id)]):
                    registros.presupuesto = i.presupuesto
            else:
                registros.presupuesto = 0

    fecha = fields.Date('Fecha')
    min = fields.Char('MIN')
    iccid = fields.Char('ICCID')
    imei = fields.Char('IMEI')
    contrato = fields.Char('Contrato')
    valor = fields.Char('Valor')
    custcode = fields.Char('CUSTCODE')
    marca_del_equipo = fields.Char('Marca del equipo')
    nombre_de_equipo_en_stok = fields.Char('Nombre del equipo en STOK')
    nombre_de_la_simcard_en_stok = fields.Char('Nombre de la simcard en STOK')
    modelo_del_equipo = fields.Char('Modelo del equipo')
    valor_del_equipo = fields.Char('Valor del equipo')
    nombre_para_mostrar_del_vendedor = fields.Char('Nombre para mostrar del vendedor')
    tipo_de_vendedor = fields.Char('Tipo de vendedor')
    regional = fields.Char('Regional')
    sucursal = fields.Char('Sucursal')
    ciudad = fields.Char('Ciudad')
    nombre_del_plan = fields.Char('Nombre del plan')
    tipo_de_plan = fields.Char('Tipo de plan')
    valor_cobrado = fields.Char('Valor cobrado')
    codigo_distribuidor = fields.Char('Código de distribuuidor')
    cliente_nombre = fields.Char('Nombre del cliente')
    cliente_id = fields.Char('Código del cliente')
    vendedor_nombre = fields.Char('Nombre del vendedor')
    vendedor_id = fields.Char('Ientificación del vendedor')
    cargo_fijo_mensual = fields.Char('Cargo fijo mensual')
    permanencia_pendiente = fields.Char('Permanencia pendiente')
    clasificacion_del_plan = fields.Char('Claseificación del plan')
    es_multiplay = fields.Boolean('Es multiplay')
    es_upgrade = fields.Boolean('Es upgrade')
    es_linea_nueva = fields.Boolean('Es slínea nueva')
    es_venta_digital = fields.Boolean('Es venta digital')
    es_con_equipo = fields.Boolean('Es con equipo')
    es_telemercadeo = fields.Boolean('Es telemercadeo')
    fecha_de_activacion_en_punto_de_activacion = fields.Date('Fecha de activación')
    usuario_creador = fields.Char('Usuario creador')
    venta_id = fields.Char('Venta ID', help='ID de la venta en TIPS')
    plan_id = fields.Many2one('gestor.planes.team')
    meses = fields.Integer('Meses', help='Tiempo en meses desde la activación a la fecha del cruce')
    valor_a_pagar = fields.Float('Valor a pagar', help='Valor a pagar de la comisión al vendedor')
    estado_tips = fields.Char('Estado TIPS')
    empleado_id = fields.Many2one('hr.employee', index=True)
    categoria_empleado = fields.Char(string='Categoría Empleado', related='empleado_id.category_id.name', store=True)
    cargo = fields.Char(string='Cargo', related='empleado_id.job_id.name', store=True)
    responsable = fields.Many2one('hr.employee', string='Responsable ID', related='empleado_id.parent_id', store=True)
    responsable_nombre = fields.Char(related='responsable.name', string='Responsable', store=True)
    tipo_plan = fields.Char(string='Tipo de Plan',
                            related='plan_id.tipo_plan.name')
    categoria_tipo_plan = fields.Char(string='Categoría Plan',
                                      compute='_get_categoria_plan',
                                      store=True)
    year = fields.Integer('Año', compute='_get_year', store=True, group_operator=False)
    mes = fields.Char('Mes', compute='_get_month', store=True)
    presupuesto = fields.Integer(compute='_get_presupuesto', string='Preuspuesto', store=True, group_operator='avg')
    comision_pagada = fields.Char('Comisión Pagada')
    reconocimiento_pagado = fields.Char('Reconocimiento Pagado')
    tipo_de_activacion = fields.Char('Tipo de Activación')
    con_equipo = fields.Char('Con Equipo')
    cfm = fields.Char('CFM')
    tipo_linea = fields.Char('Tipo de Línea', help='Nueva, Portación o Upgrade y otras opciones de las líneas desde Teps')
