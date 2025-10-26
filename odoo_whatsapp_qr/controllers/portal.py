from odoo import http
from odoo.http import request

class WhatsappQRPortal(http.Controller):
    @http.route(['/my/whatsapp_qr'], type='http', auth='user', website=True)
    def portal_whatsapp_qr(self, **kw):
        user = request.env.user
        qr_records = request.env['whatsapp.qr'].sudo().search([('user_id', '=', user.id)])
        return request.render('odoo_whatsapp_qr.portal_whatsapp_qr_list', {
            'qr_records': qr_records,
        })

    @http.route(['/my/whatsapp_qr/<int:qr_id>'], type='http', auth='user', website=True)
    def portal_whatsapp_qr_detail(self, qr_id, **kw):
        qr = request.env['whatsapp.qr'].sudo().browse(qr_id)
        if qr.user_id.id != request.env.user.id:
            return request.not_found()
        return request.render('odoo_whatsapp_qr.portal_whatsapp_qr_detail', {
            'qr': qr,
        })

    @http.route(['/my/whatsapp_qr/<int:qr_id>/update_logs'], type='json', auth='user', website=True)
    def portal_whatsapp_qr_update_logs(self, qr_id, **kw):
        qr = request.env['whatsapp.qr'].sudo().browse(qr_id)
        if qr.user_id.id != request.env.user.id:
            return {'error': 'No autorizado'}
        qr.action_show_logs()
        return {'logs': qr.logs_preview}
