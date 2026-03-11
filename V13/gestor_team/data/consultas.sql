-- FUNCTION: public.concatenar_campos_hogar_team(character varying, character varying, character varying)

-- DROP FUNCTION public.concatenar_campos_hogar_team(character varying, character varying, character varying);

CREATE OR REPLACE FUNCTION public.concatenar_campos_hogar_team(
	l_ot character varying,
	l_cuenta character varying,
	l_estado character varying)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
columna_concatenada character varying;
contador int;
reg RECORD;

begin
	set schema 'public';

	-- Esta fucnión devuelve los datos existentes en cada campo por registro encontrado
	columna_concatenada = '';
	contador=1;
	for reg in select * from gestor_hogares_claro
			   where cuenta= l_cuenta  and ot= l_ot
			   and tipo_registro= l_estado
	loop
		if contador = 1 then
			columna_concatenada = columna_concatenada || COALESCE(reg.paquete) || ' ';
		else
			columna_concatenada = COALESCE(reg.paquete) || ', ' || columna_concatenada;
		end if;
		contador = contador + 1 ;


	end loop;
	return columna_concatenada;

end;
$BODY$;

ALTER FUNCTION public.concatenar_campos_hogar_team(character varying, character varying, character varying)
    OWNER TO odoo;

	-- FUNCTION: public.cruce_ventas_tips(integer, date)

	-- DROP FUNCTION public.cruce_ventas_tips(integer, date);

	CREATE OR REPLACE FUNCTION public.cruce_ventas_tips(
		uid integer,
		fecha_rp date)
	    RETURNS void
	    LANGUAGE 'plpgsql'
	    COST 100
	    VOLATILE PARALLEL UNSAFE
	AS $BODY$
	declare

	begin
		set schema 'public';

		-- Limpiando la tabla de cruces
		truncate table gestor_cruce_ventas_tips cascade;

		-- Realizando el cruce
		insert into gestor_cruce_ventas_tips
		(fecha_tips,
				fecha_rp,
				revision_fecha,
				nombre_plan_tips,
				nombre_plan_rp,
				revision_del_plan,
				tipo_de_plan_tips,
				tipo_de_plan_rp,
				revision_tipo_de_plan,
				iccid_tips,
				iccid_rp,
				imei_tips,
				imei_rp,
				revision_imei,
				min_tips,
				min_rp,
				revision_min,
				equipo_tips,
				equipo_stok,
				revision_equipo,
				costo_rec_log,
				pago,
				sucursal,
				tipo_de_vendedor,
				nombre_para_mostrar_del_vendedor,
				estado_actual,
				cliente_actual,
				usuario_creador,
				venta_id_tips,
		 		plan_tips_id,
			   	create_uid,
			    create_date,
				encontrada_rp,
				estado_tips)
	select
		a.fecha fecha_tips,
		COALESCE(to_date(c.activacion, 'YYYYMMDD'), to_date(b.fecha_reposicion, 'YYYY/MM/DD')) fecha_rp,
		case when a.fecha = COALESCE(to_date(c.activacion, 'YYYYMMDD'), to_date(b.fecha_reposicion, 'YYYY/MM/DD')) then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_fecha,
		a.nombre_del_plan nombre_plan_tips,
		--COALESCE(b.producto,'') || COALESCE(c.descripcion,'') nombre_plan_rp,
		COALESCE(c.descripcion, COALESCE(b.producto,'')) nombre_plan_rp,
		cruce_ventas_tips_valida_nombre_plan(a.nombre_del_plan, a.tipo_de_plan, b.producto, c.producto1, c.descripcion, b.id, c.id) revision_del_plan,
		a.tipo_de_plan tipo_de_plan_tips,
		upper(COALESCE(b.producto, COALESCE(c.producto1,''))) tipo_de_plan_rp,
		cruce_ventas_tips_valida_tipo_plan(a.tipo_de_plan, b.producto, c.producto1, b.id, c.id) revision_tipo_de_plan,
		a.iccid iccid_tips,
		b.iccid iccid_rp,
		a.imei imei_tips,
		b.imei imei_rp,
		case when REPLACE(LTRIM(REPLACE(COALESCE(a.imei,''), '0', ' ')),' ', '0')=REPLACE(LTRIM(REPLACE(COALESCE(b.imei,''), '0', ' ')),' ', '0') then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_imei,
		a.min min_tips,
		COALESCE(b.min, c.min) min_rp,
		case when COALESCE(a.min,'') = COALESCE(b.min, c.min) then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_min,
		a.marca_del_equipo || ' ' || a.modelo_del_equipo equipo_tips,
		a.nombre_de_equipo_en_stok equipo_stok, -- Concatenar el modelo
		case when (strpos(trim(upper(a.nombre_de_equipo_en_stok)),
		(trim(upper(a.marca_del_equipo)) || ' ' || trim(upper(a.modelo_del_equipo))))) > 0 then
			'ok'
		when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'No coincidente'
		end revision_equipo,
		'' costo_rec_log,
		'' pago,
		a.sucursal,
		a.tipo_De_vendedor,
		a.nombre_para_mostrar_del_vendedor,
		'' estado_actual,
		a.cliente_nombre cliente_Actual,
		a.usuario_creador,
		a.venta_id::integer,
		f.id,
		uid, now(),
		case when b.id is null and c.id is null then
			'No encontrada en RP'
		else
			'Encontrada'
		end Revision_RP,
		a.estado_tips
		from gestor_consulta_ventas_tips a
			left join gestor_rp_team b on b.imei=a.imei
			and b.imei is not null and b.imei not like '0%'
			and REPLACE(LTRIM(REPLACE(b.imei, '0', ' ')),' ', '0') != ''
			--and (b.producto like 'REPO%' or b.producto like 'KIT%')
			and (upper(a.tipo_de_plan) like 'REPO%' or upper(a.tipo_de_plan) like 'KIT%')
			and (b.fecha_reposicion::date >= fecha_rp or b.fechalegalizacion is not null)
			left join gestor_rp_team c on c.min=a.min
			--and c.imei = '0'
			--and REPLACE(LTRIM(REPLACE(a.imei, '0', ' ')),' ', '0') = ''
			and c.min not like '0%'
			and c.producto like 'POS%'
			and c.descripcion is not null
			and (to_date(c.activacion, 'yyyymmdd')::date >= fecha_rp or c.fecha_reposicion::date >= fecha_rp)
			left join gestor_planes_team d on a.nombre_del_plan = d.name
			--left join gestor_tipo_plan_team e on d.tipo_plan = e.id
			left join gestor_planes_team f on a.nombre_del_plan=f.name
		where a.tipo_de_plan != 'Cambio de Servicio';

		update gestor_cruce_ventas_tips set tipo_de_plan_rp=null
		where tipo_de_plan_rp='';
		update gestor_cruce_ventas_tips set nombre_plan_rp=null
		where nombre_plan_rp='';
		update gestor_consulta_ventas_tips set id=venta_id::int;

	end;
	$BODY$;

	ALTER FUNCTION public.cruce_ventas_tips(integer, date)
	    OWNER TO odoo;



