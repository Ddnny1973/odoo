-- FUNCTION: public.cruce_ventas_tips_valida_tipo_plan(character varying, character varying, character varying, integer, integer)

-- DROP FUNCTION public.cruce_ventas_tips_valida_tipo_plan(character varying, character varying, character varying, integer, integer);

CREATE OR REPLACE FUNCTION public.cruce_ventas_tips_valida_tipo_plan(
	tipo_de_plan character varying,
	producto character varying,
	producto1 character varying,
	l_id_1 integer,
	l_id_2 integer)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
revision_tipo_plan varchar;

begin
	-- Versión 08022021.0445
	select
	case when producto1 is not null then
		case when
		(select 1
			where trim(upper(producto1)) in
		(
		select trim(upper(i.name)) from gestor_tipo_plan_team g
		join gestor_lineas_planes_team_gestor_tipo_plan_team_rel h on g.id=h.gestor_tipo_plan_team_id
		join gestor_lineas_planes_team i on i.id = h.gestor_lineas_planes_team_id
		where trim(upper(g.name)) = trim(upper(tipo_de_plan)))) = 1 then
			'ok'
		else
			case when l_id_1 is null and l_id_2 is null then
					'No encontrada en RP'
				when producto is null and producto1 is null then
					'Tipo de plan No encontrado en RP'
				else
					'No coincidente'
				end
		end
		when trim(upper(tipo_de_plan)) = trim(upper(producto)) or strpos(trim(upper(producto)), trim(upper(tipo_de_plan)))>0 then
			'ok'
		else
			case when
				(select 1
				where trim(upper(producto)) in
				(
				select trim(upper(i.name)) from gestor_tipo_plan_team g
				join gestor_lineas_planes_team_gestor_tipo_plan_team_rel h on g.id=h.gestor_tipo_plan_team_id
				join gestor_lineas_planes_team i on i.id = h.gestor_lineas_planes_team_id
				where trim(upper(g.name)) = trim(upper(tipo_de_plan)))) = 1 then
				'ok'
			else
				case when l_id_1 is null and l_id_2 is null then
					'No encontrada en RP'
				when producto is null and producto1 is null then
					'Tipo de plan No encontrado en RP'
				else
					'No coincidente'
				end
			end
	end into revision_tipo_plan;
	return revision_tipo_plan;
end;
$BODY$;

ALTER FUNCTION public.cruce_ventas_tips_valida_tipo_plan(character varying, character varying, character varying, integer, integer)
    OWNER TO odoo;
