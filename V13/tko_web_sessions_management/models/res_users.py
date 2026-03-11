# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
# Copyright (C) Thinkopen Solutions <http://www.tkobr.com>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.addons.base.models.ir_cron import _intervalTypes
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging
_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _check_session_validity(self, db, uid, passwd):
        if not request:
            return
        now = fields.datetime.now()
        session = request.session
        if not (session.db and session.uid):
            return True

        session_obj = request.env['ir.sessions']

        # FIX: No usamos self._cr porque puede estar cerrado (fue abierto y
        # cerrado en check()). Abrimos un cursor propio y lo cerramos al final.
        cr = self.pool.cursor()
        try:
            cr.autocommit(True)
            session_ids = session_obj.sudo().search(
                [('session_id', '=', session.sid),
                 ('date_expiration', '>',
                  now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                 ('logged_in', '=', True)], order='date_expiration asc')

            if session_ids:
                if request.httprequest.path[:5] == '/web/' or \
                        request.httprequest.path[:9] == '/im_chat/' or \
                        request.httprequest.path[:6] == '/ajax/':
                    open_sessions = session_ids.read(['logged_in',
                                                      'date_login',
                                                      'session_seconds',
                                                      'date_expiration'])
                    for s in open_sessions:
                        session_id = session_obj.browse(s['id'])
                        date_expiration = (now + relativedelta(
                            seconds=session_id.session_seconds)).strftime(
                            DEFAULT_SERVER_DATETIME_FORMAT)
                        session_duration = str(now - datetime.strptime(
                            session_id.date_login,
                            DEFAULT_SERVER_DATETIME_FORMAT)).split('.')[0]
                        cr.execute('''UPDATE ir_sessions SET date_expiration=%s,
                        session_duration=%s WHERE id= %s''', (date_expiration,
                                                              session_duration,
                                                              session_id.id,))
                    cr.commit()
            else:
                # FIX: Solo hacer logout si la sesión existe en BD pero expiró.
                # Si no existe en BD (primer login o sesión nueva), NO hacer logout
                # porque eso bloquea al usuario recién autenticado.
                expired_sessions = session_obj.sudo().search(
                    [('session_id', '=', session.sid),
                     ('logged_in', '=', True)])
                if expired_sessions:
                    _logger.info(
                        'Session %s expired for user %s, marking as closed.',
                        session.sid, uid)
                    # Marcar la sesión como cerrada en BD sin cerrar la sesión HTTP actual
                    # (que es la NUEVA sesión del usuario que está intentando loguear)
                    expired_sessions._on_session_logout(logout_type='to')
                else:
                    _logger.debug(
                        'No session record found for sid %s user %s — '
                        'skipping logout (new session or first login).',
                        session.sid, uid)
        except Exception as e:
            _logger.error(
                '_check_session_validity error for uid %s: %s', uid, e)
        finally:
            cr.close()

        return True

    @classmethod
    def check(cls, db, uid, passwd):
        res = super(ResUsers, cls).check(db, uid, passwd)
        # FIX: Abrimos cursor solo para construir el Environment, lo cerramos
        # antes de llamar a _check_session_validity para evitar cursor leak.
        cr = cls.pool.cursor()
        try:
            self = api.Environment(cr, uid, {})[cls._name]
            user = self.browse(uid)
        finally:
            cr.commit()
            cr.close()
        # _check_session_validity abre su propio cursor internamente
        user._check_session_validity(db, uid, passwd)
        return res

    @api.depends('interval_number', 'interval_type',
                 'groups_id.interval_number', 'groups_id.interval_type')
    def _get_session_default_seconds(self):
        now = datetime.now()
        seconds = (now + _intervalTypes['weeks'](1) - now).total_seconds()
        for user in self:
            if user.interval_number and user.interval_type:
                u_seconds = (
                    now +
                    _intervalTypes[
                        user.interval_type](
                        user.interval_number) -
                    now).total_seconds()
                if u_seconds < seconds:
                    seconds = u_seconds
            else:
                # Get lowest session time
                for group in user.groups_id:
                    if group.interval_number and group.interval_type:
                        g_seconds = (
                            now +
                            _intervalTypes[
                                group.interval_type](
                                group.interval_number) -
                            now).total_seconds()
                        if g_seconds < seconds:
                            seconds = g_seconds
            user.session_default_seconds = seconds

    login_calendar_id = fields.Many2one('resource.calendar',
                                        'Allowed Login Calendar',
                                        company_dependent=True,
                                        help='''The user will be only allowed
                                        to login in the calendar defined here.
                                        \nNOTE:The calendar defined here will
                                        overlap all defined in groups.''')
    multiple_sessions_block = fields.Boolean('Block Multiple Sessions',
                                             company_dependent=True,
                                             default=False,
                                             help='''Select this to prevent
                                             user to start more than one
                                             session.''')
    interval_number = fields.Integer('Default Session Duration',
                                     company_dependent=True,
                                     help='''This is the timeout for this user.
                                     \nNOTE: The timeout defined here will
                                     overlap all the timeouts defined in
                                     groups.''')
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('work_days', 'Work Days'),
                                      ('days', 'Days'), ('weeks', 'Weeks'),
                                      ('months', 'Months')],
                                     'Interval Unit', company_dependent=True)
    session_default_seconds = fields.Integer(
        compute=_get_session_default_seconds, string='Session Seconds')
    session_ids = fields.One2many('ir.sessions', 'user_id', 'User Sessions')
    ip = fields.Char(related='session_ids.ip', string='Latest ip adress')