-- FUNCTION: public.cruce_ventas_tips_valida_nombre_plan(character varying, character varying, character varying, character varying, character varying, integer, integer)

-- DROP FUNCTION public.cruce_ventas_tips_valida_nombre_plan(character varying, character varying, character varying, character varying, character varying, integer, integer);

CREATE OR REPLACE FUNCTION public.cruce_ventas_tips_valida_nombre_plan(
	nombre_del_plan_tips character varying,
	tipo_de_plan_tips character varying,
	producto character varying,
	producto1 character varying,
	descripcion character varying,
	l_id_1 integer,
	l_id_2 integer)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
revision_nombre_plan character varying;
nombre_plan_rp character varying;
codigo_plan character varying;
existe_cod_plan int;
revision_tipo_plan character varying;

begin
	if producto is null then
		nombre_plan_rp = trim(upper(COALESCE(descripcion,'')));
	else
		nombre_plan_rp = trim(upper(COALESCE(producto,'')));
	end if;
	--nombre_plan_rp = trim(upper(COALESCE(producto,'') || COALESCE(descripcion,'')));
	existe_cod_plan = strpos(nombre_plan_rp, '-');
	codigo_plan = trim(split_part(nombre_plan_rp, '-', 2));

	raise notice 'nombre_plan_rp: %', nombre_plan_rp;
	raise notice 'Existe código de plan: %', existe_cod_plan;
	raise notice 'Código del plan: %', codigo_plan;

	if l_id_1 is null and l_id_2 is null then
		revision_nombre_plan = 'Venta no encontrada en RP';
	else
		if existe_cod_plan > 0 then			-- Revisando si tiene código de plan
			if strpos(upper(nombre_del_plan_tips), codigo_plan) > 0 then
				revision_tipo_plan = cruce_ventas_tips_valida_tipo_plan(tipo_de_plan_tips, producto, producto1, l_id_1, l_id_2) ;
				if revision_tipo_plan = 'ok' then
					revision_nombre_plan = 'ok';
				else
					--revision_nombre_plan = 'Ok en TIPS - ' || revision_tipo_plan;
					revision_nombre_plan = 'Ok pero con error en tipo de Plan';
				end if;
			else
				revision_nombre_plan = 'No coincidente';
			end if;
		else
			raise notice 'No encontó codigo de plan';
			if strpos(upper(nombre_del_plan_tips), 'KIT') > 0 then
				raise notice 'Es KIT';
				if strpos(upper(nombre_del_plan_tips), 'FINANCIADO') > 0 then
					raise notice 'Es KIT Financiado en tips';
					if strpos(nombre_plan_rp, 'FINANCIADO') > 0 then
						revision_nombre_plan = 'ok';
					else
						raise notice 'No encontró la palabra financiado en nombre_plan_rp';
						revision_nombre_plan = 'No coincidente';
					end if;
				elsif strpos(upper(nombre_del_plan_tips), 'PREPAGO') > 0 then
					if strpos(nombre_plan_rp, 'PREPAGO') > 0 then
						revision_nombre_plan = 'ok';
					else
						revision_nombre_plan = 'No coincidente';
					end if;
				else
					revision_nombre_plan = 'No coincidente';
				end if;
			elsif strpos(upper(nombre_del_plan_tips), 'REPOS') > 0 then
				if strpos(nombre_plan_rp, 'REPOS') > 0 then
						revision_nombre_plan = 'ok';
					else
						revision_nombre_plan = 'No coincidente';
					end if;
			else
				raise notice 'No encontó la palabra kit en nombre_del_plan tips';
				revision_nombre_plan = 'No coincidente';
			end if;
		end if;
	end if;
	--raise notice 'Código plan RP: %', codigo_plan;
	return revision_nombre_plan;
