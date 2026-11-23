from odoo import http
from odoo.http import request


class WhatsappQRPortal(http.Controller):
    """Portal /my/whatsapp_qr: cada usuario ve solo los servicios de WhatsApp que son suyos."""

    def _mi_servicio(self, qr_id):
        """Registro del usuario actual o un recordset vacío. Se usa sudo() solo para poder leer los
        campos de conexión (token) en el servidor; la pertenencia se comprueba aquí y además por la
        regla de registro de whatsapp.qr."""
        qr = request.env['whatsapp.qr'].sudo().browse(qr_id).exists()
        if not qr or qr.user_id.id != request.env.user.id:
            return request.env['whatsapp.qr'].sudo().browse()
        return qr

    @http.route(['/my/whatsapp_qr'], type='http', auth='user', website=True)
    def portal_whatsapp_qr(self, **kw):
        qr_records = request.env['whatsapp.qr'].sudo().search([('user_id', '=', request.env.user.id)])
        return request.render('odoo_whatsapp_qr.portal_whatsapp_qr_list', {
            'qr_records': qr_records,
        })

    @http.route(['/my/whatsapp_qr/<int:qr_id>'], type='http', auth='user', website=True)
    def portal_whatsapp_qr_detail(self, qr_id, **kw):
        qr = self._mi_servicio(qr_id)
        if not qr:
            return request.not_found()
        return request.render('odoo_whatsapp_qr.portal_whatsapp_qr_detail', {
            'qr': qr,
            'qr_code': qr._get_qr(),
            'estado': qr._get_estado(),
        })

    @http.route(['/my/whatsapp_qr/<int:qr_id>/update_qr'], type='json', auth='user', website=True)
    def portal_whatsapp_qr_update_qr(self, qr_id, **kw):
        qr = self._mi_servicio(qr_id)
        if not qr:
            return {'error': 'No autorizado'}
        return {'qr_code': qr._get_qr(), 'logs': qr._get_estado()}

    @http.route(['/my/whatsapp_qr/<int:qr_id>/update_logs'], type='json', auth='user', website=True)
    def portal_whatsapp_qr_update_logs(self, qr_id, **kw):
        qr = self._mi_servicio(qr_id)
        if not qr:
            return {'error': 'No autorizado'}
        return {'logs': qr._get_estado()}
