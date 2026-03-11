-- FUNCTION: public.presupuesto_ejecucion_responsable(integer, integer, character varying, integer)

-- DROP FUNCTION public.presupuesto_ejecucion_responsable(integer, integer, character varying, integer);

CREATE OR REPLACE FUNCTION public.presupuesto_ejecucion_responsable(
	l_empleado_id integer,
	l_year integer,
	l_mes character varying,
	l_categorias_planes integer)
    RETURNS integer
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
ejecucion_responsable integer;

begin
	-- Versión 08022021.0445

	select sum(cantidad) into ejecucion_responsable from
	(
		select count(*) as cantidad
			from gestor_consulta_comisiones_tips a
			where coalesce(a.empleado_id, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
			and a.year=l_year
			and a.mes=l_mes
			and a.categoria_tipo_plan=(select name from gestor_categoria_tipo_planes_team
									   where id = l_categorias_planes
									  )
		union
		select count(*) as cantidad
			from gestor_captura_hogar_team a
			join gestor_captura_hogar_detalle_agrupado_team f on a.id = f.captura_hogar_id
			join gestor_tipo_plan_team g on f.tipo_plan = g.id
			join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			left join hr_employee i on a.idasesor = i.identification_id
			--where coalesce(a.idasesor, 13168) in (
			where coalesce(i.id, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
			and a.year=l_year
			and a.mes=l_mes
			and h.id=(select id from gestor_categoria_tipo_planes_team
									   where id = l_categorias_planes)
		union
		-----
						select count(*) from
						(
							select y.*, g.*, h.*, s.id as employee_id from
							(
								select * from  gestor_hogar_team z
								where tipo_registro='Instalada'
								and (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)
								and year=l_year
								and mes=l_mes
								union
								select * from gestor_hogar_team x
								where tipo_registro='Digitada'
								and (cuenta, ot) not in (select cuenta, ot from  gestor_hogar_team x
														 where tipo_registro='Instalada')
								and (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)
								and year=l_year
								and mes=l_mes
							) y
							join gestor_tipo_plan_team g on g.name = replace(replace(y.venta, 'Upgrade', 'Upgrade Hogar'), 'Migracion', 'Migración')
							join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
							left join hr_employee s on s.identification_id = y.idasesor
							where h.id=l_categorias_planes
							and h.id!=10
						) m
						where coalesce(employee_id, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
		-----
		union
		select count(*) as cantidad
			from gestor_captura_pyme_team a
			join gestor_captura_pyme_detalle_agrupado_team f on a.id = f.captura_pyme_id
			join gestor_tipo_plan_team g on f.tipo_plan = g.id
			join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where coalesce(a.idasesor, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
			and a.year=l_year
			and a.mes=l_mes
			and h.id=(select id from gestor_categoria_tipo_planes_team
									   where id = l_categorias_planes)
union
		-----
						select sum(replace(valor_mensualidad,',','.')::float) from
						(
							select y.*, g.*, h.*, s.id as employee_id from
							(
								select * from  gestor_pyme_team z
								where tipo_v in ('ALTAS_F')
								and (id_venta, ot_venta) not in (select cuenta, ot from gestor_captura_pyme_team)
								and year=l_year
								and mes=l_mes
								union
								select * from gestor_pyme_team x
								where tipo_v in ('VENTAS_F')
								and (id_venta, ot_venta) not in (select id_venta, ot_venta from  gestor_pyme_team x
														 where tipo_v in ('ALTAS_F'))
								and (id_venta, ot_venta) not in (select cuenta, ot from gestor_captura_pyme_team)
								and year=l_year
								and mes=l_mes
							) y
							join gestor_tipo_plan_team g on g.name = y.red
							join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
							left join hr_employee s on s.identification_id = (select identification_id from hr_employee where id=13168)
							where h.id=l_categorias_planes
						) m
						where coalesce(employee_id, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
		-----
		union
		select count(*) as cantidad
			from gestor_aepas_team a
			join gestor_codigos_aepas_team i on a.codigo_aepas = i.name
			join gestor_tipo_plan_team g on i.descripcion = g.name
			join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where coalesce(a.vendedor_id, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
			and a.year=l_year
			and a.mes=l_mes
			and h.id=(select id from gestor_categoria_tipo_planes_team
									   where id = l_categorias_planes)
		    and coalesce(a.sim_prendida, 'false') = false
		union
		select sum(cantidad) as cantidad
			from gestor_kit_prepagos_team a
			join gestor_tipo_plan_team g on a.tipo_plan_id = g.id
			join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where coalesce(a.vendedor_id, 13168) in (
				-----------------------------------------------
					select empleado_id from gestor_empleados_recursivos_all
					where responsable_id=l_empleado_id
					and empleado_id not in (select empleado_id from gestor_presupuestos_team)
				------------------------------------------------
			)
			and a.year=l_year
			and a.mes=l_mes
			and h.id=(select id from gestor_categoria_tipo_planes_team
									   where id = l_categorias_planes)
		) x;
	return ejecucion_responsable;
end;
$BODY$;

ALTER FUNCTION public.presupuesto_ejecucion_responsable(integer, integer, character varying, integer)
    OWNER TO odoo;
