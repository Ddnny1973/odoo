-- FUNCTION: public.load_hogares_csv_file(text, text, integer)

-- DROP FUNCTION public.load_hogares_csv_file(text, text, integer);

CREATE OR REPLACE FUNCTION public.load_hogares_csv_file(
	target_table text,
	csv_path text,
	uid integer)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

begin
	-- Versión 08022021.0445
	truncate table gestor_hogares_claro;
	--copy gestor_hogares_claro
	--FROM '/var/lib/postgresql/data/compartida/rp/HOGARES.txt'
	--delimiter ';' csv header;

	execute format('copy gestor_hogares_claro from %L with delimiter '';'' quote ''"'' csv ', csv_path);

	update gestor_hogar_team a set 	(tipo_registro,
									idasesor,
									nombreasesor,
									paquete,
									fecha,
									cantserv,
									tipo_red,
									estrato_claro,
									visor_movil,
									val_identidad,
									serial_captor,
									venta,
									procesamiento_uid,
									procesamiento_date
									) = (select tipo_registro,
												 idasesor,
												 nombreasesor,
												 paquete,
												 TO_DATE(fecha,'dd/mm/yyyy'),
												 cantserv,
												 tipored,
												 estrato,
												 visor_movil,
												 val_identidad,
												 serial_captor,
										 		 venta,
										 		 uid,
										 		 now()
												from gestor_hogares_claro b
												where b.cuenta=a.cuenta
												and b.ot=a.ot
												and b.paquete=(select name from product_template c
																join product_product d on d.product_tmpl_id = c.id
																and d.id=a.producto_id)
												order by tipo_registro desc,fecha, cuenta, ot, paquete
												limit 1
												);

end;
$BODY$;

ALTER FUNCTION public.load_hogares_csv_file(text, text, integer)
    OWNER TO odoo;
