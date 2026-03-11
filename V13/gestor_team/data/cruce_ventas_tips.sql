-- FUNCTION: public.cruce_ventas_tips(integer, date)

-- DROP FUNCTION public.cruce_ventas_tips(integer, date);

CREATE OR REPLACE FUNCTION public.cruce_ventas_tips(
	uid integer,
	fecha_rp date)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

	begin
		-- Versión 08022021.0445
		set schema 'public';

		-- Limpiando la tabla de cruces
		truncate table gestor_cruce_ventas_tips cascade;

		-- Realizando el cruce
		insert into gestor_cruce_ventas_tips
		(fecha_tips,
				fecha_rp,
				revision_fecha,
				nombre_plan_tips,
				nombre_plan_rp,
				revision_del_plan,
				tipo_de_plan_tips,
				tipo_de_plan_rp,
				revision_tipo_de_plan,
				iccid_tips,
				iccid_rp,
				imei_tips,
				imei_rp,
				revision_imei,
				min_tips,
				min_rp,
				revision_min,
				equipo_tips,
				equipo_stok,
				revision_equipo,
				costo_rec_log,
				pago,
				sucursal,
				tipo_de_vendedor,
				nombre_para_mostrar_del_vendedor,
				estado_actual,
				cliente_actual,
				usuario_creador,
				venta_id_tips,
		 		plan_tips_id,
			   	create_uid,
			    create_date,
				encontrada_rp,
				estado_tips)
	select
		a.fecha fecha_tips,
		COALESCE(to_date(c.activacion, 'YYYYMMDD'), to_date(b.fecha_reposicion, 'YYYY/MM/DD')) fecha_rp,
		case when a.fecha = COALESCE(to_date(c.activacion, 'YYYYMMDD'), to_date(b.fecha_reposicion, 'YYYY/MM/DD')) then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_fecha,
		a.nombre_del_plan nombre_plan_tips,
		case when b.id is not null and b.producto is not null and c.producto1 is null then
				trim(upper(COALESCE(b.producto,'')))
			when c.id is not null and b.producto is null and c.producto1 is not null then
				trim(upper(COALESCE(c.descripcion,'')))
			when strpos(upper(a.nombre_del_plan), 'KIT') > 0 or strpos(upper(a.nombre_del_plan), 'REPO') > 0 then
				trim(upper(COALESCE(b.producto,'')))
			else
				COALESCE(c.descripcion,'')
		end nombre_plan_rp,
		case when c.producto = 'POSPAGO_PORTADO' and c.producto1 is null then
			cruce_ventas_tips_valida_nombre_plan(a.nombre_del_plan, a.tipo_de_plan, c.producto, c.producto, c.descripcion, b.id, c.id)
		else
			cruce_ventas_tips_valida_nombre_plan(a.nombre_del_plan, a.tipo_de_plan, b.producto, c.producto1, c.descripcion, b.id, c.id)
		end revision_del_plan,
		a.tipo_de_plan tipo_de_plan_tips,
		case when c.producto = 'POSPAGO_PORTADO' and c.producto1 is null then
			c.producto
		else
			upper(COALESCE(b.producto, COALESCE(c.producto1,'')))
		end tipo_de_plan_rp,
		case when c.producto = 'POSPAGO_PORTADO' and c.producto1 is null then
			cruce_ventas_tips_valida_tipo_plan(a.tipo_de_plan, c.producto, c.producto, b.id, c.id)
		else
			cruce_ventas_tips_valida_tipo_plan(a.tipo_de_plan, b.producto, c.producto1, b.id, c.id)
		end revision_tipo_de_plan,
		a.iccid iccid_tips,
		b.iccid iccid_rp,
		a.imei imei_tips,
		COALESCE(b.imei, c.imei) imei_rp,
		case when REPLACE(LTRIM(REPLACE(COALESCE(a.imei,''), '0', ' ')),' ', '0')=REPLACE(LTRIM(REPLACE(COALESCE(b.imei, c.imei), '0', ' ')),' ', '0') then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_imei,
		a.min min_tips,
		COALESCE(b.min, c.min) min_rp,
		case when COALESCE(a.min,'') = COALESCE(b.min, c.min) then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_min,
		a.marca_del_equipo || ' ' || a.modelo_del_equipo equipo_tips,
		a.nombre_de_equipo_en_stok equipo_stok, -- Concatenar el modelo
		case when (strpos(trim(upper(a.nombre_de_equipo_en_stok)),
		(trim(upper(a.marca_del_equipo)) || ' ' || trim(upper(a.modelo_del_equipo))))) > 0 then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_equipo,
		'' costo_rec_log,
		'' pago,
		a.sucursal,
		a.tipo_De_vendedor,
		a.nombre_para_mostrar_del_vendedor,
		'' estado_actual,
		a.cliente_nombre cliente_Actual,
		a.usuario_creador,
		a.venta_id::integer,
		f.id,
		uid, now(),
		case when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'Encontrada'
		end Revision_RP,
		a.estado_tips
		from gestor_consulta_ventas_tips a
			left join gestor_rp_team b on b.imei=a.imei
			and b.imei is not null and b.imei not like '0%'
			and REPLACE(LTRIM(REPLACE(b.imei, '0', ' ')),' ', '0') != ''
			--and (b.producto like 'REPO%' or b.producto like 'KIT%')
			and (upper(a.tipo_de_plan) like 'REPO%' or upper(a.tipo_de_plan) like 'KIT%')
			and (b.fecha_reposicion::date >= fecha_rp or b.fechalegalizacion is not null)
			left join gestor_rp_team c on c.min=a.min
			--and c.imei = '0'
			--and REPLACE(LTRIM(REPLACE(a.imei, '0', ' ')),' ', '0') = ''
			and c.min not like '0%'
			and c.producto like 'POS%'
			and c.descripcion is not null
			and (to_date(c.activacion, 'yyyymmdd')::date >= fecha_rp or c.fecha_reposicion::date >= fecha_rp)
			left join gestor_planes_team d on a.nombre_del_plan = d.name
			--left join gestor_tipo_plan_team e on d.tipo_plan = e.id
			left join gestor_planes_team f on a.nombre_del_plan=f.name
		where a.tipo_de_plan != 'Cambio de Servicio';

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
		update gestor_consulta_ventas_tips a set cfm=(case
													  	when cargo_fijo_mensual::float >= 69900 then
													 		'Alto Valor'
													  	else
													  		'Bajo Valor'
													  	end
													 	);
		update gestor_cruce_ventas_tips set tipo_de_plan_rp='Prueba que finalizó'
		where id=684291;

	end;
$BODY$;

ALTER FUNCTION public.cruce_ventas_tips(integer, date)
    OWNER TO odoo;
