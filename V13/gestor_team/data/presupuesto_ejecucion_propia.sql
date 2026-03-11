-- FUNCTION: public.presupuesto_ejecucion_propia(integer)

-- DROP FUNCTION public.presupuesto_ejecucion_propia(integer);

CREATE OR REPLACE FUNCTION public.presupuesto_ejecucion_propia(
	lc_id_detalle_presupuesto integer)
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
			where e.empleado_id=a.empleado_id
			and e.year=a.year
			and e.mes=a.mes
			and e.categoria_tipo_plan=d.name
			), 0)
		+
		coalesce(
			(select count(*)
				from  gestor_captura_hogar_team p
					join gestor_captura_hogar_detalle_agrupado_team f on p.id = f.captura_hogar_id
					join gestor_tipo_plan_team g on f.tipo_plan = g.id
					join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
				where p.id_asesor=a.empleado_id
				and EXTRACT(YEAR FROM p.fecha)=a.year
				and EXTRACT(MONTH FROM p.fecha)=a.mes::int
				and h.id=d.id
			), 0)
		+
		coalesce((select count(*) from
					(
						(select * from  gestor_hogar_team z
						where tipo_registro='Instalada'
						and (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)
						and z.idasesor=a.identificacion_empleado
						union
						select * from gestor_hogar_team x
						where tipo_registro='Digitada'
						and (cuenta, ot) not in (select cuenta, ot from  gestor_hogar_team x
												 where tipo_registro='Instalada')
						and (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)
						and x.idasesor=a.identificacion_empleado
						and EXTRACT(YEAR FROM x.fecha)=a.year
						and EXTRACT(MONTH FROM x.fecha)=a.mes::int
						) y
						join gestor_tipo_plan_team g on g.name = replace(replace(y.venta, 'Upgrade', 'Upgrade Hogar'), 'Migracion', 'Migración')
						join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
						and h.id=d.id
						)
				 ), 0)
		+
		coalesce((select count(*)
			from gestor_captura_pyme_team y
				join gestor_captura_hogar_detalle_agrupado_team f on y.id = f.captura_hogar_id
				join gestor_tipo_plan_team g on f.tipo_plan = g.id
				join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where y.idasesor=a.empleado_id
			and EXTRACT(YEAR FROM y.fecha)=a.year
			and EXTRACT(MONTH FROM y.fecha)=a.mes::int
			and h.id=d.id
		), 0)
		+
		coalesce((select count(*)
			from gestor_aepas_team z
				join gestor_tipo_plan_team g on z.codigo_aepas = g.name
				join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where z.vendedor_id=a.empleado_id
			and EXTRACT(YEAR FROM z.activacion)=a.year
			and EXTRACT(MONTH FROM z.activacion)=a.mes::int
			and h.id=d.id
		), 0)
		+
		coalesce((select sum(z.cantidad)
			from gestor_kit_prepagos_team z
				join gestor_tipo_plan_team g on z.tipo_plan_id = g.id
				join gestor_categoria_tipo_planes_team h on g.categoria_id = h.id
			where z.vendedor_id=a.empleado_id
			and EXTRACT(YEAR FROM z.fecha)=a.year
			and EXTRACT(MONTH FROM z.fecha)=a.mes::int
			and h.id=d.id
		), 0) into ejecucion_propia
	from gestor_presupuestos_team a
	join gestor_presupuestos_detalle_team c on c.presupuesto_id=a.id
	join gestor_categoria_tipo_planes_team d on c.categorias_planes_id=d.id
	where c.id=lc_id_detalle_presupuesto;
	return ejecucion_propia;
end;
$BODY$;

ALTER FUNCTION public.presupuesto_ejecucion_propia(integer)
    OWNER TO odoo;
