-- View: public.gestor_v_gestor_categoria_tipo_planes_team

-- DROP VIEW public.gestor_v_gestor_categoria_tipo_planes_team;

CREATE OR REPLACE VIEW public.gestor_v_gestor_categoria_tipo_planes_team
 AS
 SELECT *
   FROM gestor_categoria_tipo_planes_team;

ALTER TABLE public.gestor_v_gestor_categoria_tipo_planes_team
    OWNER TO odoo;
