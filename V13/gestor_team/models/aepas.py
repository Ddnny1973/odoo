# -*- coding: utf-8 -*-
from odoo import models, fields


class Aepas(models.Model):
    _name = 'gestor.aepas.team'
    _description = 'AEPAS'

    co_id = fields.Char('Co Id')
    tele_numb = fields.Char('Tele Numb')
    iccid = fields.Char('Iccid', index=True)
    activacion = fields.Date('Activacion')
    razon_inicial = fields.Char('Razon Inicial')
    clasecausalinic = fields.Char('Clasecausalinic')
    clasecausalfin = fields.Char('Clasecausalfin')
    ef = fields.Char('Ef')
    prep = fields.Char('Prep')
    tmcyspc = fields.Char('Tmcyspc')
    dia_aepa = fields.Char('Dia Aepa')
    cd_agente = fields.Char('Cd Agente')
    custcode_agente = fields.Char('Custcode Agente')
    nomdistribuidor = fields.Char('Nomdistribuidor')
    vl_acum_recargas = fields.Char('Vl Acum Recargas')
    clase_prepago = fields.Char('Clase Prepago')
    tipo = fields.Char('Tipo')
    producto = fields.Char('Producto')
    canal_comercial = fields.Char('Canal Comercial')
    subcanal = fields.Char('Subcanal')
    direccion = fields.Char('Direccion')
    gerencia = fields.Char('Gerencia')
    departamento = fields.Char('Departamento')
    nit = fields.Char('Nit')
    unidad = fields.Char('Unidad')
    sim_prendida = fields.Boolean('Sim Prendida')
    vendedor = fields.Char('Vendedor')
    cedula_vendedor = fields.Char('Cédula Vendedor')
    vendedor_id = fields.Many2one('hr.employee', index=True)
    id_responsable = fields.Many2one('hr.employee', string='Responsable')
    codigo_aepas_id = fields.Many2one('gestor.codigos.aepas.team')
    codigo_aepas = fields.Char(related='codigo_aepas_id.descripcion', string='Código AEPAS', store=True)
    year = fields.Integer('Año')
    mes = fields.Char('Mes')

    sql_constraints = [('unq_DP_team_iccid', 'UNIQUE (iccid)',
                        'El registro ya existe!')
                        ]

    class CodigosAepas(models.Model):
        _name = 'gestor.codigos.aepas.team'
        _description = 'Códigos AEPAS'

        name = fields.Char('Código')
        descripcion = fields.Char('Descripción  AEPAS')

        sql_constraints = [('unq_DP_team_name', 'UNIQUE (name)',
                            'El registro ya existe!')
                           ]
