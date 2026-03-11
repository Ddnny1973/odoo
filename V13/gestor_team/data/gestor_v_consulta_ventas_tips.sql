-- View: public.gestor_v_consulta_ventas_tips

DROP VIEW public.gestor_v_consulta_ventas_tips;

CREATE OR REPLACE VIEW public.gestor_v_consulta_ventas_tips
 AS
 SELECT *
   FROM gestor_consulta_ventas_tips;

ALTER TABLE public.gestor_v_consulta_ventas_tips
    OWNER TO odoo;
