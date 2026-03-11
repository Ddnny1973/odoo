-- Table: public.gestor_consulta_ventas_tips_tmp

DROP TABLE public.gestor_consulta_ventas_tips_tmp;

CREATE TABLE public.gestor_consulta_ventas_tips_tmp
(
    fecha date,
    min character(250) COLLATE pg_catalog."default",
    iccid character(250) COLLATE pg_catalog."default",
    imei character(250) COLLATE pg_catalog."default",
    estado character(250) COLLATE pg_catalog."default",
    contrato character(250) COLLATE pg_catalog."default",
    valor character(250) COLLATE pg_catalog."default",
    custcode character(250) COLLATE pg_catalog."default",
    marca_del_equipo character(250) COLLATE pg_catalog."default",
    nombre_de_equipo_en_stok character(250) COLLATE pg_catalog."default",
    nombre_de_la_simcard_en_stok character(250) COLLATE pg_catalog."default",
    modelo_del_equipo character(250) COLLATE pg_catalog."default",
    valor_del_equipo character(250) COLLATE pg_catalog."default",
    nombre_para_mostrar_del_vendedor character(250) COLLATE pg_catalog."default",
    tipo_de_vendedor character(250) COLLATE pg_catalog."default",
    regional character(250) COLLATE pg_catalog."default",
    sucursal character(250) COLLATE pg_catalog."default",
    ciudad character(250) COLLATE pg_catalog."default",
    nombre_del_plan character(250) COLLATE pg_catalog."default",
    tipo_de_plan character(250) COLLATE pg_catalog."default",
    valor_cobrado character(250) COLLATE pg_catalog."default",
    cargo_fijo_mensual character(250) COLLATE pg_catalog."default",
    "código_distribuidor" character(250) COLLATE pg_catalog."default",
    cliente_nombre character(250) COLLATE pg_catalog."default",
    cliente_id character(250) COLLATE pg_catalog."default",
    vendedor_nombre character(250) COLLATE pg_catalog."default",
    vendedor_id character(250) COLLATE pg_catalog."default",
    permanencia_pendiente character(250) COLLATE pg_catalog."default",
    "clasificación_del_plan" character(250) COLLATE pg_catalog."default",
    es_multiplay character(250) COLLATE pg_catalog."default",
    es_upgrade character(250) COLLATE pg_catalog."default",
    "es_línea_nueva" character(250) COLLATE pg_catalog."default",
    es_venta_digital character(250) COLLATE pg_catalog."default",
    es_con_equipo character(250) COLLATE pg_catalog."default",
    es_telemercadeo character(250) COLLATE pg_catalog."default",
    "fecha_de_activación_en_punto_de_activación" character(250) COLLATE pg_catalog."default",
    usuario_creador character(250) COLLATE pg_catalog."default",
    venta_id integer,
    comision_pagada character(250) COLLATE pg_catalog."default",
    reconocimiento_pagado character(250) COLLATE pg_catalog."default",
    tipo_de_activacion character(250) COLLATE pg_catalog."default",
    con_equipo character(250) COLLATE pg_catalog."default"
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.gestor_consulta_ventas_tips_tmp
    OWNER to odoo;