end;
$BODY$;

ALTER FUNCTION public.cruce_ventas_tips_valida_nombre_plan(character varying, character varying, character varying, character varying, character varying, integer, integer)
    OWNER TO odoo;


-- FUNCTION: public.cruce_ventas_tips_valida_tipo_plan(character varying, character varying, character varying, integer, integer)

-- DROP FUNCTION public.cruce_ventas_tips_valida_tipo_plan(character varying, character varying, character varying, integer, integer);

CREATE OR REPLACE FUNCTION public.cruce_ventas_tips_valida_tipo_plan(
	tipo_de_plan character varying,
	producto character varying,
	producto1 character varying,
	l_id_1 integer,
	l_id_2 integer)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare
revision_tipo_plan varchar;

begin
	select
	case when producto1 is not null then
		case when
		(select 1
			where trim(upper(producto1)) in
		(
		select trim(upper(i.name)) from gestor_tipo_plan_team g
		join gestor_lineas_planes_team_gestor_tipo_plan_team_rel h on g.id=h.gestor_tipo_plan_team_id
		join gestor_lineas_planes_team i on i.id = h.gestor_lineas_planes_team_id
		where trim(upper(g.name)) = trim(upper(tipo_de_plan)))) = 1 then
			'ok'
		else
			case when l_id_1 is null and l_id_2 is null then
					'No encontrada en RP'
				when producto is null and producto1 is null then
					'Tipo de plan No encontrado en RP'
				else
					'No coincidente'
				end
		end
		when trim(upper(tipo_de_plan)) = trim(upper(producto)) or strpos(trim(upper(producto)), trim(upper(tipo_de_plan)))>0 then
			'ok'
		else
			case when
				(select 1
				where trim(upper(producto)) in
				(
				select trim(upper(i.name)) from gestor_tipo_plan_team g
				join gestor_lineas_planes_team_gestor_tipo_plan_team_rel h on g.id=h.gestor_tipo_plan_team_id
				join gestor_lineas_planes_team i on i.id = h.gestor_lineas_planes_team_id
				where trim(upper(g.name)) = trim(upper(tipo_de_plan)))) = 1 then
				'ok'
			else
				case when l_id_1 is null and l_id_2 is null then
					'No encontrada en RP'
				when producto is null and producto1 is null then
					'Tipo de plan No encontrado en RP'
				else
					'No coincidente'
				end
			end
	end into revision_tipo_plan;
	return revision_tipo_plan;
