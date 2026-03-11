-- FUNCTION: public.gestor_ejecucion_por_empleado(date, date)

-- DROP FUNCTION public.gestor_ejecucion_por_empleado(date, date);

CREATE OR REPLACE FUNCTION public.gestor_ejecucion_por_empleado(
	l_fecha_inicial date,
	l_fecha_final date)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
DECLARE
    reg_employee RECORD;
	reg_categoria RECORD;
	ln_meses INTEGER;
	i INTEGER := 0;
	ln_year INTEGER;
	ln_mes_inicial INTEGER;
	ln_mes INTEGER;
	ln_numero_empleados INTEGER := 0 ;
	ln_iteraciones INTEGER := 0;
begin
	-- Versión 10022021.0855
	set schema 'public';
	ln_year = DATE_PART('year', l_fecha_inicial::date);
	ln_mes_inicial = DATE_PART('month', l_fecha_inicial::date);
	ln_mes = ln_mes_inicial;

	-- Meses entre las fechas
	SELECT (DATE_PART('year', l_fecha_final::date) - DATE_PART('year', l_fecha_inicial::date)) * 12 +
            (DATE_PART('month', l_fecha_final::date) - DATE_PART('month', l_fecha_inicial::date)) INTO ln_meses;
	RAISE NOTICE '-- MESES: %', ln_meses;

	-- Carga todos los empleados por categoría y calcula su ejecución
	--truncate table gestor_ejecucion_por_empleado;
	LOOP
		RAISE NOTICE '-- YEAR: %', ln_year;
		RAISE NOTICE '-- MES: %', LPAD(ln_mes::text, 2, '0');
		FOR reg_employee IN select * from hr_employee LOOP
			ln_numero_empleados = ln_numero_empleados + 1;
			--RAISE NOTICE '-- EMPLEADO: %', reg_employee.name;
			FOR reg_categoria IN select * from gestor_categoria_tipo_planes_team where active=true LOOP
				ln_iteraciones = ln_iteraciones + 1;
				insert into gestor_ejecucion_por_empleado
				(year,
				 mes,
				 categoria,
				 categorias_planes_id,
				 empleado,
				 responsable,
				 presupuesto,
				 employee_id,
				 cargo,
				 responsable_id,
				 ejecutado,
				 ejecutado_propio,
				 informe,
				 origen
				)
				values
				(ln_year,
				 LPAD(ln_mes::text, 2, '0'),
				 reg_categoria.name,												--Nombre categoría
				 reg_categoria.id,
				 reg_employee.name,													--Nombre del empleado
				 (select name from hr_employee where id=reg_employee.parent_id),   --Nombre del responsable del empleado
				 0,																	--Preuspuesto asignado al empleado
				 reg_employee.id,
				 (select name from hr_job where id=reg_employee.job_id),		   --Nombre del cargo del empleado
				 reg_employee.parent_id,											--ID responsable
				 presupuesto_ejecucion_responsable(reg_employee.id,
												   ln_year,
												   LPAD(ln_mes::text, 2, '0'),
												   reg_categoria.id
												  ),								--Ejecutado
				presupuesto_ejecucion_propia_2(reg_employee.id,
												   ln_year,
												   LPAD(ln_mes::text, 2, '0'),
												   reg_categoria.id
												  ),								--Ejecutado Propio
				 reg_categoria.informe,
				 'EJECUCIÓN POR EMPLEADO'
				) ON CONFLICT (year, mes, employee_id, categorias_planes_id) DO UPDATE set ejecutado = presupuesto_ejecucion_responsable(reg_employee.id,
																										   ln_year,
																										   LPAD(ln_mes::text, 2, '0'),
																										   reg_categoria.id
																										  ),
																							ejecutado_propio = presupuesto_ejecucion_propia_2(reg_employee.id,
																										   ln_year,
																										   LPAD(ln_mes::text, 2, '0'),
																										   reg_categoria.id
																										  );
			END LOOP;
		END LOOP;
		if ln_mes = 12 then
			ln_mes = 1;
			ln_year = ln_year + 1;
		else
			ln_mes = ln_mes + 1;
		end if;
		i = i + 1;
		exit when ln_meses = i - 1 ;
	END LOOP;
	RAISE NOTICE '-- TOTAL ITERACCIONES: %', ln_iteraciones;
end;
$BODY$;

ALTER FUNCTION public.gestor_ejecucion_por_empleado(date, date)
    OWNER TO odoo;
