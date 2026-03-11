-- FUNCTION: public.load_csv_file(text, text, text, integer, integer)

-- DROP FUNCTION public.load_csv_file(text, text, text, integer, integer);

CREATE OR REPLACE FUNCTION public.load_csv_file(
	target_table text,
	csv_path text,
	tipo_archivo text,
	col_count integer,
	uid integer)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

iter integer; -- dummy integer to iterate columns with
contador integer;
col text; -- variable to keep the column name at each iteration
col_2 text := ''; -- variable to keep the column name at each iteration
col_first text; -- first column name, e.g., top left corner on a csv file or     spreadsheet
col_first_corregida text;
col_modelo text;
col_archivo text;
tipo_dato text;
listado_columnas text := '';
values_insert text := ''; -- Listado de columnas a insertar
values_insert_2 text := ''; -- Listado de valores a insertar
values_insert_modelo text := '';
values_insert_archivo text := '';
target_table_tmp text := '';
reg RECORD;
registros int;
gestor_captura_hogar_team_id int;
registros_aux_01 int;
registros_aux_02 int;

begin
	-- Versión 10022021.0818
	set schema 'public';

	begin
		create temp table insert_from_csv ();
	exception when others then
		drop table insert_from_csv;
		create temp table insert_from_csv ();
	END;

	-- Limpiando tabla hogares
	if target_table = 'gestor_hogar_team' then
		--truncate table gestor_hogar_team;
		--truncate table gestor_hogares_claro;
	end if;

	-- Limpiando tabla Pyme
	if target_table = 'gestor_pyme_team' then
		--truncate table gestor_pyme_team;
	end if;

	-- add just enough number of columns
	for iter in 1..col_count
	loop
		execute format('alter table insert_from_csv add column col_%s text;', iter);
	end loop;

	-- copy the data from csv file
	begin
		raise notice 'Intentando separado por ;';
		execute format('copy insert_from_csv from %L with delimiter '';'' quote ''"'' csv', csv_path);
	exception when others then
		raise notice 'Intentando separado por ,';
		execute format('copy insert_from_csv from %L with delimiter '','' quote ''"'' csv', csv_path);
	end;

	select count(*) into registros from insert_from_csv;
	raise notice 'Registros importados: %', registros;

	iter := 1;
	col_first := (select col_1 from insert_from_csv limit 1);
	col_first_corregida := lower(replace(replace(col_first, '.', '_'), '""', ''));

	contador := 1;
	-- update the column names based on the first row which has the column names
	for col in execute format('select unnest(string_to_array(lower(replace(replace(replace(replace(replace(trim(insert_from_csv::text, ''()''),'' '',''_''), ''.'', ''_''), ''Í'', ''I''), ''.'', ''_''), ''-'',''_'')), '','')) from insert_from_csv where col_1 = %L', col_first)
	loop
		select c.data_type into tipo_dato
		from gestor_archivos_columnas_team a
			join gestor_archivos_team b on a.column_id = b.id
			join information_schema.columns c on c.table_name=target_table
											  and c.column_name=a.columna_modelo
		where upper(b.name)=upper(tipo_archivo)
		and replace(upper(trim(a.columna_archivo)), ' ', '_')=replace(replace(replace(upper(trim(col)), ' ', '_'), '"', ''), '"', '');

		col_2 = col;
		if col = 'null' or col is null then
			col = 'NA';
			col_2 = 'NA';
		elsif col = 'desc' or col = 'DESC' then
			col_2 = '"' || col || '"';
		else
			col_2 = col;
		end if;
		-- Revisando columna especial
		if replace(trim(upper(col)), '"', '') = upper('ICCID - (Colocar el Iccid de primero)')
			or replace(trim(upper(col)), '"', '') = upper('iccid___(colocar_el_iccid_de_primero)_') then
			col_2 = 'ICCID';
		end if;
		-- Revisar nombres de columna repetidos año_base y base, por ejemplo
		if strpos(listado_columnas, col_2) > 0 and strpos(listado_columnas, col_2) =  strpos(listado_columnas, '_' || col_2)then
			col_2 = col_2 || '_' || contador;
			contador = contador + 1;
		end if;
		listado_columnas = listado_columnas || ',' || col_2;
		listado_columnas = replace(listado_columnas, '"', '');

		execute format('alter table insert_from_csv rename column col_%s to %s', iter, col_2);

		-- Creación de valores para la inserción
		if col = 'null' or col is null or col = 'NA' or col = 'na' then
			null;
		else
			if col = 'desc' or col = 'DESC' then
				col = '"' || col || '"';
			end if;
			if iter = 1 then
				if replace(trim(upper(col)), '"', '') = upper('ICCID - (Colocar el Iccid de primero)')
					or replace(trim(upper(col)), '"', '') = upper('iccid___(colocar_el_iccid_de_primero)_') then
					col = 'ICCID';
				end if;
				values_insert := values_insert || col;
				if tipo_dato = 'date' then
					if target_table = 'gestor_hogar_team' then
						values_insert_2 := values_insert_2 || 'TO_DATE(COALESCE(' || col || '),''''DD-MM-YYYY'')';
					elsif target_table = 'gestor_sims_prendidas' then
						values_insert_2 := values_insert_2 || 'TO_DATE(COALESCE(' || col || '),''''DD/MM/YYYY'')';
					elsif tipo_archivo not in ('AEPAS', 'AEPAS 2') then
						values_insert_2 := values_insert_2 || 'TO_DATE(COALESCE(' || col || '),''''YYYY-MM-DD'')';
					else
						values_insert_2 := values_insert_2 || 'TO_DATE(COALESCE(' || col || '),''''YYYYMMDD'')';
					end if;
				elsif tipo_dato='integer' then
					values_insert_2 := values_insert_2 || 'COALESCE(' || col || ')::int';
					raise notice 'Convertir a entero: %',values_insert_2;
				else
					values_insert_2 := values_insert_2 || 'COALESCE(' || col || ')';
				end if;
			else
				if replace(trim(upper(col)), '"', '') = upper('ICCID - (Colocar el Iccid de primero)')
					or replace(trim(upper(col)), '"', '') = upper('iccid___(colocar_el_iccid_de_primero)_') then
					col = 'ICCID';
				end if;
				values_insert := values_insert || ', ' || col;
				if target_table = 'gestor_sims_prendidas' and col='valor_recargado_' then
					values_insert_2 := values_insert_2 || ', ' || 'COALESCE(' || col || ', '''')::int';
				end if;
				if tipo_dato = 'date' then
					if target_table = 'gestor_hogar_team' then
						values_insert_2 := values_insert_2 || ', ' || 'TO_DATE(COALESCE(' || col || ', ''''),''DD-MM-YYYY'')';
					elsif target_table = 'gestor_sims_prendidas' then
						values_insert_2 := values_insert_2 || ', ' || 'TO_DATE(COALESCE(' || col || ', ''''),''DD/MM/YYYY'')';
					elsif tipo_archivo not in ('AEPAS', 'AEPAS 2') then
						values_insert_2 := values_insert_2 || ', ' || 'TO_DATE(COALESCE(' || col || ', ''''),''YYYY-MM-DD'')';
					else
						values_insert_2 := values_insert_2 || ', ' || 'TO_DATE(COALESCE(' || col || ', ''''),''YYYYMMDD'')';
					end if;
				elsif tipo_dato='integer' then
					values_insert_2 := values_insert_2 || ', ' || 'COALESCE(' || col || ', '''')::int';
				else
					values_insert_2 := values_insert_2 || ', ' || 'COALESCE(' || col || ', '''')';
				end if;
			end if;
		end if;

	iter := iter + 1;
	end loop;

	-- Añadir campos de auditoria
	values_insert := values_insert || ', create_uid, create_date';
	values_insert_2 := values_insert_2 || ', ' || uid || ', now()';

	values_insert = replace(replace(replace(values_insert, '"', ''), 'desc,', '"desc",'), 'DESC,', '"DESC",');
	values_insert_2 = replace(replace(replace(values_insert_2, '"', ''), 'desc,', '"desc",'), 'DESC,', '"DESC",');

	raise notice 'Values_insert: %', values_insert;
	raise notice 'Values_insert_2: %', values_insert_2;

	-- Actualizando datos adicionales
	if target_table = 'gestor_rp_team' and tipo_archivo not in ('SERVICIOS MÓVILES',
																'SERVICIOS MÓVILES 2',
																'SERVICIOS MÓVILES 3',
																'SERVICIOS MÓVILES 4',
																'SERVICIOS MÓVILES 5',
																'RONY',
																'RONY-2',
																'PYMES',
																'PYMES 2',
																'PYMES 3',
																'HOGAR',
																'CONSOLIDADO VENTAS',
															    'AEPAS',
															    'AEPAS 2') then
		update insert_from_csv set imei=0 where imei is null or imei = '';
		update insert_from_csv set iccid=0 where iccid is null or iccid = '';
		update insert_from_csv set min=0 where min is null or min = '';
		update insert_from_csv set imei=REPLACE(LTRIM(REPLACE(imei, '0', ' ')),' ', '0') where imei like '% %';
		update insert_from_csv set imei=trim(replace(imei, '.0','')) where imei like '%.%';
		update insert_from_csv set imei=0 where imei='';
		delete from insert_from_csv where trim(upper(imei))='IMEI';
	end if;

	-- Creando campos de inserción desde la tabla parametrizada
	iter := 1;
	contador := 1;
	for reg in select a.columna_archivo, a.columna_modelo
						from gestor_archivos_columnas_team a
							join gestor_archivos_team b on a.column_id = b.id
						where b.name=tipo_archivo
						order by secuencia
	loop
		if reg.columna_modelo is not null and  reg.columna_archivo is not null then
			-- Corrigiendo nombre columna
			col_modelo = lower(COALESCE(reg.columna_modelo,''));
			col_modelo = replace(col_modelo, '.', '_' );
			col_archivo = lower(COALESCE(reg.columna_archivo,''));
			col_archivo = replace(col_archivo, '.', '_' );
			if col_archivo = 'desc' or col_archivo = 'DESC' then
				col_archivo = '"' || col_archivo || '"';
			end if;
			if col_modelo = 'desc' or col_modelo = 'DESC' then
				col_modelo = '"' || col_modelo || '"';
			end if;
			-- if strpos(values_insert_modelo, col_modelo) > 0 then
			-- Revisar nombres de campo con palabras similares year_base y base, por ejemplo
			if strpos(values_insert_modelo, col_modelo) > 0 and strpos(values_insert_modelo, col_modelo) =  strpos(values_insert_modelo, '_' || col_modelo) then
				col_modelo = col_modelo || '_' || contador;
				contador = contador + 1;
			end if;
			if iter = 1 then
				values_insert_modelo := values_insert_modelo || col_modelo;
				values_insert_archivo := values_insert_archivo || col_archivo;
			else
				values_insert_modelo := values_insert_modelo || ', ' || col_modelo;
				values_insert_archivo := values_insert_archivo || ', ' || col_archivo;
			end if;
		end if;
		iter := iter + 1;
	end loop;
	values_insert_modelo := values_insert_modelo || ', create_uid, create_date';
	values_insert_archivo := values_insert_archivo || ', ' || uid || ', now()';

	-- delete the columns row
	if replace(trim(upper(col_first_corregida)), '"', '') = upper('ICCID - (Colocar el Iccid de primero)')
					or replace(trim(upper(col_first_corregida)), '"', '') = upper('iccid___(colocar_el_iccid_de_primero)_') then
		col_first_corregida = 'ICCID';
		raise notice 'Primera columna especial: %, valor a buscar: %', col_first_corregida, col;
		execute format('delete from insert_from_csv where upper(%s) = trim(upper(%L))', col_first_corregida, col);
	else
		col_first_corregida = replace(col_first_corregida,'"', '');
		raise notice 'Primera columna normal: %', col_first_corregida;
		execute format('delete from insert_from_csv where upper(%s) = upper(%L)', col_first_corregida, col_first_corregida);
	end if;

	-- Creando la columna autonumérica
	-- Creando la secuencia debe quedar fuera de la función
	--CREATE SEQUENCE insert_from_csv_seq;

	execute format('alter table insert_from_csv add column rowID Integer default nextval(''insert_from_csv_seq'')');
	if target_table = 'gestor_rp_team' and tipo_archivo not in ('SERVICIOS MÓVILES', 'SERVICIOS MÓVILES 2', 'SERVICIOS MÓVILES 3', 'SERVICIOS MÓVILES 4', 'SERVICIOS MÓVILES 5', 'RONY', 'RONY-2', 'PYMES', 'PYMES 2', 'PYMES 3', 'HOGAR') then
	-- Eliminando repetidos (ojo, deben ser todos los campos)
		DELETE
		FROM insert_from_csv where rowid in (
		select a.rowid from insert_from_csv a
		inner join
		(
				SELECT ROW_NUMBER() OVER(PARTITION BY a.co_id, a.min, a.imei, a.iccid ORDER BY a.co_id, a.min, a.imei, a.iccid) AS POS ,a.rowID
				FROM insert_from_csv a
				JOIN
				(
					Select
					co_id, min, imei, iccid,
					COUNT(*) AS CONTADOR
					from insert_from_csv
					group by co_id, min, imei, iccid
					HAVING COUNT(*) > 1
				) TB
				ON COALESCE(a.co_id,'') = COALESCE(TB.co_id,'')
				AND COALESCE(a.min,'') = COALESCE(TB.min,'')
				AND COALESCE(a.imei,'') = COALESCE(TB.imei,'')
				AND COALESCE(a.iccid,'') = COALESCE(TB.iccid,'')
		) TB_2
		ON
		a.ROWID = tb_2.ROWID
		and tb_2.pos > 1);
	end if;
	-- Update
	-- Insertando
		/*
		raise notice 'Values_insert: %', values_insert;
		raise notice 'Values_insert_2: %', values_insert_2;
		raise notice 'Values_insert_modelo: %', values_insert_modelo;
		*/

		BEGIN
			if tipo_archivo in ('SERVICIOS MÓVILES', 'SERVICIOS MÓVILES 2', 'SERVICIOS MÓVILES 3', 'SERVICIOS MÓVILES 4', 'SERVICIOS MÓVILES 5', 'RONY', 'RONY-2') and target_table = 'gestor_rp_team' then
				-- Cargando información temporal
				truncate table gestor_temp_min;
				if tipo_archivo in ('SERVICIOS MÓVILES') then
					insert into gestor_temp_min select tele_numb, producto from insert_from_csv
												where upper(CLASE_PREPAGO) in (upper('Postpago'), upper('POSPAGO'), upper('POSPAGO_PORTADO'));
				elsif tipo_archivo in ('SERVICIOS MÓVILES 2') then
					insert into gestor_temp_min select tele_numb, plan from insert_from_csv
												where upper(CLASE_PREPAGO) in (upper('Postpago'), upper('POSPAGO'), upper('POSPAGO_PORTADO'));
				elsif tipo_archivo in ('SERVICIOS MÓVILES 3', 'SERVICIOS MÓVILES 4') then
					insert into gestor_temp_min select min, plan from insert_from_csv
												where upper(CLASE_PREPAGO) in (upper('Postpago'), upper('POSPAGO'), upper('POSPAGO_PORTADO'));
				elsif tipo_archivo in ('SERVICIOS MÓVILES 5') then
					insert into gestor_temp_min select tele_numb, activ_otras from insert_from_csv;
				elsif tipo_archivo in ('RONY', 'RONY-2') then
					insert into gestor_temp_min select min, producto1 from insert_from_csv
												where upper(producto) in (upper('Postpago'), upper('POSPAGO'));
				elsif tipo_archivo in ('POSTPAGO', 'POSTPAGO MEDELLÍN') then
					insert into gestor_temp_min select min, producto from insert_from_csv
												where upper(producto) in (upper('Postpago'), upper('POSPAGO'), upper('POSPAGO_PORTADO'));
				end if;
				if tipo_archivo = 'RONY-2' then
					--raise notice 'Comenzando actualización de RP para RONY-2';
					update gestor_rp_team a set (tipo_venta, tipo_de_convergencia, producto1) = (select tipo_venta, tipo_de_convergencia, producto1
																					 from insert_from_csv b
																					 where a.min=b.min  limit 1)
					where a.min in (select min from insert_from_csv );
				elsif tipo_archivo in ('SERVICIOS MÓVILES', 'SERVICIOS MÓVILES 2') then
					update gestor_rp_team a set producto1 = (select producto1 from gestor_temp_min b
														 where a.min=b.min  limit 1)
					where a.min in (select min from gestor_temp_min );
				elsif tipo_archivo in ('SERVICIOS MÓVILES 3', 'SERVICIOS MÓVILES 4', 'SERVICIOS MÓVILES 5') then

					update gestor_rp_team a set producto1 = (select producto1 from gestor_temp_min b
														 where a.min=b.min limit 1)
					where a.min in (select min from gestor_temp_min );
					raise notice 'Paso por aquí 02';
				else
					-- Actualizar campos RP
					raise notice 'Comenzando actualización otros archivos';
					update gestor_rp_team a set producto1 = (select producto1 from gestor_temp_min b
													 where a.min=b.min  limit 1)
					where a.min in (select min from gestor_temp_min );
				end if;

			elsif target_table = 'gestor_rp_team' then
				select count(*) into registros from
				(select imei, min, iccid, custcode from insert_from_csv
				 intersect
				 select imei, min, iccid, custcode from gestor_rp_team) a;

				update insert_from_csv set imei=0 where imei is null or imei='';
				execute format('insert into %s ( %s ) select %s from insert_from_csv group by %s
							   ON CONFLICT (imei, min, iccid, custcode)
							   DO UPDATE SET write_uid=2, write_date=now()',
							   target_table,
							   values_insert_modelo,
							   values_insert_2,
							   values_insert_2);
			elsif tipo_archivo = 'CONSOLIDADO VENTAS' then
				create index dp_iccid on insert_from_csv (iccid);
				update gestor_aepas_team a set (vendedor_id, vendedor) = (select c.id, COALESCE(c.name, b.asesor_actual)
																		  from insert_from_csv b
																		  	left join hr_employee c on b.cedula = c.identification_id
																		  where a.iccid = b.iccid
																		 limit 1);

			else
				raise notice 'Entro a otros archivos';
				if target_table != '' then
					execute format('insert into %s ( %s ) select %s from insert_from_csv group by %s ON CONFLICT DO NOTHING',
								   target_table,
								   values_insert_modelo,
								   values_insert_2,
								   values_insert_2);
				end if;
			end if;
        EXCEPTION WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
			null;
        END;

		-- HOGAR
		if target_table = 'gestor_hogar_team' or tipo_archivo = 'HOGAR' then
			-- Insertando ventas que esten en PYME

			insert into gestor_captura_hogar_team
				(cuenta,
				ot,
				id_cliente,
				nombre_cliente,
				estrato,
				tel_cliente,
				estado_venta,
				idasesor,
				nombreasesor,
				vendedor,
				id_responsable,
				id_asesor,
				cargo,
				fecha,
				year,
				mes,
				digitador,
				referido,
				cedula_referido,
				nombre_referido,
				telefono_referido,
				correo_referido,
				banco_referido,
				tipo_cuenta_referido,
				cuenta_referido,
				identificacion_vendedor,
				categoria_vendedor,
				departamento_vendedor,
				cargo_vendedor,
				sucursal_vendedor,
				create_uid,
				create_date)

				select cuenta,
				ot,
				id_cliente,
				nombre_cliente,
				estrato,
				tel_cliente,
				estado_venta,
				id_asesor,
				nombre_asesor,
				vendedor,
				id_responsable,
				idasesor,
				cargo,
				fecha,
				year,
				mes,
				digitador,
				referido,
				cedula_referido,
				nombre_referido,
				telefono_referido,
				correo_referido,
				banco_referido,
				tipo_cuenta_referido,
				cuenta_referido,
				identificacion_vendedor,
				categoria_vendedor,
				departamento_vendedor,
				cargo_vendedor,
				sucursal_vendedor,
				create_uid,
				create_date
				from gestor_captura_pyme_team
				where (cuenta, ot) in (select cuenta, ot from gestor_hogar_team)
				and (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)
				ON CONFLICT (cuenta, ot) do nothing;
				--- Eliminando de PYME Ventas existentes en HOGAR
				--update gestor_captura_pyme_team set active=false
				--where (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)

			----
			update gestor_hogar_team set mes=lpad(date_part('MONTH', fecha)::text, 2, '0'), year=date_part('YEAR', fecha)
			where year is null or mes is null;
			update gestor_captura_hogar_team a set
				(paquete_global,
				 fecha,
				 idasesor,
				 renta_global,
				 estrato,
				 venta_convergente,
				 mintic,
			 	 cantserv) =
				(
					select concatenar_campos_hogar_team(b.ot, b.cuenta, b.tipo_registro),
					b.fecha,
					b.idasesor,
					(select sum(replace(c.renta, ',', '.')::float) from gestor_hogar_team c
						where c.cuenta = a.cuenta and c.ot = a.ot
						and c.tipo_registro=b.tipo_registro),
					b.estrato_claro,
					case when b.venta_convergente='X' then
						true
					else
						false
					end,
					case (select descripcion from gestor_codigo_mintic_team where name=b.cod_tarifa limit 1)
						when 'MINTIC' then
							'MINTIC'
						when null then
							'NO DEFINIDO'
						else
							'ESPECIAL'
					end,
			 	cantserv::float
				from gestor_hogar_team b
				where a.cuenta=b.cuenta and a.ot=b.ot
				limit 1);
			update gestor_captura_hogar_team a set
				estado_venta =
				(select
					(select id from gestor_estados_ap_team where name=b.tipo_registro)
					from gestor_hogar_team b
					where  a.cuenta=b.cuenta and a.ot=b.ot
					and b.tipo_registro='Instalada'
					union
					select
				 	(select id from gestor_estados_ap_team where name=b.tipo_registro)
					from gestor_hogar_team b
					where  a.cuenta=b.cuenta and a.ot=b.ot
					and b.tipo_registro='Digitada'
					and (b.ot, b.cuenta) not in (select c.ot, c.cuenta from gestor_hogar_team c where a.cuenta=c.cuenta and a.ot=c.ot and tipo_registro='Instalada')
				limit 1)
				WHERE estado_venta is null or estado_venta = 1;

			truncate table gestor_captura_hogar_detalle_team;
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
			 );
			 update gestor_captura_hogar_team a set
				estado_venta = (select b.estado_ap from gestor_hogar_team b
								where a.cuenta=b.cuenta and a.ot=b.ot
							   limit 1)
			where (a.cuenta, a.ot) in (select c.cuenta, c.ot from gestor_hogar_team c where c.estado_ap is not null and c.estado_ap not in (1,2));
			-- Actualizando el detalle
			-- Mejorar el rendimiento para evitar el truncate
			truncate table gestor_captura_hogar_detalle_agrupado_team;
			insert into gestor_captura_hogar_detalle_agrupado_team
			(captura_hogar_id, tipo_plan, renta_total)
			select captura_hogar_id, tipo_plan_id, sum(replace(renta, ',', '.')::float)
			from gestor_captura_hogar_detalle_team
			group by captura_hogar_id, tipo_plan_id;
			-- Actualizando
		end if;

		--Pyme
		if target_table = 'gestor_pyme_team' then
			begin
				update gestor_captura_pyme_team a set
					(servicio, estado_venta, fecha, id_asesor, nombre_asesor, valor, red) =
					(select
						concatenar_campos_pyme_team(b.ot_venta, b.id_venta, b.tipo_v),
						case
							when tipo_v = 'VENTAS_F' then
								(select id from gestor_estados_ap_team where name='Digitada')
							when tipo_v = 'ALTAS_F' then
								(select id from gestor_estados_ap_team where name='Instalada')
							when tipo_v = 'LEGALIZADO_F' then
								(select id from gestor_estados_ap_team where name='Legalizado')
							when tipo_v = 'CANCELADAS_F' then
								(select id from gestor_estados_ap_team where name='Cancelada')
						end,
						to_date( b.year||'-'||lpad(split_part(b.act_mes,'.',1)::text, 2, '0')||'-'||lpad(split_part(b.act_dia,'.',1)::text, 2, '0'), 'YYYY-MM-DD'),
						b.documento,
						b.funcionario,
						(select sum(TO_NUMBER(c.valor_mensualidad, '999999999999'))::float
						from gestor_pyme_team c
						where c.ot_venta = a.ot and c.id_venta = a.cuenta
						and c.estado_contrato=estado_contrato
						),
					 b.red
					from gestor_pyme_team b
					where a.ot=b.ot_venta
					limit 1);
				EXCEPTION WHEN others THEN
					update gestor_captura_pyme_team a set
					(servicio, estado_venta, fecha, id_asesor, nombre_asesor, valor, red) =
					(select
						concatenar_campos_pyme_team(b.ot_venta, b.id_venta, b.tipo_v),
						case
							when tipo_v = 'VENTAS_F' then
								(select id from gestor_estados_ap_team where name='Digitada')
							when tipo_v = 'ALTAS_F' then
								(select id from gestor_estados_ap_team where name='Instalada')
							when tipo_v = 'LEGALIZADO_F' then
								(select id from gestor_estados_ap_team where name='Legalizado')
							when tipo_v = 'CANCELADAS_F' then
								(select id from gestor_estados_ap_team where name='Cancelada')
						end,
						to_date(b.fecha_periodo, 'DD/MM/YYYY'),
						b.documento,
						b.funcionario,
						(select sum(TO_NUMBER(c.valor_mensualidad, '999999999999'))::float
						from gestor_pyme_team c
						where c.ot_venta = a.ot and c.id_venta = a.cuenta
						and c.estado_contrato=estado_contrato
						),
					 b.red
					from gestor_pyme_team b
					where a.ot=b.ot_venta
					limit 1);
				end;
				update gestor_pyme_team set year=year_base::int, mes=lpad(act_mes, 2, '0') where year is null or mes is null;
			-- Recorriendo para generar detalle
			--Insertando
			truncate table gestor_captura_pyme_detalle_team;
			insert into gestor_captura_pyme_detalle_team
			(captura_pyme_id, fecha, tipored, division, renta, venta, paquete, paquete_pg, paquete_pvd, cod_campana, mintic, tipo_de_producto, tipo_plan_id )
			(select c.id,
			 		to_date(b.fecha_periodo, 'YYYY-MM-DD'),
			 		b.red,
			 		b.division,
			 		b.valor_mensualidad as renta,
			 		b.red as venta,
			 		b.servicio as paquete,
			 		null as paquete_pg,
			 		null as paquete_pvd,
			 		null as cod_campana,
			 		null as mintic,
			 		null as tipo_de_producto,
			 		case when b.red = 'HFC' then
			 			(select id from gestor_tipo_plan_team
						 where name='HFC')
			 		when b.red = 'FO' then
			 			(select id from gestor_tipo_plan_team
						 where name='FO')
			 		end
					from gestor_pyme_team b
					join gestor_captura_pyme_team c on b.id_venta=c.cuenta and b.ot_venta=c.ot
					and b.estado_contrato=(select name from gestor_estados_ap_team d
										   where d.id=c.estado_venta)
			where (c.id, b.servicio) not in (select d.captura_pyme_id, d.paquete
											 from gestor_captura_pyme_detalle_team d)
			 );
			-- Actualizando el detalle
			-- Mejorar el rendimiento para evitar el truncate
			truncate table gestor_captura_pyme_detalle_agrupado_team;
			insert into gestor_captura_pyme_detalle_agrupado_team
			(captura_pyme_id, tipo_plan, renta_total)
			select captura_pyme_id, tipo_plan_id, sum(renta::int)
			from gestor_captura_pyme_detalle_team
			group by captura_pyme_id, tipo_plan_id;
			-- Actualizando
		end if;
		if tipo_archivo in ('AEPAS', 'AEPAS 2', 'SIMS_PRENDIDAS') then
			update gestor_aepas_team set iccid=SUBSTRING (iccid, 3, 17)
									 where character_length(iccid)=20;
			update gestor_aepas_team set sim_prendida=true
									 where iccid in (select iccid from gestor_sims_prendidas);
			update gestor_aepas_team a set id_responsable=(select parent_id from hr_employee where id=vendedor_id),
									 (codigo_aepas_id, codigo_aepas) = (select id, name from gestor_codigos_aepas_team where name= SPLIT_PART(a.tmcyspc, '-',1));
			update gestor_aepas_team a set (codigo_aepas_id, codigo_aepas) = (select id, name from gestor_codigos_aepas_team
															   where name= '25385-2')
			where codigo_aepas_id=5
			and razon_inicial like '%32';
		end if;

end;
$BODY$;

ALTER FUNCTION public.load_csv_file(text, text, text, integer, integer)
    OWNER TO odoo;
