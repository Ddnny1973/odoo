# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class CotizacionSicone(models.Model):
    """
    Modelo principal para Cotizaciones SICONE
    Contiene el header de la cotización y gestiona las versiones
    """
    _name = 'sicone.cotizacion'
    _description = 'Cotización SICONE'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_cotizacion desc, id desc'
    
    # ============================================================================
    # CAMPOS BÁSICOS
    # ============================================================================
    
    name = fields.Char(
        string='Número de Cotización',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
        tracking=True
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    # ============================================================================
    # RELACIÓN CON PROYECTO
    # ============================================================================
    
    proyecto_id = fields.Many2one(
        'sicone.proyecto',
        string='Proyecto',
        required=False,
        ondelete='set null',
        tracking=True
    )
    
    # Campos relacionados del proyecto
    cliente = fields.Char(
        string='Cliente',
        tracking=True,
    )
    direccion = fields.Char(
        string='Dirección',
        tracking=True,
    )

    @api.onchange('proyecto_id')
    def _onchange_proyecto_id(self):
        if self.proyecto_id:
            self.cliente = self.proyecto_id.partner_id.name or ''
            self.direccion = self.proyecto_id.partner_id.street or ''
    
    # ============================================================================
    # INFORMACIÓN GENERAL
    # ============================================================================
    
    fecha_cotizacion = fields.Date(
        string='Fecha de Cotización',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    
    fecha_vencimiento = fields.Date(
        string='Válida Hasta',
        tracking=True,
        help='Fecha hasta la cual es válida esta cotización'
    )
    
    # ============================================================================
    # ESTADO Y CONTROL
    # ============================================================================
    
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('aprobada', 'Aprobada Internamente'),
        ('enviada', 'Enviada a Cliente'),
        ('aceptada', 'Aceptada por Cliente'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
    ], string='Estado', default='borrador', required=True, tracking=True)
    
    # ============================================================================
    # VERSIONAMIENTO
    # ============================================================================
    
    version_activa_numero = fields.Integer(
        string='Número de Versión',
        default=1,
        readonly=True,
        tracking=True
    )
    
    version_ids = fields.One2many(
        'sicone.cotizacion.version',
        'cotizacion_id',
        string='Versiones'
    )
    
    version_activa_id = fields.Many2one(
        'sicone.cotizacion.version',
        string='Versión Activa',
        compute='_compute_version_activa',
        store=True
    )
    
    version_count = fields.Integer(
        string='N° Versiones',
        compute='_compute_version_count'
    )
    
    # ============================================================================
    # TOTALES CONSOLIDADOS (desde versión activa)
    # ============================================================================
    
    total_capitulo1 = fields.Monetary(
        string='Total Capítulo 1',
        compute='_compute_totales_consolidados',
        store=True,
        help='Total del Capítulo 1: Diseños + Estructura + Mampostería + Techos'
    )
    
    total_capitulo2 = fields.Monetary(
        string='Total Capítulo 2',
        compute='_compute_totales_consolidados',
        store=True,
        help='Total del Capítulo 2: Cimentaciones + Complementarios'
    )
    
    total_general = fields.Monetary(
        string='Total General',
        compute='_compute_totales_consolidados',
        store=True,
        help='Total consolidado de ambos capítulos'
    )
    
    # ============================================================================
    # CONTRATOS
    # ============================================================================
    
    generar_contrato_separado = fields.Boolean(
        string='Generar Contratos Separados',
        default=True,
        tracking=True,
        help='Si está marcado, se generan dos contratos independientes (uno por capítulo)'
    )
    
    # ============================================================================
    # CAMPOS DE CONTROL
    # ============================================================================
    
    usuario_creacion_id = fields.Many2one(
        'res.users',
        string='Creado por',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True
    )
    
    notas = fields.Text(
        string='Notas Internas'
    )
    
    # ============================================================================
    # MÉTODOS COMPUTE
    # ============================================================================
    
    @api.depends('version_ids', 'version_ids.activa')
    def _compute_version_activa(self):
        """Obtiene la versión activa actual"""
        for cotizacion in self:
            version_activa = cotizacion.version_ids.filtered(lambda v: v.activa)
            cotizacion.version_activa_id = version_activa[:1] if version_activa else False
    
    @api.depends('version_ids')
    def _compute_version_count(self):
        """Cuenta el número de versiones"""
        for cotizacion in self:
            cotizacion.version_count = len(cotizacion.version_ids)
    
    @api.depends('version_activa_id.total_capitulo1', 
                 'version_activa_id.total_capitulo2',
                 'version_activa_id.total_general')
    def _compute_totales_consolidados(self):
        """Obtiene los totales desde la versión activa"""
        for cotizacion in self:
            if cotizacion.version_activa_id:
                cotizacion.total_capitulo1 = cotizacion.version_activa_id.total_capitulo1
                cotizacion.total_capitulo2 = cotizacion.version_activa_id.total_capitulo2
                cotizacion.total_general = cotizacion.version_activa_id.total_general
            else:
                cotizacion.total_capitulo1 = 0.0
                cotizacion.total_capitulo2 = 0.0
                cotizacion.total_general = 0.0
    
    # ============================================================================
    # MÉTODOS CRUD
    # ============================================================================
    
    @api.model
    def create(self, vals):
        """Genera número de cotización automático y crea versión inicial"""
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('sicone.cotizacion') or 'COT/NEW'
        
        cotizacion = super(CotizacionSicone, self).create(vals)
        
        # Crear versión inicial automáticamente
        self.env['sicone.cotizacion.version'].create({
            'cotizacion_id': cotizacion.id,
            'numero_version': 1,
            'activa': True,
            'notas_cambios': 'Versión inicial',
        })
        
        return cotizacion
    
    def write(self, vals):
        """Validaciones al modificar"""
        # Prevenir cambios en cotizaciones aprobadas/enviadas sin permisos
        if 'estado' not in vals:
            estados_bloqueados = ['aprobada', 'enviada', 'aceptada']
            for cotizacion in self:
                if cotizacion.estado in estados_bloqueados:
                    if not self.env.user.has_group('sicone.group_sicone_manager'):
                        raise UserError(
                            'No puede modificar una cotización en estado "%s". '
                            'Contacte al administrador.' % dict(cotizacion._fields['estado'].selection).get(cotizacion.estado)
                        )
        
        return super(CotizacionSicone, self).write(vals)
    
    def unlink(self):
        """Prevenir eliminación de cotizaciones aprobadas"""
        for cotizacion in self:
            if cotizacion.estado in ['aprobada', 'enviada', 'aceptada']:
                raise UserError(
                    'No puede eliminar una cotización en estado "%s".' % 
                    dict(cotizacion._fields['estado'].selection).get(cotizacion.estado)
                )
        return super(CotizacionSicone, self).unlink()
    
    # ============================================================================
    # MÉTODOS DE ACCIÓN
    # ============================================================================
    
    def action_view_versiones(self):
        """Abre la vista de versiones de la cotización"""
        self.ensure_one()
        return {
            'name': 'Versiones de Cotización',
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.cotizacion.version',
            'view_mode': 'list,form',
            'domain': [('cotizacion_id', '=', self.id)],
            'context': {
                'default_cotizacion_id': self.id,
            }
        }
    
    def action_crear_nueva_version(self):
        """Crea una nueva versión basada en la versión activa"""
        self.ensure_one()
        
        if not self.version_activa_id:
            raise UserError('No hay versión activa para duplicar.')
        
        # Desactivar versión actual
        self.version_activa_id.activa = False
        
        # Crear nueva versión duplicando la activa
        nueva_version = self.version_activa_id.copy({
            'numero_version': self.version_activa_numero + 1,
            'activa': True,
            'fecha_creacion': fields.Datetime.now(),
            'usuario_id': self.env.user.id,
            'notas_cambios': '',
        })
        
        # Actualizar número de versión activa
        self.version_activa_numero = nueva_version.numero_version
        
        return {
            'name': f'Versión {nueva_version.numero_version}',
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.cotizacion.version',
            'view_mode': 'form',
            'res_id': nueva_version.id,
            'target': 'current',
        }
    
    def action_aprobar(self):
        """Aprueba la cotización internamente"""
        self.ensure_one()
        if self.estado != 'borrador':
            raise UserError('Solo se pueden aprobar cotizaciones en estado Borrador.')
        self.estado = 'aprobada'
    
    def action_enviar_cliente(self):
        """Marca la cotización como enviada al cliente"""
        self.ensure_one()
        if self.estado != 'aprobada':
            raise UserError('Solo se pueden enviar cotizaciones aprobadas.')
        self.estado = 'enviada'
    
    def action_aceptar(self):
        """Marca la cotización como aceptada y crea proyecto + contratos"""
        self.ensure_one()
        if self.estado != 'enviada':
            raise UserError('Solo se pueden aceptar cotizaciones enviadas.')
        self.estado = 'aceptada'

        # Buscar o crear contacto del cliente
        partner = self.proyecto_id.partner_id if self.proyecto_id else False
        if not partner and self.cliente:
            partner = self.env['res.partner'].search(
                [('name', 'ilike', self.cliente)], limit=1
            )
            if not partner:
                partner = self.env['res.partner'].create({'name': self.cliente})

        # Crear proyecto automáticamente
        version = self.version_activa_id
        proyecto = self.env['sicone.proyecto'].create({
            'name': self.cliente or self.name,
            'partner_id': partner.id if partner else False,
            'cotizacion_id': self.id,
            'estado': 'contratado',
            'area_base': version.area_base if version else 0.0,
            'area_cubierta': version.area_cubierta if version else 0.0,
            'area_entrepiso': version.area_entrepiso if version else 0.0,
            'notas': f'Proyecto creado automáticamente desde {self.name}',
        })

        # Crear los dos contratos
        self.env['sicone.contrato'].create({
            'proyecto_id': proyecto.id,
            'cotizacion_id': self.id,
            'numero': '1',
            'monto': self.total_capitulo1,
            'estado': 'activo',
        })
        self.env['sicone.contrato'].create({
            'proyecto_id': proyecto.id,
            'cotizacion_id': self.id,
            'numero': '2',
            'monto': self.total_capitulo2,
            'estado': 'activo',
        })

        # Crear los 4 hitos estándar de SICONE
        hitos_config = [
            {'nombre': 'Anticipo Procesos Administrativos', 'secuencia': 10,
             'contrato_ref': 'ambos', 'pct_c1': 32.0, 'pct_c2': 25.0},
            {'nombre': 'Inicio Cimentacion', 'secuencia': 20,
             'contrato_ref': 'ambos', 'pct_c1': 17.5, 'pct_c2': 43.0},
            {'nombre': 'Fin Cimentacion Inicio Obra Gris', 'secuencia': 30,
             'contrato_ref': 'ambos', 'pct_c1': 39.0, 'pct_c2': 20.0},
            {'nombre': 'Fin de Obra', 'secuencia': 40,
             'contrato_ref': 'ambos', 'pct_c1': 9.8, 'pct_c2': 9.7},
        ]
        for hito_vals in hitos_config:
            self.env['sicone.hito'].create({
                'proyecto_id': proyecto.id,
                **hito_vals,
            })

        # Vincular proyecto a la cotización
        self.proyecto_id = proyecto.id

        return {
            'name': 'Proyecto Creado',
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.proyecto',
            'view_mode': 'form',
            'res_id': proyecto.id,
            'target': 'current',
        }
    
    def action_rechazar(self):
        """Marca la cotización como rechazada"""
        self.ensure_one()
        if self.estado in ['aceptada', 'cancelada']:
            raise UserError('No se puede rechazar una cotización aceptada o cancelada.')
        self.estado = 'rechazada'
    
    def action_cancelar(self):
        """Cancela y elimina la cotización"""
        self.ensure_one()
        if self.estado == 'aceptada':
            raise UserError('No se puede cancelar una cotización aceptada.')
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}
    
    def action_volver_borrador(self):
        """Vuelve la cotización a estado borrador"""
        self.ensure_one()
        if not self.env.user.has_group('sicone.group_sicone_manager'):
            raise UserError('Solo los administradores pueden volver a borrador.')
        
        # Validar que el proyecto asociado no esté en ejecución
        proyecto = self.env['sicone.proyecto'].search([
            ('cotizacion_id', '=', self.id),
            ('active', '=', True),
            ('estado', '=', 'ejecucion')
        ], limit=1)
        
        if proyecto:
            raise UserError(
                f'No se puede modificar esta cotización porque su proyecto '
                f'({proyecto.codigo}) ya está en ejecución con cobros aplicados.\n\n'
                f'Para ajustes en proyectos en ejecución, contacte al administrador del sistema.'
            )
        
        self.estado = 'borrador'
    
    def name_get(self):
        """Personaliza el nombre mostrado de la cotización"""
        result = []
        for cotizacion in self:
            name = f"{cotizacion.name} - {cotizacion.proyecto_id.name}"
            result.append((cotizacion.id, name))
        return result

    def action_cargar_excel(self):
        """Abre wizard para cargar Excel en esta cotización"""
        self.ensure_one()
        return {
            'name': 'Cargar Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.wizard.nueva.cotizacion',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cotizacion_id': self.id},
        }
