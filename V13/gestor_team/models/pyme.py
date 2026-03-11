from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CapturaPyme(models.Model):
    _name = 'gestor.captura.pyme.team'
    _inherit = ['mail.thread']
    _description = 'Captura Datos Pyme'

    cuenta = fields.Char('Cuenta / ID Venta', help='Número de cuenta', required=True)
    ot = fields.Char('OT', help='Orden de trabajo', required=True)
    fecha = fields.Date('Fecha')
    id_cliente = fields.Char('CC/NIT Cliente', help='Cédula / NIT', required=True)
    nombre_cliente = fields.Char('Nombre Cliente', help='Nombre del cliente', required=True)
    estrato = fields.Selection([('1', '1'),
                                ('2', '2'),
                                ('3', '3'),
                                ('4', '4'),
                                ('5', '5'),
                                ('6', '6')])
    tel_cliente = fields.Char('Tel Cliente', help='Teléfono de contacto del cliente')
    valor = fields.Float('Valor venta antes de IVA', help='Valor venta antes de IVA - Cargo fijo mensual')
    estado_venta = fields.Many2one('gestor.estados_ap.team',
                                   help='Estado de la venta antes del pago de Claro',
                                   track_visibility='onchange')
    estado_contrato = fields.Many2one('gestor.estados_ap.team',
                                      help='Estado del contrato para efectos de la liquidción.',
                                      strack_visibility='onchange')
    red = fields.Char('Red')
    servicio = fields.Char('Servicio')  # Columna servicio
    vendedor = fields.Many2one('res.users',
                               'Vendedor TEAM',
                               default=lambda self: self.env.user,
                               help='Vendedor que realiza la venta.',
                               track_visibility='onchange')
    detalle_captura_pyme_ids = fields.One2many('gestor.captura.pyme.detalle.team', 'captura_pyme_id')
    detalle_agrupado_captura_pyme_ids = fields.One2many('gestor.captura.pyme.detalle.agrupado.team', 'captura_pyme_id')
    id_asesor = fields.Char('ID Asesor')
    idasesor = fields.Many2one('hr.employee', index=True)
    cargo = fields.Char(related='idasesor.job_id.name', string='Cargo', store=True)
    nombre_asesor = fields.Char('Nombre Asesor')
    id_responsable = fields.Many2one('hr.employee', string='Responsable')
    year = fields.Integer('Año')
    mes = fields.Char('Mes')
    digitador = fields.Many2one('res.users',
                                'Digitador TEAM',
                                default=lambda self: self.env.user,
                                help='Vendedor que realiza la venta.')
    referido = fields.Boolean('Referido')
    cedula_referido = fields.Char('N. Identificación')
    nombre_referido = fields.Char('Nombre', help='Nombre completo')
    telefono_referido = fields.Char('N. Celular/Fijo', help='Teléfono de contacto')
    correo_referido = fields.Char('email', help='Correo electrónico de contacto')
    correo_referido = fields.Char('email', help='Correo electrónico de contacto')
    banco_referido = fields.Many2one('res.bank',
                                     help='Entidad bancaria.')
    tipo_cuenta_referido = fields.Selection([('ahorros', 'Ahorros'), ('corriente', 'Corriente')])
    cuenta_referido = fields.Char('N- Cuenta', help='Número de cuenta del referido donde se le va a realizar la consignación, el titular debe ser la misma cédula del referido')
    nombre_vendedor = fields.Char(related='idasesor.name', store=True)
    identificacion_vendedor = fields.Char(related='idasesor.identification_id', string='Identificación (Vendedor)', store=True)
    categoria_vendedor = fields.Many2one('hr.employee.category', related='idasesor.category_id', string='Categoría (Vendedor)', store=True)
    departamento_vendedor = fields.Many2one('hr.department', related='idasesor.department_id', string='Departamento (Vendedor)', store=True)
    cargo_vendedor = fields.Many2one('hr.job', related='idasesor.job_id', string='Cago (Vendedor)', store=True)
    sucursal_vendedor = fields.Many2one('gestor.sucursales', related='idasesor.sucursal_id', string='Sucursal (Vendedor)', store=True)
    active = fields.Boolean('Activo', default=True)

    # nombre_vendedor = fields.Char(related='id_asesor.name')
    # identificacion_vendedor = fields.Char(related='id_asesor.identification_id', string='Identificación (Vendedor)', store=True)
    # categoria_vendedor = fields.Many2one('hr.employee.category', related='id_asesor.category_id', string='Categoría (Vendedor)', store=True)
    # departamento_vendedor = fields.Many2one('hr.department', related='id_asesor.department_id', string='Departamento (Vendedor)', store=True)
    # cargo_vendedor = fields.Many2one('hr.job', related='id_asesor.job_id', string='Cago (Vendedor)', store=True)
    # sucursal_vendedor = fields.Many2one('gestor.sucursales', related='id_asesor.sucursal_id', string='Sucursal (Vendedor)', store=True)
    #

    _sql_constraints = [('unq_captura_hogar_team_cuenta_ot', 'UNIQUE (cuenta, ot)',
                         'La cuenta y la OT ya estan ingresadas, por favor verifique!')]

    @api.constrains('id_cliente', 'tel_cliente', 'cuenta', 'ot')
    def _valida_campos(self):
        if self.id_cliente:
            try:
                x = int(self.id_cliente)
            except Exception as e:
                raise ValidationError('EL campo de ID Cliente solo debe contener dígitos numéricos, por favor verifique! \nEn caso de ser un NIT ingresarlo sin dígito de verificación.')
        if self.tel_cliente:
            try:
                x = int(self.tel_cliente)
            except Exception as e:
                raise ValidationError('EL campo de Teléfono solo debe contener dígitos numéricos, por favor verifique!\nUse el siguiente formato de telefono 9999999999')
        if self.cuenta:
            try:
                x = int(self.cuenta)
            except Exception as e:
                raise ValidationError('EL campo de Cuenta solo debe contener dígitos numéricos, por favor verifique!')
        if self.ot:
            try:
                x = int(self.ot)
            except Exception as e:
                raise ValidationError('EL campo de OT solo debe contener dígitos numéricos, por favor verifique!')

    @api.constrains('vendedor')
    @api.onchange('vendedor')
    def get_responsable(self):
        for registros in self:
            empleado = registros.env['hr.employee'].search([('user_id', '=', registros.vendedor.id)], limit=1)
            registros.id_responsable = empleado.parent_id.id
            registros.nombre_asesor = empleado.name
            registros.idasesor = empleado.id

    @api.onchange('estado_venta')
    def _actualiza_estado_ap(self):
        for reg in self.env['gestor.pyme.team'].search([('ot_venta', '=', self.ot),
                                                       ('id_venta', '=', self.cuenta)]
                                                      ):
            reg.estado_ap = self.estado_venta


