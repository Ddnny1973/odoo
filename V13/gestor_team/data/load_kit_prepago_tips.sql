-- FUNCTION: public.load_kit_prepago_tips()

-- DROP FUNCTION public.load_kit_prepago_tips();

CREATE OR REPLACE FUNCTION public.load_kit_prepago_tips(
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

	insert into gestor_kit_prepagos_team
	(identificacion ,
		vendedor,
		producto,
		numerofefactura,
		fechadeventa,
		tipoproducto,
		cantidad,
	 	create_date,
	    create_uid,
	 	tipo_plan,
	 	fecha
	)
	select
		identificacion,
		vendedor,
		producto,
		numerodefactura,
		fechadeventa,
		tipodeproducto,
		cantidad::float,
		now(),
		2,
		'Kit Equipos',
		fechadeventa
	from gestor_kit_prepago_tmp;

	update gestor_kit_prepagos_team a set (vendedor_id, job_id, responsable_id) = (select id, job_id, parent_id from hr_employee b
																			 		where b.identification_id = a.identificacion
																			 		),
										  (tipo_plan_id,categoria_tipo_planes_id) = (select id, categoria_id from gestor_tipo_plan_team
																					 where name=a.tipo_plan),
										   year = date_part('year',fecha),
										   mes = LPAD(date_part('month',fecha)::text, 2, '0');

end;
$BODY$;

ALTER FUNCTION public.load_kit_prepago_tips()
    OWNER TO odoo;
