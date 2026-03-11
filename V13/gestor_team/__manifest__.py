{
    'name': 'TEAM Comunicaciones',
    'version': '13.1.1.3',
    'description': """
                    Personalización TEAM Comunicaciones
                    Se requieren módulos Python:
                        pyodbc (https://parzibyte.me/blog/2019/06/14/conexion-sql-server-python-pyodbc-crud/
                                puede necesitar: apt-get install unixodbc-dev,
                                pip install wheel),
                        pandas
                    """,
    'author': 'Gestor Consultoría',
    'website': 'http://www.gestorconsultoria.com.co',
    'depends': [
                'l10n_co_cities',
                'hr'
                ],
    'data': [
            # 'security/ir_rule.xml',

            # Tablas
            # 'data/gestor_consulta_comisiones_tips_tmp.sql',
            # 'data/gestor_consulta_ventas_tips_tmp.sql',
            # 'data/gestor_ejecucion_por_empleado.sql',
            # 'data/gestor_kit_prepago_tmp.sql',

            # Funciones / SP
            # 'data/categorias_faltantes_presupuesto.sql',
            # 'data/concatenar_campos_hogar_team.sql',
            # 'data/concatenar_campos_pyme_team.sql',
            # 'data/crear_detalle_hogar.sql',
            # 'data/cruce_ventas_tips_valida_nombre_plan.sql',
            # 'data/cruce_ventas_tips_valida_tipo_plan.sql',
            # 'data/cruce_ventas_tips.sql',
            # 'data/f_gestor_ejecucion_por_empleado.sql',
            # 'data/load_comisiones_ventas_tips.sql',
            # 'data/load_csv_file.sql',
            # 'data/load_hogares_csv_file.sql',
            # 'data/load_kit_prepago_tips.sql',
            # 'data/load_ventas_tips.sql',
            # 'data/presupuesto_ejecucion_propia_2.sql',
            # 'data/presupuesto_ejecucion_responsable.sql',
            # 'data/valor_comision_venta.sql',

            # Vistas SQL
            # 'data/gestor_v_consulta_ventas_tips.sql',
            # 'data/gestor_v_gestor_cartera_team.sql',
            # 'data/gestor_v_gestor_categoria_tipo_planes_team.sql',
            # 'data/gestor_v_gestor_tipo_plan_team.sql',
            # 'data/gestor_v_hogar.sql',
            # 'data/gestor_v_hr_employee.sql',
            # 'data/gestor_v_presupuesto_ventas.sql',
            # 'data/gestor_v_sucursales.sql',

            # Seguridad ODOO
            'security/gestor_team_security.xml',
            'security/ir.model.access.csv',

            # Vistas ODOO
            'views/views_sucursales.xml',
            'views/views_zonas.xml',
            'views/inerited_views_hr_employee.xml',
            'views/views_planes_team.xml',
            'views/views_rp_team.xml',
            'views/views_reconocimiento_logistico_team.xml',
            'views/views_hogar.xml',
            'views/views_pyme.xml',
            # 'views/views_pos_order_ineherit.xml',
            'views/archivos.xml',
            'views/views_comisiones.xml',
            'views/views_ventas_tips.xml',
            'views/views_cruce_tips.xml',
            'views/views_presupuestos.xml',
            'views/views_sims_prendidas.xml',
            'views/views_aepas.xml',
            'views/views_cartera.xml',
            'views/views_productos_team.xml',
            'views/views_digesto.xml',
            'views/views_descuentos.xml',
            'views/views_biometrias.xml',
            'views/views_clientes_team.xml',

            'reports/report_liquidacion.xml',

            'wizard/cambio_responsables_wz.xml',
            'wizard/planes_wz.xml',
            'wizard/rp_wz.xml',
            'wizard/cargar_archivos_wz.xml',
            'wizard/actualizar_presupuestos_wz.xml',
            # 'wizard/hogar_wz.xml',
            'wizard/liquidacion_comisiones_wz.xml',
            'wizard/actualizacion_tips_wz.xml',
            'wizard/cartera_wz.xml',
            'wizard/liquidacion_comisiones_hogar_wz.xml',
            'wizard/pago_colillas_comisiones.xml',
            'wizard/pago_colillas_comisiones_2.xml',
            'wizard/actualizar_proceso_biometria_wz.xml',
            'wizard/cargar_archivos_mail_wz.xml',
            'wizard/cerrar_mes_wz.xml',
            'wizard/liquidar_directores_wz.xml',
            'wizard/liquidar_descuentos_wz.xml',
            # 'wizard/reporte_presupuestos.xml',

            # 'reports/report.xml',
            # 'reports/report_presupuestos.xml',

            'views/menu.xml',
            ],
    'application': True,
}
