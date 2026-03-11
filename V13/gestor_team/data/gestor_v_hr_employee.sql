-- View: public.gestor_v_hr_employee

-- DROP VIEW public.gestor_v_hr_employee;

CREATE OR REPLACE VIEW public.gestor_v_hr_employee
 AS
 SELECT a.id,
    a.identification_id AS identificacion,
    a.name AS nombre,
    c.name AS cargo,
    e.name AS categoria,
    a.parent_id,
    b.name AS nombre_responsable,
    d.name AS cargo_responsable,
    f.name AS sucursal,
    a.work_email,
    a.work_phone,
    a.mobile_phone,
    g.name AS departamento
   FROM hr_employee a
     LEFT JOIN hr_employee b ON a.parent_id = b.id
     LEFT JOIN hr_job c ON a.job_id = c.id
     LEFT JOIN hr_job d ON b.job_id = d.id
     LEFT JOIN hr_employee_category e ON a.category_id = e.id
     LEFT JOIN gestor_sucursales f ON a.sucursal_id = f.id
     LEFT JOIN hr_department g ON a.department_id = g.id;

ALTER TABLE public.gestor_v_hr_employee
    OWNER TO odoo;

