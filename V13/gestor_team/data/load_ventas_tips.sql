-- FUNCTION: public.load_ventas_tips()

-- DROP FUNCTION public.load_ventas_tips();

CREATE OR REPLACE FUNCTION public.load_ventas_tips(
	)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

begin
	-- Versión 08022021.0445
	set schema 'public';

	-- Corrige la consulta de ventas de TIPS y las carga en el modelo ventas de Odoo
	-- Adiciona valores KEY de odoo

	truncate table gestor_consulta_ventas_tips;
	insert into gestor_consulta_ventas_tips
	(fecha,
	min,
	iccid,
	imei,
	contrato,
	valor,
	custcode,
	marca_del_equipo,
	nombre_de_equipo_en_stok,
	nombre_de_la_simcard_en_stok,
	modelo_del_equipo,
	valor_del_equipo,
	nombre_para_mostrar_del_vendedor,
	tipo_de_vendedor,
	regional,
	sucursal,
	ciudad,
	nombre_del_plan,
	tipo_de_plan,
	valor_cobrado,
	codigo_distribuidor,
	cliente_nombre,
	cliente_id,
	vendedor_id,
	vendedor_nombre,
	cargo_fijo_mensual,
	permanencia_pendiente,
	clasificacion_del_plan,
	es_multiplay,
	es_upgrade,
	es_linea_nueva,
	es_venta_digital,
	es_con_equipo,
	es_telemercadeo,
	fecha_de_activacion_en_punto_de_activacion,
	usuario_creador,
	venta_id,
	meses,
	plan_id,
	estado_tips,
	comision_pagada,
	reconocimiento_pagado,
	tipo_de_activacion,
	con_equipo)
	select a.fecha,
	a.min,
	a.iccid,
	a.imei,
	a.contrato,
	a.valor,
	a.custcode,
	a.marca_del_equipo,
	a.nombre_de_equipo_en_stok,
	a.nombre_de_la_simcard_en_stok,
	a.modelo_del_equipo,
	a.valor_del_equipo,
	a.nombre_para_mostrar_del_vendedor,
	a.tipo_de_vendedor,
	a.regional,
	a.sucursal,
	a.ciudad,
	a.nombre_del_plan,
	a.tipo_de_plan,
	a.valor_cobrado,
	a.código_distribuidor,
	a.cliente_nombre,
	a.cliente_id,
	a.vendedor_nombre,
	a.vendedor_id,
	a.cargo_fijo_mensual,
	a.permanencia_pendiente,
	a.clasificación_del_plan,
	case a.es_multiplay when 'True' then true else false end es_multiplay,
	case a.es_upgrade when 'True' then true else false end es_upgrade,
	case a.es_línea_nueva when 'True' then true else false end es_linea_nueva,
	case a.es_venta_digital when 'True' then true else false end es_venta_digital,
	case a.es_con_equipo when 'True' then true else false end es_con_equipo,
	case a.es_telemercadeo when 'True' then true else false end es_telemercadeo,
	a.fecha_de_activación_en_punto_de_activación::date fecha_de_activación_en_punto_de_activación,
	a.usuario_creador,
	a.venta_id,
	date_part('month',age(now(), a.fecha)) meses,
	b.id plan_id,
	a.estado,
	comision_pagada,
	reconocimiento_pagado,
	tipo_de_activacion,
	con_equipo
	from gestor_consulta_ventas_tips_tmp a
	join gestor_planes_team b on trim(upper(a.nombre_del_plan)) = trim(upper(b.name));

	update gestor_consulta_ventas_tips set id=venta_id::int;

	update gestor_consulta_ventas_tips a set empleado_id=(select id from hr_employee
												   where identification_id=a.vendedor_id);
		update gestor_consulta_ventas_tips a set cargo=(select c.name from hr_employee b
														 	join hr_job c on b.job_id=c.id
														   where b.id=a.empleado_id);
		update gestor_consulta_ventas_tips a set categoria_empleado=(select c.name from hr_employee b
														 	join hr_employee_category c on b.category_id=c.id
														   where b.id=a.empleado_id);
		update gestor_consulta_ventas_tips a set responsable=(select parent_id from hr_employee
														   where id=a.empleado_id);
		update gestor_consulta_ventas_tips a set responsable_nombre=(select name from hr_employee
														   where id=a.responsable);
		update gestor_consulta_ventas_tips x set categoria_tipo_plan=(select c.name from gestor_planes_team a
																		join gestor_tipo_plan_team b on a.tipo_plan=b.id
																		left join gestor_categoria_tipo_planes_team c on c.id=b.categoria_id
																		where a.id=x.plan_id);
		update gestor_consulta_ventas_tips set mes=EXTRACT(MONTH FROM fecha), year=EXTRACT(YEAR FROM fecha);
		update gestor_consulta_ventas_tips a set presupuesto=(select presupuesto
													  from gestor_presupuestos_detalle_team b
													  join gestor_categoria_tipo_planes_team c on b.categorias_planes_id=c.id
													  where a.empleado_id=b.employee_id
													  and a.categoria_tipo_plan=c.name
													  and a.year=b.year
													  and a.mes=b.mes);

		/*update gestor_consulta_ventas_tips a set cfm=(case
													  	when cargo_fijo_mensual::float >= 69900 then
													 		'Alto Valor'
													  	else
													  		'Bajo Valor'
													  	end
													 	);
														*/

end;
$BODY$;

ALTER FUNCTION public.load_ventas_tips()
    OWNER TO odoo;
