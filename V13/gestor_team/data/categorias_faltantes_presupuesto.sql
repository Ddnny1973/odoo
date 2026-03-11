-- FUNCTION: public.categorias_faltantes_presupuesto(integer, integer, character varying)

-- DROP FUNCTION public.categorias_faltantes_presupuesto(integer, integer, character varying);

CREATE OR REPLACE FUNCTION public.categorias_faltantes_presupuesto(
	l_empleado_id integer,
	l_year integer,
	l_mes character varying)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
ejecucion_propia integer;

begin
	-- Versión 01032021.0300
	select a.id
		from gestor_categoria_tipo_planes_team a
		where a.id not in (select categorias_planes_id from gestor_presupuestos_detalle_team
		where employee_id=l_empleado_id
		and year=l_year
		and mes=l_mes);
end;
$BODY$;

ALTER FUNCTION public.categorias_faltantes_presupuesto(integer, integer, character varying)
    OWNER TO odoo;
