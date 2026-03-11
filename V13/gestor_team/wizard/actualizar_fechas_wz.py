from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class ActualizarFechasVentasWizard(models.TransientModel):
    _name = "gestor.actualizar.fechas.wizard"
    _description = "Actualizar las fechas en Ventas"

    def action_fechas_update(self):
        raise ValidationError(len(self))
