-- FUNCTION: public.concatenar_campos_hogar_team(character varying, character varying, character varying)

-- DROP FUNCTION public.concatenar_campos_hogar_team(character varying, character varying, character varying);

CREATE OR REPLACE FUNCTION public.concatenar_campos_hogar_team(
	l_ot character varying,
	l_cuenta character varying,
	l_estado character varying)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
columna_concatenada character varying;
contador int;
reg RECORD;

begin
	-- Versión 08022021.0445
	set schema 'public';

	-- Esta fucnión devuelve los datos existentes en cada campo por registro encontrado
	columna_concatenada = '';
	contador=1;
	for reg in select * from gestor_hogar_team
			   where cuenta= l_cuenta  and ot= l_ot
			   and tipo_registro= l_estado
	loop
		if contador = 1 then
			columna_concatenada = columna_concatenada || COALESCE(reg.paquete) || ' ';
		else
			columna_concatenada = COALESCE(reg.paquete) || ', ' || columna_concatenada;
		end if;
		contador = contador + 1 ;


	end loop;
	return columna_concatenada;

end;
$BODY$;

ALTER FUNCTION public.concatenar_campos_hogar_team(character varying, character varying, character varying)
    OWNER TO odoo;
