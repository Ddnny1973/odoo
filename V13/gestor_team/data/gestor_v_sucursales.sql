-- View: public.gestor_v_sucursales

-- DROP VIEW public.gestor_v_sucursales;

CREATE OR REPLACE VIEW public.gestor_v_sucursales
 AS
 SELECT a.id AS id_sucursal,
    a.name,
    a.codigo,
    a.tipo,
    a.director_id,
    b.name AS director
   FROM gestor_sucursales a
     LEFT JOIN hr_employee b ON a.director_id = b.id;

ALTER TABLE public.gestor_v_sucursales
    OWNER TO odoo;