end;
$BODY$;

ALTER FUNCTION public.cruce_ventas_tips_valida_tipo_plan(character varying, character varying, character varying, integer, integer)
    OWNER TO odoo;


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
listado_columnas text := '';
values_insert text := ''; -- Listado de columnas a insertar
values_insert_2 text := ''; -- Listado de valores a insertar
values_insert_modelo text := '';
values_insert_archivo text := '';
target_table_tmp text := '';
reg RECORD;
registros int;
gestor_captura_hogar_team_id int;

begin
	set schema 'public';

	begin
		create temp table insert_from_csv ();
	exception when others then
		drop table insert_from_csv;
		create temp table insert_from_csv ();
	END;

	-- Limpiando tabla hogares
	if target_table = 'gestor_hogares_claro' then
		truncate table gestor_hogares_claro;
	end if;

	-- Limpiando tabla Pyme
	if target_table = 'gestor_pyme_claro' then
		truncate table gestor_pyme_claro;
	end if;

	-- add just enough number of columns
	for iter in 1..col_count
	loop
		execute format('alter table insert_from_csv add column col_%s text;', iter);
	end loop;

	-- copy the data from csv file
	execute format('copy insert_from_csv from %L with delimiter '';'' quote ''"'' csv', csv_path);

	select count(*) into registros from insert_from_csv;
	raise notice 'Registros importados: %', registros;

	iter := 1;
	col_first := (select col_1 from insert_from_csv limit 1);
	col_first_corregida := lower(replace(col_first, '.', '_'));

	contador := 1;
	-- update the column names based on the first row which has the column names
	for col in execute format('select unnest(string_to_array(lower(replace(replace(replace(replace(trim(insert_from_csv::text, ''()''),'' '',''_''), ''.'', ''_''), ''Í'', ''I''), ''-'',''_'')), '','')) from insert_from_csv where col_1 = %L', col_first)
	loop
		col_2 = col;
		if col = 'null' or col is null then
			col = 'NA';
			col_2 = 'NA';
		end if;
		if col = 'desc' or col = 'DESC' then
			col_2 = '"' || col || '"';
		else
			col_2 = col;
		end if;
		if strpos(listado_columnas, col_2) > 0 then
			col_2 = col_2 || '_' || contador;
			contador = contador + 1;
		end if;
		listado_columnas = listado_columnas || ',' || col_2;

		execute format('alter table insert_from_csv rename column col_%s to %s', iter, col_2);

		-- Creación de valores para la inserción
		if col = 'null' or col is null or col = 'NA' or col = 'na' then
			null;
		else
			if col = 'desc' or col = 'DESC' then
				col = '"' || col || '"';
			end if;
			if iter = 1 then
				values_insert := values_insert || col;
				values_insert_2 := values_insert_2 || 'COALESCE(' || col || ', '''')';
			else
				values_insert := values_insert || ', ' || col;
				values_insert_2 := values_insert_2 || ', ' || 'COALESCE(' || col || ', '''')';
			end if;
		end if;

	iter := iter + 1;
	end loop;

	-- Añadir campos de auditoria
	values_insert := values_insert || ', create_uid, create_date';
	values_insert_2 := values_insert_2 || ', ' || uid || ', now()';

	raise notice 'Values_insert: %', values_insert;
	raise notice 'Values_insert_2: %', values_insert_2;

	-- Actualizando datos adicionales
	if target_table = 'gestor_rp_team' and tipo_archivo not in ('SERVICIOS MÓVILES', 'PYMES', 'HOGAR') then
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
	raise notice 'Tipo de archivo: %', tipo_archivo;
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
			if strpos(values_insert_modelo, col_modelo) > 0 then
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
	execute format('delete from insert_from_csv where %s = %L', col_first_corregida, col_first_corregida);

	-- Creando la columna autonumérica
	-- Creando la secuencia debe quedar fuera de la función
	--CREATE SEQUENCE insert_from_csv_seq;

	execute format('alter table insert_from_csv add column rowID Integer default nextval(''insert_from_csv_seq'')');

	if target_table = 'gestor_rp_team' and tipo_archivo not in ('SERVICIOS MÓVILES', 'PYMES', 'HOGAR') then
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
		raise notice 'Values_insert: %', values_insert;
		raise notice 'Values_insert_2: %', values_insert_2;
		raise notice 'Values_insert_modelo: %', values_insert_modelo;

		BEGIN
			if tipo_archivo = 'SERVICIOS MÓVILES' and target_table = 'gestor_rp_team' then
				-- Cargando información temporal
				truncate table gestor_temp_min;
				insert into gestor_temp_min select min, producto from insert_from_csv where CLASE_PREPAGO = 'Postpago';
				-- Actualizar campos RP
				update gestor_rp_team a set producto1 = (select producto1 from gestor_temp_min b
														 where a.min=b.min );

			elsif target_table = 'gestor_rp_team' then
				select count(*) into registros from
				(select imei, min, iccid, custcode from insert_from_csv
				 intersect
				 select imei, min, iccid, custcode from gestor_rp_team) a;

				raise notice 'Registros faltantes: %', registros;
				update insert_from_csv set imei=0 where imei is null or imei='';
				execute format('insert into %s ( %s ) select %s from insert_from_csv group by %s
							   ON CONFLICT (imei, min, iccid, custcode)
							   DO UPDATE SET write_uid=2, write_date=now()',
							   target_table,
							   values_insert_modelo,
							   values_insert_2,
							   values_insert_2);
			else
				execute format('insert into %s ( %s ) select %s from insert_from_csv group by %s ON CONFLICT DO NOTHING',
							   target_table,
							   values_insert_modelo,
							   values_insert_2,
							   values_insert_2);
			end if;
        EXCEPTION WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
			null;
        END;

		if target_table = 'gestor_hogares_claro' then
			update gestor_captura_hogar_team a set
				(paquete_global, estado_venta, fecha, idasesor, nombreasesor, renta_global) =
				(select concatenar_campos_hogar_team(b.ot, b.cuenta, b.tipo_registro),
				(select id from gestor_estados_ap_team where name='Instalada'),
				to_date(b.fecha, 'DD/MM/YYYY'), b.idasesor, b.nombreasesor,
				(select sum(c.renta::float) from gestor_hogares_claro c
					where c.cuenta = a.cuenta and c.ot = a.ot
					and c.tipo_registro='Instalada')
				from gestor_hogares_claro b
				where a.cuenta=b.cuenta and a.ot=b.ot
				and tipo_registro='Instalada'
				limit 1);
			update gestor_captura_hogar_team a set
				(paquete_global, estado_venta, fecha, idasesor, nombreasesor, renta_global) =
				(select concatenar_campos_hogar_team(b.ot, b.cuenta, b.tipo_registro),
				(select id from gestor_estados_ap_team where name='Digitada'),
				to_date(b.fecha, 'DD/MM/YYYY'), b.idasesor, b.nombreasesor,
				(select sum(c.renta::float) from gestor_hogares_claro c
					where c.cuenta = a.cuenta and c.ot = a.ot
					and c.tipo_registro='Digitada')
				from gestor_hogares_claro b
				where a.cuenta=b.cuenta and a.ot=b.ot
				and tipo_registro='Digitada'
				limit 1)
			where estado_venta!=(select id from gestor_estados_ap_team where name='Instalada')
			or estado_venta is null;
			-- Recorriendo para generar detalle
			--Insertando
			truncate table gestor_captura_hogar_detalle_team;
			insert into gestor_captura_hogar_detalle_team
			(captura_hogar_id, fecha, tipored, division, renta, venta, paquete, paquete_pg, paquete_pvd, cod_campana, mintic, tipo_de_producto, tipo_plan_id )
			(select c.id, b.fecha, b.tipored, b.division, b.renta, b.venta, b.paquete, b.paquete_pg, b.paquete_pvd, b.cod_campana, b.mintic, b.tipo_de_producto,
			 		case when tipored = 'DTH' then
			 			355
			 		when venta = 'Servicios Principales' then
			 			354
			 		when venta = 'Servicios Adicionales' then
			 			353
			 		when venta = 'Upgrade' then
			 			356
					when venta = 'Migración' or venta = 'Migracion' then
						357
			 		end
					from gestor_hogares_claro b
					join gestor_captura_hogar_team c on b.cuenta=c.cuenta and b.ot=c.ot
					and b.tipo_registro=(select name from gestor_estados_ap_team d where d.id=c.estado_venta)
			where (c.id, b.paquete) not in (select d.captura_hogar_id, d.paquete from gestor_captura_hogar_detalle_team d)
			 );
			-- Actualizando el detalle
			-- Mejorar el rendimiento para evitar el truncate
			truncate table gestor_captura_hogar_detalle_agrupado_team;
			insert into gestor_captura_hogar_detalle_agrupado_team
			(captura_hogar_id, tipo_plan, renta_total)
			select captura_hogar_id, tipo_plan_id, sum(renta::int) from gestor_captura_hogar_detalle_team
			group by captura_hogar_id, tipo_plan_id;
			-- Actualizando
		end if;

