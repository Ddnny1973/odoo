-- View: public.gestor_v_hogar

-- DROP VIEW public.gestor_v_hogar;

CREATE OR REPLACE VIEW public.gestor_v_hogar
 AS
 SELECT gestor_hogar_team.cuenta,
    gestor_hogar_team.ot,
    concatenar_campos_hogar_team(gestor_hogar_team.ot, gestor_hogar_team.cuenta, gestor_hogar_team.tipo_registro) AS paquete_global,
    gestor_hogar_team.tipo_registro,
        CASE
            WHEN gestor_hogar_team.venta_convergente::text = 'X'::text THEN true
            ELSE false
        END AS venta_convergente,
        CASE ( SELECT gestor_codigo_mintic_team.descripcion
               FROM gestor_codigo_mintic_team
              WHERE gestor_codigo_mintic_team.name::text = gestor_hogar_team.cod_tarifa::text
              GROUP BY gestor_codigo_mintic_team.descripcion)
            WHEN 'MINTIC'::text THEN 'MINTIC'::text
            WHEN NULL::text THEN 'NO DEFINIDO'::text
            ELSE 'ESPECIAL'::text
        END AS mintic,
    gestor_hogar_team.tercero,
    gestor_hogar_team.punto,
    gestor_hogar_team.grupo,
    gestor_hogar_team.categoria,
    gestor_hogar_team.canal2,
    gestor_hogar_team.cantserv,
    gestor_hogar_team.area,
    gestor_hogar_team.zona,
    gestor_hogar_team.d_distrito,
    gestor_hogar_team.poblacion,
    ( SELECT sum(c.renta::double precision) AS sum
           FROM gestor_hogar_team c
          WHERE c.cuenta::text = gestor_hogar_team.cuenta::text AND gestor_hogar_team.ot::text = c.ot::text AND c.tipo_registro::text = gestor_hogar_team.tipo_registro::text) AS renta_global,
    gestor_hogar_team.no_contrato,
    gestor_hogar_team.estrato,
    gestor_hogar_team.gv_area,
    gestor_hogar_team.cod_tarifa,
    gestor_hogar_team.visor_movil,
    gestor_hogar_team.serial_captor,
    ( SELECT gestor_estados_ap_team.id
           FROM gestor_estados_ap_team
          WHERE gestor_estados_ap_team.name::text = gestor_hogar_team.tipo_registro::text) AS estado_venta,
    gestor_hogar_team.fecha_venta AS fecha
   FROM gestor_hogar_team
  ORDER BY gestor_hogar_team.tipo_registro, gestor_hogar_team.paquete;

ALTER TABLE public.gestor_v_hogar
    OWNER TO odoo;