class CapturaPymeDetalle(models.Model):
    _name = 'gestor.captura.pyme.detalle.team'
    _description = 'Captura el detalle de Datos Pyme'
    _order = 'venta'

    captura_pyme_id = fields.Many2one('gestor.captura.pyme.team')
    fecha = fields.Char('Fecha')
    tipored = fields.Char('Tipo Red')
    division = fields.Char('División')
    renta = fields.Char('Renta')
    venta = fields.Char('Venta')
    paquete = fields.Char('Paquete')
    paquete_pg = fields.Char('Paquete PG')
    paquete_pvd = fields.Char('Paquete PVD')
    cod_campana = fields.Char('Cod. Campaña')
    mintic = fields.Char('MINTIC')
    tipo_de_producto = fields.Char('Tipo de producto')
    tipo_plan_id = fields.Many2one('gestor.tipo.plan.team')  # domain --> tipo_producto='Hogar'


class CapturaPymeResumenPago(models.Model):
    _name = 'gestor.captura.pyme.detalle.agrupado.team'
    _description = 'Total por Venta Pyme'

    captura_pyme_id = fields.Many2one('gestor.captura.pyme.team')
    tipo_plan = fields.Many2one('gestor.tipo.plan.team')
    renta_total = fields.Float('Renta')


class PymeTEAM(models.Model):
    _name = 'gestor.pyme.team'
    _description = 'Claro Pyme TEAM'

    llave = fields.Char('Llave')
    proveedor = fields.Char('Proveedor')
    act_year = fields.Char('Act Año')
    act_mes = fields.Char('Act Mes')
    act_dia = fields.Char('Act Dia')
    year_base = fields.Char('Año Base')
    mes_base = fields.Char('Mes Base')
    base = fields.Char('Base')
    tipo = fields.Char('Tipo')
    tipo_v = fields.Char('Tipo V')
    id_venta = fields.Char('Id Venta')
    ot_venta = fields.Char('Ot Venta')
    servicio = fields.Char('Servicio')
    estado_contrato = fields.Char('Estado Contrato')
    act_fecha_legalizacion = fields.Char('Act Fecha Legalizacion')
    numero_contrato = fields.Char('Número Contrato')
    velocidad_homologada = fields.Char('Velocidad Homologada')
    linea_1_pyme = fields.Char('Línea 1 Pyme')
    linea_2_pyme = fields.Char('Línea 2 Pyme')
    fecha_periodo = fields.Char('Fecha Periodo')
    tipo_documento_cliente = fields.Char('Tipo Documento Cliente')
    identificacion_cliente = fields.Char('Identificacion Cliente')
    razon_social_cliente = fields.Char('Razón Social Cliente')
    segmento_comercial = fields.Char('Segmento Comercial')
    segmento_cliente = fields.Char('Segmento Cliente')
    red = fields.Char('Red')
    duracion_contrato = fields.Char('Duración Contrato')
    tipo_de_linea = fields.Char('Tipo De Línea')
    numero_de_lineas = fields.Char('Número De Líneas')
    numero_de_servicios = fields.Char('Número De Servicios')
    valor_de_servicios = fields.Char('Valor De Servicios')
    alquiler_equipos = fields.Char('Alquiler Equipos')
    cargo_instalacion = fields.Char('Cargo Instalacion')
    soporte_pc = fields.Char('Soporte Pc')
    cargo_mensual = fields.Char('Cargo Mensual')
    valor_mensualidad = fields.Char('Valor Mensualidad')
    valor_contrato = fields.Char('Valor Contrato')
    valor_neto = fields.Char('Valor Neto')
    valor_bruto = fields.Char('Valor Bruto')
    saldo = fields.Char('Saldo')
    division = fields.Char('División')
    division_residencial = fields.Char('División Residencial')
    regional = fields.Char('Regional')
    canal_residencial = fields.Char('Canal Residencial')
    soho = fields.Char('Soho')
    telemercadeo = fields.Char('Telemercadeo')
    area_residencial = fields.Char('Área Residencial')
    tipo_venta = fields.Char('Tipo Venta')
    campana_prom = fields.Char('Campaña Prom')
    clase_venta = fields.Char('Clase Venta')
    codigo_tarifa = fields.Char('Código Tarifa')
    departamento = fields.Char('Departamento')
    departamento_origen = fields.Char('Departamento Origen')
    ciudad_incidente = fields.Char('Ciudad Incidente')
    direccion = fields.Char('Dirección')
    estrato = fields.Char('Estrato')
    manual_tarifas = fields.Char('Manual Tarifas')
    nodo = fields.Char('Nodo')
    notas_descripcion_servicio = fields.Char('Notas Descripción Servicio')
    enlace = fields.Char('Enlace')
    fecha_inicio_facturacion = fields.Char('Fecha Inicio Facturación')
    tipo_solicitud = fields.Char('Tipo Solicitud')
    codigo_sku = fields.Char('Código Sku')
    servicio_onyx = fields.Char('Servicio Onyx')
    grupo_onyx = fields.Char('Grupo Onyx')
    numero_unico_de_activacion = fields.Char('Número Único De Activación')
    fecha_cancelacion = fields.Char('Fecha Cancelación')
    razon_cancelada_1 = fields.Char('Razón Cancelada 1')
    razon_cancelada_2 = fields.Char('Razón Cancelada 2')
    razon_cancelada_3 = fields.Char('Razón Cancelada 3')
    documento = fields.Char('Documento')
    funcionario = fields.Char('Funcionario')
    cargo = fields.Char('Cargo')
    act_cc_consultor = fields.Char('Act Cc Consultor')
    act_consultor = fields.Char('Act Consultor')
    act_coordinador = fields.Char('Act Coordinador')
    act_jefe = fields.Char('Act Jefe')
    act_gerente = fields.Char('Act Gerente')
    act_coordinador_tercero = fields.Char('Act Coordinador Tercero')
    cedula_consultor_it = fields.Char('Cédula Consultor It')
    consultor_it = fields.Char('Consultor It')
    act_ito_col = fields.Char('Act Ito Col')
    canal = fields.Char('Canal')
    year = fields.Integer('Año')
    mes = fields.Char('Mes')
    estado_ap = fields.Many2one('gestor.estados_ap.team', string='Estado Antes del Pago',
                                help='Ej. Legalizado, Carrusel, Fraude')
    estado_pp = fields.Many2one('gestor.estados_pp.team', string='Estado Posterior al Pago',
                                help='Ej. Pago devuelto, A Pagar,  Pagado')
    procesamiento_uid = fields.Many2one('res.users', string='Usuario último procesamiento')
    procesamiento_date = fields.Datetime('Fecha último procesamiento')

    _sql_constraints = [('unq_gestor_pyme_team', 'UNIQUE (id_venta, ot_venta, red, tipo_v, valor_mensualidad)',
                         'La Venta y la OT ya estan ingresadas, por favor verifique!')]

    @api.onchange('estado_ap')
    def _actualiza_estado_ap(self):
        for reg in self:
            for cuentas_ids in reg.env['gestor.pyme.team'].search([('ot_venta', '=', reg.ot_venta),
                                                                    ('id_venta', '=', reg.id_venta)]
                                                                   ):
                cuentas_ids.estado_ap = reg.estado_ap
        for cuentas_captura_ids in reg.env['gestor.captura.pyme.team'].search([('ot', '=', reg.ot_venta),
                                                                                ('cuenta', '=', reg.id_venta)]
                                                                              ):
            cuentas_captura_ids.estado_venta = reg.estado_ap

    @api.onchange('estado_pp')
    def _actualiza_estado_pp(self):
        for reg in self:
            for cuentas_ids in reg.env['gestor.pyme.team'].search([('ot_venta', '=', reg.ot_venta),
                                                                    ('id_venta', '=', reg.id_venta)]
                                                                   ):
                cuentas_ids.estado_pp=reg.estado_pp