end;
$BODY$;

ALTER FUNCTION public.load_csv_file(text, text, text, integer, integer)
    OWNER TO odoo;


-- FUNCTION: public.load_hogares_csv_file(text, text, integer)

-- DROP FUNCTION public.load_hogares_csv_file(text, text, integer);

CREATE OR REPLACE FUNCTION public.load_hogares_csv_file(
	target_table text,
	csv_path text,
	uid integer)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

begin

	truncate table gestor_hogares_claro;
	--copy gestor_hogares_claro
	--FROM '/var/lib/postgresql/data/compartida/rp/HOGARES.txt'
	--delimiter ';' csv header;

	execute format('copy gestor_hogares_claro from %L with delimiter '';'' quote ''"'' csv ', csv_path);

	update gestor_hogar_team a set 	(tipo_registro,
									idasesor,
									nombreasesor,
									paquete,
									fecha,
									cantserv,
									tipo_red,
									estrato_claro,
									visor_movil,
									val_identidad,
									serial_captor,
									venta,
									procesamiento_uid,
									procesamiento_date
									) = (select tipo_registro,
												 idasesor,
												 nombreasesor,
												 paquete,
												 TO_DATE(fecha,'dd/mm/yyyy'),
												 cantserv,
												 tipored,
												 estrato,
												 visor_movil,
												 val_identidad,
												 serial_captor,
										 		 venta,
										 		 uid,
										 		 now()
												from gestor_hogares_claro b
												where b.cuenta=a.cuenta
												and b.ot=a.ot
												and b.paquete=(select name from product_template c
																join product_product d on d.product_tmpl_id = c.id
																and d.id=a.producto_id)
												order by tipo_registro desc,fecha, cuenta, ot, paquete
												limit 1
												);

