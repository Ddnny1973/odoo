from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _get_action(self):
        return self.env['res.users'].search([('login', '=', 'default'),
                                             ('active', '=', False)]).action_id

    action_id = fields.Many2one(default=_get_action)
