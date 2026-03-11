# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError
import pymssql
import logging


_logger = logging.getLogger(__name__)


# Connection parameters, yours will be different
# param_dic = {
#             'server': 'team.soluciondigital.com.co',
#             'database': 'TipsII',
#             'user': 'procesos',
#             'password': 'TeamC02020*'
#             }

param_dic = {
            'server': 'team.soluciondigital.com.co',
            'database': 'TipsII',
            'user': 'sa',
            'password': 'Soluciondig2015'
            }


def connect(params_dic):
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # connect to the MSsqlServer server
        print('Conectandose con base de datos MS SQL Server Solución digital...')
        conn = pymssql.connect(**params_dic)
    except Exception as error:
        print(error)
        raise ValidationError(error)
    print("Conexión satisfactoria")
    return conn


def send_to_channel(self, body):
    ch_obj = self.env['mail.channel']
    # ch = ch_obj.sudo().search([('name', 'ilike', 'general')])
    ch = ch_obj.sudo().search([('name', 'ilike', 'OdooBot'), ('alias_id', '=', 9)])
    body_ok = body

    ch.message_post(attachment_ids=[], body=body_ok,
                    content_subtype='html', message_type='comment',
                    partner_ids=[], subtype='mail.mt_comment')
    return True


class Cruce(models.Model):
    _name = 'gestor.cruce.ventas.tips'
    _description = 'CruceVentas registradas en TIPS'
    _order = 'fecha_rp desc'

    fecha_tips = fields.Date('Fecha TIPS')
    fecha_rp = fields.Date('Fecha RP')
    revision_fecha = fields.Char('Revisión Fecha')
    nombre_plan_tips = fields.Char('Nombre Plan TIPS')
    nombre_plan_rp = fields.Char('Nombre Plan RP')
    revision_del_plan = fields.Char('Revisión Plan')
    tipo_de_plan_tips = fields.Char('Tipo Plan TIPS')
    tipo_de_plan_rp = fields.Char('Tipo Plan RP')
    revision_tipo_de_plan = fields.Char('Revisión Tipo Plan')
    iccid_tips = fields.Char('ICCID TIPS')
    iccid_rp = fields.Char('ICCID RP')
    imei_tips = fields.Char('IMEI TIPS')
    imei_rp = fields.Char('IMEI RP')
    revision_imei = fields.Char('Revisión IMEI')
    min_tips = fields.Char('MIN TIPS')
    min_rp = fields.Char('MIN RP')
    revision_min = fields.Char('Revisión MIN')
    equipo_tips = fields.Char('Equipo TIPS')
    equipo = fields.Many2one('gestor.equipos.tips', help='Nombre equipo en TIPS para actualización')
    equipo_stok = fields.Char('Equipo STOK')
    revision_equipo = fields.Char('Revisión Equipo')
    costo_rec_log = fields.Char('Costo Reconocimiento Logístico')
    pago = fields.Char('Pago')
    sucursal = fields.Char('Sucursal')
    tipo_de_vendedor = fields.Char('tipo_de_vendedor')
    nombre_para_mostrar_del_vendedor = fields.Char('Nombre Vendedor TIPS')
    estado_actual = fields.Char('Estado Actual')
    cliente_actual = fields.Char('Cliente Actual')
    usuario_creador = fields.Char('Usuario Creador')
    venta_id = fields.Integer('venta_id')
    venta_id_tips = fields.Integer('Venta id TIPS')
    plan_tips_id = fields.Many2one('gestor.planes.team', help='Plan a modificar en TIPS')
    tipo_plan_tips = fields.Char(related='plan_tips_id.tipo_plan.name',
                                 string="Tipo Plan TIPS Relacionado",
                                 help='Tipo de plan asociado a el Plan en TIPS que será modificado')
    encontrada_rp = fields.Char(string='Encontrada en RP', help='Indica si la venta fue encontrada en RP')
    estado_tips = fields.Char('Estado TIPS')
    tipo_linea = fields.Char('Tipo Línea')
    id_tips = fields.Integer('ID TIPS')
    id_rp = fields.Integer('ID RP')
    co_id_rp = fields.Char('CO_ID RP')
    posible_duplicado = fields.Boolean('Posible duplicado')

    def actualizar_venta_tips(self):
        tipo_linea_id = self.env['gestor.tipo.lineas.planes.team'].search([('name', '=', self.tipo_linea)])
        if len(tipo_linea_id) > 0:
            tipo_linea = tipo_linea_id.id_tips
        else:
            tipo_linea = False

        try:
            if self.equipo:
                _logger.info('Equipo a actualizar: ' + str(self.equipo))
                _logger.info('Equipo a actualizar: ' + str(self.equipo.id_tips))
                _logger.info('Codigo del plan: ' + str(self.plan_tips_id.codigo_id))
                actualizar_equipo = self.equipo.id_tips
            else:
                _logger.info('Codigo del plan: ' + str(self.plan_tips_id.codigo_id))
                actualizar_equipo = 'null'

            id_tips = 'null'
            gestor_lineas_planes_team = self.env['gestor.lineas.planes.team'].search([('name', '=', self.tipo_de_plan_rp)])
            for i in self.env['gestor.tipo.lineas.planes.team'].search([]):
                if gestor_lineas_planes_team.id in i.lineas_planes_ids.ids:
                    self.tipo_linea = i.id
                    id_tips = i.id_tips

            instruccion_insertar = 'Declare @Ventas dbo.TipsTduDatosParaCambioDeVentas; \ninsert into @Ventas(Id,PlanId,Min,Iccid,Imei,Fecha,CoId,TipoDeActivacionId,EquipoId,TipoDeLineaId) VALUES \n'
            lineas_insertar = ''
            lineas_insertar = lineas_insertar + '(' + \
                                                   str(self.venta_id_tips) + ',' + \
                                                   str(self.plan_tips_id.codigo_id) + ',' + \
                                                   self.min_tips + \
                                                   ', null, ' + \
                                                   self.imei_tips + ',' + \
                                                   '\'' + str(self.fecha_tips) + '\'' \
                                                   ', null, ' + \
                                                   'null, ' + \
                                                   actualizar_equipo + \
                                                   ', ' + str(id_tips) + \
                                                   ') \n'

            lineas_insertar = instruccion_insertar + lineas_insertar + ';\nExec pro_ext_Gtor_ModificarVentasMasivamente @Ventas;'
            raise ValidationError('SQL: ' + lineas_insertar)

            conn = connect(param_dic)
            cursor = conn.cursor()
            cursor.execute(lineas_insertar)
            conn.commit()
            reporte = 'Actualización en TIPS Exitosa'
            # send_to_channel(self, reporte)
            # raise ValidationError('Actualización exitosa!')
        except Exception as error:
            # conn.rollback()
            raise ValidationError(error)


class EquiposStock(models.Model):
    _name = 'gestor.equipos.stock'
    _description = 'Equipos existentes en Stock'

    name = fields.Char('Nombre del equipo')
    estado = fields.Char('Estado del equipo', help='Estado del equipo en STOK')
    serializado = fields.Char('Serializado')


class EquiposTips(models.Model):
    _name = 'gestor.equipos.tips'
    _description = 'Equipos existentes en TIPS'

    name = fields.Char('Nombre del equipo')
    id_tips = fields.Integer('ID', help='ID equipo en TIPS')
    nombre_equipo_stock = fields.Many2many('gestor.equipos.stock')
    active = fields.Boolean('Activo', default=True)