end;
$BODY$;

ALTER FUNCTION public.load_hogares_csv_file(text, text, integer)
    OWNER TO odoo;


-- FUNCTION: public.load_ventas_tips()

-- DROP FUNCTION public.load_ventas_tips();

CREATE OR REPLACE FUNCTION public.load_ventas_tips(
	)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
declare

begin
	set schema 'public';

	-- Corrige la consulta de ventas de TIPS y las carga en el modelo ventas de Odoo
	-- Adiciona valores KEY de odoo

	truncate table gestor_consulta_ventas_tips;
	insert into gestor_consulta_ventas_tips
	(fecha,
	min,
	iccid,
	imei,
	contrato,
	valor,
	custcode,
	marca_del_equipo,
	nombre_de_equipo_en_stok,
	nombre_de_la_simcard_en_stok,
	modelo_del_equipo,
	valor_del_equipo,
	nombre_para_mostrar_del_vendedor,
	tipo_de_vendedor,
	regional,
	sucursal,
	ciudad,
	nombre_del_plan,
	tipo_de_plan,
	valor_cobrado,
	codigo_distribuidor,
	cliente_nombre,
	cliente_id,
	vendedor_nombre,
	vendedor_id,
	cargo_fijo_mensual,
	permanencia_pendiente,
	clasificacion_del_plan,
	es_multiplay,
	es_upgrade,
	es_linea_nueva,
	es_venta_digital,
	es_con_equipo,
	es_telemercadeo,
	fecha_de_activacion_en_punto_de_activacion,
	usuario_creador,
	venta_id,
	meses,
	plan_id,
	estado_tips)
	select a.fecha,
	a.min,
	a.iccid,
	a.imei,
	a.contrato,
	a.valor,
	a.custcode,
	a.marca_del_equipo,
	a.nombre_de_equipo_en_stok,
	a.nombre_de_la_simcard_en_stok,
	a.modelo_del_equipo,
	a.valor_del_equipo,
	a.nombre_para_mostrar_del_vendedor,
	a.tipo_de_vendedor,
	a.regional,
	a.sucursal,
	a.ciudad,
	a.nombre_del_plan,
	a.tipo_de_plan,
	a.valor_cobrado,
	a.código_distribuidor,
	a.cliente_nombre,
	a.cliente_id,
	a.vendedor_nombre,
	a.vendedor_id,
	a.cargo_fijo_mensual,
	a.permanencia_pendiente,
	a.clasificación_del_plan,
	case a.es_multiplay when 'True' then true else false end es_multiplay,
	case a.es_upgrade when 'True' then true else false end es_upgrade,
	case a.es_línea_nueva when 'True' then true else false end es_linea_nueva,
	case a.es_venta_digital when 'True' then true else false end es_venta_digital,
	case a.es_con_equipo when 'True' then true else false end es_con_equipo,
	case a.es_telemercadeo when 'True' then true else false end es_telemercadeo,
	a.fecha_de_activación_en_punto_de_activación::date fecha_de_activación_en_punto_de_activación,
	a.usuario_creador,
	a.venta_id,
	date_part('month',age(now(), a.fecha)) meses,
	b.id plan_id, a.estado
	from gestor_consulta_ventas_tips_tmp a
	join gestor_planes_team b on trim(upper(a.nombre_del_plan)) = trim(upper(b.name));

	update gestor_consulta_ventas_tips set id=venta_id::int;

end;
$BODY$;

ALTER FUNCTION public.load_ventas_tips()
    OWNER TO odoo;
