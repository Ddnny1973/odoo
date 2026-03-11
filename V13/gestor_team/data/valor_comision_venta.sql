-- FUNCTION: public.valor_comision_venta(integer)

-- DROP FUNCTION public.valor_comision_venta(integer);

CREATE OR REPLACE FUNCTION public.valor_comision_venta(
	l_id integer)
    RETURNS double precision
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
ln_Valor_Comision float;
ln_cfm_con_iva float;
ln_cfm_sin_iva float;
ln_empleado_id integer;
ln_mes_de_liquidacion integer;

begin
	-- Versión 08022021.0445
	set schema 'public';
	ln_Valor_Comision :=0;


	select cfm_con_iva, cfm_sin_iva, empleado_id, mes_de_liquidacion into ln_cfm_con_iva, ln_cfm_sin_iva, ln_empleado_id, ln_mes_de_liquidacion
	from gestor_consulta_comisiones_tips
	where id=l_id;

	-- Esta función calcula el valor a pagar por la venta según esquema de comisiones
	-- Versión 0.01

	-- Cálculo por empleado
	if ln_mes_de_liquidacion = 0 then
		--select a.id, a.name, c.name esquema, c.mes1, c.mes2, c.mes3, c.mes4, c.mes5, c.mes6, tipo_pago
		select sum(mes1) into ln_Valor_Comision  from
		(
			select case when tipo_pago = 'porcentaje' then
							c.mes1 / 100 * ln_cfm_sin_iva
						else
							c.mes1
						end
			from hr_employee a
			join gestor_comisiones_team_hr_employee_rel b on b.hr_employee_id = a.id
			join gestor_comisiones_team c on b.gestor_comisiones_team_id = c.id
			where a.id in (ln_empleado_id)
			union
			select case when tipo_pago = 'porcentaje' then
							c.mes1 / 100 * ln_cfm_sin_iva
						else
							c.mes1
						end
			from gestor_comisiones_team c
			join gestor_comisiones_team_hr_employee_category_rel e on e.gestor_comisiones_team_id = c.id
																   and e.hr_employee_category_id = (select category_id from hr_employee
																									where id in (ln_empleado_id) )
			) x;
	else
		ln_Valor_Comision = 0;
	end if;
	---
	return ln_Valor_Comision;

end;
$BODY$;

ALTER FUNCTION public.valor_comision_venta(integer)
    OWNER TO odoo;
