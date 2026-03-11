-- FUNCTION: public.cruce_ventas_tips_valida_nombre_plan(character varying, character varying, character varying, character varying, character varying, integer, integer)

-- DROP FUNCTION public.cruce_ventas_tips_valida_nombre_plan(character varying, character varying, character varying, character varying, character varying, integer, integer);

CREATE OR REPLACE FUNCTION public.cruce_ventas_tips_valida_nombre_plan(
	nombre_del_plan_tips character varying,
	tipo_de_plan_tips character varying,
	producto character varying,
	producto1 character varying,
	descripcion character varying,
	l_id_1 integer,
	l_id_2 integer)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
revision_nombre_plan character varying;
nombre_plan_rp character varying;
codigo_plan character varying;
existe_cod_plan int;
revision_tipo_plan character varying;

begin
	-- Versión 02032021.0445
	if l_id_1 is not null and producto is not null and producto1 is null then
		nombre_plan_rp = trim(upper(COALESCE(producto,'')));
	elsif l_id_2 is not null and producto is null and producto1 is not null then
		nombre_plan_rp = trim(upper(COALESCE(descripcion,'')));
	elsif strpos(upper(nombre_del_plan_tips), 'KIT') > 0 or strpos(upper(nombre_del_plan_tips), 'REPO') > 0 then
		nombre_plan_rp = trim(upper(COALESCE(producto,'')));
	else
		nombre_plan_rp = COALESCE(descripcion,'');
	end if;
	--nombre_plan_rp = trim(upper(COALESCE(producto,'') || COALESCE(descripcion,'')));
	existe_cod_plan = strpos(nombre_plan_rp, '-');
	codigo_plan = trim(split_part(nombre_plan_rp, '-', 2));

	--raise notice 'nombre_plan_rp: %', nombre_plan_rp;
	--raise notice 'Existe código de plan: %', existe_cod_plan;
	--raise notice 'Código del plan: %', codigo_plan;

	if l_id_1 is null and l_id_2 is null then
		revision_nombre_plan = 'Venta no encontrada en RP';
	else
		if existe_cod_plan > 0 then			-- Revisando si tiene código de plan
			if strpos(upper(nombre_del_plan_tips), codigo_plan) > 0 then
				if producto = 'POSPAGO_PORTADO' and producto1 = 'POSPAGO_PORTADO' then
					--raise notice 'Entró en revisión de tipo de plan para el nombre del plan 1';
					revision_tipo_plan = cruce_ventas_tips_valida_tipo_plan(tipo_de_plan_tips, producto, producto, l_id_1, l_id_2) ;
				else
					--raise notice 'Entró en revisión de tipo de plan para el nombre del plan 2';
					--raise notice 'producto %  producto1: %', producto, producto1;
					revision_tipo_plan = cruce_ventas_tips_valida_tipo_plan(tipo_de_plan_tips, producto, producto1, l_id_1, l_id_2) ;
				end if;
				if revision_tipo_plan = 'ok' then
					revision_nombre_plan = 'ok';
				else
					--revision_nombre_plan = 'Ok en TIPS - ' || revision_tipo_plan;
					revision_nombre_plan = 'Ok pero con error en tipo de Plan';
				end if;
			else
				revision_nombre_plan = 'No coincidente';
			end if;
		else
			raise notice 'No encontó codigo de plan';
			if strpos(upper(nombre_del_plan_tips), 'KIT') > 0 then
				raise notice 'Es KIT';
				if strpos(upper(nombre_del_plan_tips), 'FINANCIADO') > 0 then
					raise notice 'Es KIT Financiado en tips';
					if strpos(nombre_plan_rp, 'FINANCIADO') > 0 then
						revision_nombre_plan = 'ok';
					else
						raise notice 'No encontró la palabra financiado en nombre_plan_rp';
						revision_nombre_plan = 'No coincidente';
					end if;
				elsif strpos(upper(nombre_del_plan_tips), 'PREPAGO') > 0 then
					if strpos(nombre_plan_rp, 'PREPAGO') > 0 then
						revision_nombre_plan = 'ok';
					else
						revision_nombre_plan = 'No coincidente';
					end if;
				else
					revision_nombre_plan = 'No coincidente';
				end if;
			elsif strpos(upper(nombre_del_plan_tips), 'REPOS') > 0 then
				if strpos(nombre_plan_rp, 'REPOS') > 0 then
						revision_nombre_plan = 'ok';
					else
						revision_nombre_plan = 'No coincidente';
					end if;
			else
				raise notice 'No encontó la palabra kit en nombre_del_plan tips';
				revision_nombre_plan = 'No coincidente';
			end if;
		end if;
	end if;
	--raise notice 'Código plan RP: %', codigo_plan;
	return revision_nombre_plan;
end;
$BODY$;

ALTER FUNCTION public.cruce_ventas_tips_valida_nombre_plan(character varying, character varying, character varying, character varying, character varying, integer, integer)
    OWNER TO odoo;
