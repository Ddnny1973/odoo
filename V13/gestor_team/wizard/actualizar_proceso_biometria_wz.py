from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class ActualizarProcesoBiometriasWizard(models.TransientModel):
    _name = "gestor.actualizar.proceso.biometria.wizard"
    _description = "Actualizar el proceso de biometrías"

    def action_actualizar_biometrias(self):
        self.env.cr.execute("""select actualizaciones_automaticas();""")
