# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SiconeCentroCosto(models.Model):
    """
    Tabla de matching entre centros de costo del libro auxiliar
    y proyectos SICONE. Permite que el parser identifique
    automáticamente a qué proyecto pertenece cada movimiento.
    """
    _name = 'sicone.centro.costo'
    _description = 'Centro de Costo - Proyecto'
    _order = 'nombre_cc'

    nombre_cc = fields.Char(
        string='Centro de Costo (Contabilidad)',
        required=True,
        help='Nombre exacto del centro de costo como aparece en el libro auxiliar. Ej: OBRA JORGE CALLE -'
    )
    proyecto_id = fields.Many2one(
        'sicone.proyecto',
        string='Proyecto SICONE',
        required=True,
        ondelete='cascade',
    )
    activo = fields.Boolean(string='Activo', default=True)
    notas = fields.Char(string='Notas')

    _sql_constraints = [
        ('nombre_cc_unique', 'UNIQUE(nombre_cc)',
         'Ya existe un centro de costo con ese nombre.')
    ]

    def name_get(self):
        result = []
        for cc in self:
            result.append((cc.id, f"{cc.nombre_cc} → {cc.proyecto_id.name}"))
        return result


class SiconeCuentaClasificacion(models.Model):
    """
    Tabla de clasificación de cuentas contables.
    Mapea el nombre de la cuenta contable a una categoría
    de análisis (Materiales, Mano de Obra, Variables, Administración).
    Reemplaza el diccionario TABLA_CLASIFICACION_CUENTAS de Streamlit.
    """
    _name = 'sicone.cuenta.clasificacion'
    _description = 'Clasificación de Cuenta Contable'
    _order = 'categoria, nombre_cuenta'

    nombre_cuenta = fields.Char(
        string='Nombre de Cuenta Contable',
        required=True,
        help='Nombre exacto de la cuenta como aparece en el libro auxiliar'
    )
    categoria = fields.Selection([
        ('materiales', 'Materiales'),
        ('mano_obra', 'Mano de Obra'),
        ('variables', 'Variables (Equipos/Imprevistos/Logística)'),
        ('administracion', 'Administración'),
    ], string='Categoría', required=True)

    activo = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('nombre_cuenta_unique', 'UNIQUE(nombre_cuenta)',
         'Ya existe una clasificación para esa cuenta.')
    ]


class SiconeMovimientoContable(models.Model):
    """
    Registro de cada movimiento importado desde el libro auxiliar contable.
    Almacena el movimiento original y su clasificación para análisis
    de flujo de caja real vs proyectado.

    IMPORTANTE: Este modelo es la fuente única de verdad para egresos
    e ingresos reales del período. No eliminar registros — el sistema
    detecta duplicados por fecha+comprobante+secuencia.
    """
    _name = 'sicone.movimiento.contable'
    _description = 'Movimiento Contable'
    _order = 'fecha desc, proyecto_id'

    # ── Identificación única del movimiento ──────────────────────────
    fecha = fields.Date(string='Fecha', required=True, index=True)
    comprobante = fields.Char(string='Comprobante')
    secuencia = fields.Char(string='Secuencia')

    # ── Datos contables ───────────────────────────────────────────────
    codigo_cuenta = fields.Char(string='Código Contable', index=True)
    nombre_cuenta = fields.Char(string='Cuenta Contable')
    identificacion = fields.Char(string='Identificación Tercero')
    nombre_tercero = fields.Char(string='Nombre Tercero')
    descripcion = fields.Char(string='Descripción')
    detalle = fields.Char(string='Detalle')
    nombre_cc = fields.Char(string='Centro de Costo (Original)', index=True)

    # ── Proyecto y clasificación ──────────────────────────────────────
    proyecto_id = fields.Many2one(
        'sicone.proyecto',
        string='Proyecto',
        index=True,
        help='Asignado automáticamente por el centro de costo'
    )
    categoria = fields.Selection([
        ('materiales', 'Materiales'),
        ('mano_obra', 'Mano de Obra'),
        ('variables', 'Variables'),
        ('administracion', 'Administración'),
        ('ingreso_proyecto', 'Ingreso de Proyecto'),
        ('gasto_fijo', 'Gasto Fijo Administrativo'),
        ('sin_clasificar', 'Sin Clasificar'),
    ], string='Categoría', index=True)

    tipo = fields.Selection([
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ], string='Tipo', required=True, index=True)

    # ── Valores ───────────────────────────────────────────────────────
    debito = fields.Monetary(
        string='Débito',
        currency_field='currency_id',
    )
    credito = fields.Monetary(
        string='Crédito',
        currency_field='currency_id',
    )
    monto = fields.Monetary(
        string='Monto',
        currency_field='currency_id',
        help='Monto neto del movimiento (débito o crédito según tipo)'
    )

    # ── Hito aplicado (para ingresos) ─────────────────────────────────
    hito_id = fields.Many2one(
        'sicone.hito',
        string='Hito Aplicado',
        help='Hito al que se aplicó este ingreso (calculado por prorrateo)'
    )
    pago_id = fields.Many2one(
        'sicone.pago',
        string='Pago Generado',
        help='Registro de pago creado a partir de este movimiento'
    )

    # ── Control ───────────────────────────────────────────────────────
    fuente = fields.Selection([
        ('libro_auxiliar', 'Libro Auxiliar'),
        ('carga_historica', 'Carga Histórica JSON'),
        ('manual', 'Manual'),
        ('banco', 'Cuenta Bancaria'),
    ], string='Fuente', default='libro_auxiliar')

    clasificacion_manual = fields.Boolean(
        string='Clasificación Manual',
        default=False,
        help='Si es True, el wizard no sobrescribirá la categoría/proyecto de este movimiento'
    )

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    _sql_constraints = [
        ('movimiento_unique',
         'UNIQUE(fecha, comprobante, secuencia, codigo_cuenta, nombre_cc)',
         'Ya existe un movimiento con esa combinación fecha/comprobante/secuencia/cuenta/CC.')
    ]