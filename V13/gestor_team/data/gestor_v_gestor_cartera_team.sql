-- View: public.gestor_v_gestor_cartera_team

DROP VIEW public.gestor_v_gestor_cartera_team;

CREATE OR REPLACE VIEW public.gestor_v_gestor_cartera_team
 AS
 SELECT *
   FROM gestor_cartera_team;

ALTER TABLE public.gestor_v_gestor_cartera_team
    OWNER TO odoo;
