# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Sucursales(models.Model):
    _name = 'gestor.sucursales'
    _description = 'Sucursales o puntos de venta de ciudad'

    @api.onchange('state_id','country_id','cities')
    def cityfilter(self):
        if self.cities:
            return {'domain': {'cities': [('state_id', '=?', self.state_id.id)],'postal_id': [('city_id', '=?', self.cities.id)]}}
        elif self.state_id:
            return {'domain': {'cities': [('state_id', '=?', self.state_id.id)],'postal_id': [('state_id', '=?', self.state_id.id)]}}
        elif self.country_id:
            return {'domain': {'cities': [('state_id', '=', False)],'postal_id': [('country_id', '=?', self.country_id.id)]}}
        else:
            return {'domain': {'cities': [('state_id', '!=', False)],'postal_id': [('state_id', '!=', False)]}}

    name = fields.Char('Nombre Sucursal')
    codigo = fields.Char('Código')
    tipo = fields.Selection([('Oficina', 'oficina'),
                             ('Sede', 'sede'),
                             ('Local', 'local')])
    country_id = fields.Many2one('res.country', string='País')
    state_id = fields.Many2one('res.country.state', domain="[('country_id', '=', country_id)]", string='Departamento')
    cities = fields.Many2one('l10n_co_cities.city', context="{'default_state_id': state_id}", domain="[('state_id', '=', state_id)]", string='Ciudad')
    active = fields.Boolean('Activo', default=True)
    employees_ids = fields.One2many('hr.employee', 'sucursal_id', string='Empleados')
    director_id = fields.Many2one('hr.employee', string='Director')
    planillas_wz_id = fields.Integer('Planillas WZ', help='Planillas que se aplican a esta sucursal')
    porcentajepresupuestales_ids = fields.One2many('gestor.porcentaje.presupuestales', 'sucursal_id', string='Presupuestos')

    # @api.constrains('name')
    # def _check_name(self):
    #     if self.name == self.name:
    #         raise ValidationError("El nombre de la sucursal ya existe!")

    _sql_constraints = [('unq_sucursal_name', 'UNIQUE (name)',
                         'El nombre de la sucursal ya existe!')
                        ]
    _sql_constraints = [('unq_sucursal_code', 'UNIQUE (codigo)',
                         'Este código ya existe!')
                        ]

    @api.constrains('name', 'porcentajepresupuestales_ids')
    def _valida_porcentaje(self):
        total = 0
        sucursal_id = self._origin.id
        # raise ValidationError('sucursal_id: ' + str(sucursal_id.id))
        porcentajes_ids = self.env['gestor.porcentaje.presupuestales'].search([('sucursal_id', '=', sucursal_id)])
        if len(porcentajes_ids) > 0:
            for i in porcentajes_ids:
                total += i.porcentaje
            if total != 100:
                raise ValidationError('La suma de porcentajes debe ser igual al 100%.\nSuma actual: ' + str(total) + '%')


class PorcentajesPresupuestales(models.Model):
    _name = 'gestor.porcentaje.presupuestales'
    _description = 'Porcentajes Presupuestales por Sucursal'

    name = fields.Many2one('gestor.categoria.tipo.planes.team')
    porcentaje = fields.Float('Porcentaje %', help='Valor de porcentaje ej. 25%')
    sucursal_id = fields.Many2one('gestor.sucursales')
    employee_id = fields.Many2one('hr.employee')


class Distritos(models.Model):
    _name = 'gestor.distritos'
    _description = 'Distritos Operativos'

    name = fields.Char('Distrito')
    aplica = fields.Boolean('Aplica', help='Aplica el distrito para las liquidaciones')
    distrito_historico_ids = fields.One2many('gestor.distritos.historico', 'name', string='Cargo', track_visibility='onchange')

    def cargar_distritos(self):
        self.env.cr.execute("""insert into gestor_distritos (name)
                                select upper(trim(d_distrito)) from gestor_captura_hogar_team
                                where d_distrito is not null and d_distrito != ''
                                and d_distrito not in (select name from gestor_distritos)
                                group by d_distrito
                                order by d_distrito asc;""")

    @api.constrains('name', 'aplica')
    def _cambio_distrito(self):
        for registros in self:
            reg = registros.env['gestor.distritos.historico'].search([('name', '=', registros.idname)], limit=1)
            if len(reg) > 0:
                registros.name = reg.name
                registros.aplica = reg.aplica
            else:
                vals = {'name': registros.name,
                        'aplica': registros._origin.aplica,
                        }
                registros.env['gestor.distritos.historico'].create(vals)


class DistritosHist(models.Model):
    _name = 'gestor.distritos.historico'
    _inherit = ['mail.thread']
    _description = 'Historico de distritos'
    _order = "fecha_inicio desc"

    name = fields.Many2one('gestor.distritos', string='Distrito', required=True, track_visibility='onchange')
    aplica = fields.Boolean('Aplica', help='Aplica el distrito para las liquidaciones')
    fecha_inicio = fields.Date('Inicio', required=True, default=fields.Date.today(), track_visibility='onchange')
    fecha_fin = fields.Date('Fin', track_visibility='onchange')

    _sql_constraints = [
                        ('unq_distritos_historico', 'UNIQUE (name, fecha_inicio)',
                         'Ya existe un distrito con esa vigencia!')
                        ]
