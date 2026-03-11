-- FUNCTION: public.crear_detalle_hogar(character varying, character varying)

-- DROP FUNCTION public.crear_detalle_hogar(character varying, character varying);

CREATE OR REPLACE FUNCTION public.crear_detalle_hogar(
	l_ot character varying,
	l_cuenta character varying)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

begin
	-- Versión 08022021.0445
	set schema 'public';
	insert into gestor_captura_hogar_detalle_team
			(captura_hogar_id,
			 fecha,
			 tipored,
			 division,
			 renta,
			 venta,
			 paquete,
			 paquete_pg,
			 paquete_pvd,
			 cod_campana,
			 mintic,
			 tipo_de_producto,
			 tipo_plan_id)
			(select c.id,
			 		b.fecha,
			 		b.tipo_red,
			 		b.division,
			 		b.renta,
			 		b.venta,
			 		b.paquete,
			 		b.paquete_pg,
			 		b.paquete_pvd,
			 		b.cod_campana,
			 		b.mintic,
			 		b.tipo_de_producto,
			 		case when tipo_red = 'DTH' then
			 			(select id from gestor_tipo_plan_team
						 where name='DTH')
			 		when venta = 'Servicios Principales' then
			 			(select id from gestor_tipo_plan_team
						 where name='Servicios Principales')
			 		when venta = 'Servicios Adicionales' then
			 			(select id from gestor_tipo_plan_team
						 where name='Servicios Adicionales')
			 		when venta = 'Upgrade' then
			 			(select id from gestor_tipo_plan_team
						 where name='Upgrade Hogar')
					when venta = 'Migración' or venta = 'Migracion' then
						(select id from gestor_tipo_plan_team
						 where name='Migración')
			 		end
					from gestor_hogar_team b
					join gestor_captura_hogar_team c on b.cuenta=c.cuenta and b.ot=c.ot
					and b.tipo_registro=(select name from gestor_estados_ap_team d where d.id=c.estado_venta)
			where (c.id, b.paquete) not in (select d.captura_hogar_id, d.paquete from gestor_captura_hogar_detalle_team d)
			and b.ot = l_ot and b.cuenta = l_cuenta
			 );

			insert into gestor_captura_hogar_detalle_agrupado_team
			(captura_hogar_id, tipo_plan, renta_total)
			select captura_hogar_id, tipo_plan_id, sum(renta::int)
			from gestor_captura_hogar_detalle_team a
			join gestor_captura_hogar_team b on a.captura_hogar_id = b.id
			where b.ot = l_ot and b.cuenta = l_cuenta
			group by captura_hogar_id, tipo_plan_id;

end;
$BODY$;

ALTER FUNCTION public.crear_detalle_hogar(character varying, character varying)
    OWNER TO odoo;
