-- View: public.gestor_v_gestor_tipo_plan_team

DROP VIEW IF EXISTS public.gestor_v_gestor_tipo_plan_team;

-- Versión 08022021.0445

create or replace view gestor_v_gestor_tipo_plan_team as
select * from gestor_tipo_plan_team;

ALTER TABLE public.gestor_v_gestor_tipo_plan_team
    OWNER TO odoo;
