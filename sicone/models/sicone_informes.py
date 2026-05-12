# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import io
import base64
import json

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


class SiconeInformes(models.Model):
    _name = 'sicone.informes'
    _description = 'Informes Ejecutivos SICONE'

    name = fields.Char(string='Nombre', default='Informes Ejecutivos', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True,
                                  default=lambda self: self.env.company)
    
    # Archivos PDF generados
    pdf_multiproyecto = fields.Binary(string='PDF Multiproyecto', readonly=True)
    pdf_multiproyecto_filename = fields.Char(string='Nombre archivo MP', readonly=True)
    
    pdf_proyecciones = fields.Binary(string='PDF Proyecciones', readonly=True)
    pdf_proyecciones_filename = fields.Char(string='Nombre archivo Proy', readonly=True)
    
    fecha_generacion_mp = fields.Datetime(string='Fecha Gen. Multiproyecto', readonly=True)
    fecha_generacion_proy = fields.Datetime(string='Fecha Gen. Proyecciones', readonly=True)

    def formatear_moneda(self, valor):
        """Formatea valores en millones"""
        if valor >= 1000000000:
            return f"${valor/1e9:.1f}B"
        return f"${valor/1e6:.0f}M"

    def _generar_grafico_proyecciones(self, datos):
        """Genera gráfico matplotlib con histórico + 3 escenarios + burn rate"""
        fig, ax = plt.subplots(figsize=(10, 4))
        
        labels_h = datos.get('labels_hist', [])
        labels_p = datos.get('labels_proy', [])
        
        # Combinar labels (sin duplicar punto de unión)
        labels_all = labels_h + [l for l in labels_p if l not in labels_h]
        n_hist = len(labels_h)
        
        # Histórico: valores reales + nulls para proyección
        hist_full = datos.get('hist', []) + [None] * (len(labels_p) - 1)
        
        # Proyecciones: nulls hasta penúltimo histórico + valores
        def mk_proy(vals):
            return [None] * (n_hist - 1) + (vals or [])
        
        conservador = mk_proy(datos.get('conservador'))
        moderado = mk_proy(datos.get('moderado'))
        optimista = mk_proy(datos.get('optimista'))
        
        # Burn rate (línea horizontal)
        burn_promedio = datos.get('burn_promedio', 0)
        
        # Dibujar líneas
        ax.plot(labels_all, hist_full, 'o-', color='#6C757D', linewidth=2.5,
                label='Histórico', markersize=3)
        ax.plot(labels_all, conservador, '--', color='#2980B9', linewidth=2,
                label='Conservador', markersize=4, marker='o')
        ax.plot(labels_all, moderado, '--', color='#E67E22', linewidth=2,
                label='Moderado', markersize=4, marker='o')
        ax.plot(labels_all, optimista, '--', color='#27AE60', linewidth=2,
                label='Optimista', markersize=4, marker='o')
        ax.axhline(y=burn_promedio, color='#E74C3C', linewidth=3,
                   linestyle='--', label='Burn Rate Promedio')
        
        # Formato
        ax.set_ylabel('Saldo (Millones COP)', fontsize=10)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=8)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        
        plt.title('Saldo de Caja — Histórico + Proyecciones', fontsize=12, 
                 fontweight='bold', pad=10)
        plt.tight_layout()
        
        # Guardar a bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf

    def _generar_gantt_inversiones(self, inversiones):
        """Genera timeline Gantt de inversiones temporales"""
        if not inversiones:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 2))
        
        # Preparar datos
        from datetime import datetime as dt
        
        inv_data = []
        for inv in inversiones:
            inicio = inv.fecha_inicio
            fin = inv.fecha_vencimiento
            inv_data.append({
                'nombre': inv.instrumento,
                'inicio': inicio,
                'fin': fin,
                'monto': inv.monto,
                'duracion': (fin - inicio).days
            })
        
        # Ordenar por fecha de inicio
        inv_data.sort(key=lambda x: x['inicio'])
        
        # Colores por instrumento
        colores = {
            'fondo_liquidez': '#E67E22',
            'cuenta_remunerada': '#27AE60',
            'cdt': '#2980B9',
        }
        
        # Dibujar barras
        for i, inv in enumerate(inv_data):
            color = colores.get(inv['nombre'], '#95A5A6')
            inicio = matplotlib.dates.date2num(inv['inicio'])
            duracion = inv['duracion']
            
            ax.barh(i, duracion, left=inicio, height=0.6, 
                   color=color, edgecolor='black', linewidth=1)
            
            # Etiqueta con monto
            monto_str = self.formatear_moneda(inv['monto'])
            ax.text(inicio + duracion/2, i, monto_str,
                   ha='center', va='center', fontsize=9, fontweight='bold',
                   color='white')
        
        # Configurar ejes
        ax.set_yticks(range(len(inv_data)))
        ax.set_yticklabels([inv['nombre'].replace('_', ' ').title() 
                           for inv in inv_data])
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b %Y'))
        
        plt.xlabel('Fecha de Vencimiento', fontsize=10)
        plt.title('Timeline de Inversiones Temporales', fontsize=11, fontweight='bold')
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf

    def _generar_waterfall_matplotlib(self, datos_waterfall):
        """Genera gráfico waterfall simple - últimos 6 meses"""
        import numpy as np
        
        datos = datos_waterfall.get('datos', [])
        if not datos or len(datos) < 2:
            return None
        
        # Últimas 6 entradas
        datos = datos[-6:]
        
        labels = [d['mes'] for d in datos]
        saldos = [d['sal'] / 1e6 for d in datos]
        
        fig, ax = plt.subplots(figsize=(7, 3.5))
        
        # Barras simples de saldo
        colors = ['#4A90E2'] * len(saldos)
        bars = ax.bar(labels, saldos, color=colors, edgecolor='black', linewidth=1)
        
        # Etiquetas en barras
        for bar, val in zip(bars, saldos):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height/2,
                   f'${val:.0f}M', ha='center', va='center',
                   fontweight='bold', color='white', fontsize=9)
        
        ax.set_ylabel('Saldo (Millones COP)', fontsize=10)
        ax.set_title('Flujo de Caja Consolidado (últimos 6 meses)', fontsize=11, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf

        return buf

    def _generar_pie_categorias(self, categorias):
        """Genera gráfico pie de categorías de gasto"""
        fig, ax = plt.subplots(figsize=(5, 4))
        
        labels = list(categorias.keys())
        sizes = [v/1e6 for v in categorias.values()]
        colors = ['#4A90E2', '#52B788', '#E67E22', '#E74C3C']
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        ax.set_title('Categorías de Gasto', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf

    def _generar_barras_cobertura(self, proyectos_data):
        """Genera gráfico de barras de cobertura por proyecto"""
        fig, ax = plt.subplots(figsize=(8, 5))
        
        nombres = [p['nombre'][:15] for p in proyectos_data]
        coberturas = [p['cobertura'] for p in proyectos_data]
        
        # Colores según nivel
        colores = []
        for c in coberturas:
            if c >= 20:
                colores.append('#52B788')  # Verde
            elif c >= 10:
                colores.append('#E67E22')  # Naranja
            elif c >= 5:
                colores.append('#E74C3C')  # Rojo
            else:
                colores.append('#6C757D')  # Gris
        
        bars = ax.barh(nombres, coberturas, color=colores, edgecolor='black', linewidth=0.5)
        
        # Etiquetas en barras
        for i, (bar, val) in enumerate(zip(bars, coberturas)):
            ax.text(val + 1, i, f'{val:.1f}s', va='center', fontsize=9)
        
        ax.set_xlabel('Cobertura (semanas)', fontsize=10)
        ax.set_title('Estado Financiero por Proyecto', fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Leyenda
        ax.axvline(x=20, color='#52B788', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=10, color='#E67E22', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=5, color='#E74C3C', linestyle='--', alpha=0.5, linewidth=1)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf

    def action_generar_multiproyecto(self):
        """Genera el reporte PDF multiproyecto histórico"""
        self.ensure_one()
        
        # ========================================================================
        # OBTENER DATOS
        # ========================================================================
        
        # Consolidado más reciente
        ultimo_mes = self.env['sicone.consolidado.mes'].search(
            [], order='anio desc, mes desc', limit=1
        )
        
        if not ultimo_mes:
            raise UserError('No hay datos consolidados. Calcula el dashboard primero.')
        
        # Configuración empresa
        config = self.env['sicone.config.empresa'].search([('active', '=', True)], limit=1)
        
        # Proyectos activos con su último cashflow
        proyectos = self.env['sicone.proyecto'].search([('active', '=', True)])
        
        cashflows = []
        for proyecto in proyectos:
            cf = self.env['sicone.proyecto.cashflow'].search([
                ('proyecto_id', '=', proyecto.id)
            ], order='anio desc, mes desc', limit=1)
            
            if cf:
                # Calcular cobrado e hitos cumplidos
                hitos = self.env['sicone.hito'].search([('proyecto_id', '=', proyecto.id)])
                cobrado = sum(h.cobrado for h in hitos)
                total_hitos = len(hitos)
                hitos_pagados = len([h for h in hitos if h.estado == 'pagado'])
                
                cashflows.append({
                    'nombre': proyecto.name,
                    'cobrado': cobrado,
                    'saldo': cf.saldo_acumulado,
                    'burn_rate': cf.burn_rate_semanal,
                    'cobertura': cf.runway_semanas,
                    'hitos_cumplidos': f'{hitos_pagados}/{total_hitos}',
                })
        
        # Ordenar por nombre
        cashflows.sort(key=lambda x: x['nombre'])
        
        # Inversiones activas
        inversiones = self.env['sicone.inversion.temporal'].search([
            ('estado', '=', 'activa')
        ])
        total_inversiones = sum(inv.monto for inv in inversiones)
        
        # Categorías de gasto (suma de todos los proyectos activos - último mes)
        categorias_query = """
            SELECT 
                SUM(egresos_materiales) as materiales,
                SUM(egresos_mano_obra) as mano_obra,
                SUM(egresos_variables) as variables,
                SUM(egresos_admin) as admin,
                SUM(egresos) as egresos_total
            FROM sicone_proyecto_cashflow cf
            JOIN sicone_proyecto p ON p.id = cf.proyecto_id
            WHERE p.active = true
              AND (cf.proyecto_id, cf.anio, cf.mes) IN (
                SELECT proyecto_id, MAX(anio), MAX(mes)
                FROM sicone_proyecto_cashflow
                GROUP BY proyecto_id
            )
        """
        self.env.cr.execute(categorias_query)
        cat_result = self.env.cr.fetchone()
        
        # Calcular sin_clasificar (egresos totales - suma categorías)
        total_egresos = sum(cat_result[:5]) if cat_result else 0
        suma_categorias = sum(cat_result[:4]) if cat_result else 0
        sin_clasificar = total_egresos - suma_categorias
        
        categorias = {
            'Materiales': cat_result[0] or 0,
            'Mano de Obra': cat_result[1] or 0,
            'Variables': cat_result[2] or 0,
            'Administración': (cat_result[3] or 0) + sin_clasificar,  # Incluye sin_clasificar
        }
        
        # Datos waterfall
        waterfall_data = config.get_waterfall_data() if config else {'datos': [], 'saldo_inicial': 0}
        
        # ========================================================================
        # GENERAR PDF
        # ========================================================================
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=0.4*inch, bottomMargin=0.4*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # TÍTULO
        titulo_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                    fontSize=16, textColor=colors.HexColor('#5D4E99'),
                                    alignment=TA_CENTER, spaceAfter=6)
        story.append(Paragraph("REPORTE GERENCIAL MULTIPROYECTO", titulo_style))
        
        subtitulo_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                        fontSize=11, textColor=colors.HexColor('#6c757d'),
                                        alignment=TA_CENTER, spaceAfter=12)
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Generado: {fecha_gen}", subtitulo_style))
        story.append(Spacer(1, 12))
        
        # KPIs (2 FILAS)
        kpi_data = [
            ['Fecha', 'Estado de Caja', 'Margen de Protección', 'Cobertura'],
            [
                datetime.now().strftime('%d/%m/%Y'),
                self.formatear_moneda(ultimo_mes.saldo_acumulado),
                self.formatear_moneda(ultimo_mes.margen_proteccion),
                f'{ultimo_mes.runway_semanas:.1f} semanas'
            ],
            ['Disponible Inversión', 'Burn Rate Semanal', 'Estado General', 'Proyectos Activos'],
            [
                self.formatear_moneda(total_inversiones),
                self.formatear_moneda(ultimo_mes.burn_rate_semanal),
                'CRÍTICO' if ultimo_mes.runway_semanas < 8 else ('ATENCIÓN' if ultimo_mes.runway_semanas < 12 else 'OK'),
                f'{len([cf for cf in cashflows if cf["hitos_cumplidos"].split("/")[0] != cf["hitos_cumplidos"].split("/")[1]])}/{len(proyectos)}'
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[1.8*inch]*4)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8f9fa')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.white),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 2), (-1, 2), 9),
            ('FONTSIZE', (0, 3), (-1, 3), 10),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f8f9fa')),
            ('BACKGROUND', (2, 3), (2, 3), colors.HexColor('#dc3545')),  # Estado rojo si crítico
            ('TEXTCOLOR', (2, 3), (2, 3), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 12))
        
        # GRÁFICOS (2 columnas)
        graficos_data = []
        
        # Waterfall
        waterfall_buf = self._generar_waterfall_matplotlib(waterfall_data)
        if waterfall_buf:
            graficos_data.append(Image(waterfall_buf, width=3.5*inch, height=2.5*inch))
        
        # Pie (solo categorías con datos > 0, excluir Admin)
        categorias_pie = {k: v for k, v in categorias.items() 
                         if k != 'Administración' and v > 0}
        pie_buf = self._generar_pie_categorias(categorias_pie) if categorias_pie else None
        if pie_buf:
            graficos_data.append(Image(pie_buf, width=3.5*inch, height=2.5*inch))
        
        if graficos_data:
            graficos_table = Table([graficos_data], colWidths=[3.5*inch, 3.5*inch])
            story.append(graficos_table)
            story.append(Spacer(1, 12))
        
        # BARRAS COBERTURA
        barras_buf = self._generar_barras_cobertura(cashflows)
        if barras_buf:
            story.append(Image(barras_buf, width=7*inch, height=3*inch))
            story.append(Spacer(1, 12))
        
        # TABLA PROYECTOS
        tabla_data = [['Proyecto', 'Cobrado', 'Saldo', 'Burn Rate', 'Cobertura', 'Hitos']]
        
        for cf in cashflows:
            tabla_data.append([
                cf['nombre'][:20],
                self.formatear_moneda(cf['cobrado']),
                self.formatear_moneda(cf['saldo']) if cf['saldo'] else '-',
                self.formatear_moneda(cf['burn_rate']) + '/s' if cf['burn_rate'] else '-',
                f"{cf['cobertura']:.1f}s" if cf['cobertura'] else '-',
                cf['hitos_cumplidos']
            ])
        
        tabla = Table(tabla_data, colWidths=[1.4*inch, 1*inch, 1*inch, 1*inch, 0.9*inch, 0.9*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Título de tabla
        tabla_titulo = ParagraphStyle('TablaTitle', parent=styles['Heading2'],
                                     fontSize=12, textColor=colors.HexColor('#1B4332'),
                                     spaceAfter=6)
        story.append(Paragraph("DETALLE POR PROYECTO", tabla_titulo))
        story.append(tabla)
        
        # Generar PDF
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        filename = f"multiproyecto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        self.write({
            'pdf_multiproyecto': base64.b64encode(pdf_data),
            'pdf_multiproyecto_filename': filename,
            'fecha_generacion_mp': fields.Datetime.now()
        })
        
        # Descargar automáticamente
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/sicone.informes/{self.id}/pdf_multiproyecto/{filename}?download=true',
            'target': 'new',
        }

    def action_generar_proyecciones(self):
        """Genera el reporte PDF de proyecciones e inversiones"""
        self.ensure_one()
        
        # Obtener datos
        ultimo_mes = self.env['sicone.consolidado.mes'].search(
            [], order='anio desc, mes desc', limit=1
        )
        
        if not ultimo_mes:
            raise UserError('No hay datos consolidados. Calcula el dashboard primero.')
        
        proyeccion = self.env['sicone.proyeccion.gerencial'].search([
            ('ultimo_calculo', '!=', False)
        ], order='ultimo_calculo desc', limit=1)
        
        if not proyeccion or not proyeccion.datos_grafico:
            raise UserError('No hay proyecciones disponibles. Genera una proyección primero.')
        
        # Parsear datos del gráfico
        datos_grafico = json.loads(proyeccion.datos_grafico)
        
        inversiones = self.env['sicone.inversion.temporal'].search([
            ('estado', '=', 'activa')
        ], order='fecha_vencimiento')
        
        # Generar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=0.4*inch, bottomMargin=0.4*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # ========================================================================
        # TÍTULO
        # ========================================================================
        titulo_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                    fontSize=16, textColor=colors.HexColor('#5D4E99'),
                                    alignment=TA_CENTER, spaceAfter=6)
        story.append(Paragraph("PROYECCIONES DE CASH FLOW", titulo_style))
        
        subtitulo_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                        fontSize=11, textColor=colors.HexColor('#6c757d'),
                                        alignment=TA_CENTER, spaceAfter=12)
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"{proyeccion.nombre} | Generado: {fecha_gen}", subtitulo_style))
        story.append(Spacer(1, 12))
        
        # ========================================================================
        # KPIs (2 FILAS)
        # ========================================================================
        total_inversiones = sum(inv.monto for inv in inversiones)
        
        kpi_data = [
            ['SALDO ACTUAL', 'BURN RATE PROM.', 'ALERTA', 'INVERSIONES ACT.'],
            [
                self.formatear_moneda(ultimo_mes.saldo_acumulado),
                self.formatear_moneda(ultimo_mes.burn_rate_semanal * 4.33) + '/mes',
                'Crítico',  # TODO: Calcular estado real
                self.formatear_moneda(total_inversiones)
            ],
            ['', '', '', ''],
            ['EGRESOS PROY (PROM)', 'GF CALCULADO/MES', 'GF ESTIMADO/MES', 'MESES PROY.'],
            [
                self.formatear_moneda(proyeccion.gastos_fijos_estimados * 5.5),
                self.formatear_moneda(ultimo_mes.gastos_fijos * 4.33),
                self.formatear_moneda(proyeccion.gastos_fijos_estimados),
                str(proyeccion.meses_proyeccion)
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[1.8*inch]*4)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8f9fa')),
            ('BACKGROUND', (2, 1), (2, 1), colors.HexColor('#dc3545')),  # Alerta roja
            ('TEXTCOLOR', (2, 1), (2, 1), colors.white),
            
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 3), (-1, 3), colors.white),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 3), (-1, 3), 9),
            
            ('FONTSIZE', (0, 4), (-1, 4), 10),
            ('ALIGN', (0, 4), (-1, 4), 'CENTER'),
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f8f9fa')),
            
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 12))
        
        # ========================================================================
        # GRÁFICO PROYECCIONES
        # ========================================================================
        grafico_buf = self._generar_grafico_proyecciones(datos_grafico)
        img = Image(grafico_buf, width=7*inch, height=2.8*inch)
        story.append(img)
        story.append(Spacer(1, 12))
        
        # ========================================================================
        # GANTT INVERSIONES
        # ========================================================================
        if inversiones:
            gantt_buf = self._generar_gantt_inversiones(inversiones)
            if gantt_buf:
                img_gantt = Image(gantt_buf, width=7*inch, height=1.5*inch)
                story.append(img_gantt)
                story.append(Spacer(1, 12))
        
        # ========================================================================
        # TABLA MENSUAL
        # ========================================================================
        
        # Usar arrays del JSON que ya tienen los saldos acumulados correctos
        labels_p = datos_grafico.get('labels_proy', [])
        conservador_vals = datos_grafico.get('conservador', [])
        moderado_vals = datos_grafico.get('moderado', [])
        optimista_vals = datos_grafico.get('optimista', [])
        
        # Obtener inversiones por mes desde las líneas
        lineas = self.env['sicone.proyeccion.linea'].search([
            ('proyeccion_id', '=', proyeccion.id),
            ('escenario', '=', 'conservador')
        ], order='fecha')
        
        inv_por_mes = {linea.label: linea.ingresos_inversiones for linea in lineas}
        
        tabla_data = [['Período', 'Conservador', 'Moderado', 'Optimista', 'Ing. Inv.', 'Estado']]
        
        # Iterar sobre los meses proyectados
        for i, label in enumerate(labels_p):
            cons_val = conservador_vals[i] if i < len(conservador_vals) else None
            mode_val = moderado_vals[i] if i < len(moderado_vals) else None
            opti_val = optimista_vals[i] if i < len(optimista_vals) else None
            ing_inv = inv_por_mes.get(label, 0)
            
            # Determinar estado basado en saldo moderado (valores en millones)
            if mode_val:
                if mode_val > 1000:
                    estado = 'OK'
                elif mode_val > 700:
                    estado = 'Atención'
                else:
                    estado = 'Crítico'
            else:
                estado = '-'
            
            tabla_data.append([
                label,
                '-' if cons_val is None else self.formatear_moneda(cons_val * 1e6),
                '-' if mode_val is None else self.formatear_moneda(mode_val * 1e6),
                '-' if opti_val is None else self.formatear_moneda(opti_val * 1e6),
                '-' if ing_inv == 0 else self.formatear_moneda(ing_inv),
                estado
            ])
        
        tabla = Table(tabla_data, colWidths=[1.2*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1*inch, 1*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(tabla)
        
        # Generar PDF
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        filename = f"proyecciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        self.write({
            'pdf_proyecciones': base64.b64encode(pdf_data),
            'pdf_proyecciones_filename': filename,
            'fecha_generacion_proy': fields.Datetime.now()
        })
        
        # Descargar automáticamente
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/sicone.informes/{self.id}/pdf_proyecciones/{filename}?download=true',
            'target': 'new',
        }

    def action_download_multiproyecto(self):
        """Descarga el PDF multiproyecto"""
        self.ensure_one()
        if not self.pdf_multiproyecto:
            raise UserError('No hay PDF generado. Genera el reporte primero.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/sicone.informes/{self.id}/pdf_multiproyecto/{self.pdf_multiproyecto_filename}?download=true',
            'target': 'self',
        }

    def action_download_proyecciones(self):
        """Descarga el PDF de proyecciones"""
        self.ensure_one()
        if not self.pdf_proyecciones:
            raise UserError('No hay PDF generado. Genera el reporte primero.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/sicone.informes/{self.id}/pdf_proyecciones/{self.pdf_proyecciones_filename}?download=true',
            'target': 'self',
        }
