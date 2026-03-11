-- FUNCTION: public.presupuesto_ejecucion_propia_2(integer, integer, character varying, integer)

-- DROP FUNCTION public.presupuesto_ejecucion_propia_2(integer, integer, character varying, integer);

CREATE OR REPLACE FUNCTION public.presupuesto_ejecucion_propia_2(
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
ejecucion_propia integer;

begin
	-- Versión 08022021.1443
	select
		coalesce((select count(*)
			from gestor_consulta_comisiones_tips e
			where coalesce(e.empleado_id, 13168)=l_empleado_id
			and e.year=l_year
			and e.mes=l_mes
			and e.categoria_tipo_plan=(select name from gestor_categoria_tipo_planes_team
										where id=l_categorias_planes)
			), 0)
		+
		coalesce(
			(select count(*)
				from  gestor_captura_hogar_team p
					join gestor_captura_hogar_detalle_team f on p.id = f.captura_hogar_id
					join gestor_tipo_plan_team g on f.venta = g.name
					join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
				where coalesce(id_asesor, 13168)=l_empleado_id
				and year=l_year
				and p.mes=l_mes
				and h.id=l_categorias_planes
			), 0)
		+
		coalesce(
					(
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
							and h.id=l_categorias_planes
						) m
						where coalesce(employee_id, 13168)=l_empleado_id
					), 0)
		+
		coalesce(
					(
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
							where h.id=10 and y.renta::Float > 0
						) m
						where coalesce(employee_id, 13168)=l_empleado_id
						and categoria_id=10
						and categoria_id=l_categorias_planes
					), 0)
		+
		coalesce((select count(*)
			from gestor_captura_pyme_team y
				join gestor_captura_hogar_detalle_agrupado_team f on y.id = f.captura_hogar_id
				join gestor_tipo_plan_team g on f.tipo_plan = g.id
				join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where coalesce(y.idasesor, 13168)=l_empleado_id
			and year=l_year
			and mes=l_mes
			and h.id=l_categorias_planes
		), 0)
		+
		coalesce(
					(
						select sum(valor_mensualidad::float) from
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
						where coalesce(employee_id, 13168)=l_empleado_id
					), 0)
		+
		coalesce((select count(*)
			from gestor_aepas_team z
				join gestor_codigos_aepas_team i on z.codigo_aepas = i.name
				join gestor_tipo_plan_team g on i.descripcion = g.name
				join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where coalesce(z.vendedor_id, 13168)=l_empleado_id
			and z.year=l_year
			and z.mes=l_mes
			and h.id=l_categorias_planes
			and coalesce(z.sim_prendida, 'false') = false
		), 0)
		+
		coalesce((select sum(z.cantidad)
			from gestor_kit_prepagos_team z
				join gestor_tipo_plan_team g on z.tipo_plan_id = g.id
				join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where coalesce(vendedor_id, 13168)=l_empleado_id
			and z.year=l_year
			and z.mes=l_mes
			and h.id=l_categorias_planes
		), 0) into ejecucion_propia;
	--from gestor_presupuestos_team a
	--join gestor_presupuestos_detalle_team c on c.presupuesto_id=a.id
	--join gestor_categoria_tipo_planes_team d on c.categorias_planes_id=d.id;
	--where c.id=lc_id_detalle_presupuesto;
	return ejecucion_propia;
end;
$BODY$;

ALTER FUNCTION public.presupuesto_ejecucion_propia_2(integer, integer, character varying, integer)
    OWNER TO odoo;
