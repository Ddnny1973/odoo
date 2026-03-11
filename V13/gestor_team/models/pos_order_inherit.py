# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_cargar_hogares(self):
        for ordenes in self:
            valor_ot = 0
            valor_cuenta = 0
            cantidad_servicios = 0
            for lineas_control in ordenes.lines:
                if lineas_control['product_id'].product_tmpl_id.name in ('OT'):
                    valor_ot = lineas_control['pack_lot_ids'].lot_name
                elif lineas_control['product_id'].product_tmpl_id.name in ('Cuenta'):
                    valor_cuenta = lineas_control['pack_lot_ids'].lot_name
            for lineas in ordenes.lines:
                if lineas['product_id'].pos_categ_id.name == 'Servicios Principales':
                    cantidad_servicios += 1
                if lineas['product_id'].product_tmpl_id.name not in ('OT', 'Cuenta'):
                    res = {
                        'name': ordenes['name'],
                        'cuenta': valor_cuenta,
                        'ot': valor_ot,
                        'fecha_venta': ordenes['date_order'],
                        'producto_id': lineas['product_id'].id,
                        'tipo_venta': lineas['product_id'].pos_categ_id.name,
                        # 'cant_servicios': cantidad_servicios
                        'vendedor_id': 1,
                        }
                    self.env['gestor.hogar.team'].create(res)

    def action_pos_order_paid(self):
        if not self._is_pos_order_paid():
            raise UserError(_("Order %s is not fully paid.") % self.name)
        self.write({'state': 'paid'})
        self.action_cargar_hogares()
        return self.create_picking